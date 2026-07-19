import base64

import vision


class TestEncodeImage:
    def test_bytes_to_base64(self):
        assert vision.encode_image_bytes(b"hello") == base64.b64encode(b"hello").decode()

    def test_roundtrip(self):
        raw = b"\x89PNG\r\n\x1a\n fake image data"
        assert base64.b64decode(vision.encode_image_bytes(raw)) == raw


class TestBuildVisionPayload:
    def test_payload_shape(self):
        payload = vision.build_vision_payload("Describe this", b"imgbytes", model="llava")
        assert payload["model"] == "llava"
        assert payload["prompt"] == "Describe this"
        assert payload["stream"] is False
        assert payload["images"] == [base64.b64encode(b"imgbytes").decode()]

    def test_default_model(self):
        payload = vision.build_vision_payload("x", b"y")
        assert payload["model"] == vision.DEFAULT_VISION_MODEL


class TestAnalyzeImage:
    def test_posts_and_returns_response(self, monkeypatch):
        captured = {}

        class FakeResp:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"response": "A blue chart."}

        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            return FakeResp()

        monkeypatch.setattr(vision.requests, "post", fake_post)
        out = vision.analyze_image(b"imgbytes", "What is this?", model="llava")
        assert out == "A blue chart."
        assert captured["url"] == vision.OLLAMA_API_URL
        assert captured["json"]["images"] == [vision.encode_image_bytes(b"imgbytes")]
        assert captured["json"]["prompt"] == "What is this?"

    def test_error_status_returns_message(self, monkeypatch):
        class FakeResp:
            status_code = 500
            text = "boom"
            def raise_for_status(self):
                raise Exception("500 error")

        monkeypatch.setattr(vision.requests, "post", lambda *a, **k: FakeResp())
        out = vision.analyze_image(b"x", "q")
        assert "Error" in out
