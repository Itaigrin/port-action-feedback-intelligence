"""Classify each feedback record with an LLM, under a validated schema.

The LLM only reads, summarises, and categorises. Every number in the dashboard
is computed later by plain Python -- nothing here produces a statistic.

Three controls keep the output trustworthy:
  1. Pydantic schema with closed enums -- an invented label fails validation.
  2. Quote grounding -- the evidence excerpt must appear verbatim in the source,
     checked in Python after the response returns.
  3. A per-record cache -- an interrupted run resumes instead of restarting,
     and the committed results make the demo reproducible.

    python -m src.analysis.classify            # classify anything not cached
    python -m src.analysis.classify --limit 5  # smoke test
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from ..models.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt, source_text
from ..models.schema import FeedbackClassification, ground_excerpt
from ..models.taxonomy import SCHEMA_VERSION, TAXONOMY_VERSION

ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = ROOT / "data" / "processed"
CACHE_DIR = ROOT / "data" / "cache"

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_EFFORT = "medium"
MAX_TOKENS = 2000


def cache_key(text: str, model: str) -> str:
    """Cache is invalidated by any change that could change the answer.

    Prompt, taxonomy and schema versions are all part of the key. That is the
    mechanism which guarantees a taxonomy revision produces a genuine
    reclassification rather than replaying labels from a scheme that no longer
    exists.
    """
    parts = f"{text}|{PROMPT_VERSION}|{TAXONOMY_VERSION}|{SCHEMA_VERSION}|{model}"
    return sha256(parts.encode("utf-8")).hexdigest()


def _opt(row, field: str, default=None):
    """Read an optional column, tolerating absence and NaN."""
    value = getattr(row, field, None)
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return default
    return value


def classify_one(client, model: str, effort: str, title: str,
                 description: str | None, category: str | None,
                 source_system: str | None = None,
                 retries: int = 3) -> tuple[FeedbackClassification | None, str | None]:
    """Classify one record. Returns (classification, error_reason)."""
    base_prompt = build_user_prompt(title, description, category, source_system)
    correction = ""

    for attempt in range(retries):
        try:
            resp = client.messages.parse(
                model=model,
                max_tokens=MAX_TOKENS,
                # Identical on every call -> cached at ~0.1x input cost.
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                output_config={"effort": effort},
                messages=[{"role": "user", "content": base_prompt + correction}],
                output_format=FeedbackClassification,
            )
            # Safety classifiers can decline; check before reading content.
            if getattr(resp, "stop_reason", None) == "refusal":
                return None, "refusal"
            parsed = resp.parsed_output
            if parsed is None:
                raise ValueError("no parsed output returned")
            return parsed, None

        except Exception as exc:                      # noqa: BLE001
            name = type(exc).__name__
            message = str(exc)

            # A schema violation retried verbatim produces the same violation --
            # the model has no way to learn what it got wrong. Feed the
            # validation error back so the retry is actually a correction. The
            # constraint itself is never relaxed: a summary that will not fit in
            # 200 characters is not a summary.
            if name == "ValidationError":
                correction = (
                    "\n\nYour previous answer failed schema validation:\n"
                    f"{message[:400]}\n"
                    "Return the same classification with that field corrected to "
                    "satisfy the constraint. Do not change any other field."
                )

            # Most 400s mean the request itself is wrong, so retrying is pointless.
            # "Grammar compilation timed out" is the exception: it is a transient
            # server-side hiccup while compiling the structured-output schema, and
            # the identical request usually succeeds on a second attempt.
            transient_400 = "grammar compilation timed out" in message.lower()
            fatal = name in ("AuthenticationError", "PermissionDeniedError") or (
                name == "BadRequestError" and not transient_400
            )
            if fatal or attempt == retries - 1:
                return None, f"{name}: {message[:120]}"
            time.sleep(2 ** attempt)                  # backoff on transient failure

    return None, "exhausted_retries"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="classify only N records")
    parser.add_argument("--no-cache", action="store_true", help="ignore cached results")
    args = parser.parse_args()

    load_dotenv(override=True)
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    effort = os.environ.get("ANTHROPIC_EFFORT", DEFAULT_EFFORT)

    # One id for this whole batch, so every record can be traced to the run
    # that produced it and two runs are never conflated in the artifact.
    started = datetime.now(timezone.utc)
    analysis_run_id = (
        f"{started.strftime('%Y%m%dT%H%M%SZ')}-{PROMPT_VERSION}-{TAXONOMY_VERSION}"
    )

    df = pd.read_csv(PROC_DIR / "feedback_clean.csv")
    if args.limit:
        df = df.head(args.limit)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    import anthropic
    client = anthropic.Anthropic()

    results: list[dict] = []
    stats = {"cached": 0, "called": 0, "failed": 0, "refused": 0,
             "grounding_failures": 0, "trimmed": 0, "low_confidence": 0,
             "needs_review": 0, "irrelevant": 0, "with_secondary": 0}

    for i, row in enumerate(df.itertuples(index=False), 1):
        title = str(row.title)
        description = None if pd.isna(row.description) else str(row.description)
        category = None if pd.isna(row.category) else str(row.category)
        source_system = str(_opt(row, "source_system", "Port portal"))
        lifecycle_status = str(_opt(row, "lifecycle_status", "Unknown"))
        src = source_text(title, description)

        key = cache_key(src, model)
        cache_file = CACHE_DIR / f"{key}.json"

        if cache_file.exists() and not args.no_cache:
            payload = json.loads(cache_file.read_text(encoding="utf-8"))
            stats["cached"] += 1
        else:
            classification, error = classify_one(
                client, model, effort, title, description, category, source_system)
            stats["called"] += 1
            if classification is None:
                stats["failed"] += 1
                if error == "refusal":
                    stats["refused"] += 1
                print(f"  [{i}/{len(df)}] FAIL {error} :: {title[:50]}", flush=True)
                continue
            payload = {
                "classification": classification.model_dump(),
                "model_name": model,
                "prompt_version": PROMPT_VERSION,
                "taxonomy_version": TAXONOMY_VERSION,
                "schema_version": SCHEMA_VERSION,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
            cache_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                                  encoding="utf-8")

        c = payload["classification"]

        # Quote grounding -- computed here, never taken from the model.
        # Only the verified portion is kept, so anything displayed is
        # guaranteed to appear character-for-character in the source.
        verified, grounded = ground_excerpt(c["evidence_excerpt"], src)
        if verified and grounded != c["evidence_excerpt"]:
            stats["trimmed"] += 1
        c["evidence_excerpt"] = grounded
        if not verified:
            stats["grounding_failures"] += 1
        if c["confidence"] < 0.7:
            stats["low_confidence"] += 1
        if c.get("needs_human_review"):
            stats["needs_review"] += 1
        if not c["is_relevant"]:
            stats["irrelevant"] += 1
        if c.get("secondary_assignments"):
            stats["with_secondary"] += 1

        # Secondary assignments are a nested list; flatten to display strings so
        # the record stays a flat row for pandas, while keeping the structured
        # form for anything that needs the pair.
        secondaries = c.get("secondary_assignments") or []

        results.append({
            "feedback_id": str(row.feedback_id),
            "title": title,
            "description": description,
            # Normalised at collection time, never inferred by the model.
            "source_system": source_system,
            "lifecycle_status": lifecycle_status,
            "comments_count": None if pd.isna(row.comments_count) else int(row.comments_count),
            "status": None if pd.isna(row.status) else str(row.status),
            "category": category,
            "created_at": None if pd.isna(row.created_at) else str(row.created_at),
            "source_url": str(row.source_url),
            # Provenance carried through from collection so every analysed
            # record can be traced back to when it was retrieved.
            "retrieved_at": None if pd.isna(row.retrieved_at) else str(row.retrieved_at),
            "slug": None if pd.isna(row.slug) else str(row.slug),
            **c,
            "secondary_categories": [s["category"] for s in secondaries],
            "secondary_subcategories": [s["subcategory"] for s in secondaries],
            "evidence_verified": verified,
            "model_name": payload["model_name"],
            "prompt_version": payload["prompt_version"],
            "taxonomy_version": payload.get("taxonomy_version", TAXONOMY_VERSION),
            "schema_version": payload.get("schema_version", SCHEMA_VERSION),
            "analysis_run_id": analysis_run_id,
            "analyzed_at": payload["analyzed_at"],
        })

        if i % 25 == 0 or i == len(df):
            print(f"  [{i}/{len(df)}] cached={stats['cached']} "
                  f"called={stats['called']} failed={stats['failed']}", flush=True)

    relevant = [r for r in results if r["is_relevant"]]
    out = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "analysis_run_id": analysis_run_id,
            "model_name": model,
            "effort": effort,
            "prompt_version": PROMPT_VERSION,
            "taxonomy_version": TAXONOMY_VERSION,
            "schema_version": SCHEMA_VERSION,
            "records_analyzed": len(results),
            "records_relevant": len(relevant),
            "records_irrelevant": len(results) - len(relevant),
            **stats,
            "note": "The LLM classifies only. All counts, averages, rankings and "
                    "scores in the dashboard are computed in Python from these records.",
        },
        "records": results,
    }
    (PROC_DIR / "analyzed.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"Analyzed            : {len(results)}")
    print(f"Relevant            : {len(relevant)}")
    print(f"Irrelevant          : {len(results) - len(relevant)}")
    print(f"API calls / cached  : {stats['called']} / {stats['cached']}")
    print(f"Failed / refused    : {stats['failed']} / {stats['refused']}")
    print(f"Grounding failures  : {stats['grounding_failures']}")
    print(f"Quotes trimmed      : {stats['trimmed']} (trailing generation artifacts)")
    print(f"Low confidence (<0.7): {stats['low_confidence']}")
    print(f"Flagged for review  : {stats['needs_review']}")
    print(f"With a secondary    : {stats['with_secondary']}")
    print(f"Run id              : {analysis_run_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
