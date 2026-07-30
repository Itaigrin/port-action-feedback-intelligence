"""Design tokens and the stylesheet that gives Streamlit the mockup's shell.

Values here are lifted from action_feedback_solution_mockup.html rather than
re-derived, so the two cannot drift apart by eye. Anything that exists only to
neutralise a Streamlit default is grouped at the bottom and labelled, because
that is the part most likely to break on a Streamlit upgrade.
"""

from __future__ import annotations

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
.afi-kpis {{
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 14px; margin-bottom: 20px;
}}
.afi-kpi {{
  padding: 16px; box-shadow: none; background: rgba(255,255,255,.78);
  border: 1px solid var(--line); border-radius: 14px;
}}
.afi-kpi .label {{ color: var(--muted); font-size: 12px; }}
.afi-kpi .value {{
  display: block; font-size: 27px; font-weight: 750;
  letter-spacing: -.04em; margin: 4px 0;
}}
.afi-kpi .detail {{ font-size: 12px; color: var(--muted); }}
.afi-kpi .detail.good {{ color: var(--green); }}
.afi-kpi .detail.warning {{ color: var(--amber); }}

/* ----------------------------------------------------------------- badges */
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
/* The card whose records the feedback section is currently showing. */
.afi-action-btn.is-selected {{
  background: var(--blue); border-color: var(--blue); color: #fff !important;
}}
.afi-action-btn.is-selected:hover {{
  background: #1d54c9; border-color: #1d54c9; color: #fff !important;
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
   Still used by the Guide for confusion pairs and the severity/persona split.
   The dashboard's comparison panel was removed as a product decision and its
   wrapper rule went with it; these shared rules did not. */
.afi-comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.afi-comparison > div {{ border-radius: 10px; padding: 13px; }}
.afi-comparison .old {{ background: #fff7ed; border: 1px solid #fed7aa; }}
.afi-comparison .new {{ background: #effcf7; border: 1px solid #bbf7d0; }}
.afi-comparison ul {{ margin: 8px 0 0; padding-left: 18px; color: #475569; }}
.afi-comparison li {{ margin-bottom: 3px; }}

/* -------------------------------------------------------------- guide tab */
.afi-guide-h2 {{ font-size: 20px; letter-spacing: -.02em; margin: 0 0 6px; }}

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
.st-key-afi_page [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
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
.st-key-afi_hidden_nav {{
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
  .afi-content-grid {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 650px) {{
  .afi-topbar {{ padding: 0 16px; }}
  .afi-hero {{ display: block; }}
  .afi-section-head {{ display: block; }}
  .afi-run-meta {{ margin-top: 12px; }}
  .afi-kpis {{ grid-template-columns: 1fr; }}
  .afi-comparison {{ grid-template-columns: 1fr; }}
  .afi-search {{ margin-top: 10px; }}
}}
</style>
"""
