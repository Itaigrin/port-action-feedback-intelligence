# Design answers

Direct answers to the two design questions from Part 2 of the assignment, written as standalone prose rather than scattered across the implementation docs. Everything here is backed by working code in this repository — where a claim is demonstrated rather than just asserted, the file is named.

---

## 1. "Explain how you would design such a system?"

### The problem shape

Port receives qualitative feedback about Action Configuration from three sources — Slack, Zendesk, Gong — each with a different structure, a different signal-to-noise ratio, and a different reason someone wrote something down. A system that treats them identically will average away exactly the differences that matter: a Slack message is a passing complaint, a Zendesk ticket is a problem someone cared enough to file formally, a Gong call is what a paying customer said out loud to a human who could act on it. Design has to start from that asymmetry, not from "ingest everything into one pipeline."

### The pipeline

```
Sources → Cleaning & dedup → AI categorisation → Deterministic aggregation → Product dashboard
```

Five stages, each a separate, independently re-runnable unit that writes a durable artifact before the next stage reads it. This project implements the shape end-to-end against one public source (`src/collectors/` → `src/analysis/clean.py` → `src/analysis/classify.py` → `src/analysis/aggregate.py` → `app.py`); production swaps stage 1 for three source-specific connectors and leaves the rest of the shape intact.

**The single design decision everything else follows from:** the LLM reads and categorises; ordinary code counts, ranks, and scores. An LLM call is not reproducible run-to-run and cannot be audited the way a `pandas.groupby` can. Every number a product manager will make a roadmap decision from — theme frequency, vote totals, the priority score — is produced by deterministic Python, and nothing in that path calls the model. See `ARCHITECTURE.md` → *"The central rule — who does what"* for the full statement, and `src/analysis/aggregate.py` for the code that enforces it.

### Per-stage design choices, and why

**Collection.** Each source needs its own extraction logic, but they converge on one schema before anything downstream sees them. Slack needs thread reconstruction — a complaint and its resolution are separate messages that must be joined. Zendesk tickets already carry structured metadata (status, resolution, tags) that should be preserved, not discarded. Gong is transcribed speech, where *who* said a sentence changes how much weight it deserves — a customer's frustration and a rep's paraphrase of it are not the same evidence. This project's collector (`src/collectors/portal.py`) demonstrates the pattern once, against Port's public board: source-specific extraction, normalised into one record shape, written to an **immutable** raw snapshot before any cleaning touches it — so a bug downstream can never corrupt the evidence of what was actually said.

**Cleaning and deduplication.** Real feedback streams contain the same complaint restated, cross-posted, or merged by an agent closing a duplicate ticket. Deduplication needs multiple independent keys — an ID match, a canonical-URL match, and a normalised-text-hash match — because no single key catches every duplicate shape. `src/analysis/clean.py` implements exactly this, and it is unit-tested against planted duplicates rather than only checked against real data (`tests/test_pipeline.py::test_deduplication_catches_planted_duplicates`), because a dedup step that silently does nothing produces the same "0 duplicates" result as one that works — the difference only shows up if you deliberately try to break it.

**AI categorisation.** Covered in full under question 2 below.

**Aggregation and scoring.** Once records carry a theme, a stage, a severity and a feedback type, everything a product team wants — volume by theme, demand by stage, a priority ranking — is arithmetic over a table. No LLM call belongs in this stage. `src/analysis/aggregate.py` computes a transparent priority score (45% vote-weighted demand, 30% frequency, 25% severity — see the priority-score design decision below) and is independently re-verified: the score is recomputed by hand from raw records in `tests/test_pipeline.py::test_priority_score_recomputed_by_hand`, not just re-run through the same function that produced it.

**Presentation.** A dashboard is only as trustworthy as its traceability. Every aggregate figure in this system's UI links back to the individual records that produced it — the Evidence Explorer section of the dashboard is that traceability made concrete, not an afterthought bolted onto a chart.

### Design principles that generalise beyond this POC

