"""The floating Product Data Assistant panel.

Rendering only. Every number shown here comes from `src.assistant.analytics`,
which is plain pandas over the classified records -- no model is called when a
question is answered, so the panel works with no API key, offline, and at zero
token cost.

The panel is a keyed Streamlit container that CSS pins to the viewport. It is
rendered once at shell level, after both tabs, so the same conversation is on
screen whichever view the reader is in.

Result rows carry `data-afi-click` proxies to hidden buttons, the same
mechanism the dashboard charts use, so an evidence drill-down is an ordinary
rerun rather than a navigation.
"""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from ..assistant import QUESTIONS, QUESTIONS_BY_ID
from ..assistant.analytics import Answer
from .theme import SEVERITY_BADGE

SCOPE_ALL = "All in-scope feedback"
SCOPE_FILTERED = "Use current Dashboard filters"
SCOPE_OPTIONS = (SCOPE_ALL, SCOPE_FILTERED)

MAX_HISTORY = 10
EVIDENCE_PAGE = 5

EV_CLICK = "afiev"

INTRO = ("Choose one of the questions below. Every answer is calculated from "
         "the existing feedback data without using AI.")

# The longer "prototype mode" paragraph that used to sit above the intro is
# gone. It said the same thing as the intro line and the production footer
# between them, and three explanations of what the assistant is not left less
# room for what it does.

PRODUCTION_NOTE = (
    "Optional AI could add free-text questions and cross-record synthesis — "
    "still citing the exact records it used, and only where deterministic "
    "analysis falls short."
)

LAUNCHER_LABEL = "Open Product Data Assistant"

LAUNCHER_LABEL_SCRIPT = f"""
<script>
(() => {{
  const doc = window.parent.document;
  const apply = () => {{
    const btn = doc.querySelector('.st-key-afi_assistant_launcher button');
    if (btn) btn.setAttribute('aria-label', {LAUNCHER_LABEL!r});
  }};
  apply();
  setTimeout(apply, 300);
}})();
</script>
"""

STATE_DEFAULTS: dict[str, object] = {
    "afi_assistant_open": False,
    "afi_assistant_history": [],
    "afi_assistant_selected_question": None,
    "afi_assistant_scope": SCOPE_ALL,
    "afi_assistant_evidence_ids": [],
    "afi_assistant_evidence_key": None,
    "afi_assistant_evidence_title": "",
    "afi_assistant_evidence_limit": EVIDENCE_PAGE,
    "afi_assistant_show_questions": True,
}


def _esc(value: object) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def init_state() -> None:
    for key, value in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = list(value) if isinstance(value, list) else value


# --- callbacks -------------------------------------------------------------
# All of these run as on_click callbacks, before the next script run creates
# any widget, so they may assign widget-bound keys freely.
def _toggle_panel() -> None:
    st.session_state["afi_assistant_open"] = not st.session_state["afi_assistant_open"]


def _close_panel() -> None:
    """Closing hides the panel and keeps the conversation, per the spec."""
    st.session_state["afi_assistant_open"] = False


def _clear_conversation() -> None:
    st.session_state["afi_assistant_history"] = []
    st.session_state["afi_assistant_selected_question"] = None
    st.session_state["afi_assistant_show_questions"] = True
    _close_evidence()


def _show_questions() -> None:
    st.session_state["afi_assistant_show_questions"] = True


def _close_evidence() -> None:
    st.session_state["afi_assistant_evidence_ids"] = []
    st.session_state["afi_assistant_evidence_key"] = None
    st.session_state["afi_assistant_evidence_title"] = ""
    st.session_state["afi_assistant_evidence_limit"] = EVIDENCE_PAGE


def _open_evidence(key: str, ids: list[str], title: str) -> None:
    if st.session_state.get("afi_assistant_evidence_key") == key:
        _close_evidence()
        return
    st.session_state["afi_assistant_evidence_key"] = key
    st.session_state["afi_assistant_evidence_ids"] = list(ids)
    st.session_state["afi_assistant_evidence_title"] = title
    st.session_state["afi_assistant_evidence_limit"] = EVIDENCE_PAGE


def _more_evidence() -> None:
    st.session_state["afi_assistant_evidence_limit"] = (
        st.session_state.get("afi_assistant_evidence_limit", EVIDENCE_PAGE)
        + EVIDENCE_PAGE)


def _ask(question_id: str) -> None:
    st.session_state["afi_assistant_selected_question"] = question_id
    st.session_state["afi_assistant_show_questions"] = False
    _close_evidence()


# --- scope -----------------------------------------------------------------
def resolve_scope(full: pd.DataFrame, filtered: pd.DataFrame,
                  choice: str) -> tuple[pd.DataFrame, str]:
    """The records a question runs against, and the line describing them.

    Default is the whole in-scope dataset. Dashboard filters are opt-in
    because they are not visible from inside the panel: an answer that
    silently reflected a subcategory filter set ten minutes ago would look
    like a fact about the product.
    """
    if choice == SCOPE_FILTERED:
        return (filtered,
                f"Based on {len(filtered)} record"
                f"{'' if len(filtered) == 1 else 's'} matching the current "
                f"Dashboard filters")
    return (full, f"Based on all {len(full)} in-scope feedback records")


