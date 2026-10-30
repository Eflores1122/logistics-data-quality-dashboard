"""Render a persisted run as Markdown or a self-contained HTML report."""

from __future__ import annotations

import html
from datetime import date, datetime

from rutanorte_dq.evaluate import Evaluation
from rutanorte_dq.history import StoredRun
from rutanorte_dq.scoring import DAY_TABLE

DISCLAIMER = (
    "Reference implementation for Edgar Flores. RutaNorte Paqueteria is a fictitious "
    "Mexican parcel network created for this project. All warehouse rows are synthetic. "
    "This report does not describe any employer, client, or production system."
)


def render_markdown(run: StoredRun, evaluation: Evaluation | None = None) -> str:
    lines = [
        "# RutaNorte data-quality report",
        "",
        f"> {DISCLAIMER}",
        "",
        f"- Suite: `{run.suite_name}`",
        f"- Run: `{run.run_id}`",
        f"- Run timestamp (UTC): {_fmt_ts(run.run_ts)}",
        f"- As-of date: {run.as_of.isoformat()}",
        f"- SLA: score >= {run.pass_score:.0f}",
        f"- Critical failure fails the day: {'yes' if run.fail_on_critical else 'no'}",
        "",
    ]
    if evaluation is not None:
        lines.extend(_markdown_evaluation(evaluation))
    lines.extend(_markdown_scores(run))
    lines.extend(_markdown_failures(run))
    return "\n".join(lines).rstrip() + "\n"


