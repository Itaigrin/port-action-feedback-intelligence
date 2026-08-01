"""Centralized taxonomy for Action Configuration feedback classification.

Single source of truth. The classifier, the Pydantic schema, the dashboard,
the guide tab and the tests all import from here -- nothing redefines a
category, subcategory, stage, problem type or status anywhere else.

FOUR INDEPENDENT DIMENSIONS
---------------------------
  TAXONOMY CATEGORY   (11)  -- what broad product area does this concern?
  TAXONOMY SUBCATEGORY(30)  -- what specific part of that area needs attention?
  PROBLEM TYPE        (14)  -- what kind of problem is this?
  JOURNEY STAGE       (8)   -- where in the Action experience does it happen?

The 30 subcategories are v3.0, consolidated from 63 in v2.1. The finer v2.1
name survives per record as `topic_tags`: the distinction was often real but
too thin to carry a group of its own, and a group of one or two records
cannot support a trend, a share, or a ranking.

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
TAXONOMY_VERSION = "v3.0"
SCHEMA_VERSION = "v3.0"

# The fallback bucket. Deliberately NOT one of the 30 core subcategories: it
# exists so future feedback that genuinely fits nowhere has a home instead of
# being forced into the nearest core group, which would quietly corrupt that
# group's count. It is excluded from every "30 core" figure, and the reference
# views hide it until something is actually filed under it.
FALLBACK_SUBCATEGORY = "Other / Emerging"
FALLBACK_CATEGORY_HINT = (
    "Use only when the feedback is about Action configuration but matches no "
    "core subcategory. Prefer a core subcategory whenever one genuinely fits."
)


# ===========================================================================
# TAXONOMY v3.0: 11 categories -> 30 core subcategories
# ===========================================================================
# Consolidated from the 63 v2.1 subcategories; SUBCATEGORY_MIGRATION below
# records where each of the 63 went. Definitions and boundaries are generated
# from the assignment workbook by scripts/build_taxonomy_v3.py, and the
# examples are real evidence excerpts from records assigned to each group --
# invented ones would teach a distinction the data does not contain.
#
# Per category:  plain / default_stage / confusable / subcategories
# Per subcategory: plain / use_for[] / avoid / examples[]
TAXONOMY: dict[str, dict] = {
    "Discovery, Organization & Reuse": {
        "plain": "How users find, organize, display and reuse Actions.",
        "default_stage": "Action discovery & organization",
        "confusable": ["Permissions & Approvals", "Context, Targeting & Pre-fill"],
        "subcategories": {
            "Action discovery, organization & placement": {
                "plain": "Finding, organizing, ordering and placing Actions so users "
                          "see the right Action in the right catalog surface.",
                "use_for": [
                    "Action discovery, grouping & ordering",
                    "Conditional availability & placement",
                ],
                "avoid": "Authorization-based visibility belongs to Access control & "
                          "action eligibility. Multi-entity execution belongs to Bulk "
                          "actions.",
                "examples": [
                    "“there is a requirement to filter Self Service Actions on custom "
                    "catalogue pages”",
                    "“Allow categorizing self service actions for ease of finding "
                    "appropriate actions for your needs.”",
                ],
            },
            "Bulk actions": {
                "plain": "Running one Action against multiple selected or filtered "
                          "entities in a single operation.",
                "use_for": [
                    "Bulk actions",
                ],
                "avoid": "Several backend steps inside one Action belong to "
                          "Orchestration. Payload shaping belongs to Payload mapping & "
                          "transformation.",
                "examples": [
                    "“It would be great to have an option to do bulk actions(day2 and "
                    "DELETE) on entities”",
                    "“I want to run a single action that references all entities”",
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
            "Contextual launch, targeting & pre-fill": {
                "plain": "Launching an Action from the right surface with the "
                          "intended entity/resource and values Port can infer from "
                          "context.",
                "use_for": [
                    "Contextual entry & deep links",
                    "Entity and resource targeting",
                    "Pre-fill & context-specific defaults",
                    "Embedded & alternative launch surfaces",
                ],
                "avoid": "General defaults not derived from launch context belong to "
                          "Dynamic inputs, defaults & computed fields. Acting as the "
                          "requester belongs to Authentication, execution identity & "
                          "requester context.",
                "examples": [
                    "“an action if associated with service overview entity cant be "
                    "associated with the service blueprint entity - which means a new "
                    "actions should be created”",
                    "“the bot intentionally does not execute the action automatically. "
                    "Instead, it collects some parameters and then redirects the user "
                    "back to the Port UI”",
                ],
            },
        },
    },

    "Form Configuration": {
        "plain": "The visible form, the fields it contains, and how users complete it.",
        "default_stage": "Form & input configuration",
        "confusable": ["Validation & Rules", "Context, Targeting & Pre-fill", "Orchestration"],
        "subcategories": {
            "Input types & structured data": {
                "plain": "The field and control types available in Action forms, "
                          "including arrays, objects, tables and repeatable groups.",
                "use_for": [
                    "Input types & controls",
                    "Structured & repeatable inputs",
                ],
                "avoid": "Fields that change based on another value belong to Dynamic "
                          "inputs, defaults & computed fields. Visual arrangement "
                          "belongs to Form presentation, layout & guidance.",
                "examples": [
                    "“requiring users to manually select each item one by one — which "
                    "becomes tedious and time-consuming when dealing with large lists”",
                    "“Without a table view, the UX is not good”",
                ],
            },
            "Dynamic inputs, defaults & computed fields": {
                "plain": "Form values, options, visibility or editability that are "
                          "populated or recalculated from other inputs, data or "
                          "context.",
                "use_for": [
                    "Dynamic & dependent inputs",
                    "Defaults & computed fields",
                ],
                "avoid": "Context inherited from the launch surface belongs to "
                          "Contextual launch, targeting & pre-fill. Acceptance rules "
                          "belong to Form validation, messages & conditional rules.",
                "examples": [
                    "“This is done by calculating values based on the data of other "
                    "form inputs, user data, and entity data.”",
                    "“auto-generated from the previous inputs and NOT EDITABLE from "
                    "the user form”",
                ],
            },
            "Form presentation, layout & guidance": {
                "plain": "How the form is arranged, navigated, labelled and explained "
                          "to the end user.",
                "use_for": [
                    "Form layout, sections & multi-page forms",
                    "Labels, descriptions & display controls",
                ],
                "avoid": "New input capabilities belong to Input types & structured "
                          "data. Invalid-value explanations belong to Form validation, "
                          "messages & conditional rules.",
                "examples": [
                    "“This button will allow users to initiate the action immediately "
                    "if they do not need to modify any fields in subsequent steps.”",
                    "“the button is always displayed, even for forms intended purely "
                    "for informational or navigational purposes, which can confuse "
                    "users”",
                ],
            },
        },
    },

    "Validation & Rules": {
        "plain": "Rules deciding whether the values are acceptable and submission may "
                  "proceed.",
        "default_stage": "Validation, dependencies & conditional logic",
        "confusable": ["Form Configuration", "Observability & Debugging"],
        "subcategories": {
            "Form validation, messages & conditional rules": {
                "plain": "Pre-submission rules that determine whether form values are "
                          "valid and explain how users should correct them.",
                "use_for": [
                    "Input & cross-field validation",
                    "Conditional logic",
                    "Validation messages",
                ],
                "avoid": "Rules that must also hold through API/MCP belong to "
                          "Server-side & API enforcement. Runtime failures belong to "
                          "Logs & error diagnostics.",
                "examples": [
                    "“When the identifier is null, Port auto-generates an identifier "
                    "with a UUID so no error is raised from Port API, even though we "
                    "want to enforce it”",
                    "“conditional logic like \"replica count must be at least 3 when "
                    "deploying to production\", cross-field rules like email "
                    "confirmation, and meaningful error messages”",
                ],
            },
            "Server-side & API enforcement": {
                "plain": "Consistent validation and guardrail enforcement across UI, "
                          "API, MCP, JSON and other non-UI invocation paths.",
                "use_for": [
                    "Server-side & API enforcement",
                ],
                "avoid": "Missing integrations belong to Backends, APIs & event "
                          "triggers. UI-only validation belongs to Form validation, "
                          "messages & conditional rules.",
                "examples": [
                    "“validate the user input for corectness against custom business "
                    "logic, and display an error returned from the backend under the "
                    "text field, without actually submitting the form”",
                    "“Any execution path that bypasses the form UI, JSON mode, direct "
                    "API calls, or Port's MCP, skips these validations entirely, "
                    "allowing invalid or unauthorized inputs to be submitted.”",
                ],
            },
            "Expression & JQ authoring": {
                "plain": "Writing, testing, understanding and maintaining JQ or other "
                          "expressions used in Action configuration.",
                "use_for": [
                    "Expression and JQ rule authoring",
                ],
                "avoid": "Runtime expression failures belong to Logs & error "
                          "diagnostics. Payload reshaping belongs to Payload mapping & "
                          "transformation.",
                "examples": [
                    "“it is not possible to use JQ when creating conditions for Day-2 "
                    "or Delete actions”",
                    "“We should find a way to alert relevant stakeholders to the fact "
                    "that the calculated value is invalid when it occurs.”",
                ],
            },
        },
    },

    "Invocation & Integrations": {
        "plain": "How the submitted Action connects to the system that does the work.",
        "default_stage": "Backend & invocation setup",
        "confusable": ["Identity, Secrets & Security", "Orchestration"],
        "subcategories": {
            "Backends, APIs & event triggers": {
                "plain": "Choosing and connecting the backend, API, integration or "
                          "event mechanism that invokes or triggers the work.",
                "use_for": [
                    "Backend & invocation method selection",
                    "APIs & external integrations",
                    "Event triggers & action-to-automation integration",
                ],
                "avoid": "Payload shape belongs to Payload mapping & transformation. "
                          "Private execution infrastructure belongs to Execution "
                          "agents & runners.",
                "examples": [
                    "“another invocation type that would be awesome, would be directly "
                    "integrating with Lambda and OpenFAAS”",
                    "“Add the option to use a generic invocation method that sends a "
                    "log message to an action run ID provided as an input.”",
                ],
            },
            "Payload mapping & transformation": {
                "plain": "Selecting, reshaping, encoding, previewing or passing "
                          "through the data sent to a backend.",
                "use_for": [
                    "Payload mapping & transformation",
                ],
                "avoid": "Information inherited from the launch context belongs to "
                          "Contextual launch, targeting & pre-fill. Authentication "
                          "identity belongs to Identity, Secrets & Security.",
                "examples": [
                    "“The self-service engineer should be able to choose which entity "
                    "properties or property are relevant to send to the self-service "
                    "action.”",
                    "“base64 encoding username:PAT (or :PAT) is the correct approach, "
                    "and right now you have to do so outside of Port”",
                ],
            },
            "Execution agents & runners": {
                "plain": "Where an Action physically executes, including agent "
                          "selection, routing, connectivity and runner configuration.",
                "use_for": [
                    "Execution agents & runners",
                ],
                "avoid": "Selecting a normal SaaS backend belongs to Backends, APIs & "
                          "event triggers. Credentials belong to Credentials, secrets "
                          "& request signing.",
                "examples": [
                    "“You cannot control which agent processes which message at the "
                    "moment.”",
                    "“We want to communicate with an internal service without the "
                    "hassle of handling the self signed certificates”",
                ],
            },
        },
    },

    "Identity, Secrets & Security": {
        "plain": "Who or what executes the Action, and how sensitive data is "
                  "protected.",
        "default_stage": "Backend & invocation setup",
        "confusable": ["Invocation & Integrations", "Permissions & Approvals"],
        "subcategories": {
            "Authentication, execution identity & requester context": {
                "plain": "Who or what executes the Action and which trusted requester "
                          "identity/context is propagated to downstream systems.",
                "use_for": [
                    "Authentication & delegated execution",
                    "Service accounts & execution identity",
                    "Current-user and context propagation",
                ],
                "avoid": "Permission to start the Action belongs to Access control & "
                          "action eligibility. Secret storage belongs to Credentials, "
                          "secrets & request signing.",
                "examples": [
                    "“Passing the User Form .user object to the backend is not safe, "
                    "as it can be spoofed and allow user impersonation.”",
                    "“we need is to perform a request to obtain the JWT before each "
                    "SSA action and then include it in the header of the action”",
                ],
            },
            "Credentials, secrets & request signing": {
                "plain": "Securely storing, resolving and using credentials, tokens "
                          "and signatures for Action invocations.",
                "use_for": [
                    "Credentials & secrets management",
                    "Message signing & webhook security",
                ],
                "avoid": "Preventing sensitive values from appearing in UI/logs "
                          "belongs to Sensitive-data masking & redaction.",
                "examples": [
                    "“Infosec policy mandates all secrets stored in HashiCorp Vault "
                    "only”",
                    "“Allow the {{ .secrets.<secret_name> }} syntax in the secret "
                    "field for webhook, consistent with how secrets are already used "
                    "in self-service action and automation payloads.”",
                ],
            },
            "Sensitive-data masking & redaction": {
                "plain": "Preventing sensitive inputs, payload fields, outputs and "
                          "logs from being exposed to unauthorized viewers.",
                "use_for": [
                    "Sensitive-data masking & redaction",
                ],
                "avoid": "Secret storage and retrieval belong to Credentials, secrets "
                          "& request signing. General payload visibility belongs to "
                          "Observability unless the restriction is security-driven.",
                "examples": [
                    "“There is currently no way to mark a variable as sensitive so "
                    "that its value is redacted or masked in the run history display.”",
                    "“defining an input as a secret does not work in cases where there "
                    "is an approver on the action”",
                ],
            },
        },
    },

    "Permissions & Approvals": {
        "plain": "Who can see or run an Action, and who must approve it before it "
                  "runs.",
        "default_stage": "Permissions & approvals",
        "confusable": ["Identity, Secrets & Security", "Discovery, Organization & Reuse"],
        "subcategories": {
            "Access control & action eligibility": {
                "plain": "Rules deciding who may view, create, edit, trigger or "
                          "inspect an Action and whether the UI reflects that "
                          "eligibility early.",
                "use_for": [
                    "RBAC & dynamic permissions",
                    "Action visibility & eligibility",
                ],
                "avoid": "The UI for creating/testing permission rules belongs to "
                          "Permission authoring & testing. Downstream execution "
                          "identity belongs to Identity, Secrets & Security.",
                "examples": [
                    "“those values aren't present on the .user object in the dynamic "
                    "permissions/self service action context”",
                    "“I want to allow some users to be able to create self-service "
                    "actions in our STG environment without giving them full Admin "
                    "access.”",
                ],
            },
            "Permission authoring & testing": {
                "plain": "Creating, previewing, testing and debugging permission "
                          "rules and their outcomes.",
                "use_for": [
                    "Permission authoring & testing",
                ],
                "avoid": "New access-control capability belongs to Access control & "
                          "action eligibility. Action-definition release lifecycle "
                          "belongs to Authoring, Testing & Management.",
                "examples": [
                    "“the error message logged provides no context about what specific "
                    "part of the dynamic permission caused the action to be denied”",
                    "“execute permissions can be removed entirely, which allows an "
                    "action to be saved with no execute permissions at all”",
                ],
            },
            "Approval policies & approver routing": {
                "plain": "Deciding when approval is required, how many approvals are "
                          "needed and who should receive the request.",
                "use_for": [
                    "Approval policies & thresholds",
                    "Approver routing & identity",
                ],
                "avoid": "The approver's decision UI and messages belong to Approver "
                          "experience & notifications. Mid-workflow approvals belong "
                          "to Orchestration.",
                "examples": [
                    "“Allows Port Admins to intervene and instantly approve any "
                    "pending request manually.”",
                    "“we approve our own requests... we have to approve our own "
                    "request, which is just extra work”",
                ],
            },
            "Approver experience & notifications": {
                "plain": "How approvers are notified, understand the request, "
                          "communicate, edit permitted values and approve or reject "
                          "it.",
                "use_for": [
                    "Approver experience & request editing",
                    "Approval notifications",
                ],
                "avoid": "Policy configuration and approver selection belong to "
                          "Approval policies & approver routing. Historical approval "
                          "evidence belongs to Run history, audit, APIs & export.",
                "examples": [
                    "“the admin that approves the request will want to make a change "
                    "to the inputs provided by the user”",
                    "“both the approver and the requester should be able to exchange "
                    "messages/comments directly within the action run context in Port”",
                ],
            },
        },
    },

    "Orchestration": {
        "plain": "Actions containing several connected execution steps, decisions or "
                  "systems.",
        "default_stage": "Backend & invocation setup",
        "confusable": ["Form Configuration", "Invocation & Integrations", "Execution Lifecycle"],
        "subcategories": {
            "Multi-step orchestration, branching & data flow": {
                "plain": "Building multi-step workflows with sequencing, branches, "
                          "multiple systems and data passed between steps.",
                "use_for": [
                    "Multi-step workflows",
                    "Shared context & output passing",
                    "Branching & conditional paths",
                    "Multi-backend & multi-system sequencing",
                ],
                "avoid": "Multiple visual pages in a form belong to Form "
                          "Configuration. Selecting a single backend belongs to "
                          "Invocation & Integrations.",
                "examples": [
                    "“the .outputs available to downstream JQ expressions only include "
                    "workflowRunUrl and workflowRunId, not result, workflowStatus, or "
                    "any error detail”",
                    "“Due to Port's current setup, I have to combine these 5 GH "
                    "actions into one since the SSA can only trigger one backend”",
                ],
            },
            "Workflow approvals, error handling & recovery": {
                "plain": "Controlling workflow steps through intermediate approvals, "
                          "failure branches, retries, compensation and recovery "
                          "behavior.",
                "use_for": [
                    "Intermediate approvals",
                    "Step-level error handling & recovery",
                ],
                "avoid": "Approval before an Action starts belongs to Permissions & "
                          "Approvals. Whole-run retry/cancel belongs to Execution "
                          "Lifecycle.",
                "examples": [
                    "“Can't easily implement basic alerting without misrepresenting "
                    "operational health.”",
                    "“prompt an approval request and based on the approval, invoke "
                    "another trigger”",
                ],
            },
        },
    },

    "Execution Lifecycle": {
        "plain": "What users can do to a Run, and how the Run behaves over its life.",
        "default_stage": "Execution, monitoring & run control",
        "confusable": ["Observability & Debugging", "Orchestration"],
        "subcategories": {
            "Retry, rerun, cancel & resume": {
                "plain": "User controls for repeating, interrupting or continuing an "
                          "Action run.",
                "use_for": [
                    "Retry, rerun & duplicate execution",
                    "Cancel, stop & resume",
                ],
                "avoid": "Automatic resilience belongs to Reliability, timeouts & "
                          "concurrency. Step-level recovery belongs to Orchestration.",
                "examples": [
                    "“Ability to cancel the execution of an action after triggering it”",
                    "“Adding a retry action for a run can be nice addition”",
                ],
            },
            "Reliability, timeouts & concurrency": {
                "plain": "Runtime safeguards governing duration, simultaneous "
                          "execution, duplicate prevention and automatic handling of "
                          "transient failures.",
                "use_for": [
                    "Timeouts",
                    "Concurrency, rate limits & duplicate prevention",
                    "Reliability & transient-failure handling",
                ],
                "avoid": "Manual retry/cancel belongs to Retry, rerun, cancel & "
                          "resume. A deterministic product defect remains a Bug "
                          "problem type.",
                "examples": [
                    "“Ability to configure timeout values for actions within Port so "
                    "that certain operations, like deploying a service, do not exceed "
                    "a certain duration.”",
                    "“users can click the button multiple times, unintentionally "
                    "triggering duplicate executions”",
                ],
            },
            "Completion & result-state control": {
                "plain": "Determining, setting or correcting when a Run is complete "
                          "and which terminal/result state it has.",
                "use_for": [
                    "Completion & result-state control",
                ],
                "avoid": "Displaying status belongs to Run status, progress & "
                          "notifications. Failure explanation belongs to Logs & error "
                          "diagnostics.",
                "examples": [
                    "“I would like to have the same ability just with create/update "
                    "invocation type.”",
                    "“the list should contain all Gitlab's possible pipeline statuses: "
                    "(created, waiting_for_resource, preparing, pending, running, "
                    "success, failed, canceled, skipped, manual, scheduled)”",
                ],
            },
        },
    },

    "Observability & Debugging": {
        "plain": "Helping users understand what happened during or after a Run.",
        "default_stage": "Execution, monitoring & run control",
        "confusable": ["Execution Lifecycle", "Validation & Rules", "Permissions & Approvals"],
        "subcategories": {
            "Run status, progress & notifications": {
                "plain": "Showing current run state/progress and proactively "
                          "notifying users of success, failure, delay or completion.",
                "use_for": [
                    "Run status & progress",
                    "Execution notifications & alerting",
                ],
                "avoid": "Changing the state belongs to Completion & result-state "
                          "control. Detailed diagnostics belong to Logs & error "
                          "diagnostics.",
                "examples": [
                    "“action run status are predefined and limited to \"Success\", "
                    "\"Failure\" and \"In progress\"”",
                    "“There is no indication of whether the action is queued, "
                    "rate-limited, or encountered an error during startup.”",
                ],
            },
            "Logs & error diagnostics": {
                "plain": "Detailed runtime logs, backend responses and actionable "
                          "explanations of execution failures.",
                "use_for": [
                    "Logs & log streaming",
                    "Error messages & backend responses",
                ],
                "avoid": "Pre-submission errors belong to Validation & Rules. "
                          "Sensitive-log masking belongs to Identity, Secrets & "
                          "Security.",
                "examples": [
                    "“users must wait for an action to complete or a certain amount of "
                    "data to be processed before logs can be viewed”",
                    "“Currently, there is no way to edit current action logs.”",
                ],
            },
            "Run history, audit, APIs & export": {
                "plain": "Searching, auditing, filtering, exporting or "
                          "programmatically querying historical Run and approval "
                          "records.",
                "use_for": [
                    "Run history, audit & filtering",
                    "Run-history APIs & export",
                    "Approval audit & context",
                ],
                "avoid": "Linking a Run to the objects it changed belongs to Run "
                          "traceability & related entities. Definition-change history "
                          "belongs to Authoring, Testing & Management.",
                "examples": [
                    "“A dashboard/homepage widget that displays the runs of a specific "
                    "self-service action.”",
                    "“there is not enough ability for filtering of the returned runs, "
                    "there is no \"include\" parameter, and the limit is set to max of "
                    "1000 runs without ability for pagination”",
                ],
            },
            "Run traceability & related entities": {
                "plain": "Connecting a Run to its Action, requester, pipeline and the "
                          "entities/resources it affected.",
                "use_for": [
                    "Run traceability & related entities",
                ],
                "avoid": "General historical querying belongs to Run history, audit, "
                          "APIs & export. Outbound payload construction belongs to "
                          "Payload mapping & transformation.",
                "examples": [
                    "“The Gitlab default payload config should reflect back a url to "
                    "the pipeline for easy access”",
                    "“Currently it's only possible tying entities to an action run by "
                    "manually sending an API request to the entities with the "
                    "`run_id`”",
                ],
            },
        },
    },

    "Authoring, Testing & Management": {
        "plain": "Helping builders safely create, test, edit, publish and maintain "
                  "Actions.",
        "default_stage": "Testing, editing & publishing",
        "confusable": ["Execution Lifecycle", "Validation & Rules"],
        "subcategories": {
            "Action authoring, testing & release management": {
                "plain": "Safely creating, learning, previewing, editing, publishing, "
                          "disabling, versioning and rolling back Action definitions.",
                "use_for": [
                    "Preview & dry run",
                    "Playground, examples & in-product help",
                    "Editing & unsaved-change safety",
                    "Drafts, publishing & disablement",
                    "Versioning, change detection & rollback",
                ],
                "avoid": "Form fields and end-user form UX belong to Form "
                          "Configuration. Programmatic configuration and reuse belong "
                          "to Reusable configuration, API & IaC management.",
                "examples": [
                    "“In the GUI mode, users may accidentally navigate away without "
                    "saving their changes.”",
                    "“The examples that are being provided are automatically generated "
                    "and in some cases are not aligned with the actual data.”",
                ],
            },
            "Reusable configuration, API & IaC management": {
                "plain": "Creating reusable Action definitions and managing or moving "
                          "them programmatically through API, IaC, templates, import "
                          "or export.",
                "use_for": [
                    "API & IaC configuration management",
                    "Reusability & templates",
                ],
                "avoid": "Invoking an Action via API belongs to Invocation & "
                          "Integrations. Reusing only a permission policy remains "
                          "primarily Access control & action eligibility.",
                "examples": [
                    "“It would be really nice if you could go into a self service "
                    "action and see a similar view.”",
                    "“that action has to be created and its inputs need to be "
                    "configured manually”",
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

# --- feedback polarity -----------------------------------------------------
# What the customer was expressing, judged from the text itself.
#
# Deliberately independent of lifecycle_status. A Completed roadmap item still
# records the pain that prompted it, so a shipped request is not automatically
# positive; classifying from status rather than text would erase the original
# signal and make "what hurts" unanswerable for anything already delivered.
POLARITIES: dict[str, str] = {
    "Negative": "Describes a problem, unmet need, blocker, friction, failure "
                "or difficulty -- including a feature request clearly motivated "
                "by current pain or an inability to finish a task.",
    "Positive": "Expresses satisfaction, praise, a successful outcome, or "
                "confirms that a shipped capability solved the problem.",
    "Neutral": "Primarily informational, descriptive, a factual question or a "
               "technical clarification, with no clear praise or pain.",
}
POLARITY_NAMES: tuple[str, ...] = tuple(POLARITIES)

LIFECYCLE_STATUSES: tuple[str, ...] = (
    "Open", "Planned", "In progress", "Completed", "Closed", "Unknown",
)

# Statuses representing live, unmet demand.
#
# Only "Open" counts. Planned and In progress were previously included, but
# both mean Port has already committed to the work -- counting them as open
# demand argues for building something that is already being built. They stay
# visible through the lifecycle filter and are labelled with their status; they
# simply do not add to a product action's supporting count or its ranking.
COUNTED_STATUSES: frozenset[str] = frozenset({"Open"})

# Retained for the evidence explorer, which still distinguishes work that is
# live in some form from work that has shipped or been dropped.
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
    {"left": "Permissions & Approvals - permissions side",
     "right": "Permissions & Approvals - approvals side",
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
        "subcategory": "Contextual launch, targeting & pre-fill",
        "problem_type": "Usability friction",
        "stage": "Contextual entry, targeting & pre-fill",
        "why": "The problem is not the type of input. Port already knows the relevant "
               "Service and should fill it in automatically.",
    },
    {
        "feedback": "The available regions should change after I select a cloud provider.",
        "category": "Form Configuration",
        "subcategory": "Dynamic inputs, defaults & computed fields",
        "problem_type": "Feature gap",
        "stage": "Form & input configuration",
        "why": "The field's options must react to another selection. Nothing is being "
               "checked for validity yet, so this is not Validation.",
    },
    {
        "feedback": "The user can run the Action, but a manager must approve production "
                    "deployments.",
        "category": "Permissions & Approvals",
        "subcategory": "Approval policies & approver routing",
        "problem_type": "Feature gap",
        "stage": "Permissions & approvals",
        "why": "The issue is not whether the user may start the Action. It is the "
               "approval required before it executes.",
    },
    {
        "feedback": "The Action started and failed, but the run page does not explain why.",
        "category": "Observability & Debugging",
        "subcategory": "Logs & error diagnostics",
        "problem_type": "Poor error message",
        "stage": "Execution, monitoring & run control",
        "why": "The failure happened after submission, so it belongs to execution "
               "rather than form validation.",
    },
    {
        "feedback": "Divide this long form into three screens.",
        "category": "Form Configuration",
        "subcategory": "Form presentation, layout & guidance",
        "problem_type": "Usability friction",
        "stage": "Form & input configuration",
        "why": "Several visual pages are a form-layout concern. Only several BACKEND "
               "operations would be Orchestration.",
    },
    {
        "feedback": "The approver never received the Slack request to approve.",
        "category": "Permissions & Approvals",
        "subcategory": "Approver experience & notifications",
        "problem_type": "Bug / defect",
        "stage": "Permissions & approvals",
        "why": "An approval-request notification blocks the user at the approval stage, "
               "not at execution -- unlike a success or failure alert.",
    },
    {
        "feedback": "Secrets must be stored in HashiCorp Vault, not inside Port.",
        "category": "Identity, Secrets & Security",
        "subcategory": "Credentials, secrets & request signing",
        "problem_type": "Security or privacy concern",
        "stage": "Backend & invocation setup",
        "why": "Storing and retrieving the credential is a secrets concern, even though "
               "the credential is used during invocation.",
    },
    {
        "feedback": "Let me retry the failed Run without filling in the form again.",
        "category": "Execution Lifecycle",
        "subcategory": "Retry, rerun, cancel & resume",
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

# ===========================================================================
# v2.1 -> v3.0 SUBCATEGORY MIGRATION
# ===========================================================================
# Where each of the 63 former subcategories went. Every one has a destination:
# a migration that silently drops a name would strand any record still
# carrying it, and the test suite asserts the map covers all 63.
#
# The former name is not thrown away -- it is preserved per record as
# topic_tags, so the finer technical distinction stays queryable even though
# it is no longer an analytical group.
SUBCATEGORY_MIGRATION: dict[str, str] = {
    # -> Action authoring, testing & release management
    "Drafts, publishing & disablement": "Action authoring, testing & release management",
    "Editing & unsaved-change safety": "Action authoring, testing & release management",
    "Playground, examples & in-product help": "Action authoring, testing & release management",
    "Preview & dry run": "Action authoring, testing & release management",
    "Versioning, change detection & rollback": "Action authoring, testing & release management",
    # -> Reusable configuration, API & IaC management
    "API & IaC configuration management": "Reusable configuration, API & IaC management",
    "Reusability & templates": "Reusable configuration, API & IaC management",
    # -> Contextual launch, targeting & pre-fill
    "Contextual entry & deep links": "Contextual launch, targeting & pre-fill",
    "Embedded & alternative launch surfaces": "Contextual launch, targeting & pre-fill",
    "Entity and resource targeting": "Contextual launch, targeting & pre-fill",
    "Pre-fill & context-specific defaults": "Contextual launch, targeting & pre-fill",
    # -> Action discovery, organization & placement
    "Action discovery, grouping & ordering": "Action discovery, organization & placement",
    "Conditional availability & placement": "Action discovery, organization & placement",
    # -> Bulk actions
    "Bulk actions": "Bulk actions",
    # -> Completion & result-state control
    "Completion & result-state control": "Completion & result-state control",
    # -> Reliability, timeouts & concurrency
    "Concurrency, rate limits & duplicate prevention": "Reliability, timeouts & concurrency",
    "Reliability & transient-failure handling": "Reliability, timeouts & concurrency",
    "Timeouts": "Reliability, timeouts & concurrency",
    # -> Retry, rerun, cancel & resume
    "Cancel, stop & resume": "Retry, rerun, cancel & resume",
    "Retry, rerun & duplicate execution": "Retry, rerun, cancel & resume",
    # -> Dynamic inputs, defaults & computed fields
    "Defaults & computed fields": "Dynamic inputs, defaults & computed fields",
    "Dynamic & dependent inputs": "Dynamic inputs, defaults & computed fields",
    # -> Form presentation, layout & guidance
    "Form layout, sections & multi-page forms": "Form presentation, layout & guidance",
    "Labels, descriptions & display controls": "Form presentation, layout & guidance",
    # -> Input types & structured data
    "Input types & controls": "Input types & structured data",
    "Structured & repeatable inputs": "Input types & structured data",
    # -> Authentication, execution identity & requester context
    "Authentication & delegated execution": "Authentication, execution identity & requester context",
    "Current-user and context propagation": "Authentication, execution identity & requester context",
    "Service accounts & execution identity": "Authentication, execution identity & requester context",
    # -> Credentials, secrets & request signing
    "Credentials & secrets management": "Credentials, secrets & request signing",
    "Message signing & webhook security": "Credentials, secrets & request signing",
    # -> Sensitive-data masking & redaction
    "Sensitive-data masking & redaction": "Sensitive-data masking & redaction",
    # -> Backends, APIs & event triggers
    "APIs & external integrations": "Backends, APIs & event triggers",
    "Backend & invocation method selection": "Backends, APIs & event triggers",
    "Event triggers & action-to-automation integration": "Backends, APIs & event triggers",
    # -> Execution agents & runners
    "Execution agents & runners": "Execution agents & runners",
    # -> Payload mapping & transformation
    "Payload mapping & transformation": "Payload mapping & transformation",
    # -> Logs & error diagnostics
    "Error messages & backend responses": "Logs & error diagnostics",
    "Logs & log streaming": "Logs & error diagnostics",
    # -> Run history, audit, APIs & export
    "Approval audit & context": "Run history, audit, APIs & export",
    "Run history, audit & filtering": "Run history, audit, APIs & export",
    "Run-history APIs & export": "Run history, audit, APIs & export",
    # -> Run status, progress & notifications
    "Execution notifications & alerting": "Run status, progress & notifications",
    "Run status & progress": "Run status, progress & notifications",
    # -> Run traceability & related entities
    "Run traceability & related entities": "Run traceability & related entities",
    # -> Multi-step orchestration, branching & data flow
    "Branching & conditional paths": "Multi-step orchestration, branching & data flow",
    "Multi-backend & multi-system sequencing": "Multi-step orchestration, branching & data flow",
    "Multi-step workflows": "Multi-step orchestration, branching & data flow",
    "Shared context & output passing": "Multi-step orchestration, branching & data flow",
    # -> Workflow approvals, error handling & recovery
    "Intermediate approvals": "Workflow approvals, error handling & recovery",
    "Step-level error handling & recovery": "Workflow approvals, error handling & recovery",
    # -> Access control & action eligibility
    "Action visibility & eligibility": "Access control & action eligibility",
    "RBAC & dynamic permissions": "Access control & action eligibility",
    # -> Approval policies & approver routing
    "Approval policies & thresholds": "Approval policies & approver routing",
    "Approver routing & identity": "Approval policies & approver routing",
    # -> Approver experience & notifications
    "Approval notifications": "Approver experience & notifications",
    "Approver experience & request editing": "Approver experience & notifications",
    # -> Permission authoring & testing
    "Permission authoring & testing": "Permission authoring & testing",
    # -> Expression & JQ authoring
    "Expression and JQ rule authoring": "Expression & JQ authoring",
    # -> Form validation, messages & conditional rules
    "Conditional logic": "Form validation, messages & conditional rules",
    "Input & cross-field validation": "Form validation, messages & conditional rules",
    "Validation messages": "Form validation, messages & conditional rules",
    # -> Server-side & API enforcement
    "Server-side & API enforcement": "Server-side & API enforcement",
}

CATEGORY_NAMES: tuple[str, ...] = tuple(TAXONOMY)

SUBCATEGORY_NAMES_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    cat: tuple(meta["subcategories"]) for cat, meta in TAXONOMY.items()
}

# The 30 core subcategories. This is what the guide, the filter rail and every
# count mean by "the taxonomy" -- the fallback is deliberately absent.
ALL_SUBCATEGORY_NAMES: tuple[str, ...] = tuple(
    sub for subs in SUBCATEGORY_NAMES_BY_CATEGORY.values() for sub in subs
)

# What the classifier is allowed to return: the 30 core groups plus the
# fallback. Separate from ALL_SUBCATEGORY_NAMES on purpose -- the fallback has
# to be reachable for feedback that fits nowhere, without inflating the core
# count or appearing in a reference view as a 31st group.
ASSIGNABLE_SUBCATEGORY_NAMES: tuple[str, ...] = (
    *ALL_SUBCATEGORY_NAMES, FALLBACK_SUBCATEGORY,
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
    """True if the subcategory really belongs to that category.

    The fallback is valid under any of the 11 categories: "no core subcategory
    fits" is a statement about the subcategory level, not the category, and a
    record that reaches it still knows which product area it belongs to.
    """
    if subcategory == FALLBACK_SUBCATEGORY:
        return category in TAXONOMY
    return subcategory in SUBCATEGORY_NAMES_BY_CATEGORY.get(category, ())


def default_stage_for(category: str) -> str | None:
    return DEFAULT_STAGE_FOR_CATEGORY.get(category)