# --- markup ----------------------------------------------------------------
def render_header() -> str:
    """The robot mark is painted by CSS -- see theme.robot_data_uri."""
    return (
        '<div class="afi-bot-head">'
        '<span class="afi-bot-avatar" aria-hidden="true"></span>'
        '<div class="afi-bot-heading">'
        '<div class="afi-bot-title">Product Data Assistant</div>'
        '<div class="afi-bot-sub">Explore the feedback with predefined analyses</div>'
        "</div></div>"
    )


def render_bubble(text: str, role: str = "bot") -> str:
    return f'<div class="afi-bot-msg afi-bot-{_esc(role)}">{_esc(text)}</div>'


def render_answer(entry: dict, index: int) -> str:
    """One answered question: scope, finding, ranked rows, method note."""
    answer: Answer = entry["answer"]
    out = [f'<div class="afi-bot-msg afi-bot-user">{_esc(entry["label"])}</div>',
           '<div class="afi-bot-msg afi-bot-answer">',
           f'<div class="afi-bot-scope">{_esc(entry["scope_label"])}</div>']

    if answer.is_empty:
        out.append(f'<div class="afi-bot-empty">{_esc(answer.empty_message)}</div>')
    else:
        out.append(f'<div class="afi-bot-finding">{_esc(answer.finding)}</div>')
        out.append('<div class="afi-bot-rows">')
        for position, row in enumerate(answer.rows):
            cells = "".join(
                f'<span class="afi-bot-cell"><em>{_esc(head)}</em>'
                f"<b>{_esc(row.values.get(field, '—'))}</b></span>"
                for field, head in answer.columns
            )
            sub = (f'<div class="afi-bot-rowsub">{_esc(row.sublabel)}</div>'
                   if row.sublabel else "")
            count = len(row.feedback_ids)
            link = (
                f'<a class="afi-bot-evidence-link" href="#" role="button" '
                f'data-afi-click="{EV_CLICK}_{index}_{position}">'
                f"View supporting records ({count})</a>"
            ) if count else ""
            out.append(
                '<div class="afi-bot-row">'
                f'<div class="afi-bot-rank">{position + 1}</div>'
                '<div class="afi-bot-rowbody">'
                f'<div class="afi-bot-rowtitle">{_esc(row.label)}</div>'
                f"{sub}"
                f'<div class="afi-bot-cells">{cells}</div>'
                f"{link}</div></div>"
            )
        out.append("</div>")

    if answer.note:
        out.append(f'<div class="afi-bot-note">{_esc(answer.note)}</div>')
    out.append("</div>")
    return "".join(out)


def render_evidence(records: list[dict], title: str, total: int) -> str:
    """The source records behind one result row.

    Selected by exact feedback_id, never by category: the row was computed
    from these records, so anything else would be a different claim wearing
    the same number.
    """
    out = ['<div class="afi-bot-ev">',
           f'<div class="afi-bot-ev-head">Supporting records · {_esc(title)}'
           f'<span>{len(records)} of {total}</span></div>']
    for r in records:
        created = (r.get("created_at") or "")[:10]
        badges = [
            f'<span class="afi-badge b-neutral">{_esc(r.get("source_system"))}</span>',
            f'<span class="afi-badge b-blue">{_esc(r.get("lifecycle_status"))}</span>',
        ]
        if created:
            badges.append(f'<span class="afi-badge b-neutral">{_esc(created)}</span>')
        badges.append(
            f'<span class="afi-badge '
            f'{SEVERITY_BADGE.get(int(r.get("severity") or 1), "b-neutral")}">'
            f'Severity {_esc(r.get("severity"))}</span>')
        badges.append(f'<span class="afi-badge b-neutral">Confidence '
                      f'{float(r.get("confidence") or 0):.2f}</span>')
        quote = (f'<div class="afi-bot-ev-quote">“{_esc(r.get("evidence_excerpt"))}”'
                 "</div>" if r.get("evidence_verified") else "")
        out.append(
            '<div class="afi-bot-ev-card">'
            f'<div class="afi-bot-ev-title">{_esc(r.get("title"))}</div>'
            f'<div class="afi-bot-ev-meta">{"".join(badges)}</div>'
            f"{quote}"
            f'<a class="afi-source" target="_blank" '
            f'href="{_esc(r.get("source_url"))}">Open original source ↗</a>'
            "</div>"
        )
    out.append("</div>")
    return "".join(out)


def render_footer() -> str:
    return (
        '<div class="afi-bot-foot">'
        '<div class="afi-bot-foot-title">Production extension</div>'
        f"<p>{_esc(PRODUCTION_NOTE)}</p>"
        "</div>"
    )


