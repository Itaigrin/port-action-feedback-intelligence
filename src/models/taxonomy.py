"""Centralized taxonomy for Action Configuration feedback classification.

Single source of truth. The classifier, the Pydantic schema, the dashboard,
the guide tab and the tests all import from here -- nothing redefines a
category, subcategory, stage, problem type or status anywhere else.

FOUR INDEPENDENT DIMENSIONS
---------------------------
  TAXONOMY CATEGORY   (11)  -- what broad product area does this concern?
  TAXONOMY SUBCATEGORY(63)  -- what specific part of that area needs attention?
  PROBLEM TYPE        (14)  -- what kind of problem is this?
  JOURNEY STAGE       (8)   -- where in the Action experience does it happen?

They are deliberately independent. A dynamic-permission failure sits in the
Permissions & Approvals *category* while its *problem type* is "Poor error
message" -- encoding the problem type into the category name would make both
unusable for aggregation.

Severity, persona, lifecycle status and review state are further independent
dimensions and are never folded into a category name either.

ORDERING IS LOAD-BEARING
------------------------
TAXONOMY insertion order defines CATEGORY_NAMES; JOURNEY_STAGES insertion
order is the chronological lifecycle and drives every chart, filter and guide
section. Reordering either dict silently reorders the product story.
"""

from __future__ import annotations

# Bumping these invalidates the classification cache, which is what forces a
# genuine reclassification rather than a label rename.
TAXONOMY_VERSION = "v2.0"
SCHEMA_VERSION = "v2.0"


