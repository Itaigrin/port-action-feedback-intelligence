# V2 Visual Parity Report

Comparison of the Streamlit dashboard against `docs/action_feedback_solution_mockup.html`.

Repeatable capture: `python -m scripts.capture_parity` (needs the app on :8504).
Screenshots and raw geometry: `docs/parity/`.

---

## Screenshots created

| File | What it shows |
|---|---|
| `docs/parity/mockup-desktop.png` / `app-desktop.png` | 1440×1200 side by side |
| `docs/parity/mockup-mobile.png` / `app-mobile.png` | 390×844 side by side |
| `docs/parity/*-full.png` | Full-page versions of all four |
| `docs/parity/app-feedback-section.png` | Feedback cards at full width |
| `docs/parity/app-comparison.png` | Final comparison panel |
| `docs/parity/geometry.json` | Measured box for every probed element |

## Measured geometry — desktop, 1440×1200

`width × height @ x,y`

| Element | Mockup | App | Δ |
|---|---|---|---|
| Top bar | 1440×64 @0,0 | 1440×64 @0,0 | **exact** |
| Filter rail | 270×767 @32,88 | 270×676 @32,88 | width/x/y **exact** |
| Hero | 1082×106 @326,88 | 1082×134 @326,88 | width/x/y **exact** |
| KPI row | 1082×142 @326,216 | 1082×142 @326,230 | width **exact**, y +14 |
| KPI card | 260×142 | 260×142 | **exact** |
| Actions panel | 690×1928 @326,378 | 693×2802 @326,378 | x/y **exact**, w +3 |
| Charts panel | 372×461 @1036,378 | 369×1234 @1039,378 | y **exact**, x +3 |
| Feedback section | 1082×2804 @326 | 1082×10223 @326 | width/x **exact** |
| Comparison panel | 1082×214 @326 | 1082×250 @326 | width/x **exact** |

## Measured geometry — mobile, 390×844

Every section stacks to 354 wide at x=18, matching the mockup exactly. No
horizontal page scroll at either breakpoint.

## Differences found and corrected

| # | Difference | Cause | Fix |
|---|---|---|---|
| 1 | Filter rail 246px and 13,534px tall | Streamlit columns are equal-height flex children | `st.container(key="afi_rail")` + `align-self: flex-start`, `height: fit-content`, sticky at 88px |
| 2 | Main content wrapped *below* the rail | Second column had an intrinsic min-width floor | `flex: 1 1 0; min-width: 0` on the last column, `flex-wrap: nowrap` on the row |
| 3 | Content started 49px too low | Native tab strip occupied 35px + 14px panel padding | Only the tab strip is pinned into the top bar; panels stay in flow |
| 4 | Feedback card wrapper did not contain the cards | Open and close tags were in separate `st.markdown` calls, and Streamlit balances each block independently | One keyed container, `.st-key-afi_feedback`, styled as the card |
| 5 | Nav styling had no effect at all | Targeted `[data-baseweb="tab-list"]`; Streamlit 1.60 emits `[role="tablist"]` | Switched to ARIA-role selectors, which are part of the accessibility contract and outlive component-library changes |
| 6 | Mobile did not stack — columns squeezed to 60px | The `:first-child` desktop rule outranked the media-query rule on specificity | Media query now matches `:first-child`/`:last-child` too |
| 7 | Chart rows rendered as blue underlined hyperlinks | Streamlit's global `a` styling overrode the row style | Explicit `!important` colour/decoration resets on `.afi-category-row`, `.afi-source`, `.afi-action-btn` |
| 8 | Nested white card inside the filter rail | An inner `.afi-panel` inside the already-panelled rail | Inner panel border/shadow/padding zeroed |
| 9 | KPI 1 and KPI 2 both showed 54 | "Open product actions" counted groups *containing* an open record — which is all of them | Redefined as groups that are **entirely** unmet (no completed or closed record): 54 → 37 |
| 10 | Stylesheet edits appeared not to apply | `CSS` is a module-level constant, so the running server held the old import | Server restart between capture runs |

## Remaining differences, and why

| Difference | Reason |
|---|---|
| Section **heights** differ throughout (e.g. feedback 10,223px vs 2,804px) | Content, not layout. The mockup holds 11 sample records; the app renders 182 in-scope records and 54 product actions. Widths, x-positions and section order all match. |
| KPI row sits 14px lower | The real hero subtitle wraps to two lines where the mockup's fits on one. Driven by real run metadata. |
| Actions panel 3px wider, charts panel 3px narrower | Streamlit's column gap resolves to a slightly different sub-pixel split than the mockup's CSS grid. Not visible. |
| Rail is shorter than the mockup's | The mockup's Scope filter was removed per the V2 requirements, so there is one control fewer. |

No unavoidable Streamlit limitation was left in place as a layout difference.

## Charts: Plotly was removed

The mockup's "charts" are CSS bars (`.category-row` + `.bar > span`), not a
plotting library. Reproducing them as HTML/CSS matches the mockup exactly and
removes every Plotly conflict the brief lists — canvas background, toolbar,
margins, fonts, legend. `plotly` no longer appears in `app.py` or `src/ui/`, and
a test asserts that.

## Interactions verified live

| Interaction | Result |
|---|---|
| Category bar click → subcategory drill-down | `?cat=Permissions & Approvals` → breadcrumb "Categories › Permissions & Approvals" + 8 subcategory rows |
| `View supporting feedback ↓` | `?focus=RBAC & dynamic permissions` → 13 records, filter-state line updated, back control shown |
| `← Back to filtered view` | Clears the query params and restores the filtered view |
| Feedback card contents | Recommended-action block, verified quote, and all labels including `Secondary:` present |

## Tests

`python -m pytest tests/ -q` → **58 passed**

`tests/test_ui.py` (21 new) covers: no Scope filter, exactly four KPIs with the
approved labels, no legacy KPI, exact chart titles, no Plotly and no old Theme
chart, chronological journey order, dashboard section order, separate
Category/Subcategory controls, filter-panel order, Top-actions default of 10,
Source/Status/Created-date rendered separately, banned metadata absent, the
comparison panel, the Guide as a separate view, both responsive breakpoints,
design tokens matching the mockup, Streamlit defaults neutralised, and that the
UI renders pipeline data rather than hardcoded markup.

### One test I had wrong

`test_ui_uses_real_data_not_mockup_records` originally asserted that no mockup
record title appears in the dataset. It failed — because **the mockup's sample
records are real roadmap.port.io posts**, not invented ones, so the overlap is
expected. The test now checks the mechanism instead: no static record markup in
the source, and a rendered card reproducing the values held in `analyzed.json`.
