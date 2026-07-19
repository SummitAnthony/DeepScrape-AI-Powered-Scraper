import parse


class TestRecordKey:
    def test_order_independent(self):
        a = parse._record_key({"name": "X", "price": "10"})
        b = parse._record_key({"price": "10", "name": "X"})
        assert a == b

    def test_case_and_space_insensitive(self):
        a = parse._record_key({"name": " Widget "})
        b = parse._record_key({"name": "widget"})
        assert a == b


class TestMergeCandidateRuns:
    def test_majority_vote_keeps_consistent_records(self):
        runs = [
            [{"name": "A", "price": "10"}, {"name": "B", "price": "20"}],
            [{"name": "A", "price": "10"}, {"name": "B", "price": "20"}],
            [{"name": "A", "price": "10"}],  # B missing here
        ]
        merged = parse.merge_candidate_runs(runs)
        # Both A and B appear in >= majority of runs (A:3, B:2 of 3)
        names = sorted(r["name"] for r in merged)
        assert names == ["A", "B"]

    def test_drops_low_agreement_records(self):
        runs = [
            [{"name": "A", "price": "10"}],
            [{"name": "A", "price": "10"}],
            [{"name": "Noise", "price": "99"}],  # appears once only
        ]
        merged = parse.merge_candidate_runs(runs)
        names = [r["name"] for r in merged]
        assert "A" in names
        assert "Noise" not in names

    def test_dedupes_within_result(self):
        runs = [
            [{"name": "A"}, {"name": "A"}],
            [{"name": "A"}],
        ]
        merged = parse.merge_candidate_runs(runs)
        assert len(merged) == 1

    def test_empty_runs(self):
        assert parse.merge_candidate_runs([]) == []
        assert parse.merge_candidate_runs([[], []]) == []

    def test_single_run_returns_its_records(self):
        merged = parse.merge_candidate_runs([[{"name": "A"}, {"name": "B"}]])
        names = sorted(r["name"] for r in merged)
        assert names == ["A", "B"]

    def test_preserves_field_values_from_first_occurrence(self):
        runs = [
            [{"name": "A", "price": "10"}],
            [{"name": "A", "price": "10"}],
        ]
        merged = parse.merge_candidate_runs(runs)
        assert merged[0]["price"] == "10"
