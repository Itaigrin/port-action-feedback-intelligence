"""The review flag is exactly one rule: confidence < THRESHOLD.

Before, "needs_human_review" was a boolean set by three unrelated causes --
classifier confidence, a workbook disagreement, a migration marker -- so a
card could read "Confidence 0.85" beside "Needs human review" and look like
the app contradicting itself. 59 previously flagged records were read by a
reviewer, who gave each one a confidence of their own; for those records
`confidence` in the data now *is* the reviewer's number, and the flag is
just a threshold on whichever number -- reviewer's or classifier's -- sits in
that one field. The tests below fail if anything reintroduces a second cause.
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


def test_the_flag_is_exactly_confidence_below_threshold(records):
    """No exceptions: not scope, not a workbook marker, not a disagreement."""
    for record in records:
        expected = float(record.get(review.CONFIDENCE_FIELD) or 1.0) < review.THRESHOLD
        assert bool(record.get(review.FLAG_FIELD)) is expected, (
            f"{record['feedback_id']}: confidence "
            f"{record.get(review.CONFIDENCE_FIELD)} but flag is "
            f"{record.get(review.FLAG_FIELD)}")


def test_a_reviewed_records_confidence_is_the_reviewers_own_number(records, verdicts):
    """For the 59 (60, with the one the safety net caught), the field is mine."""
    by_id = {str(r["feedback_id"]): r for r in records}
    for fid, verdict in verdicts.items():
        record = by_id.get(fid)
        if record is None:
            continue  # a verdict for a record a later run dropped
        assert record[review.CONFIDENCE_FIELD] == pytest.approx(verdict["confidence"]), (
            f"{fid}: reviewer scored {verdict['confidence']} but the record's "
            f"confidence is {record[review.CONFIDENCE_FIELD]}")
        assert record.get(review.REVIEWED_FIELD) is True


def test_an_unreviewed_record_keeps_its_own_field_and_flag(records, verdicts):
    """The instruction was explicit: leave every non-reviewed record as is."""
    unreviewed = [r for r in records
                 if str(r["feedback_id"]) not in verdicts]
    assert unreviewed, "no unreviewed records in this dataset -- fixture is stale"
    for record in unreviewed:
        assert record.get(review.REVIEWED_FIELD) is False


def test_no_stray_reasons_or_review_confidence_field(records):
    """The two-field, reasoned design was replaced, not layered on top of."""
    for record in records:
        assert "review_reasons" not in record, record["feedback_id"]
        assert "review_confidence" not in record, record["feedback_id"]


def test_apply_computes_the_flag_from_the_final_confidence():
    """Applied to a record flagged by something else, the flag is recomputed
    from whichever confidence ends up on the record -- reviewer's if there is
    a verdict, the record's own otherwise.
    """
    stale = [
        {"feedback_id": "a", "confidence": 0.95, "needs_human_review": True},
        {"feedback_id": "b", "confidence": 0.95, "needs_human_review": False},
        {"feedback_id": "c", "confidence": 0.4, "needs_human_review": False},
    ]
    counts = review.apply_adjudications(stale, {"b": {"confidence": 0.4}})

    assert stale[0][review.FLAG_FIELD] is False, "high confidence but still flagged"
    assert stale[0][review.REVIEWED_FIELD] is False

    assert stale[1][review.CONFIDENCE_FIELD] == 0.4, "reviewer's number wasn't substituted"
    assert stale[1][review.FLAG_FIELD] is True
    assert stale[1][review.REVIEWED_FIELD] is True

    assert stale[2][review.CONFIDENCE_FIELD] == 0.4, "untouched record's confidence changed"
    assert stale[2][review.FLAG_FIELD] is True

    assert counts == {"reviewed": 1, "flagged": 2}


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


def test_the_card_shows_one_confidence_and_a_plain_badge():
    """The badge no longer carries a reason -- the confidence chip already
    tells the reader whose number it is showing.
    """
    html = _card(confidence=0.92, human_reviewed=True, needs_human_review=False)
    assert "Model confidence 0.92" in html
    assert "Reviewed - classification confirmed" in html
    assert "Needs human review" not in html


def test_a_flagged_card_shows_the_plain_badge_only():
    html = _card(confidence=0.45, human_reviewed=True, needs_human_review=True)
    assert "Needs human review</span>" in html, "badge must not carry a reason"
    assert "Reviewed - classification confirmed" not in html


def test_an_unreviewed_cleared_card_shows_no_confirmation():
    """Nobody looked at this record; the card must not claim otherwise."""
    html = _card(confidence=0.9, human_reviewed=False, needs_human_review=False)
    assert "Reviewed" not in html
    assert "Needs human review" not in html


def test_a_missing_verdict_file_is_not_a_crash(tmp_path):
    """The dashboard must still start on a checkout without the file."""
    assert review.load_adjudications(tmp_path / "nope.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert review.load_adjudications(bad) == {}
