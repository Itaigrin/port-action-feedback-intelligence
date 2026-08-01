"""The v2.1 -> v3.0 taxonomy migration contract.

These assert the migration actually happened and stayed honest: that the
consolidated taxonomy is the one shape everything reads, that every existing
record landed where the assignment workbook says it should, that out-of-scope
feedback still cannot reach a figure, and that no retired v2.1 name survives
anywhere a reader could see it.

The workbook is the authority. Where it is present these compare against it
directly rather than against a number retyped into a test, so a test cannot
agree with a migration that drifted from its own source.

All offline: no network, no API key, no LLM calls.

    python -m pytest tests/test_taxonomy_v3_migration.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
APP = (ROOT / "app.py").read_text(encoding="utf-8")

EXPECTED_TOTAL = 327
EXPECTED_RELEVANT = 185
EXPECTED_OUT_OF_SCOPE = 142
EXPECTED_CATEGORIES = 11
EXPECTED_CORE_SUBCATEGORIES = 30
EXPECTED_FORMER_SUBCATEGORIES = 63


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))["records"]


@pytest.fixture(scope="module")
def relevant(records) -> list[dict]:
    return [r for r in records if r["is_relevant"]]


@pytest.fixture(scope="module")
def core_subcategories() -> set[str]:
    from src.models.taxonomy import ALL_SUBCATEGORY_NAMES

    return set(ALL_SUBCATEGORY_NAMES)


@pytest.fixture(scope="module")
def former_subcategories() -> set[str]:
    from src.models.taxonomy import SUBCATEGORY_MIGRATION

    return set(SUBCATEGORY_MIGRATION)


# --- record counts ---------------------------------------------------------
def test_record_counts_are_unchanged_by_the_migration(records, relevant):
    """A taxonomy change must not add, drop or re-scope a single record."""
    assert len(records) == EXPECTED_TOTAL
    assert len(relevant) == EXPECTED_RELEVANT
    assert len(records) - len(relevant) == EXPECTED_OUT_OF_SCOPE


# --- taxonomy shape --------------------------------------------------------
def test_taxonomy_is_eleven_categories_and_thirty_core_subcategories(core_subcategories):
    from src.models.taxonomy import CATEGORY_NAMES, TAXONOMY_VERSION

    assert TAXONOMY_VERSION == "v3.0"
    assert len(CATEGORY_NAMES) == EXPECTED_CATEGORIES
    assert len(core_subcategories) == EXPECTED_CORE_SUBCATEGORIES


def test_every_former_subcategory_maps_somewhere(former_subcategories,
                                                 core_subcategories):
    from src.models.taxonomy import SUBCATEGORY_MIGRATION

    assert len(former_subcategories) == EXPECTED_FORMER_SUBCATEGORIES
    for former, destination in SUBCATEGORY_MIGRATION.items():
        assert destination in core_subcategories, (
            f"{former!r} maps to {destination!r}, which is not a core subcategory")


def test_the_fallback_is_reachable_but_is_not_a_core_group():
    """It must exist for unmatched feedback without inflating the thirty."""
    from src.models.taxonomy import (
        ALL_SUBCATEGORY_NAMES,
        ASSIGNABLE_SUBCATEGORY_NAMES,
        FALLBACK_SUBCATEGORY,
        is_valid_pair,
    )

    assert FALLBACK_SUBCATEGORY not in ALL_SUBCATEGORY_NAMES
    assert FALLBACK_SUBCATEGORY in ASSIGNABLE_SUBCATEGORY_NAMES
    # Valid under any real category, because "no core group fits" says nothing
    # about which product area the record belongs to.
    assert is_valid_pair("Orchestration", FALLBACK_SUBCATEGORY)
    assert not is_valid_pair("Not A Category", FALLBACK_SUBCATEGORY)


# --- assignments -----------------------------------------------------------
def test_every_relevant_record_carries_a_core_v3_assignment(relevant,
                                                            core_subcategories):
    from src.models.taxonomy import CATEGORY_FOR_SUBCATEGORY

    for record in relevant:
        sub = record["primary_taxonomy_subcategory"]
        cat = record["primary_taxonomy_category"]
        assert sub in core_subcategories, (record["feedback_id"], sub)
        assert CATEGORY_FOR_SUBCATEGORY[sub] == cat, (record["feedback_id"], cat, sub)


def test_no_record_still_carries_a_retired_subcategory(relevant,
                                                       former_subcategories,
                                                       core_subcategories):
    """A name that only existed in v2.1 must be gone from the assignment.

    Names that survived the consolidation unchanged are excluded from the
    check -- eight of the 63 kept their name, and flagging those would make
    this test impossible to satisfy.
    """
    retired = former_subcategories - core_subcategories
    for record in relevant:
        assert record["primary_taxonomy_subcategory"] not in retired, record["feedback_id"]
        for sub in record.get("secondary_subcategories") or []:
            assert sub not in retired, (record["feedback_id"], sub)


def test_relevant_assignments_match_the_workbook(relevant):
    """The workbook is the authority for where each record landed."""
    workbook = _load_workbook()
    if workbook is None:
        pytest.skip("assignment workbook not available in this checkout")

    expected = {
        str(row["feedback_id"]): (str(row["recommended_category_v3"]),
                                  str(row["recommended_subcategory_v3"]))
        for _, row in workbook.iterrows()
    }
    assert len(expected) == EXPECTED_RELEVANT

    mismatches = [
        record["feedback_id"] for record in relevant
        if (record["primary_taxonomy_category"],
            record["primary_taxonomy_subcategory"]) != expected.get(
                str(record["feedback_id"]))
    ]
    assert not mismatches, f"{len(mismatches)} records differ from the workbook"


def test_out_of_scope_records_carry_no_taxonomy_at_all(records):
    for record in records:
        if record["is_relevant"]:
            continue
        assert record["primary_taxonomy_category"] is None, record["feedback_id"]
        assert record["primary_taxonomy_subcategory"] is None, record["feedback_id"]
        assert not record.get("secondary_subcategories"), record["feedback_id"]
        assert not record.get("topic_tags"), record["feedback_id"]


# --- preserved detail ------------------------------------------------------
def test_reconciliation_state_is_recorded_honestly(records):
    """An incomplete reclassification must say so in the artifact.

    classify.py rewrites analyzed.json with whatever it managed to process,
    so a run that dies partway truncates the dataset silently -- one did,
    stopping at 290 of 327 when the API balance ran out, and left the file
    holding 290 records. Two guards came out of that: the dataset is checked
    for its full size, and the reconciliation records whether it actually
    finished rather than letting a partial run read as a complete one.
    """
    analyzed = json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))
    assert len(records) == EXPECTED_TOTAL, (
        "analyzed.json is truncated -- a classification run was interrupted")

    reconciliation = analyzed.get("meta", {}).get("v3_reconciliation")
    if reconciliation is None:
        pytest.skip("no reconciliation has been run against this dataset")

    assert "complete" in reconciliation, "completeness must be stated, not implied"
    compared = reconciliation["records_compared"]
    missing = reconciliation["records_without_classification"]
    assert compared + missing == EXPECTED_TOTAL, (
        "the reconciliation does not account for every record")
    assert reconciliation["complete"] == (missing == 0), (
        "the complete flag disagrees with the record counts behind it")


def test_agreement_is_reported_per_model_not_blended():
    """Two models classified this dataset; one rate would describe neither.

    The Anthropic run covered 290 records before its balance ran out and the
    remaining 37 were finished on DeepSeek. That seam is only survivable
    because reconciliation never lets a model overwrite the workbook -- a
    model can raise a review flag, never change an assignment -- so what has
    to be true is that the split stays visible rather than averaged away.
    """
    analyzed = json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))
    reconciliation = analyzed.get("meta", {}).get("v3_reconciliation")
    if reconciliation is None:
        pytest.skip("no reconciliation has been run against this dataset")

    by_model = reconciliation.get("by_model")
    assert by_model, "the per-model breakdown must be recorded"

    compared = sum(counts["compared"] for counts in by_model.values())
    assert compared == reconciliation["records_compared"], (
        "the per-model counts do not add up to the total compared")

    for name, counts in by_model.items():
        assert name, "every classification must name the model that produced it"
        agreed = counts.get("taxonomy_agreed", 0)
        disagreed = counts.get("taxonomy_disagreement", 0)
        oos = counts.get("out_of_scope_agreed", 0)
        relevance = counts.get("relevance_disagreement", 0)
        assert agreed + disagreed + oos + relevance == counts["compared"], (
            f"{name}: outcomes do not account for every record compared")


def test_disagreements_keep_the_workbook_and_were_reviewed(relevant):
    """A disagreement is information; resolving it silently discards it.

    It no longer forces the review flag -- that now means one thing, "a
    reviewer was unsure" (see test_review_adjudication). What must still hold
    is that no disagreement was cleared without somebody ruling on it, and
    that the workbook's label is the one that survived.
    """
    report = PROC / "v3_reconciliation.json"
    if not report.exists():
        pytest.skip("no reconciliation report in this checkout")

    from src.analysis import review
    verdicts = review.load_adjudications()

    data = json.loads(report.read_text(encoding="utf-8"))
    by_id = {str(r["feedback_id"]): r for r in relevant}
    for entry in data["disagreements"]:
        assert str(entry["feedback_id"]) in verdicts, (
            f"{entry['feedback_id']} disagreed with the model and no reviewer "
            f"ever ruled on it")
        record = by_id.get(entry["feedback_id"])
        if record is None:          # a relevance disagreement on an OOS record
            continue
        if entry["field"] == "taxonomy":
            kept = f'{record["primary_taxonomy_category"]} / ' \
                   f'{record["primary_taxonomy_subcategory"]}'
            assert kept == entry["workbook"], (
                f"{entry['feedback_id']} took the model's side over the workbook")


def test_the_former_subcategory_is_preserved_as_topic_tags(relevant):
    """Consolidation loses a group on purpose; it must not lose the detail."""
    tagged = [r for r in relevant if r.get("topic_tags")]
    assert tagged, "no record kept its former subcategory"
    # Every tag is a real former name or the workbook's own topic note, never
    # a restatement of the group the record now sits in.
    for record in tagged:
        assert record["primary_taxonomy_subcategory"] not in record["topic_tags"], \
            record["feedback_id"]


def test_records_the_workbook_marked_for_review_were_reviewed(relevant):
    """The workbook's marker is a request for a second look, not a verdict.

    So the marker must reach a reviewer -- but once one has read the record
    and said it is filed correctly, it is settled, and keeping the flag on
    would leave a warning nobody can clear.
    """
    workbook = _load_workbook()
    if workbook is None:
        pytest.skip("assignment workbook not available in this checkout")

    from src.analysis import review
    verdicts = review.load_adjudications()

    marked = {
        str(row["feedback_id"]) for _, row in workbook.iterrows()
        if str(row.get("assignment_review_status", "")).strip()
        == "Recommended - review during v3 rerun"
    }
    by_id = {str(r["feedback_id"]): r for r in relevant}
    missed = [fid for fid in marked if fid in by_id and fid not in verdicts]
    assert not missed, f"{len(missed)} workbook review rows were never reviewed"


# --- dashboard reads v3 ----------------------------------------------------
def test_dashboard_aggregations_run_on_v3_assignments(relevant, core_subcategories):
    """Whatever the charts group by must be a v3 name, not a legacy one."""
    import pandas as pd

    from src.analysis.aggregate import (
        COUNTED_STATUSES,
        product_actions,
        subcategory_table,
    )

    frame = pd.DataFrame(relevant)
    # The dashboard derives these before aggregating; subcategory_table sums
    # is_open, so building the frame without it tests nothing but the fixture.
    frame["is_open"] = frame["lifecycle_status"].isin(COUNTED_STATUSES)

    table = subcategory_table(frame)
    assert set(table["primary_taxonomy_subcategory"]) <= core_subcategories
    assert set(table["primary_taxonomy_category"]) <= set(_categories())

    actions = product_actions(frame)
    assert len(actions), "grouping produced nothing to rank"
    for names in actions["primary_categories"]:
        for name in names:
            assert name in _categories(), f"action grouped under {name!r}"


def _categories() -> tuple[str, ...]:
    from src.models.taxonomy import CATEGORY_NAMES

    return CATEGORY_NAMES


def test_no_ui_element_references_a_retired_subcategory(former_subcategories,
                                                        core_subcategories):
    """Filters, labels and reference views must not name a dead group.

    Both reference views read src.models.taxonomy rather than holding their
    own list, so this checks the app source for a hard-coded survivor.
    """
    retired = former_subcategories - core_subcategories
    render = (ROOT / "src" / "ui" / "render.py").read_text(encoding="utf-8")
    theme = (ROOT / "src" / "ui" / "theme.py").read_text(encoding="utf-8")
    for name in retired:
        for label, source in (("app.py", APP), ("render.py", render),
                              ("theme.py", theme)):
            assert name not in source, f"{label} still names retired {name!r}"


def test_both_reference_views_read_the_central_taxonomy():
    """Neither view may keep its own copy of the hierarchy.

    A duplicated list is how the guide and the classifier drift apart: the
    taxonomy changes, one of them is updated, and the other keeps teaching a
    scheme the code no longer implements.
    """
    guide = APP[APP.index("def render_guide("):]
    rail = APP[APP.index("def render_filter_panel("):APP.index("def apply_filters(")]

    # Both iterate the imported TAXONOMY dict.
    assert "TAXONOMY.items()" in guide, "the guide must iterate the central taxonomy"
    assert "TAXONOMY.items()" in rail, "the rail must iterate the central taxonomy"
    assert 'block["subcategories"]' in guide
    assert 'block["subcategories"]' in rail


def test_the_guide_does_not_print_the_use_for_list(former_subcategories,
                                                   core_subcategories):
    """`use_for` holds the v2.1 names each v3 group absorbed.

    That is genuinely useful to the classifier, which benefits from the extra
    topical phrasing, but rendering it in the guide put a list of retired
    names on screen under the heading "Use it for" -- teaching a reader a
    scheme the code no longer implements. Caught live, not by inspection.
    """
    guide = APP[APP.index("def render_guide("):]
    assert 'sub["use_for"]' not in guide, (
        "the guide renders use_for, which in v3 is a list of retired names")
    assert 'sub["plain"]' in guide, "the definition must still be shown"
    assert 'sub["avoid"]' in guide, "the boundary rule must still be shown"

    # And the boundaries themselves must name only living groups.
    from src.models.taxonomy import TAXONOMY

    retired = former_subcategories - core_subcategories
    for block in TAXONOMY.values():
        for sub, meta in block["subcategories"].items():
            for name in retired:
                assert name not in meta["avoid"], (sub, name)


def test_reference_views_cover_all_thirty_under_the_right_category(core_subcategories):
    """Rendering the hierarchy must reach every core subcategory exactly once."""
    from src.models.taxonomy import SUBCATEGORY_NAMES_BY_CATEGORY, TAXONOMY

    rendered: list[str] = []
    for category, block in TAXONOMY.items():
        for sub in block["subcategories"]:
            assert sub in SUBCATEGORY_NAMES_BY_CATEGORY[category]
            rendered.append(sub)

    assert len(rendered) == EXPECTED_CORE_SUBCATEGORIES
    assert set(rendered) == core_subcategories
    assert len(set(rendered)) == len(rendered), "a subcategory rendered twice"


def test_the_fallback_is_hidden_from_the_reference_views_until_it_is_used(relevant):
    """It is a safety valve, not a thirty-first group to browse."""
    from src.models.taxonomy import FALLBACK_SUBCATEGORY, TAXONOMY

    in_taxonomy = any(FALLBACK_SUBCATEGORY in b["subcategories"]
                      for b in TAXONOMY.values())
    used = any(r["primary_taxonomy_subcategory"] == FALLBACK_SUBCATEGORY
               for r in relevant)
    assert not in_taxonomy, "the fallback would render as a browsable group"
    assert not used, (
        "a record reached the fallback -- it should now be surfaced, and this "
        "test updated deliberately rather than left asserting it never happens")


# --- helpers ---------------------------------------------------------------
def _load_workbook():
    """The assignment workbook, or None when it is not in the checkout.

    It lives outside the repo, so the suite must pass without it -- but when
    it is present these tests compare against the real authority rather than
    against numbers retyped here.
    """
    import glob

    candidates = [
        *glob.glob(str(ROOT / "*Taxonomy_v3_Assignments*.xlsx")),
        *glob.glob(str(Path.home() / "Downloads" / "*Taxonomy_v3_Assignments*.xlsx")),
    ]
    if not candidates:
        return None
    import pandas as pd

    return pd.read_excel(candidates[0], sheet_name="Relevant Assignments")
