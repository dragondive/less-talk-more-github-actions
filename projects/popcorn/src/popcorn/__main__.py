"""Run Popcorn from the command line."""

import argparse
import asyncio
import json
from pathlib import Path

from popcorn.agent import answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Popcorn demo agent")
    parser.add_argument(
        "question",
        nargs="?",
        help='for example: "Tell me about The Matrix" or "What movies has Keanu Reeves acted in?"',
    )
    parser.add_argument("--trace", type=Path, help="write the execution trace as JSON")
    parser.add_argument("--credits", action="store_true", help="show Popcorn and TMDB attribution")
    args = parser.parse_args()
    if args.credits:
        print("This product uses the TMDB API but is not endorsed or certified by TMDB.")
        print("Movie data provided by TMDB: https://www.themoviedb.org")
        return
    if not args.question:
        parser.error("provide a question or use --credits")
    response, trace = asyncio.run(answer(args.question))
    print(response)
    if args.trace:
        args.trace.parent.mkdir(parents=True, exist_ok=True)
        args.trace.write_text(json.dumps(trace.to_dict(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
