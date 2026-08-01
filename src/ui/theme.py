"""Design tokens and the stylesheet that gives Streamlit the mockup's shell.

Values here are lifted from action_feedback_solution_mockup.html rather than
re-derived, so the two cannot drift apart by eye. Anything that exists only to
neutralise a Streamlit default is grouped at the bottom and labelled, because
that is the part most likely to break on a Streamlit upgrade.
"""

from __future__ import annotations

from urllib.parse import quote

# --- tokens ----------------------------------------------------------------
INK = "#182330"
MUTED = "#64748b"
LINE = "#e2e8f0"
SURFACE = "#ffffff"
BG = "#f3f6fb"
BLUE = "#2764e7"
BLUE_SOFT = "#eaf1ff"
GREEN = "#087b61"
GREEN_SOFT = "#e9fbf4"
AMBER = "#aa6100"
AMBER_SOFT = "#fff5df"
RED = "#c43e3e"
RED_SOFT = "#fff0f0"
PURPLE = "#6d43b8"
PURPLE_SOFT = "#f2ebff"
SHADOW = "0 8px 24px rgba(15, 23, 42, .06)"

SEVERITY_BADGE = {5: "b-red", 4: "b-red", 3: "b-amber", 2: "b-neutral", 1: "b-neutral"}


# --- the assistant's robot mark --------------------------------------------
# Painted as a background image rather than placed in the markup: the launcher
# is an st.button, whose label is plain text, so there is nowhere to put an
# <svg>. A data URI keeps it self-contained -- no request, nothing to 404 on a
# cold deploy, and it renders identically on every platform, which an emoji
# does not.
#
# Two-tone by construction: the white head is drawn over the button's blue,
# and the face is repainted in that same blue so the eyes read as cut-outs.
# Both surfaces that carry the mark are therefore blue.
_ROBOT_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>"
    "<g fill='%(w)s'>"
    "<circle cx='12' cy='3.15' r='1.55'/>"
    "<rect x='11.45' y='4.3' width='1.1' height='2.4' rx='.55'/>"
    "<rect x='3.9' y='6.2' width='16.2' height='12.1' rx='4.7'/>"
    "<rect x='1.75' y='10.3' width='2.7' height='4.6' rx='1.35'/>"
    "<rect x='19.55' y='10.3' width='2.7' height='4.6' rx='1.35'/>"
    "<path d='M9.5 16.6h4.9l-4.6 4.9z'/>"
    "</g>"
    "<rect x='6.55' y='8.55' width='10.9' height='7.5' rx='2.9' fill='%(f)s'/>"
    "<g fill='%(w)s'>"
    "<ellipse cx='9.75' cy='12.3' rx='.95' ry='1.5'/>"
    "<ellipse cx='14.25' cy='12.3' rx='.95' ry='1.5'/>"
    "</g></svg>"
)


def robot_data_uri(face: str = BLUE, white: str = "#ffffff") -> str:
    """The mark as a CSS url(), with the face painted to match its surface."""
    svg = _ROBOT_SVG % {"w": white, "f": face}
    # `<`, `>`, `#` and `%` are the characters that actually break a data URI
    # inside url(). Everything else is left readable rather than encoded into
    # an unreviewable blob.
    return 'url("data:image/svg+xml,' + quote(svg, safe="/:=' ,.") + '")'


ROBOT_ON_BLUE = robot_data_uri()


CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;650;700;750;800&display=swap');

:root {{
  --ink: {INK};
  --muted: {MUTED};
  --line: {LINE};
  --surface: {SURFACE};
  --bg: {BG};
  --blue: {BLUE};
  --blue-soft: {BLUE_SOFT};
  --green: {GREEN};
  --green-soft: {GREEN_SOFT};
  --amber: {AMBER};
  --amber-soft: {AMBER_SOFT};
  --red: {RED};
  --red-soft: {RED_SOFT};
  --purple: {PURPLE};
  --purple-soft: {PURPLE_SOFT};
  --shadow: {SHADOW};
}}

html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: var(--bg) !important;
  color: var(--ink);
  font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.stApp * {{ box-sizing: border-box; }}
body {{ overflow-x: hidden; }}

/* ---------------------------------------------------------------- top bar */
.afi-topbar {{
  height: 64px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px; border-bottom: 1px solid var(--line);
  background: rgba(255,255,255,.92); backdrop-filter: blur(10px);
  position: fixed; top: 0; left: 0; right: 0; z-index: 999;
}}
.afi-brand {{
  display: flex; align-items: center; gap: 11px;
  font-weight: 750; letter-spacing: -.02em; font-size: 15px; color: var(--ink);
}}
.afi-brand-mark {{
  display: grid; place-items: center; width: 29px; height: 29px;
  border-radius: 8px; background: var(--blue); color: #fff; font-size: 18px;
}}
.afi-top-meta {{ color: var(--muted); font-size: 12px; }}

/* --------------------------------------------------------------- surfaces */
.afi-panel, .afi-card {{
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 14px; box-shadow: var(--shadow);
}}
.afi-section {{ padding: 19px; }}
.afi-section-head {{
  display: flex; justify-content: space-between; align-items: start;
  gap: 12px; margin-bottom: 14px;
}}
.afi-section-head p {{ margin: 0; font-size: 12px; color: var(--muted); }}
.afi-section-head h2 {{ font-size: 17px; letter-spacing: -.02em; margin: 0 0 6px; }}

/* ------------------------------------------------------------------- hero */
.afi-hero {{
  display: flex; justify-content: space-between; gap: 24px;
  margin-bottom: 22px; align-items: end;
}}
.afi-hero h1 {{
  font-size: 28px; letter-spacing: -.04em; margin: 0 0 7px;
  font-weight: 750; line-height: 1.2; color: var(--ink);
}}
.afi-hero p {{ max-width: 720px; margin: 0; color: var(--muted); }}
.afi-eyebrow {{
  color: var(--blue); font-weight: 750; font-size: 12px;
  text-transform: uppercase; letter-spacing: .08em; margin-bottom: 4px;
}}
.afi-run-meta {{
  min-width: 240px; background: #f8fafc; border: 1px solid var(--line);
  border-radius: 10px; padding: 11px 13px; color: var(--muted); font-size: 12px;
}}
.afi-run-meta b {{ color: var(--ink); }}

