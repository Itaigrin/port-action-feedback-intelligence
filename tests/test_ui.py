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
    "What this changes compared with a flat-theme dashboard",
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
        "render_comparison_panel",
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
    labels = re.findall(r'st\.(?:multiselect|slider|number_input|selectbox)\(\s*"([^"]+)"',
                        APP)
    expected = ["Lifecycle status", "Problem type", "Journey stage",
                "Taxonomy category", "Taxonomy subcategory", "Minimum severity",
                "Top Recommended product actions", "Persona",
                "Confidence / review state"]
    assert labels[:len(expected)] == expected, labels[:len(expected)]


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


def test_comparison_panel_present():
    from src.ui.render import render_comparison_panel

    html = render_comparison_panel()
    assert "What this changes compared with a flat-theme dashboard" in html
    assert 'class="old"' in html and 'class="new"' in html


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
