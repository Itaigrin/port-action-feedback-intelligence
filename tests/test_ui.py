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
    "Action Feedback Analyzer",
    "Filters",
    "Product actions",
    "Open product actions",
    "High severity",
    "Needs human review",
    "Recommended product actions",
    "Matching feedback by category",
    "Matching feedback by Journey stage",
    "Feedback behind recommended actions",
    "Where users struggle most",
    "Negative feedback by Journey stage - last 3 months",
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


def _growth(**overrides) -> dict:
    base = {"name": "Access control & action eligibility", "previous_average": 0.33,
            "last_week_count": 4, "absolute_increase": 3.67,
            "growth_pct": 1100.0, "is_new_spike": False, "has_data": True}
    base.update(overrides)
    return base


def test_exactly_four_kpis_with_approved_labels():
    """The original row, restored to exactly what it was before the trend
    cards existed: four cards, no fifth or sixth squeezed in."""
    from src.ui.render import render_kpis

    html = render_kpis(54, 37, 23, 26, total_feedback=185)
    assert html.count('class="afi-card afi-kpi"') == 4
    for label in ("Product actions", "Open product actions",
                  "High severity", "Needs human review"):
        assert f">{label}<" in html
    assert "out of 185 feedback responses" in html


def test_no_legacy_kpi_rendered():
    from src.ui.render import render_kpis

    html = render_kpis(1, 1, 1, 1, total_feedback=1)
    for banned in ("Total votes", "Relevant feedback", "Average confidence",
                   "Completed demand", "Total sources", "Matching feedback",
                   "Feedback records analysed", "In scope for Action Configuration"):
        assert banned not in html, f"legacy KPI rendered: {banned}"


def test_trend_row_has_exactly_two_cards_journey_stage_first():
    from src.ui.render import render_trend_cards

    html = render_trend_cards(fastest_stage=_growth(name="Backend & invocation setup"),
                              fastest_subcategory=_growth(name="Access control & action eligibility"))
    assert html.count("afi-kpi-growth") == 2
    assert "Largest increase in negative feedback - Journey Stage" in html
    assert "Largest increase in negative feedback - Subcategory" in html
    # Left card is the stage, right card is the subcategory -- a fixed
    # reading order, so this checks position, not which one "won".
    assert html.index("Journey Stage") < html.index("Backend &amp; invocation setup")
    assert (html.index("Backend &amp; invocation setup")
            < html.index("Access control &amp; action eligibility"))


def test_growth_card_shows_the_absolute_increase_in_red_with_pct_as_context():
    from src.ui.render import render_growth_kpi

    html = render_growth_kpi("T", _growth())
    assert "Access control &amp; action eligibility" in html, "names must be escaped"
    assert "Prev 3-week avg: <b>0.33</b>" in html
    assert "Last full week: <b>4</b>" in html
    assert '<b class="afi-growth-increase">+3.67</b>' in html
    assert '<span class="afi-growth-pct">+1100%</span>' in html


def test_a_zero_baseline_reads_new_spike_with_the_increase_and_no_percent():
    from src.ui.render import render_growth_kpi

    html = render_growth_kpi("T", _growth(previous_average=0.0, growth_pct=None,
                                          is_new_spike=True, last_week_count=1,
                                          absolute_increase=1.0))
    assert "New spike" in html
    assert '<b class="afi-growth-increase">+1</b>' in html
    assert "%" not in html, "a ratio against zero must never print as one"


def test_growth_card_has_a_compact_empty_state():
    from src.ui.render import render_growth_kpi

    html = render_growth_kpi("T", {"has_data": False})
    assert "No recent negative trend" in html
    assert "Prev 3-week avg" not in html


def test_the_increase_is_red_and_the_trend_row_cannot_overflow():
    """minmax(0, 1fr) is load-bearing: a grid track defaults to min-width
    auto, so one long unbroken subcategory name would widen its column and
    push the whole row past the page instead of wrapping inside its card."""
    assert ".afi-growth-increase" in THEME and "color: var(--red)" in THEME
    assert "repeat(2, minmax(0, 1fr))" in THEME
    assert "overflow-wrap: anywhere" in THEME


