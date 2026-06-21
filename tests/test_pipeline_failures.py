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


def _seed_pipeline_with_failure_runs(db: Session) -> None:
    pipeline = Pipeline(name="ETL Job", description="Daily sync")
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)

    runs = [
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Source file missing",
            run_timestamp=datetime(2026, 6, 21, 8, 0, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Source file missing",
            run_timestamp=datetime(2026, 6, 21, 8, 15, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Source file missing",
            run_timestamp=datetime(2026, 6, 21, 8, 30, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Source file missing",
            run_timestamp=datetime(2026, 6, 21, 8, 45, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Source file missing",
            run_timestamp=datetime(2026, 6, 21, 9, 0, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Schema mismatch",
            run_timestamp=datetime(2026, 6, 21, 9, 15, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Schema mismatch",
            run_timestamp=datetime(2026, 6, 21, 9, 30, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Schema mismatch",
            run_timestamp=datetime(2026, 6, 21, 9, 45, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Connection timeout",
            run_timestamp=datetime(2026, 6, 21, 10, 0, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message="Connection timeout",
            run_timestamp=datetime(2026, 6, 21, 10, 15, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="SUCCESS",
            error_message=None,
            run_timestamp=datetime(2026, 6, 21, 10, 30, 0, tzinfo=timezone.utc),
        ),
        PipelineRun(
            pipeline_id=pipeline.id,
            status="FAILED",
            error_message=None,
            run_timestamp=datetime(2026, 6, 21, 10, 45, 0, tzinfo=timezone.utc),
        ),
    ]
    db.add_all(runs)
    db.commit()


def test_get_pipeline_failures_aggregates_error_messages() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        _seed_pipeline_with_failure_runs(db)
    finally:
        db.close()

    response = client.get("/pipeline-failures")

    assert response.status_code == 200
    assert response.json() == {
        "Source file missing": 5,
        "Schema mismatch": 3,
        "Connection timeout": 2,
    }


def test_get_pipeline_failures_returns_empty_dict_when_no_errors() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        pipeline = Pipeline(name="Healthy Pipeline")
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)

        db.add(
            PipelineRun(
                pipeline_id=pipeline.id,
                status="SUCCESS",
                error_message=None,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/pipeline-failures")

    assert response.status_code == 200
    assert response.json() == {}
