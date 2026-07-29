# Taxonomy

How every piece of feedback is categorised. Defined **before** any data was classified, so the categories were not fitted to the answer.

Two dimensions at different granularity, answering different questions:

| Dimension | Question | Count |
|---|---|---|
| **Journey stage** | *Where* in setting up an action is the user stuck? | 7 |
| **Theme** | *What* specific problem area is it? | 12 |

Keeping them separate is what makes the dashboard's "themes" and "journey" views genuinely different rather than the same chart twice. Some themes deliberately span stages — that cross-tab is where the useful findings are.

---

## Journey stages

Mirrors Port's own documented self-service flow, so a result like *"friction concentrates in permissions and approvals"* points at a surface the team already owns.

| # | Stage | Covers |
|---|---|---|
| 1 | **Discovering and organizing actions** | Finding the right action, browsing or searching the catalog, grouping and categorizing, controlling what appears to whom |
| 2 | **Configuring forms and inputs** | Input field types, controls, ordering, defaults, prefilled values, form layout |
| 3 | **Validations and conditional logic** | Required fields, regex and type checks, cross-field rules, inputs that depend on each other |
| 4 | **Backend and invocation setup** | Webhooks, CI pipelines, payload mapping, secrets and credentials, invocation settings |
| 5 | **Permissions and approvals** | Who may run or edit an action, dynamic permissions, manual and automatic approvals |
| 6 | **Testing and editing** | Trying an action before release, iterating on an existing one, the editing experience |
| 7 | **Execution and monitoring** | Run status, progress, logs, errors, audit history, retries, cancelling |

---

## Themes

| Theme | Covers |
|---|---|
| **Action discovery & organization** | Cannot find, group, or make sense of available actions |
| **Input types & controls** | Available field types are missing or too limited |
| **Dynamic & dependent inputs** | Inputs that react to other inputs or are populated from an API/dataset |
| **Validation & conditional logic** | Required-ness, patterns, cross-field checks, conditional visibility |
| **Backend & invocation configuration** | Webhooks, pipelines, payload construction, secrets, invocation settings |
| **Permissions & access control** | Who may see, run, or edit an action; dynamic permission rules |
| **Approval workflows** | Approvers, thresholds, approver notifications, approval routing |
| **Testing & editing experience** | Trying an action safely; ergonomics of editing |
| **Execution visibility & logs** | Status, progress, logs, errors, audit history |
| **Run control & retries** | Retrying, cancelling, pausing, resuming, marking outcomes |
| **Multi-step & orchestration** | Actions composed of several steps; sequencing work |
| **Notifications & alerting** | Email, Slack, Teams, and other channels |

---

## Feedback types

| Type | Meaning |
|---|---|
| **Feature request** | Asks for a capability that does not exist today |
| **Usability friction** | The capability exists but is confusing, tedious, or harder than it should be |
| **Bug** | Behaves incorrectly compared to what is documented or expected |
| **Documentation gap** | The capability exists, but the user could not discover or understand it |
| **Reliability issue** | Works inconsistently: intermittent failures, timeouts, breakage at scale |

---

## Severity

Judged **only from the pain described in the text** — not from vote count, and not from how hard something would be to build.

| Score | Meaning |
|---|---|
| **5** | **Blocking.** Cannot complete setup or execution at all; no workaround described |
| **4** | **Major.** A workaround exists but is expensive — custom code, an external system, or manual work every time |
| **3** | **Moderate.** Noticeably slows setup or forces repeated manual steps, but the goal is achievable |
| **2** | **Minor.** Small inefficiency, rough edge, or cosmetic problem |
| **1** | **Nice to have.** No pain described; purely additive |

---

## Disambiguation rules

Written after inspecting the real board, because these cases genuinely recur. Without them the model splits near-identical posts across stages — which shows up as low agreement in evaluation.

1. **Classify by where the user is stuck, not by which feature is named.** A complaint that a form is hard to configure is *Configuring forms and inputs*, even if it mentions the backend.
2. Automations and workflow triggers that configure how an action is invoked → **Backend and invocation setup**.
3. Anything about not being able to *see* what happened (status, logs, errors, audit trail) → **Execution and monitoring**, regardless of which stage caused the failure.
4. Approvals stay in **Permissions and approvals** even when the ask is about notifying approvers — the notification is the *theme*, approvals is the *stage*.
5. If a post spans several stages, choose where the user's **problem starts**, not what they mention last.
6. Multi-step or staged forms → stage *Configuring forms and inputs*, theme *Multi-step & orchestration*.

---

## Two anti-fabrication controls

**1. Closed enums.** Every categorical field is a `Literal` built directly from this taxonomy. A label the model invents fails Pydantic validation instead of quietly entering the dataset. Verified: an invented theme, an out-of-range severity, a confidence above 1.0, and even a stage name with a trailing space are all rejected.

**2. Quote grounding.** Every `evidence_excerpt` is checked in Python as an exact substring of the source text before the record is accepted. Only unicode form, whitespace, and curly-quote style are normalised — the words themselves must match. A fabricated quote sets `evidence_verified = False` and is never displayed as evidence.

The model cannot attribute a complaint to a customer who never made it, because it cannot produce a quote that is not in the source.

---

## Notes on judgment

- **Relevance is strict.** Catalog modelling, dashboards, scorecards, data sources, and third-party integrations are *not* relevant unless the post is specifically about an action that uses them. Padding the dataset to hit a target would produce false conclusions.
- **Some posts are written by Port staff**, not customers — curated roll-ups that read like product copy. The classifier is told to categorise the underlying user problem and to prefer quoting the sentence that states the *problem* over the one that pitches the solution.
- **Confidence is a quality signal only.** It never affects prioritisation. Records below 0.7 are reported, not hidden.

**Prompt version `v1.0`** is recorded on every classified record, so any figure in the dashboard can be traced back to the exact prompt and model that produced it.
