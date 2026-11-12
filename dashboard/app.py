"""Interactive control room for the fictitious RutaNorte Paqueteria data-quality suite."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from rutanorte_dq.evaluate import evaluate_results, load_defects
from rutanorte_dq.paths import (
    default_db_path,
    default_ground_truth_path,
    default_suite_path,
    repo_root,
)
from rutanorte_dq.scoring import DAY_TABLE
from rutanorte_dq.suite import load_suite
from rutanorte_dq.warehouse import connect, latest_run, load_samples

PASS = "#1F7A4D"
FAIL = "#9C2F2F"
TEAL = "#0E6B67"
COPPER = "#C4622D"
INK = "#142226"
MUTED = "#5C6B6E"


def main() -> None:
    st.set_page_config(
        page_title="RutaNorte Data Quality",
        page_icon="◆",
        layout="wide",
    )
    _css()
    st.markdown(
        """
        <div class="np-hero">
          <div class="np-kicker">Synthetic reference · Mexico</div>
          <h1>RutaNorte data quality</h1>
          <p>Control room for a fictitious parcel network. Scores, failing checks,
          offending rows, and table lineage come from the local DuckDB history.
          This is not an employer system.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    db_path = default_db_path()
    if not db_path.exists():
        st.error(
            "Warehouse not found. From the repository root run "
            "`rutanorte-dq generate` and then `rutanorte-dq run`."
        )
        st.stop()

    try:
        run_header, checks, scores = _load(str(db_path), db_path.stat().st_mtime)
    except Exception as exc:  # noqa: BLE001 - show a recoverable dashboard error
        st.error(f"Could not read the data-quality history: {exc}")
        st.stop()
    if checks.empty or scores.empty:
        st.warning("The warehouse has no suite run yet. Run `rutanorte-dq run`.")
        st.stop()

    suite = load_suite(default_suite_path(), root=repo_root())
    evaluation = _evaluation(checks)
    day = scores[scores["table_name"] == DAY_TABLE].sort_values("business_date")
    latest = day.iloc[-1]
    failing_days = int((day["status"] == "fail").sum())

    cards = st.columns(6)
    cards[0].metric("Latest score", f"{latest['score']:.1f}")
    cards[1].metric("Latest SLA", str(latest["status"]).upper())
    cards[2].metric("Days failing SLA", f"{failing_days} / {len(day)}")
    cards[3].metric("Failing checks", int((checks["status"] == "fail").sum()))
    if evaluation is None:
        cards[4].metric("Defects caught", "n/a")
        cards[5].metric("Precision / recall", "n/a")
    else:
        cards[4].metric(
            "Defects caught",
            f"{evaluation.defects_caught} / {evaluation.defects_total}",
        )
        cards[5].metric(
            "Precision / recall",
            f"{evaluation.precision:.3f} / {evaluation.recall:.3f}",
        )

    as_of = _as_date(run_header[3])
    st.caption(
        f"Run {run_header[0]} · {run_header[1]} UTC · suite {run_header[2]} · "
        f"as-of {as_of.isoformat()} · pass score {run_header[5]:.0f}. "
        "A day above the score line still fails SLA when a critical check fails."
    )

    _trend(day, float(run_header[5]))
    _heatmap(scores)

    focus_dates = [_as_date(value) for value in day["business_date"]]
    date_labels = ["All dates", *[item.isoformat() for item in focus_dates]]
    selected_label = st.selectbox("Business date", date_labels, index=0)
    if selected_label == "All dates":
        visible = checks
        lineage_day = focus_dates[-1]
        lineage_note = f"Lineage colors use the latest business date, {lineage_day.isoformat()}."
    else:
        selected = date.fromisoformat(selected_label)
        visible = checks[checks["business_date"].map(_as_date) == selected]
        lineage_day = selected
        lineage_note = f"Lineage colors use {lineage_day.isoformat()}."

    left, right = st.columns([1.15, 0.85])
    with left:
        st.subheader("Failing checks")
        failing = visible[visible["status"] == "fail"].copy()
        if failing.empty:
            st.success("No failing checks for this selection.")
        else:
            show = failing[
                [
                    "business_date",
                    "table_name",
                    "check_id",
                    "severity",
                    "metric_value",
                    "threshold",
                    "failed_row_count",
                    "message",
                ]
            ].sort_values(["business_date", "severity", "check_id"])
            st.dataframe(show, width="stretch", hide_index=True, height=320)
    with right:
        st.subheader("Table lineage")
        st.caption(lineage_note)
        status_by_table = _status_map(scores, lineage_day)
        st.markdown(_lineage_svg(suite, status_by_table), unsafe_allow_html=True)

    st.subheader("Evidence")
    _evidence(failing if not failing.empty else visible[visible["status"] == "fail"])


