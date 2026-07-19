import watch


class TestNormalizeContent:
    def test_strips_tags_and_scripts(self):
        html = "<html><head><script>var x=1;</script><style>.a{}</style></head><body><p>Hello</p></body></html>"
        text = watch.normalize_content(html)
        assert "Hello" in text
        assert "var x" not in text
        assert ".a{}" not in text

    def test_collapses_blank_lines(self):
        text = watch.normalize_content("<p>a</p>\n\n\n<p>b</p>")
        assert text == "a\nb"

    def test_empty(self):
        assert watch.normalize_content("") == ""
        assert watch.normalize_content(None) == ""


class TestDiffTexts:
    def test_identical(self):
        d = watch.diff_texts("a\nb", "a\nb")
        assert d == {"added": [], "removed": []}

    def test_added_and_removed(self):
        d = watch.diff_texts("price: $10\nold item", "price: $12\nnew item")
        assert "price: $12" in d["added"]
        assert "price: $10" in d["removed"]
        assert "old item" in d["removed"]
        assert "new item" in d["added"]


class TestWatchStore:
    def test_roundtrip_and_latest(self, tmp_path):
        db = str(tmp_path / "w.db")
        store = watch.WatchStore(db)
        store.save_snapshot("http://a", "v1", fetched_at=100.0)
        store.save_snapshot("http://a", "v2", fetched_at=200.0)
        content, ts = store.last_snapshot("http://a")
        store.close()
        assert content == "v2"
        assert ts == 200.0

    def test_missing_url(self, tmp_path):
        store = watch.WatchStore(str(tmp_path / "w.db"))
        assert store.last_snapshot("http://nope") is None
        store.close()

    def test_persistence(self, tmp_path):
        db = str(tmp_path / "w.db")
        store = watch.WatchStore(db)
        store.save_snapshot("http://a", "kept")
        store.close()
        store2 = watch.WatchStore(db)
        assert store2.last_snapshot("http://a")[0] == "kept"
        store2.close()


class TestCheckUrl:
    def test_first_run(self, tmp_path):
        db = str(tmp_path / "w.db")
        result = watch.check_url("http://a", db_path=db, fetcher=lambda u: "<p>hello</p>")
        assert result["first_run"] is True
        assert result["changed"] is False

    def test_unchanged(self, tmp_path):
        db = str(tmp_path / "w.db")
        watch.check_url("http://a", db_path=db, fetcher=lambda u: "<p>same</p>")
        result = watch.check_url("http://a", db_path=db, fetcher=lambda u: "<p>same</p>")
        assert result["first_run"] is False
        assert result["changed"] is False

    def test_changed(self, tmp_path):
        db = str(tmp_path / "w.db")
        watch.check_url("http://a", db_path=db, fetcher=lambda u: "<p>price: $10</p>")
        result = watch.check_url("http://a", db_path=db, fetcher=lambda u: "<p>price: $12</p>")
        assert result["changed"] is True
        assert "price: $12" in result["added"]
        assert "price: $10" in result["removed"]
        assert result["previous_at"] is not None
