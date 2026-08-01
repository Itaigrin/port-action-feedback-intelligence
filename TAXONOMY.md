<!-- GENERATED FILE — do not edit by hand.
     Source: src/models/taxonomy.py
     Regenerate: python -m scripts.render_taxonomy_doc -->

# Taxonomy

How every piece of feedback is categorised. Defined **before** any data was classified, so the categories were not fitted to the answer.

Single source of truth: [`src/models/taxonomy.py`](src/models/taxonomy.py). The classifier, the Pydantic schema, the dashboard, the in-app guide and this document all read from it. This file is generated from that module, so it cannot describe a taxonomy the code does not implement.

> **Version v3.0.** The flat theme list was replaced by a two-level structure of 11 categories and 30 subcategories, with problem type, persona, lifecycle status and source system split out as independent dimensions. Because the change is semantic rather than cosmetic, every record was **reclassified** rather than relabelled — the classification cache is keyed on the taxonomy version precisely so that a revision cannot replay old labels.

---

## Four independent dimensions

| Dimension | Question it answers | Count |
|---|---|---|
| **Taxonomy category** | *Which broad product area* does this concern? | **11** |
| **Taxonomy subcategory** | *Which specific part* of that area needs work? | **30** |
| **Problem type** | *What kind* of problem is it? | **14** |
| **Journey stage** | *Where* in the Action lifecycle does the user hit it? | **8** |

Keeping them independent is what makes the dashboard's views genuinely different rather than the same chart four times. A dynamic-permission failure sits in the **Permissions & Approvals** category while its problem type is **Poor error message** — encoding the problem type into the category name would make both unusable for counting.

Severity, persona, lifecycle status and source system are further independent dimensions, and are never folded into a category name either.

---

## Journey stages (8, chronological)

Order is load-bearing: every chart, filter and guide section derives its order from this list, so reordering it silently reorders the product story. Always pick the stage where the user **first** becomes blocked.

| # | Stage | What the user is trying to do | Typical feedback |
|---|---|---|---|
| 1 | **Action discovery & organization** | Work out which Action does what they need, out of everything available. | "There are dozens of Actions in one flat list and I cannot tell which one deploys my service." |
| 2 | **Contextual entry, targeting & pre-fill** | Start the Action already pointed at the right service, resource or environment. | "I clicked the Action from a service page, but it asks me to choose the service again." |
| 3 | **Form & input configuration** | Fill in a form that has the right fields, clearly labelled and sensibly ordered. | "There is no way to attach a file, and the fields are in a confusing order." |
| 4 | **Validation, dependencies & conditional logic** | Be guided to valid input, with fields that adapt to earlier choices. | "It rejects my value without saying what format it expects." |
| 5 | **Backend & invocation setup** | Connect the Action to the pipeline, API or system that performs the task. | "We need to reshape the data before it is sent to our workflow." |
| 6 | **Permissions & approvals** | Only run what they are entitled to, with the right approvals in place. | "I filled in the whole form and only then was told I am not permitted." |
| 7 | **Testing, editing & publishing** | Build, test and release an Action safely, without breaking it for users. | "I want to try the Action myself before anyone else can see it." |
| 8 | **Execution, monitoring & run control** | See the outcome, understand failures, and retry or cancel when needed. | "The Run failed hours ago and nobody was notified." |

---

## Categories and subcategories (11 × 30)

Each subcategory carries a **Do NOT use when** rule. Those rules matter more than the definitions: almost every misclassification is a confusion between two adjacent subcategories, and the avoid line is what names the neighbour and sends you to it.

### 1. Discovery, Organization & Reuse

How users find, organize, display and reuse Actions.

*Usual journey stage:* `Action discovery & organization`  
*Most often confused with:* *Permissions & Approvals*, *Context, Targeting & Pre-fill*

#### Action discovery, organization & placement

Finding, organizing, ordering and placing Actions so users see the right Action in the right catalog surface.

**Use for:** Action discovery, grouping & ordering; Conditional availability & placement.

> ⛔ **Do NOT use when:** Authorization-based visibility belongs to Access control & action eligibility. Multi-entity execution belongs to Bulk actions.

- “there is a requirement to filter Self Service Actions on custom catalogue pages”
- “Allow categorizing self service actions for ease of finding appropriate actions for your needs.”

#### Bulk actions

Running one Action against multiple selected or filtered entities in a single operation.

**Use for:** Bulk actions.

> ⛔ **Do NOT use when:** Several backend steps inside one Action belong to Orchestration. Payload shaping belongs to Payload mapping & transformation.

