"""HTML renderers for the dashboard shell.

Each function returns a markup string rather than calling Streamlit, so the
layout can be unit-tested without a running server and so the section order is
readable in one place in app.py.

Interactions inside these HTML blocks (category drill-down, "View supporting
feedback", the back control) are plain anchors carrying query parameters.
Streamlit re-runs on navigation and reads them back, which keeps the mockup's
markup intact while staying wired to real data -- no static mockup records
appear anywhere in this file.
"""

from __future__ import annotations

from html import escape
from urllib.parse import quote

from ..models.taxonomy import SEVERITY_SCALE  # noqa: F401  (documents the 1-5 scale)
from .theme import SEVERITY_BADGE

# Anchor target for the feedback section, so an action link jumps to the
# records it filtered instead of leaving the reader at the top of the page.
FEEDBACK_ANCHOR = "afi-feedback"


def _esc(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def _href(param: str, value: str, fragment: str = "") -> str:
    """Build a query-parameter link.

    The value must be percent-encoded, not HTML-escaped. Most taxonomy names
    contain an ampersand ("Permissions & Approvals"); HTML-escaping produces
    `&amp;`, the browser decodes that back to a bare `&`, and the query string
    then splits there -- so the app received "Permissions " and matched nothing.
    Eight of eleven categories and forty-six of fifty-four subcategories were
    affected.
    """
    encoded = quote(str(value), safe="")
    tail = f"#{fragment}" if fragment else ""
    return f"?{param}={encoded}{tail}"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# --------------------------------------------------------------------------
def render_topbar(meta: dict) -> str:
    taxonomy = _esc(meta.get("taxonomy_version", "v2.0"))
    return (
        '<div class="afi-topbar">'
        '<div class="afi-brand">'
        '<span class="afi-brand-mark">&#8961;</span> Action Feedback Intelligence '
        '<span class="afi-badge b-blue">POC concept</span>'
        "</div>"
        f'<div class="afi-top-meta">Evidence-first qualitative analysis · '
        f"taxonomy {taxonomy}</div>"
        "</div>"
    )


def render_hero(meta: dict, in_scope: int, excluded: int) -> str:
    model = _esc(meta.get("model_name", "—"))
    prompt = _esc(meta.get("prompt_version", "—"))
    taxonomy = _esc(meta.get("taxonomy_version", "—"))
    run_id = _esc(meta.get("analysis_run_id", "—"))
    return (
        '<div class="afi-hero"><div>'
        '<div class="afi-eyebrow">Action Configuration feedback</div>'
        "<h1>Turn feedback into decisions that retain the original evidence.</h1>"
        f'<p>{in_scope} in-scope records, categorised under a closed taxonomy and '
        f"counted in Python. {excluded} out-of-scope records are excluded from "
        "every figure.</p>"
        "</div>"
        f'<div class="afi-run-meta"><b>Analysis run</b><br>'
        f"Model {model} · prompt {prompt}<br>"
        f"Taxonomy {taxonomy} · human review enabled<br>"
        f'<span style="font-size:11px">{run_id}</span></div>'
        "</div>"
    )


def render_kpis(product_actions: int, open_actions: int,
                high_severity: int, needs_review: int) -> str:
    cards = [
        ("Product actions", product_actions,
         "Distinct taxonomy subcategories in view", ""),
        ("Open product actions", open_actions,
         "Entirely unmet — nothing shipped in this area yet", "good"),
        ("High severity", high_severity,
         "Matching records at severity 4+", "warning"),
        ("Needs human review", needs_review,
         "Ambiguous or low-confidence classification", ""),
    ]
    html = ['<div class="afi-kpis">']
    for label, value, detail, tone in cards:
        html.append(
            f'<div class="afi-card afi-kpi"><span class="label">{_esc(label)}</span>'
            f'<span class="value">{value:,}</span>'
            f'<span class="detail {tone}">{_esc(detail)}</span></div>'
        )
    html.append("</div>")
    return "".join(html)


# --------------------------------------------------------------------------
def render_product_actions(actions: list[dict], limit: int) -> str:
    head = (
        '<div class="afi-actions"><div class="afi-section-head"><div>'
        "<h2>Recommended product actions</h2>"
        "<p>Derived from open, in-scope feedback. Open an action to inspect its "
        "evidence.</p></div></div>"
    )
    if not actions:
        return (
            head
            + '<div class="afi-empty">No recommended product actions match these '
              "filters. Try widening lifecycle status, problem type, journey stage, "
              "taxonomy, persona, confidence or severity.</div></div>"
        )

    rows = ['<div class="afi-action-list">']
    for action in actions[:limit]:
        severity = int(round(action["avg_severity"]))
        cls = "afi-insight afi-insight-high" if action["max_severity"] >= 4 else "afi-insight"
        badge = SEVERITY_BADGE.get(severity, "b-neutral")
        signal = action.get("signal") or ""
        metrics = [
            f'<span class="afi-badge b-blue">'
            f'{_plural(action["open_records"], "open supporting record")}</span>',
            f'<span class="afi-badge b-neutral">{_esc(action["category"])}</span>',
        ]
        if action.get("source_diversity", 1) > 1:
            metrics.append(
                f'<span class="afi-badge b-green">'
                f'{_plural(action["source_diversity"], "source")}</span>'
            )
        if action.get("needs_review"):
            metrics.append(
                f'<span class="afi-badge b-amber">'
                f'{action["needs_review"]} flagged for review</span>'
            )
        focus = _href("focus", action["subcategory"], FEEDBACK_ANCHOR)
        rows.append(
            f'<div class="{cls}">'
            f'<div class="afi-insight-top">'
            f'<h3 class="afi-action-title">{_esc(action["product_action"])}</h3>'
            f'<span class="afi-badge {badge}">Severity {severity}</span></div>'
            f"<p>{_esc(signal)}</p>"
            f'<div class="afi-action-metrics">{"".join(metrics)}</div>'
            f'<a class="afi-action-btn" href="{focus}" target="_self">'
            f"View supporting feedback &#8595;</a>"
            "</div>"
        )
    rows.append("</div>")
    return head + "".join(rows) + "</div>"


# --------------------------------------------------------------------------
def _bar_rows(rows: list[tuple[str, int]], link: str | None) -> str:
    """Shared CSS-bar markup. The mockup charts are bars, not a plotting library."""
    if not rows:
        return '<div class="afi-empty">No matching feedback.</div>'
    top = max((count for _, count in rows), default=0) or 1
    out = ['<div class="afi-category-list">']
    for name, count in rows:
        width = round(count / top * 100)
        body = (
            f"<div><strong>{_esc(name)}</strong>"
            f'<div class="afi-bar"><span style="width:{width}%"></span></div></div>'
            f'<div class="afi-row-num"><b>{count}</b> '
            f'{"record" if count == 1 else "records"}</div>'
        )
        if link:
            out.append(
                f'<a class="afi-category-row" href="{_href(link, name)}" '
                f'target="_self">{body}</a>'
            )
        else:
            out.append(f'<div class="afi-category-row">{body}</div>')
    out.append("</div>")
    return "".join(out)


def render_taxonomy_chart(rows: list[tuple[str, int]],
                          drilled_category: str | None) -> str:
    if drilled_category:
        crumb = (
            f'<div class="afi-crumb">'
            f'<span><a href="?" target="_self">Categories</a> › '
            f"<b>{_esc(drilled_category)}</b></span>"
            f'<a href="?" target="_self">← Back</a></div>'
        )
        desc = "Subcategories inside this category. Select one to filter everything."
        chart = _bar_rows(rows, link="sub")
    else:
        crumb = ""
        desc = "Based on the number of records matching the current filters. "\
               "Select a category to open its subcategories."
        chart = _bar_rows(rows, link="cat")

    return (
        '<div class="afi-card afi-section" style="box-shadow:none">'
        '<div class="afi-section-head"><div>'
        "<h2>Matching feedback by taxonomy category</h2>"
        f"<p>{desc}</p></div></div>{crumb}{chart}</div>"
    )


def render_journey_chart(rows: list[tuple[str, int]]) -> str:
    """Chronological order is preserved by the caller; never sorted by size."""
    return (
        '<div class="afi-card afi-section" style="box-shadow:none;margin-top:20px">'
        '<div class="afi-section-head"><div>'
        "<h2>Matching feedback by Journey stage</h2>"
        "<p>In the order a user meets them, not by volume.</p></div></div>"
        + _bar_rows(rows, link=None)
        + "</div>"
    )


# --------------------------------------------------------------------------
def _severity_badge(severity: int) -> str:
    return f'<span class="afi-badge {SEVERITY_BADGE.get(severity, "b-neutral")}">' \
           f"Severity {severity}</span>"


def render_feedback_cards(records: list[dict]) -> str:
    if not records:
        return ('<div class="afi-empty">No feedback matches these filters. '
                "Try widening them, or clear the search box.</div>")

    out = [f'<div class="afi-evidence" id="{FEEDBACK_ANCHOR}">']
    for r in records:
        meta = [
            f'<span class="afi-badge b-neutral">{_esc(r["source_system"])}</span>',
            f'<span class="afi-badge b-blue">{_esc(r["lifecycle_status"])}</span>',
        ]
        created = (r.get("created_at") or "")[:10]
        if created:
            meta.append(f'<span class="afi-badge b-neutral">{_esc(created)}</span>')
        meta.append(
            f'<span class="afi-badge b-neutral">'
            f'Confidence {float(r["confidence"]):.2f}</span>'
        )
        meta.append(f'<span class="afi-badge b-purple">{_esc(r["persona"])}</span>')
        if r.get("needs_human_review"):
            meta.append('<span class="afi-badge b-amber">Needs human review</span>')

        labels = [
            f'<span class="afi-label">Primary: '
            f'{_esc(r["primary_taxonomy_category"])}</span>',
            f'<span class="afi-label">Subcategory: '
            f'{_esc(r["primary_taxonomy_subcategory"])}</span>',
        ]
        for category in (r.get("secondary_categories") or []):
            labels.append(f'<span class="afi-label">Secondary: {_esc(category)}</span>')
        labels.append(f'<span class="afi-label">Problem: {_esc(r["problem_type"])}</span>')
        labels.append(f'<span class="afi-label">Stage: {_esc(r["journey_stage"])}</span>')

        quote = (f'<div class="afi-quote">“{_esc(r["evidence_excerpt"])}”</div>'
                 if r.get("evidence_verified") else "")

        out.append(
            '<div class="afi-feedback">'
            f'<div class="afi-feedback-head">'
            f'<div class="afi-feedback-title">{_esc(r["title"])}</div>'
            f'{_severity_badge(int(r["severity"]))}</div>'
            f'<div class="afi-recommended-action"><span>Recommended product action</span>'
            f'<strong>{_esc(r["suggested_product_action"])}</strong></div>'
            f'<div class="afi-feedback-meta">{"".join(meta)}</div>'
            f"{quote}"
            f'<div class="afi-labels">{"".join(labels)}</div>'
            f'<p style="margin:10px 0 0"><a class="afi-source" target="_blank" '
            f'href="{_esc(r["source_url"])}">Open original source ↗</a></p>'
            "</div>"
        )
    out.append("</div>")
    return "".join(out)


def render_filter_state(shown: int, total: int, open_count: int,
                        min_severity: int, focus: str | None) -> str:
    focused = (f' · focused on <b>{_esc(focus)}</b>' if focus else "")
    back = (
        '<a class="afi-focus-back" href="?" target="_self">← Back to filtered view</a>'
        if focus else ""
    )
    return (
        '<div class="afi-filter-state-row">'
        f'<p class="afi-filter-state">Showing {shown} of {total} in-scope records · '
        f"{open_count} open · severity {min_severity}+{focused}</p>{back}</div>"
    )
