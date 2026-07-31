"""Product-action membership, ranking, polarity, insights and trend.

The bug these guard against: a card read "4 open supporting records" and its
drill-down opened onto every record in the taxonomy subcategory, because the
subcategory *was* the group. Membership is now an explicit list of feedback
ids, and the count is the length of that list.

    python -m pytest tests/test_product_actions.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"


@pytest.fixture(scope="module")
def records() -> list[dict]:
    data = json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))
    return [r for r in data["records"] if r["is_relevant"]]


@pytest.fixture(scope="module")
def rel(records) -> pd.DataFrame:
    return pd.DataFrame(records)


@pytest.fixture(scope="module")
def aggregates() -> dict:
    return json.loads((PROC / "aggregates.json").read_text(encoding="utf-8"))


def _record(**overrides) -> dict:
    base = {
        "feedback_id": "id-1", "title": "t", "is_relevant": True,
        "primary_taxonomy_category": "Identity, Secrets & Security",
        "primary_taxonomy_subcategory": "Authentication & delegated execution",
        "suggested_product_action": "Support OAuth2 per-user delegated execution",
        "problem_type": "Feature gap",
        "journey_stage": "Backend & invocation setup",
        "lifecycle_status": "Open", "severity": 3, "confidence": 0.8,
        "source_system": "Port portal", "created_at": "2026-06-01T00:00:00Z",
        "needs_human_review": False, "feedback_polarity": "Negative",
        "short_summary": "Actions run under a shared identity",
        "evidence_verified": True, "evidence_excerpt": "q",
    }
    base.update(overrides)
    return base


# --- membership ------------------------------------------------------------
def test_every_action_has_a_stable_id_and_explicit_members(aggregates):
    actions = aggregates["product_actions"]
    assert actions, "expected at least one product action"
    ids = [a["product_action_id"] for a in actions]
    assert all(ids), "every action needs a stable id"
    for action in actions:
        assert action["supporting_feedback_ids"], action["product_action_id"]
        assert action["product_action_title"]


def test_count_equals_unique_open_supporting_ids(aggregates):
    """The invariant the whole fix rests on."""
    for action in aggregates["product_actions"]:
        open_ids = action["open_supporting_feedback_ids"]
        assert len(open_ids) == len(set(open_ids)), "a record counted twice"
        assert action["open_supporting_record_count"] == len(set(open_ids)), \
            action["product_action_id"]


def test_only_open_records_are_counted(records, aggregates):
    by_id = {r["feedback_id"]: r for r in records}
    for action in aggregates["product_actions"]:
        for fid in action["open_supporting_feedback_ids"]:
            assert by_id[fid]["lifecycle_status"] == "Open", (
                f"{fid} is {by_id[fid]['lifecycle_status']} but counts as open")


def test_a_record_belongs_to_only_one_action(aggregates):
    seen: dict[str, str] = {}
    for action in aggregates["product_actions"]:
        for fid in action["supporting_feedback_ids"]:
            assert fid not in seen, (
                f"{fid} is in both {seen.get(fid)} and {action['product_action_id']}")
            seen[fid] = action["product_action_id"]


def test_subcategory_records_do_not_leak_into_an_action(rel):
    """The regression test for the reported bug.

    Four records share one subcategory but ask for three different changes.
    The action holding the two matching records must open onto exactly those
    two -- not onto all four.
    """
    from src.analysis.aggregate import evidence_for_action, product_actions

    frame = pd.DataFrame([
        _record(feedback_id="a",
                suggested_product_action="Support OAuth2 per-user delegated execution"),
        _record(feedback_id="b",
                suggested_product_action="Support OAuth2 delegated per-user execution"),
        _record(feedback_id="c",
                suggested_product_action="Add configurable service accounts per action"),
        _record(feedback_id="d",
                suggested_product_action="Mask secret values in run history output"),
    ])
    actions = product_actions(frame)
    assert len(actions) == 3, "distinct requests must not merge on subcategory"

    oauth = next(a for a in actions.to_dict("records")
                 if a["open_supporting_record_count"] == 2)
    assert set(oauth["open_supporting_feedback_ids"]) == {"a", "b"}

    drill = evidence_for_action(frame, oauth["open_supporting_feedback_ids"])
    assert len(drill) == oauth["open_supporting_record_count"]
    assert {r["feedback_id"] for r in drill} == {"a", "b"}


def test_completed_records_join_the_group_but_not_the_count(rel):
    from src.analysis.aggregate import product_actions

    frame = pd.DataFrame([
        _record(feedback_id="open-1", lifecycle_status="Open"),
        _record(feedback_id="done-1", lifecycle_status="Completed"),
        _record(feedback_id="plan-1", lifecycle_status="Planned"),
        _record(feedback_id="prog-1", lifecycle_status="In progress"),
    ])
    action = product_actions(frame).to_dict("records")[0]
    assert action["open_supporting_record_count"] == 1
    assert action["open_supporting_feedback_ids"] == ["open-1"]
    # Membership still records them, so the group's history stays auditable.
    assert len(action["supporting_feedback_ids"]) == 4


# --- ranking ---------------------------------------------------------------
def _rank(frames: list[list[dict]]) -> list[str]:
    from src.analysis.aggregate import product_actions

    rows = [r for frame in frames for r in frame]
    ranked = product_actions(pd.DataFrame(rows))
    return list(ranked["product_action_title"])


def test_ranking_key_order_is_exact(aggregates):
    from src.analysis.aggregate import RANK_KEYS

    assert [k for k, *_ in RANK_KEYS] == [
        "severity_band", "open_supporting_record_count", "average_confidence",
        "source_diversity", "latest_created_sort",
    ]
    assert [e["key"] for e in aggregates["ranking"]["keys"]] == \
        [k for k, *_ in RANK_KEYS]


def test_higher_severity_band_wins_even_with_fewer_records():
    order = _rank([
        [_record(feedback_id="hi", severity=5,
                 suggested_product_action="Alpha severe single request")],
        [_record(feedback_id=f"lo{i}", severity=2,
                 suggested_product_action="Beta mild popular request")
         for i in range(5)],
    ])
    assert order[0].startswith("Alpha"), order


def test_more_open_records_wins_when_bands_match():
    order = _rank([
        [_record(feedback_id="one", severity=3,
                 suggested_product_action="Alpha lonely matching band")],
        [_record(feedback_id=f"many{i}", severity=3,
                 suggested_product_action="Beta crowded matching band")
         for i in range(3)],
    ])
    assert order[0].startswith("Beta"), order


def test_confidence_breaks_a_tie_on_count_and_band():
    order = _rank([
        [_record(feedback_id="lowc", severity=3, confidence=0.60,
                 suggested_product_action="Alpha unsure request here")],
        [_record(feedback_id="highc", severity=3, confidence=0.95,
                 suggested_product_action="Beta confident request here")],
    ])
    assert order[0].startswith("Beta"), order


def test_source_diversity_breaks_a_tie_on_confidence():
    order = _rank([
        [_record(feedback_id="s1", severity=3, confidence=0.8,
                 source_system="Port portal",
                 suggested_product_action="Alpha single source request"),
         _record(feedback_id="s2", severity=3, confidence=0.8,
                 source_system="Port portal",
                 suggested_product_action="Alpha single source request")],
        [_record(feedback_id="d1", severity=3, confidence=0.8,
                 source_system="Port portal",
                 suggested_product_action="Beta multi source request"),
         _record(feedback_id="d2", severity=3, confidence=0.8,
                 source_system="Zendesk",
                 suggested_product_action="Beta multi source request")],
    ])
    assert order[0].startswith("Beta"), order


def test_recency_breaks_a_tie_on_diversity():
    order = _rank([
        [_record(feedback_id="old", severity=3, confidence=0.8,
                 created_at="2025-01-01T00:00:00Z",
                 suggested_product_action="Alpha older identical request")],
        [_record(feedback_id="new", severity=3, confidence=0.8,
                 created_at="2026-06-01T00:00:00Z",
                 suggested_product_action="Beta newer identical request")],
    ])
    assert order[0].startswith("Beta"), order


def test_title_is_the_final_tie_breaker_so_ranking_is_deterministic():
    # Deliberately share no meaningful tokens, or clustering would correctly
    # merge them and there would be nothing left to tie-break.
    rows = [
        _record(feedback_id="a",
                suggested_product_action="Zulu rewrite outbound payload mapping"),
        _record(feedback_id="b",
                suggested_product_action="Alpha cancel long running executions"),
    ]
    from src.analysis.aggregate import product_actions

    first = list(product_actions(pd.DataFrame(rows))["product_action_title"])
    second = list(product_actions(pd.DataFrame(rows[::-1]))["product_action_title"])
    assert first == second, "ranking must not depend on row order"
    assert first[0].startswith("Alpha")


def test_completed_records_do_not_move_any_ranking_field():
    from src.analysis.aggregate import product_actions

    base = [_record(feedback_id="o1", severity=2, confidence=0.7)]
    noisy = base + [_record(feedback_id="c1", severity=5, confidence=0.99,
                            lifecycle_status="Completed",
                            source_system="Zendesk",
                            created_at="2026-07-30T00:00:00Z")]
    clean = product_actions(pd.DataFrame(base)).to_dict("records")[0]
    with_completed = product_actions(pd.DataFrame(noisy)).to_dict("records")[0]
    for field in ("severity_band", "open_supporting_record_count",
                  "average_confidence", "source_diversity", "latest_created_at"):
        assert clean[field] == with_completed[field], field


def test_typical_severity_is_the_median_not_the_maximum():
    from src.analysis.aggregate import product_actions

    rows = [_record(feedback_id=f"m{i}", severity=s)
            for i, s in enumerate([1, 1, 1, 1, 5])]
    action = product_actions(pd.DataFrame(rows)).to_dict("records")[0]
    assert action["typical_severity"] == 1, "one severe record must not dominate"
    assert action["max_severity"] == 5


# --- polarity --------------------------------------------------------------
def test_polarity_values_are_closed():
    from pydantic import ValidationError

    from src.models.schema import FeedbackClassification

    valid = dict(
        is_relevant=True, relevance_reason="Concerns action validation rules.",
        primary_taxonomy_category="Validation & Rules",
        primary_taxonomy_subcategory="Input & cross-field validation",
        problem_type="Feature gap",
        journey_stage="Validation, dependencies & conditional logic",
        persona="Action builder", severity=3,
        short_summary="Validation cannot compare two fields.",
        user_need="Express rules across fields.",
        suggested_product_action="Support cross-field validation rules.",
        confidence=0.8, evidence_excerpt="cannot compare two fields",
    )
    for good in ("Negative", "Positive", "Neutral"):
        assert FeedbackClassification(
            **dict(valid, feedback_polarity=good)).feedback_polarity == good
    for bad in ("negative", "Angry", "Mixed", ""):
        with pytest.raises(ValidationError):
            FeedbackClassification(**dict(valid, feedback_polarity=bad))


def test_polarity_is_independent_of_lifecycle_status(records):
    """A completed request may still record the pain that prompted it."""
    if not any(r.get("feedback_polarity") for r in records):
        pytest.skip("records not yet reclassified with polarity")
    completed = [r for r in records if r["lifecycle_status"] == "Completed"]
    if not completed:
        pytest.skip("no completed records in this dataset")
    polarities = {r.get("feedback_polarity") for r in completed}
    assert polarities - {"Positive"}, (
        "every completed record was called Positive, which means polarity was "
        "read off the status rather than the text")


# --- insights --------------------------------------------------------------
def test_insight_counts_only_negative_records():
    from src.analysis.aggregate import negative_insight

    frame = pd.DataFrame([
        _record(feedback_id="n1", feedback_polarity="Negative"),
        _record(feedback_id="n2", feedback_polarity="Negative"),
        _record(feedback_id="p1", feedback_polarity="Positive"),
        _record(feedback_id="u1", feedback_polarity="Neutral"),
    ])
    card = negative_insight(frame, "journey_stage")
    assert card["negative_feedback_count"] == 2
    assert set(card["supporting_feedback_ids"]) == {"n1", "n2"}


def test_insight_respects_an_explicit_selection():
    from src.analysis.aggregate import negative_insight

    frame = pd.DataFrame(
        [_record(feedback_id=f"b{i}", journey_stage="Backend & invocation setup")
         for i in range(4)]
        + [_record(feedback_id="f1", journey_stage="Form & input configuration")]
    )
    # Unfiltered, the busiest stage wins.
    assert negative_insight(frame, "journey_stage")["group_name"] == \
        "Backend & invocation setup"
    # Selected, the card must follow the filter beside it.
    picked = negative_insight(frame, "journey_stage",
                              selected=["Form & input configuration"])
    assert picked["group_name"] == "Form & input configuration"
    assert picked["negative_feedback_count"] == 1


def test_insight_shows_at_most_three_grounded_examples():
    from src.analysis.aggregate import MAX_INSIGHT_EXAMPLES, negative_insight

    frame = pd.DataFrame([
        _record(feedback_id=f"x{i}", severity=5 - (i % 4),
                short_summary=f"Distinct problem number {i} blocks the user")
        for i in range(9)
    ])
    card = negative_insight(frame, "journey_stage")
    assert len(card["examples"]) <= MAX_INSIGHT_EXAMPLES
    ids = {r["feedback_id"] for r in frame.to_dict("records")}
    for example in card["examples"]:
        assert example["supporting_feedback_ids"], "examples must stay traceable"
        assert set(example["supporting_feedback_ids"]) <= ids


def test_insight_empty_state_rather_than_a_zero_winner():
    from src.analysis.aggregate import negative_insight

    frame = pd.DataFrame([_record(feedback_id="p", feedback_polarity="Positive")])
    card = negative_insight(frame, "subcategory")
    assert card["negative_feedback_count"] == 0
    assert card["group_name"] == ""


def test_subcategory_insight_uses_primary_assignments_only():
    from src.analysis.aggregate import negative_insight

    frame = pd.DataFrame([
        _record(feedback_id="p1",
                primary_taxonomy_subcategory="Authentication & delegated execution"),
        _record(feedback_id="p2",
                primary_taxonomy_subcategory="Service accounts & execution identity"),
    ])
    card = negative_insight(frame, "subcategory")
    # Two different primaries, one record each -- the tie resolves
    # alphabetically and the count is 1, never 2 from a secondary.
    assert card["negative_feedback_count"] == 1


# --- trend -----------------------------------------------------------------
def test_trend_uses_created_at_and_monday_weeks():
    from src.analysis.aggregate import TREND_WEEKS, negative_trend

    frame = pd.DataFrame([
        _record(feedback_id="t1", created_at="2026-06-03T00:00:00Z"),   # Wed
        _record(feedback_id="t2", created_at="2026-06-05T00:00:00Z"),   # Fri
    ])
    trend = negative_trend(frame)
    assert len(trend["weeks"]) == TREND_WEEKS
    for label in trend["weeks"]:
        assert pd.Timestamp(label).dayofweek == 0, "weeks must start on Monday"
    # Both records fall in the same Monday week and must be counted once each.
    assert sum(sum(s["points"]) for s in trend["series"]) == 2


def test_trend_counts_only_negative_and_never_twice():
    from src.analysis.aggregate import negative_trend

    frame = pd.DataFrame([
        _record(feedback_id="n1", created_at="2026-06-03T00:00:00Z"),
        _record(feedback_id="p1", created_at="2026-06-03T00:00:00Z",
                feedback_polarity="Positive"),
    ])
    trend = negative_trend(frame)
    assert sum(sum(s["points"]) for s in trend["series"]) == 1


def test_trend_keeps_stages_in_chronological_order():
    from src.models.taxonomy import STAGE_NAMES

    aggregates = json.loads((PROC / "aggregates.json").read_text(encoding="utf-8"))
    stages = [s["stage"] for s in aggregates["negative_trend"]["series"]]
    order = [STAGE_NAMES.index(s) for s in stages]
    assert order == sorted(order), "legend must follow the journey, not volume"


def test_trend_fills_missing_weeks_with_zero():
    from src.analysis.aggregate import TREND_WEEKS, negative_trend

    frame = pd.DataFrame([_record(feedback_id="t1",
                                  created_at="2026-06-03T00:00:00Z")])
    trend = negative_trend(frame)
    for entry in trend["series"]:
        assert len(entry["points"]) == TREND_WEEKS
        assert entry["points"].count(0) == TREND_WEEKS - 1


# --- duplicate focus lines --------------------------------------------------
def _card(name: str, ranking: list[str], focus: str) -> dict:
    return {"group_name": name, "problem_type_ranking": ranking,
            "recommended_focus": focus}


def test_duplicate_focus_is_resolved_on_the_subcategory_first():
    """Two identical sentences side by side read as a failed render.

    The subcategory card is re-pointed at the next problem type it actually
    contains, so the difference is still something the records show.
    """
    from src.analysis.aggregate import resolve_focus_collision

    shared = "Mostly feature gap, then configuration complexity."
    journey = _card("Permissions & approvals",
                    ["feature gap", "configuration complexity"], shared)
    subcategory = _card("RBAC & dynamic permissions",
                        ["feature gap", "configuration complexity",
                         "security or privacy concern"], shared)

    resolve_focus_collision(journey, subcategory)
    assert journey["recommended_focus"] == shared, "the journey card is left alone"
    assert subcategory["recommended_focus"] != shared
    assert "security or privacy concern" in subcategory["recommended_focus"]


def test_duplicate_focus_falls_back_to_the_journey_card():
    """Only when the subcategory has nothing further to say."""
    from src.analysis.aggregate import resolve_focus_collision

    shared = "Mostly feature gap, then configuration complexity."
    journey = _card("Permissions & approvals",
                    ["feature gap", "configuration complexity",
                     "usability friction"], shared)
    subcategory = _card("RBAC & dynamic permissions",
                        ["feature gap", "configuration complexity"], shared)

    resolve_focus_collision(journey, subcategory)
    assert subcategory["recommended_focus"] == shared
    assert "usability friction" in journey["recommended_focus"]


def test_duplicate_focus_is_kept_when_neither_card_has_more():
    """Repeating a true sentence beats inventing a distinguishing one."""
    from src.analysis.aggregate import resolve_focus_collision

    shared = "Mostly feature gap, then configuration complexity."
    ranking = ["feature gap", "configuration complexity"]
    journey = _card("Permissions & approvals", list(ranking), shared)
    subcategory = _card("RBAC & dynamic permissions", list(ranking), shared)

    resolve_focus_collision(journey, subcategory)
    assert journey["recommended_focus"] == shared
    assert subcategory["recommended_focus"] == shared


def test_distinct_focus_lines_are_left_untouched():
    from src.analysis.aggregate import resolve_focus_collision

    journey = _card("A", ["feature gap"], "Mostly feature gap.")
    subcategory = _card("B", ["bug / defect"], "Mostly bug / defect.")
    resolve_focus_collision(journey, subcategory)
    assert journey["recommended_focus"] == "Mostly feature gap."
    assert subcategory["recommended_focus"] == "Mostly bug / defect."


def test_real_cards_do_not_repeat_the_same_focus(aggregates):
    journey = aggregates["insights"]["journey_stage"]["recommended_focus"]
    subcategory = aggregates["insights"]["subcategory"]["recommended_focus"]
    if journey and subcategory:
        ranking = aggregates["insights"]["subcategory"]["problem_type_ranking"]
        if len(ranking) > 2:
            assert journey != subcategory, (
                "the subcategory had a third problem type available")


# --- example wording --------------------------------------------------------
def test_examples_are_never_cut_mid_sentence():
    """Counting off N words ended sentences mid-thought behind an ellipsis.

    Condensation now cuts at a clause boundary or not at all, so nothing on a
    card trails off.
    """
    from src.analysis.aggregate import _example_text

    long_summary = _record(short_summary=(
        "Organizations with more than 1,000 users cannot get a complete list "
        "of eligible approvers because the dynamic approval policy caps query "
        "results at 1,000 entities"))
    text = _example_text(long_summary)
    assert "…" not in text and "..." not in text
    assert text == ("Organizations with more than 1,000 users cannot get a "
                    "complete list of eligible approvers")


def test_a_parenthetical_comma_is_not_a_cut_point():
    """Cutting at the aside strands the sentence before it says anything."""
    from src.analysis.aggregate import _example_text

    text = _example_text(_record(short_summary=(
        "Admins cannot restrict which channels, such as MCP versus the UI, "
        "are allowed to trigger a given action, leaving actions exposed")))
    assert text.startswith("Admins cannot restrict which channels, such as MCP")
    assert "leaving" not in text, "the trailing explanation should still go"


def test_a_short_summary_is_left_whole():
    from src.analysis.aggregate import _example_text

    text = _example_text(_record(short_summary="Runs cannot be cancelled"))
    assert text == "Runs cannot be cancelled"


def test_no_example_anywhere_trails_off(aggregates):
    for key in ("journey_stage", "subcategory"):
        for example in aggregates["insights"][key]["examples"]:
            assert "…" not in example["text"], example["text"]
            assert not example["text"].endswith(","), example["text"]


def test_insight_cards_are_equal_height_by_construction():
    """Uneven cards read as one having failed to load."""
    from src.ui.theme import CSS

    marker = CSS.index(".afi-insight-grid {")
    rule = CSS[marker:CSS.index("}", marker)]
    assert "align-items: stretch" in rule, "cards must stretch to match"
    assert "align-items: start" not in rule
    assert ".afi-insight-examples { margin-top: auto" in CSS.replace("\n", " ") \
        or "margin-top: auto" in CSS, "the list must absorb the slack"