- “It would be great to have an option to do bulk actions(day2 and DELETE) on entities”
- “I want to run a single action that references all entities”

---

### 2. Context, Targeting & Pre-fill

Using what Port already knows so the Action opens in the right context and stops asking the user to repeat itself.

*Usual journey stage:* `Contextual entry, targeting & pre-fill`  
*Most often confused with:* *Form Configuration*, *Discovery, Organization & Reuse*

#### Contextual launch, targeting & pre-fill

Launching an Action from the right surface with the intended entity/resource and values Port can infer from context.

**Use for:** Contextual entry & deep links; Entity and resource targeting; Pre-fill & context-specific defaults; Embedded & alternative launch surfaces.

> ⛔ **Do NOT use when:** General defaults not derived from launch context belong to Dynamic inputs, defaults & computed fields. Acting as the requester belongs to Authentication, execution identity & requester context.

- “an action if associated with service overview entity cant be associated with the service blueprint entity - which means a new actions should be created”
- “the bot intentionally does not execute the action automatically. Instead, it collects some parameters and then redirects the user back to the Port UI”

---

### 3. Form Configuration

The visible form, the fields it contains, and how users complete it.

*Usual journey stage:* `Form & input configuration`  
*Most often confused with:* *Validation & Rules*, *Context, Targeting & Pre-fill*, *Orchestration*

#### Input types & structured data

The field and control types available in Action forms, including arrays, objects, tables and repeatable groups.

**Use for:** Input types & controls; Structured & repeatable inputs.

> ⛔ **Do NOT use when:** Fields that change based on another value belong to Dynamic inputs, defaults & computed fields. Visual arrangement belongs to Form presentation, layout & guidance.

- “requiring users to manually select each item one by one — which becomes tedious and time-consuming when dealing with large lists”
- “Without a table view, the UX is not good”

#### Dynamic inputs, defaults & computed fields

Form values, options, visibility or editability that are populated or recalculated from other inputs, data or context.

**Use for:** Dynamic & dependent inputs; Defaults & computed fields.

> ⛔ **Do NOT use when:** Context inherited from the launch surface belongs to Contextual launch, targeting & pre-fill. Acceptance rules belong to Form validation, messages & conditional rules.

- “This is done by calculating values based on the data of other form inputs, user data, and entity data.”
- “auto-generated from the previous inputs and NOT EDITABLE from the user form”

#### Form presentation, layout & guidance

How the form is arranged, navigated, labelled and explained to the end user.

**Use for:** Form layout, sections & multi-page forms; Labels, descriptions & display controls.

> ⛔ **Do NOT use when:** New input capabilities belong to Input types & structured data. Invalid-value explanations belong to Form validation, messages & conditional rules.

- “This button will allow users to initiate the action immediately if they do not need to modify any fields in subsequent steps.”
- “the button is always displayed, even for forms intended purely for informational or navigational purposes, which can confuse users”

---

### 4. Validation & Rules

Rules deciding whether the values are acceptable and submission may proceed.

*Usual journey stage:* `Validation, dependencies & conditional logic`  
*Most often confused with:* *Form Configuration*, *Observability & Debugging*

#### Form validation, messages & conditional rules

Pre-submission rules that determine whether form values are valid and explain how users should correct them.

**Use for:** Input & cross-field validation; Conditional logic; Validation messages.

> ⛔ **Do NOT use when:** Rules that must also hold through API/MCP belong to Server-side & API enforcement. Runtime failures belong to Logs & error diagnostics.

- “When the identifier is null, Port auto-generates an identifier with a UUID so no error is raised from Port API, even though we want to enforce it”
- “conditional logic like "replica count must be at least 3 when deploying to production", cross-field rules like email confirmation, and meaningful error messages”

#### Server-side & API enforcement

Consistent validation and guardrail enforcement across UI, API, MCP, JSON and other non-UI invocation paths.

**Use for:** Server-side & API enforcement.

> ⛔ **Do NOT use when:** Missing integrations belong to Backends, APIs & event triggers. UI-only validation belongs to Form validation, messages & conditional rules.

- “validate the user input for corectness against custom business logic, and display an error returned from the backend under the text field, without actually submitting the form”
- “Any execution path that bypasses the form UI, JSON mode, direct API calls, or Port's MCP, skips these validations entirely, allowing invalid or unauthorized inputs to be submitted.”

#### Expression & JQ authoring

Writing, testing, understanding and maintaining JQ or other expressions used in Action configuration.

