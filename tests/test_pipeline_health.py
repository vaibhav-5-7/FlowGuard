from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, create_tables
from app.main import app
from app.models.pipeline import Pipeline, PipelineRun

client = TestClient(app)


def _reset_db() -> None:
    create_tables()
    db = SessionLocal()
    try:
        db.query(PipelineRun).delete()
        db.query(Pipeline).delete()
        db.commit()
    finally:
        db.close()


def _seed_pipeline_with_runs(db: Session) -> int:
    pipeline = Pipeline(name="ETL Job", description="Daily sync")
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    runs = [
        PipelineRun(
            pipeline_id=pipeline.id,
            status="SUCCESS",
            duration_seconds=50.0,
            run_timestamp=datetime(2026, 6, 21, 8, 0, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            duration_seconds=100.0,
            run_timestamp=datetime(2026, 6, 21, 8, 15, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="SUCCESS",
            duration_seconds=100.0,
            run_timestamp=datetime(2026, 6, 21, 8, 31, 2, tzinfo=timezone.utc),
        ),
    ]
    db.add_all(runs)
    db.commit()
    return pipeline.id


def test_get_pipeline_health_returns_metrics() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        pipeline_id = _seed_pipeline_with_runs(db)
    finally:
        db.close()

    response = client.get(f"/pipeline-health/{pipeline_id}")

    assert response.status_code == 200
    assert response.json() == {
        "pipeline_id": pipeline_id,
        "total_runs": 3,
        "successful_runs": 2,
        "failed_runs": 1,
        "success_rate": 66.67,
        "avg_duration_seconds": 83.33,
        "last_run_status": "SUCCESS",
        "last_run_timestamp": "2026-06-21T08:31:02+00:00",
    }


def test_get_pipeline_health_returns_404_for_missing_pipeline() -> None:
    _reset_db()

    response = client.get("/pipeline-health/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Pipeline not found"}


def test_get_pipeline_health_for_pipeline_with_no_runs() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        pipeline = Pipeline(name="Empty Pipeline")
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)
        pipeline_id = pipeline.id
    finally:
        db.close()

    response = client.get(f"/pipeline-health/{pipeline_id}")

    assert response.status_code == 200
    assert response.json() == {
        "pipeline_id": pipeline_id,
        "total_runs": 0,
        "successful_runs": 0,
        "failed_runs": 0,
        "success_rate": 0.0,
        "avg_duration_seconds": 0.0,
        "last_run_status": None,
        "last_run_timestamp": None,
    }
