"""
Sam-PPT: Image Search to PowerPoint Generator
A Streamlit application that performs reverse image search and creates presentations
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from image_search import search_image
from web_scraper import scrape_websites
from ppt_generator import create_presentation


# Page configuration
st.set_page_config(
    page_title="Sam-PPT | Image Search to PowerPoint",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Main styling */
    .main {
        padding: 2rem;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
    
    /* Card styling */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        border: 1px solid #e8eaed;
    }
    
    .card-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #202a44;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .status-success {
        background: #e6f4ea;
        color: #1e8e3e;
    }
    
    .status-warning {
        background: #fef7e0;
        color: #f9ab00;
    }
    
    .status-error {
        background: #fce8e6;
        color: #d93025;
    }
    
    .status-info {
        background: #e8f0fe;
        color: #1a73e8;
    }
    
    /* Result cards */
    .result-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid #1a73e8;
    }
    
    .result-title {
        font-weight: 600;
        color: #202a44;
        margin-bottom: 0.25rem;
    }
    
    .result-url {
        font-size: 0.85rem;
        color: #1a73e8;
        word-break: break-all;
    }
    
    /* Progress section */
    .progress-section {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #1a73e8 0%, #1557b0 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(26, 115, 232, 0.3);
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #34a853 0%, #1e8e3e 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 8px;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: #f8f9fa;
    }
    
    /* File uploader */
    .uploadedFile {
        border: 2px dashed #1a73e8;
        border-radius: 8px;
    }
    
    /* Info boxes */
    .info-box {
        background: #e8f0fe;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #1a73e8;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #5f6368;
        font-size: 0.9rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables"""
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'web_data' not in st.session_state:
        st.session_state.web_data = None
    if 'ppt_path' not in st.session_state:
        st.session_state.ppt_path = None
    if 'image_path' not in st.session_state:
        st.session_state.image_path = None
    if 'processing' not in st.session_state:
        st.session_state.processing = False


