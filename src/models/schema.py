"""Validated output schema for LLM classification.

Every categorical field is a closed enum built from the taxonomy, so a label
the model invents fails validation rather than quietly entering the dataset.
That is the first anti-fabrication control. The second is quote grounding,
verified in Python after the response returns (see ground_excerpt).

The taxonomy is hierarchical -- category then subcategory -- so a further
control applies: the pair must be internally consistent. A subcategory that
exists but belongs to a different category is rejected, which prevents the
model from assembling a plausible-looking but impossible classification.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .taxonomy import (
    ASSIGNABLE_SUBCATEGORY_NAMES,
    CATEGORY_NAMES,
    PERSONA_NAMES,
    POLARITY_NAMES,
    PROBLEM_TYPE_NAMES,
    STAGE_NAMES,
    is_valid_pair,
)

# Literal types are built from the taxonomy so the two can never drift apart.
TaxonomyCategory = Literal[CATEGORY_NAMES]        # type: ignore[valid-type]
# Assignable, not core: the schema must permit the fallback so unmatched
# feedback has somewhere legal to go. Views and counts use the core list.
TaxonomySubcategory = Literal[ASSIGNABLE_SUBCATEGORY_NAMES]  # type: ignore[valid-type]
JourneyStage = Literal[STAGE_NAMES]               # type: ignore[valid-type]
ProblemType = Literal[PROBLEM_TYPE_NAMES]         # type: ignore[valid-type]
Persona = Literal[PERSONA_NAMES]                  # type: ignore[valid-type]
Polarity = Literal[POLARITY_NAMES]                # type: ignore[valid-type]

MAX_SECONDARY_ASSIGNMENTS = 2

# topic_tags is a stored field on the record, NOT a field the model returns.
#
# It was tried as a model output first and could not ship: adding an array of
# strings to this schema pushed the structured-output grammar past its compile
# budget, and the API answered "Grammar compilation timed out" on every call.
# Measured, with everything else identical -- with the array the request fails
# after ~120s; without it the same request succeeds. Bounding the item length
# did not help; the array itself is the cost.
#
# Nothing is lost by moving it. What v3 needs preserved is the former v2.1
# subcategory of each existing record, which the migration knows exactly and
# the model would only be guessing at. scripts/migrate_taxonomy_v3.py writes
# it, and the reconcile step restores it after a reclassification run.
MAX_TOPIC_TAGS = 4


class SecondaryAssignment(BaseModel):
    """An additional product area meaningfully involved in the same feedback.

    Secondary assignments exist so a record like "dynamic permission denial
    does not explain which condition failed" can be visible to both the
    Permissions and the Observability owner. They never affect counts or
    ranking -- only the primary assignment does -- so adding one can never
    inflate a total.
    """

    category: TaxonomyCategory = Field(
        description="A second product area genuinely involved in this feedback."
    )
    subcategory: TaxonomySubcategory = Field(
        description="A subcategory that belongs to that category."
    )

    @model_validator(mode="after")
    def _pair_must_be_consistent(self) -> "SecondaryAssignment":
        if not is_valid_pair(self.category, self.subcategory):
            raise ValueError(
                f"subcategory {self.subcategory!r} does not belong to "
                f"category {self.category!r}"
            )
        return self


class FeedbackClassification(BaseModel):
    """The structured record the model produces for one feedback item."""

    # --- scope --------------------------------------------------------------
    is_relevant: bool = Field(
        description="True only if this feedback is about configuring, running, "
                    "approving or debugging Port self-service Actions. False "
                    "for catalog modelling, dashboards, scorecards, general "
                    "automations and other unrelated product areas."
    )
    relevance_reason: str = Field(
        min_length=10, max_length=200,
        description="One sentence explaining why this is, or is not, Action "
                    "Configuration feedback."
    )

    # --- taxonomy (hierarchical) -------------------------------------------
    primary_taxonomy_category: TaxonomyCategory | None = Field(
        default=None,
        description="The single product area where the main change should be "
                    "made. Null only when is_relevant is false."
    )
    primary_taxonomy_subcategory: TaxonomySubcategory | None = Field(
        default=None,
        description="The specific part of that category needing attention. "
                    "Must belong to primary_taxonomy_category."
    )
    secondary_assignments: list[SecondaryAssignment] = Field(
        default_factory=list, max_length=MAX_SECONDARY_ASSIGNMENTS,
        description="At most two further product areas meaningfully involved. "
                    "Leave empty unless another area is genuinely implicated -- "
                    "not merely mentioned."
    )

    # --- independent dimensions --------------------------------------------
    problem_type: ProblemType | None = Field(
        default=None,
        description="What kind of problem this is, independent of product area. "
                    "Null only when is_relevant is false."
    )
    journey_stage: JourneyStage | None = Field(
        default=None,
        description="Where in the Action experience the user first becomes "
                    "blocked. Null only when is_relevant is false."
    )
    persona: Persona = Field(
        default="Unknown",
        description="The kind of user the feedback comes from. Use 'Unknown' "
                    "when the text does not make it clear."
    )
    severity: int = Field(
        ge=1, le=5,
        description="1 = nice to have, 5 = blocking with no workaround."
    )
    feedback_polarity: Polarity = Field(
        default="Neutral",
        description="What the customer was expressing, judged from the text "
                    "itself. Negative = a problem, unmet need, blocker, "
                    "friction or difficulty, including a feature request "
                    "clearly motivated by current pain. Positive = "
                    "satisfaction, praise, or confirmation that something "
                    "shipped solved the problem. Neutral = informational or a "
                    "factual question. Judge the original signal, never the "
                    "lifecycle status: a completed request may still record "
                    "negative feedback."
    )
    polarity_reason: str = Field(
        default="", max_length=160,
        description="One short clause naming the phrase that decided the "
                    "polarity. Leave empty only if the text gives nothing."
    )

    # --- narrative ----------------------------------------------------------
    short_summary: str = Field(
        min_length=10, max_length=200,
        description="One plain sentence describing the problem, in business "
                    "language. No jargon, no restating the title."
    )
    user_need: str = Field(
        min_length=10, max_length=200,
        description="What the user is ultimately trying to achieve, phrased as "
                    "a need rather than a solution."
    )
    suggested_product_action: str = Field(
        min_length=10, max_length=200,
        description="The product change that would resolve this, phrased as a "
                    "capability. Records asking for the same change should "
                    "produce near-identical wording so they group together."
    )

    # --- quality signals ----------------------------------------------------
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="How certain you are of this classification. Be honest: "
                    "use below 0.7 when the feedback is vague or genuinely "
                    "spans two areas."
    )
    needs_human_review: bool = Field(
        default=False,
        description="True when the feedback is ambiguous, two categories are "
                    "equally plausible, or scope is unclear."
    )
    evidence_excerpt: str = Field(
        min_length=10, max_length=300,
        description="A short quote copied EXACTLY from the feedback text. Must "
                    "appear verbatim in the source. Never paraphrase."
    )

    @model_validator(mode="after")
    def _check_taxonomy_consistency(self) -> "FeedbackClassification":
        if self.is_relevant:
            missing = [
                name for name, value in (
                    ("primary_taxonomy_category", self.primary_taxonomy_category),
                    ("primary_taxonomy_subcategory", self.primary_taxonomy_subcategory),
                    ("problem_type", self.problem_type),
                    ("journey_stage", self.journey_stage),
                )
                if value is None
            ]
            if missing:
                raise ValueError(
                    "relevant records require " + ", ".join(missing)
                )
            if not is_valid_pair(
                self.primary_taxonomy_category, self.primary_taxonomy_subcategory
            ):
                raise ValueError(
                    f"subcategory {self.primary_taxonomy_subcategory!r} does not "
                    f"belong to category {self.primary_taxonomy_category!r}"
                )
        else:
            # Irrelevant records carry no taxonomy at all. Clearing rather than
            # rejecting keeps one out-of-scope record from failing a whole run,
            # and guarantees out-of-scope feedback can never reach a category
            # total.
            self.primary_taxonomy_category = None
            self.primary_taxonomy_subcategory = None
            self.problem_type = None
            self.journey_stage = None
            self.secondary_assignments = []
            # Tags go too. They are taxonomy detail, and an out-of-scope record
            # carrying "Approval policies & thresholds" would still surface in
            # a tag search as though it had been classified.

        # A secondary that repeats the primary, or repeats another secondary,
        # would double-count the same area in the drill-down.
        seen: set[tuple[str, str]] = set()
        if self.primary_taxonomy_category:
            seen.add(
                (self.primary_taxonomy_category, self.primary_taxonomy_subcategory)
            )
        deduped: list[SecondaryAssignment] = []
        for assignment in self.secondary_assignments:
            key = (assignment.category, assignment.subcategory)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(assignment)
        self.secondary_assignments = deduped
        return self


class AnalyzedRecord(BaseModel):
    """A classification joined to its source record, with provenance."""

    feedback_id: str
    title: str
    source_system: str
    lifecycle_status: str
    comments_count: int | None
    category: str | None
    created_at: str | None
    retrieved_at: str | None
    source_url: str

    classification: FeedbackClassification

    # Written by the migration, never by the model -- see MAX_TOPIC_TAGS.
    topic_tags: list[str] = Field(default_factory=list, max_length=MAX_TOPIC_TAGS)

    feedback_polarity: str
    # provenance -- recorded so any figure can be traced to what produced it
    model_name: str
    prompt_version: str
    taxonomy_version: str
    schema_version: str
    analysis_run_id: str
    analyzed_at: str
    # computed in Python, never generated by the model
    evidence_verified: bool


# --- quote grounding -------------------------------------------------------
_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    """Normalise for substring comparison without weakening the check.

    Only unicode form, whitespace, and quote style are relaxed -- the words
    themselves must still match exactly.
    """
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    return _WS.sub(" ", text).strip().lower()


MIN_GROUNDED_WORDS = 6


def verify_excerpt(excerpt: str, source_text: str) -> bool:
    """True if the excerpt appears verbatim in the source."""
    if not excerpt or not source_text:
        return False
    return _norm(excerpt) in _norm(source_text)


def ground_excerpt(excerpt: str, source_text: str) -> tuple[bool, str]:
    """Return (verified, excerpt_to_display).

    Structured-output generation occasionally appends stray characters to the
    end of a string field -- observed in practice as a trailing brace, a lone
    quote mark, a CJK character, or a fragment of the model's own commentary.
    The quoted words themselves are correct; only the tail is corrupt.

    Rather than discard an otherwise-valid quote, trim trailing words until
    what remains is a genuine substring of the source, and display only that.
    This *tightens* the guarantee: whatever is shown to a user has been
    verified character-for-character against the source text.

    A quote that cannot be grounded to at least MIN_GROUNDED_WORDS words is
    rejected outright and never displayed.
    """
    if not excerpt or not source_text:
        return False, excerpt

    if verify_excerpt(excerpt, source_text):
        return True, excerpt.strip()

    words = excerpt.split()
    for end in range(len(words) - 1, MIN_GROUNDED_WORDS - 1, -1):
        candidate = " ".join(words[:end])
        if verify_excerpt(candidate, source_text):
            return True, candidate.rstrip(" ,;:-\"'").strip()

    # Leading garbage is rarer, but check before giving up.
    for start in range(1, min(4, len(words) - MIN_GROUNDED_WORDS)):
        candidate = " ".join(words[start:])
        if verify_excerpt(candidate, source_text):
            return True, candidate.strip()

    return False, excerpt