# ===========================================================================
# TAXONOMY: 11 categories -> 63 subcategories
# ===========================================================================
# Per category:  plain / default_stage / confusable / subcategories
# Per subcategory: plain / use_for[] / avoid / examples[]
TAXONOMY: dict[str, dict] = {
    "Discovery, Organization & Reuse": {
        "plain": "How users find, organize, display and reuse Actions.",
        "default_stage": "Action discovery & organization",
        "confusable": ["Permissions & Approvals", "Context, Targeting & Pre-fill"],
        "subcategories": {
            "Action discovery, grouping & ordering": {
                "plain": "Finding the right Action in a crowded catalog.",
                "use_for": [
                    "Searching for an Action",
                    "Categories, subcategories, folders, tags",
                    "Sorting and ordering",
                    "Unclear Action names",
                    "Too many Actions in one catalog",
                    "Organizing Actions in menus or catalogs",
                ],
                "avoid": "The Action is hidden because the user lacks permission "
                         "-- that is Permissions & Approvals.",
                "examples": [
                    "\"There are too many Actions on the page and no way to group them.\"",
                    "\"We cannot tell which Action deploys a service from the name alone.\"",
                ],
            },
            "Conditional availability & placement": {
                "plain": "Controlling where an Action appears, for non-authorization reasons.",
                "use_for": [
                    "Showing an Action only on a specific page or surface",
                    "Showing an Action only for a specific Blueprint or Entity type",
                    "Placement rules that are not authorization rules",
                ],
                "avoid": "Hidden because of permissions -> Permissions & Approvals. "
                         "Retaining the launch context -> Context, Targeting & Pre-fill.",
                "examples": [
                    "\"This Action should only appear on Service pages, not everywhere.\"",
                    "\"Show the deploy Action only for Blueprints that have a repo.\"",
                ],
            },
            "Bulk actions": {
                "plain": "Running one Action against many Entities at once.",
                "use_for": [
                    "Running one Action against several Entities",
                    "Selecting multiple targets",
                    "Batch execution and bulk configuration operations",
                ],
                "avoid": "Several backend steps inside one Action -- that is Orchestration.",
                "examples": [
                    "\"Let me run this Action on all 40 services at once.\"",
                    "\"Select multiple entities from the table and trigger one Action.\"",
                ],
            },
            "Reusability & templates": {
                "plain": "Reusing an Action definition instead of rebuilding it each time.",
                "use_for": [
                    "Reusing an Action definition, templates, shared configurations",
                    "Reusing an Action across Blueprints or teams",
                    "Avoiding repeated manual Action setup",
                    "Cloning standardized Action configurations",
                ],
                "avoid": "If the reusable object is specifically a permission policy, the "
                         "primary category may be Permissions & Approvals with this as secondary.",
                "examples": [
                    "\"We copy the same Action definition into six Blueprints by hand.\"",
                    "\"Give us Action templates so teams start from a standard config.\"",
                ],
            },
        },
    },

    "Context, Targeting & Pre-fill": {
        "plain": "Using what Port already knows so the Action opens in the right "
                 "context and stops asking the user to repeat itself.",
        "default_stage": "Contextual entry, targeting & pre-fill",
        "confusable": ["Form Configuration", "Discovery, Organization & Reuse"],
        "subcategories": {
            "Contextual entry & deep links": {
                "plain": "Opening an Action from a specific place, with that context intact.",
                "use_for": [
                    "Direct links to an Action",
                    "Links that carry Action context",
                    "Opening an Action from a specific page",
                    "Preserving context through a URL",
                    "Deep-linking to a form with known values",
                ],
                "avoid": "A fixed default configured for everyone is not contextual "
                         "-- that is Form Configuration.",
                "examples": [
                    "\"Send a link that opens this Action already filled in for this service.\"",
                    "\"We want a URL that deep-links straight into the request form.\"",
                ],
            },
            "Entity and resource targeting": {
                "plain": "Deciding which Entity or resource the Action applies to.",
                "use_for": [
                    "Selecting which Entity or resource the Action applies to",
                    "Automatically determining the target",
                    "Target Blueprint, Service, Namespace, Environment or Resource",
                    "Avoiding ambiguous Action targets",
                ],
                "avoid": "Adding a new selector field is Form Configuration.",
                "examples": [
                    "\"The Action should know it applies to the namespace I came from.\"",
                    "\"It is ambiguous which resource this Action will actually change.\"",
                ],
            },
            "Pre-fill & context-specific defaults": {
                "plain": "Filling in values Port can already infer from where the user was.",
                "use_for": [
                    "Automatically filling known values",
                    "Values derived from the current Entity",
                    "Values derived from the originating page",
                    "Context-specific defaults",
                    "Avoiding repeated manual selection",
                ],
                "avoid": "A fixed default configured for every user may belong to "
                         "Form Configuration -> Defaults & computed fields.",
                "examples": [
                    "\"I opened the Action from this Service page, so the Service should already be selected.\"",
                    "\"Stop asking me for the environment when the page already knows it.\"",
                ],
            },
            "Embedded & alternative launch surfaces": {
                "plain": "Launching the Action from somewhere other than the Self-Service page.",
                "use_for": [
                    "Opening the Action in a modal",
                    "Opening the Action inside an Entity page",
                    "Launching from a widget",
                    "Launching from Slack or another surface",
                    "Avoiding navigation to the general Self-Service page",
                ],
                "avoid": "Changing which users can see the Action is Permissions & Approvals.",
                "examples": [
                    "\"Let us trigger this Action straight from Slack.\"",
                    "\"Open the Action in a modal instead of navigating away.\"",
                ],
            },
            "Current-user and context propagation": {
                "plain": "Passing who the requester is, and their org context, into the Action.",
                "use_for": [
                    "Passing the current user",
                    "Passing team, organization, Entity, Blueprint, account or environment context",
                    "Using requester identity as an input",
                    "Propagating context into the Action or backend invocation",
                ],
                "avoid": "Executing *as* that user, or authenticating as them, is "
                         "Identity, Secrets & Security.",
                "examples": [
                    "\"The backend needs to know which team the requester belongs to.\"",
                    "\"Pass the current user's email into the payload automatically.\"",
                ],
            },
        },
    },

    "Form Configuration": {
        "plain": "The visible form, the fields it contains, and how users complete it.",
        "default_stage": "Form & input configuration",
        "confusable": ["Validation & Rules", "Context, Targeting & Pre-fill", "Orchestration"],
        "subcategories": {
            "Input types & controls": {
                "plain": "Which kinds of form field exist at all.",
                "use_for": [
                    "Text, number, date, file upload, dropdown, multi-select",
                    "Maps, tables, long text, boolean controls",
                    "Any missing or limited form control",
                ],
                "avoid": "A field that changes because of another field is "
                         "Dynamic & dependent inputs.",
                "examples": [
                    "\"We need a file upload field to attach a config.\"",
                    "\"There is no map or key-value input type.\"",
                ],
            },
            "Structured & repeatable inputs": {
                "plain": "Repeating a group of fields, or entering a list of objects.",
                "use_for": [
                    "Arrays of objects",
                    "Repeatable sections, adding or removing rows",
                    "Structured lists and nested input groups",
                    "Repeating the same group of fields multiple times",
                ],
                "avoid": "Several backend steps -> Orchestration. Several form pages "
                         "-> Form layout, sections & multi-page forms.",
                "examples": [
                    "\"Let users add several environment-variable rows.\"",
                    "\"We need an array of objects, not one flat text field.\"",
                ],
            },
            "Dynamic & dependent inputs": {
                "plain": "Fields that change by themselves based on other fields or data.",
                "use_for": [
                    "Dropdown values changing based on another field",
                    "One field depending on another",
                    "Options loaded from an API or dataset",
                    "Conditional field visibility",
                    "Dynamically enabled, disabled or read-only fields",
                    "Inputs that adapt while the user fills in the form",
                ],
                "avoid": "If the issue is only whether the entered value is acceptable, "
                         "that is Validation & Rules.",
                "examples": [
                    "\"The region options should change after I pick a cloud provider.\"",
                    "\"Show the risk field only when environment is Production.\"",
                ],
            },
            "Defaults & computed fields": {
                "plain": "Values the form fills in or calculates on its own.",
                "use_for": [
                    "General default values",
                    "Computed fields, formula-derived inputs",
                    "Automatically calculated values",
                    "Values derived from other form fields",
                ],
                "avoid": "If the value comes from the page or Entity the Action was "
                         "opened from, use Context, Targeting & Pre-fill.",
                "examples": [
                    "\"Default the replica count to 3 for everyone.\"",
                    "\"Compute the resource name from the two fields above.\"",
                ],
            },
            "Form layout, sections & multi-page forms": {
                "plain": "How the form is arranged and broken up visually.",
                "use_for": [
                    "Field ordering, grouping, form sections, collapsible sections",
                    "Reducing form complexity",
                    "Splitting a long form into several visual pages",
                    "Wizard-like form navigation",
                    "Filters placed before large selectors",
                ],
                "avoid": "IMPORTANT: several visual PAGES belong here; several backend "
                         "OPERATIONS in sequence belong to Orchestration.",
                "examples": [
                    "\"Split this 25-field form into three steps.\"",
                    "\"Group the network settings into a collapsible section.\"",
                ],
            },
            "Labels, descriptions & display controls": {
                "plain": "The wording and presentation around each field.",
                "use_for": [
                    "Field labels, descriptions, placeholder text, help text",
                    "Units and display formatting",
                    "Hiding labels",
                    "Improving the clarity of a field",
                ],
                "avoid": "An unclear message about an invalid value is "
                         "Validation & Rules -> Validation messages.",
                "examples": [
                    "\"Nobody understands what this field wants; we need help text.\"",
                    "\"Show the unit (GB) next to the size field.\"",
                ],
            },
        },
    },

    "Validation & Rules": {
        "plain": "Rules deciding whether the values are acceptable and submission may proceed.",
        "default_stage": "Validation, dependencies & conditional logic",
        "confusable": ["Form Configuration", "Observability & Debugging"],
        "subcategories": {
            "Input & cross-field validation": {
                "plain": "Checking that entered values are acceptable.",
                "use_for": [
                    "Required fields, format validation",
                    "Minimum or maximum values, regex validation",
                    "Comparing two fields, date rules, cross-field checks",
                    "Preventing invalid form submission",
                ],
                "avoid": "A dropdown merely changing its options is Form Configuration "
                         "-> Dynamic & dependent inputs.",
                "examples": [
                    "\"Replica count must be at least 3 in production.\"",
                    "\"The end date must be after the start date.\"",
                ],
            },
            "Conditional logic": {
                "plain": "Business rules that decide whether submission can continue.",
                "use_for": [
                    "\"If A, then B is required\"",
                    "Rules that determine whether submission can proceed",
                    "Conditional requirements",
                    "Business rules applied before execution",
                ],
                "avoid": "A dropdown simply changing its options -> Form Configuration "
                         "-> Dynamic & dependent inputs.",
                "examples": [
                    "\"If the tier is Enterprise, the approval reason becomes required.\"",
                    "\"Block submission unless a cost centre is supplied.\"",
                ],
            },
            "Server-side & API enforcement": {
                "plain": "Making the rules hold even when the UI is not used.",
                "use_for": [
                    "Validation that works only in the UI",
                    "API, MCP, webhook or backend paths bypassing validation",
                    "Consistent enforcement across UI and non-UI invocation paths",
                    "Security-sensitive server-side validation",
                ],
                "avoid": "Missing an integration entirely is Invocation & Integrations.",
                "examples": [
                    "\"The API accepts values the form would have rejected.\"",
                    "\"MCP execution bypasses our front-end validation.\"",
                ],
            },
            "Validation messages": {
                "plain": "Explaining clearly what is wrong before submission.",
                "use_for": [
                    "Unclear pre-submission error messages",
                    "Missing explanation of which value is invalid",
                    "Messages that do not explain how to correct the form",
                    "Custom validation messages",
                ],
                "avoid": "Errors AFTER the Action started belong to "
                         "Observability & Debugging -> Error messages & backend responses.",
                "examples": [
                    "\"It says invalid but never says which format it wants.\"",
                    "\"Let us write our own message for this regex rule.\"",
                ],
            },
            "Expression and JQ rule authoring": {
                "plain": "Writing, testing and debugging the rule expressions themselves.",
                "use_for": [
                    "Writing JQ expressions",
                    "Testing rule expressions",
                    "Rule-builder usability",
                    "Debugging condition syntax",
                    "Previewing rule results and expression validation",
                ],
                "avoid": "Runtime JQ failures during execution are "
                         "Observability & Debugging.",
                "examples": [
                    "\"The jqQuery becomes unreadable with five conditions.\"",
                    "\"We need a way to preview what this expression evaluates to.\"",
                ],
            },
        },
    },

    "Invocation & Integrations": {
        "plain": "How the submitted Action connects to the system that does the work.",
        "default_stage": "Backend & invocation setup",
        "confusable": ["Identity, Secrets & Security", "Orchestration"],
        "subcategories": {
            "Backend & invocation method selection": {
                "plain": "Choosing what actually runs when the form is submitted.",
                "use_for": [
                    "Selecting a webhook, pipeline, GitHub workflow, GitLab pipeline, Kafka target",
                    "Choosing how the Action is invoked",
                    "Supporting additional invocation methods",
                    "Configuring which execution mechanism should run",
                ],
                "avoid": "Viewing or controlling a Run that already started is "
                         "Execution Lifecycle or Observability & Debugging.",
                "examples": [
                    "\"We need to trigger an Azure DevOps pipeline, not just GitHub.\"",
                    "\"Support Kafka as an invocation target.\"",
                ],
            },
            "Payload mapping & transformation": {
                "plain": "Shaping the data sent to the backend.",
                "use_for": [
                    "Building the outbound payload",
                    "Renaming submitted fields, transforming values",
                    "Mapping form inputs to backend parameters",
                    "Restructuring JSON, adding or removing payload fields",
                    "Previewing the outgoing payload",
                ],
                "avoid": "Changing what the user sees in the form is Form Configuration.",
                "examples": [
                    "\"Use JQ to reshape the payload before sending it to the workflow.\"",
                    "\"Let us preview exactly what will be POSTed.\"",
                ],
            },
            "APIs & external integrations": {
                "plain": "Connecting Actions to outside systems.",
                "use_for": [
                    "Connecting Actions to external APIs",
                    "Integration configuration",
                    "Missing API support",
                    "External systems used by the Action",
                    "API-specific invocation behavior",
                ],
                "avoid": "Do not use just because an API supplies dropdown values -- that "
                         "is Form Configuration -> Dynamic & dependent inputs.",
                "examples": [
                    "\"We need a native ServiceNow integration for this Action.\"",
                    "\"The Action must call our internal provisioning API.\"",
                ],
            },
            "Execution agents & runners": {
                "plain": "Where the Action physically runs, and reaching it.",
                "use_for": [
                    "Execution agents, runners, agent configuration",
                    "Selecting where the Action runs",
                    "Connectivity between Port and the execution environment",
                ],
                "avoid": "Security or identity issues involving the runner may primarily "
                         "belong to Identity, Secrets & Security.",
                "examples": [
                    "\"The agent cannot reach our private network.\"",
                    "\"Let us choose which runner executes this Action.\"",
                ],
            },
            "Event triggers & action-to-automation integration": {
                "plain": "Wiring an Action to events and automations.",
                "use_for": [
                    "Connecting an Action to an Automation",
                    "Triggering workflows or automations from an Action",
                    "Event-based invocation",
                    "Action-trigger configuration",
                    "Passing Action events into another system",
                ],
                "avoid": "General Automation authoring unrelated to Actions is out of "
                         "scope entirely -- mark is_relevant=false.",
                "examples": [
                    "\"Trigger a downstream automation when this Action completes.\"",
                    "\"Fire this Action from an external event.\"",
                ],
            },
        },
    },

    "Identity, Secrets & Security": {
        "plain": "Who or what executes the Action, and how sensitive data is protected.",
        "default_stage": "Backend & invocation setup",
        "confusable": ["Invocation & Integrations", "Permissions & Approvals"],
        "subcategories": {
            "Authentication & delegated execution": {
                "plain": "Running the Action as a particular identity.",
                "use_for": [
                    "OAuth, JWT, authentication flows",
                    "Running on behalf of a user, impersonation",
                    "Delegated authorization",
                    "Passing user identity to a backend",
                ],
                "avoid": "Deciding *whether* a user may run it is Permissions & Approvals.",
                "examples": [
                    "\"Run the Action as the requesting user, not a shared token.\"",
                    "\"We need OAuth delegation to the downstream system.\"",
                ],
            },
            "Service accounts & execution identity": {
                "plain": "Which machine identity performs the work.",
                "use_for": [
                    "Service accounts",
                    "Selecting the identity that performs the Action",
                    "Per-Action execution identity, scoped credentials",
                    "Organization-level versus Action-level identity",
                ],
                "avoid": "Storing the secret itself is Credentials & secrets management.",
                "examples": [
                    "\"Each Action should use its own scoped service account.\"",
                    "\"One org-wide token is too broad for this Action.\"",
                ],
            },
            "Credentials & secrets management": {
                "plain": "Storing and retrieving passwords, tokens and secrets.",
                "use_for": [
                    "Passwords, tokens, secret inputs",
                    "HashiCorp Vault",
                    "Secret storage, retrieval and rotation",
                    "Credentials used by an Action",
                ],
                "avoid": "Hiding a secret from view is Sensitive-data masking & redaction.",
                "examples": [
                    "\"Secrets must live in Vault, not inside Port.\"",
                    "\"We need to rotate the Action's token without editing it.\"",
                ],
            },
            "Message signing & webhook security": {
                "plain": "Proving a request really came from Port.",
                "use_for": [
                    "Signing webhook messages, signature verification",
                    "Request integrity",
                    "Secure communication between Port and execution agents",
                    "Webhook authentication mechanisms",
                ],
                "avoid": "Choosing the webhook target is Invocation & Integrations.",
                "examples": [
                    "\"Sign agent messages with a service account credential.\"",
                    "\"We cannot verify the webhook actually came from Port.\"",
                ],
            },
            "Sensitive-data masking & redaction": {
                "plain": "Keeping secrets out of forms, logs and Run history.",
                "use_for": [
                    "Hiding secrets from the form, masking sensitive inputs",
                    "Redacting logs",
                    "Preventing sensitive outputs appearing in Run history",
                    "Protecting credentials during approval flows",
                ],
                "avoid": "General log detail is Observability & Debugging.",
                "examples": [
                    "\"The token appears in plain text in the run output.\"",
                    "\"Mask the password input so approvers cannot read it.\"",
                ],
            },
        },
    },

    "Permissions & Approvals": {
        "plain": "Who can see or run an Action, and who must approve it before it runs.",
        "default_stage": "Permissions & approvals",
        "confusable": ["Identity, Secrets & Security", "Discovery, Organization & Reuse"],
        "subcategories": {
            "RBAC & dynamic permissions": {
                "plain": "Rules deciding who is allowed to do what.",
                "use_for": [
                    "Role-based access, attribute-based access",
                    "User, team, group or role permissions",
                    "Dynamic permission conditions",
                    "Permission behavior based on Entity properties",
                ],
                "avoid": "Platform-wide admin RBAC unrelated to Actions is out of scope.",
                "examples": [
                    "\"Only the owning team should be able to run this Action.\"",
                    "\"Permissions should depend on the entity's environment property.\"",
                ],
            },
            "Action visibility & eligibility": {
                "plain": "Hiding what a user cannot run, and telling them early.",
                "use_for": [
                    "Hiding Actions users cannot run",
                    "Determining whether a user is eligible",
                    "Showing unavailable Actions",
                    "Rejecting a user only after they completed the entire form",
                    "Controlling visibility based on authorization",
                ],
                "avoid": "Placement rules that are not about authorization belong to "
                         "Discovery -> Conditional availability & placement.",
                "examples": [
                    "\"I filled in the whole form and only then was told I am not permitted.\"",
                    "\"Hide Actions the user has no permission to run.\"",
                ],
            },
            "Permission authoring & testing": {
                "plain": "Building and checking permission rules without guessing.",
                "use_for": [
                    "Creating permission rules",
                    "Previewing permission outcomes",
                    "Testing whether a user can execute an Action",
                    "Debugging permission conditions",
                    "Improving the permission configuration UI",
                ],
                "avoid": "Testing the Action itself is Authoring, Testing & Management.",
                "examples": [
                    "\"Managing dynamic permissions requires specific skills and is hard to verify.\"",
                    "\"Let us preview whether this user would pass the rule.\"",
                ],
            },
            "Approval policies & thresholds": {
                "plain": "Whether approval is needed, and how much of it.",
                "use_for": [
                    "Whether approval is required, conditional approval, automatic approval",
                    "Production versus non-production approval",
                    "Number of required approvals, \"two out of five approvers\"",
                    "Risk-based approval, guardrails for sensitive Actions",
                ],
                "avoid": "Who may start the Action at all is Action visibility & eligibility.",
                "examples": [
                    "\"Production deploys need two approvals; staging needs none.\"",
                    "\"Require approval only above a cost threshold.\"",
                ],
            },
            "Approver routing & identity": {
                "plain": "Finding and reaching the right approver.",
                "use_for": [
                    "Selecting the correct approver, dynamic approver selection",
                    "Routing to a team, manager, owner or Entity relation",
                    "Finding the responsible approver",
                    "Escalation to another approver",
                ],
                "avoid": "The notification itself is Approval notifications.",
                "examples": [
                    "\"Route approval to the entity's owning team automatically.\"",
                    "\"If no approver responds, escalate to their manager.\"",
                ],
            },
            "Approver experience & request editing": {
                "plain": "What the approver sees and can change before deciding.",
                "use_for": [
                    "Approval UI, information shown to the approver",
                    "Approvers editing request inputs",
                    "Comments during approval",
                    "Approver decision experience",
                    "Viewing relevant context before approving",
                ],
                "avoid": "Recording what happened after the fact is Approval audit & context.",
                "examples": [
                    "\"Approvers cannot see which values they are approving.\"",
                    "\"Let the approver correct a typo instead of rejecting.\"",
                ],
            },
            "Approval notifications": {
                "plain": "Telling someone that their approval is needed.",
                "use_for": [
                    "Slack, email, Teams or other notifications requesting approval",
                    "Missing approval request notification",
                    "Approval reminders",
                    "Notification routing to approvers",
                ],
                "avoid": "Success or failure notifications AFTER execution belong to "
                         "Observability & Debugging -> Execution notifications & alerting.",
                "examples": [
                    "\"The approver never received the approval request.\"",
                    "\"Send approval requests to Slack, not only email.\"",
                ],
            },
            "Approval audit & context": {
                "plain": "The record of who approved what, and why.",
                "use_for": [
                    "Who approved and when",
                    "Approval decision history",
                    "Reason for approval or rejection",
                    "Context displayed in the approval record",
                    "Auditability of approval decisions",
                ],
                "avoid": "General Run history is Observability & Debugging.",
                "examples": [
                    "\"We cannot tell afterwards who approved this deployment.\"",
                    "\"Capture the rejection reason in the run record.\"",
                ],
            },
        },
    },

    "Orchestration": {
        "plain": "Actions containing several connected execution steps, decisions or systems.",
        "default_stage": "Backend & invocation setup",
        "confusable": ["Form Configuration", "Invocation & Integrations", "Execution Lifecycle"],
        "subcategories": {
            "Multi-step workflows": {
                "plain": "One Action performing several backend operations in order.",
                "use_for": [
                    "Several execution steps",
                    "Ordered workflow stages, sequential operations",
                    "One Action containing multiple backend tasks",
                ],
                "avoid": "IMPORTANT: several form PAGES are Form Configuration. Several "
                         "execution STEPS are Orchestration.",
                "examples": [
                    "\"Provision, then configure, then register -- as one Action.\"",
                    "\"Chain several backend calls in a defined order.\"",
                ],
            },
            "Shared context & output passing": {
                "plain": "Using the result of one step in the next.",
                "use_for": [
                    "Passing output from one step to another",
                    "Shared variables and shared context",
                    "Reusing intermediate results",
                    "Referencing previous step outputs",
                ],
                "avoid": "Passing launch context into the Action is "
                         "Context, Targeting & Pre-fill.",
                "examples": [
                    "\"Step two needs the resource ID that step one created.\"",
                    "\"Reference the previous step's output in the payload.\"",
                ],
            },
            "Branching & conditional paths": {
                "plain": "Different execution routes depending on conditions.",
                "use_for": [
                    "If/else paths, conditional branches",
                    "Different execution paths based on inputs or previous results",
                    "Parallel paths",
                ],
                "avoid": "Conditional form behaviour is Form Configuration or "
                         "Validation & Rules.",
                "examples": [
                    "\"If the environment is prod, take the approval path.\"",
                    "\"Run these two backend steps in parallel.\"",
                ],
            },
            "Intermediate approvals": {
                "plain": "Pausing mid-workflow for a human decision.",
                "use_for": [
                    "Approval between execution steps",
                    "Pause for approval in the middle of a workflow",
                    "Approval before a specific destructive step",
                ],
                "avoid": "Approval before the Action starts at all is "
                         "Permissions & Approvals.",
                "examples": [
                    "\"Pause before the destructive step and ask for sign-off.\"",
                    "\"Approve between provisioning and deployment.\"",
                ],
            },
            "Step-level error handling & recovery": {
                "plain": "What happens when one step of many fails.",
                "use_for": [
                    "Retrying one workflow step",
                    "Catch or finally behavior",
                    "Recovery after a partial failure",
                    "Rollback or compensation",
                    "Continuing after a non-critical step failure",
                ],
                "avoid": "Retrying the whole Run is Execution Lifecycle.",
                "examples": [
                    "\"If step three fails, roll back what step two created.\"",
                    "\"We need a catch-all branch for workflow failures.\"",
                ],
            },
            "Multi-backend & multi-system sequencing": {
                "plain": "Coordinating several different systems in one Action.",
                "use_for": [
                    "Several backends in one Action",
                    "Coordinating multiple systems",
                    "Routing different steps to different execution mechanisms",
                    "Sequential operations across multiple integrations",
                ],
                "avoid": "Choosing a single backend is Invocation & Integrations.",
                "examples": [
                    "\"This Action must hit GitHub, then Jira, then our API.\"",
                    "\"Route each step to a different backend.\"",
                ],
            },
        },
    },

    "Execution Lifecycle": {
        "plain": "What users can do to a Run, and how the Run behaves over its life.",
        "default_stage": "Execution, monitoring & run control",
        "confusable": ["Observability & Debugging", "Orchestration"],
        "subcategories": {
            "Retry, rerun & duplicate execution": {
                "plain": "Running it again after a failure or to repeat work.",
                "use_for": [
                    "Retry after failure, rerun with the same inputs",
                    "Duplicate a previous Run",
                    "Start another similar Run",
                    "Retry while preserving execution context",
                ],
                "avoid": "Explaining *why* it failed is Observability & Debugging.",
                "examples": [
                    "\"Let me retry the failed Run without refilling the form.\"",
                    "\"Duplicate this Run with the same inputs.\"",
                ],
            },
            "Cancel, stop & resume": {
                "plain": "Interrupting or continuing a Run in progress.",
                "use_for": [
                    "Cancel, stop, pause, resume, abort",
                    "Continue an interrupted Run",
                ],
                "avoid": "Preventing a Run from starting is Permissions & Approvals.",
                "examples": [
                    "\"Add a cancel button to a running Action.\"",
                    "\"I triggered it by mistake and cannot stop it.\"",
                ],
            },
            "Timeouts": {
                "plain": "How long a Run may take before it is cut off.",
                "use_for": [
                    "Run timeout configuration",
                    "Long-running Actions, timeout limits and behavior",
                    "Extending or customizing timeout duration",
                ],
                "avoid": "Slow performance at scale is a Performance problem type, not "
                         "necessarily this subcategory.",
                "examples": [
                    "\"Our Action needs a 30-minute timeout, not 10.\"",
                    "\"Make the timeout configurable per Action.\"",
                ],
            },
            "Concurrency, rate limits & duplicate prevention": {
                "plain": "Stopping the same work from running twice or too often.",
                "use_for": [
                    "Preventing multiple Runs at the same time",
                    "Concurrency control, rate limiting",
                    "Duplicate request prevention, locks, queuing",
                ],
                "avoid": "Bulk execution across entities is Discovery -> Bulk actions.",
                "examples": [
                    "\"Two people triggered the same deploy simultaneously.\"",
                    "\"Queue Runs instead of running them all at once.\"",
                ],
            },
            "Reliability & transient-failure handling": {
                "plain": "Coping with flaky backends and temporary outages.",
                "use_for": [
                    "Intermittent failures, automatic retry",
                    "Temporary backend outages, network instability",
                    "Resilience behavior, backoff",
                ],
                "avoid": "A consistent, reproducible failure is a Bug / defect.",
                "examples": [
                    "\"Transient 502s fail the Run instead of retrying.\"",
                    "\"Add exponential backoff for backend errors.\"",
                ],
            },
            "Completion & result-state control": {
                "plain": "Deciding and correcting when a Run counts as done.",
                "use_for": [
                    "Marking a Run completed or failed",
                    "Custom completion state",
                    "Overriding or correcting Run outcome",
                    "Determining when a long-running Action is considered complete",
                ],
                "avoid": "Displaying the status is Observability & Debugging "
                         "-> Run status & progress.",
                "examples": [
                    "\"Let us mark this Run as successful manually.\"",
                    "\"The Run never reaches a terminal state.\"",
                ],
            },
        },
    },

    "Observability & Debugging": {
        "plain": "Helping users understand what happened during or after a Run.",
        "default_stage": "Execution, monitoring & run control",
        "confusable": ["Execution Lifecycle", "Validation & Rules", "Permissions & Approvals"],
        "subcategories": {
            "Run status & progress": {
                "plain": "Seeing where a Run currently is.",
                "use_for": [
                    "Current Run state, progress indicators",
                    "Step progress, pending or running state",
                    "Live execution status",
                ],
                "avoid": "Changing the state is Execution Lifecycle "
                         "-> Completion & result-state control.",
                "examples": [
                    "\"There is no indication the job is queued rather than stuck.\"",
                    "\"Show step-by-step progress while it runs.\"",
                ],
            },
            "Logs & log streaming": {
                "plain": "Reading the detailed output of a Run.",
                "use_for": [
                    "Viewing logs, streaming logs",
                    "More detailed runtime output, step-level logs",
                    "Log retention",
                ],
                "avoid": "Hiding secrets in logs is Identity, Secrets & Security.",
                "examples": [
                    "\"We need real-time logs while the Action runs.\"",
                    "\"Attach the backend logs to the Run page.\"",
                ],
            },
            "Error messages & backend responses": {
                "plain": "Explaining clearly why a Run failed.",
                "use_for": [
                    "Vague runtime errors, truncated errors",
                    "Missing HTTP response or backend response body",
                    "Diagnostic context",
                    "Explaining why the Run failed",
                ],
                "avoid": "Use only AFTER the Action started. Pre-submission errors "
                         "belong to Validation & Rules -> Validation messages.",
                "examples": [
                    "\"The Run failed and the page does not say why.\"",
                    "\"We never see the backend's HTTP response body.\"",
                ],
            },
            "Run history, audit & filtering": {
                "plain": "Finding past Runs and who triggered them.",
                "use_for": [
                    "Run history, audit trail",
                    "Filtering and searching Runs",
                    "Who triggered the Action and when",
                    "Historical execution records",
                ],
                "avoid": "General platform audit logs not specific to Action Runs are "
                         "out of scope -- mark is_relevant=false.",
                "examples": [
                    "\"We cannot filter Runs by who triggered them.\"",
                    "\"Run history only keeps the last few days.\"",
                ],
            },
            "Run-history APIs & export": {
                "plain": "Getting Run data out programmatically.",
                "use_for": [
                    "API access to Run history, pagination",
                    "Exporting Run data",
                    "Programmatic Run querying",
                    "Missing API filters for Action Runs",
                ],
                "avoid": "Invoking the Action via API is Invocation & Integrations.",
                "examples": [
                    "\"The Runs API has no filter for action identifier.\"",
                    "\"We need to export Run history for analysis.\"",
                ],
            },
            "Execution notifications & alerting": {
                "plain": "Telling people the Run succeeded or failed.",
                "use_for": [
                    "Success, failure and completion notifications",
                    "Slack, email, Teams, Kafka or other runtime alerts",
                    "Alerts for long-running or failed Actions",
                ],
                "avoid": "Approval REQUEST notifications belong to Permissions & Approvals "
                         "-> Approval notifications.",
                "examples": [
                    "\"Nobody was told the overnight Run failed.\"",
                    "\"Notify the requester in Slack when it completes.\"",
                ],
            },
            "Run traceability & related entities": {
                "plain": "Connecting a Run to what it actually changed.",
                "use_for": [
                    "Linking a Run to the affected Entity",
                    "Showing which resource changed",
                    "Tracing a Run back to its Action and requester",
                    "Connecting Runs to related objects",
                    "End-to-end execution traceability",
                ],
                "avoid": "Approval provenance is Permissions & Approvals "
                         "-> Approval audit & context.",
                "examples": [
                    "\"We cannot tell which entity this Run modified.\"",
                    "\"Link the Run back to the service it deployed.\"",
                ],
            },
        },
    },

    "Authoring, Testing & Management": {
        "plain": "Helping builders safely create, test, edit, publish and maintain Actions.",
        "default_stage": "Testing, editing & publishing",
        "confusable": ["Execution Lifecycle", "Validation & Rules"],
        "subcategories": {
            "Preview & dry run": {
                "plain": "Trying an Action without real consequences.",
                "use_for": [
                    "Previewing an Action, dry run",
                    "Testing without real side effects",
                    "Viewing the expected payload or outcome",
                    "Validation before publishing",
                ],
                "avoid": "A real user's submitted Run is Execution Lifecycle or "
                         "Observability & Debugging.",
                "examples": [
                    "\"Let us dry-run the Action to check it before release.\"",
                    "\"Show the payload that would be sent, without sending it.\"",
                ],
            },
            "Playground, examples & in-product help": {
                "plain": "Learning how to build an Action while building it.",
                "use_for": [
                    "Interactive examples, playground, sample configurations",
                    "In-product guidance",
                    "Documentation shown during Action creation",
                    "Builder onboarding",
                ],
                "avoid": "Missing end-user help text on a field is Form Configuration "
                         "-> Labels, descriptions & display controls.",
                "examples": [
                    "\"Show a working example next to the JQ editor.\"",
                    "\"New builders have nowhere to experiment safely.\"",
                ],
            },
            "Editing & unsaved-change safety": {
                "plain": "Changing an existing Action without losing work.",
                "use_for": [
                    "Editing existing Actions",
                    "Unsaved-change warnings, preventing accidental loss",
                    "Edit-form usability",
                    "Duplicating an Action for editing",
                ],
                "avoid": "Version history is Versioning, change detection & rollback.",
                "examples": [
                    "\"I lost my edits because nothing warned me.\"",
                    "\"It asks about unsaved changes even when nothing changed.\"",
                ],
            },
            "Drafts, publishing & disablement": {
                "plain": "Controlling whether an Action is live.",
                "use_for": [
                    "Saving a draft, publishing, unpublishing",
                    "Disabling an Action",
                    "Returning to unfinished configuration",
                    "Separating draft and live states",
                ],
                "avoid": "Hiding it from certain users is Permissions & Approvals.",
                "examples": [
                    "\"Let us save a half-built Action as a draft.\"",
                    "\"Temporarily disable an Action without deleting it.\"",
                ],
            },
            "Versioning, change detection & rollback": {
                "plain": "Tracking and undoing changes to an Action definition.",
                "use_for": [
                    "Version history, comparing versions",
                    "Detecting configuration changes",
                    "Rollback, restoring an earlier version",
                    "Audit of Action-definition changes",
                ],
                "avoid": "Run-level history is Observability & Debugging.",
                "examples": [
                    "\"We cannot see who changed this Action or roll it back.\"",
                    "\"Compare this Action's config against last week's.\"",
                ],
            },
            "API & IaC configuration management": {
                "plain": "Managing Action definitions as code.",
                "use_for": [
                    "Managing Action definitions through API",
                    "Terraform, Pulumi, Infrastructure as Code",
                    "Exporting or importing Action configuration",
                    "Programmatic configuration management",
                ],
                "avoid": "Invoking the Action programmatically is "
                         "Invocation & Integrations.",
                "examples": [
                    "\"Manage all our Actions through Terraform.\"",
                    "\"Export an Action definition and import it elsewhere.\"",
                ],
            },
        },
    },
}


