from pathlib import Path

from popcorn_tasting.evaluate import evaluate_dataset, score_rubric


def test_golden_dataset_checks_fixed_answer_usage_and_variable_response_rubric():
    dataset = Path(__file__).resolve().parents[1] / "data/golden/demo.json"
    report = evaluate_dataset(dataset)
    assert report["passed"]
    assert len(report["results"]) == 2
    assert report["results"][1]["rubric"]["score"] == 1.0
    assert [sample["score"] for sample in report["results"][1]["rubric"]["sample_responses"]] == [1.0, 0.7]
    assert report["results"][1]["rubric"]["sample_average"] == 0.9
    assert report["coverage"]["skill"]["greeting"]["expected_invocation_coverage_percent"] == 100
    assert report["coverage"]["mcp_tool"]["say_hello"]["succeeded"] == 1


def test_rubric_scores_variable_answers_without_exact_string_matching():
    variants = [
        "The Matrix could suit action fans. Its sci-fi story is intense.",
        "Action lovers enjoy the dark science fiction tone.",
    ]
    scores = [score_rubric(variant)["score"] for variant in variants]
    assert scores == [1.0, 0.7]
