"""Deterministic analyses behind the Product Data Assistant.

Every function here is plain pandas over the already-classified records. No
model is called, nothing is generated, and the same input always produces the
same answer -- which is the whole point: an assistant that computes is
checkable in a way that one which narrates is not.

Each answer carries the exact `feedback_id` list behind every row, so the
evidence drawer opens onto the records the number was computed from rather
than onto everything sharing a category.

Grouping, lifecycle and taxonomy definitions are imported, never re-derived.
A second copy of the product-action grouping would be free to disagree with
the dashboard, and eventually would.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

from ..analysis.aggregate import COUNTED_STATUSES, product_actions
from ..models.taxonomy import CATEGORY_FOR_SUBCATEGORY, STAGE_NAMES

TOP_N = 5

# Statuses meaning the work is committed but not yet delivered.
COMMITTED_STATUSES = ("Planned", "In progress")

# Problem types that describe something broken rather than something missing.
DEFECT_PROBLEM_TYPES = ("Bug / defect", "Validation gap", "Poor error message")

HIGH_SEVERITY = 4
MIN_SHARE_DENOMINATOR = 3      # question 6
MIN_CATEGORY_RECORDS = 5       # question 7


@dataclass(frozen=True)
class AnswerRow:
    """One ranked result, with the records it was computed from."""

    label: str
    values: dict[str, str]
    feedback_ids: list[str] = field(default_factory=list)
    sublabel: str = ""


@dataclass(frozen=True)
class Answer:
    finding: str
    columns: tuple[tuple[str, str], ...] = ()
    rows: tuple[AnswerRow, ...] = ()
    note: str = ""
    empty_message: str = "No records match this question in the selected scope."

    @property
    def is_empty(self) -> bool:
        return not self.rows


# --- shared helpers --------------------------------------------------------
def _dates(frame: pd.DataFrame) -> pd.Series:
    """Parsed `created_at`. Never analysed_at or retrieved_at.

    Those record when the pipeline ran, so ranking by them would say the same
    thing about every record and call it recency.
    """
    return pd.to_datetime(frame.get("created_at"), errors="coerce", utc=True)


def reference_date(frame: pd.DataFrame) -> pd.Timestamp:
    """The date ages are measured against.

    The newest record in the data, not today. This dataset is a snapshot, and
    measuring against the wall clock would silently inflate every age by
    however long ago it was collected.
    """
    parsed = _dates(frame).dropna()
    if parsed.empty:
        return pd.Timestamp.now(tz="UTC").normalize()
    return parsed.max().normalize()


def open_records(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["lifecycle_status"].isin(COUNTED_STATUSES)]


def negative_records(frame: pd.DataFrame) -> pd.DataFrame:
    if "feedback_polarity" not in frame.columns:
        return frame.iloc[0:0]
    return frame[frame["feedback_polarity"] == "Negative"]


def _ids(frame: pd.DataFrame) -> list[str]:
    """Distinct ids, sorted. A record must never be counted twice."""
    return sorted({str(v) for v in frame["feedback_id"]})


def _actions_with_records(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Product actions plus a lookup from feedback id to record."""
    actions = product_actions(frame)
    by_id = {str(r["feedback_id"]): r for r in frame.to_dict("records")}
    return actions, by_id


def _pct(part: int, whole: int) -> str:
    return f"{(part / whole * 100):.0f}%" if whole else "-"


# --- question 1 ------------------------------------------------------------
def oldest_unresolved_actions(frame: pd.DataFrame) -> Answer:
    actions, by_id = _actions_with_records(frame)
    if not len(actions):
        return Answer(finding="", empty_message="No open product actions in scope.")

    today = reference_date(frame)
    rows = []
    for action in actions.to_dict("records"):
        ids = action["open_supporting_feedback_ids"]
        dated = [(pd.Timestamp(by_id[i]["created_at"]), i) for i in ids
                 if i in by_id and pd.notna(pd.to_datetime(
                     by_id[i].get("created_at"), errors="coerce", utc=True))]
        if not dated:
            # No usable date means no age. Ranking it anyway would put an
            # unknown above a genuinely old request.
            continue
        oldest, _ = min(dated, key=lambda p: p[0])
        rows.append((oldest, action, ids))

    rows.sort(key=lambda r: (r[0],
                             -int(r[1]["severity_band"]),
                             -int(r[1]["open_supporting_record_count"]),
                             r[1]["product_action_title"]))

    out = []
    for oldest, action, ids in rows[:TOP_N]:
        age = (today - oldest.tz_convert("UTC").normalize()).days
        out.append(AnswerRow(
            label=action["product_action_title"],
            sublabel=action["primary_categories"][0] if action["primary_categories"] else "",
            values={
                "oldest": oldest.strftime("%Y-%m-%d"),
                "age": f"{age} days",
                "records": str(action["open_supporting_record_count"]),
                "severity": str(action["severity_band"]),
            },
            feedback_ids=ids,
        ))

    finding = (f"“{out[0].label}” has been open longest - "
               f"{out[0].values['age']} since its earliest open record."
               if out else "")
    return Answer(
        finding=finding,
        columns=(("oldest", "Oldest open"), ("age", "Age"),
                 ("records", "Open records"), ("severity", "Typical severity")),
        rows=tuple(out),
        note=f"Age measured from each action's earliest open `created_at`, "
             f"against the newest date in the data ({today.date()}). Actions "
             f"with no dated open record are excluded rather than ranked.",
    )


# --- question 2 ------------------------------------------------------------
def recurring_demand(frame: pd.DataFrame) -> Answer:
    actions, by_id = _actions_with_records(frame)
    if not len(actions):
        return Answer(finding="", empty_message="No open product actions in scope.")

    rows = []
    for action in actions.to_dict("records"):
        ids = action["open_supporting_feedback_ids"]
        dated = sorted(
            pd.Timestamp(by_id[i]["created_at"]) for i in ids
            if i in by_id and pd.notna(pd.to_datetime(
                by_id[i].get("created_at"), errors="coerce", utc=True)))
        # One record is a report, not a recurrence.
        if len(dated) < 2:
            continue
        span = (dated[-1] - dated[0]).days
        rows.append((span, action, dated, ids))

    rows.sort(key=lambda r: (-r[0],
                             -int(r[1]["open_supporting_record_count"]),
                             -int(r[1]["severity_band"]),
                             r[1]["product_action_title"]))

    out = [AnswerRow(
        label=action["product_action_title"],
        sublabel=action["primary_categories"][0] if action["primary_categories"] else "",
        values={
            "first": dated[0].strftime("%Y-%m-%d"),
            "last": dated[-1].strftime("%Y-%m-%d"),
            "span": f"{span} days",
            "records": str(action["open_supporting_record_count"]),
        },
        feedback_ids=ids,
    ) for span, action, dated, ids in rows[:TOP_N]]

    finding = (f"“{out[0].label}” has been raised repeatedly across "
               f"{out[0].values['span']}." if out else "")
    return Answer(
        finding=finding,
        columns=(("first", "First raised"), ("last", "Most recent"),
                 ("span", "Demand span"), ("records", "Open records")),
        rows=tuple(out),
        note="Only actions with at least two dated open records appear. A "
             "single record is a report, not recurring demand.",
        empty_message="No product action has two or more dated open records in "
                      "this scope, so nothing here recurs.",
    )


# --- question 3 ------------------------------------------------------------
def most_discussed_in_portal(frame: pd.DataFrame) -> Answer:
    actions, by_id = _actions_with_records(frame)
    if not len(actions):
        return Answer(finding="", empty_message="No open product actions in scope.")

    rows = []
    for action in actions.to_dict("records"):
        ids = action["open_supporting_feedback_ids"]
        portal = [by_id[i] for i in ids
                  if i in by_id and by_id[i].get("source_system") == "Port portal"]
        commented = [r for r in portal if int(r.get("comments_count") or 0) > 0]
        total = sum(int(r.get("comments_count") or 0) for r in portal)
        if total <= 0:
            continue
        rows.append((total, len(commented), action, ids))

    rows.sort(key=lambda r: (-r[0], -r[1],
                             -int(r[2]["open_supporting_record_count"]),
                             -int(r[2]["severity_band"]),
                             r[2]["product_action_title"]))

    out = [AnswerRow(
        label=action["product_action_title"],
        sublabel=action["primary_categories"][0] if action["primary_categories"] else "",
        values={
            "comments": str(total),
            "posts": str(commented),
            "records": str(action["open_supporting_record_count"]),
            "severity": str(action["severity_band"]),
        },
        feedback_ids=ids,
    ) for total, commented, action, ids in rows[:TOP_N]]

    finding = (f"“{out[0].label}” has drawn the most portal discussion - "
               f"{out[0].values['comments']} comments." if out else "")
    return Answer(
        finding=finding,
        columns=(("comments", "Comments"), ("posts", "Posts with comments"),
                 ("records", "Open records"), ("severity", "Typical severity")),
        rows=tuple(out),
        note="Portal comments are an engagement signal only. They are not used "
             "in the official Product Action ranking because other sources may "
             "not provide an equivalent metric. A comment count is a count of "
             "comments, not of distinct customers.",
        empty_message="No open supporting record from the Port portal carries "
                      "any comments in this scope.",
    )


