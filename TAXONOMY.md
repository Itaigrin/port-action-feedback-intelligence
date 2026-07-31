<!-- GENERATED FILE — do not edit by hand.
     Source: src/models/taxonomy.py
     Regenerate: python -m scripts.render_taxonomy_doc -->

# Taxonomy

How every piece of feedback is categorised. Defined **before** any data was classified, so the categories were not fitted to the answer.

Single source of truth: [`src/models/taxonomy.py`](src/models/taxonomy.py). The classifier, the Pydantic schema, the dashboard, the in-app guide and this document all read from it. This file is generated from that module, so it cannot describe a taxonomy the code does not implement.

> **Version v2.1.** The flat theme list was replaced by a two-level structure of 11 categories and 63 subcategories, with problem type, persona, lifecycle status and source system split out as independent dimensions. Because the change is semantic rather than cosmetic, every record was **reclassified** rather than relabelled — the classification cache is keyed on the taxonomy version precisely so that a revision cannot replay old labels.

---

## Four independent dimensions

| Dimension | Question it answers | Count |
|---|---|---|
| **Taxonomy category** | *Which broad product area* does this concern? | **11** |
| **Taxonomy subcategory** | *Which specific part* of that area needs work? | **63** |
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

## Categories and subcategories (11 × 63)

Each subcategory carries a **Do NOT use when** rule. Those rules matter more than the definitions: almost every misclassification is a confusion between two adjacent subcategories, and the avoid line is what names the neighbour and sends you to it.

### 1. Discovery, Organization & Reuse

How users find, organize, display and reuse Actions.

*Usual journey stage:* `Action discovery & organization`  
*Most often confused with:* *Permissions & Approvals*, *Context, Targeting & Pre-fill*

#### Action discovery, grouping & ordering

Finding the right Action in a crowded catalog.

**Use for:** Searching for an Action; Categories, subcategories, folders, tags; Sorting and ordering; Unclear Action names; Too many Actions in one catalog; Organizing Actions in menus or catalogs.

> ⛔ **Do NOT use when:** The Action is hidden because the user lacks permission -- that is Permissions & Approvals.

- "There are too many Actions on the page and no way to group them."
- "We cannot tell which Action deploys a service from the name alone."

#### Conditional availability & placement

Controlling where an Action appears, for non-authorization reasons.

**Use for:** Showing an Action only on a specific page or surface; Showing an Action only for a specific Blueprint or Entity type; Placement rules that are not authorization rules.

> ⛔ **Do NOT use when:** Hidden because of permissions -> Permissions & Approvals. Retaining the launch context -> Context, Targeting & Pre-fill.

- "This Action should only appear on Service pages, not everywhere."
- "Show the deploy Action only for Blueprints that have a repo."

#### Bulk actions

Running one Action against many Entities at once.

**Use for:** Running one Action against several Entities; Selecting multiple targets; Batch execution and bulk configuration operations.

> ⛔ **Do NOT use when:** Several backend steps inside one Action -- that is Orchestration.

- "Let me run this Action on all 40 services at once."
- "Select multiple entities from the table and trigger one Action."

#### Reusability & templates

Reusing an Action definition instead of rebuilding it each time.

**Use for:** Reusing an Action definition, templates, shared configurations; Reusing an Action across Blueprints or teams; Avoiding repeated manual Action setup; Cloning standardized Action configurations.

> ⛔ **Do NOT use when:** If the reusable object is specifically a permission policy, the primary category may be Permissions & Approvals with this as secondary.

- "We copy the same Action definition into six Blueprints by hand."
- "Give us Action templates so teams start from a standard config."

---

### 2. Context, Targeting & Pre-fill

Using what Port already knows so the Action opens in the right context and stops asking the user to repeat itself.

*Usual journey stage:* `Contextual entry, targeting & pre-fill`  
*Most often confused with:* *Form Configuration*, *Discovery, Organization & Reuse*

#### Contextual entry & deep links

Opening an Action from a specific place, with that context intact.

**Use for:** Direct links to an Action; Links that carry Action context; Opening an Action from a specific page; Preserving context through a URL; Deep-linking to a form with known values.

> ⛔ **Do NOT use when:** A fixed default configured for everyone is not contextual -- that is Form Configuration.

