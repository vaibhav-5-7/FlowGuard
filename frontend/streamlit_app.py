import sys
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Literal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from frontend.api_client import (
    FlowGuardAPIError,
    FlowGuardClient,
    PipelineHealth,
    PipelineRun,
)
from frontend.config import API_BASE_URL

PAGE_TITLE = "FlowGuard - Pipeline Health Monitor"

CHART_HEIGHT = 380
COLOR_SUCCESS = "#22c55e"
COLOR_FAILED = "#ef4444"
COLOR_HEALTHY = "#22c55e"
COLOR_WARNING = "#f59e0b"
COLOR_CRITICAL = "#ef4444"
COLOR_NO_DATA = "#94a3b8"
SUCCESS_STATUSES = frozenset({"SUCCESS", "SUCCEEDED", "OK", "COMPLETED"})
FAILED_STATUSES = frozenset({"FAILED", "FAILURE", "ERROR"})
SUCCESS_RATE_ALERT_THRESHOLD = 80.0
SUCCESS_RATE_WARNING_THRESHOLD = 50.0


@dataclass(frozen=True)
class PipelineAlert:
    pipeline_label: str
    alert_type: Literal["low_success_rate", "failed_last_run"]
    message: str


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remaining_seconds = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {remaining_seconds}s"
    hours, remaining_minutes = divmod(minutes, 60)
    return f"{hours}h {remaining_minutes}m"


def _format_last_status(status: str | None) -> str:
    if not status:
        return "—"

    normalized_status = status.upper()
    if normalized_status == "SUCCESS":
        return "🟢 Healthy"
    if normalized_status == "FAILED":
        return "🔴 Failed"
    return "🟡 Warning"


def _pipeline_health_status(
    total_runs: int,
    success_rate: float,
) -> Literal["no_data", "healthy", "warning", "critical"]:
    if total_runs == 0:
        return "no_data"
    if success_rate >= SUCCESS_RATE_ALERT_THRESHOLD:
        return "healthy"
    if success_rate >= SUCCESS_RATE_WARNING_THRESHOLD:
        return "warning"
    return "critical"


def _success_rate_health(total_runs: int, success_rate: float) -> str:
    status = _pipeline_health_status(total_runs, success_rate)
    if status == "no_data":
        return "⚪ No Data"
    if status == "healthy":
        return "🟢 Healthy"
    if status == "warning":
        return "🟡 Warning"
    return "🔴 Critical"


def _health_to_dataframe(health_records: list[PipelineHealth]) -> pd.DataFrame:
    rows = [
        {
            "Pipeline ID": record.pipeline_id,
            "Total Runs": record.total_runs,
            "Successful Runs": record.successful_runs,
            "Failed Runs": record.failed_runs,
            "Success Rate": (
                f"{record.success_rate:.2f}%"
                if record.total_runs > 0
                else "—"
            ),
            "Health": _success_rate_health(record.total_runs, record.success_rate),
            "Average Duration": _format_duration(record.avg_duration_seconds),
            "Last Status": _format_last_status(record.last_run_status),
        }
        for record in health_records
    ]
    return pd.DataFrame(rows)


@st.cache_data(ttl=30, show_spinner=False)
def _load_dashboard_data(
    api_base_url: str,
) -> tuple[dict, list[PipelineHealth], list[str], dict[int, str]]:
    client = FlowGuardClient(base_url=api_base_url)
    pipelines = client.list_pipelines()
    pipeline_names = {pipeline["id"]: pipeline["name"] for pipeline in pipelines}
    summary, health_records, fetch_errors = client.fetch_dashboard_data()
    return (
        {
            "total_pipelines": summary.total_pipelines,
            "total_runs": summary.total_runs,
            "successful_runs": summary.successful_runs,
            "failed_runs": summary.failed_runs,
            "success_rate": summary.success_rate,
            "avg_duration_seconds": summary.avg_duration_seconds,
        },
        health_records,
        fetch_errors,
        pipeline_names,
    )


