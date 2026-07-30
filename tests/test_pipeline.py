"""The essential checks.

Deliberately not an exhaustive suite -- these cover the claims the dashboard
makes, so that if one breaks, a number on screen is wrong.

All tests are offline: no network, no API key, no LLM calls.

    python -m pytest tests/ -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"

MIN_RELEVANT_POSTS = 50
REQUIRED_FIELDS = ("feedback_id", "title", "source_url", "retrieved_at",
                   "source_system", "lifecycle_status")


@pytest.fixture(scope="module")
def analyzed() -> dict:
    return json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def records(analyzed) -> list[dict]:
    return analyzed["records"]


@pytest.fixture(scope="module")
def relevant(records) -> list[dict]:
    return [r for r in records if r["is_relevant"]]


@pytest.fixture(scope="module")
def aggregates() -> dict:
    return json.loads((PROC / "aggregates.json").read_text(encoding="utf-8"))


# --- 1. Enough real, relevant posts ---------------------------------------
def test_at_least_50_unique_relevant_posts(relevant):
    assert len(relevant) >= MIN_RELEVANT_POSTS, (
        f"only {len(relevant)} relevant posts; the project requires "
        f"at least {MIN_RELEVANT_POSTS}"
    )
    assert len({r["feedback_id"] for r in relevant}) == len(relevant)


def test_records_are_real_portal_posts(records):
    """Every record must point at a real post on Port's portal."""
    for r in records:
        assert r["source_url"].startswith("https://roadmap.port.io/ideas/p/"), r["source_url"]


def test_no_fabricated_source_systems(records):
    """The POC collects one public source and must never imply otherwise.

    source_system exists because production ingests four systems through the
    same schema. This asserts the field describes what was actually collected
    rather than being populated to make the demo look multi-source.
    """
    from src.models.taxonomy import SOURCE_SYSTEMS

    seen = {r["source_system"] for r in records}
    assert seen <= set(SOURCE_SYSTEMS), seen
    assert seen == {"Port portal"}, (
        f"only Port portal data was collected, but records claim {seen}"
    )


# --- 2. No duplicates ------------------------------------------------------
def test_no_duplicate_ids_or_urls(records):
    ids = [r["feedback_id"] for r in records]
    urls = [r["source_url"] for r in records]
    assert len(ids) == len(set(ids)), "duplicate feedback_id present"
    assert len(urls) == len(set(urls)), "duplicate source_url present"


def test_deduplication_catches_planted_duplicates():
    """A dedup that silently does nothing would also report zero duplicates."""
    from src.analysis.clean import deduplicate

    base = {
        "feedback_id": "abc123", "title": "Support conditional inputs",
        "description": "We need conditional logic in action forms.",
        "votes": 10, "created_at": "2026-01-01T00:00:00Z",
        "source_url": "https://roadmap.port.io/ideas/p/conditional-inputs",
    }
    same_id = dict(base, title="Totally different", description="xyz",
                   source_url="https://roadmap.port.io/ideas/p/other")
    same_url = dict(base, feedback_id="different1", title="Another title",
                    description="abc",
                    source_url=base["source_url"] + "/?utm_source=x")
    same_text = dict(base, feedback_id="different2", votes=99,
                     source_url="https://roadmap.port.io/ideas/p/repost")

    kept, dropped = deduplicate([base, same_id, same_url, same_text])
    assert len(kept) == 1, "duplicates were not collapsed"
    assert {d["matched_on"] for d in dropped} == {"id", "url", "text"}
    assert kept[0]["votes"] == 99, "tie-break should keep the highest-vote record"


# --- 3. Required fields and closed vocabularies ---------------------------
def test_required_fields_populated(records):
    for r in records:
        for field in REQUIRED_FIELDS:
            assert r.get(field), f"{field} missing on {r.get('feedback_id')}"


def test_classified_fields_within_taxonomy(relevant):
    from src.models.taxonomy import (
        CATEGORY_NAMES,
        PERSONA_NAMES,
        PROBLEM_TYPE_NAMES,
        STAGE_NAMES,
        is_valid_pair,
    )

    for r in relevant:
        category = r["primary_taxonomy_category"]
        subcategory = r["primary_taxonomy_subcategory"]
        assert category in CATEGORY_NAMES, category
        assert is_valid_pair(category, subcategory), (category, subcategory)
        assert r["journey_stage"] in STAGE_NAMES, r["journey_stage"]
        assert r["problem_type"] in PROBLEM_TYPE_NAMES, r["problem_type"]
        assert r["persona"] in PERSONA_NAMES, r["persona"]
        assert 1 <= r["severity"] <= 5
        assert 0.0 <= r["confidence"] <= 1.0


def test_lifecycle_statuses_are_normalized(records):
    from src.models.taxonomy import LIFECYCLE_STATUSES

    for r in records:
        assert r["lifecycle_status"] in LIFECYCLE_STATUSES, r["lifecycle_status"]


def test_irrelevant_records_carry_no_taxonomy(records):
    """Out-of-scope feedback must be structurally unable to reach a total."""
    for r in records:
        if not r["is_relevant"]:
            assert r["primary_taxonomy_category"] is None, r["feedback_id"]
            assert r["primary_taxonomy_subcategory"] is None, r["feedback_id"]
            assert r["problem_type"] is None, r["feedback_id"]
            assert r["journey_stage"] is None, r["feedback_id"]
            assert r["relevance_reason"], "an exclusion must be explained"


def test_secondary_assignments_never_duplicate_the_primary(relevant):
    from src.models.schema import MAX_SECONDARY_ASSIGNMENTS

    for r in relevant:
        pairs = list(zip(r["secondary_categories"], r["secondary_subcategories"]))
        assert len(pairs) <= MAX_SECONDARY_ASSIGNMENTS, r["feedback_id"]
        assert len(set(pairs)) == len(pairs), f"duplicate secondary on {r['feedback_id']}"
        primary = (r["primary_taxonomy_category"], r["primary_taxonomy_subcategory"])
        assert primary not in pairs, f"secondary repeats primary on {r['feedback_id']}"


def test_schema_rejects_invented_values():
    from pydantic import ValidationError

    from src.models.schema import FeedbackClassification

    valid = dict(
        is_relevant=True,
        relevance_reason="Concerns approval routing for self-service actions.",
        primary_taxonomy_category="Permissions & Approvals",
        primary_taxonomy_subcategory="Approver routing & identity",
        problem_type="Feature gap",
        journey_stage="Permissions & approvals",
        persona="Action builder",
        severity=3,
        short_summary="Approvers cannot be selected flexibly enough.",
        user_need="Route approvals to the right people automatically.",
        suggested_product_action="Route approval requests to the owning team automatically.",
        confidence=0.8,
        evidence_excerpt="approval is not sent to anyone",
    )
    FeedbackClassification(**valid)          # sanity: the valid case passes

    for bad in (
        dict(valid, primary_taxonomy_category="Invented Category"),
        dict(valid, primary_taxonomy_subcategory="Not A Subcategory"),
        # A real subcategory, but belonging to a different category.
        dict(valid, primary_taxonomy_subcategory="Timeouts"),
        dict(valid, journey_stage="Not A Stage"),
        dict(valid, problem_type="Rant"),
        dict(valid, persona="Chief Executive"),
        dict(valid, severity=9),
        dict(valid, confidence=1.5),
        # Relevant records may not omit the taxonomy.
        dict(valid, primary_taxonomy_category=None, primary_taxonomy_subcategory=None),
    ):
        with pytest.raises(ValidationError):
            FeedbackClassification(**bad)


# --- 3b. Taxonomy shape and ordering --------------------------------------
# Ordering is load-bearing: charts, filters and the guide all derive their
# order from CATEGORY_NAMES and STAGE_NAMES, so a reordered dict silently
# reorders the product story everywhere.

EXPECTED_CATEGORIES = (
    "Discovery, Organization & Reuse",
    "Context, Targeting & Pre-fill",
    "Form Configuration",
    "Validation & Rules",
    "Invocation & Integrations",
    "Identity, Secrets & Security",
    "Permissions & Approvals",
    "Orchestration",
    "Execution Lifecycle",
    "Observability & Debugging",
    "Authoring, Testing & Management",
)

EXPECTED_STAGES = (
    "Action discovery & organization",
    "Contextual entry, targeting & pre-fill",
    "Form & input configuration",
    "Validation, dependencies & conditional logic",
    "Backend & invocation setup",
    "Permissions & approvals",
    "Testing, editing & publishing",
    "Execution, monitoring & run control",
)

