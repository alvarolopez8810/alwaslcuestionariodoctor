# Medical & Performance Reporting Workflow Audit

A small Streamlit app for Al Wasl FC. The medical department fills in a
**process questionnaire**. It records what reports exist, who owns, reviews
and receives them, how they are defined, checked, stored and shared, and what
a future daily data-entry workflow needs.

> **Process audit only.** The app does not ask for, and must never store,
> player names, diagnoses, injury details, VAS/RPE values, clinical notes or
> any other player-level medical data. The privacy notice sits at the top
> of the form. A required confirmation checkbox and a text guard block
> submission until the submitter checks anything that looks player-level,
> such as "VAS 7" or injury terms. The guard is a safety net and cannot catch
> everything (player names especially), so the notice stays the primary
> control.

This app is **independent** of the live Doctor Input Dash app
(`alwasl_workflow`). It shares nothing with it at runtime and does not change it.

---

## 1. What is in the questionnaire

| # | Section | Format |
|---|---|---|
| 1 | Report inventory | Repeatable rows: name, type, owner, reviewer, audience, source, format, cadence, cut-off, storage, access level, created/received/updated, notes |
| 2 | Department roles and deputies | Repeatable rows + cover/handover questions |
| 3 | Definitions and populations | Roster, attendance, unique players vs attendance events, AM/PM and repeat entries, availability, VAS/RPE definitions, load metrics, source of truth |
| 4 | Data quality checks and approval | |
| 5 | File naming, versioning, correction, archive | |
| 6 | Storage locations and channels | Incl. shared folders, email, WhatsApp, and whether the Doctor Input workbook is still used and what replaced it |
| 7 | Access boundaries | Audience × access-level matrix, what may go to the sporting director, what stays restricted |
| 8 | Reporting workload and manual work | |
| 9 | Future daily data-entry workflow | |
| 10 | Sign-off | |

Dropdowns are **suggestions only**: nothing is preselected, and every
choice list has an **Other** route with a free-text field. The whole
questionnaire is defined in `audit/questions.py`. Edit that one file to
change wording or options. Answers are keyed by stable question IDs, so
older submissions still export correctly.

## 2. Run locally

```bash
cd MEDICAL_PROCESS_AUDIT
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env          # then edit .env (gitignored)
set -a; source .env; set +a   # load the variables into this shell

.venv/bin/streamlit run app.py   # http://localhost:8501
```

For a quick local review without a password, use
`AUDIT_ALLOW_NO_AUTH=1 .venv/bin/streamlit run app.py`. The app shows a
warning banner in this mode, and it is ignored on Render.

Tests:

```bash
.venv/bin/python -m pytest -q
```

## 3. Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `AUDIT_APP_PASSWORD` | **Yes, for any hosted use** | Shared access password. Without it the app stays locked (except local no-auth mode). |
| `AUDIT_ALLOW_NO_AUTH` | No | `1` turns the login off for **local review only**. Ignored when `RENDER` is set. |
| `AUDIT_STORAGE_BACKEND` | No | `sql` (default) or `sheets`. |
| `AUDIT_DATABASE_URL` | Hosted `sql` | SQLAlchemy URL, e.g. `postgresql://…`. Empty locally = SQLite at `~/.alwasl_process_audit/submissions.db`. |
| `AUDIT_SHEET_ID` | `sheets` | Google Sheet ID that receives the `AUDIT SUBMISSIONS` worksheet. |
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | `sheets` (hosted) | Full service-account JSON as one env var. |
| `GOOGLE_SHEETS_CREDENTIALS_FILE` | `sheets` (local) | Path to the service-account JSON key, kept outside the repo. |
| `AUDIT_EMAIL_TO` | For email | Comma-separated recipient list. |
| `SMTP_HOST` | For email | SMTP server. |
| `SMTP_PORT` | No | Default `587`. |
| `SMTP_SECURITY` | No | `starttls` (default), `ssl` or `none`. |
| `SMTP_USER` / `SMTP_PASSWORD` | Usually | SMTP login (use an app password, not a personal one). |
| `SMTP_FROM` | For email | Sender address (defaults to `SMTP_USER`). |

No address, password or key is hard-coded anywhere in the code.

## 4. Data storage

