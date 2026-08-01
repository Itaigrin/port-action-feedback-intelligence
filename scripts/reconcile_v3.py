"""Reconcile a v3 reclassification against the assignment workbook.

Reads the classification **cache**, not a rewritten analyzed.json.

That is deliberate. `python -m src.analysis.classify` overwrites analyzed.json
with whatever it managed to process, so a run that dies partway -- an expired
key, an exhausted balance, a dropped connection -- silently truncates the
dataset to the records it reached. That happened here: a run stopped at 290
of 327 and left analyzed.json holding 290 records. Reading the cache instead
means a partial run degrades to partial *information* rather than to data
loss, and reconciling can be re-run any time without another API call.

What it does with a second opinion:

  * Agreement leaves the assignment alone.
  * Disagreement keeps the WORKBOOK and flags the record for human review.
    Silently taking either side would throw away the one thing a
    disagreement tells you.
  * Relevance is pinned to the workbook the same way, so a model that
    re-scopes a record cannot move the 185/142 split every figure rests on.
  * Records with no cached classification are counted and named, never
    quietly treated as agreeing.

    python -m scripts.reconcile_v3 <workbook.xlsx> [--dry-run] [--report out.json]
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

from src.analysis.classify import DEFAULT_MODEL, cache_key  # noqa: E402
from src.models.prompt import source_text  # noqa: E402
from src.models.taxonomy import TAXONOMY_VERSION  # noqa: E402

PROC = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "cache"
ANALYZED = PROC / "analyzed.json"
CLEAN = PROC / "feedback_clean.csv"

REVIEW_STATUS_FLAG = "Recommended - review during v3 rerun"


def _cached_classification(title: str, description: str | None, model: str):
    """The cached v3 classification for one record, or None."""
    src = source_text(title, description)
    path = CACHE / f"{cache_key(src, model)}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))["classification"]
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report", type=Path,
                        default=PROC / "v3_reconciliation.json")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    all_rows = pd.read_excel(args.workbook, sheet_name="All Records")
    rel_rows = pd.read_excel(args.workbook, sheet_name="Relevant Assignments")
    scope = {str(r["feedback_id"]): str(r["is_relevant"]).strip().lower() == "yes"
             for _, r in all_rows.iterrows()}
    assignment = {str(r["feedback_id"]): r for _, r in rel_rows.iterrows()}

    clean = pd.read_csv(CLEAN)
    source = {str(r.feedback_id): (str(r.title),
                                   None if pd.isna(r.description) else str(r.description))
              for r in clean.itertuples(index=False)}

    data = json.loads(ANALYZED.read_text(encoding="utf-8"))
    records = data["records"]

    stats = Counter()
    disagreements: list[dict] = []
    unclassified: list[str] = []

    for record in records:
        fid = str(record["feedback_id"])
        want_relevant = scope.get(fid)
        if want_relevant is None:
            stats["not_in_workbook"] += 1
            continue

        title, description = source.get(fid, (record.get("title", ""), None))
        got = _cached_classification(title, description, args.model)
        if got is None:
            stats["no_cached_classification"] += 1
            unclassified.append(fid)
            continue
        stats["compared"] += 1

        # --- relevance -----------------------------------------------------
        if bool(got.get("is_relevant")) != want_relevant:
            stats["relevance_disagreement"] += 1
            disagreements.append({
                "feedback_id": fid, "field": "is_relevant",
                "model": bool(got.get("is_relevant")), "workbook": want_relevant,
                "title": str(record.get("title", ""))[:90],
            })
            record["needs_human_review"] = True
            continue

        if not want_relevant:
            stats["out_of_scope_agreed"] += 1
            continue

        row = assignment[fid]
        want = (str(row["recommended_category_v3"]),
                str(row["recommended_subcategory_v3"]))
        mine = (got.get("primary_taxonomy_category"),
                got.get("primary_taxonomy_subcategory"))

        if mine == want:
            stats["taxonomy_agreed"] += 1
        else:
            stats["taxonomy_disagreement"] += 1
            disagreements.append({
                "feedback_id": fid, "field": "taxonomy",
                "model": f"{mine[0]} / {mine[1]}",
                "workbook": f"{want[0]} / {want[1]}",
                "title": str(record.get("title", ""))[:90],
            })
            # The workbook already sits on the record. Only the flag changes.
            record["needs_human_review"] = True

    in_scope = stats["taxonomy_agreed"] + stats["taxonomy_disagreement"]
    complete = not unclassified

    meta = data.setdefault("meta", {})
    meta["taxonomy_version"] = TAXONOMY_VERSION
    meta["v3_reconciliation"] = {
        "workbook": args.workbook.name,
        "complete": complete,
        "records_compared": stats["compared"],
        "records_without_classification": stats["no_cached_classification"],
        "taxonomy_agreed": stats["taxonomy_agreed"],
        "taxonomy_disagreements": stats["taxonomy_disagreement"],
        "relevance_disagreements": stats["relevance_disagreement"],
    }

    print(f"records in dataset      : {len(records)}")
    print(f"compared against model  : {stats['compared']}")
    print(f"no cached classification: {stats['no_cached_classification']}")
    print(f"out-of-scope agreed     : {stats['out_of_scope_agreed']}")
    print(f"taxonomy agreed         : {stats['taxonomy_agreed']}"
          + (f" ({stats['taxonomy_agreed'] / in_scope:.1%})" if in_scope else ""))
    print(f"taxonomy disagreements  : {stats['taxonomy_disagreement']} "
          f"(workbook kept, flagged)")
    print(f"relevance disagreements : {stats['relevance_disagreement']} "
          f"(workbook kept, flagged)")
    print(f"flagged for review now  : "
          f"{sum(1 for r in records if r.get('needs_human_review'))}")
    if not complete:
        print(f"\n!! INCOMPLETE: {len(unclassified)} records were never classified.")
        print("   Re-run `python -m src.analysis.classify` to fill the gap; the "
              "cache means only the missing records cost a call.")

    args.report.write_text(json.dumps({
        "complete": complete,
        "stats": dict(stats),
        "unclassified_feedback_ids": unclassified,
        "disagreements": disagreements,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {args.report.relative_to(ROOT)}")

    if args.dry_run:
        print("--dry-run: analyzed.json not written")
        return 0

    ANALYZED.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"wrote {ANALYZED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