def render_header():
    """Render the main header"""
    st.markdown("""
    <div class="main-header">
        <h1>🔍 Sam-PPT</h1>
        <p>Transform any image into a comprehensive PowerPoint presentation with web research</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with configuration options"""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        st.markdown("---")
        
        num_results = st.slider(
            "Number of websites to find",
            min_value=1,
            max_value=10,
            value=5,
            help="Select how many top websites to include in the presentation"
        )
        
        st.markdown("---")
        st.markdown("### 📋 How it works")
        st.markdown("""
        1. **Upload** an image
        2. **Search** finds matching websites
        3. **Scrape** extracts content & screenshots
        4. **Generate** creates a PowerPoint
        5. **Download** your presentation
        """)
        
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        Sam-PPT uses reverse image search to find websites 
        containing your image, then compiles the information 
        into a professional presentation.
        """)
        
        return num_results


def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded file to temporary location"""
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, uploaded_file.name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path


def render_results(search_results: list[dict]):
    """Render search results"""
    st.markdown("### 🔗 Found Websites")
    
    for i, result in enumerate(search_results, 1):
        st.markdown(f"""
        <div class="result-card">
            <div class="result-title">{i}. {result.get('title', 'Unknown')[:80]}</div>
            <div class="result-url">{result.get('url', '')[:100]}</div>
        </div>
        """, unsafe_allow_html=True)


def render_upload_section():
    """Render the image upload section"""
    st.markdown("""
    <div class="card">
        <div class="card-title">📤 Upload Image</div>
    """, unsafe_allow_html=True)
    
    uploaded = st.file_uploader(
        "Choose an image file",
        type=['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'],
        help="Upload the image you want to search for"
    )
    
    if uploaded:
        image = Image.open(uploaded)
        st.image(image, caption="Uploaded Image", use_container_width=True)
        st.session_state.image_path = save_uploaded_file(uploaded)
    
    st.markdown("</div>", unsafe_allow_html=True)
    return uploaded


def render_generate_section(uploaded_file, num_results: int):
    """Render the generate presentation section"""
    st.markdown("""
    <div class="card">
        <div class="card-title">🚀 Generate Presentation</div>
    """, unsafe_allow_html=True)
    
    if uploaded_file:
        st.markdown(f"""
        <div class="info-box">
            <strong>Ready to process:</strong> {uploaded_file.name}<br>
            <strong>Will search for:</strong> {num_results} websites
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔍 Start Search & Generate PPT", use_container_width=True):
            st.session_state.processing = True
    else:
        st.info("👆 Please upload an image first")
    
    st.markdown("</div>", unsafe_allow_html=True)


def run_image_search(progress_bar, status_text, num_results: int) -> list[dict] | None:
    """Run image search step"""
    status_text.markdown("""
    <span class="status-badge status-info">Step 1/3</span> 
    🔍 Performing reverse image search...
    """, unsafe_allow_html=True)
    progress_bar.progress(10)
    
    search_results = search_image(st.session_state.image_path, num_results=num_results)
    
    if not search_results:
        st.warning("⚠️ No results found. Try a different image or the image might be too unique.")
        st.session_state.processing = False
        return None
    
    st.session_state.search_results = search_results
    progress_bar.progress(30)
    
    with st.expander("📋 Search Results", expanded=True):
        render_results(search_results)
    
    return search_results


def run_web_scraping(progress_bar, status_text, search_results: list[dict]) -> list:
    """Run web scraping step"""
    status_text.markdown("""
    <span class="status-badge status-info">Step 2/3</span> 
    📄 Scraping website content and taking screenshots...
    """, unsafe_allow_html=True)
    
    temp_screenshots_dir = tempfile.mkdtemp()
    
    def progress_callback(current, total, url):
        progress = 30 + int((current / total) * 40)
        progress_bar.progress(progress)
        status_text.markdown(f"""
        <span class="status-badge status-info">Step 2/3</span> 
        📄 Scraping ({current}/{total}): {url[:50]}...
        """, unsafe_allow_html=True)
    
    urls = [r['url'] for r in search_results]
    web_data = scrape_websites(urls, output_dir=temp_screenshots_dir, progress_callback=progress_callback)
    
    st.session_state.web_data = web_data
    progress_bar.progress(70)
    
    return web_data


def run_ppt_generation(progress_bar, status_text, search_results: list[dict], web_data: list) -> str:
    """Run PPT generation step"""
    status_text.markdown("""
    <span class="status-badge status-info">Step 3/3</span> 
    📊 Generating PowerPoint presentation...
    """, unsafe_allow_html=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"image_search_results_{timestamp}.pptx"
    output_path = os.path.join(tempfile.gettempdir(), output_filename)
    
    ppt_path = create_presentation(st.session_state.image_path, search_results, web_data, output_path)
    
    st.session_state.ppt_path = ppt_path
    progress_bar.progress(100)
    
    status_text.markdown("""
    <span class="status-badge status-success">✅ Complete!</span> 
    Your presentation is ready for download.
    """, unsafe_allow_html=True)
    
    return ppt_path


def process_image(num_results: int):
    """Process the uploaded image through all steps"""
    st.markdown("---")
    st.markdown("### ⏳ Processing")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        search_results = run_image_search(progress_bar, status_text, num_results)
        if not search_results:
            return
        
        web_data = run_web_scraping(progress_bar, status_text, search_results)
        run_ppt_generation(progress_bar, status_text, search_results, web_data)
        st.session_state.processing = False
        
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        st.session_state.processing = False


def render_download_section():
    """Render the download section"""
    st.markdown("---")
    st.markdown("### 📥 Download Your Presentation")
    
    _, col2, _ = st.columns([1, 2, 1])
    
    with col2:
        with open(st.session_state.ppt_path, "rb") as f:
            st.download_button(
                label="⬇️ Download PowerPoint",
                data=f,
                file_name=os.path.basename(st.session_state.ppt_path),
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True
            )
    
    if st.session_state.web_data:
        render_summary()


def render_summary():
    """Render the presentation summary"""
    with st.expander("📊 Presentation Summary"):
        st.markdown(f"""
        - **Total Slides:** {len(st.session_state.search_results) + 3}
        - **Websites Analyzed:** {len(st.session_state.search_results)}
        - **Screenshots Captured:** {sum(1 for d in st.session_state.web_data if d.screenshot_path)}
        """)
        
        st.markdown("**Included Websites:**")
        for i, (result, data) in enumerate(zip(st.session_state.search_results, st.session_state.web_data), 1):
            status = "✅" if not data.error else "⚠️"
            st.markdown(f"{i}. {status} [{result['title'][:50]}...]({result['url']})")


def main():
    """Main application function"""
    init_session_state()
    render_header()
    
    num_results = render_sidebar()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = render_upload_section()
    
    with col2:
        render_generate_section(uploaded_file, num_results)
    
    if st.session_state.processing and st.session_state.image_path:
        process_image(num_results)
    
    if st.session_state.ppt_path and os.path.exists(st.session_state.ppt_path):
        render_download_section()
    
    st.markdown("""
    <div class="footer">
        <p>Sam-PPT • Image Search to PowerPoint Generator</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
