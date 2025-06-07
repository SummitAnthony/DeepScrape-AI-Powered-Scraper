import streamlit as st
from scrape import scrape_website, download_pdf, scrape_website_content, scrape_for_pdf
from parse import sync_parse_with_deepseek as parse_with_ollama, get_ollama_status
import time
import os
import base64
from datetime import datetime
import json
from pathlib import Path
from retrying import retry
import logging
from fpdf import FPDF
import tempfile
import tkinter as tk
from tkinter import filedialog
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="AI PDF Scraper & Analyzer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container styling */
    .stApp {
        max-width: 100%;
        margin: 0;
        padding: 1rem;
        background-color: #ffffff;
    }
    
    /* Main content area */
    .main .block-container {
        max-width: 100%;
        padding: 1rem 2rem;
    }
    
    /* Header styling */
    .header {
        text-align: center;
        padding: 3rem 0;
        background: #ffffff;
        margin-bottom: 2rem;
        border-bottom: 1px solid #f0f0f0;
    }
    
    .header h1 {
        color: #1d1d1f;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    .header p {
        color: #86868b;
        font-size: 1.2rem;
        margin: 0;
        font-weight: 400;
    }
    
    /* Card styling */
    .card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        border: 1px solid #f0f0f0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }
    
    .card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    .card h3 {
        color: #1d1d1f;
        margin-bottom: 1rem;
        font-size: 1.25rem;
        font-weight: 600;
        letter-spacing: -0.3px;
    }
    
    .card p {
        color: #86868b;
        margin-bottom: 1rem;
        line-height: 1.5;
    }
    
    /* Button styling */
    .stButton button {
        width: 100%;
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        background: #0071e3;
        color: white;
        border: none;
    }
    
    .stButton button:hover {
        background: #0077ed;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 113, 227, 0.2);
    }
    
    /* Progress bar styling */
    .stProgress > div > div {
        background-color: #0071e3;
    }
    
    /* Chat message styling */
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    
    .chat-message.user {
        background-color: #f5f5f7;
    }
    
    .chat-message.assistant {
        background-color: #f0f0f0;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 500;
        color: #1d1d1f;
        font-size: 1rem;
    }
    
    /* Status messages */
    .status-success {
        color: #34c759;
        font-weight: 500;
    }
    
    .status-error {
        color: #ff3b30;
        font-weight: 500;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        padding: 2rem 0;
        color: #86868b;
        border-top: 1px solid #f0f0f0;
        margin-top: 3rem;
        width: 100%;
        font-size: 0.9rem;
    }
    
    /* Input styling */
    .stTextInput input {
        border-radius: 8px;
        border: 1px solid #d2d2d7;
        padding: 0.75rem 1rem;
    }
    
    .stTextInput input:focus {
        border-color: #0071e3;
        box-shadow: 0 0 0 2px rgba(0, 113, 227, 0.1);
    }
    
    /* Link styling */
    a {
        color: #0071e3;
        text-decoration: none;
    }
    
    a:hover {
        text-decoration: underline;
    }
    
    /* List styling */
    .card ul, .card ol {
        color: #86868b;
        padding-left: 1.2rem;
    }
    
    .card li {
        margin-bottom: 0.5rem;
        line-height: 1.5;
    }
    
    /* Responsive adjustments */
    @media (min-width: 1200px) {
        .main .block-container {
            padding: 1rem 4rem;
        }
    }
    
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        
        .header h1 {
            font-size: 2rem;
        }
        
        .header p {
            font-size: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'downloaded_pdfs' not in st.session_state:
        st.session_state.downloaded_pdfs = []
    if 'scraped_links' not in st.session_state:
        st.session_state.scraped_links = []
    if 'summary' not in st.session_state:
        st.session_state.summary = None
    if 'error' not in st.session_state:
        st.session_state.error = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = None
    if 'llm_prompt' not in st.session_state:
        st.session_state.llm_prompt = ""
    if 'ollama_status' not in st.session_state:
        st.session_state.ollama_status = get_ollama_status()
    if 'scraping_mode' not in st.session_state:
        st.session_state.scraping_mode = "Scrape Website"
    if 'current_url' not in st.session_state:
        st.session_state.current_url = ""

    # Create downloads directory if it doesn't exist
    DOWNLOAD_DIR = Path("downloads")
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    return DOWNLOAD_DIR

# Initialize session state and downloads directory
DOWNLOAD_DIR = initialize_session_state()

# Main app layout
st.markdown("""
<div class="header">
    <h1>AI Scraper & Analyzer</h1>
    <p>Extract and process web content with AI</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div class="card">
        <h3>About</h3>
        <p>Extract and analyze PDF documents from websites with AI-powered insights.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <h3>How to Use</h3>
        <ol>
            <li>Enter a website URL</li>
            <li>Click "Scrape Website"</li>
            <li>Download found PDFs</li>
            <li>Ask questions about the content</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <h3>⚠️ Prerequisites</h3>
        <p>Before using this tool, you need to:</p>
        <ol>
            <li>Install <a href="https://ollama.ai/" target="_blank">Ollama</a> on your system</li>
            <li>Pull the desired model (default is "llama2")</li>
            <li>Make sure Ollama is running locally (port 11434)</li>
        </ol>
        <p style="color: #ff3b30; font-size: 0.9rem;">Note: The AI analysis features will not work without Ollama running.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="card">
        <h3>💡 Tips</h3>
        <ul>
            <li>Use specific questions for better results</li>
            <li>For large PDFs, be patient during analysis</li>
            <li>You can change the AI model in parse.py</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

def save_content(content, filename, content_type="text"):
    """Save content to a file"""
    try:
        # Create output directory if it doesn't exist
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = output_dir / f"{filename}_{timestamp}.{content_type}"
        
        # Save content based on type
        if content_type == "pdf":
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Set font
            pdf.set_font("Arial", size=12)
            
            # Add content
            for line in content.split('\n'):
                if line.startswith('# '):
                    # Title
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(200, 10, txt=line[2:], ln=True)
                    pdf.ln(5)  # Add some space after title
                    pdf.set_font("Arial", size=12)
                elif line.startswith('## '):
                    # Heading
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(200, 10, txt=line[3:], ln=True)
                    pdf.ln(3)  # Add some space after heading
                    pdf.set_font("Arial", size=12)
                elif line.startswith('- '):
                    # List item
                    pdf.cell(10, 10, txt='•', ln=0)
                    pdf.multi_cell(0, 10, txt=line[2:])
                elif line.strip():
                    # Regular text
                    pdf.multi_cell(0, 10, txt=line)
                else:
                    # Empty line
                    pdf.ln(5)
            
            # Save PDF
            pdf.output(str(filepath))
            logger.info(f"PDF saved successfully to: {filepath}")
        elif content_type == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            logger.info(f"JSON saved successfully to: {filepath}")
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Text file saved successfully to: {filepath}")
                
        return str(filepath)
    except Exception as e:
        logger.error(f"Error saving content: {str(e)}")
        return None

def get_download_directory():
    """Open a file dialog to select download directory"""
    try:
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Make dialog appear on top
        download_dir = filedialog.askdirectory(
            title="Select Download Location",
            initialdir=os.path.expanduser("~")  # Start from user's home directory
        )
        root.destroy()
        return download_dir if download_dir else None
    except Exception as e:
        st.error(f"Error selecting download directory: {str(e)}")
        return None

def download_pdfs_with_progress(pdf_links, download_dir):
    """Download PDFs with progress tracking"""
    successful_downloads = []
    failed_downloads = []
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, link in enumerate(pdf_links):
        try:
            # Update progress
            progress = (i + 1) / len(pdf_links)
            progress_bar.progress(progress)
            status_text.text(f"Downloading PDF {i + 1} of {len(pdf_links)}")
            
            # Clean and validate the link
            if 'download_file.php' in link:
                # Extract the actual PDF URL from the download link
                try:
                    actual_url = link.split('files=')[1]
                    link = actual_url
                except:
                    pass
            
            # Download PDF
            st.write(f"Debug: Downloading from {link}")
            filepath = download_pdf(link, download_dir)
            
            if filepath:
                successful_downloads.append(filepath)
                st.write(f"Debug: Successfully downloaded to {filepath}")
            else:
                failed_downloads.append(link)
                st.write(f"Debug: Failed to download {link}")
        except Exception as e:
            logger.error(f"Error downloading {link}: {str(e)}")
            st.write(f"Debug: Error downloading {link}: {str(e)}")
            failed_downloads.append(link)
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    return successful_downloads, failed_downloads

def scraping_section():
    """Scraping section with two modes: Website and PDF"""
    st.markdown("""
    <div class="card">
        <h3>Website Scraping</h3>
        <p>Choose a scraping mode and enter a website URL to begin.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show Ollama status
    ollama_status = get_ollama_status()
    if not ollama_status["available"]:
        st.warning("⚠️ " + ollama_status["message"])
    else:
        st.success("✅ " + ollama_status["message"])
    
    # Scraping mode selection
    scraping_mode = st.radio(
        "Select Scraping Mode",
        ["Scrape Website", "Scrape for PDF"],
        horizontal=True,
        key="scraping_mode"
    )
    
    # URL input
    url = st.text_input("Enter Website URL", placeholder="https://example.com", key="current_url")
    
    if st.button("Start Scraping"):
        if not url:
            st.error("Please enter a valid URL")
            return
            
        try:
            with st.spinner("Scraping in progress..."):
                if scraping_mode == "Scrape Website":
                    data = scrape_website_content(url)
                    st.session_state.scraped_data = data
                    
                    # Display scraped content
                    st.markdown("### Scraped Content")
                    st.markdown(f"**Title:** {data['title']}")
                    
                    # Display headings
                    if data['headings']:
                        st.markdown("#### Headings")
                        for heading in data['headings']:
                            st.markdown(f"- {heading['text']}")
                    
                    # Display paragraphs
                    if data['paragraphs']:
                        st.markdown("#### Content")
                        for p in data['paragraphs']:
                            st.markdown(p)
                    
                    # Display images
                    if data['images']:
                        st.markdown("#### Images")
                        cols = st.columns(3)
                        for i, img in enumerate(data['images']):
                            with cols[i % 3]:
                                st.image(img['src'], caption=img['alt'])
                    
                else:  # Scrape for PDF
                    try:
                        with st.spinner("Searching for PDF files..."):
                            st.write("Debug: Starting PDF search...")
                            # Get all PDF links from the website
                            pdf_links = scrape_website(url)
                            
                            if pdf_links:
                                st.success(f"Found {len(pdf_links)} PDF files!")
                                
                                # Store PDF links in session state
                                st.session_state.pdf_links = pdf_links
                                
                                # Display found PDFs
                                st.markdown("### Found PDF Files")
                                for i, link in enumerate(pdf_links, 1):
                                    st.markdown(f"{i}. {link}")
                                
                                # Add download options
                                st.markdown("### Download Options")
                                
                                # Option to download all PDFs
                                if st.button("Download All PDFs", key="download_all"):
                                    try:
                                        # Get download directory from user
                                        download_dir = get_download_directory()
                                        
                                        if download_dir:
                                            # Create the directory if it doesn't exist
                                            os.makedirs(download_dir, exist_ok=True)
                                            
                                            with st.spinner("Preparing downloads..."):
                                                # Download PDFs with progress tracking
                                                successful_downloads, failed_downloads = download_pdfs_with_progress(pdf_links, download_dir)
                                                
                                                # Show results
                                                if successful_downloads:
                                                    st.success(f"Successfully downloaded {len(successful_downloads)} PDFs!")
                                                    st.markdown("#### Downloaded Files:")
                                                    for filepath in successful_downloads:
                                                        st.markdown(f"- {filepath}")
                                                
                                                if failed_downloads:
                                                    st.warning(f"Failed to download {len(failed_downloads)} PDFs:")
                                                    for link in failed_downloads:
                                                        st.markdown(f"- {link}")
                                        else:
                                            st.warning("No download location selected. Downloads cancelled.")
                                    
                                    except Exception as e:
                                        st.error(f"Error during batch download: {str(e)}")
                                        logger.error(f"Batch download error: {str(e)}")
                                
                                # Option to download individual PDFs
                                st.markdown("### Download Individual PDFs")
                                for i, link in enumerate(pdf_links, 1):
                                    col1, col2 = st.columns([3, 1])
                                    with col1:
                                        st.markdown(f"{i}. {link}")
                                    with col2:
                                        if st.button(f"Download #{i}", key=f"download_{i}"):
                                            try:
                                                # Get download directory from user
                                                download_dir = get_download_directory()
                                                
                                                if download_dir:
                                                    # Create the directory if it doesn't exist
                                                    os.makedirs(download_dir, exist_ok=True)
                                                    
                                                    with st.spinner(f"Downloading PDF #{i}..."):
                                                        # Clean and validate the link
                                                        if 'download_file.php' in link:
                                                            try:
                                                                actual_url = link.split('files=')[1]
                                                                link = actual_url
                                                            except:
                                                                pass
                                                        
                                                        st.write(f"Debug: Downloading from {link}")
                                                        filepath = download_pdf(link, download_dir)
                                                        
                                                        if filepath:
                                                            st.success(f"Downloaded successfully to: {filepath}")
                                                        else:
                                                            st.error("Download failed")
                                                else:
                                                    st.warning("No download location selected. Download cancelled.")
                                            except Exception as e:
                                                st.error(f"Error downloading PDF: {str(e)}")
                                                logger.error(f"Individual download error: {str(e)}")
                            else:
                                st.warning("No PDF files found on this page.")
                    
                    except Exception as e:
                        st.error(f"Error during PDF scraping: {str(e)}")
                        logger.error(f"PDF scraping error: {str(e)}")
                        return
        
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            return

    # Add LLM interaction section
    if st.session_state.scraped_data:
        st.markdown("### LLM Processing")
        st.markdown("Enter instructions for how you want the scraped data to be processed:")

        # Add a test button to verify LLM functionality
        if st.button("Test LLM Connection"):
            try:
                with st.spinner("Testing LLM connection..."):
                    st.write("Debug: Testing LLM connection...")
                    test_result = parse_with_ollama([], "Please respond with 'LLM is working' if you can read this message.")
                    st.write("Debug: LLM Test Response:", test_result)
                    if "LLM is working" in test_result:
                        st.success("✅ LLM is working correctly!")
                    else:
                        st.error("❌ LLM test failed. Response: " + test_result)
            except Exception as e:
                st.error(f"LLM Test Error: {str(e)}")
                st.write("Debug - Full error:", str(e))

        # Create a form for LLM processing
        with st.form(key="llm_form"):
            llm_prompt = st.text_area(
                "Processing Instructions",
                placeholder="Example: Summarize the content, organize by topics, extract key points, show in tabular format...",
                value=st.session_state.llm_prompt,
                key="llm_prompt"
            )
            
            process_button = st.form_submit_button("Process with LLM")
            
            if process_button:
                if not llm_prompt:
                    st.error("Please enter processing instructions")
                elif not ollama_status["available"]:
                    st.error(ollama_status["message"])
                else:
                    try:
                        with st.spinner("Processing with LLM..."):
                            data = st.session_state.scraped_data
                            st.write("Debug: Processing data type:", type(data))
                            
                            # Convert scraped data to text format for LLM
                            content_text = ""
                            if isinstance(data, dict):
                                # Add title if available
                                if 'title' in data:
                                    content_text += f"# {data['title']}\n\n"
                                
                                # Add headings if available
                                if 'headings' in data:
                                    content_text += "## Headings\n"
                                    for heading in data['headings']:
                                        content_text += f"- {heading['text']}\n"
                                    content_text += "\n"
                                
                                # Add paragraphs if available
                                if 'paragraphs' in data:
                                    content_text += "## Content\n"
                                    for p in data['paragraphs']:
                                        content_text += f"{p}\n\n"
                                
                                # Add sections if available
                                if 'sections' in data:
                                    for section in data['sections']:
                                        content_text += f"## {section['heading']}\n"
                                        for content in section['content']:
                                            content_text += f"{content}\n\n"
                            
                            st.write("Debug: Content length:", len(content_text))
                            
                            # Create a more specific prompt for the LLM
                            full_prompt = f"""Content to analyze:
{content_text}

User's instructions: {llm_prompt}"""

                            st.write("Debug: Sending to LLM...")
                            
                            # Process with LLM
                            result = parse_with_ollama([], full_prompt)
                            
                            if result and not result.startswith("Error:"):
                                st.markdown("### Processed Result")
                                st.markdown(result)
                            else:
                                st.error(result if result else "No result returned from LLM processing")
                    except Exception as e:
                        st.error(f"Error during LLM processing: {str(e)}")
                        logger.error(f"LLM processing error: {str(e)}")

# Add a separate section for batch downloads
if 'pdf_links' in st.session_state and st.session_state.pdf_links:
    st.markdown("### Batch Download")
    if st.button("Download All PDFs", key="batch_download"):
        try:
            # Get download directory from user
            download_dir = get_download_directory()
            
            if download_dir:
                # Create the directory if it doesn't exist
                os.makedirs(download_dir, exist_ok=True)
                
                with st.spinner("Preparing downloads..."):
                    # Download PDFs with progress tracking
                    successful_downloads, failed_downloads = download_pdfs_with_progress(st.session_state.pdf_links, download_dir)
                    
                    # Show results
                    if successful_downloads:
                        st.success(f"Successfully downloaded {len(successful_downloads)} PDFs!")
                        st.markdown("#### Downloaded Files:")
                        for filepath in successful_downloads:
                            st.markdown(f"- {filepath}")
                    
                    if failed_downloads:
                        st.warning(f"Failed to download {len(failed_downloads)} PDFs:")
                        for link in failed_downloads:
                            st.markdown(f"- {link}")
            else:
                st.warning("No download location selected. Downloads cancelled.")
        
        except Exception as e:
            st.error(f"Error during batch download: {str(e)}")
            logger.error(f"Batch download error: {str(e)}")

# Main layout
with st.container():
    scraping_section()

# Footer
st.markdown("""
<div class="footer">
    <p>Built with Streamlit and AI</p>
</div>
""", unsafe_allow_html=True)