# --- question 4 ------------------------------------------------------------
def high_severity_single_signals(frame: pd.DataFrame) -> Answer:
    actions, by_id = _actions_with_records(frame)
    if not len(actions):
        return Answer(finding="", empty_message="No open product actions in scope.")

    candidates = [a for a in actions.to_dict("records")
                  if int(a["open_supporting_record_count"]) == 1
                  and int(a["severity_band"]) >= HIGH_SEVERITY]
    candidates.sort(key=lambda a: (-int(a["severity_band"]),
                                   -float(a["average_confidence"]),
                                   a["latest_created_at"] == "",
                                   [-ord(c) for c in a["latest_created_at"]],
                                   a["product_action_title"]))

    out = []
    for action in candidates[:TOP_N]:
        ids = action["open_supporting_feedback_ids"]
        record = by_id.get(ids[0], {}) if ids else {}
        out.append(AnswerRow(
            label=action["product_action_title"],
            sublabel=f"{record.get('primary_taxonomy_category', '')} › "
                     f"{record.get('primary_taxonomy_subcategory', '')}",
            values={
                "severity": str(action["severity_band"]),
                "created": action["latest_created_at"] or "-",
                "confidence": f"{action['average_confidence']:.2f}",
            },
            feedback_ids=ids,
        ))

    finding = (f"{len(candidates)} high-severity action"
               f"{'s are' if len(candidates) != 1 else ' is'} backed by a "
               f"single open record." if out else "")
    return Answer(
        finding=finding,
        columns=(("severity", "Severity"), ("created", "Created"),
                 ("confidence", "Confidence")),
        rows=tuple(out),
        note="These are high-severity signals with limited supporting volume. "
             "They may deserve investigation, but one record alone does not "
             "establish broad demand.",
        empty_message="No open action in this scope combines severity 4+ with a "
                      "single supporting record.",
    )


# --- question 5 ------------------------------------------------------------
def needs_most_human_review(frame: pd.DataFrame) -> Answer:
    actions, by_id = _actions_with_records(frame)
    if not len(actions):
        return Answer(finding="", empty_message="No open product actions in scope.")

    rows = []
    for action in actions.to_dict("records"):
        ids = action["open_supporting_feedback_ids"]
        members = [by_id[i] for i in ids if i in by_id]
        flagged = [r for r in members if r.get("needs_human_review")]
        if not flagged:
            continue
        confidences = [float(r.get("confidence") or 0) for r in members]
        rows.append((len(flagged), len(flagged) / max(len(members), 1),
                     sum(confidences) / max(len(confidences), 1), action, ids))

    rows.sort(key=lambda r: (-r[0], -r[1],
                             -int(r[3]["severity_band"]),
                             -int(r[3]["open_supporting_record_count"]),
                             r[3]["product_action_title"]))

    out = [AnswerRow(
        label=action["product_action_title"],
        sublabel=action["primary_categories"][0] if action["primary_categories"] else "",
        values={
            "flagged": str(count),
            "share": f"{share * 100:.0f}%",
            "confidence": f"{conf:.2f}",
            "records": str(action["open_supporting_record_count"]),
        },
        feedback_ids=ids,
    ) for count, share, conf, action, ids in rows[:TOP_N]]

    finding = (f"“{out[0].label}” carries the most unresolved classification "
               f"uncertainty - {out[0].values['flagged']} of its supporting "
               f"records are flagged." if out else "")
    return Answer(
        finding=finding,
        columns=(("flagged", "Flagged"), ("share", "Share of records"),
                 ("confidence", "Avg confidence"), ("records", "Open records")),
        rows=tuple(out),
        note="A flag means the classification should be validated before this "
             "is prioritised. It does not mean the product action is wrong.",
        empty_message="No open supporting record in this scope is flagged for "
                      "human review.",
    )


# --- question 6 ------------------------------------------------------------
def high_severity_share_by_subcategory(frame: pd.DataFrame) -> Answer:
    pool = negative_records(open_records(frame))
    if pool.empty:
        return Answer(finding="", empty_message="No open negative feedback in scope.")

    rows = []
    for name, group in pool.groupby("primary_taxonomy_subcategory"):
        ids = _ids(group)
        if len(ids) < MIN_SHARE_DENOMINATOR:
            # A 1-of-1 subcategory would show 100% and mean nothing.
            continue
        severe = group[group["severity"] >= HIGH_SEVERITY]
        severe_ids = _ids(severe)
        rows.append((len(severe_ids) / len(ids), len(severe_ids), len(ids),
                     str(name), severe_ids or ids))

    rows.sort(key=lambda r: (-r[0], -r[1], -r[2], r[3]))

    out = [AnswerRow(
        label=name,
        sublabel=CATEGORY_FOR_SUBCATEGORY.get(name, ""),
        values={
            "share": f"{share * 100:.0f}%",
            "severe": str(severe),
            "total": str(total),
        },
        feedback_ids=ids,
    ) for share, severe, total, name, ids in rows[:TOP_N]]

    finding = (f"{out[0].label}: {out[0].values['share']} of its open negative "
               f"feedback is high severity ({out[0].values['severe']} of "
               f"{out[0].values['total']})." if out else "")
    return Answer(
        finding=finding,
        columns=(("share", "High-severity share"), ("severe", "Severity 4+"),
                 ("total", "Open negative")),
        rows=tuple(out),
        note=f"Share = severity 4+ ÷ all open negative records in the "
             f"subcategory. Subcategories with fewer than "
             f"{MIN_SHARE_DENOMINATOR} open negative records are excluded, "
             f"because a share out of one or two is not a rate. Primary "
             f"assignments only.",
    )


# --- question 7 ------------------------------------------------------------
def unresolved_demand_rate(frame: pd.DataFrame) -> Answer:
    if frame.empty:
        return Answer(finding="", empty_message="No records in scope.")

    rows = []
    for name, group in frame.groupby("primary_taxonomy_category"):
        ids = _ids(group)
        if len(ids) < MIN_CATEGORY_RECORDS:
            continue
        still_open = open_records(group)
        open_ids = _ids(still_open)
        rows.append((len(open_ids) / len(ids), len(open_ids), len(ids),
                     str(name), open_ids or ids))

    rows.sort(key=lambda r: (-r[0], -r[1], -r[2], r[3]))

    out = [AnswerRow(
        label=name,
        values={
            "rate": f"{rate * 100:.0f}%",
            "open": str(open_count),
            "total": str(total),
            "other": str(total - open_count),
        },
        feedback_ids=ids,
    ) for rate, open_count, total, name, ids in rows[:TOP_N]]

    finding = (f"{out[0].label} has the highest unresolved-demand rate - "
               f"{out[0].values['rate']} of its feedback is still open."
               if out else "")
    return Answer(
        finding=finding,
        columns=(("rate", "Open rate"), ("open", "Open"),
                 ("total", "All records"), ("other", "Planned/done/closed")),
        rows=tuple(out),
        note=f"Open rate = open records ÷ all in-scope records in the category. "
             f"Categories with fewer than {MIN_CATEGORY_RECORDS} records are "
             f"excluded. This is a backlog measure, not churn or conversion.",
    )


# --- question 8 ------------------------------------------------------------
def defects_by_journey_stage(frame: pd.DataFrame) -> Answer:
    pool = negative_records(open_records(frame))
    pool = pool[pool["problem_type"].isin(DEFECT_PROBLEM_TYPES)]
    if pool.empty:
        return Answer(
            finding="",
            empty_message="No open negative bugs, validation gaps or error-message "
                          "problems in this scope.")

    order = {name: i for i, name in enumerate(STAGE_NAMES)}
    rows = []
    for name, group in pool.groupby("journey_stage"):
        ids = _ids(group)
        counts = Counter(group["problem_type"])
        severe = _ids(group[group["severity"] >= HIGH_SEVERITY])
        rows.append((len(ids), len(severe), order.get(str(name), 99),
                     str(name), counts, ids))

    rows.sort(key=lambda r: (-r[0], -r[1], r[2]))

    out = [AnswerRow(
        label=name,
        values={
            "total": str(total),
            "bugs": str(counts.get("Bug / defect", 0)),
            "validation": str(counts.get("Validation gap", 0)),
            "errors": str(counts.get("Poor error message", 0)),
            "severe": str(severe),
        },
        feedback_ids=ids,
    ) for total, severe, _pos, name, counts, ids in rows[:TOP_N]]

    finding = (f"{out[0].label} carries the most operational defects - "
               f"{out[0].values['total']} open records." if out else "")
    return Answer(
        finding=finding,
        columns=(("total", "Defects"), ("bugs", "Bugs"),
                 ("validation", "Validation"), ("errors", "Error msgs"),
                 ("severe", "Severity 4+")),
        rows=tuple(out),
        note="Counts only Bug / defect, Validation gap and Poor error message. "
             "Feature-gap demand is deliberately excluded: this question is "
             "about things that are broken, not things that are missing.",
    )


