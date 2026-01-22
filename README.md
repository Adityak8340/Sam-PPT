# Sam-PPT 🔍📊

A Streamlit application that performs reverse image search and automatically generates professional PowerPoint presentations with the search results.

## Features

- **Reverse Image Search**: Upload any image and find matching websites using Google/Bing visual search
- **Configurable Results**: Choose how many top websites to include (1-10)
- **Web Scraping**: Automatically extracts content from found websites
- **Screenshots**: Captures screenshots of each website
- **PowerPoint Generation**: Creates a professional presentation with:
  - Title slide with the input image
  - Summary slide listing all found websites
  - Detailed slides for each website with screenshots and content
  - Conclusion slide

## Installation

1. **Activate the virtual environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Usage

1. **Run the application:**
   ```bash
   streamlit run src/app.py
   ```

2. **Upload an image** using the file uploader

3. **Configure** the number of websites to search for in the sidebar

4. **Click "Start Search & Generate PPT"** to begin processing

5. **Download** the generated PowerPoint presentation

## Project Structure

```
Sam-PPT/
├── src/
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Main Streamlit application
│   ├── image_search.py      # Reverse image search module
│   ├── web_scraper.py       # Web scraping and screenshots
│   └── ppt_generator.py     # PowerPoint generation
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── venv/                   # Virtual environment
```

## Dependencies

- **streamlit**: Web application framework
- **selenium**: Browser automation for image search
- **webdriver-manager**: Chrome driver management
- **beautifulsoup4**: HTML parsing
- **playwright**: Screenshot capture
- **python-pptx**: PowerPoint generation
- **Pillow**: Image processing

## How It Works

1. **Image Search**: Uses Selenium to perform reverse image search on Google/Bing
2. **Content Extraction**: BeautifulSoup extracts titles, descriptions, headings, and paragraphs
3. **Screenshots**: Playwright captures full-page screenshots of each website
4. **PPT Generation**: python-pptx creates a professional presentation with all data

## Notes

- The reverse image search uses free methods (no API keys required)
- Some websites may block scraping attempts
- Screenshots require Chromium browser (installed via Playwright)
- Processing time depends on the number of websites to search

## License

MIT License