def test_trend_row_stacks_on_small_screens():
    tablet = THEME[THEME.index("@media (max-width: 1050px)"):
                   THEME.index("@media (max-width: 650px)")]
    mobile = THEME[THEME.index("@media (max-width: 650px)"):]
    assert ".afi-trend-row" in tablet and ".afi-trend-row" in mobile


def test_kpi_row_dimensions_are_untouched_by_the_trend_row():
    """The four-card row's own CSS must read exactly as it did before the
    trend cards existed -- restored, not just visually similar."""
    assert ".afi-kpis {" in THEME
    block = THEME[THEME.index(".afi-kpis {"):THEME.index(".afi-kpis {") + 200]
    assert "repeat(4, 1fr)" in block
    assert "minmax(0" not in block, "the 5-column fix must not linger here"


def test_chart_titles_are_exact():
    from src.ui.render import render_journey_chart, render_taxonomy_chart

    assert "<h2>Matching feedback by category</h2>" in \
        render_taxonomy_chart([("A", 1)], None)
    assert "<h2>Matching feedback by Journey stage</h2>" in \
        render_journey_chart([("A", 1)])


def test_no_old_theme_chart_and_no_plotly():
    """Charts are CSS bars and one inline SVG line chart.

    Re-adding Plotly for the trend chart would bring back every canvas,
    toolbar, font and margin conflict that removing it solved, so the line
    chart is hand-drawn SVG in the same design language.
    """
    for source in (APP, RENDER_SRC):
        assert "import plotly" not in source
        assert "plotly.express" not in source
        assert "plotly.graph_objects" not in source
    assert "afi-trend-svg" in THEME, "the trend chart is inline SVG"
    assert "primary_theme" not in APP
    assert "afi-bar" in THEME


def _stage_positions(html: str, names) -> list[int]:
    from html import escape

    return [html.index(f"<strong>{escape(name, quote=True)}</strong>")
            for name in names]


def test_journey_chart_orders_stages_by_lifecycle_order():
    """The order a user actually meets the stages in, not ranked by volume.

    Counts are deliberately scrambled (highest count on the last stage) so a
    test that still sorted by volume would fail here.
    """
    from src.models.taxonomy import STAGE_NAMES
    from src.ui.render import render_journey_chart

    rows = [(name, len(STAGE_NAMES) - i) for i, name in enumerate(STAGE_NAMES)]
    html = render_journey_chart(rows)
    positions = _stage_positions(html, STAGE_NAMES)
    assert positions == sorted(positions), (
        "stages must render in STAGE_NAMES order regardless of count")


def test_journey_chart_never_reorders_on_a_tie():
    """Equal counts keep the order a user meets the stages in."""
    from src.models.taxonomy import STAGE_NAMES
    from src.ui.render import render_journey_chart

    rows = [(name, 4) for name in STAGE_NAMES]
    html = render_journey_chart(rows)
    positions = _stage_positions(html, STAGE_NAMES)
    assert positions == sorted(positions), "a tie reordered the stages"


def test_journey_chart_keeps_empty_stages_in_place():
    """An empty stage is a finding; it must stay at its own lifecycle
    position, not be dropped or promoted by whichever stage has records.
    """
    from src.models.taxonomy import STAGE_NAMES
    from src.ui.render import render_journey_chart

    rows = [(name, 0) for name in STAGE_NAMES]
    rows[3] = (STAGE_NAMES[3], 9)
    html = render_journey_chart(rows)
    positions = _stage_positions(html, STAGE_NAMES)
    assert len(positions) == len(STAGE_NAMES)
    assert positions == sorted(positions), (
        "the populated stage must stay at its own lifecycle position")


def test_dashboard_section_order():
    source = APP[APP.index("def render_dashboard("):APP.index("def render_guide(")]
    order = [
        "render_hero",
        "render_kpis",
        "render_trend_cards",
        "render_insight_cards",
        "render_trend_chart",
        "render_product_actions",
        "render_taxonomy_chart",
        "render_journey_chart",
        "Feedback behind recommended actions",
        "render_feedback_cards",
    ]
    positions = [source.index(token) for token in order]
    assert positions == sorted(positions), f"sections out of order: {order}"


