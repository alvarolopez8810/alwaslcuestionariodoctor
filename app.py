"""
Al Wasl FC - Medical & Performance Reporting Workflow Audit.

Process questionnaire for the medical department. Process data only: no
player-level medical data is requested or stored (see audit/privacy.py).

Run locally:  streamlit run app.py
"""

import json
import uuid

import pandas as pd
import streamlit as st

from audit import auth
from audit.emailer import email_configured, send_xlsx
from audit.export import build_xlsx, xlsx_filename
from audit.privacy import PRIVACY_NOTICE, scan_answers
from audit.questions import OTHER, PHASES, SECTIONS, TABLES, iter_questions
from audit.storage import StorageError, build_record, get_storage

st.set_page_config(page_title="Daily Report Discovery · Al Wasl FC", page_icon="📋", layout="wide")

st.markdown(
    """
    <style>
      .block-container {max-width: 1200px; padding-top: 4.5rem;}
      .audit-title {color:#0B4C44; font-weight:700; font-size:1.7rem; line-height:1.3; margin-bottom:0;}
      .audit-sub {color:#6b6b63; margin-top:0.1rem;}
      .privacy {border-left:5px solid #DAB344; background:#FBF6E6; padding:0.9rem 1.1rem;
                border-radius:6px; margin:0.6rem 0 1.2rem 0; color:#2b2b2b;}
      @media (max-width: 640px) {
        .block-container {padding: 3.75rem 0.9rem 2rem 0.9rem;}
        .audit-title {font-size: 1.3rem;}
        .audit-sub {font-size: 0.9rem;}
        .privacy {padding: 0.7rem 0.8rem; font-size: 0.92rem;}
        div[data-testid="stExpander"] summary p {font-size: 1rem;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)

auth.require_login()
auth.logout_button()

LABELS = {q["id"]: q["label"] for _, q in iter_questions()}


# --------------------------------------------------------------------------
# Storage (cached per session; errors are shown, not fatal)
# --------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def _storage():
    return get_storage()


try:
    storage = _storage()
    storage_error = None
except Exception as exc:  # noqa: BLE001 - surface any config/connection error in the UI
    storage, storage_error = None, f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------------------
# Session-state helpers
# --------------------------------------------------------------------------

def _empty_table(table_id: str) -> pd.DataFrame:
    spec = TABLES[table_id]
    cols = [k for k, _, _, _ in spec["columns"]]
    if "fixed_rows" in spec:
        rows = [{c: (aud if c == "audience" else None) for c in cols} for aud in spec["fixed_rows"]]
        return pd.DataFrame(rows, columns=cols)
    return pd.DataFrame([{c: None for c in cols}], columns=cols)


def _reset_form(answers: dict | None = None, submission_id: str | None = None):
    """Clear the form, or load a previous submission's answers for revision."""
    answers = answers or {}
    for _, q in iter_questions():
        qid, t, val = q["id"], q["type"], answers.get(q["id"])
        for suffix in ("", "_detail", "_other"):
            st.session_state.pop(f"q_{qid}{suffix}", None)
        if t == "table":
            df = pd.DataFrame(val) if val else _empty_table(qid)
            for k, _, _, _ in TABLES[qid]["columns"]:
                if k not in df.columns:
                    df[k] = None
            df = df[[k for k, _, _, _ in TABLES[qid]["columns"]]]
            st.session_state[f"tbl_{qid}"] = df
            st.session_state[f"cards_{qid}"] = _to_cards(_clean_records(df))
        elif val in (None, "", {}, []):
            continue
        elif t == "radio":
            if val.get("choice") in q["options"]:
                st.session_state[f"q_{qid}"] = val["choice"]
            st.session_state[f"q_{qid}_detail"] = val.get("detail", "")
        elif t == "multi":
            st.session_state[f"q_{qid}"] = [c for c in val.get("choices", []) if c in q["options"]]
            st.session_state[f"q_{qid}_other"] = val.get("other", "")
        else:
            st.session_state[f"q_{qid}"] = val
    for k in [k for k in st.session_state if str(k).startswith("card_")]:
        del st.session_state[k]
    st.session_state["editor_version"] = st.session_state.get("editor_version", 0) + 1
    st.session_state["editing_submission_id"] = submission_id
    st.session_state.pop("last_result", None)


def _clean_records(df: pd.DataFrame) -> list[dict]:
    out = []
    for rec in df.to_dict("records"):
        out.append({k: ("" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip())
                    for k, v in rec.items()})
    return out


def _to_cards(rows: list[dict]) -> list[dict]:
    """Phone-layout rows carry a stable id so widget keys survive removals."""
    return [dict(r, _uid=uuid.uuid4().hex[:8]) for r in rows]


def _table_ids() -> list[str]:
    return [q["id"] for _, q in iter_questions() if q["type"] == "table"]


def _switch_layout():
    """Carry table rows across when toggling between table and phone layouts."""
    for qid in _table_ids():
        keys = [k for k, _, _, _ in TABLES[qid]["columns"]]
        rows = st.session_state.get(f"tbl_{qid}_out") or []
        if st.session_state.get("phone_mode"):
            st.session_state[f"cards_{qid}"] = _to_cards(rows or [{k: "" for k in keys}])
        else:
            st.session_state[f"tbl_{qid}"] = (pd.DataFrame(rows, columns=keys).replace("", None)
                                              if rows else _empty_table(qid))
    for k in [k for k in st.session_state if str(k).startswith("card_")]:
        del st.session_state[k]
    st.session_state["editor_version"] += 1


if "editor_version" not in st.session_state:
    _reset_form()


def collect_answers() -> dict:
    answers = {}
    for _, q in iter_questions():
        qid, t = q["id"], q["type"]
        if t == "table":
            answers[qid] = st.session_state.get(f"tbl_{qid}_out", [])
        elif t == "radio":
            answers[qid] = {"choice": st.session_state.get(f"q_{qid}"),
                            "detail": st.session_state.get(f"q_{qid}_detail", "")}
        elif t == "multi":
            answers[qid] = {"choices": st.session_state.get(f"q_{qid}", []),
                            "other": st.session_state.get(f"q_{qid}_other", "")}
        else:
            answers[qid] = st.session_state.get(f"q_{qid}")
    return answers


# --------------------------------------------------------------------------
# Widgets
# --------------------------------------------------------------------------

def render_cards(qid: str):
    """Phone layout: one bordered card per row, fields stacked vertically."""
    spec = TABLES[qid]
    keys = [k for k, _, _, _ in spec["columns"]]
    rows = st.session_state[f"cards_{qid}"]
    for i, row in enumerate(rows):
        with st.container(border=True):
            st.markdown(f"**Item {i + 1}**")
            for key, label, kind, options in spec["columns"]:
                wkey = f"card_{qid}_{row['_uid']}_{key}"
                if wkey not in st.session_state:
                    v = row.get(key) or None
                    st.session_state[wkey] = (v if v in options else None) if kind == "select" else (v or "")
                if kind == "select":
                    st.selectbox(label, options, key=wkey, placeholder="Choose")
                elif kind == "fixed":
                    st.markdown(f"*{row.get(key)}*")
                else:
                    st.text_input(label, key=wkey)
                row[key] = st.session_state.get(wkey)
            if st.button("Remove this item", key=f"rm_{qid}_{row['_uid']}"):
                rows.pop(i)
                st.rerun()
    if st.button("➕ Add item", key=f"add_{qid}"):
        rows.append({"_uid": uuid.uuid4().hex[:8]})
        st.rerun()
    st.session_state[f"tbl_{qid}_out"] = _clean_records(
        pd.DataFrame([{k: r.get(k) for k in keys} for r in rows], columns=keys))


def render_table(qid: str):
    if st.session_state.get("phone_mode"):
        render_cards(qid)
        return
    spec = TABLES[qid]
    config = {}
    for key, label, kind, options in spec["columns"]:
        if kind == "select":
            config[key] = st.column_config.SelectboxColumn(label, options=options, width="medium")
        elif kind == "fixed":
            config[key] = st.column_config.TextColumn(label, disabled=True, width="medium")
        else:
            config[key] = st.column_config.TextColumn(label, width="medium")
    edited = st.data_editor(
        st.session_state[f"tbl_{qid}"],
        column_config=config,
        num_rows="fixed" if "fixed_rows" in spec else "dynamic",
        hide_index=True,
        width="stretch",
        key=f"editor_{qid}_{st.session_state['editor_version']}",
    )
    st.session_state[f"tbl_{qid}_out"] = _clean_records(edited)
    if "fixed_rows" not in spec:
        st.caption("Click the **+** row at the bottom of the table to add items. "
                   "Select a row's checkbox and press the bin icon to delete it.")


def render_question(q: dict):
    qid, t, label = q["id"], q["type"], q["label"]
    key = f"q_{qid}"
    if t == "table":
        render_table(qid)
    elif t == "text":
        st.text_input(label, key=key)
    elif t == "textarea":
        st.text_area(label, key=key, height=90)
    elif t == "number":
        st.number_input(label, key=key, min_value=0.0, step=1.0, value=None,
                        placeholder="Leave blank if unknown")
    elif t == "radio":
        st.radio(label, q["options"], index=None, key=key, horizontal=True)
        if q.get("detail"):
            st.text_area(q["detail"], key=f"{key}_detail", height=70)
    elif t == "multi":
        limit = q.get("max_selections")
        st.multiselect(label, q["options"], key=key, max_selections=limit,
                       placeholder=f"Choose up to {limit}" if limit else "Choose any that apply")
        if OTHER in st.session_state.get(key, []):
            st.text_input("Other: please specify", key=f"{key}_other")


# --------------------------------------------------------------------------
# Sidebar: status + previous submissions
# --------------------------------------------------------------------------

with st.sidebar:
    st.markdown("#### Status")
    if storage_error:
        st.error(f"Storage not available: {storage_error}")
    else:
        st.success(f"Storage: {storage.describe()}")
    if email_configured()[0]:
        st.success("Email: on")

    st.markdown("#### Submissions")
    if st.button("Start a new submission", width="stretch"):
        _reset_form()
        st.rerun()

    previous = []
    if storage:
        try:
            previous = storage.list_latest()
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Could not list submissions: {exc}")
    if previous:
        options = {f"{r['submission_id']} · rev {r['revision']} · {r['submitter']} · "
                   f"{r['submitted_at_utc'][:16].replace('T', ' ')}": r for r in previous}
        choice = st.selectbox("Previous submissions (latest revision)", list(options), index=None)
        if choice:
            rec = options[choice]
            prev_answers = json.loads(rec["payload_json"])
            if st.button("Load to edit as new revision", width="stretch"):
                _reset_form(prev_answers, rec["submission_id"])
                st.session_state["q_submitter"] = rec["submitter"]
                st.session_state["q_submitter_role"] = rec.get("submitter_role", "")
                st.rerun()
            st.download_button("Download XLSX", build_xlsx(rec, prev_answers),
                               file_name=xlsx_filename(rec), width="stretch")
            if email_configured()[0]:
                st.caption(f"Email status: {rec.get('email_status') or '-'}")
    else:
        st.caption("No submissions yet.")


# --------------------------------------------------------------------------
# Main form
# --------------------------------------------------------------------------

st.markdown('<p class="audit-title">Daily Report & Dashboard: Getting Started</p>'
            '<p class="audit-sub">Al Wasl FC · medical & performance staff</p>',
            unsafe_allow_html=True)

editing = st.session_state.get("editing_submission_id")
if editing:
    st.info(f"Editing **{editing}**. Submitting will save a new revision; earlier "
            "revisions are kept unchanged.")

st.markdown(
    "We want to make the daily medical/performance report quicker to produce and "
    "easier to use, and to build a clear daily dashboard for the **doctor, physical "
    "coach and coach**. Your experience is the starting point. This form takes about "
    "**10 minutes**. Short answers are perfect, and anything you are unsure about can "
    "be left blank. We will go through it together afterwards."
)
with st.expander("How we will work: 4 short phases"):
    for phase, text in PHASES:
        st.markdown(f"**{phase}.** {text}")
st.markdown(f'<div class="privacy">🔒 {PRIVACY_NOTICE}</div>', unsafe_allow_html=True)
st.toggle("📱 Phone layout: fill the tables as simple cards", key="phone_mode",
          on_change=_switch_layout,
          help="Recommended on a phone. Your answers are kept when you switch.")

for section in SECTIONS:
    with st.expander(section["title"], expanded=True):
        if section["intro"]:
            st.caption(section["intro"])
        for q in section["questions"]:
            render_question(q)

st.divider()
st.markdown("### Submit")
c1, c2 = st.columns(2)
c1.text_input("Your name (submitter)", key="q_submitter")
c2.text_input("Your position", key="q_submitter_role")

answers = collect_answers()
findings = scan_answers(answers, LABELS)
if findings:
    st.warning("Some text looks like it may contain player-level medical data. "
               "Please check and remove it, or confirm it describes a process only:")
    for label, reason in findings:
        st.markdown(f"- *{label}*: {reason}")
    flagged_ok = st.checkbox("I have checked the flagged text: it describes processes, "
                             "not individual players.")
else:
    flagged_ok = True

privacy_ok = st.checkbox("I confirm this submission contains no player names, diagnoses, "
                         "injury details, VAS/RPE values, clinical notes or other "
                         "player-level medical data.", key="privacy_confirm")

submitter = (st.session_state.get("q_submitter") or "").strip()
role = (st.session_state.get("q_submitter_role") or "").strip()
blockers = []
if not submitter:
    blockers.append("enter your name")
if not privacy_ok:
    blockers.append("tick the privacy confirmation")
if not flagged_ok:
    blockers.append("review the flagged text")
if blockers:
    st.caption("To submit: " + ", ".join(blockers) + ".")

if st.button("Submit questionnaire", type="primary", disabled=bool(blockers)):
    if storage is None:
        record = build_record(None, submission_id=None, submitter=submitter,
                              submitter_role=role, answers=answers)
        record["email_status"] = "not sent: submission not saved"
        st.session_state["last_result"] = {"record": record, "saved": False,
                                           "save_error": f"storage not available: {storage_error}",
                                           "xlsx": build_xlsx(record, answers)}
    else:
        with st.spinner("Saving submission..."):
            record = build_record(storage, submission_id=editing, submitter=submitter,
                                  submitter_role=role, answers=answers)
            if not email_configured()[0]:
                record["email_status"] = "off"
            try:
                storage.save(record)
                saved, save_error = True, None
            except Exception as exc:  # noqa: BLE001
                saved, save_error = False, f"{type(exc).__name__}: {exc}"
        xlsx = build_xlsx(record, answers)
        if saved and not email_configured()[0]:
            email_ok, email_status = None, "off"
            st.session_state["editing_submission_id"] = record["submission_id"]
        elif saved:
            with st.spinner("Sending email..."):
                email_ok, email_status = send_xlsx(record, xlsx, xlsx_filename(record))
            try:
                storage.set_email_status(record["submission_id"], record["revision"], email_status)
            except Exception:  # noqa: BLE001 - email status is informational only
                pass
            st.session_state["editing_submission_id"] = record["submission_id"]
        else:
            email_ok, email_status = False, "not sent: submission not saved"
        record["email_status"] = email_status
        st.session_state["last_result"] = {"record": record, "saved": saved,
                                           "save_error": save_error, "email_ok": email_ok,
                                           "xlsx": xlsx}

result = st.session_state.get("last_result")
if result:
    rec = result["record"]
    if result["saved"]:
        st.success(f"Thank you! Saved as **{rec['submission_id']}**, revision "
                   f"**{rec['revision']}** ({rec['submitted_at_utc'][:16].replace('T', ' ')} UTC). "
                   "You can download a copy below.")
        if result.get("email_ok"):
            st.success(f"Email {rec['email_status']}.")
        elif result.get("email_ok") is False:
            st.warning(f"Email {rec['email_status']}. The submission is saved; "
                       "use the download button below.")
    elif result.get("save_error"):
        st.error(f"The submission was NOT saved ({result['save_error']}). "
                 "Download the XLSX as a backup and contact the administrator.")
    st.download_button("Download XLSX", result["xlsx"], file_name=xlsx_filename(rec),
                       type="primary")
