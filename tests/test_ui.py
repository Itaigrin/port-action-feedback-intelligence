"""Dashboard UI contract.

These guard the whitelist and the layout, so a legacy section cannot creep back
onto the Dashboard and the mockup's structure cannot silently drift.

All offline: the renderers return markup, so nothing here needs a running
server or an API key.

    python -m pytest tests/test_ui.py -v
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

APP = (ROOT / "app.py").read_text(encoding="utf-8")
THEME = (ROOT / "src" / "ui" / "theme.py").read_text(encoding="utf-8")
RENDER_SRC = (ROOT / "src" / "ui" / "render.py").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def records() -> list[dict]:
    data = json.loads(
        (ROOT / "data" / "processed" / "analyzed.json").read_text(encoding="utf-8"))
    return [r for r in data["records"] if r["is_relevant"]]


@pytest.fixture(scope="module")
def aggregates() -> dict:
    return json.loads(
        (ROOT / "data" / "processed" / "aggregates.json").read_text(encoding="utf-8"))


# --- whitelist -------------------------------------------------------------
ALLOWED_DASHBOARD_HEADINGS = {
    "Action Configuration feedback",
    "Turn feedback into decisions that retain the original evidence.",
    "Evidence filters",
    "Product actions",
    "Open product actions",
    "High severity",
    "Needs human review",
    "Recommended product actions",
    "Matching feedback by taxonomy category",
    "Matching feedback by Journey stage",
    "Feedback behind recommended actions",
}

# Headings from the previous dashboard. Any of these reappearing means a legacy
# section was rendered again.
LEGACY_HEADINGS = (
    "Where the problems concentrate",
    "Where in the journey users get stuck",
    "What kind of problems these are",
    "Who is asking",
    "Primary owner vs. also implicated",
    "Evidence explorer",
    "How good is the AI classification?",
    "What to build next for Port Actions",
    "Executive summary",
    "Key insights",
    "How this works, and what it cannot tell you",
)


def _dashboard_source() -> str:
    """Only the dashboard half of app.py -- the Guide has its own headings."""
    start = APP.index("def render_dashboard(")
    end = APP.index("def render_guide(")
    return APP[start:end] + RENDER_SRC


def test_no_legacy_dashboard_headings():
    source = _dashboard_source()
    for heading in LEGACY_HEADINGS:
        assert heading not in source, f"legacy section still rendered: {heading}"


def test_dashboard_headings_are_whitelisted():
    headings = set(re.findall(r"<h[12][^>]*>([^<{]+)</h[12]>", _dashboard_source()))
    headings |= set(re.findall(r'"(?:#+ )?([A-Z][^"<{]{6,60})</h2>', _dashboard_source()))
    unexpected = {h.strip() for h in headings} - ALLOWED_DASHBOARD_HEADINGS
    assert not unexpected, f"non-whitelisted dashboard headings: {unexpected}"


def test_scope_filter_is_not_rendered():
    """The dashboard is permanently restricted to is_relevant == True."""
    for banned in ('"Scope"', "'Scope'", "All records", "General / out of scope"):
        assert banned not in APP, f"scope control present: {banned}"
    assert 'df[df["is_relevant"]]' in APP


def test_exactly_four_kpis_with_approved_labels():
    from src.ui.render import render_kpis

    html = render_kpis(54, 37, 23, 26)
    assert html.count('class="afi-card afi-kpi"') == 4
    for label in ("Product actions", "Open product actions",
                  "High severity", "Needs human review"):
        assert f">{label}<" in html


def test_no_legacy_kpi_rendered():
    from src.ui.render import render_kpis

    html = render_kpis(1, 1, 1, 1)
    for banned in ("Total votes", "Relevant feedback", "Average confidence",
                   "Completed demand", "Total sources", "Matching feedback",
                   "Feedback records analysed", "In scope for Action Configuration"):
        assert banned not in html, f"legacy KPI rendered: {banned}"


def test_chart_titles_are_exact():
    from src.ui.render import render_journey_chart, render_taxonomy_chart

    assert "<h2>Matching feedback by taxonomy category</h2>" in \
        render_taxonomy_chart([("A", 1)], None)
    assert "<h2>Matching feedback by Journey stage</h2>" in \
        render_journey_chart([("A", 1)])


def test_no_old_theme_chart_and_no_plotly():
    """The mockup's charts are CSS bars; Plotly would fight the surrounding design."""
    assert "plotly" not in APP.lower()
    assert "plotly" not in RENDER_SRC.lower()
    assert "primary_theme" not in APP
    assert "afi-bar" in THEME


def test_journey_chart_keeps_chronological_order():
    from src.models.taxonomy import STAGE_NAMES
    from src.ui.render import render_journey_chart

    from html import escape

    rows = [(name, i) for i, name in enumerate(STAGE_NAMES)]
    html = render_journey_chart(rows)
    positions = [html.index(f"<strong>{escape(name, quote=True)}</strong>")
                 for name in STAGE_NAMES]
    assert positions == sorted(positions), "journey stages were reordered"


def test_dashboard_section_order():
    source = APP[APP.index("def render_dashboard("):APP.index("def render_guide(")]
    order = [
        "render_hero",
        "render_kpis",
        "render_product_actions",
        "render_taxonomy_chart",
        "render_journey_chart",
        "Feedback behind recommended actions",
        "render_feedback_cards",
    ]
    positions = [source.index(token) for token in order]
    assert positions == sorted(positions), f"sections out of order: {order}"


def test_category_and_subcategory_are_separate_controls():
    assert 'st.multiselect("Taxonomy category"' in APP
    assert 'st.multiselect("Taxonomy subcategory"' in APP


def test_top_recommended_actions_defaults_to_ten():
    from app import DEFAULT_TOP_ACTIONS  # noqa: PLC0415

    assert DEFAULT_TOP_ACTIONS == 10
    assert "value=DEFAULT_TOP_ACTIONS" in APP


def test_filter_panel_order_matches_the_mockup():
    """Order is checked by position in the panel, not by widget call.

    "Minimum severity" is no longer a Streamlit widget -- it is the mockup's
    native range input -- so scanning only st.* calls would silently skip it.
    """
    panel = APP[APP.index("def render_filter_panel("):APP.index("def apply_filters(")]
    expected = ["Lifecycle status", "Problem type", "Journey stage",
                "Taxonomy category", "Taxonomy subcategory", "Minimum severity",
                "Top Recommended product actions", "Reset all filters",
                "More filters", "Persona", "Confidence / review state",
                "View full taxonomy"]
    # "Minimum severity" sits inside an HTML label, not a quoted widget arg.
    positions = [panel.index(label) for label in expected]
    assert positions == sorted(positions), (
        "filter panel is out of order: "
        + str(sorted(zip(positions, expected))))


def test_severity_uses_the_mockup_range_not_the_streamlit_slider():
    """Streamlit's slider rendered its thumb at left:100% for value 1.

    The handle sat at the maximum end for the minimum value, so the control
    read right-to-left. The mockup specifies a native range input, which fixes
    the direction and the appearance together.
    """
    from src.ui.render import NAV_SEV, render_severity_slider

    assert 'st.slider("Minimum severity"' not in APP, "the broken slider is back"
    assert "st.slider(" not in APP

    html = render_severity_slider(3)
    assert 'type="range"' in html
    assert 'min="1"' in html and 'max="5"' in html and 'value="3"' in html
    assert f'data-afi-sev="{NAV_SEV}"' in html
    assert 'aria-label="Minimum severity"' in html
    # The value row reads low, current, high -- left to right, as in the mockup.
    low = html.index("<span>1</span>")
    pill = html.index("afi-range-value")
    high = html.index("<span>5</span>")
    assert low < pill < high

    # One hidden button per level, and the CSS pins direction explicitly.
    for level in range(1, 6):
        assert f'f"{{render.NAV_SEV}}_{{level}}"' in APP or NAV_SEV in APP
    assert "direction: ltr" in THEME


def test_feedback_cards_show_source_status_and_created_date_separately(records):
    from src.ui.render import render_feedback_cards

    record = next(r for r in records if r.get("created_at"))
    html = render_feedback_cards([record])
    assert f'>{record["source_system"]}<' in html
    assert f'>{record["lifecycle_status"]}<' in html
    assert f'>{record["created_at"][:10]}<' in html
    assert "Recommended product action" in html
    assert "Open original source" in html


def test_feedback_cards_hide_banned_metadata(records):
    from src.ui.render import render_feedback_cards

    html = render_feedback_cards(records[:20])
    for banned in ("votes", "priority_score", "prompt_version", "model_name",
                   "cache", "Theme:"):
        assert banned not in html, f"banned metadata rendered: {banned}"


def test_comparison_panel_removed():
    """Removed from the dashboard as a product decision, not merely hidden."""
    import src.ui.render as render_mod

    assert not hasattr(render_mod, "render_comparison_panel")
    assert "render_comparison_panel" not in APP
    assert "flat-theme dashboard" not in APP
    assert "flat-theme dashboard" not in RENDER_SRC
    # Check the rendered stylesheet, not the source text: a comment mentioning
    # the removal is fine, a surviving rule is not.
    from src.ui.theme import CSS

    assert ".afi-why" not in CSS


def test_guide_still_uses_the_two_column_compare_block():
    """The shared .afi-comparison styling must survive the panel's removal."""
    assert ".afi-comparison" in THEME
    guide = APP[APP.index("def render_guide("):]
    assert 'class="afi-comparison"' in guide


def test_guide_is_a_separate_view():
    assert "def render_guide(" in APP
    assert 'st.tabs(\n        ["Dashboard", "Themes & Journey Stages Guide"])' in APP
    # Guide-only content must not appear in the dashboard half.
    dashboard = APP[APP.index("def render_dashboard("):APP.index("def render_guide(")]
    for guide_only in ("Glossary", "Worked examples", "Commonly confused pairs"):
        assert guide_only not in dashboard


def test_responsive_breakpoints_present():
    assert "@media (max-width: 1050px)" in THEME
    assert "@media (max-width: 650px)" in THEME
    assert "overflow-x: hidden" in THEME


def test_design_tokens_match_the_mockup():
    from src.ui import theme

    assert (theme.BG, theme.INK, theme.MUTED) == ("#f3f6fb", "#182330", "#64748b")
    assert (theme.BLUE, theme.GREEN, theme.AMBER) == ("#2764e7", "#087b61", "#aa6100")
    assert (theme.RED, theme.PURPLE, theme.LINE) == ("#c43e3e", "#6d43b8", "#e2e8f0")
    assert "height: 64px" in theme.CSS          # top bar
    assert "max-width: 1500px" in theme.CSS     # page width
    assert "270px" in theme.CSS                 # filter rail


def test_streamlit_defaults_are_neutralised():
    for rule in ('header[data-testid="stHeader"] {{ display: none',
                 '[data-testid="stSidebar"] {{ display: none'):
        assert rule in THEME, rule


def test_ui_renders_pipeline_data_not_hardcoded_markup(records):
    """The UI must build every card from analyzed.json, not from fixed markup.

    Note the mockup's sample records are themselves real roadmap.port.io posts,
    not invented ones, so overlapping titles are expected and are not evidence
    of anything leaking. What matters is the mechanism: no record content may be
    literal in the source, and a rendered card must reproduce the values held in
    the classified dataset.
    """
    for source in (APP, RENDER_SRC):
        assert 'class="feedback" data-' not in source, "static record markup found"
        assert "data-severity=" not in source
        assert "data-confidence=" not in source

    from src.ui.render import render_feedback_cards

    record = records[0]
    html = render_feedback_cards([record])
    assert record["title"] in html
    assert record["suggested_product_action"] in html
    assert record["source_url"] in html
    # A record the dataset does not contain cannot appear.
    assert "Add Vault runtime resolution" not in html


def test_page_starts_without_an_api_key():
    assert "import anthropic" not in APP
    assert "ANTHROPIC_API_KEY" not in APP


