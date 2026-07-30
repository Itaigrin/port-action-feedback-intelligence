# Taxonomy

How every piece of feedback is categorised. Defined **before** any data was classified, so the categories were not fitted to the answer.

Single source of truth: [`src/models/taxonomy.py`](src/models/taxonomy.py). The classifier, the dashboard, the in-app guide and this document all read from it — nothing redefines a theme or a stage anywhere else.

> **Version 2.0.** The taxonomy was revised after reviewing real classifications: a context/pre-fill dimension was added, dynamic inputs and validation were separated more sharply, and three overlapping execution themes were merged into one. Because the change is semantic rather than cosmetic, every record was **reclassified** rather than relabelled.

---

## Two dimensions, two questions

| Dimension | Question it answers | Count |
|---|---|---|
| **Theme** | *What* is the main product problem, and what change would solve it? | **11** |
| **Journey stage** | *Where* in the action lifecycle does the user hit it? | **8** |

Keeping them separate is what makes the dashboard's "themes" and "journey" views genuinely different rather than the same chart twice.

**They are not strictly nested.** Two deliberate cases:

- *Multi-step & orchestration* sits at the **Backend & invocation setup** stage, because several connected backend operations are a backend concern. A single form split into visual pages is *Form structure*, not orchestration.
- *Execution visibility, notifications & run control* normally sits at **Execution, monitoring & run control** — but a **missing approval-request notification** sits at **Permissions & approvals**, because that is where the user is actually blocked.

That cross-tab is where the useful findings are.

---

## Journey stages (8, chronological)

Insertion order in `JOURNEY_STAGES` **is** the lifecycle order. Charts, filters, aggregations and the guide all derive their ordering from `STAGE_NAMES`, so reordering that dict reorders the product journey everywhere.

| # | Stage | The user is trying to… |
|---|---|---|
| 1 | **Action discovery & organization** | Find and understand which actions exist — search, browse, categories, folders, naming |
| 2 | **Contextual entry, targeting & pre-fill** | Start the action already pointed at the right target, carrying the context they came from |
| 3 | **Form & input configuration** | Work with a form that has the right fields, clearly labelled and sensibly ordered |
| 4 | **Validation, dependencies & conditional logic** | Be guided to valid input, with fields that adapt to earlier choices |
| 5 | **Backend & invocation setup** | Connect the action to the pipeline, API or system that performs the work |
| 6 | **Permissions & approvals** | Run only what they're entitled to, with the right sign-off in place |
| 7 | **Testing, editing & publishing** | Build, test and release an action safely (this is the *builder*, not the end user) |
| 8 | **Execution, monitoring & run control** | See the outcome, understand failures, retry or cancel |

**What changed from v1:** stage 2 is new. The old *Discovering and organizing actions* → *Execution and monitoring* seven-stage sequence conflated "the page I came from should set the target" with general form configuration, which hid a distinct class of friction.

---

## Themes (11)

| # | Theme | Plain meaning | Usual stage |
|---|---|---|---|
| 1 | **Action discovery & organization** | Can't find or make sense of available actions | 1 |
| 2 | **Context, targeting & pre-fill** | Port already knows the target but asks anyway | 2 |
| 3 | **Form structure, input types & controls** | Which field types exist and how they're laid out | 3 |
| 4 | **Dynamic & dependent inputs** | Fields that change based on context or earlier choices | 4 |
| 5 | **Validation & error guidance** | Checking input is valid, and saying clearly what to fix | 4 |
| 6 | **Backend & invocation configuration** | Wiring the action to whatever does the work | 5 |
| 7 | **Permissions, eligibility & action visibility** | Who may see or run it, and whether they're eligible | 6 |
| 8 | **Approval workflows & governance** | Who must approve, and which governance rules apply | 6 |
| 9 | **Testing, editing & drafts** | Helping builders create, test and change actions safely | 7 |
| 10 | **Execution visibility, notifications & run control** | Seeing and controlling what happens after submission | 8 |
| 11 | **Multi-step & orchestration** | One action performing several connected backend operations | 5 |

The "usual stage" column is `DEFAULT_STAGE_FOR_THEME` — a **guideline, not a constraint**. The classifier may choose a different stage when the feedback clearly warrants it.

### What changed from v1

| v1 | v2 | Why |
|---|---|---|
| *(none)* | **Context, targeting & pre-fill** | Added. "I opened this from a service page, stop asking me which service" is a distinct, actionable problem that was previously scattered across form and input themes. |
| *Input types & controls* | **Form structure, input types & controls** | Renamed and widened to cover layout, grouping and multi-page forms explicitly. |
| *Validation & conditional logic* | **Validation & error guidance** | Narrowed. Conditional behaviour moved to *Dynamic & dependent inputs*; error-message quality moved in. The old name straddled both and produced inconsistent labels. |
| *Permissions & access control* | **Permissions, eligibility & action visibility** | Renamed to make visibility and eligibility explicit — the common real complaint is being rejected *after* filling in the whole form. |
| *Approval workflows* | **Approval workflows & governance** | Widened to cover guardrails and governance policy. |
| *Testing & editing experience* | **Testing, editing & drafts** | Widened to cover drafts, versioning and publishing. |
| *Execution visibility & logs* + *Run control & retries* + *Notifications & alerting* | **Execution visibility, notifications & run control** | **Three merged into one.** In practice these split near-identical posts three ways — "the run failed and nobody was told" could land in any of them. |

