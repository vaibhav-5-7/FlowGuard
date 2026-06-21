from sqlalchemy.orm import Session

from app.models.alert import Alert

WARNING_SUCCESS_RATE_THRESHOLD = 70.0
CRITICAL_SUCCESS_RATE_THRESHOLD = 50.0

WARNING_MESSAGE = "Pipeline success rate is below 70% threshold"
CRITICAL_MESSAGE = "Pipeline success rate is below 50% threshold"


def _alert_exists(db: Session, pipeline_id: int, message: str) -> bool:
    return (
        db.query(Alert)
        .filter(Alert.pipeline_id == pipeline_id, Alert.message == message)
        .first()
        is not None
    )


def create_health_alerts(
    db: Session,
    pipeline_id: int,
    success_rate: float,
    total_runs: int,
) -> None:
    if total_runs == 0:
        return

    alerts_to_create: list[tuple[str, str]] = []
    if success_rate < WARNING_SUCCESS_RATE_THRESHOLD:
        alerts_to_create.append(("WARNING", WARNING_MESSAGE))
    if success_rate < CRITICAL_SUCCESS_RATE_THRESHOLD:
        alerts_to_create.append(("CRITICAL", CRITICAL_MESSAGE))

    created = False
    for severity, message in alerts_to_create:
        if _alert_exists(db, pipeline_id, message):
            continue
        db.add(Alert(pipeline_id=pipeline_id, severity=severity, message=message))
        created = True

    if created:
        db.commit()
