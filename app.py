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

from src.analysis.aggregate import (
    HIGH_SEVERITY,
    OPEN_STATUSES,
    product_actions,
)
from src.models.taxonomy import (
    CATEGORY_NAMES,
    CONFUSION_PAIRS,
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
    WORKED_EXAMPLES,
)
from src.ui import render
from src.ui.theme import CSS

ROOT = Path(__file__).parent
PROC = ROOT / "data" / "processed"

DEFAULT_TOP_ACTIONS = 10

st.set_page_config(
    page_title="Action Feedback Intelligence",
    page_icon="⌁",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
@st.cache_data
def load() -> tuple[pd.DataFrame, dict, dict]:
    analyzed = json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))
    aggregates = json.loads((PROC / "aggregates.json").read_text(encoding="utf-8"))
    return pd.DataFrame(analyzed["records"]), aggregates, analyzed["meta"]


try:
    df, agg, amet = load()
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
rel["is_open"] = rel["lifecycle_status"].isin(OPEN_STATUSES)
rel["is_high_severity"] = rel["severity"] >= HIGH_SEVERITY

OUT_OF_SCOPE = int(len(df) - len(rel))


# --------------------------------------------------------------------------
# Filter panel -- column 1 of the page grid, not Streamlit's native sidebar
# --------------------------------------------------------------------------
def render_filter_panel() -> dict:
    """Render the compact filter rail and return the current selections."""
    params = st.query_params

    st.markdown(
        '<div class="afi-panel" style="padding:17px">'
        '<h2 style="font-size:17px;letter-spacing:-.02em;margin:0 0 6px">'
        "Evidence filters</h2>"
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

    # A category clicked in the chart pre-seeds this control.
    present_categories = [c for c in CATEGORY_NAMES
                          if c in set(rel["primary_taxonomy_category"].dropna())]
    if params.get("cat") and params["cat"] in present_categories:
        st.session_state.setdefault("f_category", [params["cat"]])
    category = st.multiselect("Taxonomy category", present_categories, key="f_category")

    sub_pool = [
        s
        for c in (category or present_categories)
        for s in SUBCATEGORY_NAMES_BY_CATEGORY[c]
        if s in set(rel["primary_taxonomy_subcategory"].dropna())
    ]
    if params.get("sub") and params["sub"] in sub_pool:
        st.session_state.setdefault("f_subcategory", [params["sub"]])
    subcategory = st.multiselect("Taxonomy subcategory", sub_pool, key="f_subcategory")

    severity = st.slider("Minimum severity", 1, 5, 1, key="f_severity")
    st.markdown(
        '<p class="afi-rubric" style="color:#64748b;font-size:10px">'
        "1 = minor friction · 3 = meaningful workaround · 5 = blocker</p>",
        unsafe_allow_html=True,
    )

    top_n = st.number_input(
        "Top Recommended product actions", min_value=1, max_value=54,
        value=DEFAULT_TOP_ACTIONS, step=1, key="f_top_n",
    )

    if st.button("Reset all filters", key="f_reset"):
        for key in ("f_status", "f_problem", "f_stage", "f_category",
                    "f_subcategory", "f_search"):
            st.session_state.pop(key, None)
        st.session_state["f_severity"] = 1
        st.session_state["f_top_n"] = DEFAULT_TOP_ACTIONS
        st.query_params.clear()
        st.rerun()

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

    with st.expander("View full taxonomy"):
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


# ==========================================================================
# Dashboard
# ==========================================================================
def render_dashboard() -> None:
    params = st.query_params
    focus = params.get("focus")
    drilled = params.get("cat")

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

        # Every product action in view, and the subset with live demand. Both
        # are counted here so the two KPIs are genuinely different numbers.
        grouped = view.groupby(
            ["primary_taxonomy_category", "primary_taxonomy_subcategory"]
        )
        all_groups = grouped.size()
        # "Open" means the whole group is still unmet: nothing in it has been
        # completed or closed. Counting groups that merely contain an open
        # record would return the same number as the total and say nothing.
        fully_open = int(grouped["is_open"].all().sum())
        actions_df = product_actions(view)
        actions = actions_df.to_dict("records") if len(actions_df) else []

        # Attach the strongest verified quote as each action's evidence signal.
        for action in actions:
            supporting = view[
                (view["primary_taxonomy_category"] == action["category"])
                & (view["primary_taxonomy_subcategory"] == action["subcategory"])
                & (view["evidence_verified"])
            ].sort_values("severity", ascending=False)
            action["signal"] = (f'“{supporting.iloc[0]["evidence_excerpt"]}”'
                                if len(supporting) else "")

        st.markdown(render.render_hero(amet, len(rel), OUT_OF_SCOPE),
                    unsafe_allow_html=True)
        st.markdown(
            render.render_kpis(
                product_actions=int(len(all_groups)),
                open_actions=fully_open,
                high_severity=int(view["is_high_severity"].sum()),
                needs_review=int(view["needs_human_review"].sum()),
            ),
            unsafe_allow_html=True,
        )

        # --- content grid: actions left, charts right ---------------------
        content = st.container(key="afi_content")
        left, right = content.columns([1.3, 0.7], gap="medium")


        with left:
            st.markdown(
                render.render_product_actions(actions, filters["top_n"]),
                unsafe_allow_html=True,
            )

        with right, st.container(key="afi_charts"):
            if drilled and drilled in set(view["primary_taxonomy_category"]):
                counts = (view[view["primary_taxonomy_category"] == drilled]
                          ["primary_taxonomy_subcategory"].value_counts())
                rows = [(name, int(n)) for name, n in counts.items()]
            else:
                drilled = None
                counts = view["primary_taxonomy_category"].value_counts()
                rows = [(name, int(n)) for name, n in counts.items()]
            st.markdown(render.render_taxonomy_chart(rows, drilled),
                        unsafe_allow_html=True)

            stage_counts = view["journey_stage"].value_counts().to_dict()
            stage_rows = [(s, int(stage_counts.get(s, 0))) for s in STAGE_NAMES]
            st.markdown(render.render_journey_chart(stage_rows),
                        unsafe_allow_html=True)

        # --- feedback, full width -----------------------------------------
        shown = view
        if focus:
            shown = shown[shown["primary_taxonomy_subcategory"] == focus]

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
                    min_severity=filters["severity"], focus=focus,
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                render.render_feedback_cards(
                    shown.sort_values(["severity", "confidence"],
                                      ascending=[False, False])
                         .head(40).to_dict("records")
                ),
                unsafe_allow_html=True,
            )

        st.markdown(render.render_comparison_panel(), unsafe_allow_html=True)


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

    st.markdown(f'<div class="afi-card afi-section"><h2 class="afi-guide-h2">'
                f"The {len(CATEGORY_NAMES)} categories</h2></div>",
                unsafe_allow_html=True)
    for n, (name, block) in enumerate(TAXONOMY.items(), 1):
        count = cat_counts.get(name, 0)
        with st.expander(f"**{n}. {name}** — {count} record"
                         f"{'s' if count != 1 else ''} · "
                         f"{len(block['subcategories'])} subcategories"):
            st.markdown(f"**{block['plain']}**")
            st.caption(f"Usual journey stage: `{block['default_stage']}`")
            for sub_name, sub in block["subcategories"].items():
                sub_count = sub_counts.get(sub_name, 0)
                st.markdown(f"##### {sub_name} · {sub_count} record"
                            f"{'s' if sub_count != 1 else ''}")
                st.markdown(sub["plain"])
                st.markdown("**Use it for:** " + "; ".join(sub["use_for"]) + ".")
                st.warning(f"**Do NOT use when:** {sub['avoid']}",
                           icon=":material/block:")
                for example in sub["examples"]:
                    st.markdown(f"> {example}")
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

    st.markdown('<div class="afi-card afi-section" style="margin-top:16px">'
                '<h2 class="afi-guide-h2">Worked examples</h2></div>',
                unsafe_allow_html=True)
    for ex in WORKED_EXAMPLES:
        st.markdown(
            f'<div class="afi-card afi-section" style="margin-top:8px;padding:14px">'
            f'<div class="afi-quote">{ex["feedback"]}</div>'
            f'<div class="afi-labels">'
            f'<span class="afi-label">Category: {ex["category"]}</span>'
            f'<span class="afi-label">Subcategory: {ex["subcategory"]}</span>'
            f'<span class="afi-label">Problem: {ex["problem_type"]}</span>'
            f'<span class="afi-label">Stage: {ex["stage"]}</span></div>'
            f'<p style="color:#64748b;font-size:12px;margin:9px 0 0">{ex["why"]}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="afi-card afi-section" style="margin-top:16px">'
                '<h2 class="afi-guide-h2">Commonly confused pairs</h2></div>',
                unsafe_allow_html=True)
    for pair in CONFUSION_PAIRS:
        st.markdown(
            f'<div class="afi-card afi-section" style="margin-top:8px;padding:14px">'
            f'<div class="afi-comparison">'
            f'<div class="old"><strong>{pair["left"]}</strong>'
            f'<p style="margin:6px 0 0;color:#475569">{pair["left_says"]}</p></div>'
            f'<div class="new"><strong>{pair["right"]}</strong>'
            f'<p style="margin:6px 0 0;color:#475569">{pair["right_says"]}</p></div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )

    persona_counts = rel["persona"].value_counts().to_dict()
    severity_rows = "".join(
        f"<li><b>{k}</b> — {SEVERITY_SCALE[k]}</li>"
        for k in sorted(SEVERITY_SCALE, reverse=True)
    )
    persona_rows = "".join(
        f"<li><b>{name}</b> — {meaning} "
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

    glossary_rows = "".join(f"<li><b>{t}</b> — {d}</li>" for t, d in GLOSSARY.items())
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