# --- interaction regressions ----------------------------------------------
def test_interactions_do_not_navigate_the_browser():
    """Every in-panel control must trigger a rerun, not a page load.

    The controls were query-parameter anchors first. They worked, but each
    click was a real navigation: the browser tore the page down and Streamlit's
    shell repainted, which showed as a black flash and a moment of unstyled
    content. They now proxy to hidden Streamlit buttons.
    """
    from src.models.taxonomy import CATEGORY_NAMES
    from src.ui.render import (
        NAV_BACK,
        NAV_DRILL,
        NAV_FOCUS,
        NAV_SUB,
        NAV_UNFOCUS,
        render_product_actions,
        render_taxonomy_chart,
    )

    action = {
        "category": "Permissions & Approvals",
        "subcategory": "RBAC & dynamic permissions",
        "product_action": "Enforce RBAC on run pages.",
        "open_records": 3, "avg_severity": 3.0, "max_severity": 4,
        "source_diversity": 1, "needs_review": 0, "signal": "quote",
    }
    blocks = [
        render_taxonomy_chart([(c, 1) for c in CATEGORY_NAMES], None),
        render_taxonomy_chart([("RBAC & dynamic permissions", 1)],
                              "Permissions & Approvals"),
        render_product_actions([action], 10),
    ]
    for html in blocks:
        # No anchor may carry a real destination.
        for href in re.findall(r'href="([^"]*)"', html):
            assert href == "#", f"navigating link found: {href}"
        assert "target=" not in html
        assert "data-afi-click=" in html

    keys = {k for html in blocks
            for k in re.findall(r'data-afi-click="([^"]+)"', html)}
    assert f"{NAV_DRILL}_0" in keys
    assert f"{NAV_SUB}_0" in keys
    assert f"{NAV_FOCUS}_0" in keys
    assert NAV_BACK in keys

    # Every proxied key must be one app.py actually creates a button for.
    for key in keys:
        stem = re.sub(r"_\d+$", "", key)
        assert stem in (NAV_DRILL, NAV_SUB, NAV_FOCUS, NAV_BACK, NAV_UNFOCUS), key
    # app.py builds the drill/sub keys from the same constants.
    assert "render.NAV_SUB if drilled else render.NAV_DRILL" in APP
    assert "render.NAV_BACK" in APP and "render.NAV_UNFOCUS" in APP
    assert "render.NAV_FOCUS" in APP


def test_hidden_nav_buttons_are_created_for_every_proxy():
    """The forwarder is installed once and the buttons use on_click callbacks."""
    assert "def render_hidden_nav(" in APP
    assert "CLICK_FORWARDER" in APP
    assert "__afiClickBound" in APP, "listener must guard against double binding"
    # Every handler must exist and be wired as a callback -- callbacks run
    # before widgets are created, which is what makes their state writes legal.
    for handler in ("_drill_into", "_clear_drill", "_select_subcategory",
                    "_focus_on", "_clear_focus"):
        assert f"def {handler}(" in APP, handler
    # drill vs subcategory is chosen into `handler` before the button call.
    assert "handler = _select_subcategory if drilled else _drill_into" in APP
    for wired in ("on_click=handler", "on_click=_clear_drill",
                  "on_click=_clear_focus", "on_click=_focus_on"):
        assert wired in APP, wired
    assert "st.rerun()" not in APP, "callbacks rerun on their own"


def test_markdown_negative_margin_is_neutralised():
    """Streamlit pulls the next block up by 14px over a trailing <p> margin.

    Our blocks set margin:0 on that <p>, so the pull-back had nothing to cancel
    and dragged the filter-state line into the section caption.
    """
    from src.ui.theme import CSS

    assert '.st-key-afi_page [data-testid="stMarkdownContainer"]' in CSS
    marker = CSS.index('.st-key-afi_page [data-testid="stMarkdownContainer"]')
    assert "margin-bottom: 0 !important" in CSS[marker:marker + 160]


def test_feedback_section_carries_the_scroll_anchor():
    from src.ui.render import FEEDBACK_ANCHOR, render_feedback_cards

    record = {
        "title": "t", "source_system": "Port portal", "lifecycle_status": "Open",
        "created_at": "2026-01-01T00:00:00Z", "confidence": 0.9, "persona": "Unknown",
        "needs_human_review": False, "primary_taxonomy_category": "Orchestration",
        "primary_taxonomy_subcategory": "Timeouts", "secondary_categories": [],
        "problem_type": "Feature gap", "journey_stage": "Timeouts",
        "suggested_product_action": "do", "evidence_excerpt": "q",
        "evidence_verified": True, "severity": 3, "source_url": "https://x",
    }
    assert f'id="{FEEDBACK_ANCHOR}"' in render_feedback_cards([record])


def test_reset_assigns_defaults_and_never_mutates_state_mid_render():
    """Guards the two failure modes the Reset button actually hit.

    Assigning a widget key after its widget exists raises StreamlitAPIException;
    deleting the key instead leaves the browser showing stale selections. The
    reset therefore runs as an on_click callback and assigns defaults.
    """
    from app import DEFAULT_TOP_ACTIONS, FILTER_DEFAULTS

    assert "on_click=_reset_filters" in APP
    assert "st.rerun()" not in APP.split("def _reset_filters")[1].split("def ")[1]

    for key in ("f_status", "f_problem", "f_stage", "f_category", "f_subcategory",
                "f_persona", "f_review", "f_search", "f_severity", "f_top_n"):
        assert key in FILTER_DEFAULTS, f"{key} would survive a reset"
    assert FILTER_DEFAULTS["f_severity"] == 1
    assert FILTER_DEFAULTS["f_top_n"] == DEFAULT_TOP_ACTIONS
    # Deleting is what caused the frontend desync; every default is a value.
    assert all(v is not None for v in FILTER_DEFAULTS.values())


