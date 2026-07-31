# Architecture

**Port Action Feedback Intelligence** — an independent take-home project. Not an official Port product, not affiliated with or endorsed by Port.

A focused Product Analyst proof of concept, not a production platform.

---

## The problem

Port's assignment states it directly: *"while many users start configuring an action, there is a significant drop-off before they reach their first successful trigger."*

Part 1 measures that drop-off — conversion, setup time, retries. It says **where** users fall out. It cannot say **why**.

This system reads Port's public feature-request portal and produces a ranked, evidence-backed answer to the "why", where every claim traces to a real post with a clickable link.

---

## Pipeline

```
Port Public Portal → Cleaning → AI Categorization → Aggregation → Streamlit Dashboard
```

At production scale the same shape applies with different inputs:

```
Slack / Zendesk / Gong → Cleaning → AI Categorization → Aggregation → Product Dashboard
```

Four steps, each writing a file, each re-runnable from the previous step's output:

| # | Step | Code | Output |
|---|---|---|---|
| 1 | **Collect** | `src/collectors/` | `data/raw/portal_snapshot_<UTC>.json` (immutable) |
| 2 | **Clean & dedupe** | `src/analysis/clean.py` | `data/processed/feedback_clean.csv` |
| 3 | **Classify (LLM)** | `src/analysis/classify.py` | `data/processed/analyzed.json` ← **committed** |
| 4 | **Aggregate & score** | `src/analysis/` | computed at app load, deterministic |
| 5 | **Present** | `app.py` | Streamlit app: Dashboard tab (five sections) + Guide tab |

**The central rule — who does what:**

| Concern | Owner |
|---|---|
| Reading, summarizing, categorizing feedback | LLM |
| Counts, totals, averages, rankings, charts | Plain Python |

An LLM is never asked to produce a number that appears in the dashboard. Every figure comes from pandas over the classified records. This is the single most important thing to be able to explain in an interview: **the AI reads, Python counts.**

---

## Design decisions

### D-1 — Files, not a database
CSV and JSON in `data/`. At ~60 records a database adds operational surface with no benefit, and files are readable directly in the repo.

### D-2 — The app never calls the network or the LLM
`app.py` reads `data/processed/analyzed.json` and nothing else. No HTTP, no API key, no LLM call at render time.

This is a hard contract. It means the demo cannot fail on someone else's machine, pages load instantly, and a reviewer without an API key sees the complete application. Verified by a test that loads the data with the environment stripped.

### D-3 — Native structured outputs, not `instructor`
The Anthropic SDK enforces a Pydantic schema during generation:

```python
response = client.messages.parse(output_format=FeedbackClassification, ...)
classification = response.parsed_output      # validated instance
```

Adding `instructor` would wrap an SDK feature in a third-party layer for no gain. Pydantic validation — the actual requirement — is fully satisfied.

### D-4 — Model configured, never hardcoded
Default `claude-sonnet-5`, read from `ANTHROPIC_MODEL`. Cost-effective while staying reliable on the one judgment the whole dataset rests on: *is this post really about Action Configuration?* `claude-haiku-4-5` is the cheaper alternative.

**On "low randomness":** `temperature`, `top_p`, and `top_k` are rejected by current models with a 400 error — they were removed from the API. Consistency comes instead from a fixed versioned prompt, closed enums the model cannot escape, and low effort. The real guarantee is that **the committed `analyzed.json` is a fixed artifact** — the demo replays stored classifications rather than re-running the model.

Stated honestly in the README: LLM classification is not reproducible run-to-run. We make the *deliverable* reproducible and measure agreement against human labels rather than claiming determinism.

### D-5 — Quote grounding is a hard gate
Every classification carries an `evidence_excerpt`. Before a record is accepted, that excerpt is verified as an **exact substring** of the source text. If it fails, a Python-computed `evidence_verified = False` is recorded and the excerpt is never displayed.

This is the strongest anti-fabrication control in the system: the model cannot attribute a complaint to a customer who never made it, because it cannot produce a quote that isn't in the source.

### D-6 — Confidence is a quality signal, never a ranking input
`confidence` measures *the model's certainty*, not *how much the problem matters*. Letting it lift a position would mean well-phrased feedback outranks urgent-but-ambiguous feedback. It appears only as the fifth tie-breaker — used when four earlier keys are already identical — and is shown separately as a data-quality indicator.

### D-7 — No weighted score, and no vote-based ranking
An earlier version ranked themes by `0.45 × votes + 0.30 × frequency + 0.25 × severity`. Both halves of that were wrong.

**The weights were indefensible.** Multiplying unlike signals by invented coefficients produces a number that looks precise and collapses the moment someone asks why 0.45 rather than 0.4. Ranking is now **lexicographic**: an explicit ordered list of tie-breakers, where every position can be explained by naming the single key that decided it.

**Votes do not generalise.** A vote total is meaningful inside one feedback portal and meaningless across Slack, Zendesk and Gong — there is nothing to vote with in a support ticket or a sales call. Ranking on a signal only one of four sources can produce would systematically bury every problem arriving through the other three. Votes are still collected and preserved as evidence; nothing is ranked by them.

---

## Product actions

### Grouping

Feedback is grouped by the change it asks for, in `src/analysis/grouping.py`, and each group stores its members explicitly.