**Use for:** Expression and JQ rule authoring.

> ⛔ **Do NOT use when:** Runtime expression failures belong to Logs & error diagnostics. Payload reshaping belongs to Payload mapping & transformation.

- “it is not possible to use JQ when creating conditions for Day-2 or Delete actions”
- “We should find a way to alert relevant stakeholders to the fact that the calculated value is invalid when it occurs.”

---

### 5. Invocation & Integrations

How the submitted Action connects to the system that does the work.

*Usual journey stage:* `Backend & invocation setup`  
*Most often confused with:* *Identity, Secrets & Security*, *Orchestration*

#### Backends, APIs & event triggers

Choosing and connecting the backend, API, integration or event mechanism that invokes or triggers the work.

**Use for:** Backend & invocation method selection; APIs & external integrations; Event triggers & action-to-automation integration.

> ⛔ **Do NOT use when:** Payload shape belongs to Payload mapping & transformation. Private execution infrastructure belongs to Execution agents & runners.

- “another invocation type that would be awesome, would be directly integrating with Lambda and OpenFAAS”
- “Add the option to use a generic invocation method that sends a log message to an action run ID provided as an input.”

#### Payload mapping & transformation

Selecting, reshaping, encoding, previewing or passing through the data sent to a backend.

**Use for:** Payload mapping & transformation.

> ⛔ **Do NOT use when:** Information inherited from the launch context belongs to Contextual launch, targeting & pre-fill. Authentication identity belongs to Identity, Secrets & Security.

- “The self-service engineer should be able to choose which entity properties or property are relevant to send to the self-service action.”
- “base64 encoding username:PAT (or :PAT) is the correct approach, and right now you have to do so outside of Port”

#### Execution agents & runners

Where an Action physically executes, including agent selection, routing, connectivity and runner configuration.

**Use for:** Execution agents & runners.

> ⛔ **Do NOT use when:** Selecting a normal SaaS backend belongs to Backends, APIs & event triggers. Credentials belong to Credentials, secrets & request signing.

- “You cannot control which agent processes which message at the moment.”
- “We want to communicate with an internal service without the hassle of handling the self signed certificates”

---

### 6. Identity, Secrets & Security

Who or what executes the Action, and how sensitive data is protected.

*Usual journey stage:* `Backend & invocation setup`  
*Most often confused with:* *Invocation & Integrations*, *Permissions & Approvals*

#### Authentication, execution identity & requester context

Who or what executes the Action and which trusted requester identity/context is propagated to downstream systems.

**Use for:** Authentication & delegated execution; Service accounts & execution identity; Current-user and context propagation.

> ⛔ **Do NOT use when:** Permission to start the Action belongs to Access control & action eligibility. Secret storage belongs to Credentials, secrets & request signing.

- “Passing the User Form .user object to the backend is not safe, as it can be spoofed and allow user impersonation.”
- “we need is to perform a request to obtain the JWT before each SSA action and then include it in the header of the action”

#### Credentials, secrets & request signing

Securely storing, resolving and using credentials, tokens and signatures for Action invocations.

**Use for:** Credentials & secrets management; Message signing & webhook security.

> ⛔ **Do NOT use when:** Preventing sensitive values from appearing in UI/logs belongs to Sensitive-data masking & redaction.

- “Infosec policy mandates all secrets stored in HashiCorp Vault only”
- “Allow the {{ .secrets.<secret_name> }} syntax in the secret field for webhook, consistent with how secrets are already used in self-service action and automation payloads.”

#### Sensitive-data masking & redaction

Preventing sensitive inputs, payload fields, outputs and logs from being exposed to unauthorized viewers.

**Use for:** Sensitive-data masking & redaction.

> ⛔ **Do NOT use when:** Secret storage and retrieval belong to Credentials, secrets & request signing. General payload visibility belongs to Observability unless the restriction is security-driven.

- “There is currently no way to mark a variable as sensitive so that its value is redacted or masked in the run history display.”
- “defining an input as a secret does not work in cases where there is an approver on the action”

---

### 7. Permissions & Approvals

Who can see or run an Action, and who must approve it before it runs.

*Usual journey stage:* `Permissions & approvals`  
*Most often confused with:* *Identity, Secrets & Security*, *Discovery, Organization & Reuse*

#### Access control & action eligibility

Rules deciding who may view, create, edit, trigger or inspect an Action and whether the UI reflects that eligibility early.

**Use for:** RBAC & dynamic permissions; Action visibility & eligibility.

