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
    FEEDBACK_TYPES,
    JOURNEY_STAGES,
    SEVERITY_SCALE,
    THEMES,
    TIE_BREAK_RULES,
)

PROMPT_VERSION = "v1.0"


def _numbered(items: dict[str, str]) -> str:
    return "\n".join(f"  - {k}: {v}" for k, v in items.items())


SYSTEM_PROMPT = f"""\
You are a product analyst at Port, an internal developer portal company.

Port lets platform engineers build "self-service actions" -- forms developers
fill in to provision infrastructure, deploy services, or request access. Many
users start configuring an action but never reach a first successful trigger.
Your job is to read one piece of public feedback and classify it, so the
product team can see where that friction concentrates.

## Journey stages -- WHERE the user is stuck
{_numbered(JOURNEY_STAGES)}

## Themes -- WHAT the specific problem area is
{_numbered(THEMES)}

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
