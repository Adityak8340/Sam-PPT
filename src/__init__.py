"""
Package initialization for Sam-PPT
"""

from .image_search import search_image, ReverseImageSearch
from .web_scraper import scrape_websites, WebScraper, WebPageData
from .ppt_generator import create_presentation, PPTGenerator

__all__ = [
    'search_image',
    'ReverseImageSearch',
    'scrape_websites',
    'WebScraper',
    'WebPageData',
    'create_presentation',
    'PPTGenerator',
]
