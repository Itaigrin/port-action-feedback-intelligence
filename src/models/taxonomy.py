"""The controlled vocabulary used to classify Action Configuration feedback.

Two dimensions, deliberately at different granularity so they answer different
questions and the dashboard shows two genuinely different views:

  JOURNEY STAGE  (8, coarse)  -- WHERE in the action lifecycle the user hits the
                                 problem. Insertion order below IS the
                                 chronological lifecycle order, and everything
                                 downstream (charts, filters, docs) relies on it.
  THEME          (11, fine)   -- WHAT product problem or improvement is being
                                 asked for. This is what gets ranked and turned
                                 into a recommended product response.

A theme answers "what is the main product change that would solve this?".
A stage answers "where does the user's friction begin?".

Themes are not strictly nested inside stages. Two deliberate examples:
  * Multi-step & orchestration defaults to Backend & invocation setup, because
    several connected backend operations are a backend concern -- while a single
    form split into visual pages is Form structure, not orchestration.
  * Execution visibility, notifications & run control defaults to Execution,
    monitoring & run control -- but a missing approval-request notification sits
    at the Permissions & approvals stage, because that is where the user is
    blocked.

That cross-tab is where the interesting findings live.

This module is the single source of truth. Do not duplicate these definitions
in app.py or in documentation -- import them.
"""

from __future__ import annotations

# --- Journey stages ---------------------------------------------------------
# INSERTION ORDER IS CHRONOLOGICAL. Charts, filters, aggregations and the guide
# all derive their ordering from STAGE_NAMES, so reordering this dict silently
# reorders the product journey everywhere.
JOURNEY_STAGES: dict[str, str] = {
    "Action discovery & organization":
        "The user is trying to find and understand the actions available to "
        "them: searching, browsing, categories, folders, naming, and catalog "
        "organization.",
    "Contextual entry, targeting & pre-fill":
        "The user opens the action from a specific context, and Port should "
        "already know what the action applies to: opening from an entity page, "
        "selecting the target automatically, pre-filling contextual values, and "
        "preserving the originating service, resource or environment.",
    "Form & input configuration":
        "The visible form and its basic fields are being configured or "
        "completed: input types, field order, layout, labels, descriptions, "
        "form controls, multi-page forms, and reducing form complexity.",
    "Validation, dependencies & conditional logic":
        "The form reacts to what the user enters and decides whether it is "
        "valid and ready to submit: required values, validation rules, field "
        "dependencies, dynamic options and values, conditional visibility, "
        "disabled and read-only states, and pre-submission error messages.",
    "Backend & invocation setup":
        "The action is connected to the system that performs the actual work: "
        "webhooks, APIs, pipelines, payloads, authentication, credentials, "
        "secrets, backend parameter mapping, and orchestration.",
    "Permissions & approvals":
        "The system decides whether the action may continue and whether "
        "approval is required: permissions, eligibility, action visibility, "
        "RBAC, approval rules, approvers, governance, and production guardrails.",
    "Testing, editing & publishing":
        "The action builder tests and manages the action definition before or "
        "between releases: preview, test runs, draft configuration, editing, "
        "duplication, versioning, publishing, and unsaved changes.",
    "Execution, monitoring & run control":
        "The action has been submitted or started, and users need to understand "
        "or control the run: status, progress, logs, history, retry, cancel, "
        "resume, runtime notifications, and success or failure information.",
}

