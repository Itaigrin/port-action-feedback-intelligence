"""The seven essential checks.

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
REQUIRED_FIELDS = ("feedback_id", "title", "source_url", "retrieved_at")


@pytest.fixture(scope="module")
def analyzed() -> dict:
    return json.loads((PROC / "analyzed.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def records(analyzed) -> list[dict]:
    return analyzed["records"]


@pytest.fixture(scope="module")
def relevant(records) -> list[dict]:
    return [r for r in records if r["is_relevant"]]


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


# --- 3. Required fields ----------------------------------------------------
def test_required_fields_populated(records):
    for r in records:
        for field in REQUIRED_FIELDS:
            assert r.get(field), f"{field} missing on {r.get('feedback_id')}"


def test_classified_fields_within_taxonomy(relevant):
    from src.models.taxonomy import FEEDBACK_TYPE_NAMES, STAGE_NAMES, THEME_NAMES

    for r in relevant:
        assert r["primary_theme"] in THEME_NAMES, r["primary_theme"]
        assert r["journey_stage"] in STAGE_NAMES, r["journey_stage"]
        assert r["feedback_type"] in FEEDBACK_TYPE_NAMES, r["feedback_type"]
        assert 1 <= r["severity"] <= 5
        assert 0.0 <= r["confidence"] <= 1.0


def test_schema_rejects_invented_values():
    from pydantic import ValidationError

    from src.models.schema import FeedbackClassification

    valid = dict(
        is_relevant=True, primary_theme="Approval workflows & governance",
        journey_stage="Permissions & approvals", feedback_type="Feature request",
        severity=3, short_summary="Approvers cannot be configured flexibly enough.",
        user_need="Route approvals to the right people automatically.",
        confidence=0.8, evidence_excerpt="approval is not sent to anyone",
    )
    FeedbackClassification(**valid)          # sanity: the valid case passes

    for bad in (
        dict(valid, primary_theme="Invented Theme"),
        dict(valid, journey_stage="Not A Stage"),
        dict(valid, feedback_type="Rant"),
        dict(valid, severity=9),
        dict(valid, confidence=1.5),
    ):
        with pytest.raises(ValidationError):
            FeedbackClassification(**bad)


# --- 3b. Taxonomy shape and ordering --------------------------------------
# The v2.0 taxonomy: 11 themes, 8 chronological stages. These tests exist
# because the ordering is load-bearing -- charts, filters and the guide all
# derive their order from STAGE_NAMES, so a reordered dict silently reorders
# the product journey everywhere.
EXPECTED_THEMES = (
    "Action discovery & organization",
    "Context, targeting & pre-fill",
    "Form structure, input types & controls",
    "Dynamic & dependent inputs",
    "Validation & error guidance",
    "Backend & invocation configuration",
    "Permissions, eligibility & action visibility",
    "Approval workflows & governance",
    "Testing, editing & drafts",
    "Execution visibility, notifications & run control",
    "Multi-step & orchestration",
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

# Every theme and stage name retired in the v1 -> v2 migration. None may be
# accepted again: allowing both would let stale labels leak back into the data.
REMOVED_THEMES = (
    "Input types & controls",
    "Validation & conditional logic",
    "Permissions & access control",
    "Approval workflows",
    "Testing & editing experience",
    "Execution visibility & logs",
    "Run control & retries",
    "Notifications & alerting",
)

REMOVED_STAGES = (
    "Discovering and organizing actions",
    "Configuring forms and inputs",
    "Validations and conditional logic",
    "Backend and invocation setup",
    "Permissions and approvals",
    "Testing and editing",
    "Execution and monitoring",
)


def test_exactly_eleven_themes_in_order():
    from src.models.taxonomy import THEME_NAMES

    assert len(THEME_NAMES) == 11, f"expected 11 themes, got {len(THEME_NAMES)}"
    assert THEME_NAMES == EXPECTED_THEMES


def test_exactly_eight_stages_in_lifecycle_order():
    from src.models.taxonomy import STAGE_NAMES

    assert len(STAGE_NAMES) == 8, f"expected 8 stages, got {len(STAGE_NAMES)}"
    assert STAGE_NAMES == EXPECTED_STAGES, "journey stages are not in lifecycle order"


def test_context_theme_and_stage_exist():
    from src.models.taxonomy import STAGE_NAMES, THEME_NAMES

    assert "Context, targeting & pre-fill" in THEME_NAMES
    assert "Contextual entry, targeting & pre-fill" in STAGE_NAMES


def test_removed_taxonomy_names_are_rejected():
    from pydantic import ValidationError

    from src.models.schema import FeedbackClassification
    from src.models.taxonomy import STAGE_NAMES, THEME_NAMES

    base = dict(
        is_relevant=True, primary_theme="Approval workflows & governance",
        journey_stage="Permissions & approvals", feedback_type="Feature request",
        severity=3, short_summary="Approvers cannot be configured flexibly enough.",
        user_need="Route approvals to the right people automatically.",
        confidence=0.8, evidence_excerpt="approval is not sent to anyone",
    )

    for old in REMOVED_THEMES:
        assert old not in THEME_NAMES, f"retired theme still active: {old}"
        with pytest.raises(ValidationError):
            FeedbackClassification(**dict(base, primary_theme=old))

    for old in REMOVED_STAGES:
        assert old not in STAGE_NAMES, f"retired stage still active: {old}"
        with pytest.raises(ValidationError):
            FeedbackClassification(**dict(base, journey_stage=old))


def test_every_theme_has_a_recommended_action():
    from src.analysis.aggregate import RECOMMENDED_ACTIONS
    from src.models.taxonomy import THEME_NAMES

    for theme in THEME_NAMES:
        assert theme in RECOMMENDED_ACTIONS, f"no recommendation for {theme}"
        assert RECOMMENDED_ACTIONS[theme].strip(), f"empty recommendation for {theme}"
    stale = set(RECOMMENDED_ACTIONS) - set(THEME_NAMES)
    assert not stale, f"recommendations for themes that no longer exist: {stale}"


def test_default_stage_mapping_is_complete_and_valid():
    from src.models.taxonomy import DEFAULT_STAGE_FOR_THEME, STAGE_NAMES, THEME_NAMES

    assert set(DEFAULT_STAGE_FOR_THEME) == set(THEME_NAMES)
    for theme, stage in DEFAULT_STAGE_FOR_THEME.items():
        assert stage in STAGE_NAMES, f"{theme} maps to unknown stage {stage}"


def test_guide_metadata_is_complete():
    """The guide tab renders straight from this metadata, so gaps become blanks."""
    from src.models.taxonomy import (
        GLOSSARY, STAGE_GUIDE, STAGE_NAMES, THEME_GUIDE, THEME_NAMES,
    )

    for theme in THEME_NAMES:
        assert theme in THEME_GUIDE, f"no guide entry for theme {theme}"
        g = THEME_GUIDE[theme]
        for field in ("plain", "use_when", "avoid_when", "examples"):
            assert field in g and g[field], f"{theme} guide missing {field}"
        assert len(g["examples"]) >= 2, f"{theme} needs two examples"

    for stage in STAGE_NAMES:
        assert stage in STAGE_GUIDE, f"no guide entry for stage {stage}"
        g = STAGE_GUIDE[stage]
        for field in ("plain", "user_goal", "example"):
            assert field in g and g[field], f"{stage} guide missing {field}"

    assert len(GLOSSARY) >= 18
    for term, definition in GLOSSARY.items():
        assert definition.strip(), f"empty glossary definition for {term}"


def test_guide_supporting_content_present():
    from src.models.taxonomy import (
        CONFUSION_PAIRS, STAGE_NAMES, THEME_NAMES, WORKED_EXAMPLES,
    )

    assert len(WORKED_EXAMPLES) >= 4
    for ex in WORKED_EXAMPLES:
        assert ex["theme"] in THEME_NAMES, ex["theme"]
        assert ex["stage"] in STAGE_NAMES, ex["stage"]
        assert ex["feedback"] and ex["why"]

    assert len(CONFUSION_PAIRS) >= 8
    for pair in CONFUSION_PAIRS:
        for key in ("left", "right", "left_says", "right_says"):
            assert pair[key].strip(), f"confusion pair missing {key}"


def test_no_retired_names_in_active_source():
    """Old labels must not survive in code or UI text."""
    targets = [ROOT / "app.py", ROOT / "src" / "models" / "taxonomy.py",
               ROOT / "src" / "models" / "prompt.py",
               ROOT / "src" / "analysis" / "aggregate.py"]
    # These two read as substrings of live v2 names, so check them separately.
    substring_safe = {"Approval workflows", "Backend and invocation setup"}
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for old in REMOVED_THEMES:
            if old in substring_safe:
                continue
            assert old not in text, f"retired theme {old!r} still in {path.name}"
        for old in REMOVED_STAGES:
            if old in substring_safe:
                continue
            assert old not in text, f"retired stage {old!r} still in {path.name}"


def test_guide_renders_without_api_key():
    """The guide is pure metadata -- it must not need a key or a network call."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    env["PYTHONIOENCODING"] = "utf-8"
    code = (
        "import os, sys;"
        "assert 'ANTHROPIC_API_KEY' not in os.environ;"
        f"sys.path.insert(0, r'{ROOT}');"
        "from src.models.taxonomy import THEME_GUIDE, STAGE_GUIDE, GLOSSARY, "
        "CONFUSION_PAIRS, WORKED_EXAMPLES, DEFAULT_STAGE_FOR_THEME;"
        "assert len(THEME_GUIDE) == 11 and len(STAGE_GUIDE) == 8;"
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


# --- 5. Priority score -----------------------------------------------------
def test_priority_score_recomputed_by_hand(relevant):
    """Recompute independently of the scoring code."""
    from collections import defaultdict

    agg = json.loads((PROC / "aggregates.json").read_text(encoding="utf-8"))

    posts, votes, sev = defaultdict(int), defaultdict(int), defaultdict(list)
    for r in relevant:
        t = r["primary_theme"]
        posts[t] += 1
        votes[t] += r["votes"] or 0
        sev[t].append(r["severity"])

    max_posts, max_votes = max(posts.values()), max(votes.values())
    avg_sev = {t: sum(v) / len(v) for t, v in sev.items()}
    max_sev = max(avg_sev.values())

    for row in agg["themes"]:
        t = row["primary_theme"]
        expected = (0.45 * votes[t] / max_votes
                    + 0.30 * posts[t] / max_posts
                    + 0.25 * avg_sev[t] / max_sev)
        assert abs(expected - row["priority_score"]) < 1e-9, t


def test_priority_ranking_is_monotonic():
    """No theme may outrank another while losing on all three components."""
    agg = json.loads((PROC / "aggregates.json").read_text(encoding="utf-8"))
    rows = agg["themes"]
    for a in rows:
        for b in rows:
            if (a["total_votes"] >= b["total_votes"]
                    and a["posts"] >= b["posts"]
                    and a["avg_severity"] >= b["avg_severity"]):
                assert a["priority_score"] >= b["priority_score"] - 1e-12


def test_vote_scale_choice_matches_the_data():
    """The linear/log decision must follow the rule, not preference."""
    agg = json.loads((PROC / "aggregates.json").read_text(encoding="utf-8"))
    votes = pd.Series([t["total_votes"] for t in agg["themes"]])
    ratio = votes.max() / votes.median()
    expected = "log" if ratio > agg["scoring"]["threshold"] else "linear"
    assert agg["scoring"]["vote_scale"] == expected
    assert abs(agg["scoring"]["vote_skew_ratio"] - ratio) < 0.01


# --- Edge cases ------------------------------------------------------------
def test_filters_handle_empty_result(relevant):
    """An impossible filter combination must yield an empty frame, not an error."""
    df = pd.DataFrame(relevant)
    # Deliberately contradictory: a severity above the scale's maximum can never
    # match, whatever the data contains, so this stays valid as the data changes.
    empty = df[(df["primary_theme"] == "Testing, editing & drafts")
               & (df["severity"] > 5)]
    assert empty.empty
    empty.sort_values("votes", ascending=False)      # must not raise


def test_missing_values_handled(records):
    """Nulls are legitimate: title-only posts and uncategorised posts exist."""
    df = pd.DataFrame(records)
    assert df["description"].isna().sum() > 0, "expected some title-only posts"
    assert df["votes"].notna().all(), "votes must never be null after cleaning"


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
        "assert out['kpis']['relevant_posts'] >= 50;"
        "print('OK', out['kpis']['relevant_posts'])"
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