def test_category_and_subcategory_are_separate_controls():
    assert 'st.multiselect("Category"' in APP
    assert 'st.multiselect("Subcategory"' in APP


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
                "Category", "Subcategory", "Minimum severity",
                "Top Recommended product actions", "Reset all filters",
                "More filters", "Persona", "Confidence / review state",
                "View full Category - Subcategory"]
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
    # No current-value pill: the thumb's own position is the only indicator.
    assert "afi-range-value" not in html
    # A ruler tick for every step, low to high, left to right.
    positions = [html.index(f"<span>{n}</span>") for n in range(1, 6)]
    assert positions == sorted(positions)

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
    assert "What this record asks for" in html
    assert "Open original source" in html


def test_a_feedback_card_does_not_claim_to_be_the_recommendation():
    """The per-record ask and the group's recommendation are different things.

    Both were labelled "Recommended product action". That read as one thing
    while groups were formed by text similarity -- the group's title was
    literally one member's sentence, so the two matched. Curated grouping
    merges records whose wording differs, and a card headed "Support delegated
    and per-request authentication" then opened onto four records each
    announcing a different "Recommended product action", which reads as a
    mismatch rather than as the evidence behind the merge.
    """
    from src.ui.render import render_feedback_cards, render_product_actions

    card = render_feedback_cards([{
        "feedback_id": "x", "title": "t", "severity": 3,
        "source_system": "Port portal", "lifecycle_status": "Open",
        "created_at": "2026-01-01", "confidence": 0.9, "persona": "Action builder",
        "primary_taxonomy_category": "Identity, Secrets & Security",
        "primary_taxonomy_subcategory": "Authentication, execution identity & requester context",
        "problem_type": "Feature gap", "journey_stage": "Backend & invocation setup",
        "suggested_product_action": "Support per-user delegated OAuth2 execution",
        "source_url": "https://roadmap.port.io/ideas/p/x",
        "evidence_verified": False, "needs_human_review": False,
    }])
    assert "What this record asks for" in card
    # The singular group-level phrase must not appear on a record card.
    assert ">Recommended product action<" not in card


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
        NAV_INSIGHT,
        NAV_SUB,
        NAV_UNFOCUS,
        render_insight_cards,
        render_product_actions,
        render_taxonomy_chart,
    )

    action = {
        "product_action_id": "enforce-rbac-run-pages",
        "product_action_title": "Enforce RBAC on run pages.",
        "primary_categories": ["Permissions & Approvals"],
        "open_supporting_record_count": 3, "severity_band": 4,
        "source_diversity": 1, "needs_review": 0, "signal": "quote",
    }
    insight = {
        "group_type": "journey_stage", "group_name": "Permissions & approvals",
        "negative_feedback_count": 46, "recommended_focus": "Mostly feature gap.",
        "problem_type_ranking": ["feature gap"], "examples": [],
        "parent_category": "", "supporting_feedback_ids": ["a", "b"],
    }
    blocks = [
        render_taxonomy_chart([(c, 1) for c in CATEGORY_NAMES], None),
        render_taxonomy_chart([("Access control & action eligibility", 1)],
                              "Permissions & Approvals"),
        render_product_actions([action], 10),
        render_insight_cards(insight, dict(insight, group_type="subcategory")),
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
    assert f"{NAV_INSIGHT}_0" in keys and f"{NAV_INSIGHT}_1" in keys

    # Every proxied key must be one app.py actually creates a button for.
    for key in keys:
        stem = re.sub(r"_\d+$", "", key)
        assert stem in (NAV_DRILL, NAV_SUB, NAV_FOCUS, NAV_BACK, NAV_UNFOCUS,
                        NAV_INSIGHT), key
    # app.py builds the drill/sub keys from the same constants.
    assert "render.NAV_SUB if drilled else render.NAV_DRILL" in APP
    assert "render.NAV_BACK" in APP and "render.NAV_UNFOCUS" in APP
    assert "render.NAV_FOCUS" in APP
    assert "render.NAV_INSIGHT" in APP


def test_hidden_nav_buttons_are_created_for_every_proxy():
    """The forwarder re-registers itself every run, and buttons use on_click.

    Not "bound once, guarded against rebinding": that pattern goes silently
    dead the first time the surrounding layout reshapes between reruns (e.g.
    the filter rail collapsing removes a column), because the listener's
    closure lives in the components.html iframe that registered it, and
    Streamlit tears that iframe down and creates a new one when the layout
    around it changes shape. The fix is to replace the previous handler on
    every run rather than skip re-registering.
    """
    assert "def render_hidden_nav(" in APP
    assert "CLICK_FORWARDER" in APP
    assert "__afiClickHandler" in APP, (
        "listener must be re-registered every run, not bound once and left")
    assert "removeEventListener" in APP, (
        "the previous run's handler must be replaced, not merely shadowed")
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
    # Scoped to the navigation callbacks, which is what this rule is about: a
    # callback already reruns, so calling st.rerun() inside one is a second
    # run doing the same work. The label editor below them is exempt on
    # purpose -- a Streamlit dialog only closes on an explicit rerun.
    nav_block = APP[APP.index("def _drill_into("):APP.index("def _open_editor(")]
    assert "st.rerun()" not in nav_block, "nav callbacks rerun on their own"


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
        "primary_taxonomy_subcategory": "Reliability, timeouts & concurrency", "secondary_categories": [],
        "problem_type": "Feature gap", "journey_stage": "Execution, monitoring & run control",
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
        "product_action_id": "enforce-rbac-run-pages",
        "product_action_title": "Enforce RBAC on run pages.",
        "primary_categories": ["Permissions & Approvals"],
        "open_supporting_record_count": 2, "severity_band": 4,
        "source_diversity": 1, "needs_review": 0, "signal": "quote",
    }

    plain = render_product_actions([action], 10)
    assert "afi-action-evidence" not in plain
    assert "afi-feedback" not in plain, "no record markup belongs in a card"
    assert "View supporting feedback" in plain

    selected = render_product_actions([action], 10,
                                      selected=action["product_action_id"])
    assert "afi-feedback" not in selected, "selecting must not expand anything"
    assert "is-selected" in selected, "the chosen card should be identifiable"
    assert 'aria-current="true"' in selected


