"""FastAPI wrapper exposing the scraping pipeline programmatically.

Run with:  uvicorn api:app --reload
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import history
from scrape import scrape_website, scrape_website_content
from parse import sync_extract_structured

app = FastAPI(title="DeepScrape API", version="1.0")


class UrlRequest(BaseModel):
    url: str


class ExtractRequest(BaseModel):
    url: str
    fields: list[str]
    model: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scrape")
def scrape(req: UrlRequest):
    """Scrape a page's structured content (title, headings, paragraphs, images, links)."""
    try:
        data = scrape_website_content(req.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}")
    history.log_job(req.url, "api/scrape", len(data.get("paragraphs", [])))
    return data


@app.post("/pdfs")
def pdfs(req: UrlRequest):
    """Find downloadable document links (PDF/DOCX/XLSX/CSV) on a page."""
    try:
        links = scrape_website(req.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}")
    history.log_job(req.url, "api/pdfs", len(links))
    return {"pdf_links": links}


@app.post("/extract")
def extract(req: ExtractRequest):
    """Extract structured records (given fields) from a page's content as JSON."""
    try:
        data = scrape_website_content(req.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scrape failed: {e}")
    content = f"{data.get('title', '')}\n" + "\n".join(data.get("paragraphs", []))
    records, error = sync_extract_structured(content, req.fields, req.model)
    if error:
        raise HTTPException(status_code=400, detail=error)
    history.log_job(req.url, "api/extract", len(records))
    return {"records": records}
