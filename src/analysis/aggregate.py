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
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from ..models.taxonomy import (
    CATEGORY_FOR_SUBCATEGORY,
    CATEGORY_NAMES,
    COUNTED_STATUSES,
    OPEN_STATUSES,
    PERSONA_NAMES,
    POLARITY_NAMES,
    PROBLEM_TYPE_NAMES,
    STAGE_NAMES,
)
from . import grouping

ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT / "data" / "processed"

HIGH_SEVERITY = 4
LOW_CONFIDENCE = 0.7

# The trend chart's window, and how many examples an insight card shows.
TREND_WEEKS = 13                 # ~3 calendar months of Monday-starting weeks
MAX_INSIGHT_EXAMPLES = 3
RECENT_DATA_DAYS = 14            # see trend_window()

# The ranking keys, applied in this order, all descending.
#
# Each entry is (field, plain_label, explanation). The plain label exists so
# the dashboard can explain the ranking to a reader with no background here --
# a sidebar listing `severity_band` and `avg_confidence` is accurate and
# useless. Keeping the label beside the field means the readable version is
# generated from the same source that does the sorting, and cannot drift.
#
# Severity leads, and it is the *median* of the open supporting records rather
# than the mean or the max: one unusually severe report should not make an
# otherwise mild request look like a blocker.
RANK_KEYS: tuple[tuple[str, str, str], ...] = (
    ("severity_band",
     "How much it typically hurts",
     "Severity band, from the median severity of the open supporting records. "
     "A higher band always ranks first, however many records the other action "
     "has."),
    ("open_supporting_record_count",
     "How many people asked for it",
     "Distinct open feedback records supporting this exact product action."),
    ("average_confidence",
     "How sure the AI was",
     "Mean classification confidence across the open supporting records."),
    ("source_diversity",
     "How many different sources it came from",
     "Distinct source systems among the open supporting records."),
    ("latest_created_sort",
     "How recently it was raised",
     "Newest source-created date among the open supporting records. Records "
     "with no known date rank below those that have one."),
)


