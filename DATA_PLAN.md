# Data Plan

The contract for collection, cleaning, and validation. Locked **before** collection so that no field is discovered missing after the fact — re-scraping to recover a forgotten field is the failure this document exists to prevent.

---

## 1. Source

| | |
|---|---|
| **Primary** | Port public feature-request portal — https://roadmap.port.io/ |
| **Documentation reference** | https://docs.port.io/workflows/actions-and-automations/create-self-service-experiences/ (taxonomy grounding only — not collected) |
| **Fallback** | **None.** G2 is out of scope. If the portal yields fewer than 50 relevant records, the project stops and reports the exact number. |
| **Method** | HTTP GET per post page → parse the embedded `window.__data` JSON. Verified feasible; see `docs/COLLECTION_FEASIBILITY.md`. |
| **Unit of analysis** | One feature request = one primary data point. Comments are supporting evidence and are **never** counted toward the ≥50 minimum. |

### Compliance rules (non-negotiable)

1. Publicly accessible content only.
2. `robots.txt` checked and obeyed before the first request.
3. No authentication bypass, no anti-bot circumvention, no rate-limit evasion.
4. Politeness delay ≥ 2.0s between requests; single-threaded; identifying User-Agent.
5. If retrieval is blocked → **stop, report, propose a compliant alternative.** Do not work around it.
6. No personal data collected beyond what anonymisation removes (§4).
7. Original `source_url` preserved on every record.

---

## 2. Record schema

Written to `data/raw/portal_snapshot_<UTC-timestamp>.json`. Fields unavailable from the source are stored as `null` and reported in the quality report — **never** inferred, estimated, or invented.

| Field | Type | Null? | Notes |
|---|---|---|---|
| `feedback_id` | str | No | Stable portal identifier (post ID or slug). Primary dedup key. |
| `title` | str | No | Verbatim. |
| `description` | str | Yes | Verbatim body. Null when the post has no body. |
| `votes` | int | Yes | Null = not exposed. Distinct from `0` = exposed and zero. |
| `comments_count` | int | Yes | Supporting signal only. |
| `status` | str | Yes | Portal's own status, verbatim (e.g. "planned", "in progress"). |
| `category` | str | Yes | Portal's own category, verbatim (e.g. "Self-service actions"). |
| `created_at` | ISO 8601 date | Yes | Post creation date as published. |
| `source_url` | str (URL) | No | Canonical, absolute. Required — a record without one is dropped. |
| `retrieved_at` | ISO 8601 datetime (UTC) | No | Set by the collector at fetch time. |
| `raw_html_hash` | str | No | SHA-256 of the fetched payload. Provenance and change detection. |

### Where each field comes from

Every post page embeds a `window.__data` JSON blob containing the full record. Confirmed present on a live post:

| Our field | `window.__data` source |
|---|---|
| `feedback_id` | `_id` |
| `title` | `title` |
| `description` | `details` |
| `votes` | `score` |
| `comments_count` | `commentCount` |
| `status` | `status` |
| `category` | `category` |
| `created_at` | `created` (already ISO 8601) |
| `source_url` | built from `urlName` → `/ideas/p/<urlName>` |
| `retrieved_at` | set by the collector |

`authorID` is also present in the blob and is **deliberately not collected**.

**`null` vs `0` is load-bearing.** A null vote count means "the portal does not show this"; zero means "shown, and it is zero". Conflating them would corrupt every vote-weighted metric. Aggregations exclude nulls from averages and report the excluded count.

### Immutability

`data/raw/` is write-once. Cleaning reads from it and writes elsewhere. Nothing downstream ever edits a raw snapshot — the snapshot is the evidence that the analysis is faithful to what was actually published.

---

## 3. Collection scope

The portal covers all of Port, so posts must be screened for relevance to Action Configuration.

**In scope** — the assignment's Action Configuration surface:
creating/editing actions · action forms and user inputs · input validation and conditional logic · backend and invocation configuration · permissions and dynamic permissions · manual and dynamic approvals · multi-step workflows · testing and editing actions · execution status, logs, monitoring · organising, displaying, and discovering actions · automations that directly affect action configuration.

**Out of scope:** catalog/blueprint modelling, scorecards, dashboards, integrations, billing, and AI-agent features — *unless* the post is specifically about configuring or running a self-service action.

### Two-stage relevance screening

Deliberately separated, because they answer different questions:

| | Stage A — collection screen | Stage B — LLM judgment |
|---|---|---|
| **When** | During collection | During classification |
| **How** | Keyword + category heuristic, **deliberately over-inclusive** | Full-text reasoning against taxonomy definitions |
| **Output** | Candidate pool (≥60) | `is_action_configuration_related` + `relevance_reason` |
| **Purpose** | Cast a wide net cheaply | Make the real, defensible call |

Stage A is intentionally loose: a false positive costs one LLM call and gets correctly excluded at Stage B, while a false negative is invisible and permanently lost. Stage B's exclusions are **kept in the dataset and shown**, not silently deleted — the count of irrelevant-but-collected posts is itself a reported quality metric.

**No padding.** Records are never included merely to reach 50. If the genuine count falls short, the exact number is reported and the decision escalated.

---

## 4. Anonymisation

