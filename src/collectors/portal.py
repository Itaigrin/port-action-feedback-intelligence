"""Collect feature requests from Port's public feature-request portal.

The portal (roadmap.port.io, Canny-hosted) server-renders every page with a
`window.__data` JSON blob containing complete post records. So collection is a
plain HTTP GET plus a JSON parse -- no browser, no HTML scraping.

Compliance (see docs/COLLECTION_FEASIBILITY.md):
  - robots.txt is `User-agent: * / Disallow:` -- unconditional permission.
  - We still self-impose a 2s delay, single-threaded, identifying User-Agent.
  - Public pages only. Nothing is bypassed.
  - authorID and voter names are never collected.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable

import requests

BASE = "https://roadmap.port.io"
POST_URL = BASE + "/ideas/p/{slug}"

# Politeness. Do not lower.
DELAY_SECONDS = 2.0
TIMEOUT = 30

USER_AGENT = (
    "PortActionFeedbackIntelligence/1.0 (independent take-home research project; "
    "polite crawler, 2s delay)"
)

# --- PII redaction ---------------------------------------------------------
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_MENTION = re.compile(r"(?<![\w/])@[A-Za-z0-9_.-]{2,}")


def redact(text: str | None) -> tuple[str | None, int]:
    """Strip personal identifiers from free text. Returns (text, n_redactions)."""
    if not text:
        return text, 0
    n = 0
    text, k = _EMAIL.subn("[REDACTED_EMAIL]", text)
    n += k
    text, k = _MENTION.subn("[USER]", text)
    n += k
    return text, n


# --- window.__data extraction ---------------------------------------------
_MARKER = re.compile(r"window\.__data\s*=\s*")

# The blob is JavaScript, not strict JSON: Canny emits bare `undefined` for
# unset cookie values (e.g. `"__canny__browserTheme":undefined`). Rewrite those
# to null before parsing. The lookbehind/lookahead keep this to value
# positions rather than matching the word inside arbitrary prose.
_UNDEFINED = re.compile(r"(?<=[:,\[])\s*undefined\s*(?=[,}\]])")


def extract_window_data(html: str) -> dict[str, Any]:
    """Pull the embedded `window.__data` object out of a rendered page."""
    m = _MARKER.search(html)
    if not m:
        raise ValueError("window.__data not found in page")
    start = html.find("{", m.end())
    if start == -1:
        raise ValueError("window.__data present but no opening brace")
    cleaned = _UNDEFINED.sub("null", html[start:])
    # raw_decode reads exactly one JSON value and reports where it ended,
    # which handles nested braces and braces inside strings correctly.
    obj, _ = json.JSONDecoder().raw_decode(cleaned, 0)
    return obj


def _find_post(node: Any, depth: int = 0) -> dict[str, Any] | None:
    """Locate the post record inside the state blob."""
    if depth > 6 or not isinstance(node, (dict, list)):
        return None
    if isinstance(node, dict):
        if "title" in node and "urlName" in node and "score" in node:
            return node
        for value in node.values():
            found = _find_post(value, depth + 1)
            if found:
                return found
    else:
        for value in node:
            found = _find_post(value, depth + 1)
            if found:
                return found
    return None


# --- Record ----------------------------------------------------------------
@dataclass
class FeedbackRecord:
    feedback_id: str
    title: str
    description: str | None
    votes: int | None
    comments_count: int | None
    status: str | None
    category: str | None
    created_at: str | None
    source_url: str
    retrieved_at: str
    # provenance / analysis support -- not part of the required 10 fields
    slug: str
    merged_titles: list[str]
    payload_hash: str
    redactions: int


def _category_name(raw: Any) -> str | None:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("name")
    return None


def _merged_titles(state: dict[str, Any]) -> list[str]:
    """Titles of posts merged into this one -- these carry the customer voice."""
    titles: list[str] = []

    def walk(node: Any, depth: int = 0) -> None:
        if depth > 6 or not isinstance(node, (dict, list)):
            return
        if isinstance(node, dict):
            if node.get("type") == "merge" and isinstance(node.get("post"), dict):
                t = node["post"].get("title")
                if t:
                    titles.append(t)
            for value in node.values():
                walk(value, depth + 1)
        else:
            for value in node:
                walk(value, depth + 1)

    walk(state)
    return sorted(set(titles))


def parse_post(html: str, slug: str) -> FeedbackRecord:
    state = extract_window_data(html)
    post = _find_post(state)
    if not post:
        raise ValueError(f"no post record found for slug {slug!r}")

    description, n1 = redact(post.get("details"))
    title, n2 = redact(post.get("title") or "")

    return FeedbackRecord(
        feedback_id=str(post.get("_id") or slug),
        title=title,
        description=description or None,
        votes=post.get("score"),
        comments_count=post.get("commentCount"),
        status=post.get("status"),
        category=_category_name(post.get("category")),
        created_at=post.get("created"),
        source_url=POST_URL.format(slug=post.get("urlName") or slug),
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        slug=post.get("urlName") or slug,
        merged_titles=_merged_titles(state),
        payload_hash=sha256(html.encode("utf-8", "replace")).hexdigest(),
        redactions=n1 + n2,
    )


# --- Fetching --------------------------------------------------------------
def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html"})
    return s


def fetch_post(slug: str, session: requests.Session | None = None,
               retries: int = 3) -> FeedbackRecord | None:
    """Fetch and parse one post. Returns None if it cannot be retrieved."""
    sess = session or _session()
    url = POST_URL.format(slug=slug)
    for attempt in range(retries):
        try:
            resp = sess.get(url, timeout=TIMEOUT)
            if resp.status_code == 404:
                return None                      # deleted or renamed post
            resp.raise_for_status()
            # The portal sends `Content-Type: text/html` with no charset, so
            # requests falls back to ISO-8859-1 and mangles every non-ASCII
            # character (curly quotes, em dashes) into mojibake. The bytes are
            # UTF-8; say so explicitly.
            resp.encoding = "utf-8"
            return parse_post(resp.text, slug)
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)             # backoff on transient failure
    return None


def collect(slugs: Iterable[str], delay: float = DELAY_SECONDS,
            progress: bool = True) -> tuple[list[dict], list[str]]:
    """Fetch every slug politely. Returns (records, failed_slugs)."""
    sess = _session()
    records: list[dict] = []
    failed: list[str] = []
    slugs = list(dict.fromkeys(slugs))           # dedupe, preserve order

    for i, slug in enumerate(slugs, 1):
        rec = fetch_post(slug, sess)
        if rec is None:
            failed.append(slug)
        else:
            records.append(asdict(rec))
        if progress:
            print(f"  [{i}/{len(slugs)}] {'ok  ' if rec else 'FAIL'} {slug}", flush=True)
        if i < len(slugs):
            time.sleep(delay)

    return records, failed