- "Send a link that opens this Action already filled in for this service."
- "We want a URL that deep-links straight into the request form."

#### Entity and resource targeting

Deciding which Entity or resource the Action applies to.

**Use for:** Selecting which Entity or resource the Action applies to; Automatically determining the target; Target Blueprint, Service, Namespace, Environment or Resource; Avoiding ambiguous Action targets.

> ⛔ **Do NOT use when:** Adding a new selector field is Form Configuration.

- "The Action should know it applies to the namespace I came from."
- "It is ambiguous which resource this Action will actually change."

#### Pre-fill & context-specific defaults

Filling in values Port can already infer from where the user was.

**Use for:** Automatically filling known values; Values derived from the current Entity; Values derived from the originating page; Context-specific defaults; Avoiding repeated manual selection.

> ⛔ **Do NOT use when:** A fixed default configured for every user may belong to Form Configuration -> Defaults & computed fields.

- "I opened the Action from this Service page, so the Service should already be selected."
- "Stop asking me for the environment when the page already knows it."

#### Embedded & alternative launch surfaces

Launching the Action from somewhere other than the Self-Service page.

**Use for:** Opening the Action in a modal; Opening the Action inside an Entity page; Launching from a widget; Launching from Slack or another surface; Avoiding navigation to the general Self-Service page.

> ⛔ **Do NOT use when:** Changing which users can see the Action is Permissions & Approvals.

- "Let us trigger this Action straight from Slack."
- "Open the Action in a modal instead of navigating away."

#### Current-user and context propagation

Passing who the requester is, and their org context, into the Action.

**Use for:** Passing the current user; Passing team, organization, Entity, Blueprint, account or environment context; Using requester identity as an input; Propagating context into the Action or backend invocation.

> ⛔ **Do NOT use when:** Executing *as* that user, or authenticating as them, is Identity, Secrets & Security.

- "The backend needs to know which team the requester belongs to."
- "Pass the current user's email into the payload automatically."

---

### 3. Form Configuration

The visible form, the fields it contains, and how users complete it.

*Usual journey stage:* `Form & input configuration`  
*Most often confused with:* *Validation & Rules*, *Context, Targeting & Pre-fill*, *Orchestration*

#### Input types & controls

Which kinds of form field exist at all.

**Use for:** Text, number, date, file upload, dropdown, multi-select; Maps, tables, long text, boolean controls; Any missing or limited form control.

> ⛔ **Do NOT use when:** A field that changes because of another field is Dynamic & dependent inputs.

- "We need a file upload field to attach a config."
- "There is no map or key-value input type."

#### Structured & repeatable inputs

Repeating a group of fields, or entering a list of objects.

**Use for:** Arrays of objects; Repeatable sections, adding or removing rows; Structured lists and nested input groups; Repeating the same group of fields multiple times.

> ⛔ **Do NOT use when:** Several backend steps -> Orchestration. Several form pages -> Form layout, sections & multi-page forms.

- "Let users add several environment-variable rows."
- "We need an array of objects, not one flat text field."

#### Dynamic & dependent inputs

Fields that change by themselves based on other fields or data.

**Use for:** Dropdown values changing based on another field; One field depending on another; Options loaded from an API or dataset; Conditional field visibility; Dynamically enabled, disabled or read-only fields; Inputs that adapt while the user fills in the form.

> ⛔ **Do NOT use when:** If the issue is only whether the entered value is acceptable, that is Validation & Rules.

- "The region options should change after I pick a cloud provider."
- "Show the risk field only when environment is Production."

#### Defaults & computed fields

Values the form fills in or calculates on its own.

**Use for:** General default values; Computed fields, formula-derived inputs; Automatically calculated values; Values derived from other form fields.

> ⛔ **Do NOT use when:** If the value comes from the page or Entity the Action was opened from, use Context, Targeting & Pre-fill.

- "Default the replica count to 3 for everyone."
- "Compute the resource name from the two fields above."

#### Form layout, sections & multi-page forms

How the form is arranged and broken up visually.

**Use for:** Field ordering, grouping, form sections, collapsible sections; Reducing form complexity; Splitting a long form into several visual pages; Wizard-like form navigation; Filters placed before large selectors.

