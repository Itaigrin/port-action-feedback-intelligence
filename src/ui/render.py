"""HTML renderers for the dashboard shell.

Each function returns a markup string rather than calling Streamlit, so the
layout can be unit-tested without a running server and so the section order is
readable in one place in app.py.

Interactions inside these HTML blocks (category drill-down, "View supporting
feedback", the back controls) carry a `data-afi-click` attribute naming a hidden
Streamlit button. A single delegated listener forwards the click to that button,
so the interaction is an ordinary Streamlit rerun.

They were query-parameter anchors first. That worked, but every click was a real
navigation: the browser tore the page down and Streamlit's shell repainted from
scratch, which showed as a black flash and a moment of unstyled content. A rerun
keeps the page alive, so there is nothing to flash.

No static mockup records appear anywhere in this file -- every value is passed
in from the classified dataset.
"""

from __future__ import annotations

from html import escape

from ..models.taxonomy import SEVERITY_SCALE  # noqa: F401  (documents the 1-5 scale)
from .theme import SEVERITY_BADGE

# Anchor id for the feedback section, so a focus click can scroll to the records
# it just filtered rather than leaving the reader looking at an unchanged screen.
FEEDBACK_ANCHOR = "afi-feedback"

# Hidden-button key prefixes. Shared with app.py so the markup and the buttons
# it targets cannot drift apart.
NAV_DRILL = "afinav_cat"
NAV_SUB = "afinav_sub"
NAV_FOCUS = "afinav_focus"
NAV_BACK = "afinav_back"
NAV_UNFOCUS = "afinav_unfocus"
NAV_SEV = "afinav_sev"
NAV_EDIT = "afinav_edit"