# --- Themes -----------------------------------------------------------------
# Insertion order is the canonical theme order used by THEME_NAMES.
THEMES: dict[str, str] = {
    "Action discovery & organization":
        "Finding, understanding, browsing and organizing the available actions: "
        "search, categories, folders, tags, sorting, naming, and how the action "
        "catalog is presented.",
    "Context, targeting & pre-fill":
        "Using information Port already knows to open an action with the right "
        "target and context, instead of making the user re-select what the "
        "originating page already implies.",
    "Form structure, input types & controls":
        "The basic structure of the action form and the kinds of fields it "
        "contains: input controls, labels, help text, grouping, field order, "
        "and splitting a long form into visual pages.",
    "Dynamic & dependent inputs":
        "Fields that change automatically based on context or earlier "
        "selections: dependent dropdowns, options loaded from an API or "
        "dataset, dynamic defaults, conditional visibility, and enabled, "
        "disabled or read-only states.",
    "Validation & error guidance":
        "Checking whether entered information is valid and explaining clearly "
        "what needs to be corrected, before the action is submitted.",
    "Backend & invocation configuration":
        "Configuring what happens behind the scenes once the form is "
        "submitted: webhooks, APIs, pipelines, payload construction, headers, "
        "authentication, credentials, secrets, and invocation settings.",
    "Permissions, eligibility & action visibility":
        "Controlling who can see or run an action and whether they are "
        "eligible to use it: RBAC, role, team and group permissions, dynamic "
        "and attribute-based rules, and visibility conditions.",
    "Approval workflows & governance":
        "Defining who must approve an action and which governance rules apply "
        "before it runs: approvers, approval counts, conditional and "
        "risk-based approval, routing, and guardrails for sensitive actions.",
    "Testing, editing & drafts":
        "Helping action builders safely create, test, save, edit and publish "
        "an action: preview, test runs, drafts, unsaved-change warnings, "
        "version history, publishing and rollback.",
    "Execution visibility, notifications & run control":
        "Understanding and controlling what happens after an action is "
        "submitted or starts running: status, progress, runtime errors, logs, "
        "history, retry, cancel, resume, and notifications about the run.",
    "Multi-step & orchestration":
        "Actions that perform several connected backend operations or span "
        "multiple systems: sequential or parallel steps, passing data between "
        "steps, branching, and rollback or compensation between steps.",
}

# --- Feedback types (unchanged) --------------------------------------------
FEEDBACK_TYPES: dict[str, str] = {
    "Feature request":
        "Asks for a capability that does not exist today.",
    "Usability friction":
        "The capability exists, but is confusing, tedious, or harder to use "
        "than it should be.",
    "Bug":
        "Something behaves incorrectly compared to what is documented or "
        "reasonably expected.",
    "Documentation gap":
        "The capability exists, but the user could not discover or understand "
        "how to use it.",
    "Reliability issue":
        "Works inconsistently: intermittent failures, timeouts, or breakage "
        "under load or at scale.",
}

# --- Severity (unchanged) --------------------------------------------------
SEVERITY_SCALE: dict[int, str] = {
    5: "Blocking. The user cannot complete setup or execution at all, and no "
       "workaround is described.",
    4: "Major. A workaround exists but is expensive -- custom code, an external "
       "system, or a manual process on every use.",
    3: "Moderate. Noticeably slows setup or forces repeated manual steps, but "
       "the goal is still achievable.",
    2: "Minor. Small inefficiency, rough edge, or cosmetic problem.",
    1: "Nice to have. No pain described; purely additive improvement.",
}

# --- Default theme -> stage mapping ----------------------------------------
# A guideline, not a constraint. The classifier may pick a different stage when
# the feedback clearly warrants it -- the approval-notification case below is
# the canonical example.
DEFAULT_STAGE_FOR_THEME: dict[str, str] = {
    "Action discovery & organization": "Action discovery & organization",
    "Context, targeting & pre-fill": "Contextual entry, targeting & pre-fill",
    "Form structure, input types & controls": "Form & input configuration",
    "Dynamic & dependent inputs": "Validation, dependencies & conditional logic",
    "Validation & error guidance": "Validation, dependencies & conditional logic",
    "Backend & invocation configuration": "Backend & invocation setup",
    "Permissions, eligibility & action visibility": "Permissions & approvals",
    "Approval workflows & governance": "Permissions & approvals",
    "Testing, editing & drafts": "Testing, editing & publishing",
    "Execution visibility, notifications & run control":
        "Execution, monitoring & run control",
    "Multi-step & orchestration": "Backend & invocation setup",
}