> ⛔ **Do NOT use when:** IMPORTANT: several visual PAGES belong here; several backend OPERATIONS in sequence belong to Orchestration.

- "Split this 25-field form into three steps."
- "Group the network settings into a collapsible section."

#### Labels, descriptions & display controls

The wording and presentation around each field.

**Use for:** Field labels, descriptions, placeholder text, help text; Units and display formatting; Hiding labels; Improving the clarity of a field.

> ⛔ **Do NOT use when:** An unclear message about an invalid value is Validation & Rules -> Validation messages.

- "Nobody understands what this field wants; we need help text."
- "Show the unit (GB) next to the size field."

---

### 4. Validation & Rules

Rules deciding whether the values are acceptable and submission may proceed.

*Usual journey stage:* `Validation, dependencies & conditional logic`  
*Most often confused with:* *Form Configuration*, *Observability & Debugging*

#### Input & cross-field validation

Checking that entered values are acceptable.

**Use for:** Required fields, format validation; Minimum or maximum values, regex validation; Comparing two fields, date rules, cross-field checks; Preventing invalid form submission.

> ⛔ **Do NOT use when:** A dropdown merely changing its options is Form Configuration -> Dynamic & dependent inputs.

- "Replica count must be at least 3 in production."
- "The end date must be after the start date."

#### Conditional logic

Business rules that decide whether submission can continue.

**Use for:** "If A, then B is required"; Rules that determine whether submission can proceed; Conditional requirements; Business rules applied before execution.

> ⛔ **Do NOT use when:** A dropdown simply changing its options -> Form Configuration -> Dynamic & dependent inputs.

- "If the tier is Enterprise, the approval reason becomes required."
- "Block submission unless a cost centre is supplied."

#### Server-side & API enforcement

Making the rules hold even when the UI is not used.

**Use for:** Validation that works only in the UI; API, MCP, webhook or backend paths bypassing validation; Consistent enforcement across UI and non-UI invocation paths; Security-sensitive server-side validation.

> ⛔ **Do NOT use when:** Missing an integration entirely is Invocation & Integrations.

- "The API accepts values the form would have rejected."
- "MCP execution bypasses our front-end validation."

#### Validation messages

Explaining clearly what is wrong before submission.

**Use for:** Unclear pre-submission error messages; Missing explanation of which value is invalid; Messages that do not explain how to correct the form; Custom validation messages.

> ⛔ **Do NOT use when:** Errors AFTER the Action started belong to Observability & Debugging -> Error messages & backend responses.

- "It says invalid but never says which format it wants."
- "Let us write our own message for this regex rule."

#### Expression and JQ rule authoring

Writing, testing and debugging the rule expressions themselves.

**Use for:** Writing JQ expressions; Testing rule expressions; Rule-builder usability; Debugging condition syntax; Previewing rule results and expression validation.

> ⛔ **Do NOT use when:** Runtime JQ failures during execution are Observability & Debugging.

- "The jqQuery becomes unreadable with five conditions."
- "We need a way to preview what this expression evaluates to."

---

### 5. Invocation & Integrations

How the submitted Action connects to the system that does the work.

*Usual journey stage:* `Backend & invocation setup`  
*Most often confused with:* *Identity, Secrets & Security*, *Orchestration*

#### Backend & invocation method selection

Choosing what actually runs when the form is submitted.

**Use for:** Selecting a webhook, pipeline, GitHub workflow, GitLab pipeline, Kafka target; Choosing how the Action is invoked; Supporting additional invocation methods; Configuring which execution mechanism should run.

> ⛔ **Do NOT use when:** Viewing or controlling a Run that already started is Execution Lifecycle or Observability & Debugging.

- "We need to trigger an Azure DevOps pipeline, not just GitHub."
- "Support Kafka as an invocation target."

#### Payload mapping & transformation

Shaping the data sent to the backend.

**Use for:** Building the outbound payload; Renaming submitted fields, transforming values; Mapping form inputs to backend parameters; Restructuring JSON, adding or removing payload fields; Previewing the outgoing payload.

> ⛔ **Do NOT use when:** Changing what the user sees in the form is Form Configuration.