def render_html(run: StoredRun, evaluation: Evaluation | None = None) -> str:
    evaluation_html = "" if evaluation is None else _html_evaluation(evaluation)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>RutaNorte data-quality report</title>
  <style>
    body {{ font-family: "Segoe UI", Helvetica, Arial, sans-serif; margin: 2rem auto; max-width: 1100px;
            color: #142226; background: #f7f4ef; }}
    h1, h2 {{ color: #0e6b67; }}
    .disclaimer {{ background: #e7f0ee; border-left: 4px solid #0e6b67; padding: 0.8rem 1rem; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0 1.5rem; background: white; }}
    th, td {{ border: 1px solid #d5dedc; padding: 0.4rem 0.55rem; text-align: left; vertical-align: top;
             font-size: 0.92rem; }}
    th {{ background: #0e6b67; color: white; }}
    .fail {{ color: #9c2f2f; font-weight: 700; }}
    .pass {{ color: #1f7a4d; font-weight: 700; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  </style>
</head>
<body>
  <h1>RutaNorte data-quality report</h1>
  <p class="disclaimer">{html.escape(DISCLAIMER)}</p>
  <p>
    Suite <code>{html.escape(run.suite_name)}</code> ·
    run <code>{html.escape(run.run_id)}</code> ·
    {_fmt_ts(run.run_ts)} UTC ·
    as-of {run.as_of.isoformat()} ·
    pass score {run.pass_score:.0f}
  </p>
  {evaluation_html}
  <h2>Daily SLA</h2>
  {_html_table(["Date", "Score", "SLA", "Failed checks", "Critical failures"], _score_rows(run))}
  <h2>Failing checks</h2>
  {_html_failures(run)}
</body>
</html>
"""


def _fmt_ts(value: datetime) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _day_scores(run: StoredRun):
    return [row for row in run.scores if row.table_name == DAY_TABLE]


def _failures(run: StoredRun):
    return [row for row in run.checks if row.status == "fail"]


def _markdown_evaluation(evaluation: Evaluation) -> list[str]:
    return [
        "## Detection against injected defects",
        "",
        f"- Injected defects: {evaluation.defects_total}",
        f"- Caught: {evaluation.defects_caught}",
        f"- Missed: {evaluation.false_negatives}",
        f"- Unexpected failing checks: {evaluation.false_positives}",
        f"- Precision: {evaluation.precision:.3f}",
        f"- Recall: {evaluation.recall:.3f}",
        (
            f"- Row-level recall: {evaluation.row_level_caught}/"
            f"{evaluation.row_level_applicable} ({evaluation.row_level_recall:.3f})"
        ),
        "",
        "A defect is caught when its check fails on the injected business date and, where",
        "the catalog sets a minimum, the check counts at least that many offending rows.",
        "Precision is caught defects divided by caught defects plus failing checks that",
        "are not in the catalog.",
        "",
    ]


def _markdown_scores(run: StoredRun) -> list[str]:
    lines = [
        "## Daily SLA",
        "",
        "| Date | Score | SLA | Failed checks | Critical failures |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for row in _day_scores(run):
        lines.append(
            f"| {row.business_date.isoformat()} | {row.score:.2f} | {row.status} | "
            f"{row.checks_failed} | {row.critical_failed} |"
        )
    lines.append("")
    return lines


def _markdown_failures(run: StoredRun) -> list[str]:
    lines = ["## Failing checks", ""]
    failures = _failures(run)
    if not failures:
        lines.append("No failing checks.")
        lines.append("")
        return lines
    for row in failures:
        lines.append(f"### {row.business_date.isoformat()} · {row.table_name} · `{row.check_id}`")
        lines.append("")
        lines.append(f"- Severity: {row.severity}")
        lines.append(
            f"- Metric: {row.metric_name} = {_fmt_metric(row.metric_value)} (threshold {row.comparator} {_fmt_metric(row.threshold)})"
        )
        lines.append(f"- Offending rows: {row.failed_row_count} of {row.total_row_count}")
        lines.append(f"- {row.message}")
        if row.sample_rows:
            lines.append("")
            lines.append("Sample:")
            lines.append("")
            lines.append("```")
            for sample in row.sample_rows[:5]:
                lines.append(str(sample))
            lines.append("```")
        lines.append("")
    return lines


def _fmt_metric(value) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _score_rows(run: StoredRun) -> list[list[str]]:
    return [
        [
            row.business_date.isoformat()
            if isinstance(row.business_date, date)
            else str(row.business_date),
            f"{row.score:.2f}",
            row.status,
            str(row.checks_failed),
            str(row.critical_failed),
        ]
        for row in _day_scores(run)
    ]


def _html_evaluation(evaluation: Evaluation) -> str:
    cells = [
        ("Injected defects", str(evaluation.defects_total)),
        ("Caught", str(evaluation.defects_caught)),
        ("Missed", str(evaluation.false_negatives)),
        ("Unexpected fails", str(evaluation.false_positives)),
        ("Precision", f"{evaluation.precision:.3f}"),
        ("Recall", f"{evaluation.recall:.3f}"),
        (
            "Row-level recall",
            f"{evaluation.row_level_caught}/{evaluation.row_level_applicable} "
            f"({evaluation.row_level_recall:.3f})",
        ),
    ]
    body = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"
        for label, value in cells
    )
    return f"<h2>Detection against injected defects</h2><table>{body}</table>"


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = []
    for row in rows:
        rendered = []
        for index, cell in enumerate(row):
            text = html.escape(cell)
            if index == 2:
                css = "pass" if cell == "pass" else "fail" if cell == "fail" else ""
                text = f'<span class="{css}">{text}</span>'
            rendered.append(f"<td>{text}</td>")
        body.append("<tr>" + "".join(rendered) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _html_failures(run: StoredRun) -> str:
    failures = _failures(run)
    if not failures:
        return "<p>No failing checks.</p>"
    rows = []
    for row in failures:
        sample = ""
        if row.sample_rows:
            preview = html.escape(str(row.sample_rows[0]))
            sample = f"<div><code>{preview}</code></div>"
        rows.append(
            "<tr>"
            f"<td>{row.business_date.isoformat()}</td>"
            f"<td>{html.escape(row.table_name)}</td>"
            f"<td><code>{html.escape(row.check_id)}</code></td>"
            f"<td>{html.escape(row.severity)}</td>"
            f"<td>{row.failed_row_count}</td>"
            f"<td>{html.escape(row.message)}{sample}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Date</th><th>Table</th><th>Check</th><th>Severity</th>"
        "<th>Offending rows</th><th>Detail</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )
