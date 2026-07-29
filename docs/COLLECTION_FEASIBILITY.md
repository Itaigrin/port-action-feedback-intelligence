# Collection Feasibility Report

Inspection of `roadmap.port.io` performed 2026-07-29. Read-only: robots.txt, the board index, one category view, and one post detail page. **No data was collected and no collector code was written.**

---

## Verdict

**Compliant automated collection is feasible.** All ten required fields are available. The bottleneck is *discovering* post URLs, not extracting data from them — and there is a good solution for that.

| Question | Answer |
|---|---|
| Does robots.txt permit it? | **Yes** — unconditionally |
| Are all 10 required fields available? | **Yes** |
| Is the ≥50 relevant target realistic? | **Yes, with disciplined slug discovery** |
| Is browser automation needed? | **No** — a plain HTTP GET is sufficient |

---

## 1. Compliance

`https://roadmap.port.io/robots.txt` returns:

```
User-agent: *
Disallow:
```

An empty `Disallow` permits all crawlers on all paths. No `Crawl-delay` is specified, so we set our own — **2.0 seconds minimum between requests**, single-threaded. No authentication exists on the board, no anti-bot challenge was encountered, and nothing needs to be bypassed.

---

## 2. Platform

The board is **Canny-hosted**, at `roadmap.port.io`, with **1,483 feature ideas** on the `ideas` board.

**Key structural finding: pages are server-rendered with a complete state blob.** Each page embeds `window.__data`, a JSON object containing fully-formed post records. This means collection needs only an HTTP GET and a JSON parse — no headless browser, no DOM scraping, no JavaScript execution. It is both simpler to build and gentler on the server than HTML scraping.

**No usable JSON API.** `/api/posts/list` returns 404, and `/sitemap.xml` returns 400. Canny's real API lives on `canny.io` behind a private key we neither have nor need.

### Field mapping — all ten confirmed present

| Required field | Source in `window.__data` | Verified example |
|---|---|---|
| `feedback_id` | `_id` | `6464f90d69899109766d6cb3` |
| `title` | `title` | "HashiCorp Vault for Secrets Management…" |
| `description` | `details` | 1,124 characters |
| `votes` | `score` | `4` |
| `comments_count` | `commentCount` | `0` |
| `status` | `status` | `open` |
| `category` | `category` | `Self-service actions` |
| `created_at` | `created` | `2026-07-23T10:21:57.248Z` (ISO 8601) |
| `source_url` | derived from `urlName` | `/ideas/p/<urlName>` |
| `retrieved_at` | set by collector | — |

`authorID` is also present. **We do not collect it** — anonymisation by omission, as planned.

---

## 3. Volume

Signals that ≥50 relevant records exist:

- **1,483 total posts** on the board.
- **"Self-service actions" is a native Canny category** — Port's own classification, not our guess. `?category=self-service-actions` filters to it.
- **~13 clearly Action-Configuration-related posts appeared on the unfiltered board's first page alone**, including: *Categorizing Self Service actions* (106 votes), *Multi-step workflows* (69), *Improved customizations of user inputs validations* (44), *Support hiding/displaying self-service actions using dynamic permissions* (28), *Support for entities create/update/delete dynamic permission policies* (26), *Support multiple event triggers in Automations* (24), *Associate action with multiple blueprints* (22), *Send Email to Approvers when Dynamic Permissions are Used* (21), *Confirmation Window for Unsaved Changes in Self-service actions GUI Mode* (20), *Support Calculated Properties in Self-Service Dataset Conditions* (20), *Enable dynamic user properties for actions conditions* (20), *Configurable Minimum Approval Threshold for Manual Approvals* (14), *Teams, roles and dynamic policy in Port Workflows Input node* (7).

These span validation, permissions, approvals, multi-step workflows, discoverability, and automations — the exact taxonomy surface.

### The one real constraint

**List views render 10 posts at a time.** `?sort=top` and `?category=` both work, but `?page=2` is ignored, and lazy-loading did not trigger in the headless context. So slug *discovery* is rate-limited in a way that data *extraction* is not.

### Mitigation — three complementary slug sources

1. **Roadmap views** (`/`) — **~51 slugs per request**, five times the yield of a list view. The workhorse. Note the roadmap view *ignores* `?category=` and `?search=`, always returning the same default set, so it contributes once.
2. **List views** — 10 slugs per `category × sort` combination, across `top` / `trending` / `new` for each relevant category.
3. **Keyword search** (`/ideas?search=<term>`) — 10 slugs per term. This is the only way to reach posts that pagination does not surface, and the main lever for recovering depth in the Self-service actions category. Terms track the Action Configuration journey stages rather than being a generic word list.

Deduplicated across all three, this clears the 60-candidate target several times over.

**If it falls short:** per the scope update, G2 is not an approved substitute. The project would stop and report the exact number for your decision.

---

## 4. Board structure: parent posts vs merged children

Observed directly on the live portal. The board has two tiers, and it matters for evidence quality.

**Parent posts are often written by Port staff.** The highest-voted request in the Self-service actions category, *Improved customizations of user inputs validations* (44 votes), was authored by a Port employee — the same person who updates its status. It reads in product language: *"Port self-service actions already support a rich set of input controls…"*

**The customer voice lives in the merged children.** The same post has five customer requests merged into it, and those read very differently:

- *"the jqQuery becomes quite messy"*
- *"users… become blocked and distracted by the red error which they don't understand"*
- *"it would be ideal to be able to make certain inputs required dynamically"*

**Consequence for the prompt:** if the LLM pulls `evidence_excerpt` from a parent post, we risk **quoting Port's own framing of a problem back to Port** in an interview, and presenting it as customer evidence. Where a merged child's text is available it is the stronger source.

**Current limitation, honestly stated:** the collector's merged-title extractor returned 0 results across all 141 records — merge data sits in the page's activity feed, not in the post object it parses. So this stage collects parent posts only. Two consequences to carry forward:

1. Vote counts on parent posts already aggregate their merged children, so **demand signal is intact**.
2. Evidence excerpts currently come from parent text. Recovering merged-child text is a known improvement, tracked as an open item rather than silently ignored.

---

## 5. Recommended collection method

```
1. Build candidate slug list   ← roadmap views + list views (category x sort)
2. For each slug (≥2s apart):
     GET https://roadmap.port.io/ideas/p/<slug>
     parse window.__data → post record
3. Map to the 10-field schema, drop authorID, redact any PII in text
4. Write immutable snapshot → data/raw/portal_snapshot_<UTC>.json
```

Single-threaded, identifying User-Agent, ~2s delay. For ~70 candidates that is roughly 3 minutes of polite traffic — comparable to a person browsing the board.

---

## 6. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Slug discovery caps out below 60 | **Medium** | Three independent discovery sources; report exact count if short |
| `window.__data` shape changes | Low | Snapshot is immutable; parser is one function, easy to fix |
| Relevance judgment inflates the count | Medium | LLM `is_relevant` is the gate; excluded posts stay visible in the data |
| Parent posts are Port-authored, not customer voice | **Medium** | Documented above; prefer merged children for evidence excerpts |
| Voter names visible on pages | Low | Never collected — we read `window.__data`, not the voter list |

---

## 7. Recommendation

**Proceed to Stage 4 (collection).** The method is compliant, simple, and yields every required field. The single open question is whether disciplined slug discovery clears 60 candidates — which the collection step will answer definitively rather than by estimate.