# --- Disambiguation --------------------------------------------------------
# Every rule here exists because the distinction genuinely recurs in the real
# data. Without them the model splits near-identical posts across categories,
# which is exactly the defect that shows up as low agreement in evaluation.
TIE_BREAK_RULES: list[str] = [
    "DISCOVERY vs PERMISSIONS. 'I cannot find the action' -> theme 'Action "
    "discovery & organization'. 'This action should not be visible to this "
    "user' -> theme 'Permissions, eligibility & action visibility'. Absence "
    "caused by a permission rule is a permissions problem, not a search problem.",

    "CONTEXT vs FORM CONFIGURATION. 'Port already knows which service I am "
    "using, so stop asking me' -> theme 'Context, targeting & pre-fill'. 'I "
    "need a new field, or a different field order' -> theme 'Form structure, "
    "input types & controls'.",

    "FORM STRUCTURE vs DYNAMIC INPUTS. 'I need a date field' -> theme 'Form "
    "structure, input types & controls'. 'The available dates depend on the "
    "selected environment' -> theme 'Dynamic & dependent inputs'.",

    "DYNAMIC INPUTS vs VALIDATION. If a field CHANGES because of another "
    "selection -> theme 'Dynamic & dependent inputs'. If the system CHECKS "
    "whether an entered value is allowed -> theme 'Validation & error guidance'.",

    "PERMISSIONS vs APPROVALS. 'Who may see or run the action?' -> theme "
    "'Permissions, eligibility & action visibility'. 'Who must approve it "
    "before it runs?' -> theme 'Approval workflows & governance'. Both share "
    "the stage 'Permissions & approvals'.",

    "VALIDATION ERROR vs RUNTIME FAILURE. An error BEFORE submission -> theme "
    "'Validation & error guidance', stage 'Validation, dependencies & "
    "conditional logic'. A failure AFTER the action started -> theme "
    "'Execution visibility, notifications & run control', stage 'Execution, "
    "monitoring & run control'.",

    "TESTING vs EXECUTION. A builder trying an action before release -> theme "
    "'Testing, editing & drafts'. A real user's submitted run -> theme "
    "'Execution visibility, notifications & run control'.",

    "MULTI-PAGE FORM vs MULTI-STEP ORCHESTRATION. One form divided into several "
    "visual pages or sections -> theme 'Form structure, input types & "
    "controls'. Several connected BACKEND operations -> theme 'Multi-step & "
    "orchestration'.",

    "APPROVAL NOTIFICATION vs RUN NOTIFICATION. A missing notification asking "
    "someone TO APPROVE -> theme 'Execution visibility, notifications & run "
    "control' but stage 'Permissions & approvals', because that is where the "
    "user is blocked. A missing success or failure notification -> the same "
    "theme with stage 'Execution, monitoring & run control'.",

    "CONTEXTUAL DEFAULT vs GENERAL DEFAULT. A value inferred from the entity "
    "page or originating surface -> theme 'Context, targeting & pre-fill'. A "
    "default computed from other form fields -> theme 'Dynamic & dependent "
    "inputs'. A fixed default that never changes -> theme 'Form structure, "
    "input types & controls'.",

    "FEEDBACK SPANNING CATEGORIES. Choose the THEME representing the product "
    "change that would solve the main problem, and the STAGE where the user "
    "first becomes blocked. Never classify on keywords alone, and never force "
    "unrelated feedback into this taxonomy -- set is_relevant=false instead.",
]