def test_category_click_does_not_rewrite_the_filters():
    """A drill-down must not silently discard the selection the reader built."""
    panel = APP[APP.index("def render_filter_panel("):APP.index("def apply_filters(")]
    assert 'setdefault("f_category"' not in panel
    assert 'params["cat"]' not in panel


def test_streamlit_theme_matches_the_mockup_tokens():
    """The reload flash must not be a different colour from the loaded page."""
    from src.ui import theme

    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert f'backgroundColor = "{theme.BG}"' in config
    assert f'textColor = "{theme.INK}"' in config
    assert f'primaryColor = "{theme.BLUE}"' in config


def test_action_card_never_renders_its_own_evidence():
    """The card selects; the feedback section is the only place records list.

    One rendering path for a feedback record means the card's count and the
    list below it cannot drift apart.
    """
    from src.ui.render import render_product_actions

    action = {
        "category": "Permissions & Approvals",
        "subcategory": "RBAC & dynamic permissions",
        "product_action": "Enforce RBAC on run pages.",
        "open_records": 2, "avg_severity": 3.0, "max_severity": 4,
        "source_diversity": 1, "needs_review": 0, "signal": "quote",
    }

    plain = render_product_actions([action], 10)
    assert "afi-action-evidence" not in plain
    assert "afi-feedback" not in plain, "no record markup belongs in a card"
    assert "View supporting feedback" in plain

    selected = render_product_actions([action], 10, selected=action["subcategory"])
    assert "afi-feedback" not in selected, "selecting must not expand anything"
    assert "is-selected" in selected, "the chosen card should be identifiable"
    assert 'aria-current="true"' in selected


def test_selecting_an_action_narrows_the_feedback_section():
    """The button feeds the section's existing filter, not a second mechanism."""
    import inspect

    from src.ui.render import render_filter_state

    assert "focus" in inspect.signature(render_filter_state).parameters
    html = render_filter_state(10, 182, 10, 1, focus="RBAC & dynamic permissions")
    assert "showing the evidence for" in html
    assert "RBAC &amp; dynamic permissions" in html
    assert "afi-focus-back" in html, "a way back out is required"

    # Unselected, the line is plain and offers no way back.
    plain = render_filter_state(182, 182, 155, 1)
    assert "showing the evidence for" not in plain
    assert "afi-focus-back" not in plain


def test_selection_drives_the_section_and_scrolls_to_it():
    assert 'st.session_state["afi_focus"] = subcategory' in APP
    assert 'selected_action["record_ids"]' in APP,         "the section must show the records the action was ranked from"
    assert "render.render_product_actions(" in APP
    assert "selected=focus" in APP
    # The jump targets the section container, not a card.
    assert "querySelector('.st-key-afi_feedback')" in APP
    assert "scrollIntoView" in APP


def test_filter_rail_has_no_internal_scrollbar():
    """Expanding a filter section should grow the rail, not scroll inside it."""
    from src.ui.theme import CSS

    marker = CSS.index(".st-key-afi_rail {")
    rule = CSS[marker:CSS.index("}", marker)]
    # Strip comments: the rule documents why the cap was removed.
    declarations = re.sub(r"/\*.*?\*/", "", rule, flags=re.S)
    assert "max-height" not in declarations, "a capped rail scrolls internally"
    assert "overflow-y: auto" not in declarations
    assert "overflow: visible" in declarations


def test_section_shows_exactly_the_records_behind_the_selected_action(
        records, aggregates):
    """The section must list the records the action was ranked from.

    Filtering by subcategory instead would show completed work beneath a card
    reading "N open supporting records", so the list would contradict its own
    count.
    """
    assert 'view["feedback_id"].isin(' in APP

    from src.models.taxonomy import OPEN_STATUSES

    by_id = {r["feedback_id"]: r for r in records}
    for action in aggregates["product_actions"][:10]:
        supporting = [by_id[i] for i in action["record_ids"]]
        assert len(supporting) == action["open_records"]
        for record in supporting:
            assert record["lifecycle_status"] in OPEN_STATUSES