Net: 12 themes → 11, with clearer boundaries.

---

## Feedback types (5, unchanged)

| Type | Meaning |
|---|---|
| **Feature request** | Asks for a capability that does not exist today |
| **Usability friction** | Exists, but is confusing, tedious, or harder than it should be |
| **Bug** | Behaves incorrectly compared to what is documented or expected |
| **Documentation gap** | Exists, but the user could not discover or understand it |
| **Reliability issue** | Works inconsistently: intermittent failures, timeouts, breakage at scale |

## Severity (1–5, unchanged)

Judged **only from the pain described in the text** — not from vote count, and not from how hard something would be to build.

| Score | Meaning |
|---|---|
| **5** | **Blocking.** Cannot complete setup or execution at all; no workaround described |
| **4** | **Major.** A workaround exists but is expensive — custom code, external system, or manual work every time |
| **3** | **Moderate.** Noticeably slows setup or forces repeated manual steps, but achievable |
| **2** | **Minor.** Small inefficiency, rough edge, or cosmetic problem |
| **1** | **Nice to have.** No pain described; purely additive |

---

## Disambiguation rules

Eleven rules in `TIE_BREAK_RULES`. Each exists because the distinction genuinely recurs — without them the model splits near-identical posts across categories, which surfaces as low agreement in evaluation.

| # | Distinction | Left | Right |
|---|---|---|---|
| 1 | Discovery vs Permissions | "I cannot find the action" | "This action shouldn't be visible to this user" |
| 2 | Context vs Form config | "Port already knows my service" | "I need a new field / different order" |
| 3 | Form structure vs Dynamic | "I need a date field" | "Available dates depend on environment" |
| 4 | Dynamic vs Validation | A field *changes* from another choice | The system *checks* whether a value is allowed |
| 5 | Permissions vs Approvals | "Who may see or run it?" | "Who must approve it?" |
| 6 | Validation vs Runtime | Error **before** submission | Failure **after** the action started |
| 7 | Testing vs Execution | Builder trying it pre-release | A real user's submitted run |
| 8 | Multi-page vs Multi-step | One form, several visual pages | Several connected **backend** operations |
| 9 | Approval vs Run notification | Missing *approval request* → stage **Permissions & approvals** | Missing *success/failure* → stage **Execution** |
| 10 | Contextual vs general default | Inferred from the originating page | Computed from other form fields, or fixed |
| 11 | Spanning categories | Theme = the change that solves the **main** problem | Stage = where the user **first** becomes blocked |

Two global rules also apply: **never classify on keywords alone** (a post mentioning "payload" is not automatically a backend post), and **never force unrelated feedback into this taxonomy** — set `is_relevant = false` instead.

---

## One theme, one stage

Each relevant record gets exactly **one** `primary_theme` and **one** `journey_stage`. There are deliberately no secondary classifications: a record that could go two ways is resolved by the rules above, and the residual uncertainty is reported through `confidence` rather than hidden by assigning both.

---

## Two anti-fabrication controls

**1. Closed enums.** Every categorical field is a `Literal` built directly from this taxonomy, so the schema and the documentation cannot drift apart. Verified by tests: an invented theme, an out-of-range severity, a confidence above 1.0, a stage name with a trailing space, **and all 15 retired v1 names** are rejected.

**2. Quote grounding.** Every `evidence_excerpt` is checked in Python as an exact substring of the source text before the record is accepted. Only unicode form, whitespace and curly-quote style are normalised — the words themselves must match. A quote that cannot be grounded sets `evidence_verified = False` and is never displayed.

The model cannot attribute a complaint to a customer who never made it, because it cannot produce a quote that is not in the source.

---

## Notes on judgment

- **Relevance is strict.** Catalog modelling, dashboards, scorecards, data sources and third-party integrations are *not* relevant unless the post is specifically about an action that uses them. Padding the dataset to hit a target would produce false conclusions.
- **Some posts are written by Port staff**, not customers — curated roll-ups that read like product copy. The classifier categorises the underlying user problem and prefers quoting the sentence that states the *problem* over the one that pitches the solution.
- **Confidence is a quality signal only.** It never affects prioritisation. Records below 0.7 are reported, not hidden.

**Prompt version `v2.0`** is recorded on every classified record, so any figure in the dashboard traces back to the exact prompt and model that produced it. The version bump also invalidates every cache key — v1 labels are not translatable to v2, so they were regenerated rather than mapped.

---

## In-app guide

The dashboard's second tab, **Themes & Journey Stages Guide**, renders this taxonomy for readers with no software or DevOps background: plain-language explanations, use-when and do-not-use-when criteria, two examples per theme, a numbered stage timeline, worked classification examples, side-by-side confusion pairs, and an 18-term glossary. It reads from the same `taxonomy.py` metadata (`THEME_GUIDE`, `STAGE_GUIDE`, `GLOSSARY`, `CONFUSION_PAIRS`, `WORKED_EXAMPLES`), so the guide can never describe a taxonomy the classifier isn't using.