def _pipeline_label(pipeline_id: int, pipeline_names: dict[int, str]) -> str:
    return pipeline_names.get(pipeline_id, f"Pipeline {pipeline_id}")


def _normalize_status(status: str) -> str:
    return status.strip().upper()


def _is_failed_status(status: str | None) -> bool:
    return status is not None and _normalize_status(status) in FAILED_STATUSES


def _status_style(status: str) -> str:
    normalized = _normalize_status(status)
    if normalized in SUCCESS_STATUSES:
        return f"color: {COLOR_SUCCESS}; font-weight: 600"
    if normalized in FAILED_STATUSES:
        return f"color: {COLOR_FAILED}; font-weight: 600"
    return ""


def _format_status_html(status: str | None) -> str:
    if not status:
        return "—"

    normalized = _normalize_status(status)
    if normalized in SUCCESS_STATUSES:
        color = COLOR_SUCCESS
    elif normalized in FAILED_STATUSES:
        color = COLOR_FAILED
    else:
        color = COLOR_WARNING

    return (
        f'<span style="color: {color}; font-weight: 600;">{normalized}</span>'
    )


def _format_run_timestamp(timestamp: datetime | None) -> str:
    if timestamp is None:
        return "—"
    return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")


def _runs_to_dataframe(runs: list[PipelineRun]) -> pd.DataFrame:
    rows = [
        {
            "Run ID": run.id,
            "Status": run.status,
            "Duration Seconds": (
                round(run.duration_seconds, 2)
                if run.duration_seconds is not None
                else None
            ),
            "Error Message": run.error_message or "—",
            "Run Timestamp": _format_run_timestamp(run.run_timestamp),
        }
        for run in runs
    ]
    return pd.DataFrame(rows)


@st.cache_data(ttl=30, show_spinner=False)
def _load_failure_analytics(api_base_url: str) -> dict[str, int]:
    client = FlowGuardClient(base_url=api_base_url)
    return client.get_pipeline_failures()


def _failure_reasons_to_dataframe(failures: dict[str, int]) -> pd.DataFrame:
    rows = [
        {"Error Message": error_message, "Count": count}
        for error_message, count in failures.items()
    ]
    return pd.DataFrame(rows)