This replaces grouping by taxonomy subcategory, which was a defect rather than a simplification: the subcategory *was* the group, so a card's count was the size of the whole subcategory and its drill-down opened onto all of it. One subcategory routinely holds several genuinely different requests.

Clustering normalises the suggested change, drops verbs that every suggestion shares, and agglomerates on the overlap coefficient — not Jaccard, which punishes a long phrasing paired with a terse one even when the terse one is contained in it. Merging is confined to a single subcategory, which acts as a fence rather than as the group. The threshold was tuned by sweeping against the real corpus and reading every merge it produced.

**Membership is the contract.** `open_supporting_record_count == len(open_supporting_feedback_ids)`, and the drill-down resolves by id. The count shown and the records opened are the same set by construction, not by two code paths that happen to agree.

### Ranking

Lexicographic over five keys; the first that differs decides the position.

1. **Severity band** — the *median* severity of the open supporting records. A higher band always ranks first, regardless of record count.
2. **Open records** — distinct open records supporting this exact action.
3. **Average confidence** — mean classification confidence.
4. **Source diversity** — distinct source systems.
5. **Latest created** — newest `created_at`; unknown dates rank last.

A sixth alphabetical key on the title makes the order total.

**Median, not maximum.** One unusually severe report should not make an otherwise mild request look critical. **No blended score:** each key is applied in turn, so no later key can override an earlier one, and every position can be explained by naming the single key that decided it.

**Only `Open` counts.** Planned and In progress mean the work is already committed; counting them as demand argues for building something already being built. They stay visible in the evidence section, labelled with their status.

## Feedback polarity

`feedback_polarity` is classified from the feedback text as `Negative`, `Positive` or `Neutral`, and is deliberately independent of `lifecycle_status`. A completed roadmap item still records the pain that prompted it, so deriving polarity from status would erase the original signal for everything already shipped.

It drives the two "where users struggle most" cards and the three-month trend chart, both of which count only Negative records — answering *where is the pain* rather than *where is the volume*.

## Layout## Layout

```
app.py                  Streamlit app -- Dashboard tab + Taxonomy & Journey Guide tab
src/
  collectors/           portal fetch + parse
  models/               Pydantic schema + taxonomy (single source of truth for
                        categories, subcategories, stages, problem types,
                        lifecycle statuses and guide metadata)
  analysis/             clean, dedupe, classify, aggregate, score, evaluate
data/
  raw/                  immutable snapshots — write once
  processed/            clean + analysed  ← the app's only input
  evaluation/           manual review sample
tests/                  7 essential checks
docs/                   feasibility report, architecture diagram, screenshots
```

Nothing under `src/` imports Streamlit, so all analysis logic is testable without running the app.

---

## Failure handling

| Failure | Response |
|---|---|
| Collection blocked | Stop and report. Never circumvent. |
| HTTP error on one post | Retry with backoff, then skip and log |
| LLM timeout / malformed response | SDK retry, then re-validate; persistent failure → record marked failed, run continues |
| Excerpt not found in source | `evidence_verified = False`; excerpt withheld from display |
| Run interrupted | Cached results let the next run resume where it stopped |
| Missing description / date | Nullable in the schema; charts handle nulls explicitly |
| Unrecognised portal status | Normalised to `Unknown`, never passed through as if mapped |
| Model returns a subcategory from the wrong category | Rejected by a Pydantic model validator before the record is stored |
| Zero relevant records | Explicit empty state, no crash |

---

## Testing

1. ≥50 unique real feedback posts exist, all pointing at real portal URLs
2. No duplicate IDs or source URLs, and dedup is verified against *planted* duplicates — a dedup step that silently does nothing produces the same "0 duplicates" result as one that works
3. Required fields populated; every label falls inside a closed vocabulary
4. Category/subcategory pairs are internally consistent; retired names are **rejected by the schema**, not merely undocumented
5. Out-of-scope records carry no taxonomy at all, so they cannot reach a total
6. Evidence excerpts appear in the source text, and fabricated quotes are rejected
7. The ranking is recomputed by hand from raw records, and asserted to be lexicographic and total
8. No record claims a source system it did not come from
9. The Streamlit app starts, and works from cached results with no API key

All offline. No test makes a network or API call.

---

## Production scale

| POC | Production |
|---|---|
| One public portal | Connectors per source (Slack, Zendesk, Gong), each with its own auth and schema |
| Fixed taxonomy, per-record LLM call | Embedding-based clustering to *discover* categories; LLM to label them |
| Files | Warehouse table + object storage |
| Manual run | Scheduled ingestion with monitoring |
| Open-record count, severity, source diversity | Plus customer segment, ARR, churn risk, engineering effort |
| Public feedback only | Joined to internal telemetry — the Part 1 funnel |

**Why a fixed taxonomy is right here and wrong at scale:** with ~60 records, a taxonomy drawn from Port's own documentation produces findings that point at pages the team already owns, and every record can be inspected by hand. Clustering 60 records produces unstable, hard-to-interpret groups. At thousands of records the trade reverses — a fixed taxonomy cannot discover a category nobody thought to name, and per-record LLM calls stop being economic.

Slack, Zendesk, and Gong connections are **explained, not implemented**.
