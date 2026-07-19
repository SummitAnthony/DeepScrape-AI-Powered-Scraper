import notify


class TestFormatChangeMessage:
    RESULT = {"changed": True, "added": ["new price $12", "new item"], "removed": ["old price $10"], "previous_at": 1.0}

    def test_includes_url_and_counts(self):
        msg = notify.format_change_message("https://shop.com/x", self.RESULT)
        assert "https://shop.com/x" in msg
        assert "+2" in msg
        assert "-1" in msg

    def test_includes_sample_lines(self):
        msg = notify.format_change_message("https://shop.com/x", self.RESULT)
        assert "new price $12" in msg

    def test_caps_sample_lines(self):
        result = {"changed": True, "added": [f"line{i}" for i in range(50)], "removed": [], "previous_at": 1.0}
        msg = notify.format_change_message("https://x.com", result, max_lines=5)
        assert "line0" in msg
        assert "line49" not in msg


class TestNotifyWebhook:
    def test_posts_json_payload(self, monkeypatch):
        captured = {}

        class FakeResp:
            status_code = 200
            def raise_for_status(self): pass

        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            return FakeResp()

        monkeypatch.setattr(notify.requests, "post", fake_post)
        ok = notify.notify_webhook("https://hooks.slack.com/x", "Hello change")
        assert ok is True
        assert captured["url"] == "https://hooks.slack.com/x"
        # Slack/Discord both accept a "text"/"content" style payload
        assert "Hello change" in str(captured["json"])

    def test_returns_false_on_error(self, monkeypatch):
        def boom(url, json=None, timeout=None):
            raise Exception("connection refused")

        monkeypatch.setattr(notify.requests, "post", boom)
        assert notify.notify_webhook("https://x", "msg") is False

    def test_no_webhook_url_returns_false(self):
        assert notify.notify_webhook("", "msg") is False
        assert notify.notify_webhook(None, "msg") is False


class TestLoadWebhookUrl:
    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSCRAPE_WEBHOOK_URL", "https://hooks.example.com/abc")
        assert notify.load_webhook_url() == "https://hooks.example.com/abc"

    def test_missing_env_returns_none(self, monkeypatch):
        monkeypatch.delenv("DEEPSCRAPE_WEBHOOK_URL", raising=False)
        assert notify.load_webhook_url() is None
