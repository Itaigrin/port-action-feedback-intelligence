"""Apply the v3.0 taxonomy assignment workbook to the classified records.

The workbook is the authority for where each existing relevant record lands
under v3. This script writes those assignments into analyzed.json and nothing
else: raw feedback text, severity, persona, polarity, problem type, journey
stage and every product-action field are copied through untouched.

Four rules the migration holds to:

  * The former v2.1 subcategory is preserved as `topic_tags`. Consolidating 63
    groups into 30 loses an analytical distinction on purpose, but the finer
    name was often a real technical detail and is kept queryable.
  * Out-of-scope records stay unassigned. They have no category, no
    subcategory, no tags -- exactly as before -- so they can never reach a
    figure.
  * Rows the workbook marks for review keep `needs_human_review` set. A
    consolidation the workbook itself was unsure about must not arrive looking
    settled.
  * Secondary assignments are migrated through the same 63->30 map, then
    de-duplicated: two former subcategories that merged into one group would
    otherwise appear twice on the same record.

    python -m scripts.migrate_taxonomy_v3 <workbook.xlsx> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models.taxonomy import (  # noqa: E402
    CATEGORY_FOR_SUBCATEGORY,
    SUBCATEGORY_MIGRATION,
    TAXONOMY_VERSION,
)

ANALYZED = ROOT / "data" / "processed" / "analyzed.json"

# The workbook's own wording for "we mapped this mechanically, look again".
REVIEW_STATUS_FLAG = "Recommended - review during v3 rerun"


def _former_secondaries(record: dict) -> list[str]:
    """The record's secondary subcategory names, whichever shape holds them.

    classify.py writes two parallel flat lists and, separately, a list of
    assignment objects. In the stored data the flat lists are the populated
    ones -- reading only the objects finds nothing to migrate and silently
    leaves retired v2.1 names on the record.
    """
    flat = record.get("secondary_subcategories") or []
    if flat:
        return [str(s) for s in flat]
    out = []
    for item in record.get("secondary_assignments") or []:
        name = item.get("subcategory") or item.get("taxonomy_subcategory")
        if name:
            out.append(str(name))
    return out


def _migrate_secondaries(record: dict, new_primary: tuple[str, str]) -> list[dict]:
    """Move secondary assignments onto v3, dropping duplicates and self-refs.

    Two former subcategories that merged into the same v3 group would
    otherwise appear twice on one record, and a secondary that merged into the
    record's own new primary would repeat it.
    """
    seen: set[tuple[str, str]] = {new_primary}
    out: list[dict] = []
    for old_sub in _former_secondaries(record):
        new_sub = SUBCATEGORY_MIGRATION.get(old_sub, old_sub)
        new_cat = CATEGORY_FOR_SUBCATEGORY.get(new_sub)
        if not new_cat:
            # A name with no destination. Dropping beats keeping a pointer to
            # a subcategory that no longer exists.
            continue
        pair = (new_cat, new_sub)
        if pair in seen:
            continue
        seen.add(pair)
        out.append({"category": new_cat, "subcategory": new_sub})
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    assignments = pd.read_excel(args.workbook, sheet_name="Relevant Assignments")
    by_id = {str(r["feedback_id"]): r for _, r in assignments.iterrows()}

    data = json.loads(ANALYZED.read_text(encoding="utf-8"))
    records = data["records"]

    stats = {"relevant": 0, "out_of_scope": 0, "reassigned": 0,
             "unchanged_subcategory": 0, "flagged_for_review": 0,
             "tagged": 0, "missing_from_workbook": 0}

    for record in records:
        fid = str(record["feedback_id"])

        if not record.get("is_relevant"):
            stats["out_of_scope"] += 1
            # Belt and braces: assert the invariant rather than assume it.
            record["primary_taxonomy_category"] = None
            record["primary_taxonomy_subcategory"] = None
            record["secondary_assignments"] = []
            record["topic_tags"] = []
            continue

        stats["relevant"] += 1
        row = by_id.get(fid)
        if row is None:
            stats["missing_from_workbook"] += 1
            continue

        former = record.get("primary_taxonomy_subcategory")
        new_cat = str(row["recommended_category_v3"])
        new_sub = str(row["recommended_subcategory_v3"])

        if former and former != new_sub:
            stats["reassigned"] += 1
        else:
            stats["unchanged_subcategory"] += 1

        record["primary_taxonomy_category"] = new_cat
        record["primary_taxonomy_subcategory"] = new_sub

        # Both shapes, always together. classify.py flattens the assignment
        # objects into two parallel lists and the dashboard reads *those*, so
        # migrating only the objects leaves retired v2.1 names on screen while
        # the structured field looks correct.
        secondaries = _migrate_secondaries(record, (new_cat, new_sub))
        record["secondary_assignments"] = secondaries
        record["secondary_categories"] = [s["category"] for s in secondaries]
        record["secondary_subcategories"] = [s["subcategory"] for s in secondaries]

        # The former name, plus whatever the workbook noted as the topic.
        tags: list[str] = []
        for tag in (former, row.get("topic_tag")):
            tag = "" if tag is None or pd.isna(tag) else str(tag).strip()
            if tag and tag != new_sub and tag not in tags:
                tags.append(tag)
        record["topic_tags"] = tags
        if tags:
            stats["tagged"] += 1

        if str(row.get("assignment_review_status", "")) == REVIEW_STATUS_FLAG:
            record["needs_human_review"] = True
            stats["flagged_for_review"] += 1

    data.setdefault("meta", {})["taxonomy_version"] = TAXONOMY_VERSION

    print(f"records            : {len(records)}")
    for key, value in stats.items():
        print(f"{key:19}: {value}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    ANALYZED.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {ANALYZED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