> ⛔ **Do NOT use when:** The UI for creating/testing permission rules belongs to Permission authoring & testing. Downstream execution identity belongs to Identity, Secrets & Security.

- “those values aren't present on the .user object in the dynamic permissions/self service action context”
- “I want to allow some users to be able to create self-service actions in our STG environment without giving them full Admin access.”

#### Permission authoring & testing

Creating, previewing, testing and debugging permission rules and their outcomes.

**Use for:** Permission authoring & testing.

> ⛔ **Do NOT use when:** New access-control capability belongs to Access control & action eligibility. Action-definition release lifecycle belongs to Authoring, Testing & Management.

- “the error message logged provides no context about what specific part of the dynamic permission caused the action to be denied”
- “execute permissions can be removed entirely, which allows an action to be saved with no execute permissions at all”

#### Approval policies & approver routing

Deciding when approval is required, how many approvals are needed and who should receive the request.

**Use for:** Approval policies & thresholds; Approver routing & identity.

> ⛔ **Do NOT use when:** The approver's decision UI and messages belong to Approver experience & notifications. Mid-workflow approvals belong to Orchestration.

- “Allows Port Admins to intervene and instantly approve any pending request manually.”
- “we approve our own requests... we have to approve our own request, which is just extra work”

#### Approver experience & notifications

How approvers are notified, understand the request, communicate, edit permitted values and approve or reject it.

**Use for:** Approver experience & request editing; Approval notifications.

> ⛔ **Do NOT use when:** Policy configuration and approver selection belong to Approval policies & approver routing. Historical approval evidence belongs to Run history, audit, APIs & export.

- “the admin that approves the request will want to make a change to the inputs provided by the user”
- “both the approver and the requester should be able to exchange messages/comments directly within the action run context in Port”

---

### 8. Orchestration

Actions containing several connected execution steps, decisions or systems.

*Usual journey stage:* `Backend & invocation setup`  
*Most often confused with:* *Form Configuration*, *Invocation & Integrations*, *Execution Lifecycle*

#### Multi-step orchestration, branching & data flow

Building multi-step workflows with sequencing, branches, multiple systems and data passed between steps.

**Use for:** Multi-step workflows; Shared context & output passing; Branching & conditional paths; Multi-backend & multi-system sequencing.

> ⛔ **Do NOT use when:** Multiple visual pages in a form belong to Form Configuration. Selecting a single backend belongs to Invocation & Integrations.

- “the .outputs available to downstream JQ expressions only include workflowRunUrl and workflowRunId, not result, workflowStatus, or any error detail”
- “Due to Port's current setup, I have to combine these 5 GH actions into one since the SSA can only trigger one backend”

#### Workflow approvals, error handling & recovery

Controlling workflow steps through intermediate approvals, failure branches, retries, compensation and recovery behavior.

**Use for:** Intermediate approvals; Step-level error handling & recovery.

> ⛔ **Do NOT use when:** Approval before an Action starts belongs to Permissions & Approvals. Whole-run retry/cancel belongs to Execution Lifecycle.

- “Can't easily implement basic alerting without misrepresenting operational health.”
- “prompt an approval request and based on the approval, invoke another trigger”

---

### 9. Execution Lifecycle

What users can do to a Run, and how the Run behaves over its life.

*Usual journey stage:* `Execution, monitoring & run control`  
*Most often confused with:* *Observability & Debugging*, *Orchestration*

#### Retry, rerun, cancel & resume

User controls for repeating, interrupting or continuing an Action run.

**Use for:** Retry, rerun & duplicate execution; Cancel, stop & resume.

> ⛔ **Do NOT use when:** Automatic resilience belongs to Reliability, timeouts & concurrency. Step-level recovery belongs to Orchestration.

- “Ability to cancel the execution of an action after triggering it”
- “Adding a retry action for a run can be nice addition”

#### Reliability, timeouts & concurrency

Runtime safeguards governing duration, simultaneous execution, duplicate prevention and automatic handling of transient failures.

**Use for:** Timeouts; Concurrency, rate limits & duplicate prevention; Reliability & transient-failure handling.

> ⛔ **Do NOT use when:** Manual retry/cancel belongs to Retry, rerun, cancel & resume. A deterministic product defect remains a Bug problem type.

- “Ability to configure timeout values for actions within Port so that certain operations, like deploying a service, do not exceed a certain duration.”
- “users can click the button multiple times, unintentionally triggering duplicate executions”

#### Completion & result-state control

