import gzip
import json

from popcorn_tasting.history import update_history


def test_history_snapshot_keeps_latest_ten_compressed_runs(tmp_path):
    report_path = tmp_path / "report.json"
    history = tmp_path / "history"
    for number in range(12):
        report_path.write_text(json.dumps({
            "commit": f"commit-{number}",
            "execution_mode": "fixture",
            "passed": number != 11,
            "coverage": {},
            "results": [{"case_id": "example", "passed": number != 11}],
        }))
        update_history(history, report_path, run_id=f"{number:02d}",
                       created_at=f"2026-11-{number + 1:02d}T00:00:00+00:00")

    index = json.loads((history / "index.json").read_text())
    assert len(index["runs"]) == 10
    assert index["runs"][0]["id"] == "11"
    assert index["runs"][-1]["id"] == "02"
    assert len(list((history / "runs").glob("*.json.gz"))) == 10
    detail = gzip.decompress((history / index["runs"][0]["path"]).read_bytes())
    assert json.loads(detail)["results"][0]["passed"] is False


def test_history_replaces_retry_of_same_workflow_run(tmp_path):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps({"commit": "abc123", "results": [], "coverage": {}}))
    history = tmp_path / "history"
    update_history(history, report_path, run_id="77", created_at="2026-11-10T00:00:00Z")
    update_history(history, report_path, run_id="77", created_at="2026-11-10T00:01:00Z")
    index = json.loads((history / "index.json").read_text())
    assert len(index["runs"]) == 1


def test_history_index_exposes_unified_suite_and_unit_test_counts(tmp_path):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps({
        "report_type": "full-evaluation",
        "execution_mode": "full-evaluation",
        "commit": "abc123",
        "passed": True,
        "coverage": {},
        "unit_tests": {"total": 101, "passed_all": True},
        "results": [{"case_id": "offline-1", "passed": True}, {"case_id": "live-1", "passed": True}],
    }))
    index = update_history(tmp_path / "history", report_path, run_id="full-1")
    entry = index["runs"][0]
    assert entry["report_type"] == "full-evaluation"
    assert entry["unit_test_count"] == 101
    assert entry["unit_test_passed"] is True
    assert entry["case_count"] == 2