def _css() -> None:
    st.markdown(
        """
        <style>
          .stApp { background: #f7f4ef; color: #142226; }
          header, footer, #MainMenu { visibility: hidden; height: 0; }
          .np-hero h1 { margin: 0; color: #0e6b67; font-size: 2.1rem; letter-spacing: -0.03em; }
          .np-kicker { color: #c4622d; font-weight: 700; letter-spacing: 0.08em;
                       text-transform: uppercase; font-size: 0.78rem; }
          .np-hero p { max-width: 760px; color: #3d4c4e; margin-top: 0.35rem; }
          div[data-testid="stMetric"] {
            background: white; border: 1px solid #d7e2e0; border-radius: 12px; padding: 0.6rem 0.8rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def _load(db_path: str, _mtime: float):
    connection = connect(db_path, read_only=True)
    try:
        header = latest_run(connection)
        if header is None:
            return None, pd.DataFrame(), pd.DataFrame()
        checks = connection.execute("SELECT * FROM dq.latest_check_results").fetchdf()
        scores = connection.execute("SELECT * FROM dq.latest_sla_scores").fetchdf()
        return header, checks, scores
    finally:
        connection.close()


def _evaluation(checks: pd.DataFrame):
    path = default_ground_truth_path()
    if not path.exists():
        return None
    rows = []
    for record in checks.to_dict(orient="records"):
        rows.append(
            SimpleNamespace(
                check_id=record["check_id"],
                business_date=_as_date(record["business_date"]),
                status=record["status"],
                failed_row_count=int(record["failed_row_count"] or 0),
                table_name=record["table_name"],
                message=record["message"],
            )
        )
    return evaluate_results(rows, load_defects(path))


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _trend(day: pd.DataFrame, pass_score: float) -> None:
    frame = day.copy()
    frame["business_date"] = frame["business_date"].map(_as_date)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["business_date"],
            y=frame["score"],
            mode="lines+markers",
            name="Daily score",
            line={"color": TEAL, "width": 2},
            marker={
                "size": 8,
                "color": [PASS if status == "pass" else FAIL for status in frame["status"]],
                "line": {"width": 0},
            },
            hovertemplate="%{x}<br>score %{y:.2f}<extra></extra>",
        )
    )
    figure.add_hline(
        y=pass_score,
        line_dash="dash",
        line_color=COPPER,
        annotation_text=f"SLA {pass_score:.0f}",
        annotation_position="top left",
    )
    figure.update_layout(
        height=320,
        margin={"l": 16, "r": 16, "t": 24, "b": 16},
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis={"range": [60, 102], "title": "Score"},
        xaxis={"title": ""},
        showlegend=False,
        font={"color": INK},
    )
    st.plotly_chart(figure, width="stretch")


def _heatmap(scores: pd.DataFrame) -> None:
    tables = scores[scores["table_name"] != DAY_TABLE].copy()
    tables["business_date"] = tables["business_date"].map(_as_date)
    pivot = tables.pivot(index="table_name", columns="business_date", values="score")
    figure = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[column.isoformat() for column in pivot.columns],
            y=list(pivot.index),
            colorscale=[[0, FAIL], [0.55, COPPER], [1, TEAL]],
            zmin=70,
            zmax=100,
            colorbar={"title": "Score"},
            hovertemplate="%{y}<br>%{x}<br>%{z:.1f}<extra></extra>",
        )
    )
    figure.update_layout(
        height=280,
        margin={"l": 16, "r": 16, "t": 24, "b": 16},
        plot_bgcolor="#E7F0EE",
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": INK},
    )
    st.plotly_chart(figure, width="stretch")
    st.caption("Empty cells are tables scored only on the as-of date, such as the hub registry.")


def _status_map(scores: pd.DataFrame, business_date: date) -> dict[str, str]:
    subset = scores[scores["table_name"] != DAY_TABLE]
    found = {}
    for record in subset.to_dict(orient="records"):
        if _as_date(record["business_date"]) == business_date:
            found[record["table_name"]] = record["status"]
    return found


def _lineage_svg(suite, status_by_table: dict[str, str]) -> str:
    layers = ("extract", "warehouse", "mart")
    grouped = {layer: [node for node in suite.nodes if node.layer == layer] for layer in layers}
    width, height = 860, 430
    box_w, box_h = 168, 48
    columns = {"extract": 24, "warehouse": 336, "mart": 648}
    positions = {}
    for layer, nodes in grouped.items():
        gap = (height - 36 - len(nodes) * box_h) / max(len(nodes), 1)
        for index, node in enumerate(nodes):
            x = columns[layer]
            y = 24 + index * (box_h + gap)
            positions[node.id] = (x, y, node)

    lines = []
    for edge in suite.lineage:
        if edge.source not in positions or edge.target not in positions:
            continue
        x1, y1, _ = positions[edge.source]
        x2, y2, _ = positions[edge.target]
        lines.append(
            f'<line x1="{x1 + box_w}" y1="{y1 + box_h / 2:.1f}" '
            f'x2="{x2}" y2="{y2 + box_h / 2:.1f}" stroke="#9BB0AE" stroke-width="1.4" />'
        )
    boxes = []
    for node_id, (x, y, node) in positions.items():
        status = status_by_table.get(node_id)
        if status == "fail":
            stroke, fill, tag = FAIL, "#F8E8E8", "FAIL"
        elif status == "pass":
            stroke, fill, tag = PASS, "#E5F4EC", "PASS"
        else:
            stroke, fill, tag = MUTED, "#F4F7F7", "SOURCE"
        label = _escape(node.label)
        boxes.append(
            f'<rect x="{x}" y="{y:.1f}" rx="8" ry="8" width="{box_w}" height="{box_h}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.6" />'
            f'<text x="{x + 10}" y="{y + 20:.1f}" font-size="12" font-family="Segoe UI, Helvetica, sans-serif" '
            f'fill="{INK}">{label}</text>'
            f'<text x="{x + 10}" y="{y + 36:.1f}" font-size="10" font-family="Segoe UI, Helvetica, sans-serif" '
            f'fill="{stroke}">{tag}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" '
        f'aria-label="RutaNorte table lineage">' + "".join(lines) + "".join(boxes) + "</svg>"
    )


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _evidence(failing: pd.DataFrame) -> None:
    if failing.empty:
        st.info("Select a date with a failing check to see offending rows.")
        return
    labels = []
    records = failing.to_dict(orient="records")
    for record in records:
        labels.append(
            f"{_as_date(record['business_date']).isoformat()} · {record['check_id']} · {record['severity']}"
        )
    preferred = next(
        (
            index
            for index, record in enumerate(records)
            if record["check_id"] == "customers_email_completeness"
        ),
        0,
    )
    choice = st.selectbox("Failing check", labels, index=preferred)
    record = records[labels.index(choice)]
    st.markdown(f"**{record['description'] or record['check_id']}**")
    st.write(record["message"])
    samples = load_samples(record.get("sample_rows"))
    if not samples:
        st.caption("This failure did not store sample rows.")
        return
    st.dataframe(pd.DataFrame(samples), width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