def test_selecting_an_action_narrows_the_feedback_section():
    """The button feeds the section's existing filter, not a second mechanism."""
    import inspect

    from src.ui.render import render_filter_state

    assert "focus" in inspect.signature(render_filter_state).parameters
    html = render_filter_state(10, 182, 10, 1, focus="Access control & action eligibility")
    assert "showing the evidence for" in html
    assert "Access control &amp; action eligibility" in html
    assert "afi-focus-back" in html, "a way back out is required"

    # Unselected, the line is plain and offers no way back.
    plain = render_filter_state(182, 182, 155, 1)
    assert "showing the evidence for" not in plain
    assert "afi-focus-back" not in plain


def test_selection_drives_the_section_and_scrolls_to_it():
    assert 'st.session_state["afi_focus"] = action_id' in APP
    assert "open_supporting_feedback_ids" in APP,         "the section must show the action's own supporting records"
    assert "evidence_for_action(" in APP, "drill-down must resolve by id"
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


def test_filter_rail_can_collapse_and_the_toggle_survives_it():
    """The collapse control exists in both states, and main fills the width
    the rail gave up rather than leaving a reserved gap.
    """
    assert "render_rail_toggle" in APP
    assert "afi_filters_collapsed" in APP
    # Collapsed: no rail column at all, not a rail shrunk to a sliver -- main
    # must be assigned the full-width container directly.
    assert re.search(r"main\s*=\s*page\b", APP), (
        "collapsed branch must hand main the whole page container")


