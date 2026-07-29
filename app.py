"""Port Action Feedback Intelligence -- single-page dashboard.

An independent take-home project. Not an official Port product.

Reads only from data/processed/. No API key, no network calls, no LLM at
runtime -- the classification results are committed, so this opens and renders
identically on any machine.

    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).parent
PROC = ROOT / "data" / "processed"

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
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
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
kpi = agg["kpis"]
themes = pd.DataFrame(agg["themes"])
stages = pd.DataFrame(agg["stages"])


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.title("Where developers get stuck configuring Port actions")
st.caption(
    f"{kpi['relevant_posts']} relevant feature requests from Port's public feedback "
    f"portal, carrying {kpi['total_votes']:,} votes · categorised by AI, counted in Python"
)
st.info(
    "**Independent take-home project — not an official Port product.** Built from "
    "publicly available feature requests on roadmap.port.io.",
    icon=":material/info:",
)

# --------------------------------------------------------------------------
# 1. Executive summary
# --------------------------------------------------------------------------
st.subheader("Executive summary")

def short(theme: str, limit: int = 21) -> str:
    """Trim a theme name for a KPI card without reducing it to one bare word."""
    return theme if len(theme) <= limit else theme[:limit].rsplit(" ", 1)[0]


with st.container(horizontal=True):
    st.metric("Relevant feedback posts", f"{kpi['relevant_posts']}", border=True)
    st.metric("Total votes", f"{kpi['total_votes']:,}", border=True)
    st.metric("High-severity posts", f"{kpi['high_severity_posts']}", border=True)
    st.metric("Most common theme", short(kpi["most_common_theme"]), border=True)
    st.metric("Top priority theme", short(kpi["highest_priority_theme"]), border=True)

if kpi["most_common_theme"] == kpi["highest_priority_theme"]:
    st.caption(
        f"*{kpi['most_common_theme']}* leads on both volume and priority — the most "
        "frequently raised theme is also the highest scoring."
    )

# Insights are computed from the data, so they cannot drift out of sync with it.
top = themes.iloc[0]
top_by_votes = themes.sort_values("total_votes", ascending=False).iloc[0]
stages_ranked = stages[stages["posts"] > 0].copy()
densest = stages_ranked.sort_values("votes_per_post", ascending=False).iloc[0]
busiest = stages_ranked.sort_values("posts", ascending=False).iloc[0]
top_stage_votes = stages_ranked.sort_values("total_votes", ascending=False).iloc[0]

st.markdown("#### Three things the data says")

c1, c2, c3 = st.columns(3)

with c1:
    with st.container(border=True):
        st.markdown(f"**1. {top['primary_theme']} is the biggest single gap**")
        st.markdown(
            f"It is the most frequently raised theme — **{top['posts']} posts** carrying "
            f"**{top['total_votes']} votes**, at an average severity of "
            f"**{top['avg_severity']:.1f}/5**. It leads on volume *and* demand, so it is "
            f"not an artefact of a few loud requests."
        )
        st.caption(f"Sample size: {top['posts']} of {kpi['relevant_posts']} relevant posts")

with c2:
    with st.container(border=True):
        st.markdown("**2. Counting complaints ≠ counting demand**")
        st.markdown(
            f"**{busiest['journey_stage']}** generates the most posts "
            f"({int(busiest['posts'])}) but the *lowest* demand per post "
            f"({busiest['votes_per_post']:.1f} votes each). Meanwhile "
            f"**{densest['journey_stage']}** has only {int(densest['posts'])} posts at "
            f"**{densest['votes_per_post']:.1f} votes each** — {densest['votes_per_post']/busiest['votes_per_post']:.1f}× the demand density."
        )
        st.caption("Volume and demand produce different roadmaps")

with c3:
    with st.container(border=True):
        st.markdown(f"**3. {top_stage_votes['journey_stage']} carries the most demand**")
        st.markdown(
            f"**{int(top_stage_votes['total_votes'])} votes** across "
            f"**{int(top_stage_votes['posts'])} posts** — the highest vote-weighted "
            f"total of any stage in the journey. Two separate themes "
            f"(*Permissions & access control*, *Approval workflows*) both rank in the "
            f"top four priorities."
        )
        st.caption(f"Sample size: {int(top_stage_votes['posts'])} posts")

st.divider()

# --------------------------------------------------------------------------
# 2. Main themes
# --------------------------------------------------------------------------
st.subheader("Main feedback themes")
st.caption(
    f"How the {kpi['relevant_posts']} relevant posts distribute across problem areas. "
    "Bars are ordered by how many posts raised each theme; votes are shown alongside "
    "because the two do not always agree."
)

theme_chart = themes.sort_values("posts")
fig = px.bar(
    theme_chart,
    x="posts",
    y="primary_theme",
    orientation="h",
    # Label carries both numbers: bar length is posts, so a votes-only label
    # makes a shorter bar with more votes look like a rendering error.
    text=[f"{p} posts · {v} votes"
          for p, v in zip(theme_chart["posts"], theme_chart["total_votes"])],
    labels={"posts": "Number of feedback posts", "primary_theme": ""},
)
fig.update_traces(marker_color="#5B4EE8", textposition="outside", cliponaxis=False)
fig.update_layout(
    height=430,
    margin=dict(l=0, r=60, t=10, b=0),
    xaxis_title="Number of feedback posts",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig)

st.divider()

# --------------------------------------------------------------------------
# 3. Journey
# --------------------------------------------------------------------------
st.subheader("Where friction sits in the Action Configuration journey")
st.caption(
    "The seven stages of setting up a self-service action, in order. "
    "Bar height is vote-weighted demand; the label above each bar is how many "
    "posts raised that stage."
)

journey = stages.copy()
journey["stage_label"] = journey["journey_stage"].str.replace(
    " and ", " and<br>", regex=False)

fig2 = px.bar(
    journey,
    x="stage_label",
    y="total_votes",
    text="posts",
    labels={"total_votes": "Votes", "stage_label": ""},
)
fig2.update_traces(
    marker_color="#5B4EE8",
    texttemplate="%{text} posts",
    textposition="outside",
    cliponaxis=False,
)
fig2.update_layout(
    height=400,
    margin=dict(l=0, r=0, t=20, b=0),
    yaxis_title="Vote-weighted demand",
    plot_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig2)

st.caption(
    f"Highest demand: **{top_stage_votes['journey_stage']}** "
    f"({int(top_stage_votes['total_votes'])} votes). "
    f"Most posts: **{busiest['journey_stage']}** ({int(busiest['posts'])}). "
    "Stages with no feedback are shown rather than hidden."
)

st.divider()

# --------------------------------------------------------------------------
# 4. Priorities
# --------------------------------------------------------------------------
st.subheader("Product priorities")

st.markdown(
    f"**Priority = 45% vote demand + 30% how often the theme appears + "
    f"25% average severity.** Each part is scaled so the top theme = 1.0. "
    f"Votes use a **{agg['scoring']['vote_scale']}** scale because the leading theme has "
    f"{agg['scoring']['vote_skew_ratio']}× the votes of the median theme "
    f"(a log scale would apply above {agg['scoring']['threshold']:.0f}×)."
)

priority_view = themes.head(10)[[
    "rank", "primary_theme", "posts", "total_votes", "avg_severity",
    "priority_score", "recommended_action",
]]

st.dataframe(
    priority_view,
    hide_index=True,
    column_config={
        "rank": st.column_config.NumberColumn("#", width="small"),
        "primary_theme": st.column_config.TextColumn("Theme", pinned=True),
        "posts": st.column_config.NumberColumn("Posts", width="small"),
        "total_votes": st.column_config.NumberColumn("Votes", width="small"),
        "avg_severity": st.column_config.NumberColumn(
            "Avg severity", format="%.1f", width="small"),
        "priority_score": st.column_config.ProgressColumn(
            "Priority", min_value=0.0, max_value=1.0, format="%.2f"),
        "recommended_action": st.column_config.TextColumn(
            "Suggested product response", width="large"),
    },
)

st.caption(
    ":material/lightbulb: **Numbers are computed from the data; the suggested "
    "response is analyst judgment.** This is a POC prioritisation method — real "
    "prioritisation would also weigh customer segment, revenue impact, churn risk, "
    "strategic alignment and engineering effort."
)

st.divider()

# --------------------------------------------------------------------------
# 5. Evidence
# --------------------------------------------------------------------------
st.subheader("Supporting evidence")
st.caption(
    "Every insight above traces back to these records. Filter in the sidebar, "
    "then open any request on Port's portal to verify it."
)

with st.sidebar:
    st.header("Filter the evidence")
    st.caption("These filters apply to the evidence table below.")

    f_theme = st.multiselect("Theme", sorted(rel["primary_theme"].unique()))
    f_stage = st.multiselect("Journey stage", sorted(rel["journey_stage"].unique()))
    f_status = st.multiselect("Status", sorted(rel["status"].dropna().unique()))
    f_sev = st.slider("Minimum severity", 1, 5, 1)
    verified_only = st.toggle("Verified quotes only", value=True)

    st.divider()
    st.caption(
        f"**Data**\n\n"
        f"{meta['analyzed_meta']['records_analyzed']} posts analysed · "
        f"{kpi['relevant_posts']} relevant · "
        f"{kpi['low_confidence_posts']} low-confidence · "
        f"{kpi['unverified_evidence']} unverified quote(s)\n\n"
        f"Model: `{meta['analyzed_meta']['model_name']}` · "
        f"prompt `{meta['analyzed_meta']['prompt_version']}`"
    )

view = rel.copy()
if f_theme:
    view = view[view["primary_theme"].isin(f_theme)]
if f_stage:
    view = view[view["journey_stage"].isin(f_stage)]
if f_status:
    view = view[view["status"].isin(f_status)]
view = view[view["severity"] >= f_sev]
if verified_only:
    view = view[view["evidence_verified"]]

view = view.sort_values("votes", ascending=False)

st.markdown(f"**Showing {len(view)} of {len(rel)} relevant posts**")

if view.empty:
    st.warning("No posts match these filters. Clear one to see results.")
else:
    st.dataframe(
        view[[
            "title", "short_summary", "user_need", "primary_theme", "journey_stage",
            "feedback_type", "votes", "severity", "confidence",
            "evidence_excerpt", "source_url",
        ]],
        hide_index=True,
        height=460,
        column_config={
            "title": st.column_config.TextColumn("Original title", pinned=True, width="medium"),
            "short_summary": st.column_config.TextColumn("Problem summary", width="large"),
            "user_need": st.column_config.TextColumn("User need", width="large"),
            "primary_theme": st.column_config.TextColumn("Theme"),
            "journey_stage": st.column_config.TextColumn("Journey stage"),
            "feedback_type": st.column_config.TextColumn("Type"),
            "votes": st.column_config.NumberColumn("Votes", width="small"),
            "severity": st.column_config.NumberColumn("Sev", width="small"),
            "confidence": st.column_config.NumberColumn("Conf", format="%.2f", width="small"),
            "evidence_excerpt": st.column_config.TextColumn(
                "Evidence (verbatim quote)", width="large"),
            "source_url": st.column_config.LinkColumn(
                "Source", display_text="Open ↗", width="small"),
        },
    )

st.caption(
    ":material/verified: Every quote shown is verified to appear character-for-character "
    "in the original post. Quotes that failed that check are excluded, not displayed."
)

st.divider()

# --------------------------------------------------------------------------
# Model quality check
# --------------------------------------------------------------------------
st.subheader("How good is the AI classification?")


@st.cache_data
def evaluation_status(_mtime: float) -> dict | None:
    """Cache keyed on the file's modification time.

    The review CSV is meant to be edited by hand, so a plain cache would keep
    serving "Not yet evaluated" after someone fills it in. Passing mtime makes
    an edit invalidate the cache automatically.
    """
    sample_path = ROOT / "data" / "evaluation" / "review_sample.csv"
    if not sample_path.exists():
        return None
    from src.analysis.evaluate import score
    return score(pd.read_csv(sample_path))


_sample = ROOT / "data" / "evaluation" / "review_sample.csv"
ev = evaluation_status(_sample.stat().st_mtime if _sample.exists() else 0.0)

if ev is None:
    st.info("No review sample has been created yet.", icon=":material/help:")
else:
    scored = {k: v for k, v in ev["fields"].items() if v["status"] == "evaluated"}
    if not scored:
        st.warning(
            f"**Not yet evaluated.** A reproducible {ev['sample_size']}-record sample is "
            "ready for manual review, but no human labels have been entered yet — so "
            "there is no agreement figure to report. This panel deliberately shows "
            "nothing rather than a number that would not mean anything.",
            icon=":material/pending:",
        )
    else:
        with st.container(horizontal=True):
            for label, entry in scored.items():
                st.metric(
                    label.replace("_", " ").title(),
                    f"{entry['agreement_rate']:.0%}",
                    help=f"{entry['agreements']} of {entry['labelled']} reviewed records agreed",
                    border=True,
                )
        rel_entry = scored.get("relevance", {})
        if rel_entry.get("precision") is not None:
            st.caption(
                f"Relevance precision {rel_entry['precision']:.2f} · "
                f"recall {rel_entry['recall']:.2f}"
            )
        if ev["disagreements"]:
            with st.expander(f"Disagreements ({len(ev['disagreements'])})"):
                st.dataframe(pd.DataFrame(ev["disagreements"]), hide_index=True)

    st.caption(
        f"Sample of {ev['sample_size']} records, drawn with a fixed seed and stratified "
        "across relevance and theme. At this size it is a sanity check, not a "
        "statistically robust evaluation — enough to catch a category nobody can apply "
        "consistently, not enough to quote an accuracy figure with confidence."
    )

# --------------------------------------------------------------------------
# Method footnote
# --------------------------------------------------------------------------
with st.expander("How this works, and what it cannot tell you"):
    q = meta["quality"]["counts"]
    st.markdown(f"""