# ===========================================================================
# JOURNEY STAGES (8, chronological)
# ===========================================================================
JOURNEY_STAGES: dict[str, str] = {
    "Action discovery & organization":
        "The user is trying to find, understand or organize the available Actions.",
    "Contextual entry, targeting & pre-fill":
        "The Action is opened from a specific context, and the system should "
        "already know what it applies to.",
    "Form & input configuration":
        "The visible form, its controls, labels and layout are being configured "
        "or completed.",
    "Validation, dependencies & conditional logic":
        "The form reacts to input and decides whether the values are valid and "
        "ready for submission.",
    "Backend & invocation setup":
        "The Action is connected to the systems, identities, payloads, agents "
        "and workflows that perform the work.",
    "Permissions & approvals":
        "The system decides whether the user is eligible and whether approval "
        "is required.",
    "Testing, editing & publishing":
        "The Action builder tests and manages the Action definition.",
    "Execution, monitoring & run control":
        "The Action has been submitted or started, and users need to understand "
        "or control the Run.",
}

STAGE_GUIDE: dict[str, dict] = {
    "Action discovery & organization": {
        "user_goal": "Work out which Action does what they need, out of everything available.",
        "example": "\"There are dozens of Actions in one flat list and I cannot tell which one deploys my service.\"",
    },
    "Contextual entry, targeting & pre-fill": {
        "user_goal": "Start the Action already pointed at the right service, resource or environment.",
        "example": "\"I clicked the Action from a service page, but it asks me to choose the service again.\"",
    },
    "Form & input configuration": {
        "user_goal": "Fill in a form that has the right fields, clearly labelled and sensibly ordered.",
        "example": "\"There is no way to attach a file, and the fields are in a confusing order.\"",
    },
    "Validation, dependencies & conditional logic": {
        "user_goal": "Be guided to valid input, with fields that adapt to earlier choices.",
        "example": "\"It rejects my value without saying what format it expects.\"",
    },
    "Backend & invocation setup": {
        "user_goal": "Connect the Action to the pipeline, API or system that performs the task.",
        "example": "\"We need to reshape the data before it is sent to our workflow.\"",
    },
    "Permissions & approvals": {
        "user_goal": "Only run what they are entitled to, with the right approvals in place.",
        "example": "\"I filled in the whole form and only then was told I am not permitted.\"",
    },
    "Testing, editing & publishing": {
        "user_goal": "Build, test and release an Action safely, without breaking it for users.",
        "example": "\"I want to try the Action myself before anyone else can see it.\"",
    },
    "Execution, monitoring & run control": {
        "user_goal": "See the outcome, understand failures, and retry or cancel when needed.",
        "example": "\"The Run failed hours ago and nobody was notified.\"",
    },
}


