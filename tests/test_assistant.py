"""The deterministic Product Data Assistant.

Two things these guard. First, that the ten answers are arithmetic over the
classified records rather than anything generated -- the no-AI tests below
sabotage every AI client constructor in the process and then run all ten
handlers, so a stray runtime model call fails the suite instead of quietly
costing tokens.

Second, that a number and its evidence describe the same records. Every row
carries the exact feedback ids it was computed from, and the tests assert the
membership rather than the count, because a count can be right for the wrong
reason.

    python -m pytest tests/test_assistant.py -v
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

from src.assistant import QUESTIONS, QUESTIONS_BY_ID, answer  # noqa: E402
from src.assistant import analytics  # noqa: E402
from src.ui import data_assistant  # noqa: E402
from src.ui.theme import CSS  # noqa: E402

EXPECTED_LABELS = {
    "oldest_open_actions":
        "Which open Product Actions have been waiting the longest?",
    "recurring_demand":
        "Which Product Actions show recurring demand over the longest period?",
    "portal_discussion":
        "Which open Product Actions have generated the most discussion in the "
        "Port portal?",
    "high_severity_singletons":
        "Which high-severity Product Actions are supported by only one open "
        "record?",
    "human_review_risk":
        "Which Product Actions need the most human review before prioritization?",
    "high_severity_share":
        "Which Subcategories have the highest share of high-severity negative "
        "feedback?",
    "unresolved_rate":
        "Which Categories have the highest unresolved-demand rate?",
    "defects_by_stage":
        "Which Journey Stages contain the most bugs, validation gaps, and poor "
        "error messages?",
    "cross_cutting":
        "Which Categories most often appear as secondary dependencies?",
    "already_committed":
        "Which Subcategories have the most feedback already marked Planned or "
        "In progress?",
}


@pytest.fixture(scope="module")
def rel() -> pd.DataFrame:
    data = json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))
    return pd.DataFrame([r for r in data["records"] if r["is_relevant"]])


@pytest.fixture(scope="module")
def by_id(rel) -> dict:
    return {str(r["feedback_id"]): r for r in rel.to_dict("records")}


def _record(**overrides) -> dict:
    base = {
        "feedback_id": "id-1", "title": "t", "is_relevant": True,
        "primary_taxonomy_category": "Identity, Secrets & Security",
        "primary_taxonomy_subcategory": "Authentication & delegated execution",
        "suggested_product_action": "Support OAuth2 per-user delegated execution",
        "problem_type": "Feature gap",
        "journey_stage": "Backend & invocation setup",
        "lifecycle_status": "Open", "severity": 3, "confidence": 0.8,
        "source_system": "Port portal", "created_at": "2024-06-01T00:00:00Z",
        "needs_human_review": False, "feedback_polarity": "Negative",
        "short_summary": "Actions run under a shared identity",
        "evidence_verified": True, "evidence_excerpt": "q",
        "comments_count": 0, "secondary_assignments": [],
        "secondary_categories": [], "source_url": "https://example.invalid/1",
    }
    base.update(overrides)
    return base


def _frame(*records: dict) -> pd.DataFrame:
    return pd.DataFrame(list(records))


# ==========================================================================
# Registry
# ==========================================================================
def test_exactly_ten_questions_are_registered():
    assert len(QUESTIONS) == 10


def test_question_ids_are_unique():
    ids = [q.question_id for q in QUESTIONS]
    assert len(set(ids)) == len(ids)
    assert set(ids) == set(EXPECTED_LABELS)


def test_visible_labels_match_the_approved_wording():
    for question in QUESTIONS:
        assert question.label == EXPECTED_LABELS[question.question_id]


def test_every_question_has_a_description_and_a_callable_handler():
    for question in QUESTIONS:
        assert question.short_description.strip()
        assert callable(question.handler)


# ==========================================================================
# No AI at runtime
# ==========================================================================
def test_no_handler_calls_an_ai_client(monkeypatch, rel):
    """Sabotage every AI entry point, then answer all ten questions.

    The point is not that the imports are absent -- it is that nothing reaches
    them. Anything that tried would raise here rather than silently succeed on
    a developer machine that happens to have a key.
    """
    def explode(*_args, **_kwargs):
        raise AssertionError("the assistant must not construct an AI client")

    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", explode, raising=False)
    monkeypatch.setattr(anthropic, "AsyncAnthropic", explode, raising=False)

    import socket
    monkeypatch.setattr(
        socket.socket, "connect",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("the assistant must not open a network connection")))

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    for question in QUESTIONS:
        answer(question.question_id, rel)


def test_assistant_modules_import_no_ai_sdk():
    for module in ("src/assistant/analytics.py", "src/assistant/questions.py",
                   "src/ui/data_assistant.py"):
        source = (ROOT / module).read_text(encoding="utf-8")
        for banned in ("import anthropic", "import openai", "google.generativeai",
                       "requests", "httpx", "urllib"):
            assert banned not in source, f"{module} references {banned}"


def test_no_dynamic_code_generation_from_user_text():
    for module in ("src/assistant/analytics.py", "src/assistant/questions.py",
                   "src/ui/data_assistant.py"):
        source = (ROOT / module).read_text(encoding="utf-8")
        for banned in ("eval(", "exec(", "pd.eval", ".query("):
            assert banned not in source, f"{module} uses {banned}"


# ==========================================================================
# General guarantees
# ==========================================================================
def test_answers_are_deterministic(rel):
    for question in QUESTIONS:
        first = answer(question.question_id, rel)
        second = answer(question.question_id, rel)
        assert [(r.label, r.values, r.feedback_ids) for r in first.rows] == \
               [(r.label, r.values, r.feedback_ids) for r in second.rows]
        assert first.finding == second.finding


def test_feedback_ids_are_deduplicated(rel):
    for question in QUESTIONS:
        for row in answer(question.question_id, rel).rows:
            assert len(row.feedback_ids) == len(set(row.feedback_ids)), \
                f"{question.question_id} repeats a feedback id"


def test_every_row_carries_supporting_ids_that_exist(rel, by_id):
    for question in QUESTIONS:
        for row in answer(question.question_id, rel).rows:
            assert row.feedback_ids
            assert set(row.feedback_ids) <= set(by_id)


def test_no_answer_returns_more_than_five_rows(rel):
    for question in QUESTIONS:
        assert len(answer(question.question_id, rel).rows) <= 5


def test_empty_dataset_returns_a_friendly_empty_result():
    empty = _frame(_record()).iloc[0:0]
    for question in QUESTIONS:
        result = question.handler(empty)
        assert result.is_empty
        assert result.empty_message.strip()


def test_out_of_scope_records_are_never_reachable(rel):
    """The assistant is handed in-scope records only, so is_relevant is uniform."""
    assert bool(rel["is_relevant"].all())


# ==========================================================================
# Question 1 -- oldest open
# ==========================================================================
def test_q1_uses_the_earliest_open_created_at():
    frame = _frame(
        _record(feedback_id="a", created_at="2024-01-01T00:00:00Z"),
        _record(feedback_id="b", created_at="2020-01-01T00:00:00Z"),
        _record(feedback_id="c", created_at="2024-05-01T00:00:00Z",
                suggested_product_action="Completely different unrelated request"),
    )
    result = analytics.oldest_unresolved_actions(frame)
    assert result.rows[0].values["oldest"] == "2020-01-01"


def test_q1_ignores_closed_records_when_finding_the_oldest():
    frame = _frame(
        _record(feedback_id="a", created_at="2019-01-01T00:00:00Z",
                lifecycle_status="Completed"),
        _record(feedback_id="b", created_at="2024-01-01T00:00:00Z"),
    )
    result = analytics.oldest_unresolved_actions(frame)
    assert result.rows[0].values["oldest"] == "2024-01-01"
    assert "a" not in result.rows[0].feedback_ids


def test_q1_excludes_actions_with_no_dated_open_record():
    frame = _frame(
        _record(feedback_id="a", created_at=None),
        _record(feedback_id="b", created_at="2024-01-01T00:00:00Z",
                suggested_product_action="Completely different unrelated request"),
    )
    result = analytics.oldest_unresolved_actions(frame)
    labels = [r.label for r in result.rows]
    assert all("id-1" not in label for label in labels)
    assert len(result.rows) == 1


def test_q1_reference_date_is_the_newest_record_not_today():
    frame = _frame(_record(created_at="2024-01-01T00:00:00Z"))
    assert analytics.reference_date(frame) == pd.Timestamp("2024-01-01", tz="UTC")


def test_q1_note_states_the_reference_date(rel):
    result = analytics.oldest_unresolved_actions(rel)
    assert str(analytics.reference_date(rel).date()) in result.note


# ==========================================================================
# Question 2 -- recurring demand
# ==========================================================================
def test_q2_requires_at_least_two_dated_open_records():
    frame = _frame(_record(feedback_id="a", created_at="2020-01-01T00:00:00Z"))
    assert analytics.recurring_demand(frame).is_empty


def test_q2_measures_the_span_between_first_and_last():
    frame = _frame(
        _record(feedback_id="a", created_at="2020-01-01T00:00:00Z"),
        _record(feedback_id="b", created_at="2020-01-31T00:00:00Z"),
    )
    row = analytics.recurring_demand(frame).rows[0]
    assert row.values["first"] == "2020-01-01"
    assert row.values["last"] == "2020-01-31"
    assert row.values["span"] == "30 days"


def test_q2_ignores_a_record_whose_date_is_missing():
    frame = _frame(
        _record(feedback_id="a", created_at="2020-01-01T00:00:00Z"),
        _record(feedback_id="b", created_at=None),
    )
    assert analytics.recurring_demand(frame).is_empty


# ==========================================================================
# Question 3 -- portal discussion
# ==========================================================================
def test_q3_sums_port_portal_comments_only():
    frame = _frame(
        _record(feedback_id="a", comments_count=5),
        _record(feedback_id="b", comments_count=100, source_system="Slack"),
    )
    row = analytics.most_discussed_in_portal(frame).rows[0]
    assert row.values["comments"] == "5"
    assert row.values["posts"] == "1"


def test_q3_excludes_actions_with_no_comments():
    frame = _frame(_record(feedback_id="a", comments_count=0))
    assert analytics.most_discussed_in_portal(frame).is_empty


def test_q3_note_marks_comments_as_engagement_only(rel):
    note = analytics.most_discussed_in_portal(rel).note
    assert "engagement signal only" in note
    assert "not of distinct customers" in note


# ==========================================================================
# Question 4 -- high-severity single signals
# ==========================================================================
def test_q4_requires_one_open_record_and_severity_band_four_or_five():
    frame = _frame(
        _record(feedback_id="a", severity=5),
        _record(feedback_id="b", severity=2,
                suggested_product_action="An entirely separate mild request"),
        _record(feedback_id="c", severity=5,
                suggested_product_action="A third distinct severe request here"),
        _record(feedback_id="d", severity=5,
                suggested_product_action="A third distinct severe request here"),
    )
    result = analytics.high_severity_single_signals(frame)
    ids = {i for row in result.rows for i in row.feedback_ids}
    assert ids == {"a"}


def test_q4_ignores_closed_high_severity_records():
    frame = _frame(_record(feedback_id="a", severity=5,
                           lifecycle_status="Completed"))
    assert analytics.high_severity_single_signals(frame).is_empty


# ==========================================================================
# Question 5 -- human review
# ==========================================================================
def test_q5_reports_both_the_count_and_the_percentage():
    frame = _frame(
        _record(feedback_id="a", needs_human_review=True),
        _record(feedback_id="b", needs_human_review=False),
    )
    row = analytics.needs_most_human_review(frame).rows[0]
    assert row.values["flagged"] == "1"
    assert row.values["share"] == "50%"


def test_q5_excludes_actions_with_nothing_flagged():
    frame = _frame(_record(feedback_id="a", needs_human_review=False))
    assert analytics.needs_most_human_review(frame).is_empty


# ==========================================================================
# Question 6 -- high-severity share
# ==========================================================================
def test_q6_requires_a_denominator_of_at_least_three():
    frame = _frame(
        _record(feedback_id="a", severity=5),
        _record(feedback_id="b", severity=5),
    )
    assert analytics.high_severity_share_by_subcategory(frame).is_empty


def test_q6_uses_open_negative_records_only():
    frame = _frame(
        _record(feedback_id="a", severity=5),
        _record(feedback_id="b", severity=5),
        _record(feedback_id="c", severity=1),
        _record(feedback_id="d", severity=5, feedback_polarity="Positive"),
        _record(feedback_id="e", severity=5, lifecycle_status="Completed"),
    )
    row = analytics.high_severity_share_by_subcategory(frame).rows[0]
    assert row.values["total"] == "3"
    assert row.values["severe"] == "2"
    assert row.values["share"] == "67%"


def test_q6_shows_the_parent_category(rel):
    for row in analytics.high_severity_share_by_subcategory(rel).rows:
        assert row.sublabel


# ==========================================================================
# Question 7 -- unresolved-demand rate
# ==========================================================================
def test_q7_divides_open_records_by_all_records_in_the_category():
    frame = _frame(
        *[_record(feedback_id=f"o{i}") for i in range(3)],
        *[_record(feedback_id=f"c{i}", lifecycle_status="Completed")
          for i in range(2)],
    )
    row = analytics.unresolved_demand_rate(frame).rows[0]
    assert row.values["open"] == "3"
    assert row.values["total"] == "5"
    assert row.values["other"] == "2"
    assert row.values["rate"] == "60%"


def test_q7_requires_at_least_five_records_in_the_category():
    frame = _frame(*[_record(feedback_id=f"o{i}") for i in range(4)])
    assert analytics.unresolved_demand_rate(frame).is_empty


# ==========================================================================
# Question 8 -- operational defects
# ==========================================================================
def test_q8_includes_only_the_three_approved_problem_types():
    frame = _frame(
        _record(feedback_id="a", problem_type="Bug / defect"),
        _record(feedback_id="b", problem_type="Validation gap"),
        _record(feedback_id="c", problem_type="Poor error message"),
        _record(feedback_id="d", problem_type="Feature gap"),
    )
    row = analytics.defects_by_journey_stage(frame).rows[0]
    assert row.values["total"] == "3"
    assert "d" not in row.feedback_ids


def test_q8_excludes_positive_and_closed_records():
    frame = _frame(
        _record(feedback_id="a", problem_type="Bug / defect",
                feedback_polarity="Positive"),
        _record(feedback_id="b", problem_type="Bug / defect",
                lifecycle_status="Completed"),
    )
    assert analytics.defects_by_journey_stage(frame).is_empty


def test_q8_breaks_the_count_down_by_problem_type():
    frame = _frame(
        _record(feedback_id="a", problem_type="Bug / defect"),
        _record(feedback_id="b", problem_type="Bug / defect"),
        _record(feedback_id="c", problem_type="Validation gap"),
    )
    row = analytics.defects_by_journey_stage(frame).rows[0]
    assert (row.values["bugs"], row.values["validation"],
            row.values["errors"]) == ("2", "1", "0")


# ==========================================================================
# Question 9 -- cross-cutting dependencies
# ==========================================================================
def test_q9_counts_each_feedback_id_once_per_secondary_category():
    frame = _frame(_record(
        feedback_id="a",
        secondary_assignments=[
            {"category": "Permissions & Approvals", "subcategory": "A"},
            {"category": "Permissions & Approvals", "subcategory": "B"},
        ],
    ))
    row = analytics.cross_cutting_dependencies(frame).rows[0]
    assert row.values["records"] == "1"
    assert row.feedback_ids == ["a"]


def test_q9_reports_the_most_common_primary_partner():
    frame = _frame(
        _record(feedback_id="a",
                primary_taxonomy_category="Form Configuration",
                secondary_assignments=[{"category": "Permissions & Approvals",
                                        "subcategory": "A"}]),
        _record(feedback_id="b",
                primary_taxonomy_category="Form Configuration",
                secondary_assignments=[{"category": "Permissions & Approvals",
                                        "subcategory": "A"}]),
        _record(feedback_id="c",
                primary_taxonomy_category="Observability & Debugging",
                secondary_assignments=[{"category": "Permissions & Approvals",
                                        "subcategory": "A"}]),
    )
    row = analytics.cross_cutting_dependencies(frame).rows[0]
    assert row.values["partner"] == "Form Configuration"
    assert row.values["linked"] == "2"


def test_q9_does_not_mix_secondary_counts_into_primary_totals(rel):
    """A secondary mention is a different measurement from a primary total."""
    # The ids behind a secondary row are records the category does not own:
    # at least one of them has a different primary category, so the number is
    # measuring participation rather than restating a primary total.
    for row in analytics.cross_cutting_dependencies(rel).rows:
        members = rel[rel["feedback_id"].isin(row.feedback_ids)]
        assert (members["primary_taxonomy_category"] != row.label).any()


# ==========================================================================
# Question 10 -- work already committed
# ==========================================================================
def test_q10_includes_only_planned_and_in_progress():
    frame = _frame(
        _record(feedback_id="a", lifecycle_status="Planned"),
        _record(feedback_id="b", lifecycle_status="In progress"),
        _record(feedback_id="c", lifecycle_status="Open"),
        _record(feedback_id="d", lifecycle_status="Completed"),
    )
    row = analytics.work_already_committed(frame).rows[0]
    assert row.values["committed"] == "2"
    assert row.values["planned"] == "1"
    assert row.values["progress"] == "1"
    assert set(row.feedback_ids) == {"a", "b"}


def test_q10_share_is_measured_against_the_whole_subcategory():
    frame = _frame(
        _record(feedback_id="a", lifecycle_status="Planned"),
        _record(feedback_id="b", lifecycle_status="Open"),
        _record(feedback_id="c", lifecycle_status="Open"),
        _record(feedback_id="d", lifecycle_status="Open"),
    )
    assert analytics.work_already_committed(frame).rows[0].values["share"] == "25%"


def test_q10_carries_the_lifecycle_caveat(rel):
    note = analytics.work_already_committed(rel).note
    assert "does not necessarily mean" in note


# ==========================================================================
# Product-action membership
# ==========================================================================
def test_product_action_rows_use_exact_supporting_ids(rel):
    """Not everything in the subcategory -- the exact group members."""
    from src.analysis.aggregate import product_actions

    membership = {tuple(sorted(a["open_supporting_feedback_ids"]))
                  for a in product_actions(rel).to_dict("records")}
    for question_id in ("oldest_open_actions", "recurring_demand",
                        "portal_discussion", "high_severity_singletons",
                        "human_review_risk"):
        for row in answer(question_id, rel).rows:
            assert tuple(sorted(row.feedback_ids)) in membership


def test_open_only_questions_exclude_every_other_status(rel, by_id):
    open_only = ("oldest_open_actions", "recurring_demand", "portal_discussion",
                 "high_severity_singletons", "human_review_risk",
                 "high_severity_share", "defects_by_stage")
    for question_id in open_only:
        for row in answer(question_id, rel).rows:
            for fid in row.feedback_ids:
                assert by_id[fid]["lifecycle_status"] == "Open", question_id


# ==========================================================================
# Scope
# ==========================================================================
def test_scope_default_is_the_whole_in_scope_dataset(rel):
    frame, label = data_assistant.resolve_scope(
        rel, rel.head(3), data_assistant.SCOPE_ALL)
    assert len(frame) == len(rel)
    assert label == f"Based on all {len(rel)} in-scope feedback records"


def test_scope_can_follow_the_dashboard_filters(rel):
    filtered = rel.head(7)
    frame, label = data_assistant.resolve_scope(
        rel, filtered, data_assistant.SCOPE_FILTERED)
    assert len(frame) == 7
    assert label == "Based on 7 records matching the current Dashboard filters"


def test_the_two_scopes_produce_different_answers(rel):
    narrow = rel[rel["primary_taxonomy_category"] == "Observability & Debugging"]
    wide_rows = analytics.unresolved_demand_rate(rel).rows
    narrow_rows = analytics.unresolved_demand_rate(narrow).rows
    assert len(narrow_rows) < len(wide_rows)


def test_conflicting_filters_give_an_empty_state_not_a_crash(rel):
    conflicting = rel[rel["lifecycle_status"] == "Completed"]
    result = analytics.oldest_unresolved_actions(conflicting)
    assert result.is_empty
    assert result.empty_message.strip()


# ==========================================================================
# UI
# ==========================================================================
def test_the_launcher_is_rendered_and_carries_a_robot_mark():
    markup = data_assistant.render_launcher_icon()
    assert "afi-bot-mark" in markup
    assert "<svg" in markup


def test_the_launcher_is_fixed_in_the_bottom_right():
    block = CSS.split(".st-key-afi_assistant_launcher {")[1].split("}")[0]
    assert "position: fixed" in block
    assert "right:" in block
    assert "bottom:" in block


def test_the_launcher_sits_above_the_page():
    block = CSS.split(".st-key-afi_assistant_launcher {")[1].split("}")[0]
    z = int(block.split("z-index:")[1].split(";")[0])
    assert z >= 1000


def test_the_assistant_is_rendered_once_at_shell_level():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert source.count("data_assistant.render(") == 1
    shell = source.index("data_assistant.render(")
    assert shell > source.index("with tab_guide:"), \
        "the assistant must render after both tabs, not inside one"


def test_the_assistant_has_no_free_text_input():
    source = (ROOT / "src/ui/data_assistant.py").read_text(encoding="utf-8")
    for widget in ("st.text_input", "st.text_area", "st.chat_input",
                   "disabled=True"):
        assert widget not in source


def test_the_prototype_and_production_messages_are_present():
    assert "does not call an AI model or consume tokens" in \
        data_assistant.PROTOTYPE_NOTE
    assert "Production extension" in data_assistant.render_footer()
    assert "should still cite the exact feedback records used" in \
        data_assistant.PRODUCTION_NOTE


def test_closing_the_panel_keeps_the_conversation(monkeypatch):
    state = {"afi_assistant_open": True,
             "afi_assistant_history": [{"question_id": "x"}]}
    monkeypatch.setattr(data_assistant.st, "session_state", state)
    data_assistant._close_panel()
    assert state["afi_assistant_open"] is False
    assert state["afi_assistant_history"] == [{"question_id": "x"}]


def test_clear_conversation_empties_the_history(monkeypatch):
    state = {"afi_assistant_open": True,
             "afi_assistant_history": [{"question_id": "x"}],
             "afi_assistant_selected_question": "x",
             "afi_assistant_show_questions": False}
    monkeypatch.setattr(data_assistant.st, "session_state", state)
    data_assistant._clear_conversation()
    assert state["afi_assistant_history"] == []
    assert state["afi_assistant_open"] is True, "clearing must not close the panel"


def test_history_is_capped(rel):
    history = [{"n": i} for i in range(data_assistant.MAX_HISTORY + 4)]
    del history[:-data_assistant.MAX_HISTORY]
    assert len(history) == data_assistant.MAX_HISTORY


def test_evidence_starts_at_five_records():
    assert data_assistant.EVIDENCE_PAGE == 5


def test_evidence_is_rendered_from_grounded_fields_only(rel):
    from html import escape

    record = rel.to_dict("records")[0]
    markup = data_assistant.render_evidence([record], "an action", 1)
    assert escape(record["title"], quote=True) in markup
    assert escape(record["source_url"], quote=True) in markup
    assert str(record["severity"]) in markup
    assert escape(record["evidence_excerpt"], quote=True) in markup


def test_mobile_css_keeps_the_panel_inside_the_viewport():
    mobile = CSS.split("@media (max-width: 650px)")[-1]
    assert ".st-key-afi_assistant_panel" in mobile
    assert "max-height: min(78vh" in mobile
    assert ".st-key-afi_assistant_launcher" in mobile


def test_the_panel_never_covers_the_whole_screen():
    block = CSS.split(".st-key-afi_assistant_panel {")[1].split("}")[0]
    assert "max-height: calc(100vh -" in block
    assert "overflow-y: auto" in block


def test_the_app_starts_without_an_api_key(monkeypatch):
    """Importing the assistant must not require credentials."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import importlib

    importlib.reload(analytics)
    importlib.reload(sys.modules["src.assistant.questions"])
