"""Run the full collection: discover slugs, fetch posts, write a raw snapshot.

    python -m src.collectors.run              # reuse cached slug discovery
    python -m src.collectors.run --refresh    # re-sweep discovery first

Writes an immutable snapshot to data/raw/portal_snapshot_<UTC>.json. Existing
snapshots are never modified -- each run produces a new timestamped file.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import slugs as slug_discovery
from .portal import collect

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
DISCOVERY_FILE = RAW_DIR / "_discovery.json"


def get_slugs(refresh: bool) -> tuple[list[str], dict]:
    if not refresh and DISCOVERY_FILE.exists():
        cached = json.loads(DISCOVERY_FILE.read_text(encoding="utf-8"))
        print(f"Using cached discovery: {len(cached['merged'])} slugs")
        return cached["merged"], cached["sources"]

    print("Discovering candidate slugs (2s between requests)...")
    sources = slug_discovery.discover()
    merged = slug_discovery.merge(sources)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DISCOVERY_FILE.write_text(
        json.dumps({"sources": sources, "merged": merged}, indent=2), encoding="utf-8"
    )
    return merged, sources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="re-run slug discovery instead of using the cache")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap the number of posts fetched (for testing)")
    parser.add_argument("--refetch", action="store_true",
                        help="re-fetch every post instead of reusing the last snapshot")
    args = parser.parse_args()

    candidates, sources = get_slugs(args.refresh)
    if args.limit:
        candidates = candidates[: args.limit]

    # Reuse anything already collected -- re-fetching identical pages would put
    # avoidable load on Port's servers. A fresh clone has no snapshot and so
    # performs a full run; the result is the same either way.
    existing: dict[str, dict] = {}
    prior = sorted(RAW_DIR.glob("portal_snapshot_*.json"))
    if prior and not args.refetch:
        old = json.loads(prior[-1].read_text(encoding="utf-8"))
        existing = {r["slug"]: r for r in old["records"]}
        print(f"Reusing {len(existing)} already-collected records "
              f"from {prior[-1].name}")

    todo = [s for s in candidates if s not in existing]
    print(f"\nFetching {len(todo)} new posts at 2s intervals "
          f"(~{len(todo) * 2 / 60:.1f} min)...")
    fresh, failed = collect(todo) if todo else ([], [])

    kept = [existing[s] for s in candidates if s in existing]
    records = kept + fresh

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"portal_snapshot_{stamp}.json"

    snapshot = {
        "meta": {
            "source": "https://roadmap.port.io/",
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "robots_txt": "User-agent: * / Disallow: (unconditional permission)",
            "delay_seconds": 2.0,
            "candidates_discovered": len(candidates),
            "records_collected": len(records),
            "failed_slugs": failed,
            "discovery_sources": {k: len(v) for k, v in sources.items()},
            "note": "authorID and voter identities are never collected; "
                    "emails and @-mentions in text are redacted at collection time.",
        },
        "records": records,
    }
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"Collected : {len(records)} / {len(candidates)} candidates")
    print(f"Failed    : {len(failed)}")
    print(f"Redactions: {sum(r['redactions'] for r in records)}")
    print(f"Snapshot  : {out.relative_to(ROOT)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