# --- Streamlit composition -------------------------------------------------
def render(full: pd.DataFrame, filtered: pd.DataFrame,
           forwarder: str | None = None) -> None:
    """Draw the launcher and, when open, the panel."""
    init_state()
    # The forwarder is idempotent (it guards on a flag set on the document).
    # The label script is not: Streamlit renders the launcher as a button whose
    # only text is an emoji, which a screen reader announces as "robot" rather
    # than as what it opens, and there is no Streamlit parameter for aria-label.
    components.html((forwarder or "") + LAUNCHER_LABEL_SCRIPT, height=0)

    with st.container(key="afi_assistant_launcher"):
        st.button("🤖", key="afi_assistant_toggle", on_click=_toggle_panel,
                  help=LAUNCHER_LABEL)

    if not st.session_state["afi_assistant_open"]:
        return

    # Answer the pending question before drawing, so the new exchange appears
    # in this run rather than one rerun later.
    pending = st.session_state.get("afi_assistant_selected_question")
    st.session_state["afi_assistant_selected_question"] = None
    scope_choice = st.session_state.get("afi_assistant_scope", SCOPE_ALL)
    scope_frame, scope_label = resolve_scope(full, filtered, scope_choice)

    if pending:
        question = QUESTIONS_BY_ID[pending]
        st.session_state["afi_assistant_history"].append({
            "question_id": question.question_id,
            "label": question.label,
            "scope_label": scope_label,
            "answer": question.handler(scope_frame),
        })
        del st.session_state["afi_assistant_history"][:-MAX_HISTORY]

    history = st.session_state["afi_assistant_history"]

    with st.container(key="afi_assistant_panel"):
        st.markdown(render_header(), unsafe_allow_html=True)

        with st.container(key="afi_assistant_close"):
            st.button("✕", key="afi_assistant_close_btn", on_click=_close_panel,
                      help="Close the assistant")

        with st.container(key="afi_assistant_scope_box"):
            st.radio("Data scope", SCOPE_OPTIONS, key="afi_assistant_scope",
                     horizontal=False)

        st.markdown(f'<div class="afi-bot-body">{render_bubble(INTRO)}</div>',
                    unsafe_allow_html=True)

        _render_history(history, full)

        if st.session_state["afi_assistant_show_questions"]:
            st.markdown(
                '<div class="afi-bot-qhead">Predefined analyses</div>',
                unsafe_allow_html=True)
            with st.container(key="afi_assistant_questions"):
                for question in QUESTIONS:
                    st.button(question.label, key=f"afi_q_{question.question_id}",
                              on_click=_ask, args=(question.question_id,),
                              help=question.short_description)

        with st.container(key="afi_assistant_controls"):
            if not st.session_state["afi_assistant_show_questions"]:
                st.button("Ask another question", key="afi_assistant_again",
                          on_click=_show_questions)
            if history:
                st.button("Clear conversation", key="afi_assistant_clear",
                          on_click=_clear_conversation)

        st.markdown(render_footer(), unsafe_allow_html=True)


def _render_history(history: list[dict], full: pd.DataFrame) -> None:
    """Each exchange, with the evidence drawer open under the row it belongs to."""
    open_key = st.session_state.get("afi_assistant_evidence_key")
    by_id = {str(r["feedback_id"]): r for r in full.to_dict("records")}

    for index, entry in enumerate(history):
        st.markdown(f'<div class="afi-bot-body">{render_answer(entry, index)}</div>',
                    unsafe_allow_html=True)

        # Hidden proxies for this answer's "View supporting records" links.
        with st.container(key=f"afi_assistant_ev_{index}"):
            for position, row in enumerate(entry["answer"].rows):
                if not row.feedback_ids:
                    continue
                st.button("go", key=f"{EV_CLICK}_{index}_{position}",
                          on_click=_open_evidence,
                          args=(f"{index}_{position}", row.feedback_ids, row.label))

        if open_key and open_key.startswith(f"{index}_"):
            ids = st.session_state["afi_assistant_evidence_ids"]
            limit = st.session_state["afi_assistant_evidence_limit"]
            records = [by_id[i] for i in ids if i in by_id][:limit]
            st.markdown(
                '<div class="afi-bot-body">'
                + render_evidence(records,
                                  st.session_state["afi_assistant_evidence_title"],
                                  len(ids))
                + "</div>",
                unsafe_allow_html=True)
            with st.container(key=f"afi_assistant_evctl_{index}"):
                if len(records) < len(ids):
                    st.button(f"Show {min(EVIDENCE_PAGE, len(ids) - len(records))} more",
                              key=f"afi_assistant_more_{index}", on_click=_more_evidence)
                st.button("Hide supporting records", key=f"afi_assistant_hide_{index}",
                          on_click=_close_evidence)