def test_sidebar_ranking_note_is_generated_from_the_ranking_keys(aggregates):
    """The note must be built from RANK_KEYS, not hand-copied.

    A prose paraphrase of the ranking would drift the first time the keys
    change, and the sidebar is exactly where a reader decides whether to trust
    the order.
    """
    from src.analysis.aggregate import RANK_KEYS

    # Rendered from the code, not from aggregates.json. That artifact is
    # regenerated by the pipeline, so a deploy pairing new code with an older
    # artifact used to raise KeyError on a field the old file never had.
    # (the runtime-dependency check lives in its own test below, which matches
    # the actual read rather than any mention of the filename)
    assert "RANK_KEYS" in APP, "note must read the live key list"
    assert "afi-rank-note" in APP and "afi-rank-note" in THEME
    assert "How the list is ordered" in APP
    # The claims the note makes must still hold.
    assert "still open" in APP
    assert [k for k, *_ in RANK_KEYS] == [
        e["key"] for e in aggregates["ranking"]["keys"]]

    # The rail shows plain labels, never field names -- "severity_band" in a
    # sidebar is accurate and useless to the reader it is written for.
    assert "for _key, label, _why in RANK_KEYS" in APP
    for field, label, _ in RANK_KEYS:
        assert label and not label.islower() or " " in label, field
        assert f">{field}<" not in APP, f"raw field name shown in the rail: {field}"


def test_critical_actions_are_badged():
    """The severity chip rounds; the gate does not. Without a badge, an action
    averaging 3.5 reads "Severity 4" yet ranks below one that cleared the gate,
    and the order looks arbitrary."""
    from src.ui.render import render_product_actions

    base = {
        "category": "Permissions & Approvals",
        "subcategory": "RBAC & dynamic permissions",
        "product_action": "Enforce RBAC.", "open_records": 10,
        "avg_severity": 3.5, "max_severity": 5, "source_diversity": 1,
        "needs_review": 0, "signal": "quote", "is_critical": 0,
    }
    not_gated = render_product_actions([base], 10)
    assert ">Critical<" not in not_gated
    assert "Severity 4" in not_gated, "the chip still rounds 3.5 up"

    gated = render_product_actions([dict(base, is_critical=1)], 10)
    assert ">Critical<" in gated


def test_scroll_fires_on_every_selection_not_just_the_first():
    """The scroll component must be a new element on each click.

    Streamlit reuses an element whose content is unchanged. The scroll markup
    does not mention which action is selected, so without a varying value the
    iframe was never remounted after the first click and the script never ran
    again: the selection and the section updated, but the page did not move.
    """
    focus_fn = APP[APP.index("def _focus_on("):APP.index("def _clear_focus(")]
    assert 'st.session_state["afi_scroll_nonce"]' in focus_fn, (
        "every press must bump the nonce, including a repeat press")

    # The nonce must reach the rendered markup, or it changes nothing.
    block = APP[APP.index("nonce = st.session_state.get"):]
    block = block[:block.index("height=0")]
    assert "{nonce}" in block, "the component content must vary per click"
    assert block.lstrip().startswith("nonce = st.session_state.get")

    # And it must be read back with a default, so a first render cannot crash.
    assert 'st.session_state.get("afi_scroll_nonce", 0)' in APP


def test_app_does_not_read_the_aggregates_artifact_at_runtime():
    """The dashboard must run on the records plus this code, nothing else.

    aggregates.json is regenerated by the pipeline. Reading presentation text
    out of it meant a deploy that shipped new code alongside an older artifact
    crashed with KeyError on a field the old file did not have. The app now
    recomputes actions from the records and takes labels from RANK_KEYS, so
    that class of failure is gone.
    """
    assert 'PROC / "aggregates.json"' not in APP
    assert 'agg["ranking"]' not in APP
    assert "RANK_KEYS" in APP

    # Every ranking key must supply a label, or the rail renders a blank item.
    from src.analysis.aggregate import RANK_KEYS

    for entry in RANK_KEYS:
        assert len(entry) == 3, entry
        field, label, explanation = entry
        assert label.strip() and explanation.strip(), field
        assert "_" not in label, f"{field} label reads like a field name: {label}"
        # Labels lead with the readable field name, then the plain meaning.
        assert "—" in label, f"{field} label is missing its plain gloss: {label}"