def _esc(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def _click(key: str) -> str:
    """Attributes that turn any element into a proxy for a hidden button.

    href="#" keeps the element keyboard-focusable and styled as a control; the
    delegated listener calls preventDefault, so the fragment is never applied.
    """
    return f'href="#" role="button" data-afi-click="{_esc(key)}"'



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
    model = _esc(meta.get("model_name", "-"))
    prompt = _esc(meta.get("prompt_version", "-"))
    taxonomy = _esc(meta.get("taxonomy_version", "-"))
    run_id = _esc(meta.get("analysis_run_id", "-"))
    return (
        '<div class="afi-hero"><div>'
        '<div class="afi-eyebrow">Action Configuration feedback</div>'
        "<h1>Action Feedback Analyzer</h1>"
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
         "Distinct changes being asked for", ""),
        ("Open product actions", open_actions,
         "Still backed by at least one open record", "good"),
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
def render_product_actions(actions: list[dict], limit: int,
                           selected: str | None = None) -> str:
    """Ranked action cards.

    Every figure comes from the action's own supporting-id list, so the count
    shown here is by construction the number of records the drill-down opens.
    It used to be the size of the whole taxonomy subcategory, which is why a
    card could claim four records and open onto fourteen.
    """
    head = (
        '<div class="afi-actions"><div class="afi-section-head"><div>'
        "<h2>Recommended product actions</h2>"
        "<p>Feedback asking for the same change, grouped together. Only open "
        "records count.</p></div></div>"
    )
    if not actions:
        return (
            head
            + '<div class="afi-empty">No recommended product actions match these '
              "filters. Try widening lifecycle status, problem type, journey stage, "
              "taxonomy, persona, confidence or severity.</div></div>"
        )

    rows = ['<div class="afi-action-list">']
    for index, action in enumerate(actions[:limit]):
        band = int(action.get("severity_band") or 0)
        count = int(action.get("open_supporting_record_count") or 0)
        cls = ("afi-insight afi-insight-high" if band >= 4
               else "afi-insight")
        badge = SEVERITY_BADGE.get(band, "b-neutral")
        signal = action.get("signal") or ""

        metrics = [
            f'<span class="afi-badge b-blue">'
            f'{_plural(count, "open supporting record")}</span>',
        ]
        for category in (action.get("primary_categories") or [])[:1]:
            metrics.append(f'<span class="afi-badge b-neutral">{_esc(category)}</span>')
        if int(action.get("source_diversity") or 0) > 1:
            metrics.append(
                f'<span class="afi-badge b-green">'
                f'{_plural(int(action["source_diversity"]), "source")}</span>')
        if action.get("needs_review"):
            metrics.append(
                f'<span class="afi-badge b-amber">'
                f'{action["needs_review"]} flagged for review</span>')

        is_selected = (selected is not None
                       and action.get("product_action_id") == selected)
        btn_class = "afi-action-btn is-selected" if is_selected else "afi-action-btn"
        label = ("Showing its feedback below &#8595;" if is_selected
                 else "View supporting feedback &#8595;")
        rows.append(
            f'<div class="{cls}">'
            f'<div class="afi-insight-top">'
            f'<h3 class="afi-action-title">'
            f'{_esc(action["product_action_title"])}</h3>'
            f'<span class="afi-badge {badge}">Severity {band}</span></div>'
            f"<p>{_esc(signal)}</p>"
            f'<div class="afi-action-metrics">{"".join(metrics)}</div>'
            f'<a class="{btn_class}" {_click(f"{NAV_FOCUS}_{index}")}'
            f'{" aria-current=\"true\"" if is_selected else ""}>{label}</a>'
            "</div>"
        )
    rows.append("</div>")
    return head + "".join(rows) + "</div>"


# --------------------------------------------------------------------------
def render_insight_cards(journey_stage: dict, subcategory: dict) -> str:
    """The two "where users struggle most" cards.

    Both count only records the classifier judged Negative, so they answer
    "where is the pain" rather than "where is the volume" -- a subcategory can
    be busy with neutral questions and still be nobody's problem.
    """

    def card(data: dict, label: str) -> str:
        name = data.get("group_name") or ""
        count = int(data.get("negative_feedback_count") or 0)
        if not name or not count:
            return (
                '<div class="afi-card afi-insight-card">'
                f'<span class="afi-insight-label">{_esc(label)}</span>'
                '<div class="afi-empty" style="margin-top:10px">'
                "No negative feedback matches these filters.</div></div>"
            )

        parent = data.get("parent_category") or ""
        parent_html = (f'<div class="afi-insight-parent">{_esc(parent)}</div>'
                       if parent else "")
        examples = "".join(
            f"<li>{_esc(ex['text'])}</li>" for ex in data.get("examples", []))
        return (
            '<div class="afi-card afi-insight-card">'
            f'<span class="afi-insight-label">{_esc(label)}</span>'
            f'<div class="afi-insight-name">{_esc(name)}</div>'
            f"{parent_html}"
            f'<div class="afi-insight-count">'
            f'<span class="afi-badge b-red">{_plural(count, "negative feedback record")}'
            f"</span></div>"
            f'<p class="afi-insight-focus"><b>Recommended focus:</b> '
            f'{_esc(data.get("recommended_focus", ""))}</p>'
            f"<ul class=\"afi-insight-examples\">{examples}</ul>"
            "</div>"
        )

    return (
        '<div class="afi-struggle">'
        '<div class="afi-section-head"><div>'
        "<h2>Where users struggle most</h2>"
        "<p>Counting only feedback that describes a problem, under the current "
        "filters.</p></div></div>"
        '<div class="afi-insight-grid">'
        + card(journey_stage, "Journey stage with most negative feedback")
        + card(subcategory, "Subcategory with most negative feedback")
        + "</div></div>"
    )


# --- trend chart -----------------------------------------------------------
# Inline SVG rather than a plotting library: the dashboard's other charts are
# CSS bars, and adding Plotly back for one line chart would reintroduce every
# canvas, toolbar and font conflict that removing it solved.
TREND_COLOURS = ("#2764e7", "#6d43b8", "#087b61", "#c43e3e", "#aa6100",
                 "#0e7490", "#9333ea", "#475569")


def render_trend_chart(trend: dict) -> str:
    weeks = trend.get("weeks") or []
    series = trend.get("series") or []
    window = f'{trend.get("window_start", "")} to {trend.get("window_end", "")}'
    note = (" · latest available data, not the current date"
            if trend.get("is_historical_snapshot") else "")

    head = (
        '<div class="afi-card afi-section afi-trend">'
        '<div class="afi-section-head"><div>'
        "<h2>Negative feedback by Journey stage - last 3 months</h2>"
        f'<p>Weekly, by the date the feedback was raised · {_esc(window)}'
        f"{_esc(note)}</p></div></div>"
    )
    if not series or not weeks:
        return head + ('<div class="afi-empty">No negative feedback in this '
                       "period for the current filters.</div></div>")

    width, height = 640, 230
    pad_l, pad_r, pad_t, pad_b = 30, 8, 12, 26
    peak = max((max(s["points"]) for s in series), default=0) or 1
    span = max(len(weeks) - 1, 1)

    def x(i: int) -> float:
        return pad_l + i * (width - pad_l - pad_r) / span

    def y(v: int) -> float:
        return pad_t + (1 - v / peak) * (height - pad_t - pad_b)

    parts = [f'<svg class="afi-trend-svg" viewBox="0 0 {width} {height}" '
             f'role="img" aria-label="Negative feedback per week by journey stage">']
    # Horizontal guides plus the value axis.
    for step in range(4):
        value = round(peak * (3 - step) / 3)
        gy = y(value)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" '
                     f'y2="{gy:.1f}" class="afi-trend-grid" />')
        parts.append(f'<text x="{pad_l - 6}" y="{gy + 3:.1f}" '
                     f'class="afi-trend-axis" text-anchor="end">{value}</text>')

    for index, entry in enumerate(series):
        colour = TREND_COLOURS[index % len(TREND_COLOURS)]
        points = " ".join(f"{x(i):.1f},{y(v):.1f}"
                          for i, v in enumerate(entry["points"]))
        parts.append(f'<polyline points="{points}" fill="none" '
                     f'stroke="{colour}" stroke-width="2" '
                     'stroke-linejoin="round" stroke-linecap="round" />')
        for i, value in enumerate(entry["points"]):
            if value:
                parts.append(
                    f'<circle cx="{x(i):.1f}" cy="{y(value):.1f}" r="2.6" '
                    f'fill="{colour}" />')

    # Every third week label, so the axis stays readable at this width.
    for i, week in enumerate(weeks):
        if i % 3 == 0 or i == len(weeks) - 1:
            parts.append(f'<text x="{x(i):.1f}" y="{height - 8}" '
                         f'class="afi-trend-axis" text-anchor="middle">'
                         f"{_esc(week[5:])}</text>")

    # --- shared hover -----------------------------------------------------
    # One invisible column per week. Hovering anywhere in it reveals a guide
    # line and a single panel listing every stage at that week -- reading one
    # week across all lines is the question this chart exists to answer, and
    # per-point tooltips could not answer it: they required hitting a 2.6px
    # dot, and a stage sitting at zero had no dot to hit.
    #
    # Pure SVG and CSS. A scripted tooltip would have to live in a component
    # iframe, which cannot draw over the page.
    half = (width - pad_l - pad_r) / max(len(weeks) - 1, 1) / 2
    # Baselines, not box tops. The header needs a full line of clearance or it
    # sits on top of the first row.
    row_h = 15
    head_baseline = 15
    first_row_baseline = 33
    tip_w = 246

    for i, week in enumerate(weeks):
        cx = x(i)
        # Only stages that actually have feedback this week. Listing every
        # stage with a zero filled the panel with rows that said nothing and
        # buried the one or two that mattered.
        present = [(index, entry) for index, entry in enumerate(series)
                   if entry["points"][i]]
        tip_h = (first_row_baseline + row_h * (len(present) - 1) + 11
                 if present else first_row_baseline + 4)

        # Flip the panel to the left once the column is past the midpoint, so
        # it never runs off the edge.
        flip = cx > width / 2
        tip_x = cx - tip_w - 10 if flip else cx + 10
        tip_x = max(pad_l, min(tip_x, width - pad_r - tip_w))
        tip_y = pad_t + 2

        rows = []
        for slot, (index, entry) in enumerate(present):
            colour = TREND_COLOURS[index % len(TREND_COLOURS)]
            ry = tip_y + first_row_baseline + row_h * slot
            rows.append(
                f'<rect x="{tip_x + 9:.1f}" y="{ry - 7:.1f}" width="8" '
                f'height="3" rx="1.5" fill="{colour}" />'
                f'<text x="{tip_x + 22:.1f}" y="{ry:.1f}" '
                f'class="afi-trend-tip-row">{_esc(entry["stage"])}</text>'
                f'<text x="{tip_x + tip_w - 10:.1f}" y="{ry:.1f}" '
                f'class="afi-trend-tip-val" text-anchor="end">'
                f'{entry["points"][i]}</text>'
            )
        if not present:
            rows.append(
                f'<text x="{tip_x + 10:.1f}" '
                f'y="{tip_y + first_row_baseline - 6:.1f}" '
                'class="afi-trend-tip-row">No negative feedback this week</text>'
            )

        parts.append(
            f'<g class="afi-trend-col">'
            f'<rect x="{cx - half:.1f}" y="{pad_t}" width="{half * 2:.1f}" '
            f'height="{height - pad_t - pad_b}" fill="transparent" />'
            f'<line class="afi-trend-guide" x1="{cx:.1f}" y1="{pad_t}" '
            f'x2="{cx:.1f}" y2="{height - pad_b}" />'
            f'<g class="afi-trend-tip">'
            f'<rect x="{tip_x:.1f}" y="{tip_y:.1f}" width="{tip_w}" '
            f'height="{tip_h}" rx="8" class="afi-trend-tip-bg" />'
            f'<text x="{tip_x + 10:.1f}" y="{tip_y + head_baseline:.1f}" '
            f'class="afi-trend-tip-head">Week of {_esc(week)}</text>'
            f'{"".join(rows)}</g></g>'
        )

    parts.append("</svg>")

    legend = "".join(
        f'<span class="afi-trend-key">'
        f'<i style="background:{TREND_COLOURS[i % len(TREND_COLOURS)]}"></i>'
        f'{_esc(entry["stage"])}</span>'
        for i, entry in enumerate(series)
    )
    return (head + "".join(parts)
            + f'<div class="afi-trend-legend">{legend}</div></div>')


# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
def _bar_rows(rows: list[tuple[str, int]], click_prefix: str | None) -> str:
    """Shared CSS-bar markup. The mockup charts are bars, not a plotting library."""
    if not rows:
        return '<div class="afi-empty">No matching feedback.</div>'
    top = max((count for _, count in rows), default=0) or 1
    out = ['<div class="afi-category-list">']
    for index, (name, count) in enumerate(rows):
        width = round(count / top * 100)
        body = (
            f"<div><strong>{_esc(name)}</strong>"
            f'<div class="afi-bar"><span style="width:{width}%"></span></div></div>'
            f'<div class="afi-row-num"><b>{count}</b> '
            f'{"record" if count == 1 else "records"}</div>'
        )
        if click_prefix:
            out.append(
                f'<a class="afi-category-row" '
                f'{_click(f"{click_prefix}_{index}")}>{body}</a>'
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
            f'<span><a {_click(NAV_BACK)}>Categories</a> › '
            f"<b>{_esc(drilled_category)}</b></span>"
            f'<a {_click(NAV_BACK)}>← Back</a></div>'
        )
        desc = "Subcategories inside this category. Select one to filter everything."
        chart = _bar_rows(rows, NAV_SUB)
    else:
        crumb = ""
        desc = "Based on the number of records matching the current filters. "\
               "Select a category to open its subcategories."
        chart = _bar_rows(rows, NAV_DRILL)

    return (
        '<div class="afi-card afi-section" style="box-shadow:none">'
        '<div class="afi-section-head"><div>'
        "<h2>Matching feedback by category</h2>"
        f"<p>{desc}</p></div></div>{crumb}{chart}</div>"
    )