def test_collapsing_the_rail_does_not_silently_reset_the_filters():
    """The bug this guards against: Streamlit prunes a widget-bound
    session_state entry at the end of any run that does not instantiate that
    widget. Collapsing the rail stops instantiating every filter widget, so
    reading their own keys (f_category, f_status, ...) after a collapse cycle
    returns whatever those widgets default to -- empty -- not what the reader
    selected. Verified by hand during development: a category filter set
    right before collapsing read back correctly for exactly one rerun, then
    silently reset the moment the rail reopened.

    The fix is a snapshot that is not tied to any widget's lifecycle, written
    every time the widgets render and read instead of the widget keys
    whenever they do not.
    """
    assert "FILTERS_SNAPSHOT_KEY" in APP
    assert "_filters_from_snapshot" in APP
    # Reading the raw widget keys directly for the collapsed path is exactly
    # the regression: that function must not exist.
    assert "_filters_from_session_state" not in APP
    # The snapshot has to be written from inside render_filter_panel (where
    # the widgets are read) and read from the collapsed branch -- not the
    # other way around, or there would be nothing to restore from.
    panel_start = APP.index("def render_filter_panel(")
    panel_end = APP.index("\ndef ", panel_start + 1)
    assert "FILTERS_SNAPSHOT_KEY] = " in APP[panel_start:panel_end], (
        "the panel must write the snapshot after reading its widgets")


def test_reopening_the_rail_restores_the_widgets_not_just_the_filtering():
    """Filtering staying correct while collapsed is necessary but not
    sufficient: the widgets themselves must also show the reader's previous
    selections when the rail reopens, or the UI contradicts what is actually
    being filtered on. This was the second half of the same bug -- fixed
    separately from the snapshot, because Streamlit widgets read their
    initial value from their own session_state key, not from a value handed
    to them at render time.
    """
    assert "_restore_filter_widget_keys" in APP
    # Must run before any filter widget is instantiated in the same function,
    # or setting the widget-bound keys raises StreamlitAPIException.
    panel_start = APP.index("def render_filter_panel(")
    first_widget = APP.index("st.multiselect(", panel_start)
    restore_call = APP.index("_restore_filter_widget_keys()", panel_start)
    assert restore_call < first_widget, (
        "restoring session_state after a widget already exists raises "
        "StreamlitAPIException")


def test_section_shows_exactly_the_records_behind_the_selected_action(
        records, aggregates):
    """The section must list the records the action was ranked from.

    Filtering by subcategory instead would show completed work beneath a card
    reading "N open supporting records", so the list would contradict its own
    count.
    """
    assert "evidence_for_action(" in APP

    from src.models.taxonomy import COUNTED_STATUSES

    by_id = {r["feedback_id"]: r for r in records}
    for action in aggregates["product_actions"][:10]:
        supporting = [by_id[i] for i in action["open_supporting_feedback_ids"]]
        assert len(supporting) == action["open_supporting_record_count"]
        for record in supporting:
            assert record["lifecycle_status"] in COUNTED_STATUSES


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
    assert "How the recommended product actions are ordered" in APP
    # The claims the note makes must still hold.
    assert "still open" in APP
    assert [k for k, *_ in RANK_KEYS] == [
        e["key"] for e in aggregates["ranking"]["keys"]]
    assert [k for k, *_ in RANK_KEYS][0] == "severity_band"

    # The rail shows plain labels, never field names -- "severity_band" in a
    # sidebar is accurate and useless to the reader it is written for.
    assert "for _key, label, _why in RANK_KEYS" in APP
    for field, label, _ in RANK_KEYS:
        assert label and not label.islower() or " " in label, field
        assert f">{field}<" not in APP, f"raw field name shown in the rail: {field}"


def test_scroll_fires_on_every_selection_not_just_the_first():
    """The scroll component must be a new element on each click.

    Streamlit reuses an element whose content is unchanged. The scroll markup
    does not mention which action is selected, so without a varying value the
    iframe was never remounted after the first click and the script never ran
    again: the selection and the section updated, but the page did not move.
    """
    focus_fn = APP[APP.index("def _focus_on("):APP.index("def _clear_focus(")]
    assert 'st.session_state["afi_scroll_nonce"]' in focus_fn, (
        "selecting an action must bump the nonce, including a press that "
        "moves the selection from one action to another")

    # The nonce must reach the rendered markup, or it changes nothing.
    block = APP[APP.index("nonce = st.session_state.get"):]
    block = block[:block.index("height=0")]
    assert "{nonce}" in block, "the component content must vary per click"
    assert block.lstrip().startswith("nonce = st.session_state.get")

    # And it must be read back with a default, so a first render cannot crash.
    assert 'st.session_state.get("afi_scroll_nonce", 0)' in APP


