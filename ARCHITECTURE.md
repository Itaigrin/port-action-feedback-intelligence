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
| Counts, totals, averages, rankings, priority scores, charts | Plain Python |

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

### D-6 — Confidence never affects priority
`confidence` measures *the model's certainty*, not *how much the problem matters*. Letting it raise a score would mean well-phrased feedback outranks urgent-but-ambiguous feedback. It is excluded from the priority formula entirely and shown separately as a quality indicator.

---

## Priority score

```
priority = 0.45 × normalized_votes + 0.30 × normalized_frequency + 0.25 × normalized_severity
```

45% demand, 30% how often it comes up, 25% how badly it hurts. All three components are normalized to 0–1 so they are comparable, then combined. Computed in plain Python, fully inspectable.

**Explicitly a POC method.** Real prioritization would also weigh customer segment, revenue impact, churn risk, strategic alignment, and engineering effort. Stated on the dashboard, not buried.

---

## Layout

```
app.py                  Streamlit app -- Dashboard tab (5 sections) + Guide tab
src/
  collectors/           portal fetch + parse
  models/               Pydantic schema + taxonomy (single source of truth for
                        themes, stages, guide metadata and glossary)
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
| Missing votes / description / date | Nullable in the schema; charts handle nulls explicitly |
| Zero relevant records | Explicit empty state, no crash |

---

## Testing — 7 checks only

1. ≥50 unique real feedback posts exist
2. No duplicate IDs or source URLs
3. Required fields populated
4. Evidence excerpts appear in the source text
5. Priority score calculates correctly
6. The Streamlit app starts
7. The app works from cached results with no API key

All offline. No test makes a network or API call.

---

## Production scale

| POC | Production |
|---|---|
| One public portal | Connectors per source (Slack, Zendesk, Gong), each with its own auth and schema |
| Fixed taxonomy, per-record LLM call | Embedding-based clustering to *discover* themes; LLM to label them |
| Files | Warehouse table + object storage |
| Manual run | Scheduled ingestion with monitoring |
| Votes as demand signal | Customer segment, ARR, churn risk, effort |
| Public feedback only | Joined to internal telemetry — the Part 1 funnel |

**Why a fixed taxonomy is right here and wrong at scale:** with ~60 records, a taxonomy drawn from Port's own documentation produces findings that point at pages the team already owns, and every record can be inspected by hand. Clustering 60 records produces unstable, hard-to-interpret groups. At thousands of records the trade reverses — a fixed taxonomy cannot discover a theme nobody thought to name, and per-record LLM calls stop being economic.

Slack, Zendesk, and Gong connections are **explained, not implemented**.
