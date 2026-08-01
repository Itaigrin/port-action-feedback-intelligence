"""Stamp the audited product-action grouping onto the classified records.

Product actions were previously derived only by clustering the model's
`suggested_product_action` text within a subcategory. That is a reasonable
automatic default, but it produced 172 groups from 185 records -- almost one
recommendation per record, which is a list, not a set of recommendations.

An analyst regrouped them to 75 and that proposal was independently audited
(57.6% of multi-record merges approved as-is; 15 required splitting because
they bundled separate product decisions). The audited result is 101 actions,
and this writes it onto each record as `curated_action_id`.

Grouping only. Nothing else about a record is touched: not the text, not the
taxonomy, not severity, polarity, persona or lifecycle.

Records with no curated assignment keep the automatic clustering, so feedback
collected after this mapping was written still groups sensibly instead of
vanishing from the ranking.

    python -m scripts.apply_curated_actions [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
ANALYZED = PROC / "analyzed.json"
CURATED = PROC / "product_actions_curated.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    curated = json.loads(CURATED.read_text(encoding="utf-8"))["actions"]
    assignment: dict[str, tuple[str, str]] = {}
    for action_id, meta in curated.items():
        for fid in meta["feedback_ids"]:
            if fid in assignment:
                print(f"FATAL: {fid} assigned to two actions")
                return 1
            assignment[fid] = (action_id, meta["title"])

    data = json.loads(ANALYZED.read_text(encoding="utf-8"))
    records = data["records"]

    stamped = cleared = unassigned = 0
    for record in records:
        fid = str(record["feedback_id"])
        if not record.get("is_relevant"):
            # Out-of-scope records carry no product action, exactly as they
            # carry no taxonomy -- they must not be able to reach a ranking.
            record.pop("curated_action_id", None)
            record.pop("curated_action_title", None)
            cleared += 1
            continue
        found = assignment.get(fid)
        if found is None:
            record.pop("curated_action_id", None)
            record.pop("curated_action_title", None)
            unassigned += 1
            continue
        record["curated_action_id"], record["curated_action_title"] = found
        stamped += 1

    data.setdefault("meta", {})["curated_product_actions"] = {
        "source": CURATED.name,
        "actions": len(curated),
        "records_assigned": stamped,
        "records_unassigned": unassigned,
    }

    print(f"records            : {len(records)}")
    print(f"curated assignment : {stamped}")
    print(f"relevant, no action: {unassigned}")
    print(f"out of scope       : {cleared}")
    print(f"distinct actions   : {len(curated)}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    ANALYZED.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"\nwrote {ANALYZED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