- "Use JQ to reshape the payload before sending it to the workflow."
- "Let us preview exactly what will be POSTed."

#### APIs & external integrations

Connecting Actions to outside systems.

**Use for:** Connecting Actions to external APIs; Integration configuration; Missing API support; External systems used by the Action; API-specific invocation behavior.

> ⛔ **Do NOT use when:** Do not use just because an API supplies dropdown values -- that is Form Configuration -> Dynamic & dependent inputs.

- "We need a native ServiceNow integration for this Action."
- "The Action must call our internal provisioning API."

#### Execution agents & runners

Where the Action physically runs, and reaching it.

**Use for:** Execution agents, runners, agent configuration; Selecting where the Action runs; Connectivity between Port and the execution environment.

> ⛔ **Do NOT use when:** Security or identity issues involving the runner may primarily belong to Identity, Secrets & Security.

- "The agent cannot reach our private network."
- "Let us choose which runner executes this Action."

#### Event triggers & action-to-automation integration

Wiring an Action to events and automations.

**Use for:** Connecting an Action to an Automation; Triggering workflows or automations from an Action; Event-based invocation; Action-trigger configuration; Passing Action events into another system.

> ⛔ **Do NOT use when:** General Automation authoring unrelated to Actions is out of scope entirely -- mark is_relevant=false.

- "Trigger a downstream automation when this Action completes."
- "Fire this Action from an external event."

---

### 6. Identity, Secrets & Security

Who or what executes the Action, and how sensitive data is protected.

*Usual journey stage:* `Backend & invocation setup`  
*Most often confused with:* *Invocation & Integrations*, *Permissions & Approvals*

#### Authentication & delegated execution

Running the Action as a particular identity.

**Use for:** OAuth, JWT, authentication flows; Running on behalf of a user, impersonation; Delegated authorization; Passing user identity to a backend.

> ⛔ **Do NOT use when:** Deciding *whether* a user may run it is Permissions & Approvals.

- "Run the Action as the requesting user, not a shared token."
- "We need OAuth delegation to the downstream system."

#### Service accounts & execution identity

Which machine identity performs the work.

**Use for:** Service accounts; Selecting the identity that performs the Action; Per-Action execution identity, scoped credentials; Organization-level versus Action-level identity.

> ⛔ **Do NOT use when:** Storing the secret itself is Credentials & secrets management.

- "Each Action should use its own scoped service account."
- "One org-wide token is too broad for this Action."

#### Credentials & secrets management

Storing and retrieving passwords, tokens and secrets.

**Use for:** Passwords, tokens, secret inputs; HashiCorp Vault; Secret storage, retrieval and rotation; Credentials used by an Action.

> ⛔ **Do NOT use when:** Hiding a secret from view is Sensitive-data masking & redaction.

- "Secrets must live in Vault, not inside Port."
- "We need to rotate the Action's token without editing it."

#### Message signing & webhook security

Proving a request really came from Port.

**Use for:** Signing webhook messages, signature verification; Request integrity; Secure communication between Port and execution agents; Webhook authentication mechanisms.

> ⛔ **Do NOT use when:** Choosing the webhook target is Invocation & Integrations.

- "Sign agent messages with a service account credential."
- "We cannot verify the webhook actually came from Port."

#### Sensitive-data masking & redaction

Keeping secrets out of forms, logs and Run history.

**Use for:** Hiding secrets from the form, masking sensitive inputs; Redacting logs; Preventing sensitive outputs appearing in Run history; Protecting credentials during approval flows.

> ⛔ **Do NOT use when:** General log detail is Observability & Debugging.

- "The token appears in plain text in the run output."
- "Mask the password input so approvers cannot read it."

---

### 7. Permissions & Approvals

Who can see or run an Action, and who must approve it before it runs.

*Usual journey stage:* `Permissions & approvals`  
*Most often confused with:* *Identity, Secrets & Security*, *Discovery, Organization & Reuse*

#### RBAC & dynamic permissions

Rules deciding who is allowed to do what.

**Use for:** Role-based access, attribute-based access; User, team, group or role permissions; Dynamic permission conditions; Permission behavior based on Entity properties.

> ⛔ **Do NOT use when:** Platform-wide admin RBAC unrelated to Actions is out of scope.