1. **Immutable raw storage.** Never let a cleaning bug erase evidence of what a customer actually said. Raw goes in once and is never edited.
2. **The AI does language; code does arithmetic.** This is not a stylistic preference — it is the only way a stakeholder can audit *why* a number is what it is, and the only way the same input reliably produces the same output.
3. **A transparent, adjustable scoring formula**, not a black box. `priority = 0.45 × demand + 0.30 × frequency + 0.25 × severity`, stated on the dashboard in one sentence, with the weights visible and changeable. See `ARCHITECTURE.md` → *Priority score*.
4. **Confidence is a quality signal, never an input to ranking.** A model being *certain* about a classification says nothing about how much the underlying problem *matters* — conflating the two would let well-phrased feedback systematically outrank urgent, messy feedback. See design decision D-6 in `ARCHITECTURE.md`.
5. **Human review as a first-class stage, not an afterthought.** A stratified sample, reviewed independently, with disagreements surfaced rather than smoothed over. This project's evaluation stage (`src/analysis/evaluate.py`) reports **"Not yet evaluated"** until real human labels exist — there is no code path that can display a fabricated accuracy figure. At production scale this becomes a rotating stratified sample per ingestion batch, two independent reviewers, and a frozen gold set to regression-test prompt changes against.
6. **Taxonomy versioning, not silent relabelling.** When the categorisation scheme changes for a real reason — as it did once in this project, from 12 themes to 11 with a taxonomy revision — every affected record is *reclassified* under the new scheme rather than string-replaced, because a semantic change in what a category means invalidates old labels even if their names happen to survive.

### What changes at Slack/Zendesk/Gong scale, specifically

| This POC (≈300 records, one source) | Production (thousands of records, three sources) |
|---|---|
| Fixed taxonomy, defined from Port's own documentation | Embedding-based clustering *discovers* themes; the LLM labels and summarises the clusters afterward |
| One LLM call per record | Batched classification; clustering-first reduces total LLM spend |
| Files (CSV/JSON) as the data layer | A warehouse table for aggregates, object storage for raw payloads |
| Manual pipeline run | Scheduled ingestion per source, with monitoring and alerting on failure |
| A 15-record manual spot check | A stratified sample per batch, two independent reviewers, inter-annotator agreement, a frozen gold set |
| Public feedback only | Joined to internal product telemetry — the Part 1 conversion funnel |

**Why a fixed taxonomy is the right choice at this scale and the wrong one at production scale:** with a few hundred records, a taxonomy hand-derived from Port's own documented product surface produces findings that point at a page the team already owns, and every record can still be read by a human to sanity-check the category. Unsupervised clustering on a few hundred records tends to produce unstable, hard-to-name groups — there isn't enough data for the clusters to settle. At thousands of records the trade inverts: a fixed list of categories cannot discover a problem nobody thought to name in advance, and paying for an LLM call on every single record stops being economical when embeddings can group most of them first. See `ARCHITECTURE.md` → *Production scale* for the same argument in the context of this specific dataset.

---

## 2. "Explain how you would use GenAI (LLMs) to categorize this unstructured data?"

### The core design: extraction, not free-form generation

The model is never asked to write an open-ended analysis. It is asked to fill in a **strictly validated schema** for one record at a time, with every categorical field constrained to a closed list defined *before* any data was seen. This is the difference between "summarise this feedback" (unbounded, unauditable, drifts over time) and "classify this feedback into exactly one of these eleven categories" (bounded, checkable, stable). The schema itself lives in `src/models/schema.py`, built from Pydantic `Literal` types generated directly off the taxonomy in `src/models/taxonomy.py` — the categories the model is allowed to choose from and the categories the code will accept are, structurally, the same list. They cannot drift apart.

### The output schema

Nine fields per record: `is_relevant`, `primary_theme`, `journey_stage`, `feedback_type`, `severity`, `short_summary`, `user_need`, `confidence`, `evidence_excerpt`. Two independent dimensions matter most:

- **Theme** answers *what* product problem is being raised — 11 closed categories, e.g. *Backend & invocation configuration*, *Permissions, eligibility & action visibility*.
- **Journey stage** answers *where* in the user's lifecycle they hit it — 8 closed stages, kept in **chronological order** so a chart of "friction by stage" reads left-to-right as the actual user journey. Deliberately mirrors Port's own documented self-service flow, so a finding like *"friction concentrates in permissions and approvals"* names a surface the product team already owns rather than a category invented for this exercise.

