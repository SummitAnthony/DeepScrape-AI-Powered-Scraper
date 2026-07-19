import inspect

import pytest

import scrape


class TestGetPageHtmlPipeline:
    def test_cache_hit_skips_network(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        scrape._cache_put("http://t.local/p", "<html>cached</html>")
        monkeypatch.setattr(scrape, "fetch_html",
                            lambda url, timeout=15: pytest.fail("network should not be called on cache hit"))
        assert scrape.get_page_html("http://t.local/p") == "<html>cached</html>"

    def test_requests_fast_path_no_browser(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        monkeypatch.setattr(scrape, "fetch_html", lambda url, timeout=15: "<html>fast</html>")
        browser_calls = []

        def fake_browser(url):
            browser_calls.append(url)
            return "<html>browser</html>"

        assert scrape.get_page_html("http://t.local/a", browser_fetcher=fake_browser) == "<html>fast</html>"
        assert browser_calls == []
        # result was cached
        assert scrape._cache_get("http://t.local/a") == "<html>fast</html>"

    def test_browser_fallback_when_requests_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        monkeypatch.setattr(scrape, "fetch_html", lambda url, timeout=15: None)
        html = scrape.get_page_html("http://t.local/b", browser_fetcher=lambda u: "<html>js</html>")
        assert html == "<html>js</html>"
        assert scrape._cache_get("http://t.local/b") == "<html>js</html>"

    def test_use_cache_false_refetches(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        scrape._cache_put("http://t.local/c", "<html>old</html>")
        monkeypatch.setattr(scrape, "fetch_html", lambda url, timeout=15: "<html>fresh</html>")
        assert scrape.get_page_html("http://t.local/c", use_cache=False) == "<html>fresh</html>"


class TestPlaywrightMigration:
    def test_default_browser_fetcher_exists(self):
        assert callable(getattr(scrape, "_browser_fetch", None))

    def test_selenium_fully_removed(self):
        src = inspect.getsource(scrape)
        assert "selenium" not in src.lower()
        assert "chromedriver" not in src.lower()