- "Only the owning team should be able to run this Action."
- "Permissions should depend on the entity's environment property."

#### Action visibility & eligibility

Hiding what a user cannot run, and telling them early.

**Use for:** Hiding Actions users cannot run; Determining whether a user is eligible; Showing unavailable Actions; Rejecting a user only after they completed the entire form; Controlling visibility based on authorization.

> ⛔ **Do NOT use when:** Placement rules that are not about authorization belong to Discovery -> Conditional availability & placement.

- "I filled in the whole form and only then was told I am not permitted."
- "Hide Actions the user has no permission to run."

#### Permission authoring & testing

Building and checking permission rules without guessing.

**Use for:** Creating permission rules; Previewing permission outcomes; Testing whether a user can execute an Action; Debugging permission conditions; Improving the permission configuration UI.

> ⛔ **Do NOT use when:** Testing the Action itself is Authoring, Testing & Management.

- "Managing dynamic permissions requires specific skills and is hard to verify."
- "Let us preview whether this user would pass the rule."

#### Approval policies & thresholds

Whether approval is needed, and how much of it.

**Use for:** Whether approval is required, conditional approval, automatic approval; Production versus non-production approval; Number of required approvals, "two out of five approvers"; Risk-based approval, guardrails for sensitive Actions.

> ⛔ **Do NOT use when:** Who may start the Action at all is Action visibility & eligibility.

- "Production deploys need two approvals; staging needs none."
- "Require approval only above a cost threshold."

#### Approver routing & identity

Finding and reaching the right approver.

**Use for:** Selecting the correct approver, dynamic approver selection; Routing to a team, manager, owner or Entity relation; Finding the responsible approver; Escalation to another approver.

> ⛔ **Do NOT use when:** The notification itself is Approval notifications.

- "Route approval to the entity's owning team automatically."
- "If no approver responds, escalate to their manager."

#### Approver experience & request editing

What the approver sees and can change before deciding.

**Use for:** Approval UI, information shown to the approver; Approvers editing request inputs; Comments during approval; Approver decision experience; Viewing relevant context before approving.

> ⛔ **Do NOT use when:** Recording what happened after the fact is Approval audit & context.

- "Approvers cannot see which values they are approving."
- "Let the approver correct a typo instead of rejecting."

#### Approval notifications

Telling someone that their approval is needed.

**Use for:** Slack, email, Teams or other notifications requesting approval; Missing approval request notification; Approval reminders; Notification routing to approvers.

> ⛔ **Do NOT use when:** Success or failure notifications AFTER execution belong to Observability & Debugging -> Execution notifications & alerting.

- "The approver never received the approval request."
- "Send approval requests to Slack, not only email."

#### Approval audit & context

The record of who approved what, and why.

**Use for:** Who approved and when; Approval decision history; Reason for approval or rejection; Context displayed in the approval record; Auditability of approval decisions.

> ⛔ **Do NOT use when:** General Run history is Observability & Debugging.

- "We cannot tell afterwards who approved this deployment."
- "Capture the rejection reason in the run record."

---

### 8. Orchestration

Actions containing several connected execution steps, decisions or systems.

*Usual journey stage:* `Backend & invocation setup`  
*Most often confused with:* *Form Configuration*, *Invocation & Integrations*, *Execution Lifecycle*

#### Multi-step workflows

One Action performing several backend operations in order.

**Use for:** Several execution steps; Ordered workflow stages, sequential operations; One Action containing multiple backend tasks.

> ⛔ **Do NOT use when:** IMPORTANT: several form PAGES are Form Configuration. Several execution STEPS are Orchestration.

- "Provision, then configure, then register -- as one Action."
- "Chain several backend calls in a defined order."

#### Shared context & output passing

Using the result of one step in the next.

**Use for:** Passing output from one step to another; Shared variables and shared context; Reusing intermediate results; Referencing previous step outputs.

> ⛔ **Do NOT use when:** Passing launch context into the Action is Context, Targeting & Pre-fill.

- "Step two needs the resource ID that step one created."
- "Reference the previous step's output in the payload."

#### Branching & conditional paths

Different execution routes depending on conditions.

**Use for:** If/else paths, conditional branches; Different execution paths based on inputs or previous results; Parallel paths.

