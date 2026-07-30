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

**Aggregation and ranking.** Once records carry a category, a subcategory, a problem type, a stage and a severity, everything a product team wants — volume by area, friction by stage, a ranked list of what to build — is arithmetic over a table. No LLM call belongs in this stage.

The ranking deliberately **has no weighted score**. An earlier version of this project ranked themes by `0.45 × votes + 0.30 × frequency + 0.25 × severity`, and both halves of that were wrong. The weights were indefensible: multiplying unlike signals by invented coefficients produces a number that looks precise and collapses the moment someone asks why 0.45 rather than 0.4. And votes do not generalise — a vote total means something inside one feedback portal and nothing across Slack, Zendesk and Gong, because there is nothing to vote with in a support ticket or a sales call. Ranking on a signal only one of four sources can produce would systematically bury every problem arriving through the other three.

What replaced it is **lexicographic ranking**: open records are grouped by subcategory, and groups are ordered by six explicit keys applied in sequence — severity band, open supporting records, max severity, source diversity, average confidence, recency — with a final alphabetical key making the order total. Every position can be explained by naming the single key that decided it. `src/analysis/aggregate.py` implements it, and `tests/test_pipeline.py::test_ranking_recomputed_by_hand` recomputes the counts independently from the raw records rather than re-running the same function that produced them.

**Only open demand is ranked.** `Completed` and `Closed` records are excluded, so shipped work cannot argue for itself again — while staying visible in the evidence explorer, where "we already built this" is itself a finding.

**Presentation.** A dashboard is only as trustworthy as its traceability. Every aggregate figure in this system's UI links back to the individual records that produced it — the Evidence Explorer section of the dashboard is that traceability made concrete, not an afterthought bolted onto a chart.

### Design principles that generalise beyond this POC

1. **Immutable raw storage.** Never let a cleaning bug erase evidence of what a customer actually said. Raw goes in once and is never edited.
2. **The AI does language; code does arithmetic.** This is not a stylistic preference — it is the only way a stakeholder can audit *why* a number is what it is, and the only way the same input reliably produces the same output.
3. **Ranking you can explain one key at a time**, not a black box and not a fake-precise score. Lexicographic ordering over stated keys, with the key list rendered on the dashboard from the same constant the code ranks by, so the explanation cannot drift from the behaviour. See `ARCHITECTURE.md` → *Ranking product actions*.
4. **Confidence is a quality signal, never an input to ranking.** A model being *certain* about a classification says nothing about how much the underlying problem *matters* — conflating the two would let well-phrased feedback systematically outrank urgent, messy feedback. See design decision D-6 in `ARCHITECTURE.md`.
5. **Human review as a first-class stage, not an afterthought.** A stratified sample, reviewed independently, with disagreements surfaced rather than smoothed over. This project's evaluation stage (`src/analysis/evaluate.py`) reports **"Not yet evaluated"** until real human labels exist — there is no code path that can display a fabricated accuracy figure. At production scale this becomes a rotating stratified sample per ingestion batch, two independent reviewers, and a frozen gold set to regression-test prompt changes against.
6. **Taxonomy versioning, not silent relabelling.** When the categorisation scheme changes for a real reason — as it did twice here, most recently replacing a flat 11-theme list with 11 categories containing 63 subcategories — every affected record is *reclassified* under the new scheme rather than string-replaced. A semantic change in what a category means invalidates old labels even when the names survive. This is enforced structurally, not by discipline: the classification cache key includes the taxonomy and schema version, so a revision makes every cached answer unreachable and a genuine reclassification is the only way to produce a result.

7. **Separate the dimensions that answer different questions.** The single largest design change in this project was splitting one `Theme` field into four independent ones — product area, specific subcategory, problem type, and journey stage. A dynamic-permission failure belongs to *Permissions & Approvals* while its problem *type* is *Poor error message*; folding those together makes both unusable for counting, and quietly forces the analyst to pick which of the two facts to lose.

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

Each record carries scope (`is_relevant` plus a `relevance_reason`), a hierarchical taxonomy assignment, three further independent dimensions, a narrative, and quality signals. Four dimensions matter most, and the reason there are four rather than one is the core design point:

- **Taxonomy category** answers *which broad product area* — 11 closed values, e.g. *Permissions & Approvals*, *Observability & Debugging*.
- **Taxonomy subcategory** answers *which specific part of it* — 63 closed values, e.g. *Approval notifications*, *Error messages & backend responses*. Hierarchy is what lets the dashboard show a readable 11-bar chart and still drill down to something specific enough to hand to an engineer.
- **Problem type** answers *what kind of problem* — 14 closed values, e.g. *Feature gap*, *Poor error message*. Independent on purpose: a dynamic-permission failure is a *Permissions* problem whose *type* is a poor error message, and encoding that into the category name would make both unusable for counting.
- **Journey stage** answers *where* in the user's lifecycle they hit it — 8 closed stages in **chronological order**, so a chart of "friction by stage" reads left-to-right as the actual user journey. It deliberately mirrors Port's own documented self-service flow, so a finding like *"friction concentrates in permissions and approvals"* names a surface the product team already owns rather than a category invented for this exercise.

Each record gets exactly one primary category/subcategory pair, one problem type and one stage. **At most two secondary assignments** are allowed, for records that genuinely span areas — a permissions failure whose real complaint is the missing explanation should be visible to both owners. Secondaries never affect any count or ranking, so adding one can never inflate a total.