def render_journey_chart(rows: list[tuple[str, int]]) -> str:
    """Stages ordered by volume, highest first.

    Journey order is still what the caller passes in, and it decides ties, so
    two stages on the same count stay in the order a user meets them. Stages
    with no feedback are kept rather than dropped -- an empty stage is a
    finding, and sorting must not turn it into a missing row.
    """
    ordered = sorted(rows, key=lambda row: -row[1])
    return (
        '<div class="afi-card afi-section" style="box-shadow:none;margin-top:20px">'
        '<div class="afi-section-head"><div>'
        "<h2>Matching feedback by Journey stage</h2>"
        "<p>Ordered by volume, highest first. Stages with no feedback are "
        "kept, not dropped.</p></div></div>"
        + _bar_rows(ordered, None)
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
    for index, r in enumerate(records):
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
        # A reader must be able to tell a human label from a model one, so an
        # edited record says so on its face rather than only in the file.
        if r.get("manually_edited"):
            meta.append('<span class="afi-badge b-green">Labels edited by a '
                        "reviewer</span>")

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
            f'<div class="afi-feedback-foot">'
            f'<a class="afi-source" target="_blank" '
            f'href="{_esc(r["source_url"])}">Open original source ↗</a>'
            f'<a class="afi-edit-link" {_click(f"{NAV_EDIT}_{index}")}>'
            f"Edit labels</a></div>"
            "</div>"
        )
    out.append("</div>")
    return "".join(out)