Determining, setting or correcting when a Run is complete and which terminal/result state it has.

**Use for:** Completion & result-state control.

> ⛔ **Do NOT use when:** Displaying status belongs to Run status, progress & notifications. Failure explanation belongs to Logs & error diagnostics.

- “I would like to have the same ability just with create/update invocation type.”
- “the list should contain all Gitlab's possible pipeline statuses: (created, waiting_for_resource, preparing, pending, running, success, failed, canceled, skipped, manual, scheduled)”

---

### 10. Observability & Debugging

Helping users understand what happened during or after a Run.

*Usual journey stage:* `Execution, monitoring & run control`  
*Most often confused with:* *Execution Lifecycle*, *Validation & Rules*, *Permissions & Approvals*

#### Run status, progress & notifications

Showing current run state/progress and proactively notifying users of success, failure, delay or completion.

**Use for:** Run status & progress; Execution notifications & alerting.

> ⛔ **Do NOT use when:** Changing the state belongs to Completion & result-state control. Detailed diagnostics belong to Logs & error diagnostics.

- “action run status are predefined and limited to "Success", "Failure" and "In progress"”
- “There is no indication of whether the action is queued, rate-limited, or encountered an error during startup.”

#### Logs & error diagnostics

Detailed runtime logs, backend responses and actionable explanations of execution failures.

**Use for:** Logs & log streaming; Error messages & backend responses.

> ⛔ **Do NOT use when:** Pre-submission errors belong to Validation & Rules. Sensitive-log masking belongs to Identity, Secrets & Security.

- “users must wait for an action to complete or a certain amount of data to be processed before logs can be viewed”
- “Currently, there is no way to edit current action logs.”

#### Run history, audit, APIs & export

Searching, auditing, filtering, exporting or programmatically querying historical Run and approval records.

**Use for:** Run history, audit & filtering; Run-history APIs & export; Approval audit & context.

> ⛔ **Do NOT use when:** Linking a Run to the objects it changed belongs to Run traceability & related entities. Definition-change history belongs to Authoring, Testing & Management.

- “A dashboard/homepage widget that displays the runs of a specific self-service action.”
- “there is not enough ability for filtering of the returned runs, there is no "include" parameter, and the limit is set to max of 1000 runs without ability for pagination”

#### Run traceability & related entities

Connecting a Run to its Action, requester, pipeline and the entities/resources it affected.

**Use for:** Run traceability & related entities.

> ⛔ **Do NOT use when:** General historical querying belongs to Run history, audit, APIs & export. Outbound payload construction belongs to Payload mapping & transformation.

- “The Gitlab default payload config should reflect back a url to the pipeline for easy access”
- “Currently it's only possible tying entities to an action run by manually sending an API request to the entities with the `run_id`”

---

### 11. Authoring, Testing & Management

Helping builders safely create, test, edit, publish and maintain Actions.

*Usual journey stage:* `Testing, editing & publishing`  
*Most often confused with:* *Execution Lifecycle*, *Validation & Rules*

#### Action authoring, testing & release management

Safely creating, learning, previewing, editing, publishing, disabling, versioning and rolling back Action definitions.

**Use for:** Preview & dry run; Playground, examples & in-product help; Editing & unsaved-change safety; Drafts, publishing & disablement; Versioning, change detection & rollback.

> ⛔ **Do NOT use when:** Form fields and end-user form UX belong to Form Configuration. Programmatic configuration and reuse belong to Reusable configuration, API & IaC management.

- “In the GUI mode, users may accidentally navigate away without saving their changes.”
- “The examples that are being provided are automatically generated and in some cases are not aligned with the actual data.”

#### Reusable configuration, API & IaC management

Creating reusable Action definitions and managing or moving them programmatically through API, IaC, templates, import or export.

**Use for:** API & IaC configuration management; Reusability & templates.

> ⛔ **Do NOT use when:** Invoking an Action via API belongs to Invocation & Integrations. Reusing only a permission policy remains primarily Access control & action eligibility.

- “It would be really nice if you could go into a self service action and see a similar view.”
- “that action has to be created and its inputs need to be configured manually”

---

## Problem types (14)

Independent of product area. Note what is **absent**: there is no "general or irrelevant feedback" problem type. Irrelevance is expressed as `is_relevant = false`, so out-of-scope records are excluded from every distribution rather than diluting one.

