from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, create_tables
from app.main import app
from app.models.alert import Alert
from app.models.pipeline import Pipeline, PipelineRun

client = TestClient(app)


def _reset_db() -> None:
    create_tables()
    db = SessionLocal()
    try:
        db.query(Alert).delete()
        db.query(PipelineRun).delete()
        db.query(Pipeline).delete()
        db.commit()
    finally:
        db.close()


def test_create_alert() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        pipeline = Pipeline(name="Test Pipeline")
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)
        pipeline_id = pipeline.id
    finally:
        db.close()

    response = client.post(
        "/alerts",
        json={
            "pipeline_id": pipeline_id,
            "severity": "WARNING",
            "message": "Test alert message",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["pipeline_id"] == pipeline_id
    assert data["severity"] == "WARNING"
    assert data["message"] == "Test alert message"
    assert "id" in data
    assert "created_at" in data


def test_list_alerts_returns_empty_list_initially() -> None:
    _reset_db()

    response = client.get("/alerts")

    assert response.status_code == 200
    assert response.json() == []


def test_list_alerts_returns_alerts_in_descending_order() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        pipeline = Pipeline(name="Test Pipeline")
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)

        alert1 = Alert(
            pipeline_id=pipeline.id,
            severity="CRITICAL",
            message="First alert",
            created_at=datetime(2026, 6, 21, 8, 0, 0, tzinfo=timezone.utc),
        )
        alert2 = Alert(
            pipeline_id=pipeline.id,
            severity="WARNING",
            message="Second alert",
            created_at=datetime(2026, 6, 21, 9, 0, 0, tzinfo=timezone.utc),
        )
        db.add_all([alert1, alert2])
        db.commit()
    finally:
        db.close()

    response = client.get("/alerts")

    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 2
    assert alerts[0]["severity"] == "WARNING"
    assert alerts[1]["severity"] == "CRITICAL"


def test_list_alerts_by_pipeline_filters_correctly() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        pipeline1 = Pipeline(name="Pipeline 1")
        pipeline2 = Pipeline(name="Pipeline 2")
        db.add_all([pipeline1, pipeline2])
        db.commit()
        db.refresh(pipeline1)
        db.refresh(pipeline2)

        alert1 = Alert(pipeline_id=pipeline1.id, severity="WARNING", message="Alert 1")
        alert2 = Alert(pipeline_id=pipeline2.id, severity="CRITICAL", message="Alert 2")
        db.add_all([alert1, alert2])
        db.commit()
    finally:
        db.close()

    response = client.get(f"/alerts/{pipeline1.id}")

    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 1
    assert alerts[0]["pipeline_id"] == pipeline1.id
    assert alerts[0]["message"] == "Alert 1"


def test_create_alert_normalizes_severity() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        pipeline = Pipeline(name="Test Pipeline")
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)
        pipeline_id = pipeline.id
    finally:
        db.close()

    response = client.post(
        "/alerts",
        json={
            "pipeline_id": pipeline_id,
            "severity": "warning",  # lowercase
            "message": "Test alert",
        },
    )

    assert response.status_code == 201
    assert response.json()["severity"] == "WARNING"


def test_create_alert_rejects_invalid_severity() -> None:
    _reset_db()
    db = SessionLocal()
    try:
        pipeline = Pipeline(name="Test Pipeline")
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)
        pipeline_id = pipeline.id
    finally:
        db.close()

    response = client.post(
        "/alerts",
        json={
            "pipeline_id": pipeline_id,
            "severity": "INVALID",
            "message": "Test alert",
        },
    )

    assert response.status_code == 422
