"""Small web interface for the Popcorn demo agent."""

from __future__ import annotations

import json
import gzip
import os
import re
import zlib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route
from starlette.middleware.gzip import GZipMiddleware

from popcorn.agent import answer

INDEX_FILE = Path(__file__).resolve().parent / "static" / "index.html"
TESTS_FILE = Path(__file__).resolve().parent / "static" / "tests.html"
EVAL_HISTORY_URL = os.getenv(
    "POPCORN_EVAL_HISTORY_URL",
    "https://raw.githubusercontent.com/dragondive/less-talk-more-github-actions/eval-history/",
)
MAX_REQUEST_BYTES = 40_960
MAX_QUESTION_LENGTH = 500
MAX_HISTORY_MESSAGES = 8
MAX_HISTORY_MESSAGE_LENGTH = 2_000
MAX_HISTORY_CHARS = 8_000


async def homepage(_request: Request) -> Response:
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))


async def health(_request: Request) -> Response:
    return JSONResponse({"status": "ok"})


async def tests_dashboard(_request: Request) -> Response:
    return HTMLResponse(TESTS_FILE.read_text(encoding="utf-8"))


def _fetch_history_file(path: str) -> bytes:
    with urlopen(EVAL_HISTORY_URL + path, timeout=8) as response:
        return response.read()


def test_run_index(_request: Request) -> Response:
    try:
        raw = _fetch_history_file("index.json")
        return JSONResponse(json.loads(raw))
    except (OSError, URLError, json.JSONDecodeError, TimeoutError):
        return JSONResponse({"error": "Evaluation history is not available yet."}, status_code=503)


def test_run_detail(request: Request) -> Response:
    run_id = request.path_params["run_id"]
    if not run_id.isascii() or not run_id.replace("-", "").replace("_", "").isalnum():
        return JSONResponse({"error": "Unknown evaluation run."}, status_code=404)
    try:
        raw_index = _fetch_history_file("index.json")
        index = json.loads(raw_index)
        run = next((item for item in index.get("runs", []) if item.get("id") == run_id), None)
        if run is None:
            return JSONResponse({"error": "Unknown evaluation run."}, status_code=404)
        report_path = run.get("path", "")
        if not isinstance(report_path, str) or not re.fullmatch(r"runs/[A-Za-z0-9_-]+\.json\.gz", report_path):
            return JSONResponse({"error": "Unknown evaluation run."}, status_code=404)
        compressed = _fetch_history_file(report_path)
        return JSONResponse(json.loads(gzip.decompress(compressed)))
    except (OSError, URLError, json.JSONDecodeError, gzip.BadGzipFile, zlib.error, TimeoutError, KeyError):
        return JSONResponse({"error": "Evaluation run details could not be loaded."}, status_code=503)


async def chat(request: Request) -> Response:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse({"error": "Message is too large."}, status_code=413)
        except ValueError:
            return JSONResponse({"error": "Invalid content length."}, status_code=400)

    body = await request.body()
    if len(body) > MAX_REQUEST_BYTES:
        return JSONResponse({"error": "Message is too large."}, status_code=413)
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse({"error": "Send a valid JSON request."}, status_code=400)
    if not isinstance(data, dict) or not isinstance(data.get("message"), str):
        return JSONResponse({"error": "Include a message as text."}, status_code=400)

    question = data["message"].strip()
    if not question:
        return JSONResponse({"error": "Enter a message first."}, status_code=400)
    if len(question) > MAX_QUESTION_LENGTH:
        return JSONResponse(
            {"error": f"Messages must be {MAX_QUESTION_LENGTH} characters or fewer."},
            status_code=413,
        )

    history = data.get("history", [])
    if not isinstance(history, list) or len(history) > MAX_HISTORY_MESSAGES:
        return JSONResponse({"error": "Conversation context is invalid or too long."}, status_code=400)
    normalized_history: list[dict[str, str]] = []
    history_chars = 0
    expected_role = "user"
    for item in history:
        if (not isinstance(item, dict) or item.get("role") != expected_role
                or not isinstance(item.get("content"), str)):
            return JSONResponse({"error": "Conversation context must contain alternating user and assistant messages."}, status_code=400)
        content = item["content"].strip()
        if not content or len(content) > MAX_HISTORY_MESSAGE_LENGTH:
            return JSONResponse({"error": "A conversation message is empty or too long."}, status_code=400)
        history_chars += len(content)
        if history_chars > MAX_HISTORY_CHARS:
            return JSONResponse({"error": "Conversation context is too long."}, status_code=413)
        normalized_history.append({"role": expected_role, "content": content})
        expected_role = "assistant" if expected_role == "user" else "user"
    if history and expected_role != "user":
        return JSONResponse({"error": "Conversation context must end with an assistant message."}, status_code=400)

    reply, trace = await answer(question, history=normalized_history)
    return JSONResponse({"reply": reply, "trace": trace.to_dict()})


app = Starlette(
    debug=False,
    routes=[
        Route("/", homepage, methods=["GET"]),
        Route("/tests", tests_dashboard, methods=["GET"]),
        Route("/api/tests/runs", test_run_index, methods=["GET"]),
        Route("/api/tests/runs/{run_id:str}", test_run_detail, methods=["GET"]),
        Route("/healthz", health, methods=["GET"]),
        Route("/api/chat", chat, methods=["POST"]),
    ],
)
app.add_middleware(GZipMiddleware, minimum_size=1_000)
