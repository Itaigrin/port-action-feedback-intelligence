"""Reviewer corrections to the model's labels.

The contract these hold: a correction never reaches the dashboard unless it is
a legal taxonomy label, the model's own output is never overwritten, and an
edit reaches everything derived from the records at once.

All offline -- the module is plain JSON and pandas.

    python -m pytest tests/test_overrides.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis import overrides  # noqa: E402
from src.models.taxonomy import (  # noqa: E402
    CATEGORY_NAMES,
    PROBLEM_TYPE_NAMES,
    STAGE_NAMES,
    SUBCATEGORY_NAMES_BY_CATEGORY,
)

APP = (ROOT / "app.py").read_text(encoding="utf-8")
RENDER_SRC = (ROOT / "src" / "ui" / "render.py").read_text(encoding="utf-8")


@pytest.fixture
def store(tmp_path: Path) -> Path:
    """An overrides file of our own, never the repo's."""
    return tmp_path / "overrides.json"


@pytest.fixture
def legal() -> dict:
    category = CATEGORY_NAMES[0]
    return {
        overrides.CATEGORY_FIELD: category,
        overrides.SUBCATEGORY_FIELD: SUBCATEGORY_NAMES_BY_CATEGORY[category][0],
        overrides.PROBLEM_FIELD: PROBLEM_TYPE_NAMES[0],
        overrides.STAGE_FIELD: STAGE_NAMES[0],
    }


@pytest.fixture
def frame() -> pd.DataFrame:
    category = CATEGORY_NAMES[1]
    return pd.DataFrame([
        {"feedback_id": "rec-1",
         overrides.CATEGORY_FIELD: category,
         overrides.SUBCATEGORY_FIELD: SUBCATEGORY_NAMES_BY_CATEGORY[category][0],
         overrides.PROBLEM_FIELD: PROBLEM_TYPE_NAMES[1],
         overrides.STAGE_FIELD: STAGE_NAMES[1]},
        {"feedback_id": "rec-2",
         overrides.CATEGORY_FIELD: category,
         overrides.SUBCATEGORY_FIELD: SUBCATEGORY_NAMES_BY_CATEGORY[category][0],
         overrides.PROBLEM_FIELD: PROBLEM_TYPE_NAMES[1],
         overrides.STAGE_FIELD: STAGE_NAMES[1]},
    ])


# --- validation ------------------------------------------------------------
def test_every_editable_field_is_a_real_column(frame):
    for field in overrides.EDITABLE_FIELDS:
        assert field in frame.columns


def test_a_legal_set_of_labels_validates(legal):
    assert overrides.validate(legal) is None


def test_an_unknown_category_is_rejected(legal):
    assert overrides.validate({**legal,
                               overrides.CATEGORY_FIELD: "Not a category"})


def test_a_subcategory_from_another_category_is_rejected(legal):
    """The pairing is the point: a valid name under the wrong parent is wrong.

    This is the failure that would not announce itself -- the label renders
    fine and the charts quietly disagree with the taxonomy.
    """
    other = next(c for c in CATEGORY_NAMES if c != legal[overrides.CATEGORY_FIELD])
    stray = SUBCATEGORY_NAMES_BY_CATEGORY[other][0]
    assert stray not in SUBCATEGORY_NAMES_BY_CATEGORY[legal[overrides.CATEGORY_FIELD]]
    assert overrides.validate({**legal, overrides.SUBCATEGORY_FIELD: stray})


def test_an_unknown_problem_type_is_rejected(legal):
    assert overrides.validate({**legal, overrides.PROBLEM_FIELD: "Vibes"})


def test_an_unknown_stage_is_rejected(legal):
    assert overrides.validate({**legal, overrides.STAGE_FIELD: "Later"})


def test_a_missing_field_is_rejected(legal):
    for field in overrides.EDITABLE_FIELDS:
        partial = {k: v for k, v in legal.items() if k != field}
        assert overrides.validate(partial), field


# --- persistence -----------------------------------------------------------
def test_saving_then_loading_round_trips(store, legal):
    assert overrides.save_override("rec-1", legal, original={}, path=store) is None
    assert overrides.load_overrides(store)["rec-1"]["values"] == legal


def test_an_illegal_save_is_refused_and_writes_nothing(store, legal):
    error = overrides.save_override(
        "rec-1", {**legal, overrides.STAGE_FIELD: "Later"},
        original={}, path=store)
    assert error
    assert not store.exists()


def test_the_model_values_are_stored_beside_the_correction(store, legal):
    original = {field: "model-said" for field in overrides.EDITABLE_FIELDS}
    overrides.save_override("rec-1", legal, original=original, path=store)
    saved = overrides.load_overrides(store)["rec-1"]
    assert saved["model_values"] == original
    assert saved["values"] == legal
    assert saved["edited_at"]


def test_clearing_removes_only_that_record(store, legal):
    overrides.save_override("rec-1", legal, original={}, path=store)
    overrides.save_override("rec-2", legal, original={}, path=store)
    overrides.clear_override("rec-1", path=store)
    assert set(overrides.load_overrides(store)) == {"rec-2"}


def test_a_missing_file_reads_as_no_corrections(tmp_path):
    assert overrides.load_overrides(tmp_path / "nothing.json") == {}


def test_a_corrupt_file_costs_the_edits_not_the_dashboard(store):
    """The app must still start on a broken overrides file."""
    store.write_text("{not json", encoding="utf-8")
    assert overrides.load_overrides(store) == {}