# --- question 9 ------------------------------------------------------------
def cross_cutting_dependencies(frame: pd.DataFrame) -> Answer:
    if "secondary_assignments" not in frame.columns:
        return Answer(finding="", empty_message="No secondary assignments recorded.")

    mentions: dict[str, set[str]] = {}
    partners: dict[str, Counter] = {}
    for record in frame.to_dict("records"):
        fid = str(record["feedback_id"])
        primary = str(record.get("primary_taxonomy_category") or "")
        # A record counts once per secondary category, however many
        # subcategories of it the classifier named. Two secondary assignments
        # in the same category are one dependency, not two.
        assignments = record.get("secondary_assignments") or []
        for secondary in {str(a["category"]) for a in assignments if a.get("category")}:
            mentions.setdefault(secondary, set()).add(fid)
            partners.setdefault(secondary, Counter())[primary] += 1

    rows = []
    for secondary, ids in mentions.items():
        linked = partners[secondary]
        rows.append((len(ids), len(linked), secondary,
                     linked.most_common(1)[0][0] if linked else "",
                     sorted(ids)))
    rows.sort(key=lambda r: (-r[0], -r[1], r[2]))

    out = [AnswerRow(
        label=secondary,
        values={
            "records": str(count),
            "linked": str(linked),
            "partner": partner or "-",
        },
        feedback_ids=ids,
    ) for count, linked, secondary, partner, ids in rows[:TOP_N]]

    finding = (f"{out[0].label} appears as a secondary dependency in "
               f"{out[0].values['records']} records, most often alongside "
               f"{out[0].values['partner']}." if out else "")
    return Answer(
        finding=finding,
        columns=(("records", "Records"), ("linked", "Linked categories"),
                 ("partner", "Most often with")),
        rows=tuple(out),
        note="A secondary assignment means the area is involved, not that it "
             "owns the problem. These counts are kept separate from primary "
             "category totals so no record is counted twice.",
        empty_message="No record in this scope carries a secondary category.",
    )


# --- question 10 -----------------------------------------------------------
def work_already_committed(frame: pd.DataFrame) -> Answer:
    committed = frame[frame["lifecycle_status"].isin(COMMITTED_STATUSES)]
    if committed.empty:
        return Answer(
            finding="",
            empty_message="No feedback in this scope is marked Planned or In progress.")

    totals = {str(name): len(_ids(group))
              for name, group in frame.groupby("primary_taxonomy_subcategory")}

    rows = []
    for name, group in committed.groupby("primary_taxonomy_subcategory"):
        ids = _ids(group)
        planned = _ids(group[group["lifecycle_status"] == "Planned"])
        progress = _ids(group[group["lifecycle_status"] == "In progress"])
        total = totals.get(str(name), len(ids))
        rows.append((len(ids), len(ids) / total if total else 0.0,
                     len(planned), len(progress), total, str(name), ids))

    rows.sort(key=lambda r: (-r[0], -r[1], r[5]))

    out = [AnswerRow(
        label=name,
        sublabel=CATEGORY_FOR_SUBCATEGORY.get(name, ""),
        values={
            "committed": str(count),
            "planned": str(planned),
            "progress": str(progress),
            "share": _pct(count, total),
        },
        feedback_ids=ids,
    ) for count, _share, planned, progress, total, name, ids in rows[:TOP_N]]

    finding = (f"{out[0].label} has the most work already committed - "
               f"{out[0].values['committed']} records planned or in progress."
               if out else "")
    return Answer(
        finding=finding,
        columns=(("committed", "Committed"), ("planned", "Planned"),
                 ("progress", "In progress"), ("share", "Share of subcategory")),
        rows=tuple(out),
        note="Lifecycle status describes the source feedback record. It does "
             "not necessarily mean that every related Product Action is fully "
             "covered by the planned work.",
    )
