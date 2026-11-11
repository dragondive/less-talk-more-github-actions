from popcorn_tasting.full_report import build_full_report, read_unit_test_report


def _variant(name, *, passed, score, score_delta=None):
    result = {
        "case_id": "live-case",
        "passed": passed,
        "judge_summary": {"score": score, "score_delta": score_delta},
        "checks": [{"name": "skill:movie_discovery", "passed": passed}],
        "turns": [],
        "events": [],
        "invocations": [],
    }
    return {
        "passed": passed,
        "commit": "abc123",
        "llm_judge": {"model": "sarvam-test", "repetitions": 3},
        "demo_variant": name,
        "results": [result],
        "coverage": {},
        "judge_score_regressions": ([{"case_id": "live-case", "threshold": 0.6}]
                                     if score_delta is not None and score_delta <= -0.6 else []),
    }


def test_junit_report_lists_unit_test_names_and_statuses(tmp_path):
    report_path = tmp_path / "junit.xml"
    report_path.write_text('''<testsuites tests="3" failures="1" errors="0" skipped="1">
      <testsuite><testcase classname="a" name="pass" time="0.1" />
      <testcase classname="b" name="fail"><failure message="assertion failed" /></testcase>
      <testcase classname="c" name="skip"><skipped /></testcase></testsuite>
    </testsuites>''')

    report = read_unit_test_report(report_path)

    assert (report["total"], report["passed"], report["failed"], report["skipped"]) == (3, 1, 1, 1)
    assert not report["passed_all"]
    assert report["cases"][1]["message"] == "assertion failed"


def test_full_report_groups_unit_offline_and_live_variants_in_one_result():
    unit = {"total": 101, "passed": 101, "failed": 0, "skipped": 0, "passed_all": True, "cases": []}
    offline = {
        "dataset_version": "98-scenarios",
        "commit": "abc123",
        "passed": True,
        "coverage": {"skill": {"movie_discovery": {"attempted": 3}}},
        "results": [{"case_id": "offline-case", "passed": True}],
    }
    baseline = _variant("normal", passed=True, score=5.0)
    regression = _variant("intentional-regression", passed=False, score=3.5, score_delta=-1.5)
    recovery = _variant("normal", passed=True, score=5.0, score_delta=1.5)

    report = build_full_report(unit_tests=unit, offline=offline, baseline=baseline,
                               regression=regression, recovery=recovery)

    assert report["passed"]
    assert report["report_type"] == "full-evaluation"
    assert [case["case_id"] for case in report["results"]] == ["offline-case", "live-case"]
    assert report["unit_tests"]["total"] == 101
    live = report["results"][1]
    assert live["passed"]
    assert all(check["passed"] for check in live["checks"])
    assert set(live["live_variants"]) == {"baseline", "regression", "recovery"}


def test_full_report_fails_when_unexpectedly_passing_regression():
    unit = {"total": 1, "passed_all": True, "cases": []}
    offline = {"passed": True, "coverage": {}, "results": []}
    baseline = _variant("normal", passed=True, score=5.0)
    regression = _variant("intentional-regression", passed=True, score=5.0, score_delta=0.0)
    recovery = _variant("normal", passed=True, score=5.0, score_delta=0.0)

    report = build_full_report(unit_tests=unit, offline=offline, baseline=baseline,
                               regression=regression, recovery=recovery)

    assert not report["passed"]
    assert not report["results"][0]["passed"]
