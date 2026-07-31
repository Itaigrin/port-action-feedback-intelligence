"""The versioned classification prompt.

Split deliberately:
  SYSTEM  -- taxonomy, definitions, rules. Identical on every call, so it is
             marked for prompt caching and read at ~0.1x cost after the first
             request. This is what makes a taxonomy this detailed affordable:
             the 63 subcategory definitions are sent once and cached, not
             re-billed at full rate on all ~330 records.
  USER    -- only the record's title, body, source and category.

No author names, voter identities, or other personal data are ever sent: they
are not collected in the first place (see src/collectors/portal.py).

Bump PROMPT_VERSION whenever the text below changes. The version is recorded
on every analysed record so results can always be traced to the prompt that
produced them, and it forms part of the cache key so a prompt change forces a
genuine reclassification rather than replaying stale labels.
"""

from __future__ import annotations

from .taxonomy import (
    JOURNEY_STAGES,
    PERSONAS,
    POLARITIES,
    PROBLEM_TYPES,
    SEVERITY_SCALE,
    TAXONOMY,
    TIE_BREAK_RULES,
    WORKED_EXAMPLES,
)

# v4.0 -- adds feedback_polarity, judged from the text rather than from
# lifecycle status. Bumping this reclassifies every record, which is required:
# polarity cannot be back-filled from any field already stored.
#
# v3.0 -- hierarchical taxonomy (11 categories / 63 subcategories), independent
# problem type, persona, secondary assignments and a grouping-oriented
# suggested_product_action. Bumping this invalidates every cache key, which is
# intended: v2.0 labels are not translatable into this structure.
PROMPT_VERSION = "v4.0"

_NL = chr(10)


def _stages_ordered(items: dict[str, str]) -> str:
    """Number the stages so the model sees the lifecycle order explicitly."""
    return _NL.join(f"  {i}. {k}: {v}"
                    for i, (k, v) in enumerate(items.items(), 1))


def _numbered(items: dict[str, str]) -> str:
    return _NL.join(f"  - {k}: {v}" for k, v in items.items())


def _render_taxonomy() -> str:
    """Render the two-level taxonomy in full.

    Every subcategory carries its "use for" triggers AND its "avoid" rule. The
    avoid rules matter more than the definitions: almost every misclassification
    is a confusion between two adjacent subcategories, and the avoid line is
    what names the neighbour and sends the model to it.
    """
    blocks: list[str] = []
    for i, (category, meta) in enumerate(TAXONOMY.items(), 1):
        lines = [
            f"### {i}. {category}",
            f"{meta['plain']}",
            f"Usual journey stage: {meta['default_stage']}",
            "",
        ]
        for subcategory, sub in meta["subcategories"].items():
            lines.append(f"  * {subcategory}")
            lines.append(f"      {sub['plain']}")
            lines.append("      Use for: " + "; ".join(sub["use_for"]) + ".")
            lines.append(f"      Do NOT use when: {sub['avoid']}")
        blocks.append(_NL.join(lines))
    return _NL.join(blocks)


def _render_worked_examples() -> str:
    out: list[str] = []
    for ex in WORKED_EXAMPLES:
        out.append(
            f'  Feedback: "{ex["feedback"]}"\n'
            f'    -> category: {ex["category"]}\n'
            f'    -> subcategory: {ex["subcategory"]}\n'
            f'    -> problem type: {ex["problem_type"]}\n'
            f'    -> journey stage: {ex["stage"]}\n'
            f'    Why: {ex["why"]}'
        )
    return "\n\n".join(out)