Where a record could reasonably go either of two ways, **thirteen documented disambiguation rules** decide (`src/models/taxonomy.py` → `TIE_BREAK_RULES`), and whatever ambiguity is left over is reported through `confidence` and `needs_human_review` rather than papered over. Full taxonomy and every rule: `TAXONOMY.md`, which is *generated from the taxonomy module* so it cannot describe a scheme the code does not implement.

### Four controls that keep the categorisation trustworthy

**1. Closed enums reject invention, and the hierarchy rejects impossible combinations.** If the model outputs a category name that isn't one of the eleven, Pydantic fails the record outright rather than silently accepting a new, unplanned category. A hierarchical taxonomy adds a second failure mode worth closing: a *real* subcategory paired with the *wrong* parent category. A model validator rejects that pair, so the model cannot assemble a plausible-looking but impossible classification. Verified directly — `tests/test_pipeline.py::test_removed_taxonomy_names_are_rejected` asserts that every retired name from an earlier revision is now rejected by the schema, not merely documented as retired, and `test_schema_rejects_invented_values` includes a real-subcategory-wrong-category case.

Scope is enforced structurally too: when `is_relevant` is false, the validator *clears* the taxonomy fields rather than trusting them to be empty. Out-of-scope feedback is therefore incapable of reaching a category total, a problem-type distribution or a ranking.

**2. Quote grounding — the strongest anti-fabrication control in the system.** Every classification includes an `evidence_excerpt`, and before a record is accepted, **Python code — not the model — checks that the excerpt is an exact substring of the original text.** A quote that cannot be verified is marked `evidence_verified = False` and is never shown on the dashboard as evidence. This makes a specific class of failure structurally impossible: the model cannot attribute a complaint to a customer who never said it, because it cannot produce a quote that doesn't exist in the source. See design decision D-5 in `ARCHITECTURE.md`, and the grounding logic itself in `src/analysis/classify.py`.

**3. A versioned, cached prompt — the actual answer to "low randomness."** Current LLM APIs no longer expose `temperature` for deterministic sampling (`temperature`/`top_p`/`top_k` return a 400 error on the model used here), so bit-for-bit reproducibility across separate runs is not achievable, and this project says so plainly rather than claiming otherwise. What *is* achievable, and what the design relies on: a fixed, versioned prompt (`PROMPT_VERSION` in `src/models/prompt.py`, currently `v3.0`) where every field the model can output is closed, and — critically — the **classified dataset itself is a committed, versioned artifact**. The live dashboard replays stored classifications; it never re-classifies on page load. The deliverable is reproducible even though the underlying model call is not.

**4. Confidence is a quality signal, never a ranking input.** The model is asked to be honest about uncertainty — scoring below 0.7 when feedback is vague, short, or genuinely spans two areas — and to set `needs_human_review` when two categories are equally plausible. Both are surfaced separately as data-quality indicators. Confidence appears in the ranking only as the *fifth* tie-breaker, used when four earlier keys are already identical (design decision D-6), because letting model confidence drive prioritisation would silently favour well-phrased feedback over messy-but-urgent feedback — which has nothing to do with which problem actually matters more.

### Prompt design specifics

The prompt is split into a **stable system portion** (the taxonomy, the disambiguation rules, the worked examples, the output-format rules — identical on every one of the ~330 calls, and marked for prompt caching so it's read at roughly a tenth of the input cost after the first call) and a **volatile user portion** (just that one record's source, title, body and board category). Caching is what makes a taxonomy this detailed affordable: the system block is ~9,800 tokens, and it is paid for once rather than on every record.

Two prompt choices carry most of the accuracy:

**Every subcategory ships with its own "Do NOT use when" rule**, naming the specific neighbouring subcategory it is most often confused with. Definitions alone are not enough — almost every misclassification in a taxonomy this fine-grained is a confusion between two adjacent options, and the avoid line is what identifies the neighbour and sends the model there. The rules are rendered into the prompt from the same dict the guide tab renders, so the model and the human reader are reading the same instruction.

**The system prompt states explicitly that the four dimensions answer different questions** — category is *which area*, subcategory is *which part*, problem type is *what kind*, stage is *where* — because without that framing the dimensions collapse into duplicates of each other. It also instructs the model not to classify on keyword matching alone, and not to force feedback into this taxonomy that genuinely belongs to another part of the product.

One further field is specified as a **grouping key** rather than prose: `suggested_product_action` must be phrased as the capability Port would build, starting with a verb, so that two records asking for the same change converge on near-identical wording. See `src/models/prompt.py`.

### Where GenAI stops and code starts

This is worth stating as its own principle, because it's the most common design mistake in AI-augmented analytics pipelines: **the LLM's job ends at the classified record.** Every count, every average, every ranking, and the entire priority score are computed afterward by deterministic Python with no model involvement — see question 1, "the central rule," above. Using GenAI to categorise unstructured text and then using ordinary code to do arithmetic on the categories is not a limitation of this design; it is the design.

### How this scales to Slack, Zendesk, and Gong

The classification approach — closed hierarchical schema, quote grounding, versioned prompt, confidence as a quality signal — carries over unchanged to every source; none of those four controls are specific to a feature-request board. What changes is what feeds the model: at Port's real volume, per-record LLM classification against a fixed taxonomy stops being the right primary mechanism (see the taxonomy-at-scale argument under question 1), and the LLM's role shifts from *"classify this record into one of sixty-three known subcategories"* to *"label and summarise this cluster that embeddings just discovered."* The four trust controls above still apply to that labelling step exactly as they do here.