def test_the_jump_never_scrolls_an_overflow_hidden_ancestor():
    """scrollIntoView displaced the app shell and cut the page in half.

    It scrolls every scrollable ancestor, and overflow:hidden elements are
    still programmatically scrollable -- they just have no scrollbar to undo
    it. stAppViewContainer is overflow:hidden with ~5000px of content in a
    ~630px box, so each click pushed the whole app up with no way back.
    """
    block = APP[APP.index("nonce = st.session_state.get"):]
    block = block[:block.index("height=0")]
    assert "scrollIntoView" not in block, (
        "scrollIntoView also scrolls overflow:hidden ancestors")
    assert "scrollTo(" in block, "the jump must move one chosen scroller"
    # The scroller is found by walking for a real one, not by test id, so a
    # Streamlit rename degrades to no jump rather than to a broken page.
    assert "overflowY" in block and "scrollHeight > el.clientHeight" in block
    # And anything overflow:hidden that did get displaced is put back.
    assert "el.scrollTop = 0" in block


def test_the_jump_does_not_depend_on_smooth_scrolling_working():
    """behavior:'smooth' is a silent no-op in some embedded browsers.

    Found by driving the running app: the selection, the scoping and the
    nonce-forced remount all worked, the script ran, and the page simply did
    not move -- scrollTo returned normally and scrolled nothing, while a
    direct scrollTop assignment on the very same element worked. Every
    "scroll to the evidence" affordance was quietly dead there.

    So the jump verifies itself: if the scroller has not moved at all shortly
    after the request, it completes the jump instantly. Checking "did not move
    at all" rather than "has not arrived" is what keeps a genuine animation
    from being snapped mid-flight.
    """
    block = APP[APP.index("nonce = st.session_state.get"):]
    block = block[:block.index("height=0")]
    assert "scroller.scrollTop === from" in block, (
        "the jump must detect a smooth scroll that never started")
    assert "scroller.scrollTop = top" in block, (
        "and finish the jump itself when it did not")


def test_pressing_the_selected_action_again_clears_the_selection():
    """The button is a toggle, and its selected state must be readable.

    Both halves matter. Clearing has to happen before the assignment, or the
    early return can never be reached. And the selected label is painted on a
    blue fill, so it must stay white through :visited -- the button is an
    <a href="#">, which the browser treats as visited immediately, and the
    base .afi-action-btn:visited rule is otherwise specific enough to win.
    """
    # Sliced to _focus_on alone -- _focus_insight sits between it and
    # _clear_focus and sets the same keys, so a slice running to _clear_focus
    # would let one function's lines satisfy an assertion about the other's.
    focus_fn = APP[APP.index("def _focus_on("):APP.index("def _focus_insight(")]
    assert 'st.session_state.get("afi_focus") == action_id' in focus_fn
    assert focus_fn.index('st.session_state["afi_focus"] = None') < focus_fn.index(
        'st.session_state["afi_focus"] = action_id'), "the toggle must return early"

    assert ".afi-action-btn.is-selected:visited" in THEME, (
        "the selected label must survive the :visited rule")


def _insight(**over) -> dict:
    base = {
        "group_type": "journey_stage", "group_name": "Permissions & approvals",
        "negative_feedback_count": 46, "recommended_focus": "Mostly feature gap.",
        "problem_type_ranking": ["feature gap"], "examples": [],
        "parent_category": "", "supporting_feedback_ids": ["a", "b"],
    }
    return {**base, **over}


def test_the_insight_count_badge_is_a_control_that_keeps_its_number():
    """The badge scopes the evidence section, but stays a count.

    The number is the card's finding. Swapping it for a button label when
    selected -- the way the product-action button does -- would cost the
    reader the fact to gain nothing, so the selected state rides on styling
    and aria-current instead.
    """
    from src.ui.render import NAV_INSIGHT, render_insight_cards

    html = render_insight_cards(_insight(), _insight(group_type="subcategory"))
    assert f'data-afi-click="{NAV_INSIGHT}_0"' in html
    assert f'data-afi-click="{NAV_INSIGHT}_1"' in html
    assert "46 negative feedback records" in html
    assert "aria-current" not in html, "nothing is selected here"

    selected = render_insight_cards(_insight(), _insight(group_type="subcategory"),
                                    selected="journey_stage")
    assert 'aria-current="true"' in selected
    assert "is-selected" in selected
    # The count survives selection.
    assert "46 negative feedback records" in selected