# Names from the retired flat taxonomy. They must be rejected by the schema
# rather than merely absent from the docs -- a category whose meaning changed
# cannot silently keep its old labels.
REMOVED_NAMES = (
    "Form structure, input types & controls",
    "Dynamic & dependent inputs",
    "Validation & error guidance",
    "Backend & invocation configuration",
    "Permissions, eligibility & action visibility",
    "Approval workflows & governance",
    "Testing, editing & drafts",
    "Execution visibility, notifications & run control",
    "Multi-step & orchestration",
    "Action discovery & organization",       # was a theme; now only a stage
    "Context, targeting & pre-fill",         # differs in case from the stage
)

# A few retired theme names were demoted to subcategories, where they are now
# valid and narrower. Only the ones with no place at all in the new taxonomy
# may be asserted absent everywhere; the rest are checked as categories only.
DEMOTED_TO_SUBCATEGORY = ("Dynamic & dependent inputs",)


def test_exactly_eleven_categories_in_order():
    from src.models.taxonomy import CATEGORY_NAMES

    assert CATEGORY_NAMES == EXPECTED_CATEGORIES


def test_exactly_sixty_three_unique_subcategories():
    from src.models.taxonomy import (
        ALL_SUBCATEGORY_NAMES,
        CATEGORY_FOR_SUBCATEGORY,
        SUBCATEGORY_NAMES_BY_CATEGORY,
    )

    assert len(ALL_SUBCATEGORY_NAMES) == 63
    # Uniqueness is what makes CATEGORY_FOR_SUBCATEGORY a safe reverse lookup;
    # a repeated name would silently lose one of its entries.
    assert len(set(ALL_SUBCATEGORY_NAMES)) == 63
    assert len(CATEGORY_FOR_SUBCATEGORY) == 63
    assert sum(len(v) for v in SUBCATEGORY_NAMES_BY_CATEGORY.values()) == 63


def test_exactly_eight_stages_in_lifecycle_order():
    from src.models.taxonomy import STAGE_NAMES

    assert STAGE_NAMES == EXPECTED_STAGES


def test_fourteen_problem_types_excluding_irrelevance():
    """Irrelevance is is_relevant=false, never a problem type.

    If "General or irrelevant feedback" were a problem type, out-of-scope
    records would dilute every problem-type distribution instead of being
    excluded from them.
    """
    from src.models.taxonomy import PROBLEM_TYPE_NAMES

    assert len(PROBLEM_TYPE_NAMES) == 14
    for name in PROBLEM_TYPE_NAMES:
        assert "irrelevant" not in name.lower()


def test_removed_taxonomy_names_are_rejected():
    """Retired names must fail validation, not merely be undocumented."""
    from pydantic import ValidationError

    from src.models.schema import FeedbackClassification
    from src.models.taxonomy import ALL_SUBCATEGORY_NAMES, CATEGORY_NAMES

    for name in REMOVED_NAMES:
        assert name not in CATEGORY_NAMES, f"{name} should be retired as a category"
        if name not in DEMOTED_TO_SUBCATEGORY:
            assert name not in ALL_SUBCATEGORY_NAMES, f"{name} should be retired"

    base = dict(
        is_relevant=True,
        relevance_reason="Concerns validation of self-service action inputs.",
        primary_taxonomy_category="Validation & Rules",
        primary_taxonomy_subcategory="Input & cross-field validation",
        problem_type="Feature gap",
        journey_stage="Validation, dependencies & conditional logic",
        persona="Action builder", severity=3,
        short_summary="Validation rules cannot express cross-field conditions.",
        user_need="Express rules that compare two fields.",
        suggested_product_action="Support cross-field validation rules in action forms.",
        confidence=0.8, evidence_excerpt="cannot compare two fields",
    )
    for name in REMOVED_NAMES:
        with pytest.raises(ValidationError):
            FeedbackClassification(**dict(base, primary_taxonomy_category=name))