Each record gets exactly one theme and one stage — never two. Where a record could reasonably go either of two ways, **eleven documented disambiguation rules** decide (`src/models/taxonomy.py` → `TIE_BREAK_RULES`), and whatever ambiguity is left over is reported through the `confidence` field rather than papered over with a double classification. Full taxonomy and every rule: `TAXONOMY.md`.

### Four controls that keep the categorisation trustworthy

**1. Closed enums reject invention.** If the model were to output a theme name that isn't one of the eleven, Pydantic validation fails the record outright rather than silently accepting a new, unplanned category. Verified directly: `tests/test_pipeline.py::test_removed_taxonomy_names_are_rejected` asserts that every retired category name from an earlier taxonomy revision is now rejected by the schema, not just documented as retired.

**2. Quote grounding — the strongest anti-fabrication control in the system.** Every classification includes an `evidence_excerpt`, and before a record is accepted, **Python code — not the model — checks that the excerpt is an exact substring of the original text.** A quote that cannot be verified is marked `evidence_verified = False` and is never shown on the dashboard as evidence. This makes a specific class of failure structurally impossible: the model cannot attribute a complaint to a customer who never said it, because it cannot produce a quote that doesn't exist in the source. See design decision D-5 in `ARCHITECTURE.md`, and the grounding logic itself in `src/analysis/classify.py`.

**3. A versioned, cached prompt — the actual answer to "low randomness."** Current LLM APIs no longer expose `temperature` for deterministic sampling (`temperature`/`top_p`/`top_k` return a 400 error on the model used here), so bit-for-bit reproducibility across separate runs is not achievable, and this project says so plainly rather than claiming otherwise. What *is* achievable, and what the design relies on: a fixed, versioned prompt (`PROMPT_VERSION` in `src/models/prompt.py`, currently `v2.0`) where every field the model can output is closed, and — critically — the **classified dataset itself is a committed, versioned artifact**. The live dashboard replays stored classifications; it never re-classifies on page load. The deliverable is reproducible even though the underlying model call is not.

**4. Confidence is a quality signal, never a ranking input.** The model is asked to be honest about uncertainty — scoring below 0.7 when a post is vague, short, or genuinely spans two categories — and that score is surfaced separately on the dashboard as a data-quality indicator. It is explicitly excluded from the priority formula (design decision D-6), because letting model confidence influence prioritisation would silently favour well-phrased feedback over messy-but-urgent feedback, which has nothing to do with which problem actually matters more.

### Prompt design specifics

The prompt is split into a **stable system portion** (the taxonomy, the disambiguation rules, the output-format rules — identical on every one of the ~300 calls, and marked for prompt caching so it's read at roughly a tenth of the input cost after the first call) and a **volatile user portion** (just that one record's title, body, and category). The system prompt explicitly tells the model the difference between a theme and a stage — *"theme answers what, stage answers where"* — because without that framing the two dimensions collapse into duplicates of each other. It also carries an explicit instruction not to classify on keyword matching alone, and not to force feedback into this taxonomy that genuinely belongs to some other part of the product. See `src/models/prompt.py`.

### Where GenAI stops and code starts

This is worth stating as its own principle, because it's the most common design mistake in AI-augmented analytics pipelines: **the LLM's job ends at the classified record.** Every count, every average, every ranking, and the entire priority score are computed afterward by deterministic Python with no model involvement — see question 1, "the central rule," above. Using GenAI to categorise unstructured text and then using ordinary code to do arithmetic on the categories is not a limitation of this design; it is the design.

### How this scales to Slack, Zendesk, and Gong

The classification approach — closed schema, quote grounding, versioned prompt, confidence as a quality signal — carries over unchanged to every source; none of those four controls are specific to a feature-request board. What changes is what feeds the model: at Port's real volume, per-record LLM classification against a fixed taxonomy stops being the right primary mechanism (see the taxonomy-at-scale argument under question 1), and the LLM's role shifts from *"classify this record into one of eleven known categories"* to *"label and summarise this cluster that embeddings just discovered."* The four trust controls above still apply to that labelling step exactly as they do here.
