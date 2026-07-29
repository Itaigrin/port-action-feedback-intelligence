"""Discover candidate post slugs on the Port portal.

Data extraction is cheap (one GET per post); *discovery* is the constraint,
because list views render only 10 posts at a time. Two complementary sources
are combined and deduplicated:

  1. Roadmap views  -- ~51 slugs per request
  2. List views     -- 10 slugs per (category x sort) combination

Only categories plausibly touching Action Configuration are swept. Relevance
is decided later by the LLM, so this stage is deliberately over-inclusive:
a false positive costs one call, a false negative is invisible and lost.
"""

from __future__ import annotations

import re
import time
from urllib.parse import quote_plus

import requests

from .portal import BASE, DELAY_SECONDS, USER_AGENT

_SLUG = re.compile(r"/ideas/p/([a-z0-9\-]+)")

# Port's own categories that can plausibly contain Action Configuration
# feedback. Deliberately broader than the strict definition.
CATEGORIES = [
    "self-service-actions",
    "workflows",
    "automations",
    "rbac-ownership",
    "audit-log",
]

SORTS = ["top", "trending", "new"]

# Keyword search reaches posts that pagination does not surface, and is the
# main way to recover depth in the Self-service actions category. Terms track
# the Action Configuration journey stages rather than being a generic word list.
SEARCH_TERMS = [
    # discovering and organising actions
    "self service action", "action catalog", "categorize actions",
    # forms and inputs
    "action input", "action form", "dropdown input", "default value",
    # validation and conditional logic
    "validation", "conditional", "jq query", "regex",
    # backend and invocation
    "action backend", "webhook trigger", "invocation", "action payload",
    # permissions and approvals
    "action permissions", "dynamic permissions", "manual approval", "approver",
    # testing and editing
    "test action", "edit action",
    # execution and monitoring
    "action run", "action logs", "retry action", "execution status",
    # multi-step / automation
    "multi step", "automation trigger",
]


def _slugs_from(session: requests.Session, url: str) -> set[str]:
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return set(_SLUG.findall(resp.text))
    except Exception:
        return set()


def discover(session: requests.Session | None = None,
             delay: float = DELAY_SECONDS,
             progress: bool = True) -> dict[str, list[str]]:
    """Sweep every discovery source. Returns {source: [slugs]}."""
    sess = session or requests.Session()
    sess.headers.setdefault("User-Agent", USER_AGENT)

    found: dict[str, list[str]] = {}

    def sweep(label: str, url: str) -> None:
        slugs = _slugs_from(sess, url)
        found[label] = sorted(slugs)
        if progress:
            print(f"  {len(slugs):3d} slugs  {label}", flush=True)
        time.sleep(delay)

    # 1. Roadmap views -- the richest single source
    sweep("roadmap:all", f"{BASE}/")
    for cat in CATEGORIES:
        sweep(f"roadmap:{cat}", f"{BASE}/?category={cat}")

    # 2. List views, per category and sort
    for cat in CATEGORIES:
        for sort in SORTS:
            sweep(f"list:{cat}:{sort}", f"{BASE}/ideas?category={cat}&sort={sort}")

    # 3. Keyword search -- reaches posts pagination does not surface
    for term in SEARCH_TERMS:
        sweep(f"search:{term}", f"{BASE}/ideas?search={quote_plus(term)}")

    return found


def merge(found: dict[str, list[str]]) -> list[str]:
    """Flatten discovery results into one deduplicated, ordered slug list."""
    seen: dict[str, None] = {}
    for slugs in found.values():
        for s in slugs:
            seen.setdefault(s, None)
    return list(seen)
