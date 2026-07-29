"""Clean, deduplicate, and quality-check the raw portal snapshot.

Reads the newest data/raw/portal_snapshot_*.json and writes:
  data/processed/feedback_clean.csv    one row per unique record
  data/processed/quality_report.json   what was dropped and why

Everything here is deterministic Python. No LLM is involved: relevance is
*estimated* with a keyword heuristic for planning purposes only, and the real
judgment happens later in the classification stage.

    python -m src.analysis.clean
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"

REQUIRED = ("feedback_id", "title", "source_url")
ALLOWED_HOST = "roadmap.port.io"

# --- text normalisation ----------------------------------------------------
_MD = re.compile(r"[*_`~#>\[\]()!]+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Aggressive normalisation for duplicate detection only.

    Never used for display -- the goal is catching reposts of the same request
    under different wording, not preserving nuance.
    """
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = _MD.sub(" ", text)
    text = _PUNCT.sub(" ", text)
    return _WS.sub(" ", text).strip()


def text_hash(record: dict) -> str:
    blob = normalise(f"{record.get('title', '')} {record.get('description') or ''}")
    return sha256(blob.encode("utf-8")).hexdigest()


def canonical_url(url: str) -> str:
    """Strip query strings and trailing slashes so URL variants collapse."""
    p = urlparse(url or "")
    path = p.path.rstrip("/")
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", "", ""))


# --- relevance heuristic (estimate only) -----------------------------------
RELEVANT_CATEGORIES = {
    "Self-service actions", "Workflows", "Automations",
    "RBAC & Ownership", "Audit log",
}

KEYWORDS = (
    "self-service", "self service", "action", "actions", "workflow", "automation",
    "approval", "approver", "permission", "rbac", "input", "form", "validation",
    "jq", "regex", "webhook", "trigger", "invocation", "backend", "execution",
    "action run", "logs", "retry", "dynamic permission", "multi-step", "step",
)


def relevance_hint(record: dict) -> tuple[bool, int]:
    """Cheap keyword screen. Deliberately over-inclusive.

    A false positive costs one LLM call and is then correctly excluded.
    A false negative is invisible and permanently lost.
    """
    blob = normalise(f"{record.get('title', '')} {record.get('description') or ''}")
    hits = sum(1 for k in KEYWORDS if k in blob)
    in_category = record.get("category") in RELEVANT_CATEGORIES
    return (in_category or hits >= 2), hits


# --- quality gates ---------------------------------------------------------
def gate(record: dict) -> str | None:
    """Return a drop reason, or None if the record passes."""
    for field in REQUIRED:
        if not record.get(field):
            return f"missing_{field}"
    url = urlparse(record["source_url"])
    if url.scheme not in ("http", "https") or url.netloc != ALLOWED_HOST:
        return "invalid_url"
    if len(record["title"].strip()) < 3:
        return "title_too_short"
    return None


def sanitise(record: dict, issues: Counter) -> dict:
    """Null out values that fail sanity checks, recording each occurrence."""
    rec = dict(record)

    votes = rec.get("votes")
    if votes is not None and (not isinstance(votes, int) or votes < 0):
        rec["votes"] = None
        issues["votes_nulled"] += 1

    created = rec.get("created_at")
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt > datetime.now(timezone.utc):
                rec["created_at"] = None
                issues["future_date_nulled"] += 1
        except ValueError:
            rec["created_at"] = None
            issues["unparseable_date_nulled"] += 1

    return rec


# --- deduplication ---------------------------------------------------------
def _better(a: dict, b: dict) -> dict:
    """Keep the more canonical record: highest votes, then earliest created."""
    av, bv = a.get("votes") or 0, b.get("votes") or 0
    if av != bv:
        return a if av > bv else b
    ac, bc = a.get("created_at") or "9999", b.get("created_at") or "9999"
    return a if ac <= bc else b


