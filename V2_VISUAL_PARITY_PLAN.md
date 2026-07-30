# V2 Visual Parity Plan

Bringing the Streamlit app to visual parity with `action_feedback_solution_mockup.html`.
Mockup is the source of truth for layout and styling. V2 requirements are the source of
truth for data, labels, filters and functionality.

---

## UI inventory — current app vs. whitelist

Current Dashboard renders 10 sections. The whitelist allows 8 elements.

| # | Current section | Verdict |
|---|---|---|
| 1 | `st.title` "What to build next for Port Actions…" | **Restyle** → hero (eyebrow + h1 + subtitle + Analysis run box) |
| 2 | 4 `st.metric` KPIs | **Restyle** → mockup KPI cards; relabel to the 4 approved labels |
| 3 | "Recommended product actions" | **Reposition + restyle** → left column of content grid, blue gradient panel |
| 4 | "Where the problems concentrate" (Plotly + drill table) | **Rename + reposition** → "Matching feedback by taxonomy category", right column, CSS bars |
| 5 | "Where in the journey users get stuck" (Plotly) | **Rename + reposition** → "Matching feedback by Journey stage", right column below category chart |
| 6 | "What kind of problems these are" (problem-type table) | **Remove from UI** (stays a filter; `problem_type_table()` kept in backend) |
| 7 | "Who is asking" (persona table) | **Remove from UI** (persona becomes a *More filters* control; `persona_table()` kept) |
| 8 | "Primary owner vs. also implicated" | **Remove from UI** (secondary labels stay on feedback cards; `secondary_table()` kept) |
| 9 | "Evidence explorer" (`st.dataframe`) | **Replace** → "Feedback behind recommended actions", full-width card list |
| 10 | "How good is the AI classification?" (QA panel) | **Remove from UI** (`evaluate.score()` kept in backend) |
| — | Final comparison panel | Added for parity, then **removed** as a separate product decision |
| — | Custom top bar | **Missing — add** |

Nothing is deleted from the backend. Only the Dashboard stops rendering it.

## Native Streamlit blockers to parity

| Blocker | Fix |
|---|---|
| Default header/toolbar/footer | Hide; replaced by the custom 64px top bar |
| `block-container` padding + narrow max width | Override to `max-width: 1500px; padding: 24px 32px 48px` |
| Native collapsible sidebar sits outside the centred layout | Not used. Filter panel becomes column 1 of an `st.columns` grid forced to exactly 270px |
| `st.metric` chrome | Not used. KPI cards are HTML |
| Native tab bar is large and alters content width | Compact segmented nav styled to the mockup |
| Plotly canvas, toolbar, margins, fonts | **Plotly dropped for both charts.** The mockup's charts are CSS bars (`.category-row` + `.bar > span`), so HTML/CSS reproduces them exactly and removes every Plotly conflict |
| Widget vertical gaps | `[data-testid="stVerticalBlock"] { gap: 0 }` plus targeted margins |

## Interaction approach

Pure-HTML sections still need real interactions (category drill-down, "View supporting
feedback", back button). These use **`st.query_params`**: rendered HTML anchors carry a
query string, Streamlit re-runs and reads it. Keeps the mockup markup byte-for-byte while
staying wired to real data — no static mockup records anywhere.

Native widgets are kept for the filter panel, where they carry state and the mockup's
`<select>` styling can be matched with CSS.

## KPI definitions

The mockup's KPI labels differ from V2's. Required labels, with V2-consistent maths:

| Label | Definition |
|---|---|
| Product actions | Distinct (category, subcategory) groups in the filtered in-scope set |
| Open product actions | Groups that are *entirely* unmet — nothing in them completed or closed |
| High severity | Filtered records at severity ≥ 4 |
| Needs human review | Filtered records flagged by the classifier |

Ranking itself is unchanged: still open-records-only, still lexicographic over the six keys.

## File plan

| File | Role |
|---|---|
| `src/ui/theme.py` | Design tokens + the full CSS sheet + Streamlit-default overrides |
| `src/ui/render.py` | `render_topbar`, `render_hero`, `render_kpis`, `render_product_actions`, `render_taxonomy_chart`, `render_journey_chart`, `render_feedback_cards` |
| `app.py` | Orchestration, filter panel, navigation, Guide view |
| `scripts/capture_parity.py` | Repeatable side-by-side screenshots at 1440×1200 and 390×844 |
| `tests/test_ui.py` | Whitelist, section order, no-Scope-filter, breakpoints, real-data checks |
