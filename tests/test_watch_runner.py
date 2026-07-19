import watch
import watch_runner


class TestWatchedUrls:
    def test_returns_distinct_urls(self, tmp_path):
        db = str(tmp_path / "w.db")
        store = watch.WatchStore(db)
        store.save_snapshot("http://a", "v1")
        store.save_snapshot("http://a", "v2")
        store.save_snapshot("http://b", "v1")
        store.close()
        urls = watch_runner.watched_urls(db_path=db)
        assert sorted(urls) == ["http://a", "http://b"]

    def test_empty(self, tmp_path):
        assert watch_runner.watched_urls(db_path=str(tmp_path / "w.db")) == []


class TestRunBatch:
    def test_summarizes_changes(self, tmp_path, monkeypatch):
        db = str(tmp_path / "w.db")
        # seed two watched urls
        store = watch.WatchStore(db)
        store.save_snapshot("http://a", "old")
        store.save_snapshot("http://b", "same")
        store.close()

        results = {
            "http://a": {"first_run": False, "changed": True, "added": ["new line"], "removed": [], "previous_at": 1.0},
            "http://b": {"first_run": False, "changed": False, "added": [], "removed": [], "previous_at": 1.0},
        }
        monkeypatch.setattr(watch_runner, "check_url", lambda url, db_path=None: results[url])

        summary = watch_runner.run_batch(db_path=db)
        assert summary["checked"] == 2
        assert summary["changed"] == 1
        changed_urls = [c["url"] for c in summary["changes"]]
        assert changed_urls == ["http://a"]

    def test_handles_check_errors(self, tmp_path, monkeypatch):
        db = str(tmp_path / "w.db")
        store = watch.WatchStore(db)
        store.save_snapshot("http://a", "x")
        store.close()

        def boom(url, db_path=None):
            raise RuntimeError("network down")

        monkeypatch.setattr(watch_runner, "check_url", boom)
        summary = watch_runner.run_batch(db_path=db)
        assert summary["checked"] == 1
        assert summary["changed"] == 0
        assert summary["errors"] == 1

    def test_invokes_on_change_callback(self, tmp_path, monkeypatch):
        db = str(tmp_path / "w.db")
        store = watch.WatchStore(db)
        store.save_snapshot("http://a", "x")
        store.close()

        monkeypatch.setattr(watch_runner, "check_url",
                            lambda url, db_path=None: {"first_run": False, "changed": True,
                                                       "added": ["l"], "removed": [], "previous_at": 1.0})
        seen = []
        watch_runner.run_batch(db_path=db, on_change=lambda url, res: seen.append(url))
        assert seen == ["http://a"]