> ⛔ **Do NOT use when:** Conditional form behaviour is Form Configuration or Validation & Rules.

- "If the environment is prod, take the approval path."
- "Run these two backend steps in parallel."

#### Intermediate approvals

Pausing mid-workflow for a human decision.

**Use for:** Approval between execution steps; Pause for approval in the middle of a workflow; Approval before a specific destructive step.

> ⛔ **Do NOT use when:** Approval before the Action starts at all is Permissions & Approvals.

- "Pause before the destructive step and ask for sign-off."
- "Approve between provisioning and deployment."

#### Step-level error handling & recovery

What happens when one step of many fails.

**Use for:** Retrying one workflow step; Catch or finally behavior; Recovery after a partial failure; Rollback or compensation; Continuing after a non-critical step failure.

> ⛔ **Do NOT use when:** Retrying the whole Run is Execution Lifecycle.

- "If step three fails, roll back what step two created."
- "We need a catch-all branch for workflow failures."

#### Multi-backend & multi-system sequencing

Coordinating several different systems in one Action.

**Use for:** Several backends in one Action; Coordinating multiple systems; Routing different steps to different execution mechanisms; Sequential operations across multiple integrations.

> ⛔ **Do NOT use when:** Choosing a single backend is Invocation & Integrations.

- "This Action must hit GitHub, then Jira, then our API."
- "Route each step to a different backend."

---

### 9. Execution Lifecycle

What users can do to a Run, and how the Run behaves over its life.

*Usual journey stage:* `Execution, monitoring & run control`  
*Most often confused with:* *Observability & Debugging*, *Orchestration*

#### Retry, rerun & duplicate execution

Running it again after a failure or to repeat work.

**Use for:** Retry after failure, rerun with the same inputs; Duplicate a previous Run; Start another similar Run; Retry while preserving execution context.

> ⛔ **Do NOT use when:** Explaining *why* it failed is Observability & Debugging.

- "Let me retry the failed Run without refilling the form."
- "Duplicate this Run with the same inputs."

#### Cancel, stop & resume

Interrupting or continuing a Run in progress.

**Use for:** Cancel, stop, pause, resume, abort; Continue an interrupted Run.

> ⛔ **Do NOT use when:** Preventing a Run from starting is Permissions & Approvals.

- "Add a cancel button to a running Action."
- "I triggered it by mistake and cannot stop it."

#### Timeouts

How long a Run may take before it is cut off.

**Use for:** Run timeout configuration; Long-running Actions, timeout limits and behavior; Extending or customizing timeout duration.

> ⛔ **Do NOT use when:** Slow performance at scale is a Performance problem type, not necessarily this subcategory.

- "Our Action needs a 30-minute timeout, not 10."
- "Make the timeout configurable per Action."

#### Concurrency, rate limits & duplicate prevention

Stopping the same work from running twice or too often.

**Use for:** Preventing multiple Runs at the same time; Concurrency control, rate limiting; Duplicate request prevention, locks, queuing.

> ⛔ **Do NOT use when:** Bulk execution across entities is Discovery -> Bulk actions.

- "Two people triggered the same deploy simultaneously."
- "Queue Runs instead of running them all at once."

#### Reliability & transient-failure handling

Coping with flaky backends and temporary outages.

**Use for:** Intermittent failures, automatic retry; Temporary backend outages, network instability; Resilience behavior, backoff.

> ⛔ **Do NOT use when:** A consistent, reproducible failure is a Bug / defect.

- "Transient 502s fail the Run instead of retrying."
- "Add exponential backoff for backend errors."

#### Completion & result-state control

Deciding and correcting when a Run counts as done.

**Use for:** Marking a Run completed or failed; Custom completion state; Overriding or correcting Run outcome; Determining when a long-running Action is considered complete.

> ⛔ **Do NOT use when:** Displaying the status is Observability & Debugging -> Run status & progress.

- "Let us mark this Run as successful manually."
- "The Run never reaches a terminal state."

---

### 10. Observability & Debugging

Helping users understand what happened during or after a Run.

*Usual journey stage:* `Execution, monitoring & run control`  
*Most often confused with:* *Execution Lifecycle*, *Validation & Rules*, *Permissions & Approvals*

