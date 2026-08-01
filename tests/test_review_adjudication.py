"""The review flag means one thing: a reviewer read the record and was unsure.

These guard the property that made the flag worth rebuilding. Before, it was a
boolean set by three unrelated causes, so "Needs human review" could sit beside
"Confidence 0.85" and read as a contradiction. The tests below fail if anything
-- a reconciliation re-run, a reclassification, a hand edit -- puts a flag on a
record for any reason other than a reviewer's verdict.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.analysis import review

ANALYZED = Path(__file__).resolve().parents[1] / "data" / "processed" / "analyzed.json"


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return json.loads(ANALYZED.read_text(encoding="utf-8"))["records"]


@pytest.fixture(scope="module")
def verdicts() -> dict[str, dict]:
    return review.load_adjudications()


def test_every_flag_traces_to_a_verdict_below_threshold(records, verdicts):
    """No record is flagged unless a reviewer judged it below the threshold."""
    for record in records:
        if not record.get(review.FLAG_FIELD):
            continue
        fid = str(record["feedback_id"])
        verdict = verdicts.get(fid)
        assert verdict is not None, f"{fid} is flagged with no reviewer verdict"
        assert verdict["confidence"] < review.THRESHOLD, (
            f"{fid} is flagged but the reviewer scored it "
            f"{verdict['confidence']}, at or above {review.THRESHOLD}")


def test_every_verdict_at_or_above_threshold_is_cleared(records, verdicts):
    """The converse: being sure clears the flag, it does not merely allow it."""
    by_id = {str(r["feedback_id"]): r for r in records}
    for fid, verdict in verdicts.items():
        record = by_id.get(fid)
        if record is None:
            continue  # a verdict for a record a later run dropped
        expected = verdict["confidence"] < review.THRESHOLD
        assert bool(record.get(review.FLAG_FIELD)) is expected, (
            f"{fid}: reviewer scored {verdict['confidence']} but the flag is "
            f"{record.get(review.FLAG_FIELD)}")


def test_a_flagged_record_says_why(records):
    """The badge names the reason, so a flag with no reason cannot ship."""
    for record in records:
        if record.get(review.FLAG_FIELD):
            reasons = record.get(review.REASONS_FIELD) or []
            assert reasons and all(str(r).strip() for r in reasons), (
                f"{record['feedback_id']} is flagged with no reason to show")


def test_an_unflagged_record_carries_no_stray_reason(records):
    """A cleared record must not keep the wording that explained its flag."""
    for record in records:
        if not record.get(review.FLAG_FIELD):
            assert not (record.get(review.REASONS_FIELD) or []), (
                f"{record['feedback_id']} is not flagged but still has reasons")


def test_confidence_alone_never_sets_the_flag(records):
    """The bug that started this: the classifier's own score does not decide.

    A low-confidence record the reviewer was sure about is cleared, and that is
    the point -- so at least one such record must exist, or the test is passing
    on an empty set.
    """
    cleared_despite_low_confidence = [
        r for r in records
        if not r.get(review.FLAG_FIELD) and float(r.get("confidence") or 1.0) < 0.7
    ]
    assert cleared_despite_low_confidence, (
        "no low-confidence record was cleared -- the flag may have silently "
        "gone back to tracking classifier confidence")


def test_apply_is_the_only_thing_that_sets_the_flag():
    """Applied to a record flagged by something else, the flag is recomputed."""
    stale = [
        {"feedback_id": "a", "needs_human_review": True,
         "review_reasons": ["low classifier confidence"]},
        {"feedback_id": "b", "needs_human_review": False},
    ]
    counts = review.apply_adjudications(stale, {
        "b": {"confidence": 0.4, "note": "genuinely ambiguous"},
    })

    assert stale[0][review.FLAG_FIELD] is False, "a flag with no verdict survived"
    assert stale[0][review.REASONS_FIELD] == []
    assert stale[1][review.FLAG_FIELD] is True, "a verdict below threshold did not flag"
    assert stale[1][review.REASONS_FIELD] == ["genuinely ambiguous"]
    assert counts == {"flagged": 1, "cleared": 0, "unjudged_cleared": 1}


def _card(**record) -> str:
    from src.ui.render import render_feedback_cards
    base = {"feedback_id": "x", "source_system": "Port portal",
            "lifecycle_status": "In progress", "created_at": "2026-07-21",
            "confidence": 0.55, "persona": "Action builder", "title": "t",
            "suggested_product_action": "a", "evidence_excerpt": "q",
            "source_url": "https://example.invalid/1", "severity": 4,
            "primary_taxonomy_category": "Orchestration",
            "primary_taxonomy_subcategory": "Workflow approvals, error handling "
                                            "& recovery",
            "problem_type": "Feature gap", "journey_stage": "Backend & "
                                                            "invocation setup"}
    return render_feedback_cards([{**base, **record}])


def test_the_card_names_whose_confidence_it_shows():
    """The model's score and the reviewer's are different judgements.

    Showing one unlabelled beside the other's verdict is what made a card read
    as self-contradictory in both directions: 0.85 next to a flag, and 0.55
    next to no flag.
    """
    html = _card(confidence=0.55, review_confidence=0.92,
                 needs_human_review=False, review_reasons=[])
    assert "Model confidence 0.55" in html
    assert "Reviewed - classification confirmed" in html
    assert "Needs human review" not in html


def test_a_record_nobody_reviewed_claims_nothing():
    """NaN is truthy and formats as "nan"; the card must not report it."""
    html = _card(review_confidence=float("nan"), needs_human_review=False)
    assert "Reviewed" not in html
    assert "nan" not in html.lower().replace("canonical", "")

    missing = _card(needs_human_review=False)
    assert "Reviewed" not in missing


def test_a_flagged_card_shows_the_reason_not_the_confirmation():
    html = _card(confidence=0.85, review_confidence=0.45,
                 needs_human_review=True, review_reasons=["genuinely ambiguous"])
    assert "Needs human review: genuinely ambiguous" in html
    assert "Reviewed - classification confirmed" not in html


def test_a_missing_verdict_file_is_not_a_crash(tmp_path):
    """The dashboard must still start on a checkout without the file."""
    assert review.load_adjudications(tmp_path / "nope.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert review.load_adjudications(bad) == {}
