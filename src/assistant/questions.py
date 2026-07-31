"""The ten questions the Product Data Assistant can answer.

A closed registry, not an interpreter. Each entry maps a fixed label to one
deterministic handler, so there is no path from user input to generated code
and nothing to call a model about. The assistant works with no API key, no
network and no tokens.

The labels are the exact visible wording. Tests assert them, because the
question a reader clicks is part of the contract -- an answer computed from
open records only is wrong under a label that does not say "open".
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from . import analytics
from .analytics import Answer


@dataclass(frozen=True)
class AssistantQuestion:
    question_id: str
    label: str
    short_description: str
    handler: Callable[[pd.DataFrame], Answer]


QUESTIONS: tuple[AssistantQuestion, ...] = (
    AssistantQuestion(
        "oldest_open_actions",
        "Which open Product Actions have been waiting the longest?",
        "Ranks open actions by their earliest open feedback date.",
        analytics.oldest_unresolved_actions,
    ),
    AssistantQuestion(
        "recurring_demand",
        "Which Product Actions show recurring demand over the longest period?",
        "Requests raised repeatedly rather than reported once.",
        analytics.recurring_demand,
    ),
    AssistantQuestion(
        "portal_discussion",
        "Which open Product Actions have generated the most discussion in the "
        "Port portal?",
        "Uses portal comment counts as a separate engagement signal.",
        analytics.most_discussed_in_portal,
    ),
    AssistantQuestion(
        "high_severity_singletons",
        "Which high-severity Product Actions are supported by only one open "
        "record?",
        "Severe signals that a volume-led ranking can bury.",
        analytics.high_severity_single_signals,
    ),
    AssistantQuestion(
        "human_review_risk",
        "Which Product Actions need the most human review before "
        "prioritization?",
        "Where classification uncertainty could make a decision unsafe.",
        analytics.needs_most_human_review,
    ),
    AssistantQuestion(
        "high_severity_share",
        "Which Subcategories have the highest share of high-severity negative "
        "feedback?",
        "Severity concentration, not raw volume.",
        analytics.high_severity_share_by_subcategory,
    ),
    AssistantQuestion(
        "unresolved_rate",
        "Which Categories have the highest unresolved-demand rate?",
        "The share of each category's feedback still open.",
        analytics.unresolved_demand_rate,
    ),
    AssistantQuestion(
        "defects_by_stage",
        "Which Journey Stages contain the most bugs, validation gaps, and poor "
        "error messages?",
        "Separates things that are broken from things that are missing.",
        analytics.defects_by_journey_stage,
    ),
    AssistantQuestion(
        "cross_cutting",
        "Which Categories most often appear as secondary dependencies?",
        "Areas repeatedly pulled into problems another area owns.",
        analytics.cross_cutting_dependencies,
    ),
    AssistantQuestion(
        "already_committed",
        "Which Subcategories have the most feedback already marked Planned or "
        "In progress?",
        "Where work is already committed or underway.",
        analytics.work_already_committed,
    ),
)

QUESTIONS_BY_ID: dict[str, AssistantQuestion] = {q.question_id: q for q in QUESTIONS}


def answer(question_id: str, frame: pd.DataFrame) -> Answer:
    """Run one registered question. Unknown ids are a programming error."""
    return QUESTIONS_BY_ID[question_id].handler(frame)
