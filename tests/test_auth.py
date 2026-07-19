import json

import scrape


class TestLoadAuth:
    def test_loads_cookies_and_headers(self, tmp_path):
        p = tmp_path / "cookies.json"
        p.write_text(json.dumps({
            "cookies": {"session": "abc123"},
            "headers": {"Authorization": "Bearer xyz"},
        }))
        auth = scrape.load_auth(str(p))
        assert auth["cookies"] == {"session": "abc123"}
        assert auth["headers"] == {"Authorization": "Bearer xyz"}

    def test_missing_file_returns_empty(self, tmp_path):
        auth = scrape.load_auth(str(tmp_path / "nope.json"))
        assert auth == {"cookies": {}, "headers": {}}

    def test_partial_config(self, tmp_path):
        p = tmp_path / "cookies.json"
        p.write_text(json.dumps({"cookies": {"a": "1"}}))
        auth = scrape.load_auth(str(p))
        assert auth["cookies"] == {"a": "1"}
        assert auth["headers"] == {}

    def test_malformed_json_returns_empty(self, tmp_path):
        p = tmp_path / "cookies.json"
        p.write_text("{ not valid")
        assert scrape.load_auth(str(p)) == {"cookies": {}, "headers": {}}


class TestFetchHtmlUsesAuth:
    def test_injects_cookies_and_headers(self, monkeypatch):
        captured = {}

        class FakeResp:
            headers = {"Content-Type": "text/html"}
            text = "<html>ok</html>"
            def raise_for_status(self): pass

        def fake_get(url, headers=None, timeout=None, allow_redirects=None, cookies=None):
            captured["headers"] = headers
            captured["cookies"] = cookies
            return FakeResp()

        monkeypatch.setattr(scrape.requests, "get", fake_get)
        monkeypatch.setattr(scrape, "_auth", {"cookies": {"session": "abc"}, "headers": {"X-Token": "t"}})
        scrape.fetch_html("https://x.com")
        assert captured["cookies"] == {"session": "abc"}
        assert captured["headers"]["X-Token"] == "t"

    def test_no_auth_sends_no_cookies(self, monkeypatch):
        captured = {}

        class FakeResp:
            headers = {"Content-Type": "text/html"}
            text = "<html>ok</html>"
            def raise_for_status(self): pass

        def fake_get(url, headers=None, timeout=None, allow_redirects=None, cookies=None):
            captured["cookies"] = cookies
            return FakeResp()

        monkeypatch.setattr(scrape.requests, "get", fake_get)
        monkeypatch.setattr(scrape, "_auth", {"cookies": {}, "headers": {}})
        scrape.fetch_html("https://x.com")
        assert not captured["cookies"]
