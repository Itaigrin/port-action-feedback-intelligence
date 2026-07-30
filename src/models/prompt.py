"""The versioned classification prompt.

Split deliberately:
  SYSTEM  -- taxonomy, definitions, rules. Identical on every call, so it is
             marked for prompt caching and read at ~0.1x cost after the first
             request.
  USER    -- only the post's title, body, and category.

No author names, voter identities, or other personal data are ever sent: they
are not collected in the first place (see src/collectors/portal.py).

Bump PROMPT_VERSION whenever the text below changes. The version is recorded
on every analysed record so results can always be traced to the prompt that
produced them.
"""

from __future__ import annotations

from .taxonomy import (
    DEFAULT_STAGE_FOR_THEME,
    FEEDBACK_TYPES,
    JOURNEY_STAGES,
    SEVERITY_SCALE,
    THEMES,
    TIE_BREAK_RULES,
)

# v2.0 -- 11 themes / 8 stages taxonomy, with the context-and-pre-fill theme and
# stage added and the three execution themes merged. Bumping this invalidates
# every cache key, which is intended: the old labels are not translatable.
PROMPT_VERSION = "v2.0"


def _numbered(items: dict[str, str]) -> str:
    return "\n".join(f"  - {k}: {v}" for k, v in items.items())


def _stages_ordered(items: dict[str, str]) -> str:
    """Number the stages so the model sees the lifecycle order explicitly."""
    return "\n".join(f"  {i}. {k}: {v}"
                     for i, (k, v) in enumerate(items.items(), 1))


SYSTEM_PROMPT = f"""\
You are a product analyst at Port, an internal developer portal company.

Port lets platform engineers build "self-service actions" -- forms developers
fill in to provision infrastructure, deploy services, or request access. Many
users start configuring an action but never reach a first successful trigger.
Your job is to read one piece of public feedback and classify it, so the
product team can see where that friction concentrates.

## The two dimensions -- they answer DIFFERENT questions

THEME answers: "What is the main product problem, or the main product change
that would solve it?"
JOURNEY STAGE answers: "Where in the action lifecycle does the user hit this?"

They are independent. Pick the theme for the product change needed, and the
stage where the user's friction BEGINS. A theme has a usual stage (listed
below), but use a different stage when the feedback clearly calls for it.

## Journey stages -- WHERE the user is stuck (chronological lifecycle order)
{_stages_ordered(JOURNEY_STAGES)}

## Themes -- WHAT product problem is being raised
{_numbered(THEMES)}

## Usual stage for each theme (a guideline, not a rule)
{chr(10).join(f"  - {t} -> {s}" for t, s in DEFAULT_STAGE_FOR_THEME.items())}

## Feedback types
{_numbered(FEEDBACK_TYPES)}

## Severity scale
{chr(10).join(f"  {k} = {v}" for k, v in sorted(SEVERITY_SCALE.items(), reverse=True))}

## Disambiguation rules
{chr(10).join(f"  - {r}" for r in TIE_BREAK_RULES)}

## Rules you must follow

1. RELEVANCE FIRST. Set is_relevant=false for anything not about configuring,
   running, or governing self-service actions, workflows, or automations.
   Catalog modelling, dashboards, scorecards, data sources, and third-party
   integrations are NOT relevant unless the post is specifically about an
   action that uses them. Being wrongly included is worse than being excluded:
   a padded dataset produces false conclusions.

2. QUOTE EXACTLY. evidence_excerpt must be copied character-for-character from
   the post text you are given. Do not paraphrase, do not tidy grammar, do not
   join two separate sentences. Choose 10-30 words that best show the problem
   in the user's own words. If the text contains no usable sentence, quote the
   single most relevant phrase that IS present. Never invent a quote.

3. NEVER ADD FACTS. Everything you output must be supported by the text in
   front of you. Do not infer customer names, company size, urgency, or
   business impact that is not stated. Do not use knowledge about Port beyond
   what the post says.

4. SOME POSTS ARE WRITTEN BY PORT STAFF, not customers -- they read like
   product copy and describe a capability Port intends to build. Classify the
   underlying user problem, and prefer to quote the sentence that states the
   problem rather than the sentence that pitches the solution.

5. BE HONEST ABOUT CONFIDENCE. Use below 0.7 when the post is vague, very
   short, spans several areas, or could reasonably sit in two stages. A
   well-calibrated low score is more useful than false certainty. Confidence
   never affects prioritisation -- it is only a quality signal.

6. SEVERITY IS ABOUT THE USER'S PAIN as described in the text, not about how
   many votes the post has and not about how hard it would be to build. If no
   pain is described, severity is low.

7. WRITE FOR A PRODUCT AUDIENCE. short_summary and user_need should be plain
   business English that a non-engineer can follow. No Port-internal jargon.

8. DO NOT CLASSIFY ON KEYWORDS ALONE. A post that merely mentions "payload" is
   not automatically a backend post. Ask what product change would actually
   solve the user's problem, then pick that theme. If a post spans several
   areas, choose the theme for the MAIN problem and the stage where the user
   FIRST becomes blocked -- there are no secondary classifications.

Return only the structured fields requested."""


def build_user_prompt(title: str, description: str | None,
                      category: str | None) -> str:
    """Assemble the per-record message. Volatile content only."""
    body = (description or "").strip() or "(no description provided)"
    cat = category or "(uncategorised)"
    return (
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