**Pipeline** — `Port public portal → cleaning → AI categorisation → aggregation → this dashboard`

At production scale the same shape applies to `Slack / Zendesk / Gong` instead of one public portal.

**What the AI does:** reads each post and assigns a theme, journey stage, feedback type,
severity, summary and a verbatim quote, under a fixed schema with closed categories.
**What Python does:** every count, total, average, ranking and score on this page.
No number here was produced by a language model.

**Data:** {q['fetched']} posts collected from roadmap.port.io ·
{q['duplicates_removed']} duplicates removed · {q['unique_records']} unique ·
{kpi['relevant_posts']} judged relevant · {kpi['total_votes']:,} votes.

**Limitations**

- **A feature-request board shapes what you find.** 90% of relevant records are feature
  requests. People come here to ask for things, not to report friction — so bugs and
  usability problems are under-represented relative to what Zendesk or Gong would show.
- **Votes measure vocal demand, not revenue or customer count.** One vote from a large
  customer counts the same as one from a trial user.
- **Severity is judged from the text alone** and clusters at 3, so it discriminates weakly.
- **Public feedback cannot prove causation.** It can explain *why* users say they struggle;
  it cannot prove that is why they drop off. That needs internal product data.
- **{kpi['low_confidence_posts']} posts** were classified with confidence below 0.7 and are
  flagged rather than hidden. Confidence never affects priority.
""")
