import scrape


class TestLoadProxies:
    def test_parses_and_ignores_comments_and_blanks(self, tmp_path):
        p = tmp_path / "proxies.txt"
        p.write_text("# my proxies\nhttp://p1:8080\n\nhttp://p2:8080\n")
        assert scrape.load_proxies(str(p)) == ["http://p1:8080", "http://p2:8080"]

    def test_missing_file(self, tmp_path):
        assert scrape.load_proxies(str(tmp_path / "nope.txt")) == []


class TestProxyRotator:
    def test_rotates_in_order(self):
        r = scrape.ProxyRotator(["a", "b"])
        assert [r.next(), r.next(), r.next()] == ["a", "b", "a"]

    def test_empty_pool_returns_none(self):
        assert scrape.ProxyRotator([]).next() is None


class TestFetchTierOrder:
    def test_impersonate_tier_before_browser(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        calls = []
        monkeypatch.setattr(scrape, "fetch_html",
                            lambda url, timeout=15: calls.append("requests") or None)
        monkeypatch.setattr(scrape, "fetch_html_impersonate",
                            lambda url, proxy=None: calls.append("impersonate") or "<html>tls</html>")
        html = scrape.get_page_html("http://t.local/x",
                                    browser_fetcher=lambda u: calls.append("browser") or "<html>b</html>")
        assert html == "<html>tls</html>"
        assert calls == ["requests", "impersonate"]

    def test_browser_is_last_resort(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        calls = []
        monkeypatch.setattr(scrape, "fetch_html",
                            lambda url, timeout=15: calls.append("requests") or None)
        monkeypatch.setattr(scrape, "fetch_html_impersonate",
                            lambda url, proxy=None: calls.append("impersonate") or None)
        html = scrape.get_page_html("http://t.local/y",
                                    browser_fetcher=lambda u: calls.append("browser") or "<html>b</html>")
        assert html == "<html>b</html>"
        assert calls == ["requests", "impersonate", "browser"]

    def test_fast_path_skips_other_tiers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scrape, "CACHE_DIR", str(tmp_path))
        monkeypatch.setattr(scrape, "fetch_html", lambda url, timeout=15: "<html>fast</html>")
        monkeypatch.setattr(scrape, "fetch_html_impersonate",
                            lambda url, proxy=None: (_ for _ in ()).throw(AssertionError("should not run")))
        assert scrape.get_page_html("http://t.local/z") == "<html>fast</html>"
