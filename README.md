# AI PDF Scraper & Analyzer

A powerful web application that combines web scraping with AI analysis to extract and process PDF documents from websites.

How to - https://www.youtube.com/watch?v=plZyfU9T70Q

## System Requirements

- Python 3.8 or higher
- Google Chrome version 137.0.7151.68 (64-bit)
- ChromeDriver version 137.0.7151.68
- Windows 10/11 (64-bit)

## Features

- **Fast Scraping**: Plain-requests fetching with automatic headless-Chrome fallback for JS-heavy pages
- **Deep Crawl**: Follow same-domain links up to depth 3 (respects robots.txt) to find PDFs across a whole site
- **PDF Scraping**: Automatically finds and downloads PDF files from websites
- **Concurrent Batch Download**: Download multiple PDFs in parallel with progress tracking
- **AI Analysis**: Ask anything about scraped content or downloaded PDFs (requires Ollama)
  - Streaming responses render live as they're generated
  - Large content is automatically chunked and analyzed map-reduce style
  - Pick any locally installed Ollama model from the sidebar
- **Structured Extraction**: Give a list of fields (e.g. `name, price, date`) and get a table with CSV/JSON export
- **Page Caching**: Scraped pages are cached on disk (1h TTL) so re-analysis is instant
- **Custom Download Location**: Choose where to save downloaded files

## Local Installation

### 1. Prerequisites

#### Chrome Installation
- Install Google Chrome version 137.0.7151.68 (64-bit)
- You can check your Chrome version by:
  1. Opening Chrome
  2. Clicking the three dots in the top-right corner
  3. Going to Help > About Google Chrome

#### ChromeDriver Setup
The application includes an automatic ChromeDriver downloader (`download_chromedriver.py`) that will:
- Detect your Chrome version
- Download the matching ChromeDriver version
- Install it in the correct location

### 2. Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/SummitAnthony/DeepScrape-AI-Powered-Scraper.git
cd DeepScrape-AI-Powered-Scraper
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Download and setup ChromeDriver:
```bash
python download_chromedriver.py
```

5. Install Ollama (for AI features):
- Download and install from [Ollama's website](https://ollama.ai/)
- Pull the desired model (default is "llama2"):
```bash
ollama pull llama2
```

6. Run the application:
```bash
streamlit run main.py
```

## Troubleshooting

### Chrome/ChromeDriver Version Mismatch
If you encounter version mismatch errors:
1. Check your Chrome version (Help > About Google Chrome)
2. Run `python download_chromedriver.py` to download the matching ChromeDriver version
3. Ensure ChromeDriver is in your PATH or in the project directory

### Common Issues
1. **ChromeDriver not found**: Run `python download_chromedriver.py`
2. **Version mismatch**: Make sure Chrome and ChromeDriver versions match
3. **Permission errors**: Run as administrator if needed
4. **Antivirus blocking**: Add exceptions for ChromeDriver

## Usage

1. Open the application (locally)
2. Choose your scraping mode:
   - **Scrape Website**: Extract and analyze website content
   - **Scrape for PDF**: Find and download PDF files

3. Enter a website URL and click "Start Scraping"

4. For PDF scraping:
   - Optionally set a crawl depth to also scan linked pages on the same domain
   - View the list of found PDFs
   - Choose to download all PDFs (concurrent) or individual files
   - Select your preferred download location
   - Use "Analyze Downloaded PDFs" to ask the AI about their contents

5. For website content:
   - Process the content with free-form instructions (streams live)
   - Or use "Structured Extraction" to pull specific fields into a downloadable table

## Project Structure

```
DeepScrape-AI-Powered-Scraper/
├── main.py              # Main Streamlit application
├── scrape.py            # Web scraping functionality
├── parse.py             # AI processing and analysis
├── download_chromedriver.py  # ChromeDriver downloader
├── requirements.txt     # Python dependencies
├── README.md           # Project documentation
└── .gitignore          # Git ignore file
```

## Dependencies

See `requirements.txt` for the full pinned list. Key packages: streamlit, selenium, beautifulsoup4, requests, aiohttp, PyPDF2, pymupdf, fpdf, retrying, webdriver_manager.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Ollama](https://ollama.ai/) for AI capabilities
- [Selenium](https://www.selenium.dev/) for web scraping
- [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/) for ChromeDriver
