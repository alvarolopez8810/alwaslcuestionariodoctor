"""
Questionnaire definition: the single source of truth for the form, storage
payload and XLSX export. Each question has a stable `id`; answers are stored
under that id, so wording can be improved later without breaking old
submissions.

Question types
--------------
text       single-line text
textarea   multi-line text
number     non-negative number
radio      one choice from `options` (+ optional free-text detail box)
multi      several choices from `options`; "Other" reveals a free-text box
table      repeatable rows (see TABLES below)

Options are *suggestions*, never prefilled answers. Every choice question
has an "Other" route or a detail box so nothing is forced into a category.
"""

OTHER = "Other"

# --------------------------------------------------------------------------
# Repeatable tables
# --------------------------------------------------------------------------

REPORT_TYPE_SUGGESTIONS = [
    "Daily availability report",
    "Daily attendance report",
    "Training load / GPS report",
    "Wellness / readiness questionnaire summary",
    "RPE / session-RPE summary",
    "Injury & illness log (department-level)",
    "Rehab / return-to-play progress report",
    "Pre-match availability list",
    "Weekly medical summary",
    "Monthly / season medical summary",
    "Physical testing report",
    "Body composition report",
    "Medical screening / pre-season report",
    "Doctor Input workbook",
    "Imaging / scan files",
    "Treatment / physio session log",
    "Supplement / medication log",
    "Travel / away-trip medical pack",
    "Data export from vendor platform",
    "Form / questionnaire (paper or digital)",
    OTHER,
]

SOURCE_SUGGESTIONS = [
    "Manual entry (Excel)",
    "Manual entry (paper)",
    "Doctor Input app / Google Sheet",
    "GPS / tracking system",
    "Wellness / RPE app",
    "Medical record system (EMR)",
    "Imaging provider",
    "Email from another department",
    "WhatsApp message",
    "Coaching staff",
    "External provider / hospital",
    OTHER,
]

FORMAT_SUGGESTIONS = [
    "XLSX / XLSM", "CSV", "PDF", "Word", "PowerPoint", "Google Sheet",
    "Image (JPG/PNG)", "DICOM / imaging", "Web dashboard",
    "WhatsApp text", "Email body", "Paper", OTHER,
]

CADENCE_SUGGESTIONS = [
    "Per session", "Daily", "Match day", "Weekly", "Monthly",
    "Per injury / event", "Pre-season", "End of season", "Ad hoc", OTHER,
]

ACCESS_LEVEL_SUGGESTIONS = [
    "Medical staff only",
    "Medical + performance staff",
    "Medical + coaching staff",
    "Shared with sporting director",
    "Club-wide (internal)",
    "External (league / federation / provider)",
    "Not defined",
    OTHER,
]

ROLE_SUGGESTIONS = [
    "Head of Medical / Team Doctor",
    "Doctor",
    "Physiotherapist",
    "Rehab coach",
    "Sports scientist",
    "Strength & conditioning coach",
    "Performance / data analyst",
    "Nutritionist",
    "Massage therapist",
    "Team manager / administration",
    OTHER,
]

# Each table: id -> spec. `columns` is an ordered list of
# (key, label, kind, options) where kind is "text" or "select".
TABLES = {
    "report_inventory": {
        "columns": [
            ("report_name", "Report name", "text", None),
            ("report_type", "Report type", "select", REPORT_TYPE_SUGGESTIONS),
            ("owner", "Owner (role or staff name)", "text", None),
            ("reviewer", "Reviewer", "text", None),
            ("audience", "Audience / recipients", "text", None),
            ("source", "Source system", "select", SOURCE_SUGGESTIONS),
            ("format", "File format", "select", FORMAT_SUGGESTIONS),
            ("cadence", "Cadence", "select", CADENCE_SUGGESTIONS),
            ("deadline", "Cut-off / deadline", "text", None),
            ("storage", "Approved storage location", "text", None),
            ("access_level", "Access level", "select", ACCESS_LEVEL_SUGGESTIONS),
            ("direction", "Created / received / updated", "select",
             ["Created", "Received", "Updated", "Created + updated", OTHER]),
            ("notes", "Notes (incl. detail for 'Other')", "text", None),
        ],
        "min_rows": 1,
    },
    "roles": {
        "columns": [
            ("role", "Role / function", "select", ROLE_SUGGESTIONS),
            ("person", "Person (staff name or job title)", "text", None),
            ("deputy", "Deputy / cover", "text", None),
            ("responsibilities", "Reporting responsibilities", "text", None),
            ("notes", "Notes (incl. detail for 'Other')", "text", None),
        ],
        "min_rows": 1,
    },
}


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
# Phase 1 discovery: short (~10 minutes). Detailed access rules, sign-off and
# full definitions are deliberately left for Phase 4, once the dashboard
# prototype and workflow are agreed.

STAFF_GROUPS = ["Doctor", "Physiotherapists", "Physical coach / S&C", "Sports scientist",
                "Coaching staff", "Players (via wellness app)", OTHER]