SYSTEM_PROMPT = f"""\
You are a product analyst at Port, an internal developer portal company.

Port lets platform engineers build "self-service actions" -- forms developers
fill in to provision infrastructure, deploy services, or request access. Many
users start configuring an action but never reach a first successful trigger.
Your job is to read one piece of feedback and classify it, so the product team
can see where that friction concentrates and what to build next.

## The four dimensions -- they answer DIFFERENT questions

TAXONOMY CATEGORY answers: "Which broad product area does this concern?"
TAXONOMY SUBCATEGORY answers: "Which specific part of that area needs work?"
PROBLEM TYPE answers: "What KIND of problem is this?"
JOURNEY STAGE answers: "WHERE in the action lifecycle does the user hit it?"

They are independent and must not be collapsed into each other. A dynamic
permission failure sits in the Permissions & Approvals category while its
problem type is "Poor error message". Pick the category and subcategory for
the product change needed, the problem type for its nature, and the stage
where the user's friction FIRST begins.

## Journey stages -- WHERE the user is stuck (chronological lifecycle order)
{_stages_ordered(JOURNEY_STAGES)}

## Problem types -- WHAT KIND of problem this is
{_numbered(PROBLEM_TYPES)}

## Severity scale
{_NL.join(f"  {k} = {v}" for k, v in sorted(SEVERITY_SCALE.items(), reverse=True))}

## Personas
{_numbered(PERSONAS)}

## Feedback polarity -- what the customer was EXPRESSING
{_numbered(POLARITIES)}

Judge polarity from the feedback text, never from whether the request was
built. A completed roadmap item still records the pain that prompted it, so a
shipped request is not automatically positive.

Most product feedback is NEGATIVE, including feature requests: asking for a
capability because you cannot finish a task is a description of being blocked.
Only call something Positive when the text actually expresses satisfaction,
praise or a confirmed fix. Only call it Neutral when it is genuinely
informational -- a question, a description, a status note -- with no praise and
no pain. Do NOT use Neutral as a soft landing for feedback you find hard to
read; if it describes friction, it is Negative, and if you truly cannot tell,
set needs_human_review.

## Taxonomy -- 11 categories, 63 subcategories

Choose exactly ONE primary category and ONE subcategory that belongs to it.
Selecting a subcategory from a different category is invalid and will be
rejected.

{_render_taxonomy()}

## Disambiguation rules
{_NL.join(f"  - {r}" for r in TIE_BREAK_RULES)}

## Worked examples

{_render_worked_examples()}

## Rules you must follow

1. RELEVANCE FIRST. Set is_relevant=false for anything not about configuring,
   running, approving or debugging Port self-service actions. General Port
   audit logs, catalog modelling, dashboards, scorecards, data sources,
   general automation authoring and third-party integrations are NOT relevant
   unless the feedback is specifically about an action that uses them. Always
   give a relevance_reason. Being wrongly included is worse than being
   excluded: a padded dataset produces false conclusions. When is_relevant is
   false, leave the taxonomy, problem type and journey stage empty.

2. QUOTE EXACTLY. evidence_excerpt must be copied character-for-character from
   the text you are given. Do not paraphrase, do not tidy grammar, do not join
   two separate sentences. Choose 10-30 words that best show the problem in the
   user's own words. If the text contains no usable sentence, quote the single
   most relevant phrase that IS present. Never invent a quote. Output the quote
   and nothing else in that field -- no trailing commentary, braces or marks.

3. NEVER ADD FACTS. Everything you output must be supported by the text in
   front of you. Do not infer customer names, company size, urgency, revenue
   impact, or business consequences that are not stated. Do not use knowledge
   about Port beyond what the feedback says.

4. SOME RECORDS ARE WRITTEN BY PORT STAFF, not customers -- they read like
   product copy and describe a capability Port intends to build. Classify the
   underlying user problem, and prefer to quote the sentence that states the
   problem rather than the sentence that pitches the solution.

5. BE HONEST ABOUT CONFIDENCE. Use below 0.7 when the feedback is vague, very
   short, spans several areas, or could reasonably sit in two subcategories.
   Set needs_human_review=true when two categories are equally plausible or
   scope is genuinely unclear. A well-calibrated low score is more useful than
   false certainty. Confidence never affects prioritisation -- it is only a
   quality signal.

6. SEVERITY IS ABOUT THE USER'S PAIN as described in the text, not about how
   popular the request is and not about how hard it would be to build. If no
   pain is described, severity is low.

7. SECONDARY ASSIGNMENTS ARE OPTIONAL AND RARE. Add one only when a second
   product area is genuinely implicated -- for example a permissions problem
   whose real complaint is the missing explanation. Never add one merely
   because another technology is mentioned. Never repeat the primary. At most
   two. Leave the list empty when in doubt; secondary assignments never affect
   any count or ranking.

8. suggested_product_action IS A GROUPING KEY. Phrase it as the capability
   Port would build, starting with a verb, in plain product language --
   "Enforce action input validation in the server-side execution path", not
   "the user wants validation". Two records asking for the same change must
   produce near-identical wording, because these are grouped together
   downstream. Do not describe the customer; describe the change.

9. WRITE FOR A PRODUCT AUDIENCE. short_summary and user_need should be plain
   business English that a non-engineer can follow. No Port-internal jargon.

10. DO NOT CLASSIFY ON KEYWORDS ALONE. Feedback that merely mentions "payload"
    is not automatically an invocation record. Ask what product change would
    actually solve the user's problem, then pick that category and
    subcategory. Read the "Do NOT use when" line before committing: most wrong
    answers are the neighbouring subcategory it names.

11. POLARITY IS ABOUT THE CUSTOMER'S SIGNAL, not about the product's current
    state and not about how politely it is worded. Give polarity_reason as one
    short clause naming the phrase that decided it.

Return only the structured fields requested."""


def build_user_prompt(title: str, description: str | None,
                      category: str | None,
                      source_system: str | None = None) -> str:
    """Assemble the per-record message. Volatile content only."""
    body = (description or "").strip() or "(no description provided)"
    cat = category or "(uncategorised)"
    src = source_system or "Port portal"
    return (
        f"Source system: {src}\n"
        f"Board category: {cat}\n\n"
        f"Title: {title}\n\n"
        f"Body:\n{body}\n\n"
        "Classify this feedback."
    )


def source_text(title: str, description: str | None) -> str:
    """The exact text an evidence excerpt must be found in.

    Must match what build_user_prompt shows the model, or grounding checks
    would reject valid quotes.
    """
    return f"{title}\n{description or ''}"
