"""Port Action Feedback Intelligence -- two-view Streamlit app.

An independent take-home project. Not an official Port product.

View 1 "Dashboard" -- ranked product actions, each opening onto the feedback
       records that argue for it. Layout follows
       docs/action_feedback_solution_mockup.html.
View 2 "Themes & Journey Stages Guide" -- plain-language reference for readers
       with no software or DevOps background.

Reads only from data/processed/. No API key, no network calls, no LLM at
runtime -- the classification results are committed, so this opens and renders
identically on any machine.

All taxonomy definitions come from src/models/taxonomy.py, every count comes
from src/analysis/aggregate.py, and all markup comes from src/ui/. Nothing here
defines a category or computes a statistic of its own.

    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.analysis.aggregate import (
    COUNTED_STATUSES,
    HIGH_SEVERITY,
    RANK_KEYS,
    evidence_for_action,
    negative_trend,
    paired_insights,
    product_actions,
)
from src.models.taxonomy import (
    CATEGORY_FOR_SUBCATEGORY,
    CATEGORY_NAMES,
    GLOSSARY,
    LIFECYCLE_STATUSES,
    PERSONA_NAMES,
    PERSONAS,
    PROBLEM_TYPE_NAMES,
    SEVERITY_SCALE,
    STAGE_GUIDE,
    STAGE_NAMES,
    SUBCATEGORY_NAMES_BY_CATEGORY,
    TAXONOMY,
)
from src.ui import data_assistant, render, theme

ROOT = Path(__file__).parent
PROC = ROOT / "data" / "processed"

DEFAULT_TOP_ACTIONS = 10

# The detail behind the one-line summary on the actions panel. Kept as a
# constant so the copy is readable, and shown in an expander rather than on the
# cards: the ranking has to be checkable, but it should not compete with the
# recommendations for attention.
RANKING_HELP = """
Only **open** feedback counts. Feedback asking for the same change is grouped
together, and groups are ranked by typical severity, open records, average
confidence, source diversity and recency - in that order.

- **Typical severity** is the *median* of the supporting records, not the worst
  one, so a single severe report cannot make a mild request look like a blocker.
- **Open records** are the exact records supporting that action - not everything
  sharing its category or subcategory.
- **Average confidence** is how sure the classifier was, used only to separate
  otherwise equal actions.
- **Source diversity** counts distinct sources, so one source repeating itself
  does not count twice.
- **Recency** uses the date the feedback was raised, not the date it was
  analysed.

