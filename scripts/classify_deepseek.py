"""Classify the records the Anthropic run never reached, using DeepSeek.

Why this exists: the v3 reclassification stopped at 290 of 327 when the
Anthropic balance ran out. This finishes the remaining records against the
same v3 prompt and the same Pydantic schema, so the second opinion covers the
whole dataset.

TWO MODELS IN ONE DATASET -- read before trusting an agreement number.

The other 290 records were judged by claude-sonnet-5. These are judged by
deepseek-chat. That is a real methodological seam, and it is survivable here
for one specific reason: reconciliation never lets a model overwrite the
workbook. A model's only effect is to raise `needs_human_review` on a
disagreement, so a second model can add review flags but cannot corrupt a
single assignment. `model_name` is written per record, and reconcile reports
agreement per model rather than as one blended figure -- a single number
across two models would mean nothing.

DeepSeek has no equivalent of Anthropic's grammar-constrained output, so the
schema is enforced the hard way: JSON mode, then Pydantic validation, then a
retry that feeds the validation error back so the model corrects rather than
repeats itself. A response that never validates is skipped and reported, not
coerced into the dataset.

    python -m scripts.classify_deepseek [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.classify import cache_key  # noqa: E402
from src.models.prompt import (  # noqa: E402
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
    source_text,
)
from src.models.schema import (  # noqa: E402
    FeedbackClassification,
    ground_excerpt,
)
from src.models.taxonomy import SCHEMA_VERSION, TAXONOMY_VERSION  # noqa: E402

PROC = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "cache"

MODEL = "deepseek-chat"
ENDPOINT = "https://api.deepseek.com/chat/completions"
MAX_TOKENS = 2000
RETRIES = 3
ANTHROPIC_MODEL = "claude-sonnet-5"      # what the first 290 were classified with

# DeepSeek's JSON mode needs the shape spelled out; there is no grammar to
# constrain it. The schema is still the authority -- this only improves the
# odds of a first-attempt hit.
JSON_INSTRUCTION = """

Return a single JSON object with exactly these keys:
  is_relevant (bool), relevance_reason (str),
  primary_taxonomy_category (str|null), primary_taxonomy_subcategory (str|null),
  secondary_assignments (list of {"category": str, "subcategory": str}),
  problem_type (str|null), journey_stage (str|null), persona (str),
  severity (int 1-5), feedback_polarity (str), polarity_reason (str),
  short_summary (str), user_need (str), suggested_product_action (str),
  confidence (float 0-1), needs_human_review (bool), evidence_excerpt (str)

Every categorical value must be copied exactly from the lists above.
Return JSON only -- no prose, no markdown fence."""


def _post(api_key: str, messages: list[dict], timeout: float = 180.0) -> str:
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({
            "model": MODEL,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read())
    return body["choices"][0]["message"]["content"]


def classify_one(api_key: str, title: str, description: str | None,
                 category: str | None, source_system: str
                 ) -> tuple[FeedbackClassification | None, str | None]:
    """One record, validated against the same schema the Anthropic path uses."""
    base = build_user_prompt(title, description, category, source_system)
    correction = ""

    for attempt in range(RETRIES):
        try:
            raw = _post(api_key, [
                {"role": "system", "content": SYSTEM_PROMPT + JSON_INSTRUCTION},
                {"role": "user", "content": base + correction},
            ])
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```")[1].lstrip("json").strip()
            return FeedbackClassification.model_validate_json(text), None

        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            if exc.code in (429, 500, 502, 503, 529) and attempt < RETRIES - 1:
                time.sleep(2 ** attempt)
                continue
            return None, f"HTTP {exc.code}: {detail}"

        except Exception as exc:                      # noqa: BLE001
            message = str(exc)
            if attempt == RETRIES - 1:
                return None, f"{type(exc).__name__}: {message[:180]}"
            # Feed the failure back. Retrying verbatim reproduces it exactly;
            # the model has no way to learn what it got wrong otherwise.
            correction = (
                "\n\nYour previous reply was rejected:\n"
                f"{message[:600]}\n"
                "Return corrected JSON only. Every categorical value must come "
                "from the allowed lists.")
            time.sleep(1)

    return None, "exhausted retries"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    import os
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("DEEPSEEK_API_KEY is not set in .env")
        return 1

    frame = pd.read_csv(PROC / "feedback_clean.csv")

    # Only the records with no v3 classification from either model.
    todo = []
    for row in frame.itertuples(index=False):
        description = None if pd.isna(row.description) else str(row.description)
        src = source_text(str(row.title), description)
        if (CACHE / f"{cache_key(src, ANTHROPIC_MODEL)}.json").exists():
            continue
        if (CACHE / f"{cache_key(src, MODEL)}.json").exists():
            continue
        todo.append((row, description, src))

    print(f"records total          : {len(frame)}")
    print(f"already classified     : {len(frame) - len(todo)}")
    print(f"to classify with {MODEL}: {len(todo)}")
    if args.limit:
        todo = todo[:args.limit]
        print(f"limited to             : {len(todo)}")
    if args.dry_run:
        print("\n--dry-run: no calls made")
        return 0
    if not todo:
        print("\nnothing to do")
        return 0

    CACHE.mkdir(parents=True, exist_ok=True)
    ok = failed = ungrounded = 0

    for i, (row, description, src) in enumerate(todo, 1):
        category = None if pd.isna(row.category) else str(row.category)
        source_system = str(getattr(row, "source_system", "Port portal"))

        classification, error = classify_one(
            api_key, str(row.title), description, category, source_system)
        if classification is None:
            failed += 1
            print(f"  [{i}/{len(todo)}] FAIL {error} :: {str(row.title)[:45]}",
                  flush=True)
            continue

        payload = classification.model_dump()
        # Grounding is recomputed here, never trusted from the model -- the
        # same control the Anthropic path applies.
        verified, grounded = ground_excerpt(payload["evidence_excerpt"], src)
        payload["evidence_excerpt"] = grounded
        if not verified:
            ungrounded += 1

        (CACHE / f"{cache_key(src, MODEL)}.json").write_text(
            json.dumps({
                "classification": payload,
                "model_name": MODEL,
                "prompt_version": PROMPT_VERSION,
                "taxonomy_version": TAXONOMY_VERSION,
                "schema_version": SCHEMA_VERSION,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        ok += 1
        if i % 5 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] ok={ok} failed={failed}", flush=True)

    print("\n" + "=" * 56)
    print(f"classified          : {ok}")
    print(f"failed              : {failed}")
    print(f"unverified quotes   : {ungrounded}")
    print(f"model               : {MODEL}")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
