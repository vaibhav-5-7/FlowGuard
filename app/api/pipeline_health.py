from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.pipeline import Pipeline, PipelineRun
from app.schemas.pipeline_health import PipelineHealthResponse
from app.services.alert_service import create_health_alerts

router = APIRouter(prefix="/pipeline-health", tags=["pipeline-health"])

SUCCESS_STATUSES = frozenset({"SUCCESS", "SUCCEEDED", "OK", "COMPLETED"})
FAILED_STATUSES = frozenset({"FAILED", "FAILURE", "ERROR"})


def _normalize_status(status: str) -> str:
    return status.strip().upper()


def _is_successful(status: str) -> bool:
    return _normalize_status(status) in SUCCESS_STATUSES


def _is_failed(status: str) -> bool:
    return _normalize_status(status) in FAILED_STATUSES


def _calculate_health_metrics(
    pipeline_id: int,
    runs: list[PipelineRun],
) -> PipelineHealthResponse:
    total_runs = len(runs)
    successful_runs = sum(1 for run in runs if _is_successful(run.status))
    failed_runs = sum(1 for run in runs if _is_failed(run.status))

    success_rate = (
        round((successful_runs / total_runs) * 100, 2) if total_runs > 0 else 0.0
    )

    durations = [run.duration_seconds for run in runs if run.duration_seconds is not None]
    avg_duration_seconds = (
        round(sum(durations) / len(durations), 2) if durations else 0.0
    )

    last_run = max(runs, key=lambda run: run.run_timestamp) if runs else None

    return PipelineHealthResponse(
        pipeline_id=pipeline_id,
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        avg_duration_seconds=avg_duration_seconds,
        last_run_status=last_run.status if last_run else None,
        last_run_timestamp=last_run.run_timestamp if last_run else None,
    )


@router.get("/{pipeline_id}", response_model=PipelineHealthResponse)
def get_pipeline_health(
    pipeline_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> PipelineHealthResponse:
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    runs = (
        db.query(PipelineRun)
        .filter(PipelineRun.pipeline_id == pipeline_id)
        .order_by(PipelineRun.run_timestamp.desc())
        .all()
    )

    health = _calculate_health_metrics(pipeline_id, runs)
    create_health_alerts(
        db,
        pipeline_id=pipeline_id,
        success_rate=health.success_rate,
        total_runs=health.total_runs,
    )
    return health