# --- Beginner-friendly guide metadata -------------------------------------
# Consumed by the "Themes & Journey Stages Guide" tab. Kept here so the guide,
# the prompt and the classifier can never describe the taxonomy differently.
THEME_GUIDE: dict[str, dict] = {
    "Action discovery & organization": {
        "plain": "The user struggles to find or make sense of the actions available to them.",
        "use_when": [
            "Search, categories, subcategories, folders or tags",
            "Sorting, ordering, or unclear action names",
            "Too many actions on one page, or a cluttered catalog",
            "Controlling how the available actions are displayed",
        ],
        "avoid_when": "An action is hidden or shown because of the user's permissions "
                      "— that is 'Permissions, eligibility & action visibility'.",
        "examples": [
            "\"We have 60 actions in one long list and nobody can find the right one.\"",
            "\"Let us group actions into categories like Deploy, Access and Database.\"",
        ],
    },
    "Context, targeting & pre-fill": {
        "plain": "Port already knows what the action applies to, but still makes the user say it again.",
        "use_when": [
            "Automatically selecting the current entity",
            "Pre-filling a service, resource, namespace, environment or other target",
            "Opening an action from an entity page and keeping that context",
            "Avoiding repeated manual entity selection",
        ],
        "avoid_when": "The request is only for a new input type, a different field "
                      "order, or a fixed default unrelated to where the action was opened from.",
        "examples": [
            "\"I opened this action from a specific service page, so I should not have to pick that service again.\"",
            "\"The environment should be filled in automatically based on the page I came from.\"",
        ],
    },
    "Form structure, input types & controls": {
        "plain": "The form's basic building blocks — which kinds of fields exist and how they are laid out.",
        "use_when": [
            "Text, number, date, file upload, dropdown or multi-select controls",
            "Field labels, descriptions, placeholder or help text",
            "Reordering or grouping fields, reducing form complexity",
            "Splitting one long form into several visual pages",
        ],
        "avoid_when": "A field changes because of another field, a condition, or context "
                      "— that is 'Dynamic & dependent inputs'.",
        "examples": [
            "\"We need a file upload field so users can attach a config file.\"",
            "\"This form has 25 fields in one column; let us split it into sections.\"",
        ],
    },
    "Dynamic & dependent inputs": {
        "plain": "Fields that change by themselves, based on context or on what the user already chose.",
        "use_when": [
            "One input depending on another",
            "Dropdown options loaded from an API or dataset",
            "Dynamic or context-based default values",
            "Conditional visibility, or enabled, disabled and read-only states",
        ],
        "avoid_when": "The system is only checking whether a value the user typed is "
                      "acceptable — that is 'Validation & error guidance'.",
        "examples": [
            "\"When environment is Production, show the risk level field.\"",
            "\"The available regions should change after I pick a cloud provider.\"",
        ],
    },
    "Validation & error guidance": {
        "plain": "Checking that what was entered is acceptable, and explaining clearly what to fix.",
        "use_when": [
            "Required fields, format rules, minimum and maximum values",
            "Comparisons between fields, or custom validation rules",
            "Blocking submission when values are invalid",
            "Error messages that are technically correct but do not say what to do",
        ],
        "avoid_when": "The action was submitted successfully and then failed while running "
                      "— that is 'Execution visibility, notifications & run control'.",
        "examples": [
            "\"If replica count is above 3, an approval reason should become required.\"",
            "\"The form says the value is invalid but never says which format it wants.\"",
        ],
    },
    "Backend & invocation configuration": {
        "plain": "Wiring the action to whatever actually does the work once the form is submitted.",
        "use_when": [
            "Webhooks, APIs, pipelines, GitHub workflows, invocation methods",
            "Payload construction, transforming submitted values, headers",
            "Authentication, credentials and secrets",
            "Backend parameter mapping, timeouts, technical invocation settings",
        ],
        "avoid_when": "The user is trying to view or control a run that has already "
                      "started — that is 'Execution visibility, notifications & run control'.",
        "examples": [
            "\"Let us reshape the payload before it is sent to the workflow.\"",
            "\"We need to store the API token in a vault rather than inside Port.\"",
        ],
    },
    "Permissions, eligibility & action visibility": {
        "plain": "Who is allowed to see or run an action, and whether they are eligible at all.",
        "use_when": [
            "RBAC, user, role, team or group permissions",
            "Dynamic or attribute-based permissions",
            "Hiding actions a user cannot run, or eligibility rules",
            "Rejection only after the user filled in and submitted the whole form",
        ],
        "avoid_when": "The user is allowed to submit, but somebody else must approve first "
                      "— that is 'Approval workflows & governance'.",
        "examples": [
            "\"Users see actions they are not allowed to run, and only find out at the end.\"",
            "\"We need finer admin roles so some admins can only edit automations.\"",
        ],
    },
    "Approval workflows & governance": {
        "plain": "Who must approve an action, and which governance rules apply before it runs.",
        "use_when": [
            "Choosing approvers, or how many approvals are required",
            "Automatic, conditional or risk-based approval",
            "Different behaviour for production versus non-production",
            "Guardrails for destructive or sensitive actions, approval routing",
        ],
        "avoid_when": "The request is only about who can see or start the action "
                      "— that is 'Permissions, eligibility & action visibility'.",
        "examples": [
            "\"Production deployments should need two approvals, staging none.\"",
            "\"Approval should only be required when the request exceeds a cost threshold.\"",
        ],
    },
    "Testing, editing & drafts": {
        "plain": "Helping the person who builds an action create, test and change it safely.",
        "use_when": [
            "Preview or test runs before release",
            "Editing or duplicating an existing action, saving a draft",
            "Warnings about unsaved changes, version history, comparing versions",
            "Publishing, unpublishing, disabling or rolling back",
        ],
        "avoid_when": "A real user already submitted the action and that run failed "
                      "— that is 'Execution visibility, notifications & run control'.",
        "examples": [
            "\"I lost my edits because nothing warned me about leaving the page.\"",
            "\"Let us dry-run an action to check it works before exposing it to everyone.\"",
        ],
    },
    "Execution visibility, notifications & run control": {
        "plain": "Seeing and controlling what happens after an action is submitted or starts running.",
        "use_when": [
            "Run status, progress, runtime errors, logs, execution or audit history",
            "Retry, cancel, stop, resume, restart, or marking a run's outcome",
            "Who triggered the action",
            "Notifications after success, failure or completion, on Slack, email or Teams",
        ],
        "avoid_when": "The feedback is about the approver, approval policy, routing or "
                      "conditions — that is 'Approval workflows & governance'.",
        "examples": [
            "\"The run failed and the run page does not explain why.\"",
            "\"Let us retry a failed run without filling in the whole form again.\"",
        ],
    },
    "Multi-step & orchestration": {
        "plain": "One action that performs several connected backend operations, possibly across systems.",
        "use_when": [
            "Several execution steps, run in sequence or in parallel",
            "Passing data between steps, branches, or dependencies between steps",
            "Workflows spanning multiple systems",
            "Rollback or compensation between execution steps",
        ],
        "avoid_when": "It is one form divided into several visual pages "
                      "— that is 'Form structure, input types & controls'.",
        "examples": [
            "\"Chain a provisioning step, an approval, and then a deployment step.\"",
            "\"If step two fails, roll back what step one created.\"",
        ],
    },
}

