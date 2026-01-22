"""
Image Search Module
Uses SerpAPI Google Lens for reliable reverse image search
"""

from __future__ import annotations

import base64
import io
import os
import re
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from PIL import Image as PILImage

# Load environment variables
load_dotenv()

# Constants
SERP_API_KEY = os.getenv("SERP_API_KEY", "")
SERP_API_BASE_URL = "https://serpapi.com/search"

# Known e-commerce/shopping domains to prioritize
SHOPPING_DOMAINS = [
    'amazon.com', 'amazon.in', 'amazon.co.uk', 'amazon.de',
    'flipkart.com', 'myntra.com', 'ajio.com',
    'ebay.com', 'ebay.in', 'ebay.co.uk',
    'walmart.com', 'target.com', 'bestbuy.com',
    'aliexpress.com', 'alibaba.com',
    'snapdeal.com', 'paytmmall.com', 'tatacliq.com',
    'croma.com', 'reliancedigital.in', 'vijaysales.com',
    'jiomart.com', 'bigbasket.com', 'blinkit.com',
    'meesho.com', 'indiamart.com', 'shopclues.com',
    'etsy.com', 'wayfair.com', 'overstock.com',
    'homedepot.com', 'lowes.com', 'ikea.com',
    'costco.com', 'samsclub.com', 'kohls.com',
    'macys.com', 'nordstrom.com', 'zappos.com',
    'newegg.com', 'bhphotovideo.com',
]