#### Run status & progress

Seeing where a Run currently is.

**Use for:** Current Run state, progress indicators; Step progress, pending or running state; Live execution status.

> ⛔ **Do NOT use when:** Changing the state is Execution Lifecycle -> Completion & result-state control.

- "There is no indication the job is queued rather than stuck."
- "Show step-by-step progress while it runs."

#### Logs & log streaming

Reading the detailed output of a Run.

**Use for:** Viewing logs, streaming logs; More detailed runtime output, step-level logs; Log retention.

> ⛔ **Do NOT use when:** Hiding secrets in logs is Identity, Secrets & Security.

- "We need real-time logs while the Action runs."
- "Attach the backend logs to the Run page."

#### Error messages & backend responses

Explaining clearly why a Run failed.

**Use for:** Vague runtime errors, truncated errors; Missing HTTP response or backend response body; Diagnostic context; Explaining why the Run failed.

> ⛔ **Do NOT use when:** Use only AFTER the Action started. Pre-submission errors belong to Validation & Rules -> Validation messages.

- "The Run failed and the page does not say why."
- "We never see the backend's HTTP response body."

#### Run history, audit & filtering

Finding past Runs and who triggered them.

**Use for:** Run history, audit trail; Filtering and searching Runs; Who triggered the Action and when; Historical execution records.

> ⛔ **Do NOT use when:** General platform audit logs not specific to Action Runs are out of scope -- mark is_relevant=false.

- "We cannot filter Runs by who triggered them."
- "Run history only keeps the last few days."

#### Run-history APIs & export

Getting Run data out programmatically.

**Use for:** API access to Run history, pagination; Exporting Run data; Programmatic Run querying; Missing API filters for Action Runs.

> ⛔ **Do NOT use when:** Invoking the Action via API is Invocation & Integrations.

- "The Runs API has no filter for action identifier."
- "We need to export Run history for analysis."

#### Execution notifications & alerting

Telling people the Run succeeded or failed.

**Use for:** Success, failure and completion notifications; Slack, email, Teams, Kafka or other runtime alerts; Alerts for long-running or failed Actions.

> ⛔ **Do NOT use when:** Approval REQUEST notifications belong to Permissions & Approvals -> Approval notifications.

- "Nobody was told the overnight Run failed."
- "Notify the requester in Slack when it completes."

#### Run traceability & related entities

Connecting a Run to what it actually changed.

**Use for:** Linking a Run to the affected Entity; Showing which resource changed; Tracing a Run back to its Action and requester; Connecting Runs to related objects; End-to-end execution traceability.

> ⛔ **Do NOT use when:** Approval provenance is Permissions & Approvals -> Approval audit & context.

- "We cannot tell which entity this Run modified."
- "Link the Run back to the service it deployed."

---

### 11. Authoring, Testing & Management

Helping builders safely create, test, edit, publish and maintain Actions.

*Usual journey stage:* `Testing, editing & publishing`  
*Most often confused with:* *Execution Lifecycle*, *Validation & Rules*

#### Preview & dry run

Trying an Action without real consequences.

**Use for:** Previewing an Action, dry run; Testing without real side effects; Viewing the expected payload or outcome; Validation before publishing.

> ⛔ **Do NOT use when:** A real user's submitted Run is Execution Lifecycle or Observability & Debugging.

- "Let us dry-run the Action to check it before release."
- "Show the payload that would be sent, without sending it."

#### Playground, examples & in-product help

Learning how to build an Action while building it.

**Use for:** Interactive examples, playground, sample configurations; In-product guidance; Documentation shown during Action creation; Builder onboarding.

> ⛔ **Do NOT use when:** Missing end-user help text on a field is Form Configuration -> Labels, descriptions & display controls.

- "Show a working example next to the JQ editor."
- "New builders have nowhere to experiment safely."

#### Editing & unsaved-change safety

Changing an existing Action without losing work.

**Use for:** Editing existing Actions; Unsaved-change warnings, preventing accidental loss; Edit-form usability; Duplicating an Action for editing.

> ⛔ **Do NOT use when:** Version history is Versioning, change detection & rollback.