The ranking is **hierarchical, not a blended score**: each point is applied in
turn and the first one that differs decides the position, so no later point can
override an earlier one.
"""

st.set_page_config(
    page_title="Action Feedback Intelligence",
    page_icon="⌁",
    layout="wide",
    initial_sidebar_state="collapsed",
)
# theme.CSS, not a `from theme import CSS` value binding. `from X import VALUE`
# copies the string into this module's globals at import time, so a hot reload
# that refreshes the theme module leaves this copy pointing at the old
# stylesheet -- which is how a deploy ended up running new Python against the
# previous release's CSS, with the assistant rendered but unstyled. Reading the
# attribute follows the reload.
st.markdown(theme.CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
@st.cache_data
def load() -> tuple[pd.DataFrame, dict]:
    """Load the classified records.

    aggregates.json is deliberately not read here. The dashboard recomputes
    product actions from the records so that filters work, and the ranking
    labels come from RANK_KEYS -- so the app depends on the committed records
    plus this code, and nothing else. Reading presentation text out of a
    generated artifact meant a deploy that shipped new code against an older
    artifact crashed on a missing key.
    """
    analyzed = json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))
    return pd.DataFrame(analyzed["records"]), analyzed["meta"]


try:
    df, amet = load()
except FileNotFoundError:
    st.error(
        "Processed data not found. Run the pipeline first:\n\n"
        "```\npython -m src.collectors.run\n"
        "python -m src.analysis.clean\n"
        "python -m src.analysis.classify\n"
        "python -m src.analysis.aggregate\n```"
    )
    st.stop()

# The dashboard is permanently restricted to in-scope records. There is no
# Scope control: a toggle that could fold out-of-scope feedback back into a
# demand ranking is an invitation to misread it.
rel = df[df["is_relevant"]].copy()
rel["is_open"] = rel["lifecycle_status"].isin(COUNTED_STATUSES)
rel["is_high_severity"] = rel["severity"] >= HIGH_SEVERITY

OUT_OF_SCOPE = int(len(df) - len(rel))


# --------------------------------------------------------------------------
# Filter panel -- column 1 of the page grid, not Streamlit's native sidebar
# --------------------------------------------------------------------------
# Every filter widget with the value it resets to. Kept as one mapping so the
# reset cannot drift away from the widgets it is meant to clear.
FILTER_DEFAULTS: dict[str, object] = {
    "f_status": [],
    "f_problem": [],
    "f_stage": [],
    "f_category": [],
    "f_subcategory": [],
    "f_persona": [],
    "f_review": "All",
    "f_search": "",
    "f_severity": 1,
    "f_top_n": DEFAULT_TOP_ACTIONS,
}


def _reset_filters() -> None:
    """Clear every filter widget.

    Two things here are load-bearing.

    It runs as a button callback, which Streamlit executes *before* the next
    script run creates any widget. Assigning a widget-bound key *after* its
    widget exists in the same run raises StreamlitAPIException -- which is what
    the previous inline version did, and why the button crashed.

    It *assigns* defaults rather than deleting the keys. Deleting clears the
    Python value but leaves the browser holding its own widget state, so the
    data reset while the selected chips stayed on screen. Assigning pushes the
    new value to the frontend as well.
    """
    for key, value in FILTER_DEFAULTS.items():
        st.session_state[key] = value
    # Reset also drops the chart drill-down and the focused action, so the
    # dashboard returns to the state a first-time visitor sees.
    st.session_state["afi_drill"] = None
    st.session_state["afi_focus"] = None
    st.session_state["afi_scroll_nonce"] = 0


def render_filter_panel() -> dict:
    """Render the compact filter rail and return the current selections."""
    st.markdown(
        '<div class="afi-panel" style="padding:17px">'
        '<h2 style="font-size:17px;letter-spacing:-.02em;margin:0 0 6px">'
        "Filters</h2>"
        '<p style="margin:0 0 14px;color:#64748b;font-size:12px">'
        "Filters affect the recommended actions, the charts and the records "
        "together.</p></div>",
        unsafe_allow_html=True,
    )

    status = st.multiselect(
        "Lifecycle status",
        [s for s in LIFECYCLE_STATUSES if s in set(rel["lifecycle_status"])],
        key="f_status",
    )
    problem = st.multiselect(
        "Problem type",
        [p for p in PROBLEM_TYPE_NAMES if p in set(rel["problem_type"].dropna())],
        key="f_problem",
    )
    stage = st.multiselect(
        "Journey stage",  # chronological order, never alphabetical
        [s for s in STAGE_NAMES if s in set(rel["journey_stage"].dropna())],
        key="f_stage",
    )

    # Clicking a category only opens its subcategories in the chart; it must
    # not rewrite the filters, or the reader loses the selection they built.
    present_categories = [c for c in CATEGORY_NAMES
                          if c in set(rel["primary_taxonomy_category"].dropna())]
    category = st.multiselect("Category", present_categories, key="f_category")

    present_subs = set(rel["primary_taxonomy_subcategory"].dropna())
    sub_pool = [
        s
        for c in (category or present_categories)
        for s in SUBCATEGORY_NAMES_BY_CATEGORY[c]
        if s in present_subs
    ]
    subcategory = st.multiselect("Subcategory", sub_pool, key="f_subcategory")

    severity = int(st.session_state.get("f_severity", 1))
    st.markdown(
        '<label class="afi-filter-label">Minimum severity</label>'
        + render.render_severity_slider(severity)
        + '<p class="afi-rubric">1 = minor friction · 3 = meaningful '
          "workaround · 5 = blocker</p>",
        unsafe_allow_html=True,
    )

    top_n = st.number_input(
        "Top Recommended product actions", min_value=1, max_value=54,
        value=DEFAULT_TOP_ACTIONS, step=1, key="f_top_n",
    )

    st.button("Reset all filters", key="f_reset", on_click=_reset_filters)

    with st.expander("More filters"):
        persona = st.multiselect(
            "Persona",
            [p for p in PERSONA_NAMES if p in set(rel["persona"].dropna())],
            key="f_persona",
        )
        review = st.selectbox(
            "Confidence / review state",
            ["All", "Needs human review", "High confidence (0.85+)",
             "Medium confidence (0.70-0.84)", "Low confidence (<0.70)"],
            key="f_review",
        )

    with st.expander("View full Category - Subcategory"):
        for name, block in TAXONOMY.items():
            subs = "".join(f"<li>{s}</li>" for s in block["subcategories"])
            st.markdown(
                f'<details style="border-bottom:1px solid #eef2f7;padding:5px 0">'
                f'<summary style="cursor:pointer;font-weight:700;font-size:12px">'
                f"{name}</summary>"
                f'<ul style="margin:5px 0 1px;padding-left:16px;color:#475569;'
                f'font-size:12px">{subs}</ul></details>',
                unsafe_allow_html=True,
            )

    # How the ranking works, stated where the reader is already deciding what
    # to trust. The list comes straight from RANK_KEYS -- the same constant the
    # sort uses -- so it cannot drift, and it shows each key's plain label
    # rather than its field name, because a rail reading "severity_band"
    # explains nothing to the person this guide is written for.
    #
    # Read from the code, not from aggregates.json. That artifact is regenerated
    # by the pipeline, so a deploy carrying new code alongside an older artifact
    # would raise KeyError on a field the old file never had.
    keys = "".join(f"<li>{label}</li>" for _key, label, _why in RANK_KEYS)
    st.markdown(
        '<div class="afi-rank-note">'
        "<b>How the recommended product actions are ordered</b>"
        "<p>Only feedback that is <b>still open</b> counts.</p>"
        "<p>Feedback asking for the same change is grouped together. The groups "
        "are then compared on each point below, in order - the first point "
        "where they differ decides which comes first:</p>"
        f"<ol>{keys}</ol>"
        "</div>",
        unsafe_allow_html=True,
    )

    return {
        "status": status, "problem": problem, "stage": stage,
        "category": category, "subcategory": subcategory,
        "severity": severity, "top_n": int(top_n),
        "persona": persona, "review": review,
    }


def apply_filters(f: dict, search: str) -> pd.DataFrame:
    view = rel
    if f["status"]:
        view = view[view["lifecycle_status"].isin(f["status"])]
    if f["problem"]:
        view = view[view["problem_type"].isin(f["problem"])]
    if f["stage"]:
        view = view[view["journey_stage"].isin(f["stage"])]
    if f["category"]:
        view = view[view["primary_taxonomy_category"].isin(f["category"])]
    if f["subcategory"]:
        view = view[view["primary_taxonomy_subcategory"].isin(f["subcategory"])]
    if f["persona"]:
        view = view[view["persona"].isin(f["persona"])]

    review = f["review"]
    if review == "Needs human review":
        view = view[view["needs_human_review"]]
    elif review == "High confidence (0.85+)":
        view = view[view["confidence"] >= 0.85]
    elif review == "Medium confidence (0.70-0.84)":
        view = view[(view["confidence"] >= 0.70) & (view["confidence"] < 0.85)]
    elif review == "Low confidence (<0.70)":
        view = view[view["confidence"] < 0.70]

    view = view[view["severity"] >= f["severity"]]

    if search:
        needle = search.strip().lower()
        haystack = (
            view["title"].fillna("") + " "
            + view["short_summary"].fillna("") + " "
            + view["suggested_product_action"].fillna("") + " "
            + view["evidence_excerpt"].fillna("")
        ).str.lower()
        view = view[haystack.str.contains(needle, regex=False)]
    return view.copy()


# --------------------------------------------------------------------------
# Navigation
#
# The chart rows and action buttons are mockup HTML, but they must behave like
# Streamlit controls. Each carries a data-afi-click naming a hidden button; one
# delegated listener forwards the click. That keeps the interaction inside a
# normal rerun -- the earlier query-parameter links navigated the browser, which
# tore the page down and repainted Streamlit's shell (the black flash, and the
# moment of unstyled content that looked like a stray heading).
#
# Every handler is an on_click callback, so it runs before the next script run
# creates any widget and may therefore assign widget-bound keys.
# --------------------------------------------------------------------------
CLICK_FORWARDER = """
<script>
const doc = window.parent.document;
if (!doc.__afiClickBound) {
  doc.__afiClickBound = true;
  doc.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-afi-click]');
    if (!trigger) return;
    event.preventDefault();
    const button = doc.querySelector(
      '.st-key-' + trigger.dataset.afiClick + ' button');
    if (button) button.click();
  }, true);

  // The severity range proxies to one hidden button per level.
  //
  // A commit click reruns the script, and the rerun replaces this <input>
  // with a freshly rendered one -- st.markdown() re-emits the whole element,
  // it does not patch the existing DOM node. Committing on every 'input'
  // (debounced or not) meant that a drag slower than the debounce -- any
  // ordinary human drag -- got its node swapped out from under the pointer
  // while the mouse button was still down. The browser's implicit pointer
  // capture was on the node that just got removed, so the thumb stopped
  // following the cursor for the rest of that gesture. Arrow keys never hold
  // the pointer down, so they never hit this and always looked fine.
  //
  // The fix is to never commit while the pointer is down. The pill still
  // updates live on every 'input' (pure client-side, no rerun), so dragging
  // tracks the cursor the whole way; the commit itself waits for the
  // pointer to come back up. Keyboard stepping has no pointerdown to wait
  // for, so it keeps the debounce -- a range inside injected markup does not
  // deliver 'change' to this listener, only 'input', so the debounce is
  // still what stands in for "the value has settled" there.
  let sevDragSlider = null;

  doc.addEventListener('pointerdown', (event) => {
    const slider = event.target.closest('[data-afi-sev]');
    if (slider) sevDragSlider = slider;
  }, true);

  const commitSeverity = (slider) => {
    const button = doc.querySelector(
      '.st-key-' + slider.dataset.afiSev + '_' + slider.value + ' button');
    if (button) button.click();
  };

  doc.addEventListener('input', (event) => {
    const slider = event.target.closest('[data-afi-sev]');
    if (!slider) return;
    const pill = slider.parentElement.querySelector('.afi-range-value');
    if (pill) pill.textContent = slider.value;
    if (sevDragSlider === slider) return;
    clearTimeout(doc.__afiSevTimer);
    doc.__afiSevTimer = setTimeout(() => commitSeverity(slider), 300);
  }, true);

  const endSevDrag = () => {
    if (!sevDragSlider) return;
    const slider = sevDragSlider;
    sevDragSlider = null;
    clearTimeout(doc.__afiSevTimer);
    commitSeverity(slider);
  };
  doc.addEventListener('pointerup', endSevDrag, true);
  doc.addEventListener('pointercancel', endSevDrag, true);
}
</script>
"""


def _drill_into(category: str) -> None:
    st.session_state["afi_drill"] = category


def _clear_drill() -> None:
    st.session_state["afi_drill"] = None


def _select_subcategory(subcategory: str) -> None:
    """A subcategory click sets both taxonomy filters, per the requirements."""
    st.session_state["f_category"] = [CATEGORY_FOR_SUBCATEGORY[subcategory]]
    st.session_state["f_subcategory"] = [subcategory]
    st.session_state["afi_drill"] = None


def _focus_on(action_id: str) -> None:
    """Select a product action by its stable id.

    The id, not a subcategory: selecting a subcategory is what made the
    drill-down show every record in it rather than the ones supporting the
    action the reader clicked.

    Not a toggle. The button's job is to take the reader to the evidence, so
    pressing it again should land them there again rather than silently
    clearing the selection. "Back to filtered view" is what clears it.

    The nonce is bumped on *every* press, including a repeat press on the
    already-selected action. It is what makes the scroll fire again -- see
    the scroll block in render_dashboard.
    """
    st.session_state["afi_focus"] = action_id
    st.session_state["afi_scroll_nonce"] = (
        st.session_state.get("afi_scroll_nonce", 0) + 1)


def _clear_focus() -> None:
    st.session_state["afi_focus"] = None


def _set_severity(level: int) -> None:
    """Severity has no Streamlit widget, so this key is ours to assign freely."""
    st.session_state["f_severity"] = level


def render_hidden_nav(bar_rows: list[tuple[str, int]], drilled: str | None,
                      actions: list[dict]) -> None:
    """Render the buttons the HTML proxies target. Hidden, never tabbed to."""
    components.html(CLICK_FORWARDER, height=0)
    with st.container(key="afi_hidden_nav"):
        prefix = render.NAV_SUB if drilled else render.NAV_DRILL
        handler = _select_subcategory if drilled else _drill_into
        for index, (name, _count) in enumerate(bar_rows):
            st.button("go", key=f"{prefix}_{index}",
                      on_click=handler, args=(name,))
        st.button("go", key=render.NAV_BACK, on_click=_clear_drill)
        st.button("go", key=render.NAV_UNFOCUS, on_click=_clear_focus)
        for level in range(1, 6):
            st.button("go", key=f"{render.NAV_SEV}_{level}",
                      on_click=_set_severity, args=(level,))
        for index, action in enumerate(actions):
            st.button("go", key=f"{render.NAV_FOCUS}_{index}",
                      on_click=_focus_on, args=(action["product_action_id"],))


# ==========================================================================
# Dashboard
# ==========================================================================
def render_dashboard() -> None:
    focus = st.session_state.get("afi_focus")
    drilled = st.session_state.get("afi_drill")

    # --- page grid: 270px rail + main content ------------------------------
    # Keyed containers emit stable .st-key-<key> classes, which the stylesheet
    # targets instead of autogenerated test ids.
    page = st.container(key="afi_page")
    rail, main = page.columns([270, 1160], gap="medium")

    with rail:
        with st.container(key="afi_rail"):
            filters = render_filter_panel()

    with main:
        search = st.session_state.get("f_search", "")
        view = apply_filters(filters, search)

        # The assistant renders at shell level, after both tabs, so it cannot
        # call apply_filters itself without importing app.py back into itself.
        # Recording the ids here hands it the same filtered scope without a
        # second filter implementation.
        st.session_state["afi_view_ids"] = list(view["feedback_id"])

        # Every product action in view, and the subset with live demand. Both
        # are counted here so the two KPIs are genuinely different numbers.
        # Both KPIs come from the action groups themselves. "Product actions"
        # counts every distinct requested change in view; "open" counts those
        # with at least one record still Open, which is what gets ranked.
        actions_df = product_actions(view)
        actions = actions_df.to_dict("records") if len(actions_df) else []

        # The quote shown on a card must come from that action's own records,
        # selected by id -- picking by subcategory would quote a record the
        # action does not include.
        for action in actions:
            supporting = view[
                view["feedback_id"].astype(str).isin(
                    action["open_supporting_feedback_ids"])
                & view["evidence_verified"]
            ].sort_values("severity", ascending=False)
            action["signal"] = (f'“{supporting.iloc[0]["evidence_excerpt"]}”'
                                if len(supporting) else "")

        st.markdown(render.render_hero(amet, len(rel), OUT_OF_SCOPE),
                    unsafe_allow_html=True)
        st.markdown(
            render.render_kpis(
                product_actions=int(actions_df.attrs.get("total_groups",
                                                         len(actions))),
                open_actions=len(actions),
                high_severity=int(view["is_high_severity"].sum()),
                needs_review=int(view["needs_human_review"].sum()),
            ),
            unsafe_allow_html=True,
        )

        # --- where users struggle most ------------------------------------
        # Built from the filtered frame, so both cards and the trend move with
        # every filter. "Top recommended product actions" is deliberately not
        # applied: it limits how many actions are listed, not which feedback
        # exists.
        st.markdown(
            render.render_insight_cards(**paired_insights(
                view,
                stages=filters["stage"],
                subcategories=filters["subcategory"],
            )),
            unsafe_allow_html=True,
        )
        st.markdown(render.render_trend_chart(negative_trend(view)),
                    unsafe_allow_html=True)

        # Chart rows are computed before the grid so the hidden nav buttons and
        # the rendered bars are built from one list and cannot fall out of step.
        if drilled and drilled in set(view["primary_taxonomy_category"]):
            counts = (view[view["primary_taxonomy_category"] == drilled]
                      ["primary_taxonomy_subcategory"].value_counts())
        else:
            drilled = None
            counts = view["primary_taxonomy_category"].value_counts()
        bar_rows = [(name, int(n)) for name, n in counts.items()]

        render_hidden_nav(bar_rows, drilled, actions[:filters["top_n"]])

        # --- content grid: actions left, charts right ---------------------
        content = st.container(key="afi_content")
        left, right = content.columns([1.3, 0.7], gap="medium")


        with left:
            st.markdown(
                render.render_product_actions(
                    actions, filters["top_n"], selected=focus),
                unsafe_allow_html=True,
            )

            # The detail behind the one-line summary on the panel. An expander
            # rather than card copy: the ranking has to be checkable, but it
            # should not compete with the recommendations for attention.
            with st.container(key="afi_rank_help"):
                with st.expander("How this ranking works"):
                    st.markdown(RANKING_HELP)

        with right, st.container(key="afi_charts"):
            st.markdown(render.render_taxonomy_chart(bar_rows, drilled),
                        unsafe_allow_html=True)

            stage_counts = view["journey_stage"].value_counts().to_dict()
            stage_rows = [(s, int(stage_counts.get(s, 0))) for s in STAGE_NAMES]
            st.markdown(render.render_journey_chart(stage_rows),
                        unsafe_allow_html=True)

        # --- feedback, full width -----------------------------------------
        # Selecting an action narrows this section to the records that action
        # was ranked from -- its open ones, matching the count on its card.
        # Filtering by subcategory instead would list completed work under a
        # card reading "N open supporting records".
        shown = view
        selected_action = None
        if focus:
            selected_action = next(
                (a for a in actions if a["product_action_id"] == focus), None)
            if selected_action:
                # Exactly the ids the card counted -- never the subcategory.
                shown = pd.DataFrame(
                    evidence_for_action(
                        view, selected_action["open_supporting_feedback_ids"]))
            else:
                shown = view.iloc[0:0]

        with st.container(key="afi_feedback"):
            head, tools = st.columns([1, 0.32], gap="small")
            with head:
                st.markdown(
                    '<div><h2 style="font-size:17px;letter-spacing:-.02em;'
                    'margin:0 0 6px">Feedback behind recommended actions</h2>'
                    '<p style="margin:0;font-size:12px;color:#64748b">Inspect the '
                    "original signal, source, status, confidence and labels behind "
                    "any recommendation.</p></div>",
                    unsafe_allow_html=True,
                )
            with tools:
                st.markdown('<div class="afi-search">', unsafe_allow_html=True)
                st.text_input("Search feedback", key="f_search",
                              placeholder="Search feedback...",
                              label_visibility="collapsed")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                render.render_filter_state(
                    shown=len(shown), total=len(rel),
                    open_count=int(shown["is_open"].sum()),
                    min_severity=filters["severity"],
                    focus=(selected_action["product_action_title"]
                           if selected_action else None),
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                render.render_feedback_cards(
                    (shown.sort_values(["severity", "confidence"],
                                       ascending=[False, False])
                     if len(shown) else shown).head(40).to_dict("records")
                ),
                unsafe_allow_html=True,
            )

            if focus:
                # Take the reader to the evidence they asked for. A rerun
                # replaces the DOM and drops the scroll offset, so this both
                # performs the jump and stops the page landing at the top.
                #
                # The nonce is load-bearing. Streamlit reuses an element whose
                # content is unchanged, and this markup does not mention which
                # action is selected -- so from the second click onward the
                # iframe was never remounted and the script never ran again.
                # The selection and the section updated; only the jump was
                # missing. Varying the content forces a fresh mount every time.
                #
                # Retry: Streamlit streams the page, so the section may not
                # exist yet when the script first runs.
                nonce = st.session_state.get("afi_scroll_nonce", 0)
                components.html(
                    f"<script>const jump = {nonce};"
                    "let tries = 0;"
                    "const go = () => {"
                    "  const el = window.parent.document"
                    "    .querySelector('.st-key-afi_feedback');"
                    "  if (el) {"
                    "    el.scrollIntoView({behavior: 'smooth', block: 'start'});"
                    "  } else if (++tries < 25) { setTimeout(go, 120); }"
                    "};"
                    "setTimeout(go, 120);"
                    "</script>",
                    height=0,
                )


# ==========================================================================
# Guide
# ==========================================================================
def render_guide() -> None:
    st.markdown(
        '<div class="afi-card afi-section">'
        '<div class="afi-eyebrow">Reference</div>'
        '<h1 style="font-size:28px;letter-spacing:-.04em;margin:0 0 7px;'
        'font-weight:750">Themes &amp; Journey Stages Guide</h1>'
        '<p style="color:#64748b;margin:0">Written for a reader with no software '
        "or DevOps background. If you can tell what a user was trying to do and "
        "what stopped them, you can use this guide.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    n_sub = sum(len(v) for v in SUBCATEGORY_NAMES_BY_CATEGORY.values())
    cards = [
        ("🏷️", "Category", "Which broad part of the product needs to change.",
         f"{len(CATEGORY_NAMES)} categories"),
        ("🔎", "Subcategory", "The specific part of that area.",
         f"{n_sub} subcategories"),
        ("🧩", "Problem type", "A bug, a missing feature, a confusing experience.",
         f"{len(PROBLEM_TYPE_NAMES)} types"),
        ("📍", "Journey stage", "How far the user had got before they hit it.",
         f"{len(STAGE_NAMES)} stages"),
    ]
    st.markdown(
        '<div class="afi-kpis">'
        + "".join(
            f'<div class="afi-card afi-kpi"><span class="label">{icon} {title}</span>'
            f'<span style="display:block;margin:6px 0;font-size:13px">{body}</span>'
            f'<span class="detail">{detail}</span></div>'
            for icon, title, body, detail in cards
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    cat_counts = rel["primary_taxonomy_category"].value_counts().to_dict()
    sub_counts = rel["primary_taxonomy_subcategory"].value_counts().to_dict()

    with st.container(key="afi_guide_cats"):
        st.markdown(f'<h2 class="afi-guide-h2">'
                    f"The {len(CATEGORY_NAMES)} categories</h2>",
                    unsafe_allow_html=True)
        for n, (name, block) in enumerate(TAXONOMY.items(), 1):
            count = cat_counts.get(name, 0)
            with st.expander(f"**{n}. {name}** - {count} record"
                             f"{'s' if count != 1 else ''} · "
                             f"{len(block['subcategories'])} subcategories"):
                st.markdown(f"**{block['plain']}**")
                st.caption(f"Usual journey stage: `{block['default_stage']}`")
                for sub_name, sub in block["subcategories"].items():
                    sub_count = sub_counts.get(sub_name, 0)
                    use_for = "; ".join(sub["use_for"]) + "."
                    examples_html = "".join(
                        f'<div class="afi-subcat-example">{example}</div>'
                        for example in sub["examples"]
                    )
                    st.markdown(
                        '<div class="afi-subcat">'
                        '<div class="afi-subcat-head">'
                        f'<span class="afi-subcat-name">{sub_name}</span>'
                        f'<span class="afi-subcat-count">{sub_count} record'
                        f'{"s" if sub_count != 1 else ""}</span>'
                        "</div>"
                        f'<p class="afi-subcat-desc">{sub["plain"]}</p>'
                        f'<p class="afi-subcat-usefor"><b>Use it for:</b> {use_for}</p>'
                        f'<div class="afi-subcat-examples">{examples_html}</div>'
                        "</div>",
                        unsafe_allow_html=True,
                    )
                if block["confusable"]:
                    st.info("Most often confused with: "
                            + ", ".join(f"**{c}**" for c in block["confusable"]),
                            icon=":material/compare_arrows:")

    st.markdown(f'<div class="afi-card afi-section"><h2 class="afi-guide-h2">'
                f"The {len(STAGE_NAMES)} journey stages</h2>"
                f'<p style="color:#64748b;margin:0;font-size:12px">In the order a '
                f"user meets them. Always pick the stage where the user "
                f"<i>first</i> becomes blocked.</p></div>",
                unsafe_allow_html=True)
    stage_counts = rel["journey_stage"].value_counts().to_dict()
    for i, name in enumerate(STAGE_NAMES, 1):
        guide = STAGE_GUIDE[name]
        count = stage_counts.get(name, 0)
        st.markdown(
            f'<div class="afi-card afi-section" style="margin-top:8px;padding:14px">'
            f"<b>{i}. {name}</b> · {count} record{'s' if count != 1 else ''}"
            f'<div style="color:#475569;margin-top:6px"><i>The user is trying to:</i> '
            f"{guide['user_goal']}</div>"
            f'<div class="afi-quote" style="margin-top:8px">{guide["example"]}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    persona_counts = rel["persona"].value_counts().to_dict()
    severity_rows = "".join(
        f"<li><b>{k}</b> - {SEVERITY_SCALE[k]}</li>"
        for k in sorted(SEVERITY_SCALE, reverse=True)
    )
    persona_rows = "".join(
        f"<li><b>{name}</b> - {meaning} "
        f"<i>({persona_counts.get(name, 0)} records)</i></li>"
        for name, meaning in PERSONAS.items()
    )
    st.markdown(
        f'<div class="afi-card afi-section" style="margin-top:16px">'
        f'<h2 class="afi-guide-h2">Severity and personas</h2>'
        f'<div class="afi-comparison">'
        f'<div style="border:1px solid #e2e8f0;background:#f8fafc">'
        f"<strong>Severity</strong><ul>{severity_rows}</ul></div>"
        f'<div style="border:1px solid #e2e8f0;background:#f8fafc">'
        f"<strong>Personas</strong><ul>{persona_rows}</ul></div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    glossary_rows = "".join(f"<li><b>{t}</b> - {d}</li>" for t, d in GLOSSARY.items())
    st.markdown(
        f'<div class="afi-card afi-section" style="margin-top:16px">'
        f'<h2 class="afi-guide-h2">Glossary</h2>'
        f'<ul style="columns:2;column-gap:28px;color:#475569;padding-left:18px">'
        f"{glossary_rows}</ul></div>",
        unsafe_allow_html=True,
    )


# ==========================================================================
# Shell
# ==========================================================================
st.markdown(render.render_topbar(amet), unsafe_allow_html=True)

# The tab widget lives inside a keyed container so the stylesheet can pin it
# into the top bar. A sibling <div> would not wrap it: Streamlit renders each
# call as its own node.
with st.container(key="afi_nav"):
    tab_dashboard, tab_guide = st.tabs(
        ["Dashboard", "Themes & Journey Stages Guide"])

with tab_dashboard:
    render_dashboard()

with tab_guide:
    render_guide()

# The assistant is drawn once, outside both tabs, so the launcher and the
# conversation are the same object on the Dashboard and the Guide rather than
# two instances with diverging state.
#
# It answers with deterministic pandas over these records. No model is called
# here, so the app still starts and the assistant still works with no API key.
_view_ids = st.session_state.get("afi_view_ids")
_filtered = rel if _view_ids is None else rel[rel["feedback_id"].isin(_view_ids)]
data_assistant.render(rel, _filtered, forwarder=CLICK_FORWARDER)
