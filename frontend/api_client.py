from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from frontend.config import API_BASE_URL, REQUEST_TIMEOUT_SECONDS

__all__ = [
    "DashboardSummary",
    "FlowGuardAPIError",
    "FlowGuardClient",
    "PipelineHealth",
    "PipelineRun",
]


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class FlowGuardAPIError(Exception):
    """Raised when the FlowGuard API returns an error or is unreachable."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class PipelineRun:
    id: int
    pipeline_id: int
    status: str
    duration_seconds: float | None
    error_message: str | None
    run_timestamp: datetime


@dataclass(frozen=True)
class PipelineHealth:
    pipeline_id: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_duration_seconds: float
    last_run_status: str | None
    last_run_timestamp: datetime | None


@dataclass(frozen=True)
class DashboardSummary:
    total_pipelines: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_duration_seconds: float


class FlowGuardClient:
    def __init__(
        self,
        base_url: str = API_BASE_URL,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(url, timeout=self.timeout)
        except requests.ConnectionError as exc:
            raise FlowGuardAPIError(
                f"Unable to connect to FlowGuard API at {self.base_url}. "
                "Ensure the backend is running."
            ) from exc
        except requests.Timeout as exc:
            raise FlowGuardAPIError(
                f"Request to {url} timed out after {self.timeout}s."
            ) from exc
        except requests.RequestException as exc:
            raise FlowGuardAPIError(f"Request to {url} failed: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason
            raise FlowGuardAPIError(
                f"API error ({response.status_code}): {detail}",
                status_code=response.status_code,
            )

        return response.json()

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.ConnectionError as exc:
            raise FlowGuardAPIError(
                f"Unable to connect to FlowGuard API at {self.base_url}. "
                "Ensure the backend is running."
            ) from exc
        except requests.Timeout as exc:
            raise FlowGuardAPIError(
                f"Request to {url} timed out after {self.timeout}s."
            ) from exc
        except requests.RequestException as exc:
            raise FlowGuardAPIError(f"Request to {url} failed: {exc}") from exc

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason
            raise FlowGuardAPIError(
                f"API error ({response.status_code}): {detail}",
                status_code=response.status_code,
            )

        return response.json()

    def list_pipelines(self) -> list[dict[str, Any]]:
        return self._get("/pipelines")

    def create_pipeline(
        self,
        name: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        payload = {"name": name, "description": description}
        return self._post("/pipelines", payload)

    def create_pipeline_run(
        self,
        pipeline_id: int,
        status: str,
        duration_seconds: float | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "pipeline_id": pipeline_id,
            "status": status,
            "duration_seconds": duration_seconds,
            "error_message": error_message,
        }
        return self._post("/pipeline-runs", payload)

    def get_pipeline_health(self, pipeline_id: int) -> PipelineHealth:
        payload = self._get(f"/pipeline-health/{pipeline_id}")
        return PipelineHealth(
            pipeline_id=payload["pipeline_id"],
            total_runs=payload["total_runs"],
            successful_runs=payload["successful_runs"],
            failed_runs=payload["failed_runs"],
            success_rate=payload["success_rate"],
            avg_duration_seconds=payload["avg_duration_seconds"],
            last_run_status=payload.get("last_run_status"),
            last_run_timestamp=(
                _parse_timestamp(payload["last_run_timestamp"])
                if payload.get("last_run_timestamp")
                else None
            ),
        )

    def get_pipeline_failures(self) -> dict[str, int]:
        return self._get("/pipeline-failures")

    def get_pipeline_runs(self, pipeline_id: int) -> list[PipelineRun]:
        payload = self._get(f"/pipeline-runs/{pipeline_id}")
        return [
            PipelineRun(
                id=run["id"],
                pipeline_id=run["pipeline_id"],
                status=run["status"],
                duration_seconds=run.get("duration_seconds"),
                error_message=run.get("error_message"),
                run_timestamp=_parse_timestamp(run["run_timestamp"]),
            )
            for run in payload
        ]

    def fetch_dashboard_data(
        self,
    ) -> tuple[DashboardSummary, list[PipelineHealth], list[str]]:
        pipelines = self.list_pipelines()
        health_records: list[PipelineHealth] = []
        fetch_errors: list[str] = []

        for pipeline in pipelines:
            pipeline_id = pipeline["id"]
            try:
                health_records.append(self.get_pipeline_health(pipeline_id))
            except FlowGuardAPIError as exc:
                fetch_errors.append(f"Pipeline {pipeline_id}: {exc}")

        if fetch_errors and not health_records:
            raise FlowGuardAPIError(
                "Failed to load health metrics for all pipelines.\n"
                + "\n".join(fetch_errors)
            )

        summary = _build_summary(len(pipelines), health_records)
        return summary, health_records, fetch_errors


def _build_summary(
    total_pipelines: int,
    health_records: list[PipelineHealth],
) -> DashboardSummary:
    total_runs = sum(record.total_runs for record in health_records)
    successful_runs = sum(record.successful_runs for record in health_records)
    failed_runs = sum(record.failed_runs for record in health_records)

    success_rate = (
        round((successful_runs / total_runs) * 100, 2) if total_runs > 0 else 0.0
    )

    if total_runs > 0:
        weighted_duration = sum(
            record.avg_duration_seconds * record.total_runs
            for record in health_records
        )
        avg_duration_seconds = round(weighted_duration / total_runs, 2)
    else:
        avg_duration_seconds = 0.0

    return DashboardSummary(
        total_pipelines=total_pipelines,
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        avg_duration_seconds=avg_duration_seconds,
    )
