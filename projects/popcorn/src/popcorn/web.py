"""Small web interface for the Popcorn demo agent."""

from __future__ import annotations

import json
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from popcorn.agent import answer

INDEX_FILE = Path(__file__).resolve().parent / "static" / "index.html"
MAX_REQUEST_BYTES = 8_192
MAX_QUESTION_LENGTH = 500


async def homepage(_request: Request) -> Response:
    return HTMLResponse(INDEX_FILE.read_text(encoding="utf-8"))


async def health(_request: Request) -> Response:
    return JSONResponse({"status": "ok"})


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

    reply, trace = await answer(question)
    return JSONResponse({"reply": reply, "trace": trace.to_dict()})


app = Starlette(
    debug=False,
    routes=[
        Route("/", homepage, methods=["GET"]),
        Route("/healthz", health, methods=["GET"]),
        Route("/api/chat", chat, methods=["POST"]),
    ],
)