# ===========================================================================
# PROBLEM TYPES (14, independent of taxonomy)
# ===========================================================================
# "General or irrelevant feedback" is deliberately NOT a problem type --
# irrelevance is expressed by is_relevant=false, so it can never dilute a
# problem-type distribution.
PROBLEM_TYPES: dict[str, str] = {
    "Bug / defect":
        "The capability exists but behaves incorrectly.",
    "Reliability issue":
        "It works inconsistently -- intermittent failures, timeouts, flakiness.",
    "Feature gap":
        "The capability does not exist at all.",
    "Configuration complexity":
        "It is possible, but requires complicated or repeated configuration.",
    "Usability friction":
        "It works, but is confusing or difficult to use.",
    "Documentation or discoverability gap":
        "The capability exists but users cannot find or understand it.",
    "Validation gap":
        "Invalid input can pass, or a required rule is missing.",
    "Poor error message":
        "The failure is real but the explanation does not help the user fix it.",
    "Observability or debugging gap":
        "Users lack the status, logs or context needed to understand what happened.",
    "Integration or API gap":
        "An API or integration capability is missing.",
    "Security or privacy concern":
        "Sensitive information, identity or authorization is exposed or unsafe.",
    "Performance or scalability limitation":
        "The problem appears at high volume, scale or load.",
    "Reusability or maintainability issue":
        "The same configuration must be repeated and is hard to maintain.",
    "Positive / completed feedback":
        "Describes a shipped or completed improvement with no current unmet pain.",
}