def test_default_stage_mapping_is_complete_and_valid():
    from src.models.taxonomy import (
        CATEGORY_NAMES,
        DEFAULT_STAGE_FOR_CATEGORY,
        STAGE_NAMES,
    )

    assert set(DEFAULT_STAGE_FOR_CATEGORY) == set(CATEGORY_NAMES)
    for stage in DEFAULT_STAGE_FOR_CATEGORY.values():
        assert stage in STAGE_NAMES, stage


def test_open_statuses_exclude_completed_work():
    """Shipped work must not be able to argue for itself again."""
    from src.models.taxonomy import LIFECYCLE_STATUSES, OPEN_STATUSES

    assert OPEN_STATUSES <= set(LIFECYCLE_STATUSES)
    assert "Completed" not in OPEN_STATUSES
    assert "Closed" not in OPEN_STATUSES
    assert OPEN_STATUSES == {"Open", "Planned", "In progress"}


def test_portal_status_map_produces_only_known_statuses():
    from src.collectors.portal import normalize_status
    from src.models.taxonomy import LIFECYCLE_STATUSES, PORTAL_STATUS_MAP

    assert set(PORTAL_STATUS_MAP.values()) <= set(LIFECYCLE_STATUSES)
    # An unrecognised portal string must become Unknown, never pass through as
    # if it had been normalized.
    assert normalize_status("some brand new portal status") == "Unknown"
    assert normalize_status(None) == "Unknown"
    assert normalize_status("In Progress") == "In progress"


def test_guide_metadata_is_complete():
    """Every category and subcategory must be explainable in the guide tab."""
    from src.models.taxonomy import STAGE_GUIDE, STAGE_NAMES, TAXONOMY

    for category, meta in TAXONOMY.items():
        assert meta["plain"], category
        assert meta["default_stage"], category
        assert meta["subcategories"], category
        for name in meta["confusable"]:
            assert name in TAXONOMY, f"{category} points at unknown {name}"
        for subcategory, sub in meta["subcategories"].items():
            assert sub["plain"], subcategory
            assert sub["use_for"], subcategory
            assert sub["avoid"], subcategory
            assert sub["examples"], subcategory

    assert set(STAGE_GUIDE) == set(STAGE_NAMES)
    for stage, guide in STAGE_GUIDE.items():
        assert guide["user_goal"] and guide["example"], stage


def test_guide_supporting_content_present():
    from src.models.taxonomy import (
        CONFUSION_PAIRS,
        GLOSSARY,
        SEVERITY_SCALE,
        TIE_BREAK_RULES,
        WORKED_EXAMPLES,
        is_valid_pair,
    )

    assert len(TIE_BREAK_RULES) >= 12
    assert len(CONFUSION_PAIRS) >= 8
    assert len(WORKED_EXAMPLES) >= 8
    assert len(GLOSSARY) >= 20
    assert sorted(SEVERITY_SCALE) == [1, 2, 3, 4, 5]

    # A worked example that contradicted the taxonomy would teach the wrong rule.
    for ex in WORKED_EXAMPLES:
        assert is_valid_pair(ex["category"], ex["subcategory"]), ex


def test_no_retired_names_in_active_source():
    """A stale label in the UI is a visible bug even when the tests pass."""
    active = [ROOT / "app.py"] + sorted((ROOT / "src").rglob("*.py"))
    stale = ("primary_theme", "feedback_type", "THEME_NAMES", "THEME_GUIDE",
             "DEFAULT_STAGE_FOR_THEME", "priority_score", "total_votes")
    for path in active:
        text = path.read_text(encoding="utf-8")
        for name in stale:
            assert name not in text, f"{path.name} still references {name}"


