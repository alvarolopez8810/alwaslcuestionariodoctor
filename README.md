# Daily Report & Dashboard Discovery

A short Streamlit form for Al Wasl FC. It is **Phase 1** of improving the
daily medical/performance report and building a clearer daily dashboard for
the **doctor, physical coach and coach**. It takes about 10 minutes. It is a
practical starting conversation, not a compliance audit.

| Phase | Goal |
|---|---|
| 1 | Understand the current daily report and what each staff group needs (this form) |
| 2 | Build a visual dashboard prototype from one sample report |
| 3 | Review it with the doctor, physical coach and coach: what is clear, missing or misleading |
| 4 | Agree the data-entry workflow, responsibilities, storage and access rules |

> **Process only, never player data.** The form does not ask for, and must
> never store, player names, diagnoses, injury details, VAS/RPE values,
> clinical notes or any other player-level medical data. The notice sits at
> the top of the form. A required confirmation checkbox and a text guard
> block submission until the submitter checks anything that looks
> player-level, such as "VAS 7" or injury terms. Medical data needs and access
> rules are left for Phase 4.

This app is **independent** of the live Doctor Input Dash app
(`alwasl_workflow`). It shares nothing with it at runtime.

---

## 1. What the form asks

| # | Section | Format |
|---|---|---|
| 1 | Your current reports | Repeatable rows (name, type, owner, reviewer, audience, source, format, cadence, cut-off, storage, access level, notes) |
| 2 | Roles and deputies | Repeatable rows + cover/handover questions |
| 3 | Who provides, prepares and reviews the daily report | Choices + two short fields |
| 4 | Timing | When information is entered / when the report must be ready (choice + optional comment) |
| 5 | The daily dashboard | Top-of-dashboard items (**max 3**), what the medical comment should communicate, one short need each for doctor / physical coach / coach |
| 6 | Counts and definitions | Which need to be clearer (attendance, availability, rehab...) |
| 7 | Storage and sharing | Choices + optional comment |
| 8 | Biggest improvement | One change |
| 9 | Prototype feedback | Who should review the first prototype |

Options are **suggestions only**: nothing is preselected, and choice lists
include **Other** with a free-text field. The form is defined in
`audit/questions.py`. Edit that one file to change wording or options.
Answers are keyed by stable question IDs, so older submissions still export
(questions that no longer exist are simply not shown).

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
   - **Report Inventory**: one row per report.
   - **Audit Answers**: submission ID, revision, submitter and UTC time at the
     top, then one row per question (Section, Question, Answer). Unanswered
     questions show "-".
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

## 7. Deployment (Render + Google Sheets, no email)

Chosen setup: **Google Sheets** storage (free, durable, same service account
as the Doctor Input app), Render **free** web service, **email off**. The
doctor tells Álvaro when the form is submitted, and answers are read from
the Sheet or downloaded as XLSX from the app's sidebar.

**A. Google Sheet**

1. Create a new, blank Google Sheet, e.g. *Daily Report Discovery - Responses*.
   Use a separate file, not the Doctor Input sheet.
2. Share it as **Editor** with the service account
   `medical-workflow@alwasl-503211.iam.gserviceaccount.com`.
3. Copy the Sheet ID from the URL (`/spreadsheets/d/<SHEET_ID>/edit`).
4. The app creates the `AUDIT SUBMISSIONS` worksheet and its header row on
   first start. `sheet_template/AUDIT_SUBMISSIONS_headers.csv` holds the same
   headers if you prefer to import them by hand.

**B. Render web service** (or *New → Blueprint* with `render.yaml`)

1. *New → Web Service* → connect `alvarolopez8810/alwaslcuestionariodoctor`, branch `main`.
2. Runtime *Python*, plan *Free*.
   Build: `pip install -r requirements.txt`.
   Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`.
3. Environment variables:

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.7` |
| `AUDIT_APP_PASSWORD` | a strong password, shared only with the doctor and reviewers |
| `AUDIT_STORAGE_BACKEND` | `sheets` |
| `AUDIT_SHEET_ID` | the Sheet ID from step A3 |
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | the same value as in the Doctor Input Render service (the full service-account JSON) |

   Leave all `SMTP_*` / `AUDIT_EMAIL_TO` unset: email stays off and the UI
   does not mention it.
4. After the first deploy, open the URL, sign in, send one test submission
   and check the new row in the Sheet.

**Notes**

- On the free plan the service sleeps after ~15 minutes idle. The first
  visit after that takes about 30-60 seconds to load. Answers are not
  affected, because they live in the Sheet.
- The Sheet stores answers as JSON in `payload_json` (one row per
  submission revision). For reading, use the XLSX download in the app's
  sidebar.
- **Phone use:** turn on *Phone layout* at the top of the form. The two
  tables then become simple cards (one field per line, *Add item* /
  *Remove this item*). Answers are kept when switching layouts.

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
sheet_template/         Header row for the Google Sheet (optional manual import)
```