STAGE_GUIDE: dict[str, dict] = {
    "Action discovery & organization": {
        "plain": "Before anything else, the user has to find the right action.",
        "user_goal": "Work out which action does what they need, out of everything available.",
        "example": "\"There are dozens of actions in one flat list and I cannot tell which one deploys my service.\"",
    },
    "Contextual entry, targeting & pre-fill": {
        "plain": "The user opens the action from somewhere specific, and that context should carry over.",
        "user_goal": "Start the action already pointed at the right service, resource or environment.",
        "example": "\"I clicked the action from a service page, but it asks me to choose the service again.\"",
    },
    "Form & input configuration": {
        "plain": "The form itself — which fields exist and how they are arranged.",
        "user_goal": "Fill in a form that has the right fields, clearly labelled and sensibly ordered.",
        "example": "\"There is no way to attach a file, and the fields are in a confusing order.\"",
    },
    "Validation, dependencies & conditional logic": {
        "plain": "The form reacts to what is typed, and decides whether it is ready to submit.",
        "user_goal": "Be guided to valid input, with fields that adapt to earlier choices.",
        "example": "\"It rejects my value without saying what format it expects.\"",
    },
    "Backend & invocation setup": {
        "plain": "The behind-the-scenes plumbing that does the actual work.",
        "user_goal": "Connect the action to the pipeline, API or system that performs the task.",
        "example": "\"We need to reshape the data before it is sent to our workflow.\"",
    },
    "Permissions & approvals": {
        "plain": "The gate: is this person allowed, and does anyone need to sign off?",
        "user_goal": "Only run what they are entitled to, with the right approvals in place.",
        "example": "\"I filled in the whole form and only then was told I am not permitted.\"",
    },
    "Testing, editing & publishing": {
        "plain": "The builder's workshop — creating and changing the action definition.",
        "user_goal": "Build, test and release an action safely, without breaking it for users.",
        "example": "\"I want to try the action myself before anyone else can see it.\"",
    },
    "Execution, monitoring & run control": {
        "plain": "The action is running or finished, and people need to know what happened.",
        "user_goal": "See the outcome, understand failures, and retry or cancel when needed.",
        "example": "\"The run failed hours ago and nobody was notified.\"",
    },
}

