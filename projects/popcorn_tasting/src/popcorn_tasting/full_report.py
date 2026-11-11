"""Combine CI, scenario, and live-judge evidence into one dashboard report."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def read_unit_test_report(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    cases = []
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        failed = failure if failure is not None else error
        cases.append({
            "name": case.get("name", "unknown"),
            "class": case.get("classname", ""),
            "duration_seconds": float(case.get("time", "0") or 0),
            "status": "failed" if failed is not None else "skipped" if skipped is not None else "passed",
            "message": (failed.get("message") or (failed.text or ""))[:1200] if failed is not None else "",
        })
    counts = {status: sum(case["status"] == status for case in cases)
              for status in ("passed", "failed", "skipped")}
    return {
        "total": len(cases),
        **counts,
        "passed_all": bool(cases) and counts["failed"] == 0,
        "cases": cases,
    }


def _first_result(report: dict[str, Any]) -> dict[str, Any]:
    results = report.get("results")
    if not isinstance(results, list) or len(results) != 1:
        raise ValueError("Each live-judge variant must contain exactly one scenario result.")
    return results[0]


def build_full_report(
    *, unit_tests: dict[str, Any], offline: dict[str, Any],
    baseline: dict[str, Any], regression: dict[str, Any], recovery: dict[str, Any],
) -> dict[str, Any]:
    """Build one report with offline cases, one live case and its three versions."""
    versions = {name: report for name, report in (
        ("baseline", baseline), ("regression", regression), ("recovery", recovery),
    )}
    results = {name: _first_result(report) for name, report in versions.items()}
    baseline_result = results["baseline"]
    regression_result = results["regression"]
    recovery_result = results["recovery"]
    regression_summary = regression_result.get("judge_summary", {})
    score_drop = regression_summary.get("score_delta")
    score_regressions = regression.get("judge_score_regressions", [])
    deterministic_regression = any(
        not check.get("passed", False)
        and (check.get("name", "").startswith("skill:") or check.get("name", "").startswith("mcp_tool:"))
        for check in regression_result.get("checks", [])
    )
    regression_detected = (
        not bool(regression.get("passed"))
        and not bool(regression_result.get("passed"))
        and deterministic_regression
        and isinstance(score_drop, (int, float))
        and any(item.get("case_id") == regression_result.get("case_id") for item in score_regressions)
    )
    checks = [
        {"name": "baseline_passes", "passed": bool(baseline.get("passed"))},
        {"name": "regression_detected_by_judge", "passed": regression_detected,
         "score_delta": score_drop},
        {"name": "recovery_passes", "passed": bool(recovery.get("passed"))},
    ]
    live_case = {
        "case_id": baseline_result["case_id"],
        "output_evaluation": "Live Sarvam response + LLM judge regression sequence",
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "turns": baseline_result.get("turns", []),
        "events": baseline_result.get("events", []),
        "invocations": baseline_result.get("invocations", []),
        "judge_summary": baseline_result.get("judge_summary", {}),
        "live_variants": {
            name: {
                "passed": bool(report.get("passed")),
                "result": results[name],
                "coverage": report.get("coverage", {}),
                "demo_variant": report.get("demo_variant", name),
            }
            for name, report in versions.items()
        },
    }
    offline_results = offline.get("results", [])
    all_results = [*offline_results, live_case]
    complete = bool(offline.get("passed")) and bool(unit_tests.get("passed_all")) and live_case["passed"]
    return {
        "report_type": "full-evaluation",
        "execution_mode": "full-evaluation",
        "dataset_version": offline.get("dataset_version"),
        "commit": offline.get("commit") or baseline.get("commit"),
        "working_tree_dirty": offline.get("working_tree_dirty", False),
        "passed": complete,
        "unit_tests": unit_tests,
        "offline_evaluation": {
            "passed": bool(offline.get("passed")),
            "case_count": len(offline_results),
            "passed_cases": sum(bool(item.get("passed")) for item in offline_results),
        },
        "live_evaluation": {
            "passed": live_case["passed"],
            "regression_score_drop": -score_drop if isinstance(score_drop, (int, float)) and score_drop < 0 else 0,
            "judge_model": baseline.get("llm_judge", {}).get("model"),
            "repetitions": baseline.get("llm_judge", {}).get("repetitions"),
            "variants": {
                name: {
                    "passed": bool(report.get("passed")),
                    "judge_summary": results[name].get("judge_summary", {}),
                    "coverage": report.get("coverage", {}),
                }
                for name, report in versions.items()
            },
        },
        "results": all_results,
        "coverage": offline.get("coverage", {}),
        "live_coverage": {name: report.get("coverage", {}) for name, report in versions.items()},
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine all Popcorn evaluation artifacts for /tests")
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--offline", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--regression", type=Path, required=True)
    parser.add_argument("--recovery", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    read_json = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = build_full_report(
        unit_tests=read_unit_test_report(args.junit),
        offline=read_json(args.offline),
        baseline=read_json(args.baseline),
        regression=read_json(args.regression),
        recovery=read_json(args.recovery),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    offline_count = report["offline_evaluation"]["case_count"]
    print(f"{'PASS' if report['passed'] else 'FAIL'} · {unit_tests_count(report)} unit tests · {offline_count} offline scenarios · 1 live-judge scenario")
    return 0 if report["passed"] else 1


def unit_tests_count(report: dict[str, Any]) -> int:
    return int(report.get("unit_tests", {}).get("total", 0))


if __name__ == "__main__":
    raise SystemExit(main())