# ===========================================================================
# SEVERITY (1-5, independent of everything above)
# ===========================================================================
SEVERITY_SCALE: dict[int, str] = {
    5: "Blocking. No workaround exists, or the issue is a security or data risk.",
    4: "Severe. A painful workaround exists but costs real time on every use.",
    3: "Moderate. Slows people down or forces repeated manual configuration.",
    2: "Minor. Noticeable friction with an easy workaround.",
    1: "Nice to have. A polish or convenience request.",
}


# ===========================================================================
# PERSONAS, SOURCES, LIFECYCLE
# ===========================================================================
PERSONAS: dict[str, str] = {
    "Action builder":
        "Platform engineer or admin who creates and maintains Actions.",
    "Developer / end user":
        "Person who runs an Action to get something done.",
    "Approver / manager":
        "Person who reviews and approves Action requests.",
    "Platform admin":
        "Administers Port itself -- permissions, integrations, org settings.",
    "Unknown":
        "The source text does not make the persona clear.",
}

SOURCE_SYSTEMS: tuple[str, ...] = ("Slack", "Zendesk", "Gong", "Port portal")

LIFECYCLE_STATUSES: tuple[str, ...] = (
    "Open", "Planned", "In progress", "Completed", "Closed", "Unknown",
)

# Statuses representing live, unmet demand. Completed/Closed deliberately
# excluded: shipped work must never inflate open product-action ranking.
OPEN_STATUSES: frozenset[str] = frozenset({"Open", "Planned", "In progress"})

