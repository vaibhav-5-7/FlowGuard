from datetime import datetime, timezone

from frontend.api_client import FlowGuardClient


class DummyResponse:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def test_get_pipeline_health_parses_last_run_timestamp(monkeypatch) -> None:
    def fake_get(url: str, timeout: int) -> DummyResponse:
        assert url == "http://flowguard.test/pipeline-health/1"
        assert timeout == 10
        return DummyResponse(
            {
                "pipeline_id": 1,
                "total_runs": 1,
                "successful_runs": 1,
                "failed_runs": 0,
                "success_rate": 100.0,
                "avg_duration_seconds": 42.0,
                "last_run_status": "SUCCESS",
                "last_run_timestamp": "2026-06-21T08:31:02+00:00",
            }
        )

    monkeypatch.setattr("frontend.api_client.requests.get", fake_get)

    health = FlowGuardClient(base_url="http://flowguard.test").get_pipeline_health(1)

    assert health.last_run_timestamp == datetime(
        2026,
        6,
        21,
        8,
        31,
        2,
        tzinfo=timezone.utc,
    )


def test_get_pipeline_health_accepts_missing_last_run_timestamp(monkeypatch) -> None:
    def fake_get(url: str, timeout: int) -> DummyResponse:
        return DummyResponse(
            {
                "pipeline_id": 1,
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "success_rate": 0.0,
                "avg_duration_seconds": 0.0,
                "last_run_status": None,
                "last_run_timestamp": None,
            }
        )

    monkeypatch.setattr("frontend.api_client.requests.get", fake_get)

    health = FlowGuardClient(base_url="http://flowguard.test").get_pipeline_health(1)

    assert health.last_run_timestamp is None
