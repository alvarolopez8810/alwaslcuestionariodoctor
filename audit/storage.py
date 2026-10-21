"""
Durable submission storage.

Two backends, chosen with AUDIT_STORAGE_BACKEND:

  sheets  Google Sheets (worksheet "AUDIT SUBMISSIONS" in AUDIT_SHEET_ID).
          Same service-account mechanism as the Doctor Input app:
          GOOGLE_SHEETS_CREDENTIALS_JSON (full JSON in an env var, for Render)
          or GOOGLE_SHEETS_CREDENTIALS_FILE (path, for local).
  sql     Any SQLAlchemy URL in AUDIT_DATABASE_URL: a managed Postgres for
          hosting, or SQLite for local review. The default SQLite file lives
          in ~/.alwasl_process_audit/, outside the Git repository.

Submissions are append-only: editing a submission creates a new revision
row with the same submission_id and revision + 1. Nothing is overwritten
except the email-status column of the row it belongs to.

On Render (RENDER env var set) a local SQLite file would be lost on every
deploy/restart, so it is refused there.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

HEADERS = [
    "submission_id", "revision", "submitter", "submitter_role",
    "submitted_at_utc", "email_status", "payload_json",
]
WORKSHEET_TITLE = "AUDIT SUBMISSIONS"
DEFAULT_SQLITE = Path.home() / ".alwasl_process_audit" / "submissions.db"


class StorageError(RuntimeError):
    pass


def new_submission_id() -> str:
    return "AUD-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------
# SQL backend
# --------------------------------------------------------------------------

class SqlStorage:
    name = "sql"

    def __init__(self, url: str | None = None):
        from sqlalchemy import (Column, Integer, MetaData, String, Table, Text,
                                UniqueConstraint, create_engine)

        url = url or os.environ.get("AUDIT_DATABASE_URL")
        if not url:
            if os.environ.get("RENDER"):
                raise StorageError(
                    "AUDIT_DATABASE_URL is not set. A local SQLite file is not durable "
                    "on Render; use a managed Postgres URL or AUDIT_STORAGE_BACKEND=sheets.")
            DEFAULT_SQLITE.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{DEFAULT_SQLITE}"
        if url.startswith("postgres://"):  # Render/Heroku style URL
            url = "postgresql://" + url[len("postgres://"):]
        if os.environ.get("RENDER") and url.startswith("sqlite"):
            raise StorageError("SQLite is not durable on Render. Use Postgres or Google Sheets.")

        self.url = url
        self.engine = create_engine(url, future=True, pool_pre_ping=True)
        meta = MetaData()
        self.table = Table(
            "audit_submissions", meta,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("submission_id", String(40), nullable=False, index=True),
            Column("revision", Integer, nullable=False),
            Column("submitter", String(200), nullable=False),
            Column("submitter_role", String(200)),
            Column("submitted_at_utc", String(40), nullable=False),
            Column("email_status", String(500)),
            Column("payload_json", Text, nullable=False),
            UniqueConstraint("submission_id", "revision", name="uq_submission_revision"),
        )
        meta.create_all(self.engine)

    def describe(self) -> str:
        if self.url.startswith("sqlite"):
            return f"SQLite (local review only): {self.url.removeprefix('sqlite:///')}"
        return "SQL database (" + self.url.split("://", 1)[0] + ")"

    def next_revision(self, submission_id: str) -> int:
        from sqlalchemy import func, select
        with self.engine.connect() as conn:
            current = conn.execute(
                select(func.max(self.table.c.revision))
                .where(self.table.c.submission_id == submission_id)).scalar()
        return (current or 0) + 1

    def save(self, record: dict) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.table.insert().values(**{h: record.get(h) for h in HEADERS}))

    def set_email_status(self, submission_id: str, revision: int, status: str) -> None:
        t = self.table
        with self.engine.begin() as conn:
            conn.execute(t.update()
                         .where(t.c.submission_id == submission_id, t.c.revision == revision)
                         .values(email_status=status))

    def list_latest(self) -> list[dict]:
        from sqlalchemy import select
        with self.engine.connect() as conn:
            rows = conn.execute(select(*[self.table.c[h] for h in HEADERS])
                                .order_by(self.table.c.id)).mappings().all()
        return _latest_per_submission([dict(r) for r in rows])

    def get(self, submission_id: str, revision: int | None = None) -> dict | None:
        from sqlalchemy import select
        t = self.table
        q = select(*[t.c[h] for h in HEADERS]).where(t.c.submission_id == submission_id)
        q = q.where(t.c.revision == revision) if revision else q.order_by(t.c.revision.desc())
        with self.engine.connect() as conn:
            row = conn.execute(q).mappings().first()
        return dict(row) if row else None


# --------------------------------------------------------------------------
# Google Sheets backend
# --------------------------------------------------------------------------

class SheetsStorage:
    name = "sheets"
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self):
        import gspread
        from google.oauth2.service_account import Credentials

        sheet_id = os.environ.get("AUDIT_SHEET_ID")
        if not sheet_id:
            raise StorageError("AUDIT_SHEET_ID is not set.")
        json_env = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
        file_env = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE")
        if json_env:
            creds = Credentials.from_service_account_info(json.loads(json_env), scopes=self.SCOPES)
        elif file_env and Path(file_env).exists():
            creds = Credentials.from_service_account_file(file_env, scopes=self.SCOPES)
        else:
            raise StorageError("Set GOOGLE_SHEETS_CREDENTIALS_JSON or GOOGLE_SHEETS_CREDENTIALS_FILE.")

        sh = gspread.authorize(creds).open_by_key(sheet_id)
        try:
            self.ws = sh.worksheet(WORKSHEET_TITLE)
        except gspread.WorksheetNotFound:
            self.ws = sh.add_worksheet(WORKSHEET_TITLE, rows=1000, cols=len(HEADERS))
        if self.ws.row_values(1) != HEADERS:
            if any(self.ws.row_values(1)):
                raise StorageError(f"Worksheet '{WORKSHEET_TITLE}' has unexpected headers.")
            self.ws.update(range_name="A1", values=[HEADERS])

    def describe(self) -> str:
        return f"Google Sheets (worksheet '{WORKSHEET_TITLE}')"

    def _rows(self) -> list[dict]:
        rows = self.ws.get_all_records(expected_headers=HEADERS)
        for r in rows:
            r["revision"] = int(r["revision"])
        return rows

    def next_revision(self, submission_id: str) -> int:
        revs = [r["revision"] for r in self._rows() if r["submission_id"] == submission_id]
        return max(revs, default=0) + 1

    def save(self, record: dict) -> None:
        self.ws.append_row([record.get(h, "") for h in HEADERS],
                           value_input_option="RAW", insert_data_option="INSERT_ROWS")

    def set_email_status(self, submission_id: str, revision: int, status: str) -> None:
        col_sid = self.ws.col_values(1)
        col_rev = self.ws.col_values(2)
        for i, (sid, rev) in enumerate(zip(col_sid, col_rev), start=1):
            if sid == submission_id and str(rev) == str(revision):
                self.ws.update_cell(i, HEADERS.index("email_status") + 1, status)
                return

    def list_latest(self) -> list[dict]:
        return _latest_per_submission(self._rows())

    def get(self, submission_id: str, revision: int | None = None) -> dict | None:
        rows = [r for r in self._rows() if r["submission_id"] == submission_id]
        if revision:
            rows = [r for r in rows if r["revision"] == revision]
        return max(rows, key=lambda r: r["revision"]) if rows else None


# --------------------------------------------------------------------------

def _latest_per_submission(rows: list[dict]) -> list[dict]:
    latest: dict[str, dict] = {}
    for r in rows:
        cur = latest.get(r["submission_id"])
        if cur is None or r["revision"] > cur["revision"]:
            latest[r["submission_id"]] = r
    return sorted(latest.values(), key=lambda r: r["submitted_at_utc"], reverse=True)


def get_storage():
    backend = os.environ.get("AUDIT_STORAGE_BACKEND", "sql").strip().lower()
    if backend == "sheets":
        return SheetsStorage()
    if backend == "sql":
        return SqlStorage()
    raise StorageError(f"Unknown AUDIT_STORAGE_BACKEND '{backend}' (use 'sql' or 'sheets').")


def build_record(storage, *, submission_id: str | None, submitter: str,
                 submitter_role: str, answers: dict) -> dict:
    """Assign ID/revision/timestamp. A None submission_id starts a new submission."""
    sid = submission_id or new_submission_id()
    revision = storage.next_revision(sid) if submission_id else 1
    return {
        "submission_id": sid,
        "revision": revision,
        "submitter": submitter,
        "submitter_role": submitter_role,
        "submitted_at_utc": now_utc_iso(),
        "email_status": "pending",
        "payload_json": json.dumps(answers, ensure_ascii=False),
    }
