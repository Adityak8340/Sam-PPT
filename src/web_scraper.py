"""
Web Scraper Module
Extracts HTML content and takes screenshots of web pages
"""

import os
import time
import re
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


@dataclass
class WebPageData:
    """Data class to hold scraped webpage information"""
    url: str
    title: str
    screenshot_path: Optional[str]
    main_content: str
    headings: list[str]
    paragraphs: list[str]
    meta_description: str
    error: Optional[str] = None


class WebScraper:
    """Scrapes web pages for content and screenshots"""
    
    def __init__(self, output_dir: str = "temp_screenshots"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def scrape_page(self, url: str, take_screenshot: bool = True) -> WebPageData:
        """
        Scrape a web page for content and optionally take a screenshot
        
        Args:
            url: URL of the page to scrape
            take_screenshot: Whether to capture a screenshot
            
        Returns:
            WebPageData object with scraped content
        """
        screenshot_path = None
        
        # Extract content using requests + BeautifulSoup
        content_data = self._extract_content(url)
        
        # Take screenshot using Playwright
        if take_screenshot:
            screenshot_path = self._take_screenshot(url)
        
        return WebPageData(
            url=url,
            title=content_data.get('title', 'Unknown Title'),
            screenshot_path=screenshot_path,
            main_content=content_data.get('main_content', ''),
            headings=content_data.get('headings', []),
            paragraphs=content_data.get('paragraphs', []),
            meta_description=content_data.get('meta_description', ''),
            error=content_data.get('error')
        )
    
    def _extract_content(self, url: str) -> dict:
        """Extract text content from a web page"""
        result = {
            'title': '',
            'main_content': '',
            'headings': [],
            'paragraphs': [],
            'meta_description': '',
            'error': None
        }
        
        try:
            soup = self._fetch_and_parse(url)
            self._extract_title(soup, url, result)
            self._extract_meta_description(soup, result)
            self._extract_headings(soup, result)
            self._extract_paragraphs(soup, result)
            self._extract_main_content(soup, result)
            
        except requests.exceptions.Timeout:
            result['error'] = "Request timed out"
        except requests.exceptions.RequestException as e:
            result['error'] = f"Request error: {str(e)[:100]}"
        except Exception as e:
            result['error'] = f"Error: {str(e)[:100]}"
        
        return result
    
    def _fetch_and_parse(self, url: str) -> BeautifulSoup:
        """Fetch URL and return parsed BeautifulSoup object"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            element.decompose()
        
        return soup
    
    def _extract_title(self, soup: BeautifulSoup, url: str, result: dict) -> None:
        """Extract page title"""
        title_tag = soup.find('title')
        result['title'] = title_tag.get_text(strip=True) if title_tag else urlparse(url).netloc
    
    def _extract_meta_description(self, soup: BeautifulSoup, result: dict) -> None:
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            content = meta_desc.get('content')
            if content:
                result['meta_description'] = str(content)[:500]
    
    def _extract_headings(self, soup: BeautifulSoup, result: dict) -> None:
        """Extract page headings"""
        headings = []
        for level in ['h1', 'h2', 'h3']:
            for heading in soup.find_all(level)[:10]:
                text = heading.get_text(strip=True)
                if text and len(text) > 3:
                    headings.append(text[:200])
        result['headings'] = headings[:15]
    
    def _extract_paragraphs(self, soup: BeautifulSoup, result: dict) -> None:
        """Extract page paragraphs"""
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 50:
                text = re.sub(r'\s+', ' ', text)
                paragraphs.append(text[:500])
        result['paragraphs'] = paragraphs[:20]
    
    def _extract_main_content(self, soup: BeautifulSoup, result: dict) -> None:
        """Extract main content text"""
        main_elements = soup.find_all(
            ['article', 'main', 'div'], 
            class_=re.compile(r'content|article|post|body', re.I)
        )
        
        if main_elements:
            main_text = main_elements[0].get_text(separator='\n', strip=True)
        else:
            body = soup.find('body')
            main_text = body.get_text(separator='\n', strip=True) if body else ''
        
        main_text = re.sub(r'\n\s*\n', '\n\n', main_text)
        main_text = re.sub(r' +', ' ', main_text)
        result['main_content'] = main_text[:5000]
    
    def _take_screenshot(self, url: str) -> Optional[str]:
        """Take a screenshot of a web page using Playwright"""
        try:
            # Generate filename from URL
            parsed = urlparse(url)
            safe_name = re.sub(r'[^\\w_.-]', '_', parsed.netloc + parsed.path)[:50]
            screenshot_path = os.path.join(self.output_dir, f"{safe_name}_{int(time.time())}.png")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 900},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()
                
                try:
                    page.goto(url, wait_until='networkidle', timeout=30000)
                    time.sleep(2)  # Wait for any lazy-loaded content
                    
                    # Take full page screenshot
                    page.screenshot(path=screenshot_path, full_page=False)
                    
                except PlaywrightTimeout:
                    # Try with shorter timeout
                    try:
                        page.goto(url, wait_until='domcontentloaded', timeout=15000)
                        page.screenshot(path=screenshot_path, full_page=False)
                    except Exception:
                        pass
                
                finally:
                    browser.close()
            
            if os.path.exists(screenshot_path):
                return screenshot_path
                
        except Exception as e:
            print(f"Screenshot error for {url}: {e}")
        
        return None
    
    def scrape_multiple(self, urls: list[str], take_screenshots: bool = True, 
                       progress_callback=None) -> list[WebPageData]:
        """
        Scrape multiple web pages
        
        Args:
            urls: List of URLs to scrape
            take_screenshots: Whether to capture screenshots
            progress_callback: Optional callback function(current, total, url)
            
        Returns:
            List of WebPageData objects
        """
        results = []
        total = len(urls)
        
        for i, url in enumerate(urls):
            if progress_callback:
                progress_callback(i + 1, total, url)
            
            data = self.scrape_page(url, take_screenshots)
            results.append(data)
        
        return results


def scrape_websites(urls: list[str], output_dir: str = "temp_screenshots",
                   progress_callback=None) -> list[WebPageData]:
    """
    Main function to scrape multiple websites
    
    Args:
        urls: List of URLs to scrape
        output_dir: Directory to save screenshots
        progress_callback: Optional progress callback
        
    Returns:
        List of WebPageData objects
    """
    scraper = WebScraper(output_dir)
    return scraper.scrape_multiple(urls, take_screenshots=True, 
                                   progress_callback=progress_callback)