def test_guide_renders_without_api_key():
    """The guide is pure metadata -- it must not need a key or a network call."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["PYTHONIOENCODING"] = "utf-8"
    code = (
        "import os, sys;"
        "assert 'ANTHROPIC_API_KEY' not in os.environ;"
        f"sys.path.insert(0, r'{ROOT}');"
        "from src.models.taxonomy import TAXONOMY, STAGE_GUIDE, GLOSSARY, "
        "CONFUSION_PAIRS, WORKED_EXAMPLES, DEFAULT_STAGE_FOR_CATEGORY;"
        "assert len(TAXONOMY) == 11 and len(STAGE_GUIDE) == 8;"
        "print('GUIDE OK')"
    )
    result = subprocess.run([sys.executable, "-c", code], env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "GUIDE OK" in result.stdout


# --- 4. Evidence grounding -------------------------------------------------
def test_verified_excerpts_appear_in_source(records):
    """The core anti-fabrication guarantee."""
    from src.models.schema import verify_excerpt

    for r in records:
        if r["evidence_verified"]:
            source = f"{r['title']}\n{r['description'] or ''}"
            assert verify_excerpt(r["evidence_excerpt"], source), (
                f"quote marked verified but not found in source: {r['feedback_id']}"
            )


def test_grounding_rejects_fabricated_quote():
    from src.models.schema import ground_excerpt, verify_excerpt

    source = "Users cannot set conditional validation on action inputs."
    assert verify_excerpt("conditional validation on action inputs", source)
    assert not verify_excerpt("customers are furious about this", source)

    # Trailing generation artefacts are trimmed, not accepted wholesale.
    ok, cleaned = ground_excerpt("cannot set conditional validation on action inputs.对{", source)
    assert ok and "对" not in cleaned

    # Something with no overlap at all must fail outright.
    bad_ok, _ = ground_excerpt("this text shares nothing with the source at all", source)
    assert not bad_ok


# --- 5. Ranking ------------------------------------------------------------
def test_product_actions_exclude_completed_work(relevant, aggregates):
    """A ranked action must be supported only by records still open."""
    open_ids = {
        r["feedback_id"] for r in relevant
        if r["lifecycle_status"] in set(aggregates["ranking"]["open_statuses"])
    }
    for action in aggregates["product_actions"]:
        assert set(action["record_ids"]) <= open_ids, action["subcategory"]
        assert action["open_records"] == len(action["record_ids"])


def test_ranking_recomputed_by_hand(relevant, aggregates):
    """Recompute the counts independently of the aggregation code."""
    from collections import defaultdict

    open_statuses = set(aggregates["ranking"]["open_statuses"])
    counts: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in relevant:
        if r["lifecycle_status"] in open_statuses:
            counts[(r["primary_taxonomy_category"],
                    r["primary_taxonomy_subcategory"])].append(r)

    assert len(aggregates["product_actions"]) == len(counts)
    for action in aggregates["product_actions"]:
        group = counts[(action["category"], action["subcategory"])]
        assert action["open_records"] == len(group)
        assert action["max_severity"] == max(r["severity"] for r in group)
        expected_avg = sum(r["severity"] for r in group) / len(group)
        assert abs(action["avg_severity"] - expected_avg) < 0.01


def test_ranking_is_lexicographic_and_total(aggregates):
    """Every adjacent pair must be ordered by the stated keys, in order."""
    keys = [entry["key"] for entry in aggregates["ranking"]["keys"]]
    rows = aggregates["product_actions"]
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))

    for a, b in zip(rows, rows[1:]):
        for key in keys:
            if a[key] != b[key]:
                assert a[key] > b[key], (
                    f"rank {a['rank']} loses to rank {b['rank']} on {key}"
                )
                break
        else:
            # All ranking keys equal -- the alphabetical key must decide, so
            # the order is total and reruns cannot shuffle it.
            assert a["subcategory"] < b["subcategory"]


def test_no_weighted_score_survives(aggregates):
    """The invented-weights score was removed, not merely hidden from the UI."""
    text = json.dumps(aggregates)
    for banned in ("priority_score", "demand_score", "frequency_score",
                   "vote_scale", "total_votes"):
        assert banned not in text, f"{banned} still present in aggregates"


def test_product_action_labels_trace_to_a_real_record(relevant, aggregates):
    """A label on the dashboard must be one record's words, not a synthesis."""
    by_id = {r["feedback_id"]: r for r in relevant}
    for action in aggregates["product_actions"]:
        source = by_id[action["product_action_source_id"]]
        assert source["suggested_product_action"] == action["product_action"]
        assert action["product_action_source_id"] in action["record_ids"]


# --- Edge cases ------------------------------------------------------------
def test_filters_handle_empty_result(relevant):
    """An impossible filter combination must yield an empty frame, not an error."""
    df = pd.DataFrame(relevant)
    # Deliberately contradictory: a severity above the scale's maximum can never
    # match, whatever the data contains, so this stays valid as the data changes.
    empty = df[(df["primary_taxonomy_category"] == "Execution Lifecycle")
               & (df["severity"] > 5)]
    assert empty.empty
    empty.sort_values("severity", ascending=False)      # must not raise