| Problem type | Meaning |
|---|---|
| **Bug / defect** | The capability exists but behaves incorrectly. |
| **Reliability issue** | It works inconsistently -- intermittent failures, timeouts, flakiness. |
| **Feature gap** | The capability does not exist at all. |
| **Configuration complexity** | It is possible, but requires complicated or repeated configuration. |
| **Usability friction** | It works, but is confusing or difficult to use. |
| **Documentation or discoverability gap** | The capability exists but users cannot find or understand it. |
| **Validation gap** | Invalid input can pass, or a required rule is missing. |
| **Poor error message** | The failure is real but the explanation does not help the user fix it. |
| **Observability or debugging gap** | Users lack the status, logs or context needed to understand what happened. |
| **Integration or API gap** | An API or integration capability is missing. |
| **Security or privacy concern** | Sensitive information, identity or authorization is exposed or unsafe. |
| **Performance or scalability limitation** | The problem appears at high volume, scale or load. |
| **Reusability or maintainability issue** | The same configuration must be repeated and is hard to maintain. |
| **Positive / completed feedback** | Describes a shipped or completed improvement with no current unmet pain. |

## Severity

How much the problem hurts **as described in the text** — not how popular the request is, and not how hard it would be to build.

| Level | Meaning |
|---|---|
| **5** | Blocking. No workaround exists, or the issue is a security or data risk. |
| **4** | Severe. A painful workaround exists but costs real time on every use. |
| **3** | Moderate. Slows people down or forces repeated manual configuration. |
| **2** | Minor. Noticeable friction with an easy workaround. |
| **1** | Nice to have. A polish or convenience request. |

## Feedback polarity (3)

What the customer was expressing, judged from the text. Deliberately independent of lifecycle status: a completed roadmap item still records the pain that prompted it, so a shipped request is not automatically positive.

| Polarity | Meaning |
|---|---|
| **Negative** | Describes a problem, unmet need, blocker, friction, failure or difficulty -- including a feature request clearly motivated by current pain or an inability to finish a task. |
| **Positive** | Expresses satisfaction, praise, a successful outcome, or confirms that a shipped capability solved the problem. |
| **Neutral** | Primarily informational, descriptive, a factual question or a technical clarification, with no clear praise or pain. |

## Personas (5)

| Persona | Who they are |
|---|---|
| **Action builder** | Platform engineer or admin who creates and maintains Actions. |
| **Developer / end user** | Person who runs an Action to get something done. |
| **Approver / manager** | Person who reviews and approves Action requests. |
| **Platform admin** | Administers Port itself -- permissions, integrations, org settings. |
| **Unknown** | The source text does not make the persona clear. |

## Lifecycle status and source system

Lifecycle statuses: `Open`, `Planned`, `In progress`, `Completed`, `Closed`, `Unknown`.

**Open statuses** — `In progress`, `Open`, `Planned` — are the only ones counted towards a product-action ranking. Completed and closed work is excluded so a shipped feature cannot argue for itself again; it stays visible in the evidence explorer, where "we already built this" is itself a finding.

Only `Open` counts towards a product action's supporting count or its ranking. Planned and In progress mean the work is already committed, so counting them as demand would argue for building something that is already being built. They stay visible in the evidence section, labelled with their status.

Product actions are **not** taxonomy subcategories. Feedback is grouped by the change it asks for, and each group stores the exact feedback ids supporting it -- one subcategory routinely holds several genuinely different requests. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the grouping and the full ranking key order.

Portal statuses are normalised through this map. Anything unrecognised becomes `Unknown` rather than passing through as if it had been normalised.

| Portal value | Normalised |
|---|---|
| `open` | `Open` |
| `under review` | `Open` |
| `exploring` | `In progress` |
| `planned` | `Planned` |
| `in progress` | `In progress` |
| `complete` | `Completed` |
| `completed` | `Completed` |
| `closed` | `Closed` |
| `resolved` | `Completed` |

Source systems: `Slack`, `Zendesk`, `Gong`, `Port portal`. **This POC collects only `Port portal`** — the other three exist in the schema because production ingests them through the same shape. No record is ever labelled with a source it did not come from, and a test asserts it.

---

## Disambiguation rules (13)

Where a record could reasonably go either of two ways, these decide. Whatever ambiguity is left over is reported through `confidence` and `needs_human_review` rather than papered over.

1. DISCOVERY vs PERMISSIONS. 'I cannot find the Action' -> Discovery, Organization & Reuse. 'This user should not see the Action' -> Permissions & Approvals. Absence caused by an authorization rule is a permissions problem, not a search problem.

