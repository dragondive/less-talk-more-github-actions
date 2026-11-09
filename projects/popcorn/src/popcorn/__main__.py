"""Run Popcorn from the command line."""

import argparse
import asyncio
import json
from pathlib import Path

from popcorn.agent import answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Popcorn demo agent")
    parser.add_argument("question", help='for example: "Hello Maya" or "Movie fit: The Matrix"')
    parser.add_argument("--trace", type=Path, help="write the execution trace as JSON")
    args = parser.parse_args()
    response, trace = asyncio.run(answer(args.question))
    print(response)
    if args.trace:
        args.trace.parent.mkdir(parents=True, exist_ok=True)
        args.trace.write_text(json.dumps(trace.to_dict(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