def render_severity_slider(value: int, minimum: int = 1, maximum: int = 5) -> str:
    """The mockup's severity control: a native range input with a value pill.

    Streamlit's own slider is not used here. Its thumb rendered at left:100%
    while reporting value 1, so the handle sat at the maximum end for the
    minimum value and the control read right-to-left. A native input is also
    what the mockup specifies, so replacing it fixes the behaviour and the
    appearance in one move.

    The input proxies to hidden Streamlit buttons, one per severity level --
    the same mechanism the chart rows and action buttons already use.
    """
    return (
        '<div class="afi-sev">'
        '<div class="afi-range-row">'
        f"<span>{minimum}</span>"
        f'<output class="afi-range-value">{value}</output>'
        f"<span>{maximum}</span>"
        "</div>"
        f'<input type="range" min="{minimum}" max="{maximum}" step="1" '
        f'value="{value}" data-afi-sev="{NAV_SEV}" '
        'aria-label="Minimum severity" />'
        "</div>"
    )


def render_filter_state(shown: int, total: int, open_count: int,
                        min_severity: int, focus: str | None = None) -> str:
    """The line above the records, stating what narrowed them.

    When an action is selected it names that action and offers a way back, so
    the reader can always tell why they are seeing fewer records than the
    filters alone would give.
    """
    focused = (f" · showing the evidence for <b>{_esc(focus)}</b>"
               if focus else "")
    back = (
        f'<a class="afi-focus-back" {_click(NAV_UNFOCUS)}>← Back to filtered view</a>'
        if focus else ""
    )
    return (
        '<div class="afi-filter-state-row">'
        f'<p class="afi-filter-state">Showing {shown} of {total} in-scope records · '
        f"{open_count} open · severity {min_severity}+{focused}</p>{back}</div>"
    )