# Port portal raw status -> normalized lifecycle status.
PORTAL_STATUS_MAP: dict[str, str] = {
    "open": "Open",
    "under review": "Open",
    "exploring": "In progress",
    "planned": "Planned",
    "in progress": "In progress",
    "complete": "Completed",
    "completed": "Completed",
    "closed": "Closed",
    "resolved": "Completed",
}


# ===========================================================================
# DEFAULT CATEGORY -> JOURNEY STAGE MAPPING
# ===========================================================================
# A guideline, never a constraint. The classifier picks the stage where the
# user FIRST becomes blocked.
DEFAULT_STAGE_FOR_CATEGORY: dict[str, str] = {
    cat: meta["default_stage"] for cat, meta in TAXONOMY.items()
}


# ===========================================================================
# DISAMBIGUATION RULES
# ===========================================================================
TIE_BREAK_RULES: list[str] = [
    "DISCOVERY vs PERMISSIONS. 'I cannot find the Action' -> Discovery, "
    "Organization & Reuse. 'This user should not see the Action' -> Permissions "
    "& Approvals. Absence caused by an authorization rule is a permissions "
    "problem, not a search problem.",

    "CONTEXT vs FORM CONFIGURATION. 'Port already knows which Service I am "
    "using' -> Context, Targeting & Pre-fill. 'I need a new Service selector "
    "field, or a different field order' -> Form Configuration.",

    "DYNAMIC INPUT vs VALIDATION. If a field CHANGES because of another "
    "selection -> Form Configuration -> Dynamic & dependent inputs. If the "
    "system CHECKS whether an entered value is allowed -> Validation & Rules.",

    "MULTI-PAGE FORM vs ORCHESTRATION. One form divided into several visual "
    "pages -> Form Configuration -> Form layout, sections & multi-page forms. "
    "Several connected BACKEND operations -> Orchestration.",

    "INVOCATION vs IDENTITY AND SECURITY. 'Send the form to GitHub Actions' -> "
    "Invocation & Integrations. 'Use a scoped service account to authenticate' "
    "-> Identity, Secrets & Security.",

    "PERMISSIONS vs APPROVALS. 'Who may run the Action?' -> Permissions & "
    "Approvals -> RBAC / Action visibility. 'Who must approve it before it "
    "runs?' -> Permissions & Approvals -> Approval policies / routing. Both "
    "share the stage 'Permissions & approvals'.",

    "VALIDATION ERROR vs RUNTIME ERROR. An error BEFORE submission -> "
    "Validation & Rules -> Validation messages, stage 'Validation, dependencies "
    "& conditional logic'. A failure AFTER the Action started -> Observability "
    "& Debugging -> Error messages & backend responses, stage 'Execution, "
    "monitoring & run control'.",

    "EXECUTION LIFECYCLE vs OBSERVABILITY. 'Let me retry the failed Run' -> "
    "Execution Lifecycle. 'Explain why the Run failed' -> Observability & "
    "Debugging. Acting on the Run vs understanding the Run.",

    "APPROVAL NOTIFICATION vs EXECUTION NOTIFICATION. 'The approver did not "
    "receive the request' -> Permissions & Approvals -> Approval notifications, "
    "stage 'Permissions & approvals'. 'The requester did not receive a failure "
    "alert' -> Observability & Debugging -> Execution notifications & alerting, "
    "stage 'Execution, monitoring & run control'.",

    "CREDENTIALS vs INVOCATION CONFIGURATION. Storing, rotating or protecting a "
    "secret -> Identity, Secrets & Security. Choosing and wiring the backend "
    "that runs the Action -> Invocation & Integrations.",

    "CONTEXTUAL DEFAULT vs GENERAL DEFAULT. A value inferred from the Entity "
    "page or originating surface -> Context, Targeting & Pre-fill. A default "
    "computed from other form fields, or a fixed default for everyone -> Form "
    "Configuration -> Defaults & computed fields.",

    "PRIMARY vs SECONDARY. The PRIMARY assignment is the product area where the "
    "main change should be implemented. Add a secondary assignment only when "
    "another product area is meaningfully involved -- never merely because "
    "another technology is mentioned.",

    "OUT OF SCOPE. General Port audit logs, general catalog feedback, general "
    "Automation authoring unrelated to Actions, platform-wide admin RBAC, "
    "scorecards, dashboards and unrelated integrations are NOT Action "
    "Configuration. Set is_relevant=false with a relevance_reason instead of "
    "forcing them into a category.",
]


