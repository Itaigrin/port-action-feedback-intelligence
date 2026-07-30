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

## Ranking product actions

Open feedback is grouped by taxonomy subcategory, and each group becomes one candidate product action. Groups are ordered by applying these keys in sequence; the first that differs decides the position.

1. **Critical** — a gate: at least 3 open records **and** an average severity of 4.0 or above.
2. **Open records** — how many distinct open records ask for this change.
3. **Severity band** — average severity, rounded. How much it hurts when it happens.
4. **Max severity** — the single worst record in the group.
5. **Source diversity** — how many different source systems raised it.
6. **Average confidence** — a data-quality tie-breaker only.
7. **Recency** — the newest supporting record.

**Why a gate rather than another sort key.** Being widely reported *and* severe is the one combination that should beat a larger but milder problem, and it is not a quantity that can be traded off — an action either clears both floors or it does not. Both floors earn their place: the record floor blocks four singletons at severity 4.0, and the severity floor blocks *RBAC & dynamic permissions*, which has ten records but averages 3.5. Two of 54 actions qualify.

**The gate tests the raw mean, not the rounded band.** That decides a real case rather than a hypothetical one: 3.5 rounds to a band of 4, so testing the band would admit RBAC under a rule written as "4 and above". `tests/test_pipeline.py::test_critical_gate_requires_both_floors` asserts at least one such action exists and is excluded, so the distinction cannot be lost silently.

Because the severity chip on a card shows the *rounded* band, an action averaging 3.5 reads "Severity 4" while ranking below one that cleared the gate. Cards that clear it therefore carry a **Critical** badge, so the order is explicable on sight rather than looking arbitrary.

A final alphabetical key makes the order **total**, so the same input always produces the same ranking rather than one that depends on row order.

**Why volume leads severity below the gate.** The first version of this ranking put severity first, matching the "rank by severity, break ties by count" sketch in the design write-up. Run against the full dataset it produced an indefensible list: a single severity-4 request for Vault integration outranked a problem eight independent records reported. Severity is one model's reading of one piece of text, so a lone high-severity record is a far weaker signal than several records converging. High severity is surfaced instead as its own KPI and sidebar filter, where a small number of severe records stays visible without displacing widely-reported ones.

**Only open records count.** `Completed` and `Closed` are excluded via `OPEN_STATUSES`, so shipped work cannot argue for itself again. Those records stay visible in the evidence explorer, where "we already built this" is itself a finding.

**Grouping is by subcategory, not by the text of `suggested_product_action`.** Two records asking for the same change rarely phrase it identically, so text grouping would shatter real demand into singletons. The subcategory is the closed key the model was constrained to, and is therefore the only grouping that counts reliably. Each group's displayed label is one real record's wording, chosen deterministically and stored alongside that record's id — so a label on the dashboard always traces to the feedback it came from.

**Explicitly a POC method.** Real prioritization would also weigh customer segment, revenue impact, churn risk, strategic alignment, and engineering effort. Stated on the dashboard, not buried.

---

## Layout

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
