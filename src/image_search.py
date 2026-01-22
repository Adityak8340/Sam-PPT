"""
Image Search Module
Uses free methods to perform reverse image search
"""

import base64
import time
import os
from typing import Optional
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Constants
MIME_JPEG = 'image/jpeg'


class ReverseImageSearch:
    """Performs reverse image search using Google Lens"""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        return driver
    
    def search_by_image(self, image_path: str, num_results: int = 5) -> list[dict]:
        """
        Perform reverse image search and return top website results
        
        Args:
            image_path: Path to the image file
            num_results: Number of top results to return
            
        Returns:
            List of dictionaries with 'title' and 'url' keys
        """
        results = []
        
        try:
            self.driver = self._setup_driver()
            
            # Read and encode the image
            with open(image_path, 'rb') as img_file:
                image_data = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Get file extension
            ext = os.path.splitext(image_path)[1].lower()
            mime_types = {
                '.jpg': MIME_JPEG,
                '.jpeg': MIME_JPEG,
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp'
            }
            mime_type = mime_types.get(ext, MIME_JPEG)
            
            # Navigate to Google Images
            self.driver.get("https://www.google.com/imghp")
            time.sleep(2)
            
            # Try to find and click the camera icon for image search
            try:
                # Look for the camera/lens button
                camera_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Search by image'], div[data-ved] svg[class*='Gdd5U']"))
                )
                camera_button.click()
                time.sleep(1)
            except Exception:
                # Alternative: Try finding by class or other selectors
                try:
                    camera_buttons = self.driver.find_elements(By.CSS_SELECTOR, "[aria-label*='image'], [aria-label*='camera'], .nDcEnd")
                    if camera_buttons:
                        camera_buttons[0].click()
                        time.sleep(1)
                except Exception:
                    pass
            
            # Try to upload the image using JavaScript
            # Create a file input and trigger upload
            script = """
            var input = document.createElement('input');
            input.type = 'file';
            input.id = 'image-upload-input';
            input.style.display = 'none';
            document.body.appendChild(input);
            return input;
            """
            self.driver.execute_script(script)
            
            # Find actual file input on the page
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            
            if file_inputs:
                # Use the file input directly
                file_inputs[0].send_keys(os.path.abspath(image_path))
                time.sleep(5)  # Wait for upload and search
            else:
                # Alternative: Use drag and drop or paste
                # Navigate directly with image URL approach
                data_url = f"data:{mime_type};base64,{image_data}"
                
                # Try using Google Lens URL directly
                lens_url = "https://lens.google.com/uploadbyurl?url=" + quote(data_url[:1000])
                self.driver.get(lens_url)
                time.sleep(3)
            
            # Wait for results to load
            time.sleep(3)
            
            # Extract search results
            results = self._extract_results(num_results)
            
            # If no results from main method, try alternative approach
            if not results:
                results = self._alternative_search(image_path, num_results)
            
        except Exception as e:
            print(f"Error during image search: {e}")
            # Fallback to alternative method
            results = self._alternative_search(image_path, num_results)
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
        
        return results
    
    def _get_element_title(self, elem, url: str) -> str:
        """Extract title from an element, with fallback to parent"""
        title = elem.text or elem.get_attribute('title') or url
        if not title or len(title.strip()) < 3:
            try:
                parent = elem.find_element(By.XPATH, "./..")
                title = parent.text[:100] if parent.text else url
            except Exception:
                title = url
        return title[:200]
    
    def _process_search_element(self, elem, seen_urls: set, results: list, num_results: int) -> bool:
        """Process a single search element and add to results if valid. Returns True if limit reached."""
        try:
            url = elem.get_attribute('href')
            if not url or not self._is_valid_url(url) or url in seen_urls:
                return False
            
            title = self._get_element_title(elem, url)
            seen_urls.add(url)
            results.append({'title': title, 'url': url})
            return len(results) >= num_results
        except Exception:
            return False
    
    def _extract_results(self, num_results: int) -> list[dict]:
        """Extract search results from the current page"""
        results: list[dict] = []
        
        if not self.driver:
            return results
        
        time.sleep(2)
        
        selectors = [
            "a[href*='http']:not([href*='google.com']):not([href*='gstatic'])",
            "div[data-lpage] a",
            ".g a[href]",
            "a[ping]",
            "[data-ved] a[href*='http']"
        ]
        
        seen_urls: set[str] = set()
        
        for selector in selectors:
            if self._extract_from_selector(selector, seen_urls, results, num_results):
                break
        
        return results[:num_results]
    
    def _extract_from_selector(self, selector: str, seen_urls: set, 
                               results: list, num_results: int) -> bool:
        """Extract results from a single selector. Returns True if limit reached."""
        if not self.driver:
            return False
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                if self._process_search_element(elem, seen_urls, results, num_results):
                    return True
        except Exception:
            pass
        return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and not a Google internal link"""
        if not url:
            return False
        
        excluded_domains = [
            'google.com', 'gstatic.com', 'googleapis.com',
            'youtube.com', 'schema.org', 'w3.org',
            'javascript:', 'mailto:', '#'
        ]
        
        for domain in excluded_domains:
            if domain in url.lower():
                return False
        
        return url.startswith('http://') or url.startswith('https://')
    
    def _alternative_search(self, image_path: str, num_results: int) -> list[dict]:
        """Alternative search method using TinEye or Bing"""
        results = []
        
        try:
            if self.driver is None:
                self.driver = self._setup_driver()
            
            # Try Bing Visual Search
            self.driver.get("https://www.bing.com/images")
            time.sleep(2)
            
            # Look for image search input
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            
            if file_inputs:
                file_inputs[0].send_keys(os.path.abspath(image_path))
                time.sleep(5)
                
                results = self._extract_bing_results(num_results)
            
        except Exception as e:
            print(f"Alternative search error: {e}")
        
        return results
    
    def _extract_bing_results(self, num_results: int) -> list[dict]:
        """Extract results from Bing Visual Search"""
        results: list[dict] = []
        
        if not self.driver:
            return results
        
        time.sleep(3)
        links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='http']")
        seen_urls: set[str] = set()
        
        for link in links:
            if self._process_bing_link(link, seen_urls, results, num_results):
                break
        
        return results
    
    def _process_bing_link(self, link, seen_urls: set, results: list, num_results: int) -> bool:
        """Process a single Bing link. Returns True if limit reached."""
        try:
            url = link.get_attribute('href')
            if not url or not self._is_valid_url(url) or 'bing.com' in url.lower():
                return False
            if url in seen_urls:
                return False
            
            title = link.text or link.get_attribute('title') or url
            seen_urls.add(url)
            results.append({'title': title[:200], 'url': url})
            return len(results) >= num_results
        except Exception:
            return False


def search_image(image_path: str, num_results: int = 5) -> list[dict]:
    """
    Main function to perform reverse image search
    
    Args:
        image_path: Path to the image file
        num_results: Number of results to return
        
    Returns:
        List of dictionaries with website information
    """
    searcher = ReverseImageSearch()
    return searcher.search_by_image(image_path, num_results)