# ===========================================================================
# COMMONLY CONFUSED PAIRS (guide tab)
# ===========================================================================
CONFUSION_PAIRS: list[dict[str, str]] = [
    {"left": "Discovery, Organization & Reuse", "right": "Permissions & Approvals",
     "left_says": "\"I cannot find the Action.\"",
     "right_says": "\"This user should not see the Action.\""},
    {"left": "Context, Targeting & Pre-fill", "right": "Form Configuration",
     "left_says": "\"Port already knows which Service I am using.\"",
     "right_says": "\"I need a new Service selector field.\""},
    {"left": "Form Configuration → Dynamic & dependent inputs", "right": "Validation & Rules",
     "left_says": "\"The region options should change when I choose a cloud provider.\"",
     "right_says": "\"The selected region is not allowed for this environment.\""},
    {"left": "Form Configuration", "right": "Orchestration",
     "left_says": "\"Divide the form into three screens.\"",
     "right_says": "\"Run three backend operations in sequence.\""},
    {"left": "Invocation & Integrations", "right": "Identity, Secrets & Security",
     "left_says": "\"Send the form to GitHub Actions.\"",
     "right_says": "\"Use a scoped service account to authenticate.\""},
    {"left": "Permissions & Approvals — permissions side",
     "right": "Permissions & Approvals — approvals side",
     "left_says": "\"Who may run the Action?\"",
     "right_says": "\"Who must approve the Action?\""},
    {"left": "Execution Lifecycle", "right": "Observability & Debugging",
     "left_says": "\"Let me retry the failed Run.\"",
     "right_says": "\"Explain why the Run failed.\""},
    {"left": "Permissions & Approvals → Approval notifications",
     "right": "Observability & Debugging → Execution notifications & alerting",
     "left_says": "\"The approver did not receive the request.\"",
     "right_says": "\"The requester did not receive a failure alert.\""},
]