/* -------------------------------------------------------------------- KPI */
/* The original four-card row. Unchanged since before the trend cards existed
   -- they now live in their own row, .afi-trend-row, below this one. */
.afi-kpis {{
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 14px; margin-bottom: 20px;
}}
.afi-kpi {{
  padding: 16px; box-shadow: none; background: rgba(255,255,255,.78);
  border: 1px solid var(--line); border-radius: 14px;
}}
/* The label naming each card reads as a heading, so it sits above the 12px
   used for the supporting detail underneath rather than level with it. */
.afi-kpi .label {{ color: var(--muted); font-size: 13.5px; font-weight: 600; }}
.afi-kpi .value {{
  display: block; font-size: 27px; font-weight: 750;
  letter-spacing: -.04em; margin: 4px 0;
}}
.afi-kpi .detail {{ font-size: 12px; color: var(--muted); }}
.afi-kpi .detail.good {{ color: var(--green); }}
.afi-kpi .detail.warning {{ color: var(--amber); }}

/* The two largest-increase cards, in their own row below the four KPIs.
   Two columns whose combined width, gap included, equals the row above:
   two of four equal tracks plus the gap between them is exactly what two
   equal tracks in a row of the same total width work out to, so no
   fractional math is needed to make the rows line up.
   minmax(0, 1fr), not 1fr: a grid track's default min-width is auto, so one
   long unbroken subcategory name would widen its own column and push the
   row past the page instead of wrapping inside the card. */
.afi-trend-row {{
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px; margin-bottom: 20px; align-items: stretch;
}}
.afi-kpi-growth {{
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  align-content: start;
  padding: 16px;
  min-height: 168px;
  box-shadow: 0 13px 32px rgba(33,53,97,.07);
  background: #fff;
  border: 1px solid #cbd6e9; border-radius: 15px;
  /* Same warning mark as a high-severity action card: this row only ever
     reports negative feedback rising. */
  border-left: 4px solid var(--red);
  min-width: 0; overflow-wrap: anywhere;
}}
.afi-kpi-growth::before {{
  content: "↗";
  position: absolute; top: 16px; left: 16px;
  display: grid; place-items: center;
  width: 34px; height: 34px;
  border-radius: 9px;
  background: var(--red-soft); color: var(--red);
  font-size: 17px; font-weight: 800; line-height: 1;
}}
.afi-kpi-growth .label {{
  grid-column: 1 / -1;
  display: block;
  min-height: 13px;
  padding-left: 48px;
  color: #8995aa; font-size: 9px; font-weight: 800;
  line-height: 1.25; letter-spacing: .08em; text-transform: uppercase;
}}
.afi-growth-name {{
  grid-column: 1 / -1;
  display: block; font-size: 15px; font-weight: 750; letter-spacing: -.02em;
  min-height: 22px;
  margin: 4px 0 10px; padding: 0 0 11px 48px;
  border-bottom: 1px solid #e2e7f0;
  line-height: 1.25; color: var(--ink);
  /* Long names wrap instead of clipping or spilling past the border. */
  overflow-wrap: anywhere; hyphens: auto;
}}
.afi-growth-stat {{
  display: grid; align-content: start; gap: 3px;
  min-width: 0; padding-right: 10px;
  border-right: 1px solid #e2e7f0;
  color: #7a879f; font-size: 9px; line-height: 1.25;
}}
.afi-growth-stat:last-child {{ border-right: 0; padding-left: 10px; padding-right: 0; }}
.afi-growth-stat:nth-last-child(2) {{ padding-left: 10px; }}
.afi-growth-stat b {{
  display: block; color: var(--ink);
  font-size: 21px; font-weight: 750; line-height: 1.05;
  letter-spacing: -.04em;
}}
/* The increase is the number the ranking is built on; growth % is only ever
   context beside it, so it stays muted and unbolded even inside a red row. */
.afi-growth-stat b.afi-growth-increase {{ color: var(--red); font-weight: 750; }}
.afi-growth-pct {{
  display: block; color: var(--red); font-weight: 650;
  margin: 0; font-size: 9px;
}}
.afi-growth-empty {{
  grid-column: 1 / -1;
  display: block; margin: 8px 0 0 48px; font-size: 12px; color: var(--muted);
}}

/* ----------------------------------------------------------------- badges */
/* The review badge now names its reason, so it is the one badge that can get
   long. Every other badge stays nowrap; this one wraps rather than pushing
   past the card edge on a narrow screen. */