def render_top_failure_reasons(failures: dict[str, int]) -> None:
    st.subheader("Top Failure Reasons")

    if not failures:
        st.info("No failure error messages recorded yet.")
        st.plotly_chart(
            _empty_chart_figure(
                "Top Failure Reasons",
                "No failure error messages recorded yet.",
            ),
            use_container_width=True,
        )
        return

    failures_df = _failure_reasons_to_dataframe(failures)
    st.dataframe(
        failures_df,
        use_container_width=True,
        hide_index=True,
    )

    error_messages = list(failures.keys())
    counts = list(failures.values())

    fig = go.Figure(
        data=[
            go.Bar(
                x=error_messages,
                y=counts,
                marker_color=COLOR_FAILED,
                text=counts,
                textposition="outside",
                hovertemplate="%{x}<br>Count: %{y}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Top Failure Reasons",
        xaxis_title="Error Message",
        yaxis_title="Count",
        height=CHART_HEIGHT,
        showlegend=False,
        margin={"t": 50, "b": 40, "l": 40, "r": 20},
        yaxis={"rangemode": "tozero"},
    )
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data(ttl=30, show_spinner=False)
def _load_pipeline_details(
    api_base_url: str,
    pipeline_id: int,
) -> tuple[PipelineHealth, list[PipelineRun]]:
    client = FlowGuardClient(base_url=api_base_url)
    health = client.get_pipeline_health(pipeline_id)
    runs = client.get_pipeline_runs(pipeline_id)
    return health, runs


def render_pipeline_details(
    pipeline_names: dict[int, str],
) -> None:
    st.subheader("Pipeline Details")

    if not pipeline_names:
        st.info("No pipelines available. Create a pipeline to view run history.")
        return

    pipeline_ids = sorted(pipeline_names.keys())
    selected_pipeline_id = st.selectbox(
        "Select Pipeline",
        options=pipeline_ids,
        format_func=lambda pipeline_id: _pipeline_label(
            pipeline_id,
            pipeline_names,
        ),
        key="pipeline_details_selector",
    )

    try:
        health, runs = _load_pipeline_details(API_BASE_URL, selected_pipeline_id)
    except FlowGuardAPIError as exc:
        st.error(f"Unable to load pipeline details: {exc}")
        return

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Pipeline ID", health.pipeline_id)
    col2.metric("Total Runs", health.total_runs)
    col3.metric(
        "Success Rate",
        f"{health.success_rate:.2f}%" if health.total_runs > 0 else "—",
    )
    col4.metric(
        "Average Duration",
        _format_duration(health.avg_duration_seconds),
    )
    with col5:
        st.markdown("**Last Status**")
        st.markdown(
            _format_status_html(health.last_run_status),
            unsafe_allow_html=True,
        )

    st.markdown("#### Run History")

    if not runs:
        st.info("No runs recorded for this pipeline yet.")
        return

    runs_df = _runs_to_dataframe(runs)
    styled_runs_df = runs_df.style.map(_status_style, subset=["Status"])
    st.dataframe(
        styled_runs_df,
        use_container_width=True,
        hide_index=True,
    )


def _build_pipeline_alerts(
    health_records: list[PipelineHealth],
    pipeline_names: dict[int, str],
) -> list[PipelineAlert]:
    alerts: list[PipelineAlert] = []

    for record in sorted(health_records, key=lambda item: item.pipeline_id):
        if record.total_runs == 0:
            continue

        label = _pipeline_label(record.pipeline_id, pipeline_names)

        if record.success_rate < SUCCESS_RATE_ALERT_THRESHOLD:
            alerts.append(
                PipelineAlert(
                    pipeline_label=label,
                    alert_type="low_success_rate",
                    message=(
                        f"🚨 {label} has success rate {record.success_rate:.2f}%"
                    ),
                )
            )

        if _is_failed_status(record.last_run_status):
            alerts.append(
                PipelineAlert(
                    pipeline_label=label,
                    alert_type="failed_last_run",
                    message=f"🚨 {label} failed on latest run",
                )
            )

    return alerts


def render_pipeline_alerts(alerts: list[PipelineAlert]) -> None:
    st.subheader("Pipeline Alerts")

    if not alerts:
        st.success("✅ All pipelines healthy")
        return

    for alert in alerts:
        if alert.alert_type == "failed_last_run":
            st.error(alert.message)
        else:
            st.warning(alert.message)


def _success_rate_bar_color(total_runs: int, success_rate: float) -> str:
    status = _pipeline_health_status(total_runs, success_rate)
    if status == "no_data":
        return COLOR_NO_DATA
    if status == "healthy":
        return COLOR_HEALTHY
    if status == "warning":
        return COLOR_WARNING
    return COLOR_CRITICAL


def _empty_chart_figure(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 14, "color": "#64748b"},
    )
    fig.update_layout(
        title=title,
        height=CHART_HEIGHT,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={"t": 50, "b": 20, "l": 20, "r": 20},
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_success_vs_failed_chart(summary: dict) -> None:
    successful_runs = summary["successful_runs"]
    failed_runs = summary["failed_runs"]

    if successful_runs == 0 and failed_runs == 0:
        st.plotly_chart(
            _empty_chart_figure(
                "Success vs Failed Runs",
                "No run data available yet.",
            ),
            use_container_width=True,
        )
        return

    fig = go.Figure(
        data=[
            go.Bar(
                x=["Successful Runs", "Failed Runs"],
                y=[successful_runs, failed_runs],
                marker_color=[COLOR_SUCCESS, COLOR_FAILED],
                text=[successful_runs, failed_runs],
                textposition="outside",
                hovertemplate="%{x}<br>Count: %{y}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Success vs Failed Runs",
        xaxis_title="",
        yaxis_title="Run Count",
        height=CHART_HEIGHT,
        showlegend=False,
        margin={"t": 50, "b": 40, "l": 40, "r": 20},
        yaxis={"rangemode": "tozero"},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_pipeline_success_rate_chart(health_records: list[PipelineHealth]) -> None:
    if not health_records:
        st.plotly_chart(
            _empty_chart_figure(
                "Pipeline Success Rate by Pipeline",
                "No pipeline health data available yet.",
            ),
            use_container_width=True,
        )
        return

    sorted_records = sorted(health_records, key=lambda record: record.pipeline_id)
    pipeline_ids = [str(record.pipeline_id) for record in sorted_records]
    success_rates = [record.success_rate for record in sorted_records]
    bar_colors = [
        _success_rate_bar_color(record.total_runs, record.success_rate)
        for record in sorted_records
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=pipeline_ids,
                y=success_rates,
                marker_color=bar_colors,
                text=[f"{rate:.1f}%" for rate in success_rates],
                textposition="outside",
                hovertemplate=(
                    "Pipeline ID: %{x}<br>Success Rate: %{y:.2f}%<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        title="Pipeline Success Rate by Pipeline",
        xaxis_title="Pipeline ID",
        yaxis_title="Success Rate (%)",
        height=CHART_HEIGHT,
        showlegend=False,
        margin={"t": 50, "b": 40, "l": 40, "r": 20},
        yaxis={"range": [0, 105]},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_summary_metrics(summary: dict) -> None:
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Total Pipelines", summary["total_pipelines"])
    col2.metric("Total Runs", summary["total_runs"])
    col3.metric("Success Rate", f"{summary['success_rate']:.2f}%")
    col4.metric("Failed Runs", summary["failed_runs"])
    col5.metric(
        "Average Duration",
        _format_duration(summary["avg_duration_seconds"]),
    )


def render_pipeline_table(health_records: list[PipelineHealth]) -> None:
    if not health_records:
        st.info("No pipeline health data available yet.")
        return

    st.dataframe(
        _health_to_dataframe(health_records),
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon="🛡️",
        layout="wide",
    )

    st.title(PAGE_TITLE)
    st.caption(f"Connected to FlowGuard API at `{API_BASE_URL}`")

    refresh_col, _ = st.columns([1, 5])
    with refresh_col:
        if st.button("Refresh", type="primary"):
            _load_dashboard_data.clear()
            _load_pipeline_details.clear()
            _load_failure_analytics.clear()

    try:
        summary, health_records, fetch_errors, pipeline_names = _load_dashboard_data(
            API_BASE_URL
        )
    except FlowGuardAPIError as exc:
        st.error(str(exc))
        st.info(
            "Start the backend with "
            "`uvicorn app.main:app --reload` and click **Refresh**."
        )
        return

    if fetch_errors:
        st.warning(
            "Some pipeline metrics could not be loaded:\n\n"
            + "\n".join(f"- {error}" for error in fetch_errors)
        )

    pipeline_alerts = _build_pipeline_alerts(health_records, pipeline_names)
    render_pipeline_alerts(pipeline_alerts)

    render_success_vs_failed_chart(summary)
    render_summary_metrics(summary)
    render_pipeline_success_rate_chart(health_records)

    try:
        failure_analytics = _load_failure_analytics(API_BASE_URL)
    except FlowGuardAPIError as exc:
        st.error(f"Unable to load failure analytics: {exc}")
        failure_analytics = {}

    render_top_failure_reasons(failure_analytics)

    st.subheader("Pipeline Health Overview")
    render_pipeline_table(health_records)

    render_pipeline_details(pipeline_names)


if __name__ == "__main__":
    main()
