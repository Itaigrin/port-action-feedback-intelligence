"""What "needs human review" means, and the reviewer's verdicts that set it.

The flag used to be a boolean carrying three unrelated meanings: the
classifier's own confidence, a disagreement between the classifier and the v3
assignment workbook, and a row the workbook itself had marked for a second
look. Only the first has anything to do with confidence, so a card could read
"Confidence 0.85" beside "Needs human review" and look like the app
contradicting itself. It wasn't -- it was one field answering three questions.

Now the flag answers one question: did a reviewer, reading the record, come
away unsure it is filed correctly? Every previously flagged record was read and
given a reviewer confidence; below THRESHOLD the record stays flagged, at or
above it the flag is cleared. Nothing else can set it.

The verdicts live in their own file rather than in analyzed.json, for the same
reason overrides do: analyzed.json is regenerated, and a judgement that only
exists inside a generated file is a judgement that gets overwritten. Keeping
them separate also means the reasoning stays readable and reviewable as a
single document, and re-running reconciliation cannot quietly reintroduce the
old three-meanings-in-one-boolean behaviour.

A verdict is recorded for records that were cleared too, not only for the ones
still flagged. "Nobody looked at this" and "somebody looked and was sure" are
different states, and dropping the second loses the audit trail for 42 of the
59 decisions.
"""

from __future__ import annotations

import json
from pathlib import Path

ADJUDICATION_FILE = (Path(__file__).resolve().parents[2]
                     / "data" / "processed" / "review_adjudication.json")

# At or above this the reviewer was sure enough to clear the record. It is the
# same 0.70 the classifier's own low-confidence cut used, so the two numbers on
# a card are read on one scale.
THRESHOLD = 0.70

FLAG_FIELD = "needs_human_review"
REASONS_FIELD = "review_reasons"
CONFIDENCE_FIELD = "review_confidence"


def load_adjudications(path: Path | None = None) -> dict[str, dict]:
    """Every recorded verdict, keyed by feedback_id.

    A missing or unreadable file means no verdicts, not a crash: the app has to
    start on a fresh checkout, and a corrupt file should cost the reasoning,
    not the dashboard.
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
    """Set the review flag on every record from the reviewer's verdicts alone.

    Records with no verdict are cleared rather than left as they were. A record
    nobody ruled on carrying a flag nobody can explain is exactly the state
    this replaces -- and it is how the twelve out-of-scope records ended up
    flagged with no reason attached to them.
    """
    if adjudications is None:
        adjudications = load_adjudications()

    counts = {"flagged": 0, "cleared": 0, "unjudged_cleared": 0}
    for record in records:
        verdict = adjudications.get(str(record.get("feedback_id")))
        if not verdict:
            record[FLAG_FIELD] = False
            record[REASONS_FIELD] = []
            record.pop(CONFIDENCE_FIELD, None)
            counts["unjudged_cleared"] += 1
            continue

        confidence = float(verdict.get("confidence", 0.0))
        note = str(verdict.get("note", "")).strip()
        record[CONFIDENCE_FIELD] = confidence
        if confidence < THRESHOLD:
            record[FLAG_FIELD] = True
            record[REASONS_FIELD] = [note] if note else []
            counts["flagged"] += 1
        else:
            record[FLAG_FIELD] = False
            record[REASONS_FIELD] = []
            counts["cleared"] += 1

    return counts
