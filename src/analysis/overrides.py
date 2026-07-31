"""Human corrections to the model's classification.

analyzed.json is never rewritten. A correction is recorded here as a separate
layer keyed by feedback_id, storing what the model said alongside what the
reviewer changed it to, so the original classification stays auditable and any
edit can be traced or undone. Overwriting the model's output in place would
destroy the only record of what it actually produced -- which is the thing the
evaluation section reports on.

Only the four labels a reviewer can judge by reading the feedback are editable:
category, subcategory, problem type and journey stage. Severity, confidence and
the evidence quote are left alone -- severity and confidence are the model's own
judgement, and the quote belongs to the source.

Every write is validated against the taxonomy before it lands. A subcategory
that does not belong to its category, or a stage that is not a stage, would
break the charts and the grouping silently, so it is rejected loudly instead.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..models.taxonomy import (
    CATEGORY_NAMES,
    PROBLEM_TYPE_NAMES,
    STAGE_NAMES,
    SUBCATEGORY_NAMES_BY_CATEGORY,
)

OVERRIDES_FILE = (Path(__file__).resolve().parents[2]
                  / "data" / "processed" / "overrides.json")

CATEGORY_FIELD = "primary_taxonomy_category"
SUBCATEGORY_FIELD = "primary_taxonomy_subcategory"
PROBLEM_FIELD = "problem_type"
STAGE_FIELD = "journey_stage"

# The order here is the order the editor shows them in: category first, because
# it constrains which subcategories are valid.
EDITABLE_FIELDS = (CATEGORY_FIELD, SUBCATEGORY_FIELD, PROBLEM_FIELD, STAGE_FIELD)

FIELD_LABELS = {
    CATEGORY_FIELD: "Category",
    SUBCATEGORY_FIELD: "Subcategory",
    PROBLEM_FIELD: "Problem type",
    STAGE_FIELD: "Journey stage",
}

# Marks a record whose labels a person changed. Rendered as a badge: a reader
# has to be able to tell a human label from a model one.
EDITED_FLAG = "manually_edited"


def validate(values: dict) -> str | None:
    """Return an error message, or None when every value is a legal label."""
    category = values.get(CATEGORY_FIELD)
    if category not in CATEGORY_NAMES:
        return f"Unknown category: {category!r}"

    subcategory = values.get(SUBCATEGORY_FIELD)
    if subcategory not in SUBCATEGORY_NAMES_BY_CATEGORY.get(category, ()):
        return f"{subcategory!r} is not a subcategory of {category!r}"

    problem = values.get(PROBLEM_FIELD)
    if problem not in PROBLEM_TYPE_NAMES:
        return f"Unknown problem type: {problem!r}"

    stage = values.get(STAGE_FIELD)
    if stage not in STAGE_NAMES:
        return f"Unknown journey stage: {stage!r}"

    return None


def load_overrides(path: Path | None = None) -> dict[str, dict]:
    """Every recorded correction, keyed by feedback_id.

    A missing or unreadable file means no corrections, not a crash: the app
    must still start on a fresh checkout, and a corrupt overrides file should
    cost the reader their edits, not the whole dashboard.
    """
    target = path or OVERRIDES_FILE
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    edits = data.get("overrides")
    return edits if isinstance(edits, dict) else {}


def _write(overrides: dict[str, dict], path: Path | None = None) -> None:
    target = path or OVERRIDES_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"overrides": overrides}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def save_override(feedback_id: str, values: dict, original: dict,
                  path: Path | None = None) -> str | None:
    """Record one correction. Returns an error message, or None on success.

    `original` is what the model produced. It is stored beside the correction
    rather than derived later, because the point of keeping it is to survive a
    reclassification that would change what "original" means.
    """
    error = validate(values)
    if error:
        return error

    overrides = load_overrides(path)
    overrides[str(feedback_id)] = {
        "values": {field: values[field] for field in EDITABLE_FIELDS},
        "model_values": {field: original.get(field) for field in EDITABLE_FIELDS},
        "edited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _write(overrides, path)
    return None


def clear_override(feedback_id: str, path: Path | None = None) -> None:
    """Drop one correction, restoring the model's own labels."""
    overrides = load_overrides(path)
    if overrides.pop(str(feedback_id), None) is not None:
        _write(overrides, path)


def apply_overrides(frame: pd.DataFrame,
                    overrides: dict[str, dict] | None = None) -> pd.DataFrame:
    """Layer corrections over the classified records.

    Applied to the whole frame before anything derives from it, so a corrected
    label reaches the charts, the filters, the product-action grouping and the
    assistant together. Applying it later, per view, is how the same record
    ends up counted under two different categories on one screen.
    """
    if overrides is None:
        overrides = load_overrides()

    out = frame.copy()
    out[EDITED_FLAG] = False
    if not overrides or "feedback_id" not in out.columns:
        return out

    ids = out["feedback_id"].astype(str)
    for feedback_id, entry in overrides.items():
        mask = ids == str(feedback_id)
        if not mask.any():
            # A correction for a record that no longer exists -- a stale entry
            # from before a reclassification. Ignored, never invented back in.
            continue
        values = entry.get("values") or {}
        if validate(values) is not None:
            # Hand-edited file, or one written by an older taxonomy. The
            # model's own label is the safer thing to show.
            continue
        for field in EDITABLE_FIELDS:
            out.loc[mask, field] = values[field]
        out.loc[mask, EDITED_FLAG] = True

    return out
