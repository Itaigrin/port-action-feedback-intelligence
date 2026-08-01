"""Reconcile a fresh v3 reclassification against the assignment workbook.

Run after `python -m src.analysis.classify` has rewritten analyzed.json under
the v3 taxonomy. The reclassification is a genuine second opinion, not a label
rename -- but it does not get the last word:

  * Where the model agrees with the workbook, the assignment stands.
  * Where it disagrees, the WORKBOOK wins and the record is flagged for human
    review. A disagreement is information, and silently taking either side
    would throw it away. Flagging is what turns it into a queue.
  * Relevance is pinned to the workbook the same way. A record the model newly
    considers out of scope would otherwise change the 185/142 split that every
    downstream figure and test depends on.

topic_tags are restored here too. classify.py rebuilds analyzed.json from the
model's output, and the model does not emit tags -- the former v2.1
subcategory is knowledge the workbook has and the model would only guess at.

    python -m scripts.reconcile_v3 <workbook.xlsx> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models.taxonomy import TAXONOMY_VERSION  # noqa: E402

ANALYZED = ROOT / "data" / "processed" / "analyzed.json"
REVIEW_STATUS_FLAG = "Recommended - review during v3 rerun"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path, default=None,
                        help="write the per-record disagreement list here")
    args = parser.parse_args()

    wb_all = pd.read_excel(args.workbook, sheet_name="All Records")
    wb_rel = pd.read_excel(args.workbook, sheet_name="Relevant Assignments")

    relevant_by_id = {str(r["feedback_id"]): r for _, r in wb_rel.iterrows()}
    scope_by_id = {str(r["feedback_id"]): (str(r["is_relevant"]).strip().lower() == "yes")
                   for _, r in wb_all.iterrows()}

    data = json.loads(ANALYZED.read_text(encoding="utf-8"))
    records = data["records"]

    stats = Counter()
    disagreements: list[dict] = []

    for record in records:
        fid = str(record["feedback_id"])
        expected_relevant = scope_by_id.get(fid)

        if expected_relevant is None:
            stats["not_in_workbook"] += 1
            continue

        # --- relevance -----------------------------------------------------
        if bool(record.get("is_relevant")) != expected_relevant:
            stats["relevance_disagreement"] += 1
            disagreements.append({
                "feedback_id": fid, "field": "is_relevant",
                "model": bool(record.get("is_relevant")),
                "workbook": expected_relevant,
                "title": record.get("title", "")[:80],
            })
            record["is_relevant"] = expected_relevant
            record["needs_human_review"] = True

        if not expected_relevant:
            stats["out_of_scope"] += 1
            record["primary_taxonomy_category"] = None
            record["primary_taxonomy_subcategory"] = None
            record["secondary_assignments"] = []
            record["secondary_categories"] = []
            record["secondary_subcategories"] = []
            record["problem_type"] = None
            record["journey_stage"] = None
            record["topic_tags"] = []
            continue

        stats["relevant"] += 1
        row = relevant_by_id[fid]
        wb_cat = str(row["recommended_category_v3"])
        wb_sub = str(row["recommended_subcategory_v3"])
        got_cat = record.get("primary_taxonomy_category")
        got_sub = record.get("primary_taxonomy_subcategory")

        if got_sub == wb_sub and got_cat == wb_cat:
            stats["agreed"] += 1
        else:
            stats["taxonomy_disagreement"] += 1
            disagreements.append({
                "feedback_id": fid, "field": "taxonomy",
                "model": f"{got_cat} / {got_sub}",
                "workbook": f"{wb_cat} / {wb_sub}",
                "title": record.get("title", "")[:80],
            })
            record["primary_taxonomy_category"] = wb_cat
            record["primary_taxonomy_subcategory"] = wb_sub
            record["needs_human_review"] = True

        # The workbook's review flag survives a run that happened to agree.
        if str(row.get("assignment_review_status", "")) == REVIEW_STATUS_FLAG:
            record["needs_human_review"] = True
            stats["workbook_review_flag"] += 1

        # Tags the model never produced.
        former = row.get("current_subcategory_v2.1")
        tags: list[str] = []
        for tag in (former, row.get("topic_tag")):
            tag = "" if tag is None or pd.isna(tag) else str(tag).strip()
            if tag and tag != wb_sub and tag not in tags:
                tags.append(tag)
        record["topic_tags"] = tags

    meta = data.setdefault("meta", {})
    meta["taxonomy_version"] = TAXONOMY_VERSION
    meta["reconciled_against_workbook"] = args.workbook.name
    meta["taxonomy_disagreements"] = stats["taxonomy_disagreement"]
    meta["relevance_disagreements"] = stats["relevance_disagreement"]
    meta["records_relevant"] = stats["relevant"]
    meta["records_irrelevant"] = stats["out_of_scope"]

    total_rel = stats["relevant"] or 1
    print(f"records                : {len(records)}")
    print(f"relevant               : {stats['relevant']}")
    print(f"out of scope           : {stats['out_of_scope']}")
    print(f"agreed with workbook   : {stats['agreed']} "
          f"({stats['agreed'] / total_rel:.1%})")
    print(f"taxonomy disagreements : {stats['taxonomy_disagreement']} (workbook kept, flagged)")
    print(f"relevance disagreements: {stats['relevance_disagreement']} (workbook kept, flagged)")
    print(f"not in workbook        : {stats['not_in_workbook']}")
    print(f"flagged for review     : "
          f"{sum(1 for r in records if r.get('needs_human_review'))}")

    if args.report and disagreements:
        args.report.write_text(
            json.dumps(disagreements, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote {len(disagreements)} disagreements to {args.report}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    ANALYZED.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {ANALYZED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