def deduplicate(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Apply three independent dedup keys. Returns (kept, dropped_log)."""
    kept: dict[str, dict] = {}          # primary key -> record
    index: dict[tuple[str, str], str] = {}   # (key_type, value) -> primary key
    dropped: list[dict] = []

    for rec in records:
        keys = [
            ("id", rec["feedback_id"]),
            ("url", canonical_url(rec["source_url"])),
            ("text", text_hash(rec)),
        ]
        hit = next((index[k] for k in keys if k in index), None)

        if hit is None:
            pk = rec["feedback_id"]
            kept[pk] = rec
            for k in keys:
                index[k] = pk
            continue

        matched_on = next(k[0] for k in keys if k in index)
        winner = _better(kept[hit], rec)
        loser = rec if winner is not kept[hit] else kept[hit]
        dropped.append({
            "dropped_id": loser["feedback_id"],
            "dropped_title": loser["title"],
            "kept_id": winner["feedback_id"],
            "matched_on": matched_on,
        })
        kept[hit] = winner
        for k in keys:
            index.setdefault(k, hit)

    return list(kept.values()), dropped


# --- pipeline --------------------------------------------------------------
def main() -> None:
    snapshots = sorted(RAW_DIR.glob("portal_snapshot_*.json"))
    if not snapshots:
        raise SystemExit("No raw snapshot found. Run: python -m src.collectors.run")
    snapshot = snapshots[-1]
    raw = json.loads(snapshot.read_text(encoding="utf-8"))
    records = raw["records"]

    issues: Counter = Counter()
    gate_drops: list[dict] = []
    passed: list[dict] = []

    for rec in records:
        reason = gate(rec)
        if reason:
            gate_drops.append({"feedback_id": rec.get("feedback_id"),
                               "title": rec.get("title"), "reason": reason})
            issues[reason] += 1
        else:
            passed.append(sanitise(rec, issues))

    unique, dup_drops = deduplicate(passed)

    for rec in unique:
        hint, hits = relevance_hint(rec)
        rec["relevance_hint"] = hint
        rec["keyword_hits"] = hits

    unique.sort(key=lambda r: -(r.get("votes") or 0))

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    columns = ["feedback_id", "title", "description", "votes", "comments_count",
               "status", "category", "created_at", "source_url", "retrieved_at",
               "slug", "relevance_hint", "keyword_hits"]
    df = pd.DataFrame(unique)[columns]
    df.to_csv(PROC_DIR / "feedback_clean.csv", index=False, encoding="utf-8")

    nulls = {c: int(df[c].isna().sum()) for c in columns}
    likely = int(df["relevance_hint"].sum())

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_snapshot": snapshot.name,
        "counts": {
            "fetched": len(records),
            "failed_quality_gates": len(gate_drops),
            "duplicates_removed": len(dup_drops),
            "unique_records": len(unique),
            "likely_relevant_keyword_estimate": likely,
        },
        "gate_drops": gate_drops,
        "duplicate_drops": dup_drops,
        "sanitisation": dict(issues),
        "null_counts": nulls,
        "category_distribution": df["category"].value_counts(dropna=False).to_dict(),
        "status_distribution": df["status"].value_counts(dropna=False).to_dict(),
        "vote_stats": {
            "min": int(df["votes"].min()), "median": float(df["votes"].median()),
            "max": int(df["votes"].max()), "total": int(df["votes"].sum()),
            "zero_vote_records": int((df["votes"] == 0).sum()),
        },
        "note": "relevance is a keyword ESTIMATE only; the real judgment is made "
                "per record by the classification stage.",
    }
    (PROC_DIR / "quality_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(f"Snapshot              : {snapshot.name}")
    print(f"Fetched               : {len(records)}")
    print(f"Failed quality gates  : {len(gate_drops)}")
    print(f"Duplicates removed    : {len(dup_drops)}")
    print(f"UNIQUE RECORDS        : {len(unique)}")
    print(f"Keyword-likely relevant: {likely}  (estimate, not a claim)")
    print(f"\nWrote {PROC_DIR.relative_to(ROOT)}/feedback_clean.csv + quality_report.json")


if __name__ == "__main__":
    main()
