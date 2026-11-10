"""Offline-first evaluation runner for Popcorn, with a replaceable agent adapter."""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from popcorn.agent import answer

DEFAULT_RUBRIC = {"criteria": [
    {"name": "action", "terms": ["action"], "weight": 0.4},
    {"name": "science fiction evidence", "terms": ["science fiction", "sci-fi"], "weight": 0.3},
    {"name": "calibrated wording", "terms": ["may", "might", "could"], "weight": 0.3},
]}


def _run_agent(question: str, history: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    response, trace = asyncio.run(answer(question, history=history))
    return response, trace.to_dict()


def _run_fixture(question: str, history: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    """Deterministic contract fixture for exercising the evaluator without APIs or an LLM."""
    music = "music" in question.casefold() or "radiohead" in question.casefold()
    skill, tool, provider = ("music_discovery", "search_musicbrainz_artists", "MusicBrainz") if music else ("movie_discovery", "search_movies", "TMDB")
    answer_text = ("Radiohead is an artist candidate returned by MusicBrainz; choose a match if results are ambiguous." if music
                   else "The Matrix is a science fiction film; it could suit fans of the genre.")
    events = [
        {"event_id": "fixture-skill", "parent_id": "fixture-agent", "name": "skill.invoke", "status": "ok", "attributes": {"skill": skill}},
        {"event_id": "fixture-mcp", "parent_id": "fixture-skill", "name": "mcp.tool.call", "status": "ok", "attributes": {"server": "popcorn-discovery", "provider": provider, "tool": tool, "arguments": {"query": "Radiohead" if music else "The Matrix"}, "response": {"fixture": True, "candidates": ["Radiohead"] if music else ["The Matrix"]}}},
        {"event_id": "fixture-response", "parent_id": "fixture-agent", "name": "agent.response", "status": "ok", "attributes": {"response": answer_text}},
    ]
    return answer_text, {"schema_version": "0.1", "request_id": "fixture-request", "execution_id": "fixture-execution", "events": events}


def score_rubric(response: str, rubric: dict[str, Any] = DEFAULT_RUBRIC) -> dict[str, Any]:
    checks = []
    for criterion in rubric.get("criteria", []):
        terms = criterion.get("terms", [])
        passed = any(term.casefold() in response.casefold() for term in terms)
        checks.append({"criterion": criterion["name"], "passed": passed, "weight": criterion.get("weight", 1.0)})
    total_weight = sum(item["weight"] for item in checks)
    score = sum(item["weight"] for item in checks if item["passed"])
    return {"score": round(score / total_weight, 3) if total_weight else 1.0, "checks": checks}


def _events(trace: dict[str, Any]) -> list[dict[str, Any]]:
    return trace.get("events", [])


def evaluate_case(case: dict[str, Any], runner: Callable = _run_agent) -> dict[str, Any]:
    history: list[dict[str, str]] = []
    turn_results = []
    all_events: list[dict[str, Any]] = []
    turns = case.get("turns") or [{key: value for key, value in case.items() if key in {"input", "expected_response", "expected_skills", "expected_tools", "must_include", "rubric"}}]
    for turn in turns:
        incoming_history = list(history)
        response, trace = runner(turn["input"], list(history))
        turn_events = _events(trace)
        all_events.extend(turn_events)
        result: dict[str, Any] = {"input": turn["input"], "response": response, "trace": trace, "checks": [], "passed": True}
        if "history_contains" in turn:
            ok = all(any(item["role"] == role and phrase.casefold() in item["content"].casefold() for item in incoming_history) for role, phrase in turn["history_contains"].items())
            result["checks"].append({"name": "conversation_history", "passed": ok, "expected": turn["history_contains"]})
            result["passed"] &= ok
        for skill in turn.get("expected_skills", []):
            ok = any(e.get("name") == "skill.invoke" and e.get("attributes", {}).get("skill") == skill for e in turn_events)
            result["checks"].append({"name": f"skill:{skill}", "passed": ok})
            result["passed"] &= ok
        for tool in turn.get("expected_tools", []):
            matching = [e for e in turn_events if e.get("name") == "mcp.tool.call" and e.get("attributes", {}).get("tool") == tool]
            attempted = bool(matching)
            succeeded = any(e.get("status") == "ok" for e in matching)
            for name, passed in ((f"mcp_tool_attempted:{tool}", attempted), (f"mcp_tool_succeeded:{tool}", succeeded)):
                result["checks"].append({"name": name, "passed": passed})
                result["passed"] &= passed
        if "rubric" in turn:
            rubric_spec = turn["rubric"]
            rubric_config = {"criteria": rubric_spec.get("criteria", DEFAULT_RUBRIC["criteria"])}
            scored = score_rubric(response, rubric_config)
            variants = [score_rubric(text, rubric_config) for text in rubric_spec.get("sample_responses", [])]
            scored["sample_responses"] = variants
            scored["sample_scores"] = [item["score"] for item in variants]
            scored["sample_average"] = round(sum(scored["sample_scores"] + [scored["score"]]) / (len(variants) + 1), 3)
            result["rubric"] = scored
            minimum = rubric_spec.get("minimum_score", 0)
            ok = scored["score"] >= minimum and all(item["score"] >= minimum for item in variants)
            result["checks"].append({"name": "rubric_minimum", "passed": ok, "minimum": minimum})
            result["passed"] &= ok
        if "expected_response" in turn:
            ok = response == turn["expected_response"]
            result["checks"].append({"name": "expected_response", "passed": ok})
            result["passed"] &= ok
        if "must_include" in turn:
            ok = all(term.casefold() in response.casefold() for term in turn["must_include"])
            result["checks"].append({"name": "must_include", "passed": ok, "terms": turn["must_include"]})
            result["passed"] &= ok
        turn_results.append(result)
        history.extend(({"role": "user", "content": turn["input"]}, {"role": "assistant", "content": response}))
    expected_sequence = case.get("expected_sequence")
    observed_sequence = [e.get("attributes", {}).get("skill") for e in all_events if e.get("name") == "skill.invoke"]
    checks = [{"name": "expected_skill_sequence", "passed": observed_sequence == expected_sequence, "expected": expected_sequence, "observed": observed_sequence}] if expected_sequence is not None else []
    if checks and not checks[0]["passed"]:
        turn_results[-1]["passed"] = False
    return {"case_id": case["id"], "turns": turn_results, "passed": all(t["passed"] for t in turn_results) and all(c["passed"] for c in checks), "checks": checks,
            "events": all_events,
            "invocations": [{"kind": "skill" if e.get("name") == "skill.invoke" else "mcp_tool", "name": e.get("attributes", {}).get("skill") if e.get("name") == "skill.invoke" else e.get("attributes", {}).get("tool"), "status": e.get("status"), "attributes": e.get("attributes", {}), "parent_id": e.get("parent_id")} for e in all_events if e.get("name") in {"skill.invoke", "mcp.tool.call"}]}


def _coverage(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    expected = Counter()
    for case in cases:
        for turn in case.get("turns", [{"input": case.get("input", "")} ]):
            expected.update(("skill", x) for x in turn.get("expected_skills", []))
            expected.update(("mcp_tool", x) for x in turn.get("expected_tools", []))
    observed = Counter()
    succeeded = Counter()
    for result in results:
        for call in result["invocations"]:
            key = (call["kind"], call["name"])
            observed[key] += 1
            succeeded[key] += call["status"] == "ok"
    rows = {}
    for (kind, name), count in sorted(expected.items()):
        rows.setdefault(kind, {})[name] = {"expected": count, "attempted": observed[kind, name], "succeeded": succeeded[kind, name], "failed": observed[kind, name] - succeeded[kind, name], "percent": round(100 * min(count, observed[kind, name]) / count)}
    for (kind, name), count in observed.items():
        if count and (kind, name) not in expected:
            rows.setdefault(kind, {})[name] = {"expected": 0, "attempted": count, "succeeded": succeeded[kind, name], "failed": count - succeeded[kind, name], "percent": 0, "unexpected": True}
    return rows


def _commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getenv("GITHUB_SHA")


def evaluate_dataset(path: Path, runner: Callable = _run_agent, baseline_path: Path | None = None, commit: str | None = None) -> dict[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    results = [evaluate_case(case, runner) for case in dataset["cases"]]
    report: dict[str, Any] = {"dataset_version": dataset["version"], "commit": commit or _commit(), "passed": all(r["passed"] for r in results), "coverage": _coverage(dataset["cases"], results), "results": results}
    if baseline_path and baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        previous = {r["case_id"]: r for r in baseline.get("results", [])}
        regressions = []
        for result in results:
            old = previous.get(result["case_id"])
            if old and old.get("passed") and not result["passed"]:
                regressions.append(result["case_id"])
        report["regressions"] = regressions
        report["passed"] &= not regressions
    return report


def render_html(report: dict[str, Any]) -> str:
    rows = []
    for case in report["results"]:
        turns = "".join(f"<h4>Input</h4><pre>{html.escape(t['input'])}</pre><h4>Outcome</h4><pre>{html.escape(t['response'])}</pre><ul>{''.join(f'<li>{"PASS" if check["passed"] else "FAIL"}: {html.escape(check["name"])}</li>' for check in t['checks'])}</ul>" for t in case["turns"])
        details = html.escape(json.dumps(case["invocations"], indent=2))
        rows.append(f"<details><summary>{html.escape(case['case_id'])}: {'PASS' if case['passed'] else 'FAIL'}</summary>{turns}<h4>Skill/MCP sequence</h4><pre>{details}</pre></details>")
    coverage = html.escape(json.dumps(report["coverage"], indent=2))
    return f"<!doctype html><meta charset='utf-8'><title>Popcorn Tasting</title><style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto}}pre{{white-space:pre-wrap;background:#f3f3f3;padding:1rem}}details{{border:1px solid #ccc;padding:1rem;margin:1rem 0}}</style><h1>Popcorn Tasting {'PASS' if report['passed'] else 'FAIL'}</h1><p>Commit: <code>{html.escape(str(report.get('commit') or 'unknown'))}</code> · Dataset: {html.escape(str(report['dataset_version']))}</p><h2>Cases</h2>{''.join(rows)}<h2>Coverage</h2><pre>{coverage}</pre>"


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run Popcorn's offline-first AI evaluation suite")
    parser.add_argument("--dataset", type=Path, default=root / "data/golden/demo.json")
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    parser.add_argument("--html", type=Path, default=Path("artifacts/index.html"))
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture", help="fixture runs offline; live calls the configured Popcorn agent and APIs")
    args = parser.parse_args()
    runner = _run_fixture if args.mode == "fixture" else _run_agent
    report = evaluate_dataset(args.dataset, runner=runner, baseline_path=args.baseline)
    report["execution_mode"] = args.mode
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.html.parent.mkdir(parents=True, exist_ok=True)
    args.html.write_text(render_html(report), encoding="utf-8")
    print(f"{'PASS' if report['passed'] else 'FAIL'} · {report['commit'] or 'unknown commit'} · {len(report['results'])} cases")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
