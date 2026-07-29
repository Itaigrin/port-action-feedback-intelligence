"""The controlled vocabulary used to classify Action Configuration feedback.

Two dimensions, deliberately at different granularity so they answer different
questions and the dashboard shows two genuinely different views:

  JOURNEY STAGE  (7, coarse)  -- WHERE in setting up an action the user is stuck.
                                 Mirrors Port's documented self-service flow, so
                                 a finding points at a surface the team owns.
  THEME          (12, fine)   -- WHAT specific problem area it is. This is what
                                 gets ranked and turned into a recommendation.

Themes are not strictly nested inside stages: several (multi-step
orchestration, notifications) legitimately span stages, and that cross-tab is
where the interesting findings live.
"""

from __future__ import annotations

# --- Journey stages --------------------------------------------------------
JOURNEY_STAGES: dict[str, str] = {
    "Discovering and organizing actions":
        "Finding the right action, browsing or searching the catalog, grouping "
        "and categorizing actions, and controlling what appears to whom.",
    "Configuring forms and inputs":
        "Defining the inputs a user fills in: field types, controls, ordering, "
        "defaults, prefilled values, and how the form is laid out.",
    "Validations and conditional logic":
        "Rules that constrain or change the form: required fields, regex and "
        "type checks, cross-field rules, and inputs that depend on each other.",
    "Backend and invocation setup":
        "Wiring the action to what actually runs it: webhooks, CI pipelines, "
        "payload mapping, secrets and credentials, and invocation settings.",
    "Permissions and approvals":
        "Who may run or edit an action, dynamic and conditional permissions, "
        "and manual or automatic approval steps before execution.",
    "Testing and editing":
        "Trying an action before release, iterating on an existing action, and "
        "the editing experience itself, including unsaved-change handling.",
    "Execution and monitoring":
        "What happens after the trigger: run status, progress, logs, errors, "
        "audit history, retries, and cancelling or re-running.",
}

# --- Themes ----------------------------------------------------------------
THEMES: dict[str, str] = {
    "Action discovery & organization":
        "Users cannot find, group, categorize, or make sense of the actions "
        "available to them.",
    "Input types & controls":
        "The available input field types or controls are missing, limited, or "
        "cannot express what the form needs.",
    "Dynamic & dependent inputs":
        "Inputs that must react to other inputs, be populated from an API or "
        "dataset, or change as the user fills the form.",
    "Validation & conditional logic":
        "Rules that constrain input or control form behaviour: required-ness, "
        "patterns, cross-field checks, and conditional visibility.",
    "Backend & invocation configuration":
        "Connecting the action to its backend: webhooks, pipelines, payload "
        "construction, secrets, and invocation settings.",
    "Permissions & access control":
        "Expressing who may see, run, or edit an action, including dynamic and "
        "attribute-based permission rules.",
    "Approval workflows":
        "Manual or automatic approval before an action runs: approvers, "
        "thresholds, notifications to approvers, and approval routing.",
    "Testing & editing experience":
        "Trying an action safely before release, and the ergonomics of editing "
        "an existing action.",
    "Execution visibility & logs":
        "Seeing what an action did or is doing: status, progress, logs, errors, "
        "and audit history.",
    "Run control & retries":
        "Acting on a run after it starts: retrying, cancelling, pausing, "
        "resuming, or marking outcomes.",
    "Multi-step & orchestration":
        "Actions composed of several steps or stages, and chaining or "
        "sequencing work across them.",
    "Notifications & alerting":
        "Telling people something needs attention or has happened, through "
        "email, Slack, Teams, or other channels.",
}

# --- Feedback types --------------------------------------------------------
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

# --- Severity --------------------------------------------------------------
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

# --- Disambiguation --------------------------------------------------------
# Written because these cases came up while inspecting the real board. Without
# them the model splits near-identical posts across stages, which is exactly
# the defect that shows up as low agreement in evaluation.
TIE_BREAK_RULES: list[str] = [
    "Classify by where the USER IS STUCK, not by which feature is named. A "
    "complaint that an action's *form* is hard to configure belongs to "
    "'Configuring forms and inputs' even if it mentions the backend.",

    "Automations and workflow triggers that configure how an action is invoked "
    "-> 'Backend and invocation setup'.",

    "Anything about not being able to SEE what happened (status, logs, errors, "
    "audit trail) -> 'Execution and monitoring', regardless of which stage "
    "produced the failure.",

    "Approvals are 'Permissions and approvals' even when the request is about "
    "notifying approvers; the notification is the theme, the stage is approvals.",

    "If a post spans several stages, choose the one the user's PROBLEM starts "
    "in, not the one they mention last.",

    "Multi-step or staged action forms -> stage 'Configuring forms and inputs', "
    "theme 'Multi-step & orchestration'.",
]

STAGE_NAMES = tuple(JOURNEY_STAGES)
THEME_NAMES = tuple(THEMES)
FEEDBACK_TYPE_NAMES = tuple(FEEDBACK_TYPES)
