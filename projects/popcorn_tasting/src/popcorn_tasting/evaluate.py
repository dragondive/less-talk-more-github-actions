"""Deterministic checks and rubric scoring for variable natural-language output."""

from __future__ import annotations

import asyncio
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from popcorn.agent import answer


@dataclass(frozen=True)
class Criterion:
    name: str
    terms: tuple[str, ...]
    weight: float


RUBRIC = (
    Criterion("action fit is discussed", ("action",), 0.4),
    Criterion("evidence from the profile is used", ("science fiction", "sci-fi"), 0.3),
    Criterion("response includes a caveat or calibrated wording", ("may", "might", "could"), 0.3),
)


def score_rubric(response: str, criteria: tuple[Criterion, ...] = RUBRIC) -> dict[str, Any]:
    """Score variable prose against simple, inspectable demo criteria."""
    lowered = response.casefold()
    checks = [
        {
            "criterion": criterion.name,
            "passed": any(term in lowered for term in criterion.terms),
            "weight": criterion.weight,
        }
        for criterion in criteria
    ]
    score = sum(item["weight"] for item in checks if item["passed"])
    return {"score": round(score, 3), "checks": checks}


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    response, trace = asyncio.run(answer(case["input"]))
    result: dict[str, Any] = {
        "case_id": case["id"],
        "response": response,
        "execution_id": trace.execution_id,
        "checks": [],
        "passed": True,
        "invocations": [
            {
                "kind": "skill" if event.name == "skill.invoke" else "mcp_tool",
                "name": event.attributes.get("skill") if event.name == "skill.invoke" else event.attributes.get("tool"),
                "status": event.status,
            }
            for event in trace.events
            if event.name in {"skill.invoke", "mcp.tool.call"}
        ],
    }
    events = trace.events
    if "expected_response" in case:
        passed = response == case["expected_response"]
        result["checks"].append({"name": "expected_response", "passed": passed})
        result["passed"] &= passed
    for skill in case.get("expected_skills", []):
        passed = any(event.name == "skill.invoke" and event.attributes.get("skill") == skill for event in events)
        result["checks"].append({"name": f"skill:{skill}", "passed": passed})
        result["passed"] &= passed
    for tool in case.get("expected_tools", []):
        attempted = any(event.name == "mcp.tool.call" and event.attributes.get("tool") == tool for event in events)
        succeeded = any(event.name == "mcp.tool.call" and event.attributes.get("tool") == tool and event.status == "ok" for event in events)
        result["checks"].append({"name": f"mcp_tool_invoked:{tool}", "passed": attempted})
        result["checks"].append({"name": f"mcp_tool_succeeded:{tool}", "passed": succeeded})
        result["passed"] &= attempted and succeeded
    if case.get("rubric"):
        rubric = score_rubric(response)
        sample_results = [
            {"response": sample, **score_rubric(sample)}
            for sample in case["rubric"].get("sample_responses", [])
        ]
        all_scores = [rubric["score"], *(sample["score"] for sample in sample_results)]
        result["rubric"] = {
            **rubric,
            "sample_responses": sample_results,
            "sample_average": round(sum(all_scores) / len(all_scores), 3),
            "sample_minimum": min(all_scores),
        }
        minimum = case["rubric"].get("minimum_score", 0.0)
        passed = all(score >= minimum for score in all_scores)
        result["checks"].append({"name": "rubric_minimum_score", "passed": passed, "minimum": minimum})
        result["passed"] &= passed
    return result


def evaluate_dataset(path: Path) -> dict[str, Any]:
    dataset = json.loads(path.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in dataset["cases"]]
    expected: dict[str, Counter[str]] = {
        "skill": Counter(skill for case in dataset["cases"] for skill in case.get("expected_skills", [])),
        "mcp_tool": Counter(tool for case in dataset["cases"] for tool in case.get("expected_tools", [])),
    }
    observed: dict[str, dict[str, Counter[str]]] = {
        kind: defaultdict(Counter) for kind in ("skill", "mcp_tool")
    }
    for result in results:
        for invocation in result["invocations"]:
            kind, name, status = invocation["kind"], invocation["name"], invocation["status"]
            if kind in observed and isinstance(name, str):
                observed[kind][name]["attempted"] += 1
                observed[kind][name]["succeeded" if status == "ok" else "failed"] += 1
    coverage: dict[str, dict[str, Any]] = {}
    for kind, entries in expected.items():
        coverage[kind] = {}
        for name, expected_count in entries.items():
            counts = observed[kind][name]
            matched = min(expected_count, counts["attempted"])
            coverage[kind][name] = {
                "expected_invocations": expected_count,
                "attempted": counts["attempted"],
                "succeeded": counts["succeeded"],
                "failed": counts["failed"],
                "expected_invocation_coverage_percent": round(100 * matched / expected_count),
            }
    return {
        "dataset_version": dataset["version"],
        "passed": all(result["passed"] for result in results),
        "coverage": coverage,
        "results": results,
    }


def render_coverage(report: dict[str, Any]) -> str:
    lines = [f"Expected invocation coverage (dataset {report['dataset_version']})"]
    for kind in ("skill", "mcp_tool"):
        lines.append(f"\n{kind.replace('_', ' ').title()}")
        for name, stats in report["coverage"][kind].items():
            lines.append(
                f"- {name}: {stats['expected_invocation_coverage_percent']}% expected invoked; "
                f"attempted={stats['attempted']} succeeded={stats['succeeded']} failed={stats['failed']}"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    import argparse

    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run Popcorn Tasting demo evaluations")
    parser.add_argument("--dataset", type=Path, default=project_root / "data/golden/demo.json")
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    parser.add_argument("--coverage-output", type=Path, default=Path("artifacts/coverage.txt"))
    args = parser.parse_args()
    report = evaluate_dataset(args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.coverage_output.parent.mkdir(parents=True, exist_ok=True)
    args.coverage_output.write_text(render_coverage(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(render_coverage(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
