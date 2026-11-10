"""Build a bounded, compressed snapshot of recent evaluation runs."""

from __future__ import annotations

import argparse
import gzip
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_LIMIT = 10


def update_history(history_dir: Path, report_path: Path, *, run_id: str, run_url: str = "",
                   created_at: str | None = None) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    created_at = created_at or datetime.now(timezone.utc).isoformat()
    commit = str(report.get("commit") or "unknown")
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", run_id)
    name = f"{safe_id}-{commit[:8]}.json.gz"
    runs_dir = history_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    (runs_dir / name).write_bytes(gzip.compress(payload, mtime=0))

    index_path = history_dir / "index.json"
    old_runs = json.loads(index_path.read_text(encoding="utf-8")).get("runs", []) if index_path.exists() else []
    runs = [item for item in old_runs if item.get("id") != safe_id]
    passed = sum(bool(case.get("passed")) for case in report.get("results", []))
    runs.append({
        "id": safe_id,
        "commit": commit,
        "created_at": created_at,
        "run_url": run_url,
        "path": f"runs/{name}",
        "mode": report.get("execution_mode", "fixture"),
        "passed": bool(report.get("passed")),
        "passed_cases": passed,
        "case_count": len(report.get("results", [])),
        "coverage": report.get("coverage", {}),
    })
    runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    retained = runs[:HISTORY_LIMIT]
    keep = {item["path"] for item in retained}
    for artifact in runs_dir.glob("*.json.gz"):
        if f"runs/{artifact.name}" not in keep:
            artifact.unlink()
    index = {"schema_version": 1, "limit": HISTORY_LIMIT, "runs": retained}
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--created-at")
    args = parser.parse_args()
    index = update_history(args.history_dir, args.report, run_id=args.run_id,
                           run_url=args.run_url, created_at=args.created_at)
    print(f"Retained {len(index['runs'])} evaluation runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