# --- applying --------------------------------------------------------------
def test_applying_replaces_every_edited_field(frame, legal):
    out = overrides.apply_overrides(frame, {"rec-1": {"values": legal}})
    row = out[out["feedback_id"] == "rec-1"].iloc[0]
    for field, value in legal.items():
        assert row[field] == value


def test_applying_leaves_other_records_alone(frame, legal):
    before = frame[frame["feedback_id"] == "rec-2"].iloc[0].to_dict()
    out = overrides.apply_overrides(frame, {"rec-1": {"values": legal}})
    after = out[out["feedback_id"] == "rec-2"].iloc[0]
    for field in overrides.EDITABLE_FIELDS:
        assert after[field] == before[field]
    assert not after[overrides.EDITED_FLAG]


def test_an_edited_record_is_flagged(frame, legal):
    out = overrides.apply_overrides(frame, {"rec-1": {"values": legal}})
    assert out[out["feedback_id"] == "rec-1"].iloc[0][overrides.EDITED_FLAG]


def test_the_flag_exists_even_with_no_corrections(frame):
    out = overrides.apply_overrides(frame, {})
    assert overrides.EDITED_FLAG in out.columns
    assert not out[overrides.EDITED_FLAG].any()


def test_applying_does_not_mutate_the_input(frame, legal):
    before = frame.copy()
    overrides.apply_overrides(frame, {"rec-1": {"values": legal}})
    pd.testing.assert_frame_equal(frame, before)


def test_a_correction_for_a_missing_record_is_ignored(frame, legal):
    """A stale entry from before a reclassification must not invent a row."""
    out = overrides.apply_overrides(frame, {"gone": {"values": legal}})
    assert list(out["feedback_id"]) == ["rec-1", "rec-2"]
    assert not out[overrides.EDITED_FLAG].any()


def test_an_illegal_stored_correction_falls_back_to_the_model(frame, legal):
    """A hand-edited file must not push an illegal label into the charts."""
    bad = {**legal, overrides.SUBCATEGORY_FIELD: "Not a subcategory"}
    before = frame[frame["feedback_id"] == "rec-1"].iloc[0].to_dict()
    out = overrides.apply_overrides(frame, {"rec-1": {"values": bad}})
    row = out[out["feedback_id"] == "rec-1"].iloc[0]
    for field in overrides.EDITABLE_FIELDS:
        assert row[field] == before[field]
    assert not row[overrides.EDITED_FLAG]


# --- wiring ----------------------------------------------------------------
def test_corrections_are_applied_before_anything_derives_from_the_records():
    """Order is the contract: charts, filters, grouping and the assistant all
    read from the same frame, so the layer has to land before rel is built."""
    assert APP.index("overrides.apply_overrides(df)") < APP.index(
        'rel = df[df["is_relevant"]].copy()')


def test_corrections_are_applied_outside_the_cache():
    """Inside load() the cache would freeze them until a restart."""
    load_body = APP[APP.index("def load()"):APP.index("try:\n    df, amet = load()")]
    assert "apply_overrides" not in load_body


def test_the_editor_only_offers_the_four_judgeable_labels():
    """Severity, confidence and the quote are not a reviewer's to rewrite.

    Counts the widgets rather than searching for field names: the prose above
    the editor names the withheld fields to explain why they are withheld, and
    a bare substring check cannot tell an explanation from an input.
    """
    editor = APP[APP.index("def _render_editor("):APP.index("def render_hidden_nav(")]
    assert editor.count("st.selectbox(") == len(overrides.EDITABLE_FIELDS)
    for offered in ("Category", "Subcategory", "Problem type", "Journey stage"):
        assert f'"{offered}"' in editor, offered
    for widget in ("st.slider(", "st.text_input(", "st.text_area(",
                   "st.number_input("):
        assert widget not in editor, widget
    # Nothing outside the four fields is read off the record into an input.
    for withheld in ("severity", "confidence", "evidence_excerpt"):
        assert f'record["{withheld}"]' not in editor, withheld


def test_the_editor_saves_through_validation():
    editor = APP[APP.index("def _render_editor("):APP.index("def render_hidden_nav(")]
    assert "overrides.save_override(" in editor
    assert "st.error(error)" in editor


def test_the_subcategory_list_follows_the_chosen_category():
    """Otherwise the editor can save a pairing the taxonomy does not allow."""
    editor = APP[APP.index("def _render_editor("):APP.index("def render_hidden_nav(")]
    assert "SUBCATEGORY_NAMES_BY_CATEGORY[category]" in editor


def test_every_edit_proxy_has_a_button_behind_it():
    """The proxies are keyed by position, so the buttons must be built from the
    same list in the same order."""
    assert "NAV_EDIT" in RENDER_SRC
    assert f'{{NAV_EDIT}}_{{index}}' in RENDER_SRC
    assert "for index, card in enumerate(cards)" in APP
    assert "on_click=_open_editor" in APP


def test_an_edited_record_says_so_on_the_card():
    """A reader has to be able to tell a human label from a model one."""
    assert "manually_edited" in RENDER_SRC
    assert "Labels edited by a" in RENDER_SRC


def test_the_editor_closes_when_its_record_leaves_the_view():
    assert "_close_editor()" in APP
    assert "on_dismiss=_close_editor" in APP, "the native X must clear the state"
