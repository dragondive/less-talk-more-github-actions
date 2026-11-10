import json
from pathlib import Path

from popcorn_tasting.evaluate import evaluate_case, evaluate_dataset, render_html, render_markdown, score_rubric


def fake_runner(question, history):
    if "movie" in question.casefold():
        skill, tool, answer = "movie_discovery", "search_movies", "The Matrix is a science fiction action film; it could suit your taste."
    else:
        skill, tool, answer = "music_discovery", "search_musicbrainz_artists", "Radiohead is an artist returned by MusicBrainz."
    trace = {"events": [
        {"name": "skill.invoke", "parent_id": "agent", "status": "ok", "attributes": {"skill": skill}},
        {"name": "mcp.tool.call", "parent_id": "skill", "status": "ok", "attributes": {"server": "popcorn-discovery", "provider": "TMDB" if tool == "search_movies" else "MusicBrainz", "tool": tool, "arguments": {"query": question}, "response": {"fixture": True}}},
    ]}
    return answer, trace


def test_deterministic_skill_tool_coverage_and_trace_payload():
    case = {"id": "movie", "input": "movie fit", "expected_skills": ["movie_discovery"], "expected_tools": ["search_movies"], "must_include": ["Matrix"]}
    result = evaluate_case(case, fake_runner)
    assert result["passed"]
    assert result["invocations"][1]["attributes"]["arguments"] == {"query": "movie fit"}
    assert result["invocations"][1]["parent_id"] == "skill"


def test_conversation_and_cross_provider_scenario_with_sequence():
    case = {"id": "follow-up", "turns": [
        {"input": "movie: The Matrix", "expected_skills": ["movie_discovery"], "expected_tools": ["search_movies"]},
        {"input": "now find music", "expected_skills": ["music_discovery"], "expected_tools": ["search_musicbrainz_artists"], "history_contains": {"user": "The Matrix", "assistant": "science fiction"}},
    ], "expected_sequence": ["movie_discovery", "music_discovery"]}
    result = evaluate_case(case, fake_runner)
    assert result["passed"]
    assert [turn["input"] for turn in result["turns"]] == ["movie: The Matrix", "now find music"]


def test_rubric_handles_variable_outputs_and_html_shows_test_input_outcome_commit():
    rubric = {"criteria": [{"name": "mention evidence", "terms": ["science fiction"], "weight": 1}]}
    assert score_rubric("This is science fiction", rubric)["score"] == 1
    assert score_rubric("A space adventure", rubric)["score"] == 0
    path = Path(__file__).resolve().parents[1] / "data/golden/demo.json"
    report = evaluate_dataset(path, runner=fake_runner, commit="abc123")
    page = render_html(report)
    assert "abc123" in page and "Input" in page and "Outcome" in page
    assert "search_movies" in page
    summary = render_markdown(report)
    assert "Test outcomes" in summary and "Skill and MCP coverage" in summary
    assert "Deterministic checks plus variable-output rubric" in summary
    assert "abc123" in summary and "The Matrix" in summary


def test_regression_comparison_flags_previously_passing_case(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"version": "x", "cases": [{"id": "movie", "input": "movie", "expected_skills": ["missing"]}]}))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"results": [{"case_id": "movie", "passed": True}]}))
    report = evaluate_dataset(path, runner=fake_runner, baseline_path=baseline, commit="deadbeef")
    assert not report["passed"]
    assert report["regressions"] == ["movie"]
    assert report["commit"] == "deadbeef"


def test_baseline_comparison_reports_check_level_regression(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"version": "x", "cases": [{"id": "movie", "input": "movie", "expected_skills": ["missing_skill"]}]}))
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"results": [{"case_id": "movie", "passed": True, "checks": [{"name": "skill:missing_skill", "passed": True}]}]}))
    report = evaluate_dataset(path, runner=fake_runner, baseline_path=baseline)
    assert not report["passed"]
    assert report["check_regressions"] == [{"case_id": "movie", "check": "skill:missing_skill"}]


def test_existing_demo_dataset_can_be_exercised_by_runner_adapter():
    from popcorn_tasting.fake_agent import run_fake_agent

    path = Path(__file__).resolve().parents[1] / "data/golden/demo.json"
    report = evaluate_dataset(path, runner=run_fake_agent)
    assert len(report["results"]) == 3
    assert report["passed"]


def test_offline_mode_runs_real_agent_orchestration_mcp_and_provider_adapters():
    from popcorn_tasting.fake_agent import run_fake_agent

    response, trace = run_fake_agent("Tell me about the movie The Matrix", [])
    assert "Keanu Reeves" in response
    names = [event["name"] for event in trace["events"]]
    assert "llm.request" in names
    assert "llm.tool.call" in names
    assert "skill.invoke" in names
    mcp = [event for event in trace["events"] if event["name"] == "mcp.tool.call"]
    assert [event["attributes"]["tool"] for event in mcp] == ["search_movies", "get_movie_details"]
    assert all(event["attributes"]["server"] == "popcorn-discovery" for event in mcp)
    assert all("response" in event["attributes"] for event in mcp)
    assert mcp[0]["attributes"]["provider_http"][0]["query"]["query"] == ["The Matrix"]
    assert mcp[0]["attributes"]["provider_http"][0]["response"]["results"][0]["id"] == 603
    decision = next(event for event in trace["events"] if event["name"] == "llm.request")
    assert decision["attributes"]["decision"][0]["tool"] == "movie_discovery"
    assert mcp[0]["attributes"]["arguments"] == {"query": "The Matrix", "language": "en-US"}


def test_offline_dataset_runs_all_conversational_scenarios_and_reports_trace():
    from popcorn_tasting.fake_agent import run_fake_agent

    path = Path(__file__).resolve().parents[1] / "data/golden/demo.json"
    report = evaluate_dataset(path, runner=run_fake_agent, commit="feedface")
    assert report["passed"], report["results"]
    assert len(report["results"]) == 3
    assert report["commit"] == "feedface"
    assert report["coverage"]["skill"]["anime_manga_discovery"]["succeeded"] == 2
    assert "MusicBrainz" in render_html(report)
    assert "provider" in render_html(report)
