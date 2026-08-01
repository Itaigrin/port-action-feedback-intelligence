"""Cluster feedback into product actions by the change each record asks for.

WHY THIS EXISTS
---------------
Product actions used to be taxonomy subcategories. That made the supporting
count wrong in a specific, misleading way: a card reading "4 open supporting
records" opened onto every record in its subcategory, because the subcategory
*was* the group. "Authentication, execution identity & requester context"
holds OAuth delegation, service accounts, JWT forwarding and impersonation
controls -- four different product changes presented as one recommendation.
Taxonomy v3.0 makes that worse rather than better: consolidating 63
subcategories into 30 puts more distinct requests inside each one.

Grouping now happens here, on the change being requested, and every group
carries the exact feedback ids that belong to it.

WHY NOT GROUP ON THE TEXT DIRECTLY
----------------------------------
`suggested_product_action` is phrased as a grouping key by the prompt, but in
the current dataset all 182 in-scope records produce a distinct string. Exact
text matching would return 182 groups of one, which is the same failure as
before with the opposite bias.

So: normalise, then agglomerate on token overlap, but only within a single
subcategory. The subcategory is no longer the group -- it is a fence that stops
"support templates for approval policies" merging with "support templates for
form layouts" on the shared word *templates*. Merging is single-link over a
similarity threshold, which is deterministic and needs no model call.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Words that carry no signal about *which* change is being asked for. Every
# suggested action starts with a verb like "support" or "add", so leaving them
# in would make unrelated requests look similar.
_STOP = frozenset("""
a an the and or but for to of in on at by with from into onto via as is are be
been being it its this that these those we our us you your they their there
should could would can cannot able allow allows allowing enable enables
enabling support supports supporting add adds adding provide provides
providing make makes making let lets letting give gives giving so that when
where which who what how not no any all each per via using use used user users
action actions port feature capability ability option options ensure required
require requires need needs also more than then more most other others new
""".split())

_WORD = re.compile(r"[a-z0-9]+")

# Two actions merge when this share of the smaller token set is common to both.
#
# Tuned by sweeping against the real corpus and reading every merge it produced.
# At 0.62 only 3 pairs joined; at 0.45 nine groups form and each one is the same
# request twice ("add a cancel/stop control", "expose the approver's identity",
# "enforce validation server-side"). Going lower began merging distinct requests,
# so 0.45 is the loosest setting that produced no false merge on this data.
SIMILARITY_THRESHOLD = 0.45

# Below this many meaningful tokens a text carries too little signal to cluster
# on, so it stays in its own group rather than absorbing a neighbour.
MIN_TOKENS = 3


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    return " ".join(_WORD.findall(text))


def tokens(text: str) -> frozenset[str]:
    return frozenset(w for w in normalise(text).split()
                     if w not in _STOP and len(w) > 2)


def similarity(a: frozenset[str], b: frozenset[str]) -> float:
    """Overlap coefficient, not Jaccard.

    Jaccard punishes a long phrasing paired with a terse one even when the
    terse one is entirely contained in it -- which is exactly how the same
    request tends to differ between a Slack line and a support ticket.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def slugify(text: str, limit: int = 60) -> str:
    words = [w for w in normalise(text).split() if w not in _STOP][:8]
    return "-".join(words)[:limit] or "product-action"


def cluster(records: list[dict]) -> list[list[dict]]:
    """Group records asking for substantially the same change.

    Single-link agglomeration inside each subcategory. Order-independent: the
    records are sorted by id first, so the same input always yields the same
    grouping regardless of how the frame was built.
    """
    by_subcategory: dict[str, list[dict]] = {}
    for record in sorted(records, key=lambda r: str(r["feedback_id"])):
        by_subcategory.setdefault(
            record.get("primary_taxonomy_subcategory") or "", []).append(record)

    groups: list[list[dict]] = []
    for members in by_subcategory.values():
        buckets: list[tuple[frozenset[str], list[dict]]] = []
        for record in members:
            signature = tokens(record.get("suggested_product_action", ""))
            placed = False
            if len(signature) >= MIN_TOKENS:
                for index, (existing, bucket) in enumerate(buckets):
                    if similarity(signature, existing) >= SIMILARITY_THRESHOLD:
                        bucket.append(record)
                        # Single-link: the bucket's signature grows, so a third
                        # record can join through either of the first two.
                        buckets[index] = (existing | signature, bucket)
                        placed = True
                        break
            if not placed:
                buckets.append((signature, [record]))
        groups.extend(bucket for _signature, bucket in buckets)
    return groups


def canonical_title(group: list[dict]) -> str:
    """The wording that labels a group.

    One real record's sentence, never a synthesis: the most common phrasing if
    several agree, otherwise the highest-severity record's, with the id kept
    alongside so a dashboard label always traces to a specific piece of
    feedback.
    """
    counts = Counter(r.get("suggested_product_action", "") for r in group)
    best, hits = counts.most_common(1)[0]
    if hits > 1:
        return best
    ordered = sorted(
        group,
        key=lambda r: (-int(r.get("severity", 0)),
                       -float(r.get("confidence", 0.0)),
                       str(r["feedback_id"])),
    )
    return ordered[0].get("suggested_product_action", "")


def title_source_id(group: list[dict], title: str) -> str:
    for record in sorted(group, key=lambda r: str(r["feedback_id"])):
        if record.get("suggested_product_action", "") == title:
            return str(record["feedback_id"])
    return str(group[0]["feedback_id"])
