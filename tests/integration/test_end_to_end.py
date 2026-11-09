from pathlib import Path

from popcorn_tasting.evaluate import evaluate_dataset


ROOT = Path(__file__).resolve().parents[2]


def test_popcorn_tasting_evaluates_popcorn_end_to_end():
    report = evaluate_dataset(ROOT / "projects/popcorn_tasting/data/golden/demo.json")
    assert report["passed"]
    assert report["coverage"]["skill"]["greeting"]["succeeded"] == 1
    assert report["coverage"]["skill"]["movie_fit"]["succeeded"] == 1
