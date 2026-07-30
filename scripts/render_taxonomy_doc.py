"""Render TAXONOMY.md directly from src/models/taxonomy.py.

The taxonomy is large enough that a hand-written document would drift from the
code within one revision, and a stale taxonomy document is worse than none: it
is the thing a reviewer trusts to tell them what the categories mean. Generating
it makes drift impossible -- if the doc is wrong, the code is wrong.

    python -m scripts.render_taxonomy_doc
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.aggregate import (  # noqa: E402
    CRITICAL_MIN_RECORDS,
    CRITICAL_MIN_SEVERITY,
)
from src.models.taxonomy import (  # noqa: E402
    ALL_SUBCATEGORY_NAMES,
    CATEGORY_NAMES,
    CONFUSION_PAIRS,
    GLOSSARY,
    JOURNEY_STAGES,
    LIFECYCLE_STATUSES,
    OPEN_STATUSES,
    PERSONAS,
    PORTAL_STATUS_MAP,
    PROBLEM_TYPES,
    SEVERITY_SCALE,
    SOURCE_SYSTEMS,
    STAGE_GUIDE,
    STAGE_NAMES,
    TAXONOMY,
    TAXONOMY_VERSION,
    TIE_BREAK_RULES,
    WORKED_EXAMPLES,
)

OUT = ROOT / "TAXONOMY.md"


def render() -> str:
    n_sub = len(ALL_SUBCATEGORY_NAMES)
    lines: list[str] = []
    add = lines.append

    add("<!-- GENERATED FILE — do not edit by hand.")
    add("     Source: src/models/taxonomy.py")
    add("     Regenerate: python -m scripts.render_taxonomy_doc -->")
    add("")
    add("# Taxonomy")
    add("")
    add("How every piece of feedback is categorised. Defined **before** any data "
        "was classified, so the categories were not fitted to the answer.")
    add("")
    add("Single source of truth: [`src/models/taxonomy.py`](src/models/taxonomy.py). "
        "The classifier, the Pydantic schema, the dashboard, the in-app guide and "
        "this document all read from it. This file is generated from that module, "
        "so it cannot describe a taxonomy the code does not implement.")
    add("")
    add(f"> **Version {TAXONOMY_VERSION}.** The flat theme list was replaced by a "
        f"two-level structure of {len(CATEGORY_NAMES)} categories and {n_sub} "
        "subcategories, with problem type, persona, lifecycle status and source "
        "system split out as independent dimensions. Because the change is "
        "semantic rather than cosmetic, every record was **reclassified** rather "
        "than relabelled — the classification cache is keyed on the taxonomy "
        "version precisely so that a revision cannot replay old labels.")
    add("")
    add("---")
    add("")

    # --- dimensions table
    add("## Four independent dimensions")
    add("")
    add("| Dimension | Question it answers | Count |")
    add("|---|---|---|")
    add(f"| **Taxonomy category** | *Which broad product area* does this concern? "
        f"| **{len(CATEGORY_NAMES)}** |")
    add(f"| **Taxonomy subcategory** | *Which specific part* of that area needs "
        f"work? | **{n_sub}** |")
    add(f"| **Problem type** | *What kind* of problem is it? | "
        f"**{len(PROBLEM_TYPES)}** |")
    add(f"| **Journey stage** | *Where* in the Action lifecycle does the user hit "
        f"it? | **{len(STAGE_NAMES)}** |")
    add("")
    add("Keeping them independent is what makes the dashboard's views genuinely "
        "different rather than the same chart four times. A dynamic-permission "
        "failure sits in the **Permissions & Approvals** category while its "
        "problem type is **Poor error message** — encoding the problem type into "
        "the category name would make both unusable for counting.")
    add("")
    add("Severity, persona, lifecycle status and source system are further "
        "independent dimensions, and are never folded into a category name either.")
    add("")
    add("---")
    add("")

    # --- stages
    add(f"## Journey stages ({len(STAGE_NAMES)}, chronological)")
    add("")
    add("Order is load-bearing: every chart, filter and guide section derives its "
        "order from this list, so reordering it silently reorders the product "
        "story. Always pick the stage where the user **first** becomes blocked.")
    add("")
    add("| # | Stage | What the user is trying to do | Typical feedback |")
    add("|---|---|---|---|")
    for i, (name, _) in enumerate(JOURNEY_STAGES.items(), 1):
        guide = STAGE_GUIDE[name]
        example = guide["example"].replace("|", "\\|")
        add(f"| {i} | **{name}** | {guide['user_goal']} | {example} |")
    add("")
    add("---")
    add("")

    # --- categories
    add(f"## Categories and subcategories ({len(CATEGORY_NAMES)} × {n_sub})")
    add("")
    add("Each subcategory carries a **Do NOT use when** rule. Those rules matter "
        "more than the definitions: almost every misclassification is a confusion "
        "between two adjacent subcategories, and the avoid line is what names the "
        "neighbour and sends you to it.")
    add("")

    for i, (category, meta) in enumerate(TAXONOMY.items(), 1):
        add(f"### {i}. {category}")
        add("")
        add(f"{meta['plain']}")
        add("")
        add(f"*Usual journey stage:* `{meta['default_stage']}`  ")
        add(f"*Most often confused with:* "
            + ", ".join(f"*{c}*" for c in meta["confusable"]))
        add("")
        for subcategory, sub in meta["subcategories"].items():
            add(f"#### {subcategory}")
            add("")
            add(sub["plain"])
            add("")
            add("**Use for:** " + "; ".join(sub["use_for"]) + ".")
            add("")
            add(f"> ⛔ **Do NOT use when:** {sub['avoid']}")
            add("")
            for example in sub["examples"]:
                add(f"- {example}")
            add("")
        add("---")
        add("")

    # --- problem types
    add(f"## Problem types ({len(PROBLEM_TYPES)})")
    add("")
    add("Independent of product area. Note what is **absent**: there is no "
        "\"general or irrelevant feedback\" problem type. Irrelevance is expressed "
        "as `is_relevant = false`, so out-of-scope records are excluded from every "
        "distribution rather than diluting one.")
    add("")
    add("| Problem type | Meaning |")
    add("|---|---|")
    for name, meaning in PROBLEM_TYPES.items():
        add(f"| **{name}** | {meaning} |")
    add("")

    # --- severity
    add("## Severity")
    add("")
    add("How much the problem hurts **as described in the text** — not how popular "
        "the request is, and not how hard it would be to build.")
    add("")
    add("| Level | Meaning |")
    add("|---|---|")
    for level in sorted(SEVERITY_SCALE, reverse=True):
        add(f"| **{level}** | {SEVERITY_SCALE[level]} |")
    add("")

    # --- personas
    add(f"## Personas ({len(PERSONAS)})")
    add("")
    add("| Persona | Who they are |")
    add("|---|---|")
    for name, meaning in PERSONAS.items():
        add(f"| **{name}** | {meaning} |")
    add("")

    # --- lifecycle + sources
    add("## Lifecycle status and source system")
    add("")
    add(f"Lifecycle statuses: {', '.join(f'`{s}`' for s in LIFECYCLE_STATUSES)}.")
    add("")
    add(f"**Open statuses** — {', '.join(f'`{s}`' for s in sorted(OPEN_STATUSES))} "
        "— are the only ones counted towards a product-action ranking. Completed "
        "and closed work is excluded so a shipped feature cannot argue for itself "
        "again; it stays visible in the evidence explorer, where \"we already built "
        "this\" is itself a finding.")
    add("")
    add(f"Lifecycle status also feeds the ranking's first key. An action backed "
        f"by at least {CRITICAL_MIN_RECORDS} **open** records whose average "
        f"severity is {CRITICAL_MIN_SEVERITY:.0f} or above is treated as "
        "critical and outranks everything else. Both floors must be cleared; the "
        "severity test uses the raw mean rather than the rounded band, so an "
        "average of 3.5 does not qualify under a rule written as "
        f"\"{CRITICAL_MIN_SEVERITY:.0f} and above\". See "
        "[`ARCHITECTURE.md`](ARCHITECTURE.md) for the full key order.")
    add("")
    add("Portal statuses are normalised through this map. Anything unrecognised "
        "becomes `Unknown` rather than passing through as if it had been "
        "normalised.")
    add("")
    add("| Portal value | Normalised |")
    add("|---|---|")
    for raw, mapped in PORTAL_STATUS_MAP.items():
        add(f"| `{raw}` | `{mapped}` |")
    add("")
    add(f"Source systems: {', '.join(f'`{s}`' for s in SOURCE_SYSTEMS)}. **This POC "
        "collects only `Port portal`** — the other three exist in the schema "
        "because production ingests them through the same shape. No record is ever "
        "labelled with a source it did not come from, and a test asserts it.")
    add("")
    add("---")
    add("")

    # --- tie-breaks
    add(f"## Disambiguation rules ({len(TIE_BREAK_RULES)})")
    add("")
    add("Where a record could reasonably go either of two ways, these decide. "
        "Whatever ambiguity is left over is reported through `confidence` and "
        "`needs_human_review` rather than papered over.")
    add("")
    for i, rule in enumerate(TIE_BREAK_RULES, 1):
        add(f"{i}. {rule}")
        add("")

    # --- confusion pairs
    add("## Commonly confused pairs")
    add("")
    add("| This… | …not this |")
    add("|---|---|")
    for pair in CONFUSION_PAIRS:
        left = f"**{pair['left']}**<br>{pair['left_says']}".replace("|", "\\|")
        right = f"**{pair['right']}**<br>{pair['right_says']}".replace("|", "\\|")
        add(f"| {left} | {right} |")
    add("")

    # --- worked examples
    add("## Worked examples")
    add("")
    for ex in WORKED_EXAMPLES:
        add(f"**\"{ex['feedback']}\"**")
        add("")
        add(f"- Category: `{ex['category']}`")
        add(f"- Subcategory: `{ex['subcategory']}`")
        add(f"- Problem type: `{ex['problem_type']}`")
        add(f"- Journey stage: `{ex['stage']}`")
        add(f"- *Why:* {ex['why']}")
        add("")

    # --- glossary
    add("## Glossary")
    add("")
    add("| Term | Plain-language meaning |")
    add("|---|---|")
    for term, definition in GLOSSARY.items():
        add(f"| **{term}** | {definition} |")
    add("")

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} "
          f"({len(CATEGORY_NAMES)} categories, {len(ALL_SUBCATEGORY_NAMES)} "
          f"subcategories, {len(STAGE_NAMES)} stages)")