Applied **at collection time**, before anything is written to disk. Nothing personal enters the repository and nothing personal is ever sent to the LLM.

| Data | Treatment |
|---|---|
| Author name / handle / avatar / profile URL | **Not collected at all** |
| Company or org names in author metadata | Not collected |
| Emails, phone numbers, tokens in body text | Regex-redacted to `[REDACTED_EMAIL]` etc.; redaction count logged |
| @-mentions in body text | Replaced with `[USER]` |
| Title, description, votes, comments count, status, category, tags, dates, URL | Retained verbatim — public product feedback |

Vote and comment counts are aggregate public metrics, not personal data. The `source_url` points to already-public content and is retained for verifiability.

---

## 5. Deduplication — three independent keys

Portals accumulate duplicates: merged posts, reposts, and near-identical requests filed separately.

| # | Key | Catches |
|---|---|---|
| 1 | `feedback_id` | The same post fetched twice (pagination overlap) |
| 2 | Canonical `source_url` | The same post reachable via different URLs (query strings, tracking params, redirects) |
| 3 | `sha256(normalised(title + description))` | Genuine reposts under different IDs |

**Text normalisation before hashing:** lowercase → collapse whitespace → strip punctuation → strip markdown. Aggressive by design; the goal is catching reposts, not preserving nuance.

**Resolution rule:** on collision, keep the record with the **highest vote count** (the canonical/most-engaged version); if votes tie, keep the earliest `created_at`. Every drop is logged with both IDs and the key that matched, so deduplication is auditable rather than a black box.

**Merged posts:** where the portal exposes posts merged into a parent, the parent is the record and the merged children are captured as a `merged_titles` list — evidence of demand concentration, not separate data points.

---

## 6. Quality gates

Run after dedup; results written to `data/processed/quality_report.json`.

| Gate | Rule | On failure |
|---|---|---|
| Required fields | `feedback_id`, `title`, `source_url` non-null | Drop record, log |
| URL validity | Absolute, well-formed, on `roadmap.port.io` | Drop record, log |
| Title length | ≥ 3 characters | Drop record, log |
| Body presence | `description` may be null | **Keep** — title-only posts are valid feedback |
| Vote sanity | Null or non-negative integer | Null it, log |
| Date sanity | Parseable, not in the future | Null it, log |
| Duplicate rate | Reported, not enforced | Informational |
| **Final count** | **≥ 50 unique relevant records** | **Stop and escalate** |

The quality report is a first-class deliverable, surfaced on the Methodology page. It records: fetched, dropped (by reason), deduplicated (by key), null counts per field, redaction count, and the final unique count.

---

## 7. Vote normalisation

Vote distributions on public boards are heavily right-skewed — a handful of posts hold most of the votes. Feeding raw counts into a priority score lets one popular request dominate every theme it appears in.

**Rule:** if the top theme's votes exceed 10× the median theme's, apply `log1p(votes)` before scaling to [0, 1]; otherwise scale directly. `log1p` (not `log`) because it is defined at zero.

Whichever applies, the dashboard says so in one sentence — e.g. *"Vote counts are on a log scale because the top request has 10× the votes of a typical one."* The choice is measured from the actual data, never asserted in advance.

**Null votes** are excluded from vote-based metrics; the excluded count is displayed next to any affected figure so a reader knows the denominator.

---

## 8. Provenance recorded per analysed record

| Field | Purpose |
|---|---|
| `model_name` | Which model produced the classification |
| `prompt_version` | Which prompt version; bumped on any prompt change |
| `analyzed_at` | UTC timestamp of the call |
| `confidence` | Model's self-reported certainty (quality signal only — never scored) |
| `evidence_verified` | **Computed in Python**, not generated by the LLM: was the excerpt found verbatim in the source? |

Provenance travels with each record so that any figure in the app can be traced to the exact model and prompt that produced it.

**LLM output schema — 9 fields:** `is_relevant`, `primary_theme`, `journey_stage`, `feedback_type`, `severity`, `short_summary`, `user_need`, `confidence`, `evidence_excerpt`.

---

## 10. Collection notes

**Independence.** Every record is fetched directly from `roadmap.port.io` by `src/collectors/`. Candidate slugs come solely from portal sweeps (roadmap views and list views). This project has **no dependency on any other dataset or project** — nothing is imported, seeded, or inherited.

**Parent vs merged posts.** Many high-vote parent posts are authored by Port staff as curated roll-ups; the customer voice lives in the requests merged into them. When selecting an `evidence_excerpt`, a merged child's text is the stronger source — quoting the parent risks quoting Port's own framing back to Port. The current collector captures parent posts only (merge data sits in the page activity feed); vote totals already aggregate merged children, so demand signal is unaffected. Tracked as an open improvement.

---

## 9. Acceptance criteria

Stage 4 (collection) is complete when:
- [ ] ≥60 candidate posts collected
- [ ] Immutable raw snapshot written with all schema fields present
- [ ] robots.txt compliance verified and documented
- [ ] Zero personal data in the snapshot

Stage 5 (cleaning) is complete when:
- [ ] All three dedup keys applied and every drop logged
- [ ] Quality report generated
- [ ] **≥50 unique relevant records confirmed** — or exact shortfall reported and escalated
- [ ] Every record has a working `source_url`
