"""Port Action Feedback Intelligence -- two-tab Streamlit app.

An independent take-home project. Not an official Port product.

Tab 1 "Dashboard" -- ranked product actions, each opening onto the feedback
       records that argue for it.
Tab 2 "Taxonomy & Journey Guide" -- plain-language reference for readers with
       no software or DevOps background.

Reads only from data/processed/. No API key, no network calls, no LLM at
runtime -- the classification results are committed, so this opens and renders
identically on any machine.

All taxonomy definitions come from src/models/taxonomy.py, and every count
comes from src/analysis/aggregate.py. Nothing here defines a category or
computes a statistic of its own.

    streamlit run app.py
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.aggregate import (
    HIGH_SEVERITY,
    OPEN_STATUSES,
    evidence_for,
    product_actions,
)
from src.models.taxonomy import (
    CATEGORY_NAMES,
    CONFUSION_PAIRS,
    GLOSSARY,
    LIFECYCLE_STATUSES,
    PROBLEM_TYPE_NAMES,
    SEVERITY_SCALE,
    STAGE_GUIDE,
    STAGE_NAMES,
    SUBCATEGORY_NAMES_BY_CATEGORY,
    TAXONOMY,
    WORKED_EXAMPLES,
)

ROOT = Path(__file__).parent
PROC = ROOT / "data" / "processed"

ACCENT = "#5B4EE8"

st.set_page_config(
    page_title="Port Action Feedback Intelligence",
    page_icon="🛠️",
    layout="wide",
)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
@st.cache_data
def load() -> tuple[pd.DataFrame, dict, dict]:
    analyzed = json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))
    aggregates = json.loads((PROC / "aggregates.json").read_text(encoding="utf-8"))
    quality = json.loads((PROC / "quality_report.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(analyzed["records"])
    return df, aggregates, {"analyzed_meta": analyzed["meta"], "quality": quality}


try:
    df, agg, meta = load()
except FileNotFoundError:
    st.error(
        "Processed data not found. Run the pipeline first:\n\n"
        "```\npython -m src.collectors.run\n"
        "python -m src.analysis.clean\n"
        "python -m src.analysis.classify\n"
        "python -m src.analysis.aggregate\n```"
    )
    st.stop()

rel = df[df["is_relevant"]].copy()
rel["is_open"] = rel["lifecycle_status"].isin(OPEN_STATUSES)
rel["is_high_severity"] = rel["severity"] >= HIGH_SEVERITY

kpi = agg["kpis"]
amet = meta["analyzed_meta"]


def _wrap(label: str, width: int = 22) -> str:
    """Wrap a long category or stage name onto several lines for a chart axis."""
    return "<br>".join(textwrap.wrap(label, width=width))


# --------------------------------------------------------------------------
# Filters -- one set, applied to everything
# --------------------------------------------------------------------------
def sidebar_filters() -> tuple[pd.DataFrame, bool]:
    """Build the filter controls and return the filtered relevant records.

    There is deliberately no Scope filter. Out-of-scope feedback is excluded
    at classification time and is not a view the dashboard offers, because a
    "product actions" ranking that could be toggled to include feedback the
    system judged irrelevant would be an invitation to misread it.
    """
    with st.sidebar:
        st.header("Filters")
        st.caption(
            "These apply to everything on the Dashboard tab at once — the "
            "product actions, the charts and the evidence. What you see ranked "
            "is always what you see supporting it."
        )

        present_categories = set(rel["primary_taxonomy_category"].dropna())
        f_category = st.multiselect(
            "Taxonomy category",
            [c for c in CATEGORY_NAMES if c in present_categories],
        )

        # Subcategory choices narrow to the chosen categories, so the control
        # can never offer an option that would return nothing.
        sub_pool = [
            s
            for c in (f_category or [c for c in CATEGORY_NAMES if c in present_categories])
            for s in SUBCATEGORY_NAMES_BY_CATEGORY[c]
            if s in set(rel["primary_taxonomy_subcategory"].dropna())
        ]
        f_subcategory = st.multiselect("Subcategory", sub_pool)

        present_stages = set(rel["journey_stage"].dropna())
        f_stage = st.multiselect(
            "Journey stage",  # chronological order, not alphabetical
            [s for s in STAGE_NAMES if s in present_stages],
        )

        present_problems = set(rel["problem_type"].dropna())
        f_problem = st.multiselect(
            "Problem type", [p for p in PROBLEM_TYPE_NAMES if p in present_problems]
        )

        present_status = set(rel["lifecycle_status"].dropna())
        f_status = st.multiselect(
            "Lifecycle status", [s for s in LIFECYCLE_STATUSES if s in present_status]
        )

        f_sev = st.slider("Minimum severity", 1, 5, 1)
        verified_only = st.toggle("Verified quotes only", value=True)

        n_unverified = int((~rel["evidence_verified"]).sum())
        st.caption(
            f"Every quote is checked in Python against the original text, word "
            f"for word. **{n_unverified} of {len(rel)}** could not be matched — "
            f"the model paraphrased instead of copying. Leave this on to hide "
            f"them. Their category, stage and severity still count everywhere "
            f"else; only the quote is withheld."
        )

        st.divider()
        st.caption(
            f"**Data**\n\n"
            f"{amet.get('records_analyzed', len(df))} records analysed · "
            f"{kpi['in_scope_records']} in scope · "
            f"{kpi['records_needing_review']} flagged for review · "
            f"{kpi['unverified_evidence']} unverified quote(s)\n\n"
            f"{len(CATEGORY_NAMES)} categories · "
            f"{sum(len(v) for v in SUBCATEGORY_NAMES_BY_CATEGORY.values())} "
            f"subcategories · {len(STAGE_NAMES)} journey stages\n\n"
            f"Model `{amet.get('model_name', '?')}` · "
            f"prompt `{amet.get('prompt_version', '?')}` · "
            f"taxonomy `{amet.get('taxonomy_version', '?')}`\n\n"
            f"Run `{amet.get('analysis_run_id', '?')}`"
        )

    view = rel
    if f_category:
        view = view[view["primary_taxonomy_category"].isin(f_category)]
    if f_subcategory:
        view = view[view["primary_taxonomy_subcategory"].isin(f_subcategory)]
    if f_stage:
        view = view[view["journey_stage"].isin(f_stage)]
    if f_problem:
        view = view[view["problem_type"].isin(f_problem)]
    if f_status:
        view = view[view["lifecycle_status"].isin(f_status)]
    view = view[view["severity"] >= f_sev]
    return view.copy(), verified_only


# ==========================================================================
# TAB 1 -- DASHBOARD
# ==========================================================================
def render_dashboard() -> None:
    view, verified_only = sidebar_filters()

    st.title("What to build next for Port Actions, and who is asking for it")
    st.caption(
        f"{kpi['in_scope_records']} in-scope feedback records from Port's public "
        f"portal · categorised by AI under a closed taxonomy, counted in Python · "
        f"every recommendation opens onto the records that argue for it"
    )

    if view.empty:
        st.warning("No records match these filters.", icon=":material/filter_alt_off:")
        return

    # Recomputed from the filtered records using the same function that built
    # the committed aggregates -- so a filtered view shows real counts for that
    # selection rather than whole-dataset totals with a filtered table below.
    actions = product_actions(view)
    live = view[view["is_open"]]

    # -------------------------------------------------------------- 1. KPIs
    with st.container(horizontal=True):
        st.metric("Feedback records analysed", f"{len(df):,}",
                  help="Every record collected, in scope or not.", border=True)
        st.metric("In scope for Action Configuration", f"{len(view):,}",
                  delta=f"{kpi['out_of_scope_records']} excluded as out of scope",
                  delta_color="off", border=True)
        st.metric("Recommended product actions", f"{len(actions):,}",
                  help="Distinct product changes, grouped from open feedback.",
                  border=True)
        st.metric("High-severity open records", f"{int(live['is_high_severity'].sum()):,}",
                  help=f"Open records at severity {HIGH_SEVERITY} or above.",
                  border=True)

    st.divider()

    # -------------------------------------------- 2. Ranked product actions
    st.subheader("Recommended product actions")
    st.caption(
        "Ranked from open feedback only — completed and closed requests are "
        "excluded so shipped work cannot argue for itself again. Ranking is "
        "lexicographic over the keys below; there is no weighted score, because "
        "a number built from invented weights cannot be defended when someone "
        "asks why 0.45."
    )

    with st.expander("How this ranking is decided"):
        st.markdown(agg["ranking"]["explanation"])
        for i, entry in enumerate(agg["ranking"]["keys"], 1):
            st.markdown(f"{i}. **{entry['key']}** — {entry['explanation']}")
        st.caption(
            f"Open statuses: {', '.join(agg['ranking']['open_statuses'])}. "
            "Severity, category and problem type are the model's reading of the "
            "text; the counting and ordering are plain Python."
        )

    for row in actions.head(10).to_dict("records"):
        with st.container(border=True):
            head, stat = st.columns([5, 2])
            with head:
                st.markdown(f"**{row['rank']}. {row['product_action']}**")
                st.caption(
                    f"`{row['category']}` › `{row['subcategory']}` · "
                    f"mostly *{row['top_problem_type']}* · "
                    f"first felt at *{row['top_journey_stage']}*"
                )
            with stat:
                st.markdown(
                    f"**{row['open_records']}** open record"
                    f"{'s' if row['open_records'] != 1 else ''} · "
                    f"avg severity **{row['avg_severity']}** (max {row['max_severity']})"
                )
                if row["needs_review"]:
                    st.caption(f":material/flag: {row['needs_review']} flagged for review")

            evidence = evidence_for(view, row["category"], row["subcategory"], n=3)
            label = (f"Supporting feedback ({row['open_records']} open record"
                     f"{'s' if row['open_records'] != 1 else ''})")
            with st.expander(label):
                if not evidence:
                    st.caption(
                        "No verified quote is available for this group. The "
                        "records still count; only their quotes are withheld."
                    )
                for ev in evidence:
                    st.markdown(f"> {ev['evidence_excerpt']}")
                    st.caption(
                        f"[{ev['title']}]({ev['source_url']}) · "
                        f"severity {ev['severity']} · "
                        f"{ev['lifecycle_status']} · {ev['source_system']} · "
                        f"confidence {ev['confidence']:.2f}"
                    )

    st.caption(
        ":material/lightbulb: **The counts and the ranking are computed; the "
        "wording of each action is taken verbatim from one real record and "
        "labelled with that record's id in the data.** This is a POC "
        "prioritisation method — real prioritisation would also weigh customer "
        "segment, revenue impact, churn risk, strategic alignment and "
        "engineering effort."
    )

    st.divider()

    # ------------------------------------------- 3. Category + drill-down
    st.subheader("Where the problems concentrate")
    st.caption(
        f"{len(CATEGORY_NAMES)} product areas. Bars count in-scope records. "
        "Pick a category to see which specific part of it the feedback is about."
    )

    cat_counts = (
        view.groupby("primary_taxonomy_category")
        .agg(records=("feedback_id", "count"),
             open_records=("is_open", "sum"),
             avg_severity=("severity", "mean"))
        .reset_index()
        .sort_values("records", ascending=True)
    )

    chart_col, drill_col = st.columns([3, 2])

    with chart_col:
        fig = px.bar(
            cat_counts,
            x="records",
            y="primary_taxonomy_category",
            orientation="h",
            text=[f"{r} records · {o} open"
                  for r, o in zip(cat_counts["records"], cat_counts["open_records"])],
            labels={"records": "In-scope feedback records",
                    "primary_taxonomy_category": ""},
            color_discrete_sequence=[ACCENT],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=460, margin=dict(l=0, r=90, t=10, b=10), showlegend=False,
        )
        st.plotly_chart(fig, width="stretch")

    with drill_col:
        present = [c for c in CATEGORY_NAMES
                   if c in set(view["primary_taxonomy_category"].dropna())]
        chosen = st.selectbox("Drill into a category", present, key="drill_category")
        subs = (
            view[view["primary_taxonomy_category"] == chosen]
            .groupby("primary_taxonomy_subcategory")
            .agg(records=("feedback_id", "count"),
                 open_records=("is_open", "sum"),
                 avg_severity=("severity", "mean"))
            .reset_index()
            .sort_values("records", ascending=False)
        )
        subs["avg_severity"] = subs["avg_severity"].round(1)
        st.caption(
            f"**{TAXONOMY[chosen]['plain']}** "
            f"{len(subs)} of {len(SUBCATEGORY_NAMES_BY_CATEGORY[chosen])} "
            f"subcategories appear in this feedback."
        )
        st.dataframe(
            subs, hide_index=True, width="stretch",
            column_config={
                "primary_taxonomy_subcategory": st.column_config.TextColumn(
                    "Subcategory", width="large"),
                "records": st.column_config.NumberColumn("Records", width="small"),
                "open_records": st.column_config.NumberColumn("Open", width="small"),
                "avg_severity": st.column_config.NumberColumn("Avg sev", width="small"),
            },
        )

    st.divider()

    # ------------------------------------------------------ 4. Journey stage
    st.subheader("Where in the journey users get stuck")
    st.caption(
        "The eight stages in the order a user meets them, left to right. This "
        "answers *where* the friction happens; the categories above answer "
        "*what* needs building. A record sits in exactly one of each."
    )

    stage_counts = (
        view.groupby("journey_stage")
        .agg(records=("feedback_id", "count"),
             open_records=("is_open", "sum"),
             avg_severity=("severity", "mean"))
        .reset_index()
    )
    missing = [s for s in STAGE_NAMES if s not in set(stage_counts["journey_stage"])]
    if missing:
        stage_counts = pd.concat([stage_counts, pd.DataFrame(
            {"journey_stage": missing, "records": 0,
             "open_records": 0, "avg_severity": 0.0})], ignore_index=True)
    stage_counts["order"] = stage_counts["journey_stage"].map(
        {n: i for i, n in enumerate(STAGE_NAMES)})
    stage_counts = stage_counts.sort_values("order")
    stage_counts["label"] = stage_counts["journey_stage"].map(_wrap)

    fig = px.bar(
        stage_counts,
        x="label",
        y="records",
        text="records",
        labels={"label": "", "records": "In-scope feedback records"},
        color_discrete_sequence=[ACCENT],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=10),
                      showlegend=False, xaxis=dict(tickfont=dict(size=11)))
    st.plotly_chart(fig, width="stretch")

    busiest = stage_counts.sort_values("records", ascending=False).iloc[0]
    empty_stages = stage_counts[stage_counts["records"] == 0]["journey_stage"].tolist()
    st.markdown(
        f"**{busiest['journey_stage']}** carries the most feedback "
        f"({int(busiest['records'])} records, {int(busiest['open_records'])} still open)."
        + (f" No feedback at all mentions "
           f"{', '.join(f'*{s}*' for s in empty_stages)} — an empty stage is a "
           f"finding, not a gap in the chart." if empty_stages else "")
    )

    st.divider()

    # --------------------------------------------------- 5. Problem types
    st.subheader("What kind of problems these are")
    st.caption(
        "Problem type is independent of product area. A permission failure can "
        "be a *Poor error message*; folding that into the category name would "
        "make both unusable for counting."
    )
    problems = (
        view.groupby("problem_type")
        .agg(records=("feedback_id", "count"),
             open_records=("is_open", "sum"),
             avg_severity=("severity", "mean"))
        .reset_index()
        .sort_values("records", ascending=False)
    )
    problems["avg_severity"] = problems["avg_severity"].round(1)
    st.dataframe(
        problems, hide_index=True, width="stretch",
        column_config={
            "problem_type": st.column_config.TextColumn("Problem type", width="large"),
            "records": st.column_config.NumberColumn("Records", width="small"),
            "open_records": st.column_config.NumberColumn("Open", width="small"),
            "avg_severity": st.column_config.NumberColumn("Avg severity", width="small"),
        },
    )

    st.divider()

    # ------------------------------------------------------- 6. Evidence
    st.subheader("Evidence explorer")
    st.caption(
        "Every figure above traces back to these records. Open any of them on "
        "Port's portal to verify the quote yourself."
    )

    ev_view = view[view["evidence_verified"]] if verified_only else view
    ev_view = ev_view.sort_values(
        ["severity", "confidence"], ascending=[False, False])

    st.dataframe(
        ev_view[[
            "title", "short_summary", "suggested_product_action",
            "primary_taxonomy_category", "primary_taxonomy_subcategory",
            "problem_type", "journey_stage", "lifecycle_status", "severity",
            "confidence", "needs_human_review", "evidence_excerpt", "source_url",
        ]],
        hide_index=True, width="stretch", height=420,
        column_config={
            "title": st.column_config.TextColumn("Title", width="medium"),
            "short_summary": st.column_config.TextColumn("AI summary", width="large"),
            "suggested_product_action": st.column_config.TextColumn(
                "Suggested change", width="large"),
            "primary_taxonomy_category": st.column_config.TextColumn("Category"),
            "primary_taxonomy_subcategory": st.column_config.TextColumn("Subcategory"),
            "problem_type": st.column_config.TextColumn("Problem type"),
            "journey_stage": st.column_config.TextColumn("Journey stage"),
            "lifecycle_status": st.column_config.TextColumn("Status", width="small"),
            "severity": st.column_config.NumberColumn("Sev", width="small"),
            "confidence": st.column_config.NumberColumn("Conf", format="%.2f", width="small"),
            "needs_human_review": st.column_config.CheckboxColumn("Review?", width="small"),
            "evidence_excerpt": st.column_config.TextColumn("Verified quote", width="large"),
            "source_url": st.column_config.LinkColumn("Source", display_text="Open"),
        },
    )
    st.caption(f"{len(ev_view)} of {len(view)} filtered records shown.")

    st.divider()
    render_quality_panel()


# --------------------------------------------------------------------------
# Model quality
# --------------------------------------------------------------------------
def render_quality_panel() -> None:
    st.subheader("How good is the AI classification?")

    @st.cache_data
    def evaluation_status(_mtime: float) -> dict | None:
        """Cache keyed on the file's modification time.

        The review CSV is meant to be edited by hand, so a plain cache would
        keep serving "Not yet evaluated" after someone fills it in. Passing
        mtime makes an edit invalidate the cache automatically.
        """
        sample_path = ROOT / "data" / "evaluation" / "review_sample.csv"
        if not sample_path.exists():
            return None
        from src.analysis.evaluate import score
        return score(pd.read_csv(sample_path))

    sample = ROOT / "data" / "evaluation" / "review_sample.csv"
    ev = evaluation_status(sample.stat().st_mtime if sample.exists() else 0.0)

    if ev is None:
        st.info("No review sample has been created yet.", icon=":material/help:")
        return

    scored = {k: v for k, v in ev["fields"].items() if v["status"] == "evaluated"}
    if not scored:
        st.warning(
            f"**Not yet evaluated.** A reproducible {ev['sample_size']}-record "
            "sample is ready for manual review, but no human labels have been "
            "entered yet — so there is no agreement figure to report. This panel "
            "deliberately shows nothing rather than a number that would not mean "
            "anything.",
            icon=":material/pending:",
        )
    else:
        with st.container(horizontal=True):
            for label, entry in scored.items():
                st.metric(
                    label.replace("_", " ").title(),
                    f"{entry['agreement_rate']:.0%}",
                    help=f"{entry['agreements']} of {entry['labelled']} reviewed "
                         f"records agreed",
                    border=True,
                )
        if ev["disagreements"]:
            with st.expander(f"Disagreements ({len(ev['disagreements'])})"):
                st.dataframe(pd.DataFrame(ev["disagreements"]), hide_index=True)

    st.caption(
        f"Sample of {ev['sample_size']} records, drawn with a fixed seed and "
        "stratified across relevance and category. At this size it is a sanity "
        "check, not a statistically robust evaluation — enough to catch a "
        "category nobody can apply consistently, not enough to quote an accuracy "
        "figure with confidence."
    )


# ==========================================================================
# TAB 2 -- GUIDE
# ==========================================================================
def render_guide() -> None:
    st.title("Taxonomy & Journey Guide")
    st.caption(
        "Written for a reader with no software or DevOps background. If you can "
        "tell what a user was trying to do and what stopped them, you can use "
        "this guide."
    )

    st.info(
        "**An Action is a form.** Someone fills it in to get something done — "
        "deploy a service, spin up a database, request access. Everything in "
        "this guide is about the moment that form fails its user.",
        icon=":material/info:",
    )

    st.subheader("The four questions every record answers")
    with st.container(horizontal=True):
        with st.container(border=True):
            st.markdown(
                f"#### 🏷️ Category — *what area*\n"
                f"Which broad part of the product needs to change.\n\n"
                f"**{len(CATEGORY_NAMES)} categories.**"
            )
        with st.container(border=True):
            st.markdown(
                f"#### 🔎 Subcategory — *what exactly*\n"
                f"The specific part of that area.\n\n"
                f"**{sum(len(v) for v in SUBCATEGORY_NAMES_BY_CATEGORY.values())} "
                f"subcategories.**"
            )
        with st.container(border=True):
            st.markdown(
                f"#### 🧩 Problem type — *what kind*\n"
                f"A bug, a missing feature, a confusing experience.\n\n"
                f"**{len(PROBLEM_TYPE_NAMES)} types.**"
            )
        with st.container(border=True):
            st.markdown(
                f"#### 📍 Journey stage — *where*\n"
                f"How far the user had got before they hit it.\n\n"
                f"**{len(STAGE_NAMES)} stages.**"
            )

    st.caption(
        "They are independent on purpose. *Permissions* is the area; *Poor error "
        "message* is the kind of problem; *Permissions & approvals* is the moment "
        "it happened. Merging them would make all three impossible to count."
    )

    st.divider()

    # ------------------------------------------------- how to decide
    st.subheader("How to place a piece of feedback, in four steps")
    for step, text in [
        ("1", "**Ask what the user was trying to do**, in one plain sentence. "
              "Not what they asked for — what they wanted."),
        ("2", "**Ask what stopped them.** That points at the category."),
        ("3", "**Read the subcategory's _Do NOT use when_ line** before you "
              "commit. Almost every wrong answer is the neighbour it names."),
        ("4", "**Ask how far they had got.** That is the journey stage — the "
              "moment they *first* became blocked, not where it was noticed."),
    ]:
        st.markdown(f"**{step}.** {text}")

    st.divider()

    # ------------------------------------------------- categories
    st.header(f"The {len(CATEGORY_NAMES)} categories")
    cat_counts = rel["primary_taxonomy_category"].value_counts().to_dict()
    sub_counts = rel["primary_taxonomy_subcategory"].value_counts().to_dict()

    for n, (name, block) in enumerate(TAXONOMY.items(), 1):
        count = cat_counts.get(name, 0)
        with st.expander(
            f"**{n}. {name}** — {count} record{'s' if count != 1 else ''} "
            f"· {len(block['subcategories'])} subcategories"
        ):
            st.markdown(f"**{block['plain']}**")
            st.caption(f":material/place: Usual journey stage: `{block['default_stage']}`")

            for sub_name, sub in block["subcategories"].items():
                sub_count = sub_counts.get(sub_name, 0)
                st.markdown(f"##### {sub_name}  ·  {sub_count} record"
                            f"{'s' if sub_count != 1 else ''}")
                st.markdown(sub["plain"])
                st.markdown("**Use it for:** " + "; ".join(sub["use_for"]) + ".")
                st.warning(f"**Do NOT use when:** {sub['avoid']}", icon=":material/block:")
                for example in sub["examples"]:
                    st.markdown(f"> {example}")
                st.markdown("")

            if block["confusable"]:
                st.info(
                    "Most often confused with: "
                    + ", ".join(f"**{c}**" for c in block["confusable"]),
                    icon=":material/compare_arrows:",
                )

    st.divider()

    # ------------------------------------------------- stages
    st.header(f"The {len(STAGE_NAMES)} journey stages")
    st.caption(
        "In the order a user meets them. Always pick the stage where the user "
        "*first* becomes blocked."
    )
    stage_counts = rel["journey_stage"].value_counts().to_dict()
    for i, name in enumerate(STAGE_NAMES, 1):
        guide = STAGE_GUIDE[name]
        count = stage_counts.get(name, 0)
        with st.container(border=True):
            st.markdown(f"**{i}. {name}** · {count} record{'s' if count != 1 else ''}")
            st.markdown(f"*The user is trying to:* {guide['user_goal']}")
            st.markdown(f"> {guide['example']}")

    st.divider()

    # ------------------------------------------------- worked examples
    st.header("Worked examples")
    st.caption("Real classification decisions, with the reasoning shown.")
    for ex in WORKED_EXAMPLES:
        with st.container(border=True):
            st.markdown(f"> {ex['feedback']}")
            a, b, c, d = st.columns(4)
            a.markdown(f"🏷️ **Category**\n\n`{ex['category']}`")
            b.markdown(f"🔎 **Subcategory**\n\n`{ex['subcategory']}`")
            c.markdown(f"🧩 **Problem type**\n\n`{ex['problem_type']}`")
            d.markdown(f"📍 **Stage**\n\n`{ex['stage']}`")
            st.caption(f":material/lightbulb: {ex['why']}")

    st.divider()

    # ------------------------------------------------- confusion pairs
    st.header("Commonly confused pairs")
    st.caption(
        "These are the decisions that go wrong most often. The difference is "
        "always what the user is complaining about, never which words they used."
    )
    for pair in CONFUSION_PAIRS:
        with st.container(border=True):
            left, right = st.columns(2)
            left.markdown(f"**{pair['left']}**\n\n{pair['left_says']}")
            right.markdown(f"**{pair['right']}**\n\n{pair['right_says']}")

    st.divider()

    # ------------------------------------------------- severity + glossary
    st.header("Severity")
    st.caption("How much the problem hurts, as described in the text — not how "
               "popular the request is and not how hard it would be to build.")
    for level in sorted(SEVERITY_SCALE, reverse=True):
        st.markdown(f"**{level}** — {SEVERITY_SCALE[level]}")

    st.divider()

    st.header("Glossary")
    st.caption("Every term used in this app, in plain language.")
    terms = list(GLOSSARY.items())
    half = (len(terms) + 1) // 2
    left, right = st.columns(2)
    for column, chunk in ((left, terms[:half]), (right, terms[half:])):
        with column:
            for term, definition in chunk:
                st.markdown(f"**{term}** — {definition}")


# ==========================================================================
# Tabs
# ==========================================================================
tab_dashboard, tab_guide = st.tabs(["📊 Dashboard", "📖 Taxonomy & Journey Guide"])

with tab_dashboard:
    render_dashboard()

with tab_guide:
    render_guide()
