import history


class TestHistoryStore:
    def test_log_and_list(self, tmp_path):
        db = str(tmp_path / "h.db")
        store = history.HistoryStore(db)
        store.log_job("https://a.com", "Scrape for PDF", 5, logged_at=100.0)
        store.log_job("https://b.com", "Watch Page", 0, logged_at=200.0)
        jobs = store.list_jobs()
        store.close()
        assert len(jobs) == 2
        # newest first
        assert jobs[0]["url"] == "https://b.com"
        assert jobs[0]["mode"] == "Watch Page"
        assert jobs[1]["url"] == "https://a.com"
        assert jobs[1]["items_found"] == 5

    def test_limit(self, tmp_path):
        db = str(tmp_path / "h.db")
        store = history.HistoryStore(db)
        for i in range(10):
            store.log_job(f"https://{i}.com", "Scrape Website", i, logged_at=float(i))
        jobs = store.list_jobs(limit=3)
        store.close()
        assert len(jobs) == 3
        assert jobs[0]["url"] == "https://9.com"

    def test_persistence(self, tmp_path):
        db = str(tmp_path / "h.db")
        store = history.HistoryStore(db)
        store.log_job("https://a.com", "Scrape for PDF", 1)
        store.close()
        store2 = history.HistoryStore(db)
        assert len(store2.list_jobs()) == 1
        store2.close()

    def test_empty(self, tmp_path):
        store = history.HistoryStore(str(tmp_path / "h.db"))
        assert store.list_jobs() == []
        store.close()


class TestLogJobHelper:
    def test_module_level_helper(self, tmp_path):
        db = str(tmp_path / "h.db")
        history.log_job("https://x.com", "Scrape for PDF", 3, db_path=db)
        jobs = history.list_jobs(db_path=db)
        assert len(jobs) == 1
        assert jobs[0]["items_found"] == 3