class ReverseImageSearch:
    """Performs reverse image search using SerpAPI Google Lens"""
    
    def __init__(self) -> None:
        self.api_key = SERP_API_KEY
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
    
    def search_by_image(self, image_path: str, num_results: int = 5) -> list[dict]:
        """
        Perform reverse image search and return top website results
        
        Args:
            image_path: Path to the image file
            num_results: Number of top results to return
            
        Returns:
            List of dictionaries with 'title' and 'url' keys
        """
        results: list[dict] = []
        
        if not self.api_key:
            print("Error: SERP_API_KEY not found in .env file")
            return results
        
        # Try SerpAPI Google Lens first (best for product matching)
        try:
            print("Searching with SerpAPI Google Lens (product focus)...")
            results = self._search_serpapi_lens(image_path, num_results * 2)  # Get more to filter
            if results:
                print(f"Found {len(results)} product results via SerpAPI Google Lens")
                # Prioritize shopping results
                shopping = [r for r in results if self._is_shopping_domain(urlparse(r['url']).netloc)]
                others = [r for r in results if not self._is_shopping_domain(urlparse(r['url']).netloc)]
                results = (shopping + others)[:num_results]
                return results
        except Exception as e:
            print(f"SerpAPI Google Lens search failed: {e}")
        
        # Fallback to SerpAPI Google Reverse Image Search
        if not results:
            try:
                print("Trying SerpAPI Google Reverse Image search...")
                results = self._search_serpapi_reverse(image_path, num_results)
                if results:
                    print(f"Found {len(results)} results via SerpAPI Reverse Image")
                    return results[:num_results]
            except Exception as e:
                print(f"SerpAPI Reverse Image search failed: {e}")
        
        return results[:num_results]
    
    def _search_serpapi_lens(self, image_path: str, num_results: int) -> list[dict]:
        """Search using SerpAPI Google Lens"""
        results: list[dict] = []
        
        # First upload the image to get a URL
        image_url = self._upload_image(image_path)
        if not image_url:
            print("Could not upload image for Google Lens search")
            return results
        
        try:
            params = {
                'engine': 'google_lens',
                'url': image_url,
                'api_key': self.api_key,
            }
            
            response = self.session.get(SERP_API_BASE_URL, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                results = self._parse_serpapi_lens_results(data, num_results)
            else:
                error_text = response.text[:500] if response.text else "No error message"
                print(f"SerpAPI returned status {response.status_code}: {error_text}")
                
        except Exception as e:
            print(f"SerpAPI Lens error: {e}")
        
        return results
    
    def _parse_serpapi_lens_results(self, data: dict, num_results: int) -> list[dict]:
        """Parse SerpAPI Google Lens results - prioritize shopping/product results"""
        shopping_results: list[dict] = []
        other_results: list[dict] = []
        seen_domains: set[str] = set()
        
        # First priority: Shopping results (product listings with prices)
        self._extract_shopping_results(data, shopping_results, seen_domains)
        
        # Second priority: Visual matches from known shopping sites
        self._extract_visual_matches(data, shopping_results, other_results, seen_domains)
        
        # Third priority: Knowledge graph shopping links
        self._extract_knowledge_graph(data, other_results, seen_domains, num_results)
        
        # Fourth priority: Text/organic results from shopping sites
        self._extract_text_results(data, other_results, seen_domains, num_results)
        
        # Combine: shopping results first, then others
        all_results = shopping_results + other_results
        return all_results[:num_results]
    
    def _extract_shopping_results(
        self, data: dict, results: list[dict], seen_domains: set[str]
    ) -> None:
        """Extract shopping results with prices - these are product listings."""
        # Google Lens returns shopping results in 'shopping_results' or 'visual_matches' with price
        shopping = data.get('shopping_results', [])
        for item in shopping:
            url = item.get('link', '') or item.get('source', '')
            title = item.get('title', '')
            price = item.get('price', '')
            
            if url and self._is_valid_result_url(url, seen_domains):
                domain = urlparse(url).netloc
                seen_domains.add(domain)
                display_title = f"{title} - {price}" if price else title or domain
                results.append({'title': display_title, 'url': url})
                print(f"  [SHOP] {display_title} - {url[:60]}...")
    
    def _extract_visual_matches(
        self, data: dict, shopping_results: list[dict], 
        other_results: list[dict], seen_domains: set[str]
    ) -> None:
        """Extract results from visual_matches field - prioritize shopping sites."""
        visual_matches = data.get('visual_matches', [])
        for match in visual_matches:
            url = match.get('link', '')
            title = match.get('title', '') or match.get('source', '')
            price = match.get('price', {})
            
            # Extract price string
            if isinstance(price, dict):
                price_str = price.get('value', '')
            elif price:
                price_str = str(price)
            else:
                price_str = ''
            
            if not url or not self._is_valid_result_url(url, seen_domains):
                continue
            
            domain = urlparse(url).netloc.lower()
            seen_domains.add(domain)
            
            display_title = f"{title} - {price_str}" if price_str else title or domain
            result = {'title': display_title, 'url': url}
            
            # Check if it's a known shopping domain
            if self._is_shopping_domain(domain):
                shopping_results.append(result)
                print(f"  [SHOP] {display_title} - {url[:60]}...")
            else:
                other_results.append(result)
                print(f"  [OTHER] {display_title} - {url[:60]}...")
    
    def _is_shopping_domain(self, domain: str) -> bool:
        """Check if domain is a known shopping/e-commerce site."""
        domain_lower = domain.lower()
        return any(shop in domain_lower for shop in SHOPPING_DOMAINS)
    
    def _extract_knowledge_graph(
        self, data: dict, results: list[dict], seen_domains: set[str], num_results: int
    ) -> None:
        """Extract results from knowledge_graph field."""
        knowledge_graph = data.get('knowledge_graph', [])
        if not isinstance(knowledge_graph, list):
            return
        for item in knowledge_graph:
            if len(results) >= num_results:
                return
            url = item.get('link', '') or item.get('source', {}).get('link', '')
            title = item.get('title', '')
            self._add_result_if_valid(url, title, results, seen_domains)
    
    def _extract_text_results(
        self, data: dict, results: list[dict], seen_domains: set[str], num_results: int
    ) -> None:
        """Extract results from text_results or organic_results field."""
        text_results = data.get('text_results', []) or data.get('organic_results', [])
        for item in text_results:
            if len(results) >= num_results:
                return
            url = item.get('link', '')
            title = item.get('title', '')
            self._add_result_if_valid(url, title, results, seen_domains)
    
    def _add_result_if_valid(
        self, url: str, title: str, results: list[dict], seen_domains: set[str]
    ) -> None:
        """Add a result to the list if the URL is valid."""
        if url and self._is_valid_result_url(url, seen_domains):
            domain = urlparse(url).netloc
            seen_domains.add(domain)
            display_title = title or domain
            results.append({'title': display_title, 'url': url})
            print(f"  Found: {display_title} - {url[:70]}...")
    
    def _search_serpapi_reverse(self, image_path: str, num_results: int) -> list[dict]:
        """Search using SerpAPI Google Reverse Image Search"""
        results: list[dict] = []
        
        # First upload the image to get a URL
        image_url = self._upload_image(image_path)
        if not image_url:
            print("Could not upload image for reverse image search")
            return results
        
        try:
            params = {
                'engine': 'google_reverse_image',
                'image_url': image_url,
                'api_key': self.api_key,
            }
            
            response = self.session.get(SERP_API_BASE_URL, params=params, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                results = self._parse_serpapi_reverse_results(data, num_results)
            else:
                print(f"SerpAPI returned status {response.status_code}")
                
        except Exception as e:
            print(f"SerpAPI Reverse error: {e}")
        
        return results
    
    def _parse_serpapi_reverse_results(self, data: dict, num_results: int) -> list[dict]:
        """Parse SerpAPI Google Reverse Image Search results"""
        results: list[dict] = []
        seen_domains: set[str] = set()
        
        # Get image results
        self._extract_image_results(data, results, seen_domains, num_results)
        
        # Also check inline images for source pages
        self._extract_inline_images(data, results, seen_domains, num_results)
        
        return results
    
    def _extract_image_results(
        self, data: dict, results: list[dict], seen_domains: set[str], num_results: int
    ) -> None:
        """Extract results from image_results field."""
        image_results = data.get('image_results', [])
        for match in image_results:
            if len(results) >= num_results:
                return
            url = match.get('link', '') or match.get('source', '')
            title = match.get('title', '') or match.get('snippet', '')
            self._add_result_if_valid(url, title, results, seen_domains)
    
    def _extract_inline_images(
        self, data: dict, results: list[dict], seen_domains: set[str], num_results: int
    ) -> None:
        """Extract results from inline_images field."""
        inline_images = data.get('inline_images', [])
        for img in inline_images:
            if len(results) >= num_results:
                return
            url = img.get('source', '') or img.get('link', '')
            title = img.get('title', '')
            self._add_result_if_valid(url, title, results, seen_domains)
    
    def _upload_image(self, image_path: str) -> str | None:
        """Upload image to freeimage.host and return the URL"""
        try:
            img_data = self._prepare_image_for_upload(image_path)
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            response = self.session.post(
                "https://freeimage.host/api/1/upload",
                data={
                    'key': '6d207e02198a847aa98d0a2a901485a5',
                    'source': img_base64,
                    'format': 'json',
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status_code') == 200:
                    url = data.get('image', {}).get('url')
                    if url:
                        print(f"Image uploaded: {url}")
                        return url
        except Exception as e:
            print(f"Image upload failed: {e}")
        return None
    
    def _prepare_image_for_upload(self, image_path: str) -> bytes:
        """Prepare image for upload - resize if needed"""
        img = PILImage.open(image_path)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large (max 1200px on longest side)
        max_size = 1200
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, PILImage.Resampling.LANCZOS)
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
    
    def _is_valid_result_url(self, url: str, seen_domains: set[str]) -> bool:
        """Check if URL is a valid webpage result (not an image URL or spam site)"""
        if not url or not url.startswith('http'):
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # Skip if already seen this domain
            if domain in seen_domains:
                return False
            
            # Skip search engines and their related domains
            excluded_domains = [
                'google.com', 'googleapis.com', 'gstatic.com',
                'bing.com', 'microsoft.com', 'msn.com', 'live.com',
                'yahoo.com', 'yandex.com', 'yandex.ru', 'baidu.com',
                'duckduckgo.com', 'ask.com',
                'tineye.com', 'serpapi.com',
            ]
            if any(excl in domain for excl in excluded_domains):
                return False
            
            # Skip image hosting / CDN domains
            image_domains = [
                'imgur.com', 'imgbb.com', 'i.imgur.com',
                'flickr.com', 'staticflickr.com',
                'cloudinary.com', 'res.cloudinary.com',
                'pinimg.com', 'pbs.twimg.com',
                'media.tumblr.com', 'images.unsplash.com',
                'cdn.shopify.com', 'encrypted-tbn',
                'iili.io', 'freeimage.host', '0x0.st',
            ]
            if any(img_domain in domain for img_domain in image_domains):
                return False
            
            # Skip social media (not product pages)
            social_domains = [
                'facebook.com', 'instagram.com', 'twitter.com', 
                'tiktok.com', 'pinterest.com', 'linkedin.com',
                'reddit.com', 'tumblr.com',
            ]
            if any(social in domain for social in social_domains):
                return False
            
            # Skip video platforms (unless it's a product video)
            video_domains = ['youtube.com', 'youtu.be', 'vimeo.com']
            if any(video in domain for video in video_domains):
                return False
            
            # Skip suspicious/spam domains (common patterns)
            spam_patterns = [
                'bank', 'family.org', 'fellowship.org', 'church',
                'carbiderelatedtech', 'curaresaude', 'advogados',
                'school.org', 'spec-school', 'muhouseware.en.made-in-china',
            ]
            if any(spam in domain for spam in spam_patterns):
                return False
            
            # Skip direct image file URLs
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
            if any(path.endswith(ext) for ext in image_extensions):
                return False
            
            # Skip URLs with image dimension patterns
            if self._has_image_dimensions(url):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _has_image_dimensions(self, url: str) -> bool:
        """Check if URL contains image dimension patterns"""
        dimension_patterns = [
            r'\d{2,4}x\d{2,4}',  # 800x600, 1920x1080
            r'_\d{2,4}x\d{2,4}',  # _800x600
            r'-\d{2,4}x\d{2,4}',  # -800x600
            r'/\d{2,4}x\d{2,4}/',  # /800x600/
        ]
        return any(re.search(pattern, url) for pattern in dimension_patterns)
    
    def close(self) -> None:
        """Clean up resources"""
        self.session.close()


def search_image(image_path: str, num_results: int = 5) -> list[dict]:
    """
    Convenience function to perform reverse image search
    
    Args:
        image_path: Path to the image file
        num_results: Number of results to return
        
    Returns:
        List of dictionaries with 'title' and 'url' keys
    """
    searcher = ReverseImageSearch()
    try:
        return searcher.search_by_image(image_path, num_results)
    finally:
        searcher.close()