def test_aggregation_survives_an_empty_selection(relevant):
    """The dashboard recomputes actions per filter, so empty input must be safe."""
    from src.analysis.aggregate import product_actions

    df = pd.DataFrame(relevant)
    assert product_actions(df[df["severity"] > 5]).empty


def test_missing_values_handled(records):
    """Nulls are legitimate: title-only posts and uncategorised posts exist."""
    df = pd.DataFrame(records)
    assert df["description"].isna().sum() > 0, "expected some title-only posts"
    assert df["lifecycle_status"].notna().all(), "status must never be null"


# --- 6 & 7. App starts, and works with no API key -------------------------
def test_app_loads_data_without_api_key():
    """The demo must work on a machine that has never seen a key."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_EFFORT")}
    env["PYTHONIOENCODING"] = "utf-8"

    code = (
        "import os, sys;"
        "assert 'ANTHROPIC_API_KEY' not in os.environ;"
        f"sys.path.insert(0, r'{ROOT}');"
        "from src.analysis.aggregate import build_all;"
        "out = build_all();"
        "assert out['kpis']['in_scope_records'] >= 50;"
        "print('OK', out['kpis']['in_scope_records'])"
    )
    result = subprocess.run([sys.executable, "-c", code], env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_app_module_does_not_require_anthropic_at_import():
    """app.py must not construct an LLM client just to render."""
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "import anthropic" not in source
    assert "ANTHROPIC_API_KEY" not in source


def test_dashboard_has_no_scope_filter():
    """A scope toggle would invite reading out-of-scope feedback as demand."""
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'multiselect("Scope' not in source
    assert 'selectbox("Scope' not in source
    assert 'toggle("Scope' not in source


def test_streamlit_app_starts():
    """Launch the real app and confirm it serves without crashing."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
         "--server.headless", "true", "--server.port", "8599"],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        import urllib.request

        served = False
        for _ in range(40):                      # up to ~20s for cold start
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen("http://localhost:8599", timeout=2) as resp:
                    if resp.status == 200:
                        served = True
                        break
            except Exception:
                time.sleep(0.5)

        assert proc.poll() is None, "streamlit exited during startup"
        assert served, "app did not serve a page within the timeout"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_critical_gate_requires_both_floors(aggregates):
    """`is_critical` must need volume AND severity, and must not round.

    Rounding matters here rather than in theory: an action averaging 3.5 rounds
    to a severity band of 4, so a gate written against the band would admit it
    under a rule that says "4 and above".
    """
    from src.analysis.aggregate import CRITICAL_MIN_RECORDS, CRITICAL_MIN_SEVERITY

    assert CRITICAL_MIN_RECORDS == 3
    assert CRITICAL_MIN_SEVERITY == 4.0

    # The gate is the first key applied.
    assert aggregates["ranking"]["keys"][0]["key"] == "is_critical"

    rounds_up_but_excluded = 0
    for action in aggregates["product_actions"]:
        expected = int(action["open_records"] >= CRITICAL_MIN_RECORDS
                       and action["avg_severity"] >= CRITICAL_MIN_SEVERITY)
        assert action["is_critical"] == expected, action["subcategory"]

        if action["is_critical"]:
            assert action["open_records"] >= CRITICAL_MIN_RECORDS
            assert action["avg_severity"] >= CRITICAL_MIN_SEVERITY
        elif (action["open_records"] >= CRITICAL_MIN_RECORDS
              and action["severity_band"] >= CRITICAL_MIN_SEVERITY):
            # Enough records, band rounds to 4, raw mean below 4 -> excluded.
            assert action["avg_severity"] < CRITICAL_MIN_SEVERITY
            rounds_up_but_excluded += 1

    assert rounds_up_but_excluded, (
        "expected at least one action whose band rounds to 4 while its raw mean "
        "does not -- that case is what the unrounded test exists for"
    )


def test_critical_actions_outrank_everything_else(aggregates):
    rows = aggregates["product_actions"]
    ranks = [r["rank"] for r in rows if r["is_critical"]]
    if ranks:
        assert ranks == list(range(1, len(ranks) + 1)), (
            "critical actions must occupy the top ranks")