SECTIONS = [
    {
        "id": "s1",
        "title": "1. Your current reports",
        "intro": (
            "Start with the daily report(s). Add other regular reports if you find it useful. "
            "One row per report; describe the report, not its contents. Dropdowns are "
            "suggestions; choose 'Other' and add a note if nothing fits."
        ),
        "questions": [
            {"id": "report_inventory", "type": "table",
             "label": "Reports the department prepares"},
            {"id": "inventory_missing", "type": "textarea",
             "label": "Anything you could not describe above, or someone else who would know? "
                      "(optional)"},
        ],
    },
    {
        "id": "s2",
        "title": "2. Roles and deputies",
        "intro": "Who does what for reporting, and who covers when they are away.",
        "questions": [
            {"id": "roles", "type": "table", "label": "Roles and deputies"},
            {"id": "cover_gap", "type": "textarea",
             "label": "What happens when both the owner and the deputy are "
                      "unavailable (holiday, away trip, illness)?"},
            {"id": "handover", "type": "textarea",
             "label": "How is a handover done between staff (written note, "
                      "message, meeting, nothing formal)?"},
        ],
    },
    {
        "id": "s3",
        "title": "3. Who provides, prepares and reviews the daily report",
        "intro": "A quick picture of the daily flow.",
        "questions": [
            {"id": "info_providers", "type": "multi",
             "label": "Who provides the information?", "options": STAFF_GROUPS},
            {"id": "report_preparer", "type": "text",
             "label": "Who prepares the daily report? (role)"},
            {"id": "report_reviewer", "type": "text",
             "label": "Who reviews it before it is shared? (role, or 'nobody')"},
        ],
    },
    {
        "id": "s4",
        "title": "4. Timing",
        "intro": "When information goes in and when the report is needed.",
        "questions": [
            {"id": "entry_time", "type": "radio",
             "label": "When is the information usually entered?",
             "options": ["Before the morning session", "Within 1 hour after the session",
                         "End of the day", "Varies", OTHER],
             "detail": "Optional comment"},
            {"id": "ready_time", "type": "radio",
             "label": "When should the report be ready?",
             "options": ["Before training", "Before the staff / coaches' meeting",
                         "Same day, after training", "Next morning", "Varies", OTHER],
             "detail": "Optional comment (e.g. a specific time)"},
        ],
    },
    {
        "id": "s5",
        "title": "5. The daily dashboard",
        "intro": "What a clearer, more useful daily dashboard should show.",
        "questions": [
            {"id": "dashboard_top", "type": "multi", "max_selections": 3,
             "label": "Which information should be visible at the top of the daily "
                      "dashboard? Choose up to three.",
             "options": ["Player availability", "Attendance", "Players with a complaint",
                         "Players in rehabilitation", "Wellness flags",
                         "Doctor's comment and recommendation", "Training modifications",
                         "Physical-load summary", "Follow-up actions", OTHER]},
            {"id": "medical_comment", "type": "multi",
             "label": "What should the daily medical comment communicate?",
             "options": ["What happened", "Why it matters", "What action is recommended",
                         "Who should act", "By when", OTHER]},
            {"id": "medical_comment_note", "type": "text",
             "label": "Optional comment on the medical comment format"},
            {"id": "needs_doctor", "type": "text",
             "label": "What does the doctor need the dashboard to show?"},
            {"id": "needs_physical_coach", "type": "text",
             "label": "What does the physical coach need the dashboard to show?"},
            {"id": "needs_coach", "type": "text",
             "label": "What does the coach need the dashboard to show?"},
        ],
    },
    {
        "id": "s6",
        "title": "6. Counts and definitions",
        "intro": "Which numbers need a clear definition so everyone reads the report the same way.",
        "questions": [
            {"id": "definitions_needed", "type": "multi",
             "label": "Which counts or definitions need to be clearer?",
             "options": ["Attendance", "Availability", "Rehabilitation",
                         "Players with a complaint", "Training modifications",
                         "AM/PM or repeat entries", "Physical load", OTHER]},
            {"id": "definitions_note", "type": "textarea",
             "label": "Briefly, how are these counted today? (optional)"},
        ],
    },
    {
        "id": "s7",
        "title": "7. Storage and sharing",
        "intro": "Where the report lives and how it reaches people.",
        "questions": [
            {"id": "storage", "type": "multi",
             "label": "Where are the report and its source files stored?",
             "options": ["Shared folder", "OneDrive / SharePoint", "Google Drive", "Email",
                         "WhatsApp", "Local laptop / USB", "Printed copies", OTHER]},
            {"id": "sharing", "type": "multi",
             "label": "How is the report shared?",
             "options": ["Email", "WhatsApp", "Shared folder link", "Printed",
                         "Presented in the staff meeting", OTHER]},
            {"id": "storage_note", "type": "text", "label": "Optional comment"},
        ],
    },
    {
        "id": "s8",
        "title": "8. Biggest improvement",
        "intro": "",
        "questions": [
            {"id": "one_change", "type": "textarea",
             "label": "What one change would save the department the most time, or "
                      "improve the report the most?"},
        ],
    },
    {
        "id": "s9",
        "title": "9. Prototype feedback",
        "intro": "We will build a first dashboard prototype from one sample report.",
        "questions": [
            {"id": "prototype_reviewers", "type": "multi",
             "label": "Who should review the first dashboard prototype?",
             "options": ["Doctor", "Physiotherapist", "Physical coach", "Head coach",
                         "Assistant coach", OTHER]},
            {"id": "prototype_note", "type": "text",
             "label": "Optional comment (e.g. best time for a 20-minute review)"},
        ],
    },
]

PHASES = [
    ("Phase 1", "Understand the current daily report and what each staff group needs (this form)."),
    ("Phase 2", "Build a visual dashboard prototype from one sample report."),
    ("Phase 3", "Review it with the doctor, physical coach and coach: what is clear, missing or misleading."),
    ("Phase 4", "Agree the data-entry workflow, responsibilities, storage and access rules."),
]


def iter_questions():
    """Yield (section, question) pairs in display order."""
    for section in SECTIONS:
        for q in section["questions"]:
            yield section, q


def table_column_labels(table_id: str) -> list[str]:
    return [label for _, label, _, _ in TABLES[table_id]["columns"]]
