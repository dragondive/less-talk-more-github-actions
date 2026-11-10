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
from urllib.parse import urlsplit

from popcorn.agent import answer
from popcorn_tasting.fake_agent import run_fake_agent, run_scripted_live_agent
from popcorn_tasting.llm_judge import JudgeError, judge_response

DEFAULT_RUBRIC = {"criteria": [
    {"name": "action", "terms": ["action"], "weight": 0.4},
    {"name": "science fiction evidence", "terms": ["science fiction", "sci-fi"], "weight": 0.3},
    {"name": "calibrated wording", "terms": ["may", "might", "could"], "weight": 0.3},
]}


def _run_agent(question: str, history: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    response, trace = asyncio.run(answer(question, history=history))
    return response, trace.to_dict()


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
    return {"case_id": case["id"], "output_evaluation": "deterministic + rubric" if any("rubric" in turn for turn in turns) else "deterministic checks", "turns": turn_results, "passed": all(t["passed"] for t in turn_results) and all(c["passed"] for c in checks), "checks": checks,
            "events": all_events,
            "invocations": [{"kind": "skill" if e.get("name") == "skill.invoke" else "mcp_tool" if e.get("name") == "mcp.tool.call" else "provider_api", "name": e.get("attributes", {}).get("skill") if e.get("name") == "skill.invoke" else e.get("attributes", {}).get("tool") if e.get("name") == "mcp.tool.call" else f"{e.get('attributes', {}).get('provider')} {e.get('attributes', {}).get('method')} {urlsplit(str(e.get('attributes', {}).get('url', ''))).path or '/'}", "status": e.get("status"), "attributes": e.get("attributes", {}), "parent_id": e.get("parent_id")} for e in all_events if e.get("name") in {"skill.invoke", "mcp.tool.call", "provider.http.call"}]}


class _LiveDemoTMDB:
    """Fixed provider fixture so repeated live LLM evaluations share evidence."""

    async def search_movies(self, query: str, year: int | None = None, language: str = "en-US") -> list[dict[str, Any]]:
        if query.casefold() == "get out" and year == 2017:
            return [{"id": 419430, "title": "Get Out", "release_date": "2017-02-24",
                     "overview": "Chris visits his girlfriend's family and uncovers a disturbing secret.",
                     "vote_average": 7.6}]
        return []

    async def movie_details(self, movie_id: int, language: str = "en-US") -> dict[str, Any]:
        return {"id": movie_id, "title": "Get Out", "release_date": "2017-02-24",
                "overview": "Chris visits his girlfriend's family and uncovers a disturbing secret.",
                "runtime": 104, "genres": [{"name": "Mystery"}, {"name": "Thriller"}, {"name": "Horror"}],
                "vote_average": 7.6, "credits": {"cast": [{"name": "Daniel Kaluuya", "character": "Chris Washington"}]}}


def _fixture_provider_runner(question: str, history: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
    """Keep the MCP server and skills real while fixing external provider evidence."""
    from popcorn import mcp_server

    original = mcp_server.TMDBClient
    try:
        mcp_server.TMDBClient = _LiveDemoTMDB
        return _run_agent(question, history)
    finally:
        mcp_server.TMDBClient = original


def _demo_regression_runner(
    question: str, history: list[dict[str, str]], delegate: Callable = _run_agent,
) -> tuple[str, dict[str, Any]]:
    """Reproduce a source-grounding regression by removing available tools."""
    from popcorn import agent

    original_prompt = agent.SYSTEM_PROMPT
    original_tools = agent.LLM_TOOLS
    try:
        agent.SYSTEM_PROMPT = (
            original_prompt
            + "\nDEMO REGRESSION: The tool catalog is unavailable. Answer the user directly from memory. "
            "Do not mention that no source data was retrieved."
        )
        agent.LLM_TOOLS = []
        return delegate(question, history)
    finally:
        agent.SYSTEM_PROMPT = original_prompt
        agent.LLM_TOOLS = original_tools


def evaluate_live_judge_case(
    case: dict[str, Any], *, runner: Callable = _run_agent,
    judge: Callable = judge_response, repetitions: int = 3,
) -> dict[str, Any]:
    """Run one live conversation repeatedly and judge variable answers against evidence."""
    if repetitions < 1 or repetitions > 10:
        raise ValueError("Live judge repetitions must be between 1 and 10.")
    turns = case.get("turns") or [case]
    if len(turns) != 1:
        raise ValueError("The limited live judge demo currently supports one user turn per scenario.")
    turn = turns[0]
    rubric = turn.get("llm_judge")
    if not isinstance(rubric, dict) or not rubric.get("criteria"):
        raise ValueError(f"Case {case['id']} needs an llm_judge rubric.")
    minimum_score = float(rubric.get("minimum_score", 4.0))
    minimum_pass_rate = float(rubric.get("minimum_pass_rate", 0.67))
    attempts = []
    for attempt_number in range(1, repetitions + 1):
        response, trace = runner(turn["input"], [])
        events = _events(trace)
        checks = []
        for skill in turn.get("expected_skills", []):
            ok = any(e.get("name") == "skill.invoke" and e.get("attributes", {}).get("skill") == skill
                     and e.get("status") == "ok" for e in events)
            checks.append({"name": f"skill:{skill}", "passed": ok})
        for tool in turn.get("expected_tools", []):
            matching = [e for e in events if e.get("name") == "mcp.tool.call" and e.get("attributes", {}).get("tool") == tool]
            ok = bool(matching) and all(e.get("status") == "ok" for e in matching)
            checks.append({"name": f"mcp_tool:{tool}", "passed": ok})
        try:
            judgement = judge(question=turn["input"], response=response, trace=trace, rubric=rubric)
            judgement["passed"] = judgement["score"] >= minimum_score
            judgement["minimum_score"] = minimum_score
        except Exception as error:
            judgement = {"error": str(error)[:600], "passed": False, "minimum_score": minimum_score}
        checks.append({"name": "llm_judge_minimum", "passed": judgement.get("passed", False),
                       "score": judgement.get("score"), "minimum": minimum_score})
        attempts.append({
            "attempt_number": attempt_number,
            "input": turn["input"],
            "response": response,
            "trace": trace,
            "events": events,
            "checks": checks,
            "llm_judge": judgement,
            "passed": all(check["passed"] for check in checks),
            "invocations": [
                {"kind": "skill" if e.get("name") == "skill.invoke" else "mcp_tool" if e.get("name") == "mcp.tool.call" else "provider_api",
                 "name": e.get("attributes", {}).get("skill") if e.get("name") == "skill.invoke" else e.get("attributes", {}).get("tool") if e.get("name") == "mcp.tool.call" else f"{e.get('attributes', {}).get('provider')} {e.get('attributes', {}).get('method')} {urlsplit(str(e.get('attributes', {}).get('url', ''))).path or '/' }",
                 "status": e.get("status"), "attributes": e.get("attributes", {}), "parent_id": e.get("parent_id")}
                for e in events if e.get("name") in {"skill.invoke", "mcp.tool.call", "provider.http.call"}
            ],
        })
    passed_attempts = sum(attempt["passed"] for attempt in attempts)
    pass_rate = passed_attempts / repetitions
    valid_judgements = [attempt["llm_judge"] for attempt in attempts if isinstance(attempt["llm_judge"].get("score"), (int, float))]
    mean_score = sum(item["score"] for item in valid_judgements) / len(valid_judgements) if valid_judgements else 0.0
    criterion_scores: dict[str, list[float]] = {}
    for item in valid_judgements:
        for criterion in item.get("criteria", []):
            criterion_scores.setdefault(criterion["name"], []).append(float(criterion["score"]))
    summary = {
        "score": round(mean_score, 2),
        "attempt_pass_rate": round(pass_rate, 3),
        "judge_pass_rate": round(sum(bool(item.get("passed")) for item in valid_judgements) / repetitions, 3),
        "passed_attempts": passed_attempts,
        "repetitions": repetitions,
        "minimum_score": minimum_score,
        "minimum_pass_rate": minimum_pass_rate,
        "criteria": {name: round(sum(values) / len(values), 2) for name, values in criterion_scores.items()},
    }
    checks = []
    for check_name in sorted({check["name"] for attempt in attempts for check in attempt["checks"]}):
        check_values = [next(check["passed"] for check in attempt["checks"] if check["name"] == check_name)
                        for attempt in attempts]
        checks.append({"name": check_name, "passed": all(check_values),
                       "passed_attempts": sum(check_values), "repetitions": repetitions})
    return {
        "case_id": case["id"],
        "output_evaluation": "Sarvam live response + LLM judge",
        "judge_summary": summary,
        "turns": attempts,
        "checks": checks,
        "events": [event for attempt in attempts for event in attempt["events"]],
        "invocations": [call for attempt in attempts for call in attempt["invocations"]],
        "passed": pass_rate >= minimum_pass_rate and all(check["passed"] for check in checks if not check["name"].startswith("llm_judge_")),
    }


def evaluate_live_judge_dataset(
    path: Path, *, repetitions: int = 3, baseline_path: Path | None = None,
    commit: str | None = None, case_ids: set[str] | None = None,
    inject_regression: bool = False, fixture_provider_data: bool = False,
    runner: Callable | None = None,
    judge: Callable = judge_response,
) -> dict[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    cases = [case for case in dataset["cases"] if case_ids is None or case["id"] in case_ids]
    base_runner = runner or (_fixture_provider_runner if fixture_provider_data else _run_agent)
    selected_runner = (
        (lambda question, history: _demo_regression_runner(question, history, base_runner))
        if inject_regression else base_runner
    )
    results = [evaluate_live_judge_case(case, runner=selected_runner, judge=judge, repetitions=repetitions)
               for case in cases]
    report: dict[str, Any] = {
        "dataset_version": dataset["version"],
        "commit": commit or _commit(),
        "working_tree_dirty": _working_tree_dirty(),
        "passed": all(result["passed"] for result in results),
        "coverage": _coverage(cases, results),
        "results": results,
        "execution_mode": "live-judge",
        "llm_judge": {"provider": "Sarvam", "model": os.getenv("SARVAM_JUDGE_MODEL", "").strip() or os.getenv("SARVAM_MODEL", "sarvam-105b"),
                      "repetitions": repetitions},
        "demo_variant": "intentional-regression" if inject_regression else "normal",
        "external_provider_mode": "deterministic TMDB evidence fixture" if fixture_provider_data else "live provider APIs",
    }
    if baseline_path and baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        previous = {result["case_id"]: result for result in baseline.get("results", [])}
        score_regressions = []
        for result in results:
            old = previous.get(result["case_id"])
            if not old or not isinstance(old.get("judge_summary"), dict):
                continue
            old_score = old["judge_summary"].get("score")
            new_score = result["judge_summary"]["score"]
            if isinstance(old_score, (int, float)):
                delta = round(new_score - old_score, 2)
                result["judge_summary"]["baseline_score"] = old_score
                result["judge_summary"]["score_delta"] = delta
                threshold = float(dataset.get("minimum_regression_drop", 0.6))
                if delta <= -threshold:
                    score_regressions.append({"case_id": result["case_id"], "baseline_score": old_score,
                                              "current_score": new_score, "drop": round(-delta, 2), "threshold": threshold})
        report["judge_score_regressions"] = score_regressions
        report["passed"] &= not score_regressions
    return report


def _coverage(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    expected = Counter()
    for case in cases:
        for turn in case.get("turns") or [case]:
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
        if kind == "provider_api":
            rows.setdefault(kind, {})[name] = {
                "attempted": count, "succeeded": succeeded[kind, name],
                "failed": count - succeeded[kind, name],
            }
            continue
        if count and (kind, name) not in expected:
            rows.setdefault(kind, {})[name] = {"expected": 0, "attempted": count, "succeeded": succeeded[kind, name], "failed": count - succeeded[kind, name], "percent": 0, "unexpected": True}
    flow_counts: Counter[str] = Counter()
    flow_succeeded: Counter[str] = Counter()
    for result in results:
        events = result.get("events", [])
        by_id = {event.get("event_id"): event for event in events}
        apis_by_mcp: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            if event.get("name") == "provider.http.call":
                apis_by_mcp.setdefault(str(event.get("parent_id")), []).append(event)
        for event in events:
            if event.get("name") != "mcp.tool.call":
                continue
            parent = by_id.get(event.get("parent_id"), {})
            skill = parent.get("attributes", {}).get("skill", "unknown skill")
            tool = event.get("attributes", {}).get("tool", "unknown tool")
            api_events = apis_by_mcp.get(str(event.get("event_id")), [])
            if not api_events:
                flow = f"{skill} → {tool}"
                flow_counts[flow] += 1
                flow_succeeded[flow] += event.get("status") == "ok"
            for api in api_events:
                attrs = api.get("attributes", {})
                route = urlsplit(str(attrs.get("url", ""))).path or "/"
                flow = f"{skill} → {tool} → {attrs.get('provider')} {attrs.get('method')} {route}"
                flow_counts[flow] += 1
                flow_succeeded[flow] += api.get("status") == "ok"
    rows["flow"] = {
        name: {"attempted": count, "succeeded": flow_succeeded[name],
               "failed": count - flow_succeeded[name]}
        for name, count in sorted(flow_counts.items())
    }
    return rows


def _commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getenv("GITHUB_SHA")


def _working_tree_dirty() -> bool | None:
    try:
        return bool(subprocess.check_output(["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL).strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def evaluate_dataset(path: Path, runner: Callable = _run_agent, baseline_path: Path | None = None, commit: str | None = None, case_ids: set[str] | None = None) -> dict[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    cases = [case for case in dataset["cases"] if case_ids is None or case["id"] in case_ids]
    results = [evaluate_case(case, runner) for case in cases]
    report: dict[str, Any] = {"dataset_version": dataset["version"], "commit": commit or _commit(), "working_tree_dirty": _working_tree_dirty(), "passed": all(r["passed"] for r in results), "coverage": _coverage(cases, results), "results": results}
    if baseline_path and baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        previous = {r["case_id"]: r for r in baseline.get("results", [])}
        regressions = []
        check_regressions = []
        for result in results:
            old = previous.get(result["case_id"])
            if old and old.get("passed") and not result["passed"]:
                regressions.append(result["case_id"])
            if old:
                def flatten_checks(item: dict[str, Any]) -> dict[str, bool]:
                    checks = list(item.get("checks", []))
                    checks.extend(check for turn in item.get("turns", []) for check in turn.get("checks", []))
                    return {c.get("name"): c.get("passed") for c in checks}
                old_checks = flatten_checks(old)
                new_checks = flatten_checks(result)
                for name, passed in new_checks.items():
                    if old_checks.get(name) is True and passed is False:
                        check_regressions.append({"case_id": result["case_id"], "check": name})
        report["regressions"] = regressions
        report["check_regressions"] = check_regressions
        report["passed"] &= not regressions
        report["passed"] &= not check_regressions
    return report


def render_html(report: dict[str, Any]) -> str:
    rows = []
    for case in report["results"]:
        rendered_attempts = []
        for item in case["turns"]:
            title = f"Attempt {item['attempt_number']}" if item.get("attempt_number") else "Input"
            judge = item.get("llm_judge")
            judge_html = ""
            if judge:
                judge_html = (f"<h4>LLM judge · score {html.escape(str(judge.get('score', 'error')))}/5</h4>"
                              f"<pre>{html.escape(json.dumps(judge, indent=2))}</pre>")
            checks = "".join(f"<li>{'PASS' if check['passed'] else 'FAIL'}: {html.escape(check['name'])}</li>" for check in item["checks"])
            rendered_attempts.append(
                f"<h4>{html.escape(title)}</h4><pre>{html.escape(item['input'])}</pre>"
                f"<h4>Outcome</h4><pre>{html.escape(item['response'])}</pre>{judge_html}<ul>{checks}</ul>"
            )
        aggregate = case.get("judge_summary")
        aggregate_html = (f"<h4>Judge aggregate</h4><pre>{html.escape(json.dumps(aggregate, indent=2))}</pre>" if aggregate else "")
        details = html.escape(json.dumps(case["events"], indent=2))
        rows.append(
            f"<details><summary>{html.escape(case['case_id'])}: {'PASS' if case['passed'] else 'FAIL'} · "
            f"{html.escape(case['output_evaluation'])}</summary>{aggregate_html}{''.join(rendered_attempts)}"
            f"<h4>Execution trace (ordered; event IDs and parent IDs)</h4><pre>{details}</pre></details>"
        )
    coverage = html.escape(json.dumps(report["coverage"], indent=2))
    return (f"<!doctype html><meta charset='utf-8'><title>Popcorn Tasting</title><style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto}}"
            f"pre{{white-space:pre-wrap;background:#f3f3f3;padding:1rem}}details{{border:1px solid #ccc;padding:1rem;margin:1rem 0}}</style>"
            f"<h1>Popcorn Tasting {'PASS' if report['passed'] else 'FAIL'}</h1><p>Commit: "
            f"<code>{html.escape(str(report.get('commit') or 'unknown'))}</code> · Working tree dirty: "
            f"{html.escape(str(report.get('working_tree_dirty')))} · Dataset: {html.escape(str(report['dataset_version']))}</p>"
            f"<h2>Cases</h2>{''.join(rows)}<h2>Coverage</h2><pre>{coverage}</pre>")


def _md(value: object) -> str:
    return html.escape(str(value), quote=False).replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def render_markdown(report: dict[str, Any]) -> str:
    """Create a concise GitHub Actions job summary with outcomes and coverage."""
    passed = sum(bool(case["passed"]) for case in report["results"])
    total = len(report["results"])
    lines = [
        f"## Popcorn Tasting: {'✅ PASS' if report['passed'] else '❌ FAIL'}", "",
        f"**Commit:** `{_md(report.get('commit') or 'unknown')}` · **Working tree dirty:** `{_md(report.get('working_tree_dirty'))}` · **Dataset:** `{_md(report['dataset_version'])}` · **Cases:** {passed}/{total} passed · **Mode:** `{_md(report.get('execution_mode', 'fixture'))}`", "",
        "### Test outcomes", "", "| Test | Output evaluation | Status | Input → outcome |", "|---|---|---:|---|",
    ]
    for case in report["results"]:
        transcripts = []
        for item in case["turns"]:
            label = f"Attempt {item['attempt_number']}" if item.get("attempt_number") else "Input"
            transcript = (f"**{label}:** {_md(item['input'])}<br>**Outcome:** {_md(item['response'])}"
                          f"<br>**Checks:** {sum(bool(c['passed']) for c in item['checks'])}/{len(item['checks'])} passed")
            if item.get("llm_judge"):
                judgement = item["llm_judge"]
                transcript += f"<br>**LLM judge:** {judgement.get('score', 'error')}/5 · {_md(judgement.get('rationale', judgement.get('error', '')))}"
            transcripts.append(transcript)
        if case.get("judge_summary"):
            summary = case["judge_summary"]
            transcripts.append(f"**Judge mean:** {summary['score']}/5 · {summary['judge_pass_rate']:.0%} judged pass rate · criteria `{_md(summary['criteria'])}`")
        lines.append(f"| {_md(case['case_id'])} | {_md(case['output_evaluation'])} | {'✅ PASS' if case['passed'] else '❌ FAIL'} | {'<br>'.join(transcripts)} |")
    lines += ["", "### Skill, MCP, and provider paths", "", "| Type | Skill / tool / path | Expected | Attempted | Succeeded | Failed | Coverage / success rate |", "|---|---|---:|---:|---:|---:|---:|"]
    for kind, entries in report["coverage"].items():
        for name, counts in entries.items():
            label = {"skill": "Skill", "mcp_tool": "MCP tool", "provider_api": "Provider API", "flow": "Execution path"}.get(kind, kind)
            note = " (unexpected)" if counts.get("unexpected") else ""
            if kind in {"provider_api", "flow"}:
                expected = "—"
                rate = round(100 * counts["succeeded"] / counts["attempted"]) if counts["attempted"] else 0
                coverage = f"{rate}% success"
            else:
                expected, coverage = counts["expected"], f"{counts['percent']}%"
            lines.append(f"| {label} | {_md(name)}{note} | {expected} | {counts['attempted']} | {counts['succeeded']} | {counts['failed']} | {coverage} |")
    deterministic = sum(case["output_evaluation"] == "deterministic checks" for case in report["results"])
    rubric = sum(case["output_evaluation"] == "deterministic + rubric" for case in report["results"])
    judge_cases = sum(case["output_evaluation"] == "Sarvam live response + LLM judge" for case in report["results"])
    lines += ["", "### Output evaluation mix", "", f"- Deterministic checks: {deterministic} case(s)", f"- Deterministic checks plus variable-output rubric: {rubric} case(s)", f"- Live Sarvam answers scored by an LLM judge: {judge_cases} case(s)"]
    if "regressions" in report:
        lines += ["", "### Baseline regressions", "", "None detected." if not report["regressions"] else ", ".join(f"`{_md(case_id)}`" for case_id in report["regressions"])]
        if report.get("check_regressions"):
            lines += ["", "Check-level pass-to-fail changes:", ""]
            lines += [f"- `{_md(item['case_id'])}` · `{_md(item['check'])}`" for item in report["check_regressions"]]
    if report.get("judge_score_regressions") is not None:
        lines += ["", "### LLM judge score changes", ""]
        regressions = report["judge_score_regressions"]
        if not regressions:
            lines.append("No material score regression detected.")
        else:
            lines += [f"- `{_md(item['case_id'])}` · {item['baseline_score']}/5 → {item['current_score']}/5 (drop {item['drop']}; threshold {item['threshold']})" for item in regressions]
    return "\n".join(lines) + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run Popcorn's offline-first AI evaluation suite")
    parser.add_argument("--dataset", type=Path, default=root / "data/golden/demo.json")
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    parser.add_argument("--html", type=Path, help="Optionally write a standalone HTML report")
    parser.add_argument("--summary", type=Path, help="Write a Markdown summary (defaults to GitHub Actions job summary when available)")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--mode", choices=("fixture", "mcp", "live", "live-judge"), default="fixture", help="fixture uses fake provider HTTP; mcp uses scripted model decisions with live provider APIs; live uses the configured model and APIs; live-judge repeats live scenarios and scores them with Sarvam as judge")
    parser.add_argument("--case-ids", nargs="+", help="Run only these case IDs (useful for bounded live checks)")
    parser.add_argument("--repetitions", type=int, default=3, help="Live-judge attempts per scenario (1–10; default 3)")
    parser.add_argument("--inject-regression", action="store_true", help="Demo-only: remove the live agent's tool catalog and ask it to answer from memory")
    parser.add_argument("--fixture-provider-data", action="store_true", help="Use a fixed TMDB response while keeping the live LLM, Popcorn skill and in-process MCP server real")
    args = parser.parse_args()
    selected_case_ids = set(args.case_ids) if args.case_ids else None
    if args.mode == "live-judge":
        report = evaluate_live_judge_dataset(
            args.dataset,
            repetitions=args.repetitions,
            baseline_path=args.baseline,
            case_ids=selected_case_ids,
            inject_regression=args.inject_regression,
            fixture_provider_data=args.fixture_provider_data,
        )
    else:
        if args.inject_regression:
            parser.error("--inject-regression requires --mode live-judge")
        runner = run_fake_agent if args.mode == "fixture" else run_scripted_live_agent if args.mode == "mcp" else _run_agent
        report = evaluate_dataset(args.dataset, runner=runner, baseline_path=args.baseline, case_ids=selected_case_ids)
        report["execution_mode"] = args.mode
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_html(report), encoding="utf-8")
    summary_path = args.summary or (Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.getenv("GITHUB_STEP_SUMMARY") else None)
    if summary_path:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8") as summary_file:
            summary_file.write(render_markdown(report))
    print(f"{'PASS' if report['passed'] else 'FAIL'} · {report['commit'] or 'unknown commit'} · {len(report['results'])} cases")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
