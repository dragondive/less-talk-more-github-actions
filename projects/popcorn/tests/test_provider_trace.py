import json

from popcorn.provider_trace import (
    capture_provider_requests,
    provider_http_status,
    provider_request,
    restore_provider_recorder,
)


def test_provider_http_evidence_redacts_secrets_and_bounds_responses():
    events = []
    token = capture_provider_requests(lambda *event: events.append(event))
    try:
        with provider_request("Last.fm", "GET", "https://example.test/api?artist=Example&api_key=private-key",
                             {"access_token": "private-token", "artist": "Example"}) as call:
            provider_http_status(200)
            call.response(json.dumps({"artist": "Example", "token": "private-token"}).encode())
    finally:
        restore_provider_recorder(token)

    name, attributes, status, duration = events[0]
    assert name == "provider.http.call" and status == "ok" and duration >= 0
    assert "private-key" not in attributes["url"]
    assert attributes["request"]["access_token"] == "[REDACTED]"
    assert attributes["response"]["token"] == "[REDACTED]"
    assert attributes["http_status"] == 200


def test_provider_http_failure_records_non_sensitive_diagnostic():
    events = []
    token = capture_provider_requests(lambda *event: events.append(event))
    try:
        try:
            with provider_request("TMDB", "GET", "https://api.themoviedb.org/3/search/movie"):
                raise TimeoutError("network timeout")
        except TimeoutError:
            pass
    finally:
        restore_provider_recorder(token)
    assert events[0][2] == "error"
    assert events[0][1]["error_type"] == "TimeoutError"
    assert "network timeout" not in json.dumps(events[0][1])
