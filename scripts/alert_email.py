"""
Builds the alert digest email for check_logs: a plain-text body and an HTML
alternative, each linking every alert to the frontend views it mentions
(workflow, email, run/attachment logs) under APP_PUBLIC_URL.
"""
import html


def _link_items(row) -> list[tuple[str, str]]:
    """(label, frontend path) for every view the log mentions."""
    log = row.Log
    items = []
    if log.workflow_id is not None:
        items.append((f"Workflow: {row.workflow_name} (#{log.workflow_id})", f"/workflow/{log.workflow_id}"))
    if log.email_id is not None:
        subject = f'"{row.email_subject}" ' if row.email_subject else ""
        items.append((f"Email: {subject}(#{log.email_id})", f"/email/{log.email_id}"))
    if log.run_id is not None:
        items.append((f"Run #{log.run_id} logs", f"/logs?q=run:{log.run_id}"))
    if log.attachment_id is not None:
        items.append((f"Attachment #{log.attachment_id} logs", f"/logs?q=attachment:{log.attachment_id}"))
    return items


def _timestamp(log) -> str:
    return log.created_at.strftime("%Y-%m-%d %H:%M:%S")


def _format_text(rows, base: str) -> str:
    lines = []
    for row in rows:
        log = row.Log
        lines.append(
            f"{_timestamp(log)} {log.level.name} {log.event_type} "
            f"wf={log.workflow_id} cp={log.checkpoint_id} - {log.message}"
        )
        if base:
            lines.extend(f"  {label}  {base}{path}" for label, path in _link_items(row))
    return "\n".join(lines)


LEVEL_COLORS = {"CRITICAL": "#b91c1c", "ERROR": "#dc2626", "WARNING": "#d97706"}
CELL_STYLE = "padding:6px 10px;border-bottom:1px solid #e5e7eb;vertical-align:top;text-align:left"


def _html_row(tag: str, cells: list[str]) -> str:
    return "<tr>" + "".join(f'<{tag} style="{CELL_STYLE}">{c}</{tag}>' for c in cells) + "</tr>"


def _format_html(rows, base: str) -> str:
    # Inline styles only: many mail clients strip <style> blocks. Every DB value is
    # escaped, since log messages and email subjects can come from incoming mail.
    e = html.escape
    body_rows = []
    for row in rows:
        log = row.Log
        links = [
            f'<a href="{e(base + path)}" style="color:#2563eb">{e(label)}</a>' if base else e(label)
            for label, path in _link_items(row)
        ]
        level = log.level.name
        body_rows.append(_html_row("td", [
            f'<span style="white-space:nowrap">{e(_timestamp(log))}</span>',
            f'<b style="color:{LEVEL_COLORS.get(level, "#374151")}">{e(level)}</b>',
            f"<code>{e(log.event_type)}</code>",
            e(log.message or ""),
            "<br>".join(links),
        ]))

    return (
        '<div style="font-family:Arial,sans-serif;font-size:14px;color:#111827">'
        f"<p>{len(rows)} alert(s)</p>"
        '<table style="border-collapse:collapse">'
        f'{_html_row("th", ["Time", "Level", "Event", "Message", "Links"])}'
        f'{"".join(body_rows)}</table></div>'
    )


def format_digest(rows, public_url: str) -> tuple[str, str, str]:
    """Subject, plain-text body and HTML body for one user's digest.

    `rows` are `_send_digests` query rows: `.Log` plus the joined
    `.workflow_name` and `.email_subject` (None when the log has no such link).
    An empty `public_url` leaves the views unlinked."""
    base = public_url.rstrip("/")
    subject = f"[mexng] {len(rows)} alert(s)"
    return subject, _format_text(rows, base), _format_html(rows, base)