Submissions are **never** written to the Git repository or to the web
server's disk on Render, because Render's filesystem is wiped on every
deploy and restart.

- **SQL (recommended for hosting):** a managed Postgres database, e.g. a
  Render Postgres instance. The `audit_submissions` table is created
  automatically on first start. On Render, the app refuses to use SQLite.
- **Google Sheets:** reuses the club's service-account pattern. Share the
  target sheet with the service account's email as *Editor*. Use a
  **separate** spreadsheet from the Doctor Input sheet so the two stay
  independent.
- **Local review:** SQLite in `~/.alwasl_process_audit/` (outside the repo).

Every row stores `submission_id`, `revision`, `submitter`,
`submitter_role`, `submitted_at_utc` (UTC, ISO-8601), `email_status` and
`payload_json` (all answers).

**Revisions are append-only.** In the sidebar, *Previous submissions →
Load to edit as new revision* reloads a submission. Submitting it saves
revision *n+1* under the same submission ID. Earlier revisions are never
overwritten. The only field updated after insert is that row's
`email_status`.

## 5. Export and email behaviour

After each submission:

1. The submission is **saved first**.
2. An XLSX is built with two tabs:
   - **Report Inventory**: one row per inventory item, with submission ID and revision.
   - **Audit Answers**: metadata (ID, revision, submitter, UTC timestamp),
     then every question by section. Unanswered questions show "(no answer)".
3. The XLSX is emailed to `AUDIT_EMAIL_TO`.
4. A **Download XLSX** button appears on the page.

If email settings are missing or sending fails, the submission stays saved.
The page shows the exact email status, which is also stored in
`email_status`, and the download button still works. If storage itself
fails, the page says clearly that the submission was **not** saved and
offers the XLSX as a backup.

You can download the XLSX of any previous submission from the sidebar.

## 6. Sample data

`samples/sample_submission_1.json` (complete) and
`samples/sample_submission_2.json` (partial, uses "Other") are **fictional,
process-only** test submissions. They contain invented staff roles and no
player data.

```bash
# Save both samples to the configured storage (+ a revision 2 of sample 1)
# and write their XLSX files to samples/exports/
.venv/bin/python scripts/load_samples.py

# Only build the XLSX files, without touching storage
.venv/bin/python scripts/load_samples.py --export-only
```

The two committed `samples/exports/SAMPLE_*.xlsx` files show the export
format. Other exports are gitignored.

## 7. Deployment notes (not deployed yet)

Review the app locally before you deploy. When ready:

1. In Render, create a **Postgres** database and a **Web Service** from
   this repository. `render.yaml` is a reviewed blueprint for both. It is
   not applied unless you choose *New → Blueprint*.
2. Build: `pip install -r requirements.txt`.
   Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.
3. In *Environment*, set `AUDIT_APP_PASSWORD` (strong, shared only with
   the doctor and reviewers), `AUDIT_DATABASE_URL` (Render's *Internal*
   connection string), and the SMTP variables if you want email.
4. Without `AUDIT_APP_PASSWORD` the hosted app stays locked, and without
   durable storage it refuses to save. Neither failure is silent.
5. After deploy, run one fictional test submission and confirm the row in
   the database and the email.

Security notes:

- The password gate is a shared-password gate for a small internal
  audience. Add an identity layer (SSO or a Cloudflare Access / Render
  private service) if the audience grows.
- The GitHub repository is **public**. It holds code and fictional samples
  only. Never commit `.env`, keys or real exports (`.gitignore` covers
  these).
- Email carries the XLSX of process answers only. The questionnaire holds
  no player-level medical data, so none can be emailed.

## 8. Project layout

```
app.py                  Streamlit UI (login, form, submit, sidebar history)
audit/questions.py      Questionnaire definition: single source of truth
audit/storage.py        SQL / Google Sheets backends, IDs, revisions
audit/export.py         XLSX builder (Report Inventory + Audit Answers)
audit/emailer.py        SMTP sender driven by env vars, returns a status
audit/privacy.py        Privacy notice + player-level text guard
audit/auth.py           Password gate
samples/                Fictional test submissions + sample XLSX
scripts/load_samples.py Load samples / build sample exports
tests/                  pytest suite
render.yaml             Render blueprint (not applied automatically)
```