- "I lost my edits because nothing warned me."
- "It asks about unsaved changes even when nothing changed."

#### Drafts, publishing & disablement

Controlling whether an Action is live.

**Use for:** Saving a draft, publishing, unpublishing; Disabling an Action; Returning to unfinished configuration; Separating draft and live states.

> ⛔ **Do NOT use when:** Hiding it from certain users is Permissions & Approvals.

- "Let us save a half-built Action as a draft."
- "Temporarily disable an Action without deleting it."

#### Versioning, change detection & rollback

Tracking and undoing changes to an Action definition.

**Use for:** Version history, comparing versions; Detecting configuration changes; Rollback, restoring an earlier version; Audit of Action-definition changes.

> ⛔ **Do NOT use when:** Run-level history is Observability & Debugging.

- "We cannot see who changed this Action or roll it back."
- "Compare this Action's config against last week's."

#### API & IaC configuration management

Managing Action definitions as code.

**Use for:** Managing Action definitions through API; Terraform, Pulumi, Infrastructure as Code; Exporting or importing Action configuration; Programmatic configuration management.

> ⛔ **Do NOT use when:** Invoking the Action programmatically is Invocation & Integrations.

- "Manage all our Actions through Terraform."
- "Export an Action definition and import it elsewhere."

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
| **Permissions & Approvals — permissions side**<br>"Who may run the Action?" | **Permissions & Approvals — approvals side**<br>"Who must approve the Action?" |
| **Execution Lifecycle**<br>"Let me retry the failed Run." | **Observability & Debugging**<br>"Explain why the Run failed." |
| **Permissions & Approvals → Approval notifications**<br>"The approver did not receive the request." | **Observability & Debugging → Execution notifications & alerting**<br>"The requester did not receive a failure alert." |

## Worked examples

**"I launched the Action from a Service page, but I still have to select the Service manually."**

- Category: `Context, Targeting & Pre-fill`
- Subcategory: `Pre-fill & context-specific defaults`
- Problem type: `Usability friction`
- Journey stage: `Contextual entry, targeting & pre-fill`
- *Why:* The problem is not the type of input. Port already knows the relevant Service and should fill it in automatically.

**"The available regions should change after I select a cloud provider."**

- Category: `Form Configuration`
- Subcategory: `Dynamic & dependent inputs`
- Problem type: `Feature gap`
- Journey stage: `Form & input configuration`
- *Why:* The field's options must react to another selection. Nothing is being checked for validity yet, so this is not Validation.

**"The user can run the Action, but a manager must approve production deployments."**

- Category: `Permissions & Approvals`
- Subcategory: `Approval policies & thresholds`
- Problem type: `Feature gap`
- Journey stage: `Permissions & approvals`
- *Why:* The issue is not whether the user may start the Action. It is the approval required before it executes.

**"The Action started and failed, but the run page does not explain why."**

- Category: `Observability & Debugging`
- Subcategory: `Error messages & backend responses`
- Problem type: `Poor error message`
- Journey stage: `Execution, monitoring & run control`
- *Why:* The failure happened after submission, so it belongs to execution rather than form validation.

**"Divide this long form into three screens."**

- Category: `Form Configuration`
- Subcategory: `Form layout, sections & multi-page forms`
- Problem type: `Usability friction`
- Journey stage: `Form & input configuration`
- *Why:* Several visual pages are a form-layout concern. Only several BACKEND operations would be Orchestration.

**"The approver never received the Slack request to approve."**

- Category: `Permissions & Approvals`
- Subcategory: `Approval notifications`
- Problem type: `Bug / defect`
- Journey stage: `Permissions & approvals`
- *Why:* An approval-request notification blocks the user at the approval stage, not at execution -- unlike a success or failure alert.

**"Secrets must be stored in HashiCorp Vault, not inside Port."**

- Category: `Identity, Secrets & Security`
- Subcategory: `Credentials & secrets management`
- Problem type: `Security or privacy concern`
- Journey stage: `Backend & invocation setup`
- *Why:* Storing and retrieving the credential is a secrets concern, even though the credential is used during invocation.

**"Let me retry the failed Run without filling in the form again."**

- Category: `Execution Lifecycle`
- Subcategory: `Retry, rerun & duplicate execution`
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