2. CONTEXT vs FORM CONFIGURATION. 'Port already knows which Service I am using' -> Context, Targeting & Pre-fill. 'I need a new Service selector field, or a different field order' -> Form Configuration.

3. DYNAMIC INPUT vs VALIDATION. If a field CHANGES because of another selection -> Form Configuration -> Dynamic & dependent inputs. If the system CHECKS whether an entered value is allowed -> Validation & Rules.

4. MULTI-PAGE FORM vs ORCHESTRATION. One form divided into several visual pages -> Form Configuration -> Form layout, sections & multi-page forms. Several connected BACKEND operations -> Orchestration.

5. INVOCATION vs IDENTITY AND SECURITY. 'Send the form to GitHub Actions' -> Invocation & Integrations. 'Use a scoped service account to authenticate' -> Identity, Secrets & Security.

6. PERMISSIONS vs APPROVALS. 'Who may run the Action?' -> Permissions & Approvals -> RBAC / Action visibility. 'Who must approve it before it runs?' -> Permissions & Approvals -> Approval policies / routing. Both share the stage 'Permissions & approvals'.

7. VALIDATION ERROR vs RUNTIME ERROR. An error BEFORE submission -> Validation & Rules -> Validation messages, stage 'Validation, dependencies & conditional logic'. A failure AFTER the Action started -> Observability & Debugging -> Error messages & backend responses, stage 'Execution, monitoring & run control'.

8. EXECUTION LIFECYCLE vs OBSERVABILITY. 'Let me retry the failed Run' -> Execution Lifecycle. 'Explain why the Run failed' -> Observability & Debugging. Acting on the Run vs understanding the Run.

9. APPROVAL NOTIFICATION vs EXECUTION NOTIFICATION. 'The approver did not receive the request' -> Permissions & Approvals -> Approval notifications, stage 'Permissions & approvals'. 'The requester did not receive a failure alert' -> Observability & Debugging -> Execution notifications & alerting, stage 'Execution, monitoring & run control'.

10. CREDENTIALS vs INVOCATION CONFIGURATION. Storing, rotating or protecting a secret -> Identity, Secrets & Security. Choosing and wiring the backend that runs the Action -> Invocation & Integrations.

11. CONTEXTUAL DEFAULT vs GENERAL DEFAULT. A value inferred from the Entity page or originating surface -> Context, Targeting & Pre-fill. A default computed from other form fields, or a fixed default for everyone -> Form Configuration -> Defaults & computed fields.

12. PRIMARY vs SECONDARY. The PRIMARY assignment is the product area where the main change should be implemented. Add a secondary assignment only when another product area is meaningfully involved -- never merely because another technology is mentioned.

13. OUT OF SCOPE. General Port audit logs, general catalog feedback, general Automation authoring unrelated to Actions, platform-wide admin RBAC, scorecards, dashboards and unrelated integrations are NOT Action Configuration. Set is_relevant=false with a relevance_reason instead of forcing them into a category.

## Commonly confused pairs

| This… | …not this |
|---|---|
| **Discovery, Organization & Reuse**<br>"I cannot find the Action." | **Permissions & Approvals**<br>"This user should not see the Action." |
| **Context, Targeting & Pre-fill**<br>"Port already knows which Service I am using." | **Form Configuration**<br>"I need a new Service selector field." |
| **Form Configuration → Dynamic & dependent inputs**<br>"The region options should change when I choose a cloud provider." | **Validation & Rules**<br>"The selected region is not allowed for this environment." |
| **Form Configuration**<br>"Divide the form into three screens." | **Orchestration**<br>"Run three backend operations in sequence." |
| **Invocation & Integrations**<br>"Send the form to GitHub Actions." | **Identity, Secrets & Security**<br>"Use a scoped service account to authenticate." |
| **Permissions & Approvals - permissions side**<br>"Who may run the Action?" | **Permissions & Approvals - approvals side**<br>"Who must approve the Action?" |
| **Execution Lifecycle**<br>"Let me retry the failed Run." | **Observability & Debugging**<br>"Explain why the Run failed." |
| **Permissions & Approvals → Approval notifications**<br>"The approver did not receive the request." | **Observability & Debugging → Execution notifications & alerting**<br>"The requester did not receive a failure alert." |

## Worked examples

**"I launched the Action from a Service page, but I still have to select the Service manually."**

- Category: `Context, Targeting & Pre-fill`
- Subcategory: `Contextual launch, targeting & pre-fill`
- Problem type: `Usability friction`
- Journey stage: `Contextual entry, targeting & pre-fill`
- *Why:* The problem is not the type of input. Port already knows the relevant Service and should fill it in automatically.

