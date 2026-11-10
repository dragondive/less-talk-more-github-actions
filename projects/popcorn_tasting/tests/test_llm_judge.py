import asyncio
import json

import pytest

from popcorn_tasting.llm_judge import JudgeError, judge_response


RUBRIC = {"criteria": [
    {"name": "grounding", "weight": 1, "description": "Facts must be supported."},
]}


def test_judge_sends_only_response_and_mcp_evidence_as_json_task():
    captured = {}

    async def completion(messages, tools, *, model, response_format):
        captured.update(messages=messages, tools=tools, model=model, response_format=response_format)
        return {"choices": [{"message": {"content": json.dumps({
            "rationale": "The release year is sourced.",
            "criteria": [{"name": "grounding", "score": 5, "rationale": "Supported.", "evidence": "TMDB says 1999."}],
        })}}], "usage": {"prompt_tokens": 100, "completion_tokens": 20}}

    result = judge_response(
        question="When was the movie released?", response="It was released in 1999.",
        trace={"events": [{"name": "mcp.tool.call", "status": "ok", "attributes": {
            "provider": "TMDB", "tool": "get_movie_details", "response": {"year": 1999},
        }}]},
        rubric=RUBRIC,
        completion=completion,
    )

    task = json.loads(captured["messages"][1]["content"])
    assert task["mcp_evidence"][0]["result"] == {"year": 1999}
    assert task["agent_response"] == "It was released in 1999."
    assert captured["tools"] == []
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"]["strict"] is True
    assert result["score"] == 5
    assert result["usage"]["prompt_tokens"] == 100
    assert result["evidence_sources"] == [{"provider": "TMDB", "tool": "get_movie_details", "status": "ok"}]


def test_judge_rejects_missing_or_invalid_rubric_scores():
    async def completion(*_args, **_kwargs):
        return {"choices": [{"message": {"content": '{"criteria": []}'}}]}

    with pytest.raises(JudgeError, match="every rubric criterion"):
        judge_response(question="q", response="a", trace={"events": []}, rubric=RUBRIC, completion=completion)


def test_judge_rejects_scores_outside_rubric_range():
    async def completion(*_args, **_kwargs):
        return {"choices": [{"message": {"content": json.dumps({"criteria": [{
            "name": "grounding", "score": 6, "rationale": "too high", "evidence": "",
        }]})}}]}

    with pytest.raises(JudgeError, match="between 1 and 5"):
        judge_response(question="q", response="a", trace={"events": []}, rubric=RUBRIC, completion=completion)