def load_records() -> pd.DataFrame:
    data = json.loads((PROC_DIR / "analyzed.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(data["records"])
    df.attrs["meta"] = data.get("meta", {})
    return df


def relevant_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["is_relevant"]].copy()


def open_only(rel: pd.DataFrame) -> pd.DataFrame:
    """Records that count as live, unmet demand.

    Only `Open`. Planned and In progress both mean Port has already committed
    to the work, so counting them as open demand argues for building something
    that is already being built; Completed and Closed have shipped or been
    dropped. All of them stay visible through the lifecycle filter and are
    labelled with their status -- they simply do not add to a product action's
    supporting count or to its ranking.
    """
    return rel[rel["lifecycle_status"].isin(COUNTED_STATUSES)].copy()


def live_only(rel: pd.DataFrame) -> pd.DataFrame:
    """Anything not yet shipped or dropped -- used for display, never ranking."""
    return rel[rel["lifecycle_status"].isin(OPEN_STATUSES)].copy()


# --- product actions -------------------------------------------------------
def _median_severity(values: list[int]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def product_actions(rel: pd.DataFrame) -> pd.DataFrame:
    """Group feedback by the change it asks for, then rank the groups.

    Membership is explicit. Each group stores the feedback ids that belong to
    it, and every figure on its card is computed from those ids -- so the count
    shown and the records the drill-down opens are the same set by
    construction. They used to be a taxonomy subcategory and its whole
    membership, which is why a card could claim four records and open onto
    fourteen.
    """
    if rel.empty:
        return pd.DataFrame()

    records = rel.to_dict("records")
    rows: list[dict] = []

    for group in grouping.cluster(records):
        title = grouping.canonical_title(group)
        supporting_ids = sorted({str(r["feedback_id"]) for r in group})

        # Only Open records feed any ranking figure.
        open_members = [r for r in group
                        if r.get("lifecycle_status") in COUNTED_STATUSES]
        open_ids = sorted({str(r["feedback_id"]) for r in open_members})

        severities = [int(r["severity"]) for r in open_members]
        confidences = [float(r["confidence"]) for r in open_members]
        sources = sorted({str(r["source_system"]) for r in open_members})
        created = sorted(str(r.get("created_at") or "") for r in open_members)
        latest = next((d for d in reversed(created) if d), "")

        typical = _median_severity(severities)
        rows.append({
            "product_action_id": grouping.slugify(title),
            "product_action_title": title,
            "product_action_source_id": grouping.title_source_id(group, title),
            "supporting_feedback_ids": supporting_ids,
            "open_supporting_feedback_ids": open_ids,
            # The invariant the card depends on: the number shown is the length
            # of the exact id list the drill-down will use.
            "open_supporting_record_count": len(open_ids),
            "typical_severity": round(typical, 2),
            "severity_band": int(round(typical)) if severities else 0,
            "max_severity": max(severities) if severities else 0,
            "average_confidence": round(sum(confidences) / len(confidences), 3)
                                  if confidences else 0.0,
            "source_systems": sources,
            "source_diversity": len(sources),
            "latest_created_at": latest[:10],
            # Empty dates must sort last, not first, on a descending sort.
            "latest_created_sort": latest or "",
            "primary_categories": sorted({str(r["primary_taxonomy_category"])
                                          for r in group}),
            "primary_subcategories": sorted({str(r["primary_taxonomy_subcategory"])
                                             for r in group}),
            "top_problem_type": Counter(
                r["problem_type"] for r in open_members or group).most_common(1)[0][0],
            "top_journey_stage": Counter(
                r["journey_stage"] for r in open_members or group).most_common(1)[0][0],
            "needs_review": sum(1 for r in open_members
                                if r.get("needs_human_review")),
            "negative_records": sum(1 for r in open_members
                                    if r.get("feedback_polarity") == "Negative"),
        })

    actions = pd.DataFrame(rows)
    total_groups = len(actions)
    # An action with no open record is not current demand and is not ranked.
    # The total is carried through so the dashboard can say how many distinct
    # changes were requested versus how many still have live demand.
    actions = actions[actions["open_supporting_record_count"] > 0]
    if actions.empty:
        empty = pd.DataFrame()
        empty.attrs["total_groups"] = total_groups
        return empty

    # Lexicographic. The title makes the order total, so the same input always
    # produces the same ranking rather than one that depends on row order.
    actions = actions.sort_values(
        [key for key, *_ in RANK_KEYS] + ["product_action_title"],
        ascending=[False] * len(RANK_KEYS) + [True],
    ).reset_index(drop=True)
    actions["rank"] = actions.index + 1
    actions.attrs["total_groups"] = total_groups
    return actions


def evidence_for_action(rel: pd.DataFrame, feedback_ids: list[str]) -> list[dict]:
    """The records behind one product action, by id.

    Never by category, subcategory, stage or label text -- the ids are the
    membership, so this cannot return a different set from the one counted.
    """
    subset = rel[rel["feedback_id"].astype(str).isin(list(feedback_ids))]
    subset = subset.sort_values(
        ["severity", "confidence", "feedback_id"], ascending=[False, False, True])
    return subset.to_dict("records")


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
# --- negative-feedback insights -------------------------------------------
def negative_only(rel: pd.DataFrame) -> pd.DataFrame:
    """Records whose author was describing a problem.

    Polarity comes from the classifier reading the text, not from lifecycle
    status: a Completed roadmap item still records the pain that prompted it,
    so filtering on status would erase the signal for everything already built.
    """
    if "feedback_polarity" not in rel.columns:
        return rel.iloc[0:0]
    return rel[rel["feedback_polarity"] == "Negative"].copy()


def _example_text(record: dict, limit: int = 12) -> str:
    """One short line naming the problem, taken from the record's own summary.

    Trimmed to roughly a dozen words. Nothing is invented: this is the model's
    summary of that record, and the record's id travels with it.
    """
    text = str(record.get("short_summary") or record.get("title") or "").strip()
    words = text.rstrip(".").split()
    if len(words) > limit:
        text = " ".join(words[:limit]) + "…"
    else:
        text = " ".join(words)
    return text[:1].upper() + text[1:] if text else ""


def _insight_examples(records: list[dict]) -> list[dict]:
    """Up to three distinct problems, chosen deterministically.

    Near-duplicates are collapsed first -- three phrasings of one complaint
    would fill the card and hide the other two problems. Ranking is the same
    lexicographic shape used elsewhere: severity, then how many records back
    the example, then confidence, then recency, then text.
    """
    buckets: list[tuple[frozenset[str], list[dict]]] = []
    for record in sorted(records, key=lambda r: str(r["feedback_id"])):
        signature = grouping.tokens(
            str(record.get("short_summary") or record.get("title") or ""))
        for index, (existing, bucket) in enumerate(buckets):
            if grouping.similarity(signature, existing) >= 0.5:
                bucket.append(record)
                buckets[index] = (existing | signature, bucket)
                break
        else:
            buckets.append((signature, [record]))

    ranked = []
    for _signature, bucket in buckets:
        lead = max(bucket, key=lambda r: (int(r.get("severity", 0)),
                                          float(r.get("confidence", 0.0))))
        ranked.append({
            "text": _example_text(lead),
            "supporting_feedback_ids": sorted({str(r["feedback_id"])
                                               for r in bucket}),
            "_severity": int(lead.get("severity", 0)),
            "_count": len(bucket),
            "_confidence": float(lead.get("confidence", 0.0)),
            "_created": str(lead.get("created_at") or ""),
        })
    ranked.sort(key=lambda e: (-e["_severity"], -e["_count"], -e["_confidence"],
                               e["_created"] == "", [-ord(c) for c in e["_created"]],
                               e["text"]))
    out = []
    for entry in ranked[:MAX_INSIGHT_EXAMPLES]:
        if entry["text"]:
            out.append({"text": entry["text"],
                        "supporting_feedback_ids": entry["supporting_feedback_ids"]})
    return out


def _recommended_focus(records: list[dict]) -> str:
    """A one-line focus, built from the problem types actually present.

    Assembled from counted fields rather than written by the model, so it
    cannot assert something the records do not show.
    """
    if not records:
        return ""
    top = Counter(str(r.get("problem_type") or "") for r in records).most_common(2)
    names = [name.lower() for name, _ in top if name]
    if not names:
        return "Reduce the friction reported here."
    if len(names) == 1:
        return f"Mostly {names[0]}."
    return f"Mostly {names[0]}, then {names[1]}."


def negative_insight(rel: pd.DataFrame, group_type: str,
                     selected: list[str] | None = None) -> dict:
    """The group with the most negative feedback, honouring the filters.

    `selected` is what the reader has already chosen. When they have picked
    exactly one value the card shows that one even if another leads globally --
    a card that ignores the filter beside it is worse than no card.
    """
    column = ("journey_stage" if group_type == "journey_stage"
              else "primary_taxonomy_subcategory")
    negative = negative_only(rel)
    if selected:
        negative = negative[negative[column].isin(selected)]
    if negative.empty:
        return {"group_type": group_type, "group_name": "",
                "negative_feedback_count": 0, "recommended_focus": "",
                "examples": [], "parent_category": ""}

    counts = negative[column].value_counts()
    # Ties resolve alphabetically so the card cannot flicker between reruns.
    top_count = int(counts.max())
    name = sorted(n for n, c in counts.items() if int(c) == top_count)[0]

    members = negative[negative[column] == name].to_dict("records")
    return {
        "group_type": group_type,
        "group_name": str(name),
        "parent_category": (CATEGORY_FOR_SUBCATEGORY.get(str(name), "")
                            if group_type == "subcategory" else ""),
        "negative_feedback_count": len(members),
        "recommended_focus": _recommended_focus(members),
        "examples": _insight_examples(members),
        "supporting_feedback_ids": sorted({str(r["feedback_id"])
                                           for r in members}),
    }


# --- trend -----------------------------------------------------------------
def trend_window(rel: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp, bool]:
    """The rolling three-month window, and whether it had to fall back.

    Normally it ends today. If the newest record is older than RECENT_DATA_DAYS
    the dataset is a historical snapshot, and ending at today would render an
    empty chart that looks like a bug -- so the window ends at the newest known
    created_at instead, and the caller labels it as such.
    """
    created = pd.to_datetime(rel.get("created_at"), errors="coerce", utc=True)
    today = pd.Timestamp.now(tz="UTC").normalize()
    newest = created.max()
    historical = bool(
        pd.isna(newest) or (today - newest).days > RECENT_DATA_DAYS)
    end = (newest.normalize() if historical and not pd.isna(newest) else today)
    # Monday of the week the window ends in, minus 12 weeks -> 13 weekly points.
    end_week = end - pd.Timedelta(days=int(end.dayofweek))
    start_week = end_week - pd.Timedelta(weeks=TREND_WEEKS - 1)
    return start_week, end_week, historical


def negative_trend(rel: pd.DataFrame) -> dict:
    """Weekly negative-feedback counts per journey stage.

    Uses `created_at` -- when the customer raised it -- never the analysis or
    retrieval timestamp, which would cluster every record onto the day the
    pipeline last ran.
    """
    negative = negative_only(rel)
    start_week, end_week, historical = trend_window(rel)
    weeks = [(start_week + pd.Timedelta(weeks=i)) for i in range(TREND_WEEKS)]
    labels = [w.strftime("%Y-%m-%d") for w in weeks]

    series: list[dict] = []
    if not negative.empty:
        frame = negative.copy()
        frame["_created"] = pd.to_datetime(frame["created_at"],
                                           errors="coerce", utc=True)
        frame = frame.dropna(subset=["_created"])
        frame["_week"] = (frame["_created"].dt.normalize()
                          - pd.to_timedelta(frame["_created"].dt.dayofweek, unit="D"))
        frame = frame[(frame["_week"] >= start_week) & (frame["_week"] <= end_week)]
        # Distinct ids only: a record must not be counted twice in a week.
        frame = frame.drop_duplicates(subset=["feedback_id"])

        for stage in STAGE_NAMES:            # chronological, never by volume
            rows = frame[frame["journey_stage"] == stage]
            if rows.empty:
                continue
            per_week = rows.groupby(rows["_week"].dt.strftime("%Y-%m-%d")).size()
            # Missing weeks are zero, not gaps in the line.
            series.append({
                "stage": stage,
                "points": [int(per_week.get(label, 0)) for label in labels],
                "total": int(len(rows)),
            })

    return {
        "weeks": labels,
        "series": series,
        "window_start": start_week.strftime("%Y-%m-%d"),
        "window_end": end_week.strftime("%Y-%m-%d"),
        "is_historical_snapshot": historical,
    }


# --- headline figures ------------------------------------------------------
def kpis(df: pd.DataFrame, rel: pd.DataFrame, actions: pd.DataFrame) -> dict:
    live = open_only(rel)
    negative = negative_only(rel)
    subcats_seen = rel["primary_taxonomy_subcategory"].nunique()
    return {
        "feedback_records_analyzed": int(len(df)),
        "in_scope_records": int(len(rel)),
        "out_of_scope_records": int(len(df) - len(rel)),
        "open_records": int(len(live)),
        "resolved_records": int(len(rel) - len(live)),
        "recommended_product_actions": int(actions.attrs.get("total_groups",
                                                             len(actions))),
        "open_product_actions": int(len(actions)),
        "high_severity_open_records": int((live["severity"] >= HIGH_SEVERITY).sum()),
        "top_product_action": (actions.iloc[0]["product_action_title"]
                               if len(actions) else ""),
        "top_product_action_category": (actions.iloc[0]["primary_categories"][0]
                                        if len(actions) else ""),
        "negative_records": int(len(negative)),
        "subcategories_covered": int(subcats_seen),
        "records_needing_review": int(rel["needs_human_review"].sum()),
        "records_with_secondary": int(
            rel["secondary_categories"].apply(lambda x: bool(x)).sum()),
        "low_confidence_records": int((rel["confidence"] < LOW_CONFIDENCE).sum()),
        "unverified_evidence": int((~rel["evidence_verified"]).sum()),
        "source_systems": sorted(df["source_system"].unique().tolist()),
    }


def polarity_table(rel: pd.DataFrame) -> pd.DataFrame:
    if "feedback_polarity" not in rel.columns:
        return pd.DataFrame({"feedback_polarity": list(POLARITY_NAMES),
                             "records": [0] * len(POLARITY_NAMES)})
    g = rel.groupby("feedback_polarity").agg(
        records=("feedback_id", "count"),
        avg_severity=("severity", "mean"),
    ).reset_index()
    g = _pad(g, "feedback_polarity", POLARITY_NAMES)
    g["avg_severity"] = g["avg_severity"].round(2)
    return g.sort_values("records", ascending=False).reset_index(drop=True)


def build_all() -> dict:
    df = load_records()
    meta = df.attrs.get("meta", {})
    rel = relevant_only(df)

    # Derived flags computed once, so every table below counts them the same way.
    rel["is_open"] = rel["lifecycle_status"].isin(COUNTED_STATUSES)
    rel["is_high_severity"] = rel["severity"] >= HIGH_SEVERITY

    actions = product_actions(rel)
    action_rows = actions.to_dict("records") if len(actions) else []

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
                "Only open feedback counts. Feedback asking for the same change "
                "is grouped together, and each group is ranked by typical "
                "severity, open records, average confidence, source diversity "
                "and recency -- in that order.\n\n"
                "The ranking is hierarchical, not a blended score: each key is "
                "applied in turn and the first one that differs decides the "
                "position, so no later key can override an earlier one. "
                "Severity is the *median* of the supporting records rather than "
                "the worst of them, so one unusually severe report cannot make "
                "an otherwise mild request look like a blocker."
            ),
            "counted_statuses": sorted(COUNTED_STATUSES),
        },
        "kpis": kpis(df, rel, actions),
        "product_actions": action_rows,
        "insights": {
            "journey_stage": negative_insight(rel, "journey_stage"),
            "subcategory": negative_insight(rel, "subcategory"),
        },
        "negative_trend": negative_trend(rel),
        "categories": category_table(rel).to_dict("records"),
        "subcategories": subcategory_table(rel).to_dict("records"),
        "stages": stage_table(rel).to_dict("records"),
        "problem_types": problem_type_table(rel).to_dict("records"),
        "personas": persona_table(rel).to_dict("records"),
        "polarity": polarity_table(rel).to_dict("records"),
        "secondary_mentions": secondary_table(rel).to_dict("records"),
        "lifecycle": lifecycle_table(rel).to_dict("records"),
        # Keyed by product action id, holding the exact supporting record ids.
        # Never keyed by category or subcategory: that is what made the count
        # and the drill-down disagree.
        "evidence": {
            r["product_action_id"]: r["open_supporting_feedback_ids"]
            for r in action_rows
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
    print(f"{'#':>2}  {'open':>4} {'sev':>4}  {'id':38s} title")
    for r in out["product_actions"][:12]:
        print(f"{r['rank']:>2}  {r['open_supporting_record_count']:>4} "
              f"{r['severity_band']:>4}  {r['product_action_id'][:38]:38s} "
              f"{r['product_action_title'][:52]}")

    print("\nNegative insights")
    for key in ("journey_stage", "subcategory"):
        card = out["insights"][key]
        print(f"  {key:14s} {card['group_name'][:40]:40s} "
              f"{card['negative_feedback_count']} negative")
        for ex in card["examples"]:
            print(f"      - {ex['text']}")

    t = out["negative_trend"]
    print(f"\nTrend {t['window_start']} -> {t['window_end']} "
          f"({len(t['series'])} stages, historical={t['is_historical_snapshot']})")

    print("Categories")
    for r in out["categories"]:
        print(f"  {r['primary_taxonomy_category'][:40]:40s} "
              f"{r['records']:>4} records  {r['open_records']:>4} open")

    print("\nJourney stages")
    for r in out["stages"]:
        print(f"  {r['journey_stage'][:42]:42s} {r['records']:>4} records")

    print(f"\nWrote {(PROC_DIR / 'aggregates.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
