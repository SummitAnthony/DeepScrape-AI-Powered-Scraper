import os
import time

import scrape


class TestIsDownloadLink:
    def test_pdf_extension(self):
        assert scrape.is_download_link("https://x.com/files/paper.pdf")

    def test_download_php(self):
        assert scrape.is_download_link("https://x.com/download_file.php?files=a.pdf")

    def test_pdf_directory(self):
        assert scrape.is_download_link("https://x.com/pdf/2024/report")

    def test_regular_page(self):
        assert not scrape.is_download_link("https://x.com/about.html")

    def test_empty(self):
        assert not scrape.is_download_link(None)
        assert not scrape.is_download_link("")


class TestGetAbsoluteUrl:
    BASE = "https://example.com/docs/index.html"

    def test_already_absolute(self):
        assert scrape.get_absolute_url(self.BASE, "https://other.com/a.pdf") == "https://other.com/a.pdf"

    def test_root_relative(self):
        assert scrape.get_absolute_url(self.BASE, "/files/a.pdf") == "https://example.com/files/a.pdf"

    def test_protocol_relative(self):
        assert scrape.get_absolute_url(self.BASE, "//cdn.example.com/a.pdf") == "https://cdn.example.com/a.pdf"

    def test_relative(self):
        assert scrape.get_absolute_url(self.BASE, "a.pdf") == "https://example.com/docs/a.pdf"

    def test_none(self):
        assert scrape.get_absolute_url(self.BASE, None) is None


class FakeResponse:
    def __init__(self, headers=None):
        self.headers = headers or {}


class TestGetFilenameFromUrl:
    def test_content_disposition(self):
        resp = FakeResponse({"Content-Disposition": 'attachment; filename="report.pdf"'})
        assert scrape.get_filename_from_url("https://x.com/dl", resp) == "report.pdf"

    def test_from_url_path(self):
        assert scrape.get_filename_from_url("https://x.com/files/paper.pdf", FakeResponse()) == "paper.pdf"

    def test_php_query_param(self):
        url = "https://x.com/download_file.php?file=exam2024.pdf"
        assert scrape.get_filename_from_url(url, FakeResponse()) == "exam2024.pdf"

    def test_appends_pdf_extension(self):
        name = scrape.get_filename_from_url("https://x.com/files/notes", FakeResponse())
        assert name.endswith(".pdf")


class TestPageCache:
    def test_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        scrape._cache_put("http://t.local/a", "<html>hi</html>")
        assert scrape._cache_get("http://t.local/a") == "<html>hi</html>"

    def test_miss(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        assert scrape._cache_get("http://t.local/nope") is None

    def test_ttl_expiry(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        scrape._cache_put("http://t.local/old", "<html>old</html>")
        stale = time.time() - scrape.CACHE_TTL - 10
        os.utime(scrape._cache_path("http://t.local/old"), (stale, stale))
        assert scrape._cache_get("http://t.local/old") is None
