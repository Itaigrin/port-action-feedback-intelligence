"""Deterministic aggregation and product-action ranking.

Every number the dashboard shows is computed here, in plain Python, from the
classified records. No LLM is involved at this stage -- the model read and
categorised the feedback; pandas does the arithmetic. That split is the point:
counts and rankings must be reproducible and auditable, and an LLM is neither.

TWO THINGS DELIBERATELY ABSENT
------------------------------
**Votes.** The previous version ranked on portal vote counts. A vote total is
meaningful inside one portal and meaningless across Slack, Zendesk and Gong --
there is nothing to vote with in a support ticket or a sales call. Ranking on a
signal that only one of four sources can produce would systematically bury
every problem that arrives through the other three. Votes are still collected
and preserved as evidence; nothing is ranked by them.

**A weighted score.** There is no `0.45 x demand + 0.30 x frequency` formula
here. Multiplying unlike signals by invented weights produces a number that
looks precise and cannot be defended when a stakeholder asks why 0.45. Ranking
is lexicographic instead: an explicit list of tie-breakers applied in a stated
order, where every position in the ranking can be explained by naming the key
that decided it.

    python -m src.analysis.aggregate
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..models.taxonomy import (
    CATEGORY_NAMES,
    OPEN_STATUSES,
    PERSONA_NAMES,
    PROBLEM_TYPE_NAMES,
    STAGE_NAMES,
)

ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT / "data" / "processed"

HIGH_SEVERITY = 4
LOW_CONFIDENCE = 0.7

# A group is "critical" when enough people report it AND it hurts badly on
# average. Both must hold: the record floor stops one severe voice topping the
# list, and the severity floor stops sheer volume doing the same. The severity
# test uses the raw mean, not the rounded band -- rounding would let an average
# of 3.5 satisfy a rule written as "4 and above".
CRITICAL_MIN_RECORDS = 3
CRITICAL_MIN_SEVERITY = 4.0

# The ranking keys, applied in this order, all descending.
#
# Each entry is (field, plain_label, explanation). The plain label exists so
# the dashboard can explain the ranking to a reader with no background here --
# a sidebar listing `severity_band` and `avg_confidence` is accurate and
# useless. Keeping the label beside the field means the readable version is
# generated from the same source that does the sorting, and cannot drift.
RANK_KEYS: tuple[tuple[str, str, str], ...] = (
    ("is_critical",
     "It's critical — at least 3 open records and an average severity "
     "of 4 or above",
     f"Critical: at least {CRITICAL_MIN_RECORDS} open records AND an average "
     f"severity of {CRITICAL_MIN_SEVERITY:.0f} or above. Widely reported and "
     "severe, so it outranks everything below regardless of the other keys."),
    ("open_records",
     "Open records — how many people asked for it",
     "Number of distinct open feedback records asking for this change -- "
     "independent voices converging on one problem."),
    ("severity_band",
     "Severity band — how much it hurts, typically",
     "Severity band (average severity, rounded) -- how much the problem hurts "
     "when it happens."),
    ("max_severity",
     "Max severity — the worst single case",
     "The single worst record in the group."),
    ("source_diversity",
     "Source diversity — how many different sources it came from",
     "How many different source systems raised it."),
    ("avg_confidence",
     "Avg confidence — how sure the AI was",
     "Average classifier confidence, as a data-quality tie-breaker only."),
    ("latest_created",
     "Latest created — how recently it was raised",
     "Recency of the newest supporting record."),
)


def load_records() -> pd.DataFrame:
    data = json.loads((PROC_DIR / "analyzed.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(data["records"])
    df.attrs["meta"] = data.get("meta", {})
    return df


def relevant_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["is_relevant"]].copy()


def open_only(rel: pd.DataFrame) -> pd.DataFrame:
    """Live demand only.

    Completed and Closed records are excluded from ranking because shipped work
    must never inflate the case for building something again. They stay in the
    dataset and remain visible in the evidence explorer -- "we already did this"
    is itself a finding.
    """
    return rel[rel["lifecycle_status"].isin(OPEN_STATUSES)].copy()


# --- product actions -------------------------------------------------------
def _representative(group: pd.DataFrame) -> pd.Series:
    """Pick the record whose wording labels the group.

    Deterministic and traceable: highest severity, then highest confidence,
    then lowest feedback_id. Because it is one real record rather than a
    synthesised sentence, the label on the dashboard can always be traced to
    the specific piece of feedback it was taken from.
    """
    ordered = group.sort_values(
        ["severity", "confidence", "feedback_id"],
        ascending=[False, False, True],
    )
    return ordered.iloc[0]


def product_actions(rel: pd.DataFrame) -> pd.DataFrame:
    """Group open feedback into ranked, recommended product actions.

    Grouping is by taxonomy subcategory, not by the text of
    suggested_product_action. Two records asking for the same thing rarely
    phrase it identically, so text grouping would fragment real demand into
    singletons; the subcategory is the closed, stable key the model was
    constrained to and is therefore the only grouping that counts reliably.
    """
    live = open_only(rel)
    if live.empty:
        return pd.DataFrame()

    rows: list[dict] = []
    for (category, subcategory), group in live.groupby(
        ["primary_taxonomy_category", "primary_taxonomy_subcategory"], sort=True
    ):
        rep = _representative(group)
        created = pd.to_datetime(group["created_at"], errors="coerce", utc=True)
        rows.append({
            "category": category,
            "subcategory": subcategory,
            "product_action": rep["suggested_product_action"],
            "product_action_source_id": rep["feedback_id"],
            "open_records": int(len(group)),
            "avg_severity": round(float(group["severity"].mean()), 2),
            # Stored as int so it sorts and serialises cleanly.
            "is_critical": int(
                len(group) >= CRITICAL_MIN_RECORDS
                and float(group["severity"].mean()) >= CRITICAL_MIN_SEVERITY
            ),
            "max_severity": int(group["severity"].max()),
            "severity_band": int(round(float(group["severity"].mean()))),
            "avg_confidence": round(float(group["confidence"].mean()), 3),
            "source_diversity": int(group["source_system"].nunique()),
            "source_systems": sorted(group["source_system"].unique().tolist()),
            "latest_created": (created.max().isoformat()
                               if created.notna().any() else ""),
            "top_problem_type": (group["problem_type"].mode().iloc[0]
                                 if not group["problem_type"].mode().empty else ""),
            "top_journey_stage": (group["journey_stage"].mode().iloc[0]
                                  if not group["journey_stage"].mode().empty else ""),
            "needs_review": int(group["needs_human_review"].sum()),
            "record_ids": group["feedback_id"].tolist(),
        })

    actions = pd.DataFrame(rows)
    # Lexicographic ranking. The final subcategory key makes the order total,
    # so the same input always produces the same ranking -- no ties broken by
    # dict or row order.
    actions = actions.sort_values(
        [key for key, *_ in RANK_KEYS] + ["subcategory"],
        ascending=[False] * len(RANK_KEYS) + [True],
    ).reset_index(drop=True)
    actions["rank"] = actions.index + 1
    return actions


# --- distribution tables ---------------------------------------------------
def _pad(g: pd.DataFrame, column: str, names: tuple[str, ...]) -> pd.DataFrame:
    """Add rows for values with no records.

    An empty category is a finding, not a gap in the chart: it says the
    taxonomy covers a product area this feedback never mentions.
    """
    missing = [n for n in names if n not in set(g[column])]
    if not missing:
        return g
    blank = {c: 0 for c in g.columns if c != column}
    return pd.concat(
        [g, pd.DataFrame([{column: n, **blank} for n in missing])],
        ignore_index=True,
    )


def category_table(rel: pd.DataFrame) -> pd.DataFrame:
    g = rel.groupby("primary_taxonomy_category").agg(
        records=("feedback_id", "count"),
        open_records=("is_open", "sum"),
        avg_severity=("severity", "mean"),
        high_severity=("is_high_severity", "sum"),
        avg_confidence=("confidence", "mean"),
        subcategories_seen=("primary_taxonomy_subcategory", "nunique"),
    ).reset_index()
    g = _pad(g, "primary_taxonomy_category", CATEGORY_NAMES)
    g["avg_severity"] = g["avg_severity"].round(2)
    g["avg_confidence"] = g["avg_confidence"].round(3)
    return g.sort_values(["records", "primary_taxonomy_category"],
                         ascending=[False, True]).reset_index(drop=True)


def subcategory_table(rel: pd.DataFrame) -> pd.DataFrame:
    """Every subcategory that actually occurs, with its parent category.

    Not padded to all 63: an all-zero drill-down chart would be unreadable,
    and the coverage figure in the KPIs already reports how many of the 63
    the dataset reaches.
    """
    g = rel.groupby(
        ["primary_taxonomy_category", "primary_taxonomy_subcategory"]
    ).agg(
        records=("feedback_id", "count"),
        open_records=("is_open", "sum"),
        avg_severity=("severity", "mean"),
    ).reset_index()
    g["avg_severity"] = g["avg_severity"].round(2)
    return g.sort_values(
        ["primary_taxonomy_category", "records", "primary_taxonomy_subcategory"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def stage_table(rel: pd.DataFrame) -> pd.DataFrame:
    """Where friction sits across the Action journey, in lifecycle order."""
    g = rel.groupby("journey_stage").agg(
        records=("feedback_id", "count"),
        open_records=("is_open", "sum"),
        avg_severity=("severity", "mean"),
        high_severity=("is_high_severity", "sum"),
    ).reset_index()
    g = _pad(g, "journey_stage", STAGE_NAMES)
    g["avg_severity"] = g["avg_severity"].round(2)
    order = {name: i for i, name in enumerate(STAGE_NAMES)}
    g["stage_order"] = g["journey_stage"].map(order)
    return g.sort_values("stage_order").reset_index(drop=True)


def problem_type_table(rel: pd.DataFrame) -> pd.DataFrame:
    g = rel.groupby("problem_type").agg(
        records=("feedback_id", "count"),
        open_records=("is_open", "sum"),
        avg_severity=("severity", "mean"),
    ).reset_index()
    g = _pad(g, "problem_type", PROBLEM_TYPE_NAMES)
    g["avg_severity"] = g["avg_severity"].round(2)
    return g.sort_values(["records", "problem_type"],
                         ascending=[False, True]).reset_index(drop=True)


def persona_table(rel: pd.DataFrame) -> pd.DataFrame:
    """Who is asking. Persona is independent of product area on purpose.

    An Action builder blocked on approval routing and a developer blocked on
    the same routing are different product problems even though they share a
    subcategory, and only this dimension separates them.
    """
    g = rel.groupby("persona").agg(
        records=("feedback_id", "count"),
        open_records=("is_open", "sum"),
        avg_severity=("severity", "mean"),
    ).reset_index()
    g = _pad(g, "persona", PERSONA_NAMES)
    g["avg_severity"] = g["avg_severity"].round(2)
    return g.sort_values(["records", "persona"],
                         ascending=[False, True]).reset_index(drop=True)


def secondary_table(rel: pd.DataFrame) -> pd.DataFrame:
    """How often each category is implicated *without* being the primary.

    A category with few primary records but many secondary mentions is a real
    finding: it is being dragged into other teams' problems rather than owning
    them. Kept in its own table, never added to the primary counts -- a record
    is counted once, in one place, or the totals stop meaning anything.
    """
    rows: list[dict] = []
    for categories in rel["secondary_categories"]:
        for category in (categories or []):
            rows.append({"category": category})
    if not rows:
        return pd.DataFrame({"category": list(CATEGORY_NAMES),
                             "secondary_mentions": 0})
    g = (pd.DataFrame(rows).groupby("category").size()
         .reset_index(name="secondary_mentions"))
    g = _pad(g, "category", CATEGORY_NAMES)
    return g.sort_values(["secondary_mentions", "category"],
                         ascending=[False, True]).reset_index(drop=True)


def lifecycle_table(rel: pd.DataFrame) -> pd.DataFrame:
    g = rel.groupby("lifecycle_status").agg(
        records=("feedback_id", "count"),
        avg_severity=("severity", "mean"),
    ).reset_index()
    g["avg_severity"] = g["avg_severity"].round(2)
    return g.sort_values("records", ascending=False).reset_index(drop=True)


# --- evidence --------------------------------------------------------------
def evidence_for(rel: pd.DataFrame, category: str, subcategory: str,
                 n: int = 3) -> list[dict]:
    """Supporting records for one product action that carry a verified quote.

    Unverified quotes are excluded here, not merely flagged: a quote the code
    could not find in the source is never shown as evidence for anything.
    """
    subset = rel[
        (rel["primary_taxonomy_category"] == category)
        & (rel["primary_taxonomy_subcategory"] == subcategory)
        & (rel["evidence_verified"])
    ]
    subset = subset.sort_values(
        ["severity", "confidence", "feedback_id"], ascending=[False, False, True]
    ).head(n)
    columns = ["feedback_id", "title", "severity", "confidence", "problem_type",
               "journey_stage", "lifecycle_status", "source_system",
               "evidence_excerpt", "short_summary", "source_url"]
    return subset[columns].to_dict("records")


# --- headline figures ------------------------------------------------------
def kpis(df: pd.DataFrame, rel: pd.DataFrame, actions: pd.DataFrame) -> dict:
    live = open_only(rel)
    subcats_seen = rel["primary_taxonomy_subcategory"].nunique()
    return {
        "feedback_records_analyzed": int(len(df)),
        "in_scope_records": int(len(rel)),
        "out_of_scope_records": int(len(df) - len(rel)),
        "open_records": int(len(live)),
        "resolved_records": int(len(rel) - len(live)),
        "recommended_product_actions": int(len(actions)),
        "high_severity_open_records": int((live["severity"] >= HIGH_SEVERITY).sum()),
        "top_product_action": (actions.iloc[0]["product_action"]
                               if len(actions) else ""),
        "top_product_action_category": (actions.iloc[0]["category"]
                                        if len(actions) else ""),
        "subcategories_covered": int(subcats_seen),
        "records_needing_review": int(rel["needs_human_review"].sum()),
        "records_with_secondary": int(
            rel["secondary_categories"].apply(lambda x: bool(x)).sum()),
        "low_confidence_records": int((rel["confidence"] < LOW_CONFIDENCE).sum()),
        "unverified_evidence": int((~rel["evidence_verified"]).sum()),
        "source_systems": sorted(df["source_system"].unique().tolist()),
    }


def build_all() -> dict:
    df = load_records()
    meta = df.attrs.get("meta", {})
    rel = relevant_only(df)

    # Derived flags computed once, so every table below counts them the same way.
    rel["is_open"] = rel["lifecycle_status"].isin(OPEN_STATUSES)
    rel["is_high_severity"] = rel["severity"] >= HIGH_SEVERITY

    actions = product_actions(rel)

    return {
        "meta": {
            "analysis_run_id": meta.get("analysis_run_id", ""),
            "model_name": meta.get("model_name", ""),
            "prompt_version": meta.get("prompt_version", ""),
            "taxonomy_version": meta.get("taxonomy_version", ""),
            "schema_version": meta.get("schema_version", ""),
            "generated_at": meta.get("generated_at", ""),
        },
        "ranking": {
            "keys": [{"key": k, "label": lbl, "explanation": e}
                     for k, lbl, e in RANK_KEYS],
            "explanation": (
                "Product actions are ranked lexicographically, not by a weighted "
                "score. Only open records count towards a ranking; completed and "
                "closed work is excluded so shipped features cannot argue for "
                "themselves again. Each key below is applied in order, and the "
                "first one that differs decides the position.\n\n"
                "**Evidence volume leads, severity follows.** Severity is one "
                "model's reading of one piece of text, so a lone severity-4 "
                "record is a far weaker signal than several independent records "
                "converging on the same problem. Ranking severity first put "
                "single-record requests above problems eight people reported. "
                "High severity is surfaced instead as its own KPI and filter, "
                "where a small number of severe records stays visible without "
                "displacing widely-reported ones."
            ),
            "open_statuses": sorted(OPEN_STATUSES),
        },
        "kpis": kpis(df, rel, actions),
        "product_actions": actions.to_dict("records") if len(actions) else [],
        "categories": category_table(rel).to_dict("records"),
        "subcategories": subcategory_table(rel).to_dict("records"),
        "stages": stage_table(rel).to_dict("records"),
        "problem_types": problem_type_table(rel).to_dict("records"),
        "personas": persona_table(rel).to_dict("records"),
        "secondary_mentions": secondary_table(rel).to_dict("records"),
        "lifecycle": lifecycle_table(rel).to_dict("records"),
        "evidence": {
            f"{r['category']}||{r['subcategory']}":
                evidence_for(rel, r["category"], r["subcategory"])
            for r in (actions.to_dict("records") if len(actions) else [])
        },
    }


def main() -> None:
    out = build_all()
    (PROC_DIR / "aggregates.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("KPIs")
    for key, val in out["kpis"].items():
        print(f"  {key:30s}: {val}")

    print("\nTop product actions")
    print(f"{'#':>2}  {'open':>4} {'sev':>4}  {'subcategory':38s} action")
    for r in out["product_actions"][:12]:
        print(f"{r['rank']:>2}  {r['open_records']:>4} {r['avg_severity']:>4.1f}  "
              f"{r['subcategory'][:38]:38s} {r['product_action'][:60]}")

    print("\nCategories")
    for r in out["categories"]:
        print(f"  {r['primary_taxonomy_category'][:40]:40s} "
              f"{r['records']:>4} records  {r['open_records']:>4} open")

    print("\nJourney stages")
    for r in out["stages"]:
        print(f"  {r['journey_stage'][:42]:42s} {r['records']:>4} records")

    print(f"\nWrote {(PROC_DIR / 'aggregates.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