GLOSSARY: dict[str, str] = {
    "Action": "A form that lets someone request or trigger a task, such as deploying "
              "a service or requesting access.",
    "Entity": "An item stored in Port, such as a service, application, environment "
              "or resource.",
    "Pre-fill": "Automatically placing known information into a field so the user "
                "does not have to enter it again.",
    "Input": "A field in a form where the user enters or selects information.",
    "Validation": "A check that confirms whether the information entered in a form "
                  "is acceptable.",
    "Payload": "The package of information sent from the form to the system that "
               "performs the task.",
    "Webhook": "A way for one system to automatically send information to another "
               "system when something happens.",
    "API": "A structured way for software systems to communicate with each other.",
    "Credential": "Information used to prove that a system or user is allowed to "
                  "connect.",
    "Secret": "Sensitive information, such as a password or access token, that "
              "should be stored securely.",
    "Permission": "A rule that determines who is allowed to see or perform something.",
    "Approval": "A decision another person must make before an action is allowed to "
                "continue.",
    "Execution": "The period when the requested task is actually being performed.",
    "Run": "One specific attempt to execute an action.",
    "Log": "A record of events and messages produced while an action is running.",
    "Retry": "Trying to run a failed action again.",
    "Orchestration": "Coordinating several connected tasks or systems as one process.",
    "Draft": "A saved version of an action that is not yet ready or published.",
}

# Commonly confused pairs, rendered side by side in the guide.
CONFUSION_PAIRS: list[dict[str, str]] = [
    {"left": "Action discovery & organization", "right": "Permissions, eligibility & action visibility",
     "left_says": "\"I cannot find the action.\"",
     "right_says": "\"The action should not be visible to this user.\""},
    {"left": "Context, targeting & pre-fill", "right": "Form structure, input types & controls",
     "left_says": "\"The system already knows which service I am using.\"",
     "right_says": "\"I need a new field, or a different field order.\""},
    {"left": "Form structure, input types & controls", "right": "Dynamic & dependent inputs",
     "left_says": "\"I need a date field.\"",
     "right_says": "\"The available dates should depend on the selected environment.\""},
    {"left": "Dynamic & dependent inputs", "right": "Validation & error guidance",
     "left_says": "\"The field changes based on another selection.\"",
     "right_says": "\"The system checks whether the entered value is allowed.\""},
    {"left": "Permissions, eligibility & action visibility", "right": "Approval workflows & governance",
     "left_says": "\"Who is allowed to see or run the action?\"",
     "right_says": "\"Who must approve it before it runs?\""},
    {"left": "Validation & error guidance", "right": "Execution visibility, notifications & run control",
     "left_says": "\"The form should not be submitted with this value.\"",
     "right_says": "\"The action was submitted, started, and then failed.\""},
    {"left": "Testing, editing & drafts", "right": "Execution visibility, notifications & run control",
     "left_says": "\"The builder is checking the action before releasing it.\"",
     "right_says": "\"A real user submitted an action and wants to see what happened.\""},
    {"left": "Form structure, input types & controls", "right": "Multi-step & orchestration",
     "left_says": "\"One form is visually divided into several pages.\"",
     "right_says": "\"The action executes several connected backend operations.\""},
    {"left": "Execution visibility, notifications & run control (stage: Permissions & approvals)",
     "right": "Execution visibility, notifications & run control (stage: Execution, monitoring & run control)",
     "left_says": "\"An approver did not receive the approval request.\"",
     "right_says": "\"The user did not receive a success or failure notification.\""},
]

# Worked examples used by the guide's "how feedback is classified" section.
WORKED_EXAMPLES: list[dict[str, str]] = [
    {
        "feedback": "I launched the action from a service page, but I still have to select "
                    "the service manually.",
        "theme": "Context, targeting & pre-fill",
        "stage": "Contextual entry, targeting & pre-fill",
        "why": "The problem is not the type of input. The system already knows the relevant "
               "service and should fill it in automatically.",
    },
    {
        "feedback": "The available regions should change after I select a cloud provider.",
        "theme": "Dynamic & dependent inputs",
        "stage": "Validation, dependencies & conditional logic",
        "why": "The field's options need to react to another selection. Nothing is being "
               "checked for validity yet.",
    },
    {
        "feedback": "The user can run the action, but a manager must approve production "
                    "deployments.",
        "theme": "Approval workflows & governance",
        "stage": "Permissions & approvals",
        "why": "The issue is not whether the user may start the action. It is the approval "
               "required before it executes.",
    },
    {
        "feedback": "The action started and failed, but the run page does not explain why.",
        "theme": "Execution visibility, notifications & run control",
        "stage": "Execution, monitoring & run control",
        "why": "The failure happened after submission, so it belongs to execution rather "
               "than form validation.",
    },
]

STAGE_NAMES = tuple(JOURNEY_STAGES)
THEME_NAMES = tuple(THEMES)
FEEDBACK_TYPE_NAMES = tuple(FEEDBACK_TYPES)
