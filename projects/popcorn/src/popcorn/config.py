"""Small environment configuration helpers for the Popcorn demo."""

from __future__ import annotations

import os
from pathlib import Path


ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


def configured_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip().strip("\"'")
    return ""