.afi-badge.b-amber {{ white-space: normal; max-width: 100%; }}
.afi-badge {{
  display: inline-flex; align-items: center; gap: 5px; white-space: nowrap;
  border-radius: 999px; padding: 3px 8px; font-size: 11px; font-weight: 700;
}}
.b-blue {{ background: var(--blue-soft); color: #2456c5; }}
.b-green {{ background: var(--green-soft); color: var(--green); }}
.b-amber {{ background: var(--amber-soft); color: var(--amber); }}
.b-red {{ background: var(--red-soft); color: var(--red); }}
.b-purple {{ background: var(--purple-soft); color: var(--purple); }}
.b-neutral {{ background: #f1f5f9; color: #475569; }}

/* -------------------------------------------------- recommended actions */
.afi-actions {{
  background: linear-gradient(155deg, #eaf1ff 0%, #f6f9ff 54%, #eef4ff 100%);
  border: 1px solid #bfd1f2; border-radius: 14px; padding: 19px;
  box-shadow: 0 14px 34px rgba(39,100,231,.13);
}}
.afi-actions .afi-section-head {{
  padding-bottom: 13px; border-bottom: 1px solid #cfddf5;
}}
.afi-actions .afi-section-head h2 {{
  color: #173f8a; font-size: 20px; margin-bottom: 5px;
}}
.afi-action-list {{ display: grid; gap: 10px; }}
/* The ranking explainer sits inside the blue panel and must not read as a
   card of its own. */
.st-key-afi_rank_help {{ margin-top: 12px; }}
.st-key-afi_rank_help summary {{
  color: #41669f !important; font-size: 12px !important; font-weight: 650;
}}
.st-key-afi_rank_help [data-testid="stExpander"] details {{
  border: 1px solid #cfddf5 !important; border-radius: 8px !important;
  background: rgba(255,255,255,.6) !important;
}}
.afi-insight {{
  border: 1px solid #d5e0f0; border-left: 4px solid var(--blue);
  border-radius: 11px; padding: 14px; background: #fff;
  box-shadow: 0 4px 12px rgba(31,65,122,.06);
}}
.afi-insight-high {{ border-left-color: var(--red); }}
.afi-insight-top {{
  display: flex; justify-content: space-between; gap: 10px; align-items: center;
}}
.afi-insight-top .afi-badge {{ padding: 4px 9px; font-size: 12px; }}
.afi-action-title {{
  font-size: 18px; letter-spacing: -.025em; margin: 0; color: #152d55;
  font-weight: 700; line-height: 1.3;
}}
.afi-insight p {{ color: #475569; margin: 10px 0; }}
.afi-action-metrics {{
  display: flex; flex-wrap: wrap; gap: 7px; margin: 10px 0 12px;
}}
.afi-action-metrics .afi-badge {{ padding: 4px 9px; font-size: 12px; }}
.afi-action-btn {{
  display: inline-block; border: 1px solid #c8d7ee; border-radius: 7px;
  background: #f8faff; color: #41669f; padding: 6px 9px; cursor: pointer;
  font-size: 12px; font-weight: 650; text-decoration: none;
}}
.afi-action-btn:hover {{
  border-color: #9fb8df; background: #f1f6ff; color: #234f91;
}}
/* The card whose records the feedback section is currently showing.
   :visited is spelled out rather than left to the base rule below. The button
   is an <a href="#">, so the browser counts it as visited the moment the page
   is loaded, and `.afi-action-btn:visited` further down is the same
   specificity as `.afi-action-btn.is-selected` -- being later in the file, it
   won the tie and painted the label dark blue on the blue fill. Naming
   :visited here raises this to three classes, so it wins wherever it sits. */
.afi-action-btn.is-selected,
.afi-action-btn.is-selected:visited {{
  background: var(--blue); border-color: var(--blue); color: #fff !important;
}}
.afi-action-btn.is-selected:hover,
.afi-action-btn.is-selected:visited:hover {{
  background: #1d54c9; border-color: #1d54c9; color: #fff !important;
}}

/* --------------------------------------------- where users struggle most */
/* Reuses the existing surface, radius, border, shadow and badge system --
   nothing new is introduced, so the section reads as part of the same page. */
.afi-struggle {{ margin-bottom: 20px; }}
/* stretch, not start: the two cards must be the same height whatever their
   content, or the pair reads as one of them having failed to load. */
.afi-insight-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
  align-items: stretch;
}}
/* Red left bar, matching a high-severity product action card.
   These four cards -- the two largest-increase cards and the two
   most-negative-feedback cards -- all report something getting worse, so they
   carry the same warning mark the ranked actions use rather than reading as
   neutral surfaces. */
.afi-insight-card {{
  padding: 16px; display: flex; flex-direction: column;
  border-left: 4px solid var(--red);
}}
/* The example list takes the slack, so the cards end level. */
.afi-insight-examples {{ margin-top: auto; }}
.afi-insight-label {{
  display: block; color: var(--muted); font-size: 13.5px;
  font-weight: 600; margin-bottom: 6px;
}}
.afi-insight-name {{
  font-size: 17px; font-weight: 750; letter-spacing: -.02em; color: var(--ink);
}}
.afi-insight-parent {{ color: var(--muted); font-size: 12px; margin-top: 2px; }}
.afi-insight-count {{ margin: 9px 0 8px; }}
.afi-insight-focus {{ margin: 0 0 8px; color: #475569; font-size: 13px; }}
.afi-insight-examples {{
  margin: 0; padding-left: 17px; color: #475569; font-size: 12px;
}}
.afi-insight-examples li {{ margin-bottom: 3px; }}

/* ---------------------------------------------------------- trend chart */
.afi-trend {{ margin-bottom: 20px; box-shadow: none; }}
.afi-trend-svg {{ width: 100%; height: auto; display: block; }}
.afi-trend-grid {{ stroke: #eef2f7; stroke-width: 1; }}
.afi-trend-axis {{ fill: var(--muted); font-size: 9px; }}
/* Shared hover: one column per week reveals a guide line and a panel listing
   every stage at that week. CSS-only, so it appears instantly -- a native
   <title> waits about a second and cannot be styled. */
.afi-trend-guide {{
  stroke: #cbd5e1; stroke-width: 1; stroke-dasharray: 3 3; opacity: 0;
}}
.afi-trend-tip {{ opacity: 0; pointer-events: none; }}
.afi-trend-col:hover .afi-trend-guide,
.afi-trend-col:hover .afi-trend-tip {{ opacity: 1; }}
/* The hovered column paints last, so its panel is never covered by a
   neighbouring column drawn after it. */
.afi-trend-col:hover {{ isolation: isolate; }}
.afi-trend-tip-bg {{
  fill: #ffffff; stroke: var(--line); stroke-width: 1;
  filter: drop-shadow(0 6px 16px rgba(15, 23, 42, .14));
}}
.afi-trend-tip-head {{
  fill: var(--ink); font-size: 10.5px; font-weight: 750;
}}
.afi-trend-tip-row {{ fill: #475569; font-size: 10px; }}
.afi-trend-tip-val {{ fill: var(--ink); font-size: 10px; font-weight: 750; }}

.afi-trend-legend {{
  display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;
}}
.afi-trend-key {{
  display: inline-flex; align-items: center; gap: 5px;
  color: #475569; font-size: 11px;
}}
.afi-trend-key i {{
  width: 9px; height: 3px; border-radius: 2px; display: inline-block;
}}

/* ----------------------------------------------------------- CSS bar chart */
.afi-category-list {{ display: grid; gap: 10px; }}
.afi-category-row {{
  display: grid; grid-template-columns: 1fr auto; gap: 12px;
  padding-bottom: 9px; border-bottom: 1px solid #eef2f7;
  text-decoration: none; color: inherit;
}}
.afi-category-row:last-child {{ border: 0; padding-bottom: 0; }}
a.afi-category-row, a.afi-category-row:visited,
a.afi-category-row *, .afi-action-btn, .afi-focus-back {{
  text-decoration: none !important;
}}
a.afi-category-row strong {{ color: var(--ink) !important; }}
a.afi-category-row .afi-row-num, a.afi-category-row .afi-row-num b {{
  color: var(--muted) !important;
}}
a.afi-category-row:hover strong {{ color: var(--blue) !important; }}
.afi-action-btn, .afi-action-btn:visited {{ color: #41669f !important; }}
.afi-focus-back, .afi-focus-back:visited {{ color: var(--blue) !important; }}
.afi-bar {{
  height: 7px; border-radius: 99px; background: #e9eef7;
  overflow: hidden; margin-top: 6px;
}}
.afi-bar span {{
  display: block; height: 100%;
  background: linear-gradient(90deg, #3b82f6, #6d5dfc); border-radius: inherit;
}}
.afi-row-num {{ color: var(--muted); font-size: 12px; text-align: right; }}
.afi-crumb {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px; font-size: 12px;
}}
.afi-crumb a {{ color: var(--blue); font-weight: 700; text-decoration: none; }}

/* -------------------------------------------------------- feedback cards */
.afi-table-section {{ margin-top: 26px; padding: 19px; }}
.afi-evidence {{ display: grid; gap: 10px; margin-top: 13px; }}
.afi-feedback {{
  border: 1px solid var(--line); border-radius: 11px; padding: 14px;
  background: #fff; transition: border-color .15s, box-shadow .15s;
}}
.afi-feedback:hover {{
  border-color: #9bb8f4; box-shadow: 0 5px 14px rgba(37,99,235,.08);
}}
.afi-feedback-head {{
  display: flex; gap: 10px; align-items: start; justify-content: space-between;
}}
.afi-feedback-title {{ font-weight: 750; letter-spacing: -.01em; }}
.afi-recommended-action {{
  margin: 11px 0 8px; padding: 10px 11px; border-radius: 8px;
  background: var(--blue-soft); border-left: 3px solid var(--blue);
}}
.afi-recommended-action span {{
  display: block; color: #3963ad; font-size: 10px; text-transform: uppercase;
  font-weight: 800; letter-spacing: .06em;
}}
.afi-recommended-action strong {{
  display: block; margin-top: 2px; color: #173f8a; font-size: 13px;
}}
.afi-feedback-meta, .afi-labels {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.afi-feedback-meta {{ margin: 8px 0; }}
.afi-quote {{
  border-left: 3px solid #bfdbfe; padding-left: 10px; color: #475569;
  font-size: 13px; margin: 9px 0 11px;
}}
.afi-labels .afi-label {{
  border: 1px solid #d7e1f4; color: #3f5472; background: #f8fbff;
  padding: 3px 7px; border-radius: 6px; font-size: 11px;
}}
.afi-source, .afi-source:visited, .afi-source:hover {{
  color: var(--blue) !important; text-decoration: none !important;
  font-weight: 650; font-size: 12px;
}}
/* Source link and the label editor share the card's last row. */
.afi-feedback-foot {{
  display: flex; align-items: center; gap: 14px; margin-top: 10px;
}}
.afi-edit-link, .afi-edit-link:visited, .afi-edit-link:hover {{
  color: #475569 !important; text-decoration: none !important;
  font-weight: 650; font-size: 12px;
  border: 1px solid #cbd5e1; border-radius: 7px; padding: 4px 9px;
}}
.afi-edit-link:hover {{ border-color: var(--blue); color: var(--blue) !important; }}
.afi-crumb a, .afi-crumb a:visited {{
  color: var(--blue) !important; text-decoration: none !important;
}}
.afi-filter-state-row {{
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin: 14px 0 11px;
}}
.afi-filter-state {{ margin: 0; color: var(--blue); font-size: 12px; font-weight: 700; }}
.afi-focus-back {{
  flex: 0 0 auto; border: 1px solid #b9cdf7; border-radius: 7px;
  background: #f6f9ff; color: var(--blue); padding: 6px 9px;
  font-weight: 750; text-decoration: none; font-size: 12px;
}}
.afi-empty {{
  padding: 28px; color: var(--muted); text-align: center;
  border: 1px dashed #cbd5e1; border-radius: 10px;
}}

/* ---- two-column compare blocks -----------------------------------------
   Still used by the Guide for the severity/persona split. The dashboard's
   comparison panel was removed as a product decision and its wrapper rule
   went with it; this shared rule did not. */
.afi-comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.afi-comparison > div {{ border-radius: 10px; padding: 13px; }}
.afi-comparison .old {{ background: #fff7ed; border: 1px solid #fed7aa; }}
.afi-comparison .new {{ background: #effcf7; border: 1px solid #bbf7d0; }}
.afi-comparison ul {{ margin: 8px 0 0; padding-left: 18px; color: #475569; }}
.afi-comparison li {{ margin-bottom: 3px; }}

/* -------------------------------------------------------------- guide tab */
.afi-guide-h2 {{ font-size: 20px; letter-spacing: -.02em; margin: 0 0 6px; }}

/* One shared card behind the whole "N categories" section -- the heading
   and every category row -- instead of a card behind just the title with
   separately-boxed expanders below it. Matches the single-surface look of
   the "N journey stages" section below it. Each expander is stripped of
   its own Streamlit chrome (border/background/shadow) and turned into a
   row inside the shared card, separated by a hairline like .afi-subcat. */
.st-key-afi_guide_cats {{
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 14px; box-shadow: var(--shadow); padding: 19px 19px 8px;
}}
.st-key-afi_guide_cats [data-testid="stExpander"],
.st-key-afi_guide_cats [data-testid="stExpander"] details {{
  background: transparent !important; border: none !important;
  box-shadow: none !important; border-radius: 0 !important;
}}
.st-key-afi_guide_cats [data-testid="stExpander"] {{
  border-top: 1px solid var(--line) !important;
  margin-top: 4px !important; padding-top: 4px !important;
}}

/* Subcategory blocks inside each category's expander. One block per
   subcategory, each separated by a hairline so the eye has a clear stopping
   point between them instead of everything running together. */
/* Streamlit wraps every st.markdown() call in its own container, so each
   .afi-subcat is an only child where it sits -- :first-child/:first-of-type
   tricks can't tell the first block in a category from a later one. A
   uniform rule on every block is the only thing that renders consistently. */
.afi-subcat {{
  padding: 16px 0; border-top: 1px solid #eef1f6;
}}
.afi-subcat-head {{
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 10px; flex-wrap: wrap;
}}
.afi-subcat-name {{
  font-size: 15px; font-weight: 750; letter-spacing: -.01em; color: #0f172a;
}}
.afi-subcat-count {{
  font-size: 12px; color: #94a3b8; font-weight: 650; white-space: nowrap;
}}
.afi-subcat-desc {{
  margin: 7px 0 12px; color: #475569; font-size: 13.5px; line-height: 1.55;
}}
.afi-subcat-usefor {{
  margin: 0 0 12px; color: #334155; font-size: 13px; line-height: 1.55;
}}
.afi-subcat-usefor b {{ color: #0f172a; }}
.afi-subcat-examples {{
  display: flex; flex-direction: column; gap: 8px;
}}
.afi-subcat-example {{
  background: #f8fafc; border-left: 3px solid #cbd5e1; border-radius: 0 8px 8px 0;
  padding: 9px 13px; color: #64748b; font-size: 12.5px; font-style: italic;
  line-height: 1.55;
}}

/* =========================================================================
   STREAMLIT DEFAULT OVERRIDES
   Everything below exists only to neutralise built-in chrome. Grouped so a
   Streamlit upgrade has one place to check.
   ========================================================================= */
header[data-testid="stHeader"] {{ display: none !important; }}
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], footer {{ display: none !important; }}
[data-testid="stSidebar"] {{ display: none !important; }}

.stApp > [data-testid="stAppViewContainer"] > .main .block-container,
[data-testid="stMainBlockContainer"] {{
  max-width: 1500px !important;
  padding: 88px 32px 48px !important;   /* 64px top bar + 24px page padding */
  /* the pinned tab strip is out of flow, so nothing is subtracted here */
  width: 100% !important;
  margin: 0 auto !important;
}}

/* Streamlit stacks every element with a gap; the mockup controls its own. */
[data-testid="stVerticalBlock"] {{ gap: 0 !important; }}

/* Streamlit gives every markdown block margin-bottom: -14px to pull the next
   element up over a trailing <p>'s own margin. Our blocks set margin:0 on that
   <p>, so there is nothing to pull back over and the negative margin drags the
   following element 14px into this one -- which is what made the filter-state
   line overlap the section caption. */
.st-key-afi_page [data-testid="stMarkdownContainer"],
.st-key-afi_guide_cats [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ gap: 0 !important; }}
[data-testid="stElementContainer"] {{ margin: 0 !important; }}

/* ---- page grid ---------------------------------------------------------
   Column 1 is the 270px filter rail. Targeted through st.container(key=...)
   which emits a stable .st-key-<key> class -- preferred over autogenerated
   test ids, which change between Streamlit releases. */
.st-key-afi_page [data-testid="stHorizontalBlock"] {{
  gap: 24px !important; align-items: flex-start !important;
}}
.st-key-afi_page > div > [data-testid="stHorizontalBlock"] {{
  flex-wrap: nowrap !important;
}}
.st-key-afi_page > div > [data-testid="stHorizontalBlock"]
  > [data-testid="stColumn"]:first-child {{
  flex: 0 0 270px !important; width: 270px !important;
  min-width: 270px !important; max-width: 270px !important;
}}
/* The main column takes the remainder. min-width:0 is required or its
   contents set an intrinsic floor and the row wraps. */
.st-key-afi_page > div > [data-testid="stHorizontalBlock"]
  > [data-testid="stColumn"]:last-child {{
  flex: 1 1 0 !important; min-width: 0 !important; max-width: none !important;
  width: auto !important;
}}
/* Streamlit columns stretch to the tallest sibling; the rail must not. */
[data-testid="stColumn"] {{ align-self: flex-start !important; }}

/* The filter rail itself is the mockup's sticky white panel. */
.st-key-afi_rail .afi-panel {{ border: 0; box-shadow: none; padding: 0 !important; }}
.st-key-afi_rail {{
  position: sticky !important; top: 88px !important;
  height: fit-content !important; align-self: flex-start !important;
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 14px; box-shadow: var(--shadow); padding: 17px !important;
  /* Deliberately no max-height or overflow. The mockup capped the rail to the
     viewport and scrolled it internally, but expanding "More filters" or "View
     full taxonomy" then produced a second scrollbar inside the page. The rail
     now grows and the page scrolls once. */
  overflow: visible;
}}

/* The feedback section is one card wrapping header, search and all records.
   Rendering the open and close tags in separate st.markdown calls does not
   work: Streamlit balances each block independently, so the wrapper would
   close before the cards were inside it. */
.st-key-afi_feedback {{
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 14px; box-shadow: var(--shadow);
  padding: 19px !important; margin-top: 26px !important;
}}
.st-key-afi_actions, .st-key-afi_charts {{ min-width: 0; }}

/* Hidden proxies for the mockup's HTML controls. Positioned off-screen rather
   than display:none -- a programmatic .click() must still reach a live button,
   and aria-hidden keeps them out of the accessibility tree and tab order. */
.st-key-afi_hidden_nav, .st-key-afi_hidden_edit {{
  position: absolute !important; width: 1px; height: 1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
}}
[data-afi-click] {{ cursor: pointer; }}
.st-key-afi_content [data-testid="stHorizontalBlock"] {{ gap: 20px !important; }}

/* Filter panel widgets, sized down to the mockup's compact scale. */
.afi-filters [data-testid="stWidgetLabel"] p {{
  color: #475569 !important; font-weight: 650 !important; font-size: 12px !important;
  margin-bottom: 4px !important;
}}
.afi-filters [data-testid="stWidgetLabel"] {{ margin-bottom: 2px !important; }}
.afi-filters [data-baseweb="select"] > div {{
  border: 1px solid #cbd5e1 !important; border-radius: 8px !important;
  min-height: 36px !important; font-size: 13px !important; background: #fff !important;
}}
.afi-filters [data-testid="stElementContainer"] {{ margin-bottom: 10px !important; }}
.afi-filters [data-testid="stSlider"] {{ padding-top: 2px !important; }}
.afi-filters .afi-rubric {{ margin: 0 0 14px !important; }}

/* Severity control, lifted from the mockup: a native range input with a tick
   ruler below it labelling every step. Streamlit's slider is not used -- it
   rendered its thumb at left:100% while reporting value 1, so the handle sat
   at the maximum end for the minimum value.

   There used to also be a pill above the track showing the current value in
   blue. Removed: the thumb's own position already shows the selection, and a
   second, separately-updating indicator was redundant with it. */
.afi-filter-label {{
  display: block; margin: 16px 0 6px; color: #475569;
  font-weight: 650; font-size: 12px;
}}
/* Pulled up against the track: the ticks label the steps, so they have to
   read as part of the control rather than as a caption under it. */
.afi-range-row {{
  display: flex; justify-content: space-between; align-items: center;
  margin-top: -4px; color: var(--muted); font-size: 12px;
}}
.afi-sev input[type="range"] {{
  width: 100%; accent-color: var(--blue); margin: 2px 0 0; cursor: pointer;
  direction: ltr;
}}
/* !important, not just specificity: Streamlit's own default paragraph rule
   targets [data-testid=...] p, which ties a bare-class selector's specificity
   -- measured live at 14px Source Sans winning over an unqualified
   .afi-rubric rule here. !important settles it regardless of cascade order,
   which is the more robust of the two against a future Streamlit version
   reordering its own stylesheet. */
.afi-rubric {{
  color: var(--muted) !important; font-size: 11px !important; margin: 4px 0 0;
}}
.afi-filters .stButton > button {{
  width: 100%; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px;
  background: #fff; color: #475569; font-weight: 700; font-size: 13px;
}}
.afi-filters .stButton > button:hover {{ border-color: var(--blue); color: var(--blue); }}
.afi-filters details {{ margin-top: 6px; }}
.afi-filters summary {{
  cursor: pointer; color: #475569; font-size: 12px; font-weight: 750;
}}

/* Ranking note at the foot of the filter rail. */
.afi-rank-note {{
  margin-top: 15px; padding-top: 12px; border-top: 1px solid var(--line);
  font-size: 11px; color: var(--muted);
}}
.afi-rank-note b {{ color: var(--ink); font-size: 12px; }}
.afi-rank-note p {{ margin: 6px 0; }}
.afi-rank-note ol {{ margin: 6px 0; padding-left: 18px; }}
.afi-rank-note li {{ margin-bottom: 2px; }}
.afi-rank-note li b {{ font-size: 11px; font-weight: 650; }}

/* Compact segmented navigation, pinned into the top bar so the main content
   still begins at the mockup's y=88 instead of being pushed down by a tab row. */
/* Only the tab strip is lifted into the top bar. Pinning the whole container
   would take the tab panels with it -- and the panels are the entire app.
   ARIA roles are used rather than data-baseweb attributes: the roles are part
   of the accessibility contract, so they survive component-library changes. */
.st-key-afi_nav [role="tablist"] {{
  position: fixed !important; top: 15px; left: 50%;
  transform: translateX(-50%); z-index: 1000; width: auto !important;
  gap: 4px !important; background: #eef2f9 !important; border-radius: 9px !important;
  padding: 3px !important; border: 1px solid var(--line) !important;
}}
/* The strip is out of flow, so its 35px placeholder and the panel's own top
   padding would otherwise push the page 49px below the mockup. */
.st-key-afi_nav [role="tablist"]::after,
.st-key-afi_nav [role="tablist"]::before {{ display: none !important; }}
.st-key-afi_nav [role="tabpanel"] {{ padding-top: 0 !important; }}
.st-key-afi_nav [data-baseweb="tab-highlight"],
.st-key-afi_nav [data-baseweb="tab-border"] {{ display: none !important; }}
.st-key-afi_nav [role="tab"] {{
  height: 30px !important; padding: 0 14px !important; border-radius: 7px !important;
  font-size: 13px !important; font-weight: 700 !important; color: #475569 !important;
  background: transparent !important;
}}
.st-key-afi_nav [role="tab"][aria-selected="true"] {{
  background: #fff !important; color: var(--blue) !important;
  box-shadow: 0 1px 3px rgba(15,23,42,.10) !important;
}}

/* Search input inside the feedback section header. */
.afi-search [data-testid="stTextInput"] input {{
  border: 1px solid #cbd5e1 !important; border-radius: 8px !important;
  padding: 8px 9px !important; font-size: 13px !important; background: #fff !important;
}}
.afi-search [data-testid="stWidgetLabel"] {{ display: none !important; }}

/* =========================================================================
   RESPONSIVE — mirrors the mockup's two breakpoints
   ========================================================================= */
@media (max-width: 1050px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 82px 18px 32px !important; }}
  .st-key-afi_page > div > [data-testid="stHorizontalBlock"] {{
    flex-wrap: wrap !important;
  }}
  .st-key-afi_page > div > [data-testid="stHorizontalBlock"]
    > [data-testid="stColumn"]:first-child,
  .st-key-afi_page > div > [data-testid="stHorizontalBlock"]
    > [data-testid="stColumn"]:last-child {{
    flex: 1 1 100% !important; width: 100% !important;
    min-width: 100% !important; max-width: 100% !important;
  }}
  /* Every nested column (content grid, feedback header) stacks too. */
  [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap !important; }}
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    flex: 1 1 100% !important; min-width: 100% !important;
  }}
  .st-key-afi_rail .afi-panel {{ border: 0; box-shadow: none; padding: 0 !important; }}
.st-key-afi_rail {{ position: static !important; max-height: none !important; }}
  [data-testid="stHorizontalBlock"].afi-grid-row {{ flex-wrap: wrap !important; }}
  [data-testid="stHorizontalBlock"].afi-grid-row > [data-testid="stColumn"] {{
    width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;
    position: static !important;
  }}
  .afi-kpis {{ grid-template-columns: repeat(2, 1fr); }}
  .afi-trend-row {{ grid-template-columns: minmax(0, 1fr); }}
  .afi-content-grid {{ grid-template-columns: 1fr; }}
  .afi-insight-grid {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 650px) {{
  .afi-topbar {{ padding: 0 16px; }}
  .afi-hero {{ display: block; }}
  .afi-section-head {{ display: block; }}
  .afi-run-meta {{ margin-top: 12px; }}
  .afi-kpis {{ grid-template-columns: 1fr; }}
  .afi-trend-row {{ grid-template-columns: minmax(0, 1fr); }}
  .afi-insight-grid {{ grid-template-columns: 1fr; }}
  .afi-comparison {{ grid-template-columns: 1fr; }}
  .afi-search {{ margin-top: 10px; }}
}}

/* =========================================================================
   PRODUCT DATA ASSISTANT — floating launcher and panel
   ========================================================================= */
/* Both are keyed containers pinned to the viewport, so they survive scrolling
   and appear identically on the Dashboard and the Guide. They are rendered
   once at shell level, outside both tabs. */
.st-key-afi_assistant_launcher {{
  position: fixed !important; right: 24px; bottom: 76px; z-index: 1200;
  width: 58px; height: 58px;
}}
.st-key-afi_assistant_launcher [data-testid="stElementContainer"],
.st-key-afi_assistant_launcher [data-testid="stButton"] {{
  width: 58px !important; margin: 0 !important;
}}
.st-key-afi_assistant_launcher button {{
  width: 58px !important; height: 58px !important; border-radius: 50% !important;
  background-color: var(--blue) !important;
  background-image: {ROBOT_ON_BLUE} !important;
  background-repeat: no-repeat !important;
  background-position: center !important;
  background-size: 32px 32px !important;
  border: 1px solid {BLUE} !important; padding: 0 !important;
  box-shadow: 0 10px 26px rgba(39, 100, 231, .34) !important;
  transition: transform .15s ease, box-shadow .15s ease;
}}
/* The emoji is the button's accessible text; the mark is painted over it, so
   the label stays in the tree for a screen reader and off the screen. */
.st-key-afi_assistant_launcher button p {{
  opacity: 0 !important; font-size: 0 !important;
}}
.st-key-afi_assistant_launcher button:hover {{
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(39, 100, 231, .42) !important;
}}
.st-key-afi_assistant_launcher button:focus-visible {{
  outline: 3px solid rgba(39, 100, 231, .35) !important; outline-offset: 2px;
}}

.st-key-afi_assistant_panel {{
  position: fixed !important; right: 24px; bottom: 146px; z-index: 1199;
  width: 420px; max-width: calc(100vw - 32px);
  /* Bottom offset (146) + the pinned top bar (~66) subtracted, so a tall
     conversation scrolls inside the panel instead of pushing its header up
     behind the top bar. */
  max-height: calc(100vh - 212px); overflow-y: auto; overflow-x: hidden;
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 14px; box-shadow: 0 18px 44px rgba(15, 23, 42, .18);
  padding: 16px 16px 14px !important;
}}
.st-key-afi_assistant_panel [data-testid="stMarkdownContainer"] {{
  margin-bottom: 0 !important;
}}

.afi-bot-head {{ display: flex; gap: 10px; align-items: center; }}
.afi-bot-avatar {{
  width: 34px; height: 34px; flex: none; border-radius: 10px;
  background-color: var(--blue);
  background-image: {ROBOT_ON_BLUE};
  background-repeat: no-repeat; background-position: center;
  background-size: 23px 23px;
}}
.afi-bot-title {{ font-weight: 750; font-size: 14.5px; color: var(--ink); }}
.afi-bot-sub {{ font-size: 11.5px; color: var(--muted); margin-top: 1px; }}

/* The close control is a real button so it is keyboard reachable; CSS lifts it
   into the header rather than spending a column layout on it. */
.st-key-afi_assistant_close {{
  position: absolute !important; top: 14px; right: 14px; width: 30px;
}}
.st-key-afi_assistant_close button {{
  width: 30px !important; height: 30px !important; min-height: 30px !important;
  padding: 0 !important; border-radius: 8px !important;
  border: 1px solid var(--line) !important; background: #fff !important;
  color: var(--muted) !important; font-size: 13px !important;
}}
.st-key-afi_assistant_close button:hover {{ color: var(--ink) !important; }}

.st-key-afi_assistant_scope_box {{
  margin-top: 12px !important; padding: 9px 11px !important;
  background: var(--bg); border: 1px solid var(--line); border-radius: 10px;
}}
.st-key-afi_assistant_scope_box [data-testid="stWidgetLabel"] p {{
  font-size: 11px !important; font-weight: 700 !important;
  color: #475569 !important; margin-bottom: 2px !important;
}}
.st-key-afi_assistant_scope_box label p {{ font-size: 12px !important; }}
.st-key-afi_assistant_scope_box [data-testid="stElementContainer"] {{
  margin-bottom: 0 !important;
}}

.afi-bot-body {{ margin-top: 12px; }}
.afi-bot-msg {{
  font-size: 12.5px; line-height: 1.55; border-radius: 12px;
  padding: 9px 11px; margin-bottom: 9px;
}}
.afi-bot-bot {{ background: var(--bg); color: var(--ink); }}
.afi-bot-user {{
  background: var(--blue); color: #fff; font-weight: 600;
  margin-left: 34px; border-bottom-right-radius: 4px;
}}
.afi-bot-answer {{
  background: #fff; border: 1px solid var(--line); color: var(--ink);
  border-bottom-left-radius: 4px;
}}
.afi-bot-scope {{
  font-size: 11px; color: var(--muted); font-weight: 650;
  text-transform: none; margin-bottom: 6px;
}}
.afi-bot-finding {{ font-size: 12.5px; font-weight: 650; margin-bottom: 9px; }}
.afi-bot-empty {{ font-size: 12.5px; color: var(--muted); }}

.afi-bot-row {{
  display: flex; gap: 9px; padding: 8px 0;
  border-top: 1px solid var(--line);
}}
.afi-bot-rank {{
  width: 19px; height: 19px; flex: none; border-radius: 6px;
  background: var(--blue-soft); color: var(--blue);
  font-size: 11px; font-weight: 750; text-align: center; line-height: 19px;
}}
.afi-bot-rowbody {{ min-width: 0; flex: 1 1 auto; }}
.afi-bot-rowtitle {{ font-size: 12.5px; font-weight: 650; line-height: 1.4; }}
.afi-bot-rowsub {{ font-size: 11px; color: var(--muted); margin-top: 1px; }}
.afi-bot-cells {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }}
.afi-bot-cell {{
  background: var(--bg); border: 1px solid var(--line); border-radius: 7px;
  padding: 3px 7px; font-size: 10.5px; line-height: 1.35;
}}
.afi-bot-cell em {{ display: block; font-style: normal; color: var(--muted); }}
.afi-bot-cell b {{ color: var(--ink); font-weight: 700; }}
.afi-bot-evidence-link {{
  display: inline-block; margin-top: 7px; font-size: 11.5px;
  font-weight: 650; color: var(--blue); text-decoration: none;
}}
.afi-bot-evidence-link:hover {{ text-decoration: underline; }}
.afi-bot-note {{
  font-size: 11px; line-height: 1.5; color: var(--muted);
  border-top: 1px solid var(--line); margin-top: 9px; padding-top: 8px;
}}

.afi-bot-ev {{
  border: 1px solid var(--line); border-radius: 11px;
  background: var(--bg); padding: 10px; margin-bottom: 9px;
}}
.afi-bot-ev-head {{
  display: flex; justify-content: space-between; gap: 8px;
  font-size: 11px; font-weight: 750; color: #475569; margin-bottom: 8px;
}}
.afi-bot-ev-head span {{ color: var(--muted); font-weight: 600; flex: none; }}
.afi-bot-ev-card {{
  background: #fff; border: 1px solid var(--line); border-radius: 9px;
  padding: 9px 10px; margin-bottom: 7px;
}}
.afi-bot-ev-card:last-child {{ margin-bottom: 0; }}
.afi-bot-ev-title {{ font-size: 12px; font-weight: 650; line-height: 1.4; }}
.afi-bot-ev-meta {{
  display: flex; flex-wrap: wrap; gap: 4px; margin: 6px 0;
}}
.afi-bot-ev-quote {{
  font-size: 11.5px; line-height: 1.5; color: #334155; font-style: italic;
  border-left: 2px solid var(--blue); padding-left: 8px; margin-bottom: 6px;
}}
.afi-bot-ev-card .afi-source {{ font-size: 11px; }}

.afi-bot-qhead {{
  font-size: 11px; font-weight: 750; color: #475569;
  text-transform: uppercase; letter-spacing: .04em; margin: 14px 0 7px;
}}
/* Question buttons: full-width cards, wrapping rather than truncating, so the
   exact question a reader clicks is the exact question they read. */
.st-key-afi_assistant_questions [data-testid="stElementContainer"] {{
  margin-bottom: 6px !important;
}}
.st-key-afi_assistant_questions button {{
  width: 100% !important; text-align: left !important;
  justify-content: flex-start !important;
  white-space: normal !important; height: auto !important;
  min-height: 0 !important; padding: 8px 11px !important;
  border: 1px solid var(--line) !important; border-radius: 10px !important;
  background: #fff !important; color: var(--ink) !important;
}}
.st-key-afi_assistant_questions button p {{
  font-size: 12px !important; font-weight: 600 !important;
  line-height: 1.45 !important; text-align: left !important;
}}
.st-key-afi_assistant_questions button:hover {{
  border-color: var(--blue) !important; background: var(--blue-soft) !important;
}}

.st-key-afi_assistant_controls [data-testid="stElementContainer"],
[class*="st-key-afi_assistant_evctl_"] [data-testid="stElementContainer"] {{
  margin-bottom: 6px !important;
}}
.st-key-afi_assistant_controls button,
[class*="st-key-afi_assistant_evctl_"] button {{
  border-radius: 9px !important; border: 1px solid var(--line) !important;
  background: #fff !important; padding: 5px 11px !important;
  min-height: 0 !important;
}}
.st-key-afi_assistant_controls button p,
[class*="st-key-afi_assistant_evctl_"] button p {{
  font-size: 11.5px !important; font-weight: 650 !important;
}}
.st-key-afi_assistant_controls {{ margin-top: 10px !important; }}

.afi-bot-foot {{
  margin-top: 14px; border-top: 1px solid var(--line); padding-top: 10px;
}}
.afi-bot-foot-title {{
  font-size: 10.5px; font-weight: 750; color: var(--blue);
  text-transform: uppercase; letter-spacing: .04em;
}}
.afi-bot-foot p {{
  font-size: 10.5px !important; line-height: 1.55; color: var(--muted);
  margin: 4px 0 0 !important;
}}

/* Hidden proxies for the "View supporting records" links, off-screen for the
   same reason as the dashboard's: a programmatic click must reach a live
   button, and these must stay out of the tab order. */
[class*="st-key-afi_assistant_ev_"] {{
  position: absolute !important; width: 1px; height: 1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap;
}}

@media (max-width: 650px) {{
  .st-key-afi_assistant_launcher {{ right: 16px; bottom: 72px; }}
  .st-key-afi_assistant_panel {{
    right: 8px; left: 8px; bottom: 140px;
    width: auto; max-width: calc(100vw - 16px);
    max-height: min(78vh, calc(100vh - 206px));
  }}
}}
</style>
"""