# ===========================================================================
# WORKED EXAMPLES (guide tab)
# ===========================================================================
WORKED_EXAMPLES: list[dict] = [
    {
        "feedback": "I launched the Action from a Service page, but I still have to "
                    "select the Service manually.",
        "category": "Context, Targeting & Pre-fill",
        "subcategory": "Pre-fill & context-specific defaults",
        "problem_type": "Usability friction",
        "stage": "Contextual entry, targeting & pre-fill",
        "why": "The problem is not the type of input. Port already knows the relevant "
               "Service and should fill it in automatically.",
    },
    {
        "feedback": "The available regions should change after I select a cloud provider.",
        "category": "Form Configuration",
        "subcategory": "Dynamic & dependent inputs",
        "problem_type": "Feature gap",
        "stage": "Form & input configuration",
        "why": "The field's options must react to another selection. Nothing is being "
               "checked for validity yet, so this is not Validation.",
    },
    {
        "feedback": "The user can run the Action, but a manager must approve production "
                    "deployments.",
        "category": "Permissions & Approvals",
        "subcategory": "Approval policies & thresholds",
        "problem_type": "Feature gap",
        "stage": "Permissions & approvals",
        "why": "The issue is not whether the user may start the Action. It is the "
               "approval required before it executes.",
    },
    {
        "feedback": "The Action started and failed, but the run page does not explain why.",
        "category": "Observability & Debugging",
        "subcategory": "Error messages & backend responses",
        "problem_type": "Poor error message",
        "stage": "Execution, monitoring & run control",
        "why": "The failure happened after submission, so it belongs to execution "
               "rather than form validation.",
    },
    {
        "feedback": "Divide this long form into three screens.",
        "category": "Form Configuration",
        "subcategory": "Form layout, sections & multi-page forms",
        "problem_type": "Usability friction",
        "stage": "Form & input configuration",
        "why": "Several visual pages are a form-layout concern. Only several BACKEND "
               "operations would be Orchestration.",
    },
    {
        "feedback": "The approver never received the Slack request to approve.",
        "category": "Permissions & Approvals",
        "subcategory": "Approval notifications",
        "problem_type": "Bug / defect",
        "stage": "Permissions & approvals",
        "why": "An approval-request notification blocks the user at the approval stage, "
               "not at execution -- unlike a success or failure alert.",
    },
    {
        "feedback": "Secrets must be stored in HashiCorp Vault, not inside Port.",
        "category": "Identity, Secrets & Security",
        "subcategory": "Credentials & secrets management",
        "problem_type": "Security or privacy concern",
        "stage": "Backend & invocation setup",
        "why": "Storing and retrieving the credential is a secrets concern, even though "
               "the credential is used during invocation.",
    },
    {
        "feedback": "Let me retry the failed Run without filling in the form again.",
        "category": "Execution Lifecycle",
        "subcategory": "Retry, rerun & duplicate execution",
        "problem_type": "Feature gap",
        "stage": "Execution, monitoring & run control",
        "why": "Acting on the Run is Execution Lifecycle. Explaining why it failed "
               "would instead be Observability & Debugging.",
    },
]


# ===========================================================================
# GLOSSARY (guide tab)
# ===========================================================================
GLOSSARY: dict[str, str] = {
    "Action": "A form that lets someone request or trigger a task, such as deploying "
              "a service or requesting access.",
    "Entity": "An item stored in Port, such as a service, application, environment "
              "or resource.",
    "Blueprint": "The template defining what a type of Entity looks like in Port.",
    "Taxonomy Category": "The broad product area a piece of feedback belongs to. "
                         "There are 11.",
    "Taxonomy Subcategory": "The specific part of that product area needing attention.",
    "Problem Type": "What kind of problem it is -- a bug, a missing feature, a "
                    "confusing experience, and so on.",
    "Journey Stage": "Where in the Action experience the user hit the problem.",
    "Pre-fill": "Automatically placing known information into a field so the user "
                "does not have to enter it again.",
    "Input": "A field in a form where the user enters or selects information.",
    "Validation": "A check confirming whether the information entered is acceptable.",
    "Payload": "The package of information sent from the form to the system that "
               "performs the task.",
    "Webhook": "A way for one system to automatically send information to another "
               "when something happens.",
    "API": "A structured way for software systems to communicate with each other.",
    "Credential": "Information used to prove that a system or user is allowed to connect.",
    "Secret": "Sensitive information, such as a password or access token, that must "
              "be stored securely.",
    "Permission": "A rule determining who is allowed to see or do something.",
    "Approval": "A decision another person must make before an Action may continue.",
    "Execution": "The period when the requested task is actually being performed.",
    "Run": "One specific attempt to execute an Action.",
    "Log": "A record of events and messages produced while an Action is running.",
    "Retry": "Trying to run a failed Action again.",
    "Orchestration": "Coordinating several connected tasks or systems as one process.",
    "Draft": "A saved version of an Action that is not yet published.",
    "Lifecycle Status": "Whether the request is Open, Planned, In progress, Completed "
                        "or Closed.",
    "Product Action": "A recommended product change, grouped from all the feedback "
                      "records asking for the same thing.",
    "Evidence quote": "A short passage copied word-for-word from the original "
                      "feedback, verified by code.",
    "Persona": "The kind of user the feedback is coming from.",
    "Source system": "Where the feedback came from -- Slack, Zendesk, Gong or the "
                     "Port portal.",
}


# ===========================================================================
# DERIVED CONSTANTS -- generated, never hand-maintained
# ===========================================================================
CATEGORY_NAMES: tuple[str, ...] = tuple(TAXONOMY)

SUBCATEGORY_NAMES_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    cat: tuple(meta["subcategories"]) for cat, meta in TAXONOMY.items()
}

ALL_SUBCATEGORY_NAMES: tuple[str, ...] = tuple(
    sub for subs in SUBCATEGORY_NAMES_BY_CATEGORY.values() for sub in subs
)

# Reverse lookup. Subcategory names are unique across the taxonomy; the test
# suite enforces that so this mapping can never silently lose an entry.
CATEGORY_FOR_SUBCATEGORY: dict[str, str] = {
    sub: cat
    for cat, subs in SUBCATEGORY_NAMES_BY_CATEGORY.items()
    for sub in subs
}

STAGE_NAMES: tuple[str, ...] = tuple(JOURNEY_STAGES)
PROBLEM_TYPE_NAMES: tuple[str, ...] = tuple(PROBLEM_TYPES)
PERSONA_NAMES: tuple[str, ...] = tuple(PERSONAS)

# The guide tab calls a Category+Subcategory pair a "Theme" for beginners.
TAXONOMY_GUIDE: dict[str, dict] = TAXONOMY


def subcategories_for(category: str | None) -> tuple[str, ...]:
    """Subcategories of one category, or every subcategory if None."""
    if not category:
        return ALL_SUBCATEGORY_NAMES
    return SUBCATEGORY_NAMES_BY_CATEGORY.get(category, ())


def is_valid_pair(category: str, subcategory: str) -> bool:
    """True if the subcategory really belongs to that category."""
    return subcategory in SUBCATEGORY_NAMES_BY_CATEGORY.get(category, ())


def default_stage_for(category: str) -> str | None:
    return DEFAULT_STAGE_FOR_CATEGORY.get(category)