def test_an_empty_insight_card_offers_no_control():
    """Nothing to scope to, so there must be nothing to press."""
    from src.ui.render import NAV_INSIGHT, render_insight_cards

    html = render_insight_cards(
        _insight(group_name="", negative_feedback_count=0,
                 supporting_feedback_ids=[]),
        _insight(group_type="subcategory"))
    assert f'data-afi-click="{NAV_INSIGHT}_0"' not in html
    assert f'data-afi-click="{NAV_INSIGHT}_1"' in html, "the other card still works"


def test_only_one_selection_can_scope_the_evidence_section():
    """A product action and an insight card are mutually exclusive.

    Both scope the same section, so two live selections would leave it showing
    one of them while both read as active on screen. Each setter drops the
    other, and clearing drops both.
    """
    focus_fn = APP[APP.index("def _focus_on("):APP.index("def _focus_insight(")]
    insight_fn = APP[APP.index("def _focus_insight("):APP.index("def _clear_focus(")]
    clear_fn = APP[APP.index("def _clear_focus("):
                   APP.index("def _toggle_filters_collapsed(")]

    assert 'st.session_state["afi_insight_focus"] = None' in focus_fn, (
        "selecting an action must drop any insight selection")
    assert 'st.session_state["afi_focus"] = None' in insight_fn, (
        "selecting an insight card must drop any action selection")
    for key in ('afi_focus', 'afi_insight_focus'):
        assert f'st.session_state["{key}"] = None' in clear_fn, key

    # The toggle: pressing the selected card again clears it, and that has to
    # happen before the assignment or the early return is unreachable.
    assert insight_fn.index(
        'st.session_state["afi_insight_focus"] = None') < insight_fn.index(
        'st.session_state["afi_insight_focus"] = group_type')


def test_the_insight_selection_scrolls_and_scopes_by_its_own_ids():
    """Scoped by the ids the badge counted, so the count and the list agree.

    Re-deriving "everything in this stage" at the section would pull in the
    non-negative records the card deliberately excluded, and the section would
    then show more records than the badge that opened it claimed.
    """
    assert 'insights.get(insight_focus)' in APP
    assert 'selected_insight.get("supporting_feedback_ids")' in APP
    # Reuses the by-id helper rather than a second filtering path.
    assert "evidence_for_action(view, insight_ids)" in APP
    # And the jump fires for either kind of selection.
    assert "if focus or insight_focus:" in APP


def test_both_insight_buttons_exist_even_when_a_card_is_empty():
    """The buttons are keyed by position, so they cannot be conditional.

    Making them depend on a card having content would shift the second card's
    key the moment the first went empty, and a click would scope the section
    to the wrong group.
    """
    nav = APP[APP.index("def render_hidden_nav("):APP.index("# ====", APP.index(
        "def render_hidden_nav("))]
    assert "for index, group_type in enumerate(render.INSIGHT_GROUPS)" in nav
    assert "on_click=_focus_insight" in nav


def test_app_does_not_read_the_aggregates_artifact_at_runtime():
    """The dashboard must run on the records plus this code, nothing else.

    aggregates.json is regenerated by the pipeline. Reading presentation text
    out of it meant a deploy that shipped new code alongside an older artifact
    crashed with KeyError on a field the old file did not have. The app now
    recomputes actions from the records and takes labels from RANK_KEYS, so
    that class of failure is gone.
    """
    assert 'PROC / "aggregates.json"' not in APP
    assert "COUNTED_STATUSES" in APP, "only Open records may count"
    assert 'agg["ranking"]' not in APP
    assert "RANK_KEYS" in APP

    # Every ranking key must supply a label, or the rail renders a blank item.
    from src.analysis.aggregate import RANK_KEYS

    for entry in RANK_KEYS:
        assert len(entry) == 3, entry
        field, label, explanation = entry
        assert label.strip() and explanation.strip(), field
        assert "_" not in label, f"{field} label reads like a field name: {label}"
