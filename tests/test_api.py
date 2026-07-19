import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(api.history, "DB_PATH", str(tmp_path / "h.db"))
    return TestClient(api.app)


class TestHealth:
    def test_root(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestScrapeEndpoint:
    def test_returns_content(self, client, monkeypatch):
        monkeypatch.setattr(api, "scrape_website_content",
                            lambda url: {"title": "T", "paragraphs": ["p1", "p2"], "headings": [], "images": [], "links": []})
        r = client.post("/scrape", json={"url": "https://x.com"})
        assert r.status_code == 200
        body = r.json()
        assert body["title"] == "T"
        assert body["paragraphs"] == ["p1", "p2"]

    def test_missing_url_is_422(self, client):
        assert client.post("/scrape", json={}).status_code == 422


class TestPdfsEndpoint:
    def test_lists_pdf_links(self, client, monkeypatch):
        monkeypatch.setattr(api, "scrape_website", lambda url: ["https://x.com/a.pdf"])
        r = client.post("/pdfs", json={"url": "https://x.com"})
        assert r.status_code == 200
        assert r.json()["pdf_links"] == ["https://x.com/a.pdf"]


class TestExtractEndpoint:
    def test_returns_records(self, client, monkeypatch):
        monkeypatch.setattr(api, "scrape_website_content",
                            lambda url: {"title": "T", "paragraphs": ["Widget $10"], "headings": [], "images": [], "links": []})
        monkeypatch.setattr(api, "sync_extract_structured",
                            lambda content, fields, model=None: ([{"name": "Widget", "price": "$10"}], None))
        r = client.post("/extract", json={"url": "https://x.com", "fields": ["name", "price"]})
        assert r.status_code == 200
        assert r.json()["records"] == [{"name": "Widget", "price": "$10"}]

    def test_extraction_error_is_400(self, client, monkeypatch):
        monkeypatch.setattr(api, "scrape_website_content",
                            lambda url: {"title": "", "paragraphs": [], "headings": [], "images": [], "links": []})
        monkeypatch.setattr(api, "sync_extract_structured",
                            lambda content, fields, model=None: (None, "no data"))
        r = client.post("/extract", json={"url": "https://x.com", "fields": ["name"]})
        assert r.status_code == 400