**"The available regions should change after I select a cloud provider."**

- Category: `Form Configuration`
- Subcategory: `Dynamic inputs, defaults & computed fields`
- Problem type: `Feature gap`
- Journey stage: `Form & input configuration`
- *Why:* The field's options must react to another selection. Nothing is being checked for validity yet, so this is not Validation.

**"The user can run the Action, but a manager must approve production deployments."**

- Category: `Permissions & Approvals`
- Subcategory: `Approval policies & approver routing`
- Problem type: `Feature gap`
- Journey stage: `Permissions & approvals`
- *Why:* The issue is not whether the user may start the Action. It is the approval required before it executes.

**"The Action started and failed, but the run page does not explain why."**

- Category: `Observability & Debugging`
- Subcategory: `Logs & error diagnostics`
- Problem type: `Poor error message`
- Journey stage: `Execution, monitoring & run control`
- *Why:* The failure happened after submission, so it belongs to execution rather than form validation.

**"Divide this long form into three screens."**

- Category: `Form Configuration`
- Subcategory: `Form presentation, layout & guidance`
- Problem type: `Usability friction`
- Journey stage: `Form & input configuration`
- *Why:* Several visual pages are a form-layout concern. Only several BACKEND operations would be Orchestration.

**"The approver never received the Slack request to approve."**

- Category: `Permissions & Approvals`
- Subcategory: `Approver experience & notifications`
- Problem type: `Bug / defect`
- Journey stage: `Permissions & approvals`
- *Why:* An approval-request notification blocks the user at the approval stage, not at execution -- unlike a success or failure alert.

**"Secrets must be stored in HashiCorp Vault, not inside Port."**

- Category: `Identity, Secrets & Security`
- Subcategory: `Credentials, secrets & request signing`
- Problem type: `Security or privacy concern`
- Journey stage: `Backend & invocation setup`
- *Why:* Storing and retrieving the credential is a secrets concern, even though the credential is used during invocation.

**"Let me retry the failed Run without filling in the form again."**

- Category: `Execution Lifecycle`
- Subcategory: `Retry, rerun, cancel & resume`
- Problem type: `Feature gap`
- Journey stage: `Execution, monitoring & run control`
- *Why:* Acting on the Run is Execution Lifecycle. Explaining why it failed would instead be Observability & Debugging.

## Glossary

| Term | Plain-language meaning |
|---|---|
| **Action** | A form that lets someone request or trigger a task, such as deploying a service or requesting access. |
| **Entity** | An item stored in Port, such as a service, application, environment or resource. |
| **Blueprint** | The template defining what a type of Entity looks like in Port. |
| **Taxonomy Category** | The broad product area a piece of feedback belongs to. There are 11. |
| **Taxonomy Subcategory** | The specific part of that product area needing attention. |
| **Problem Type** | What kind of problem it is -- a bug, a missing feature, a confusing experience, and so on. |
| **Journey Stage** | Where in the Action experience the user hit the problem. |
| **Pre-fill** | Automatically placing known information into a field so the user does not have to enter it again. |
| **Input** | A field in a form where the user enters or selects information. |
| **Validation** | A check confirming whether the information entered is acceptable. |
| **Payload** | The package of information sent from the form to the system that performs the task. |
| **Webhook** | A way for one system to automatically send information to another when something happens. |
| **API** | A structured way for software systems to communicate with each other. |
| **Credential** | Information used to prove that a system or user is allowed to connect. |
| **Secret** | Sensitive information, such as a password or access token, that must be stored securely. |
| **Permission** | A rule determining who is allowed to see or do something. |
| **Approval** | A decision another person must make before an Action may continue. |
| **Execution** | The period when the requested task is actually being performed. |
| **Run** | One specific attempt to execute an Action. |
| **Log** | A record of events and messages produced while an Action is running. |
| **Retry** | Trying to run a failed Action again. |
| **Orchestration** | Coordinating several connected tasks or systems as one process. |
| **Draft** | A saved version of an Action that is not yet published. |
| **Lifecycle Status** | Whether the request is Open, Planned, In progress, Completed or Closed. |
| **Product Action** | A recommended product change, grouped from all the feedback records asking for the same thing. |
| **Evidence quote** | A short passage copied word-for-word from the original feedback, verified by code. |
| **Persona** | The kind of user the feedback is coming from. |
| **Source system** | Where the feedback came from -- Slack, Zendesk, Gong or the Port portal. |

