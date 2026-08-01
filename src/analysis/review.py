"""What "needs human review" means, and the reviewer's verdicts behind it.

One rule, and it is the only thing that decides the flag:

    needs_human_review = confidence < THRESHOLD

The flag used to be a boolean carrying three unrelated meanings -- the
classifier's own confidence, a disagreement between the classifier and the v3
assignment workbook, and a row the workbook itself had marked for a second
look. A card could then read "Confidence 0.85" beside "Needs human review" and
look like the app contradicting itself.

59 previously flagged records were read by a reviewer and given a confidence
of their own. For those records `confidence` in analyzed.json is now the
reviewer's number, not the classifier's -- the field keeps its name and its
place on the card, "Model confidence", because from the reader's point of
view it is still the single number that says how sure the app is; only who
supplied it changed. Every other record keeps the classifier's original
score untouched.

The verdicts live in their own file rather than in analyzed.json, for the
same reason overrides do: analyzed.json is regenerated, and a judgement that
only exists inside a generated file is a judgement that gets overwritten.
"""

from __future__ import annotations

import json
from pathlib import Path

ADJUDICATION_FILE = (Path(__file__).resolve().parents[2]
                     / "data" / "processed" / "review_adjudication.json")

# Also the classifier's own cutoff for flagging a record, so one number is
# read on one scale everywhere it appears.
THRESHOLD = 0.70

FLAG_FIELD = "needs_human_review"
CONFIDENCE_FIELD = "confidence"
REVIEWED_FIELD = "human_reviewed"


def load_adjudications(path: Path | None = None) -> dict[str, dict]:
    """Every recorded verdict, keyed by feedback_id.

    A missing or unreadable file means no verdicts, not a crash: the app has
    to start on a fresh checkout, and a corrupt file should cost the
    reasoning, not the dashboard.
    """
    target = path or ADJUDICATION_FILE
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    verdicts = data.get("adjudications")
    return verdicts if isinstance(verdicts, dict) else {}


def apply_adjudications(records: list[dict],
                        adjudications: dict[str, dict] | None = None) -> dict:
    """Substitute the reviewer's confidence into reviewed records, then flag
    every record -- reviewed or not -- by the one rule: confidence < THRESHOLD.
    """
    if adjudications is None:
        adjudications = load_adjudications()

    counts = {"reviewed": 0, "flagged": 0}
    for record in records:
        verdict = adjudications.get(str(record.get("feedback_id")))
        if verdict is not None:
            record[CONFIDENCE_FIELD] = float(verdict["confidence"])
            record[REVIEWED_FIELD] = True
            counts["reviewed"] += 1
        else:
            record[REVIEWED_FIELD] = False

        flagged = float(record.get(CONFIDENCE_FIELD) or 1.0) < THRESHOLD
        record[FLAG_FIELD] = flagged
        record.pop("review_reasons", None)
        record.pop("review_confidence", None)
        if flagged:
            counts["flagged"] += 1

    return counts
