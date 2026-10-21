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

ACCESS_MATRIX_LEVELS = [
    "Full clinical detail",
    "Availability status + expected return",
    "Availability status only",
    "Team-level aggregates only",
    "No access",
    "Not defined",
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
    "access_matrix": {
        # Rows are a fixed list of audiences (structure, not answers):
        # the access-level column always starts empty.
        "columns": [
            ("audience", "Audience", "fixed", None),
            ("access", "Access level", "select", ACCESS_MATRIX_LEVELS),
            ("channel", "How they receive it", "text", None),
            ("notes", "Notes / conditions", "text", None),
        ],
        "fixed_rows": [
            "Medical staff",
            "Performance / S&C staff",
            "Head coach",
            "Assistant coaches / analysts",
            "Sporting director",
            "Club management / CEO",
            "Team manager / administration",
            "External (league, federation, insurer)",
        ],
    },
}

# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------

SECTIONS = [
    {
        "id": "s1",
        "title": "1. Report inventory",
        "intro": (
            "List every report, spreadsheet, image, export or form the department "
            "creates, receives or updates. One row per item. Use the dropdowns as "
            "suggestions; if nothing fits choose 'Other' and explain in Notes. "
            "Describe the report, not its contents: no player names or results."
        ),
        "questions": [
            {"id": "report_inventory", "type": "table",
             "label": "Report inventory"},
            {"id": "inventory_missing", "type": "textarea",
             "label": "Are there items you know exist but could not describe above "
                      "(e.g. owned by another department)? Who would know?"},
        ],
    },
    {
        "id": "s2",
        "title": "2. Department roles and deputies",
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
        "title": "3. Definitions and populations",
        "intro": (
            "How the department defines and counts things. Describe the rule, "
            "not any player's values. Do not enter any VAS or RPE scores."
        ),
        "questions": [
            {"id": "roster_population", "type": "multi",
             "label": "Who is included when you report roster size?",
             "options": ["First-team registered players", "Youth players training with first team",
                         "Trialists", "Players out on loan", "Long-term injured players",
                         "Players on international duty", OTHER]},
            {"id": "roster_definition", "type": "textarea",
             "label": "Describe the roster-size rule in your own words, including "
                      "when it changes (e.g. registration deadline, call-ups)."},
            {"id": "attendance_definition", "type": "textarea",
             "label": "How do you define attendance? (e.g. present at the session, "
                      "completed the full session, partial participation)"},
            {"id": "unique_vs_events", "type": "radio",
             "label": "When you report attendance, what do you count?",
             "options": ["Unique players", "Attendance events (player-sessions)",
                         "Both, reported separately", "Not defined / varies"],
             "detail": "Explain, with a fictional example if helpful."},
            {"id": "ampm_counting", "type": "radio",
             "label": "On a day with AM and PM sessions, how is a player counted?",
             "options": ["Once per session (can count twice per day)", "Once per day",
                         "Depends on the report", "Not defined"],
             "detail": "Which reports use which rule?"},
            {"id": "repeat_entries", "type": "textarea",
             "label": "If the same player is entered twice for the same session "
                      "(duplicate or correction), which entry counts and how is the "
                      "other removed or flagged?"},
            {"id": "availability_categories", "type": "multi",
             "label": "Which availability categories do you use?",
             "options": ["Available", "Available with restrictions / modified training",
                         "Individual / rehab training", "Unavailable", "Doubtful",
                         "Illness", "Not with the team (personal / international)", OTHER]},
            {"id": "availability_definition", "type": "textarea",
             "label": "Define each availability category and who decides the status "
                      "(and by what time each day)."},
            {"id": "vas_definition", "type": "textarea",
             "label": "VAS: which scale is used (e.g. 0-10), what question is asked, "
                      "when it is collected and by whom? (Definition only, no values.)"},
            {"id": "rpe_scale", "type": "radio",
             "label": "RPE: which scale is used?",
             "options": ["CR-10 (0-10)", "Borg 6-20", "Not collected", OTHER],
             "detail": "When is RPE collected after the session, and how is session-RPE "
                       "(RPE x minutes) calculated, if used?"},
            {"id": "load_metrics", "type": "multi",
             "label": "Which physical-load metrics are reported?",
             "options": ["Total distance", "High-speed running", "Sprint distance",
                         "Accelerations / decelerations", "Player load (accelerometer)",
                         "Session-RPE load", "Acute:chronic workload ratio",
                         "Heart-rate based load", OTHER]},
            {"id": "load_definitions", "type": "textarea",
             "label": "Give the definitions and thresholds used (e.g. speed band for "
                      "high-speed running) and where those definitions are documented."},
            {"id": "source_of_truth", "type": "textarea",
             "label": "When two systems disagree (e.g. attendance sheet vs GPS), "
                      "which one is the source of truth?"},
        ],
    },
    {
        "id": "s4",
        "title": "4. Data quality checks and approval",
        "intro": "How errors are caught before a report leaves the department.",
        "questions": [
            {"id": "qc_checks", "type": "multi",
             "label": "Which checks are done before a report is sent?",
             "options": ["Missing entries", "Duplicate entries", "Out-of-range values",
                         "Cross-check with attendance", "Cross-check with GPS / load data",
                         "Second person review", "No formal checks", OTHER]},
            {"id": "qc_who_when", "type": "textarea",
             "label": "Who performs the checks, and at what time?"},
            {"id": "approval_required", "type": "radio",
             "label": "Does a report need approval before it is sent?",
             "options": ["Always", "Only some reports", "No", "Not defined"],
             "detail": "Which reports, and who approves?"},
            {"id": "qc_recorded", "type": "textarea",
             "label": "Is the check or approval recorded anywhere (e.g. initials, "
                      "checklist, email)? Where?"},
            {"id": "qc_error_flow", "type": "textarea",
             "label": "When someone finds an error, how is it reported and to whom?"},
        ],
    },
    {
        "id": "s5",
        "title": "5. File naming, versioning, correction and archive",
        "intro": "How files are named, versioned, corrected and kept.",
        "questions": [
            {"id": "naming_convention", "type": "textarea",
             "label": "What naming convention is used? Give a fictional example "
                      "(e.g. 2026-10-21_DailyAvailability_v1.xlsx)."},
            {"id": "versioning_method", "type": "multi",
             "label": "How are versions identified?",
             "options": ["Date in file name", "v1 / v2 in file name", "'FINAL' in file name",
                         "Cloud version history", "Overwrite the same file", "No method",
                         OTHER]},
            {"id": "correction_process", "type": "textarea",
             "label": "If a report is wrong after it has been sent, what is the "
                      "correction procedure? Are recipients told what changed?"},
            {"id": "archive_rules", "type": "textarea",
             "label": "Where are old reports archived, for how long, and who can "
                      "delete them?"},
        ],
    },
    {
        "id": "s6",
        "title": "6. Current storage locations and channels",
        "intro": "Where files live today and how they move between people.",
        "questions": [
            {"id": "channels", "type": "multi",
             "label": "Which storage locations and channels are used today?",
             "options": ["Shared network folder", "OneDrive / SharePoint", "Google Drive",
                         "Email", "WhatsApp (individual chats)", "WhatsApp (groups)",
                         "Printed copies", "Local laptop / USB", "Vendor platform", OTHER]},
            {"id": "approved_storage", "type": "textarea",
             "label": "Which location is the approved, official store for medical "
                      "and performance reports?"},
            {"id": "whatsapp_use", "type": "radio",
             "label": "Is player-related medical information ever sent via WhatsApp?",
             "options": ["Never", "Sometimes", "Regularly", "Unsure"],
             "detail": "Process only: which types of message, to which groups (no content)."},
            {"id": "channels_to_stop", "type": "textarea",
             "label": "Which channels would you like to stop using, and why?"},
            {"id": "doctor_input_status", "type": "radio",
             "label": "Is the existing Doctor Input workbook still used?",
             "options": ["Yes, daily", "Yes, occasionally", "No, it was replaced",
                         "No, and nothing replaced it", "Unsure"],
             "detail": "If replaced: by what, since when, and where is it stored?"},
        ],
    },
    {
        "id": "s7",
        "title": "7. Access boundaries",
        "intro": (
            "Who may see what. Choose the access level for each audience. "
            "The rows are audiences only; no level is preselected."
        ),
        "questions": [
            {"id": "access_matrix", "type": "table", "label": "Access by audience"},
            {"id": "sd_shareable", "type": "textarea",
             "label": "Which information may be shared with the sporting director?"},
            {"id": "restricted_info", "type": "textarea",
             "label": "Which information must stay restricted to medical staff?"},
            {"id": "access_exceptions", "type": "textarea",
             "label": "Who approves an exception (sharing beyond the normal "
                      "boundary), and how is it recorded?"},
            {"id": "access_review", "type": "textarea",
             "label": "How is access removed when a staff member leaves, and how "
                      "often are folder/file permissions reviewed?"},
        ],
    },
    {
        "id": "s8",
        "title": "8. Reporting workload and repeated manual work",
        "intro": "Where time goes today.",
        "questions": [
            {"id": "hours_per_week", "type": "number",
             "label": "Approximate staff hours per week spent preparing reports "
                      "(whole department)"},
            {"id": "repeated_tasks", "type": "textarea",
             "label": "Which tasks are repeated by hand (copy-paste, re-typing, "
                      "reformatting)? Name the reports involved."},
            {"id": "double_entry", "type": "textarea",
             "label": "Is the same information entered into more than one system? Which?"},
            {"id": "pain_points", "type": "textarea",
             "label": "What are the three biggest pain points in current reporting?"},
            {"id": "automation_candidates", "type": "textarea",
             "label": "Which reports could be generated automatically if data were "
                      "entered once?"},
        ],
    },
    {
        "id": "s9",
        "title": "9. Future daily data-entry workflow",
        "intro": "Requirements for a future daily workflow. Describe needs, not data.",
        "questions": [
            {"id": "future_who", "type": "textarea",
             "label": "Who should enter data each day, and who should review it?"},
            {"id": "future_cutoff", "type": "text",
             "label": "What daily cut-off time is realistic (e.g. 30 min after the "
                      "last session)?"},
            {"id": "future_devices", "type": "multi",
             "label": "Which devices would be used for entry?",
             "options": ["Desktop / laptop", "Tablet", "Mobile phone", OTHER]},
            {"id": "future_languages", "type": "multi",
             "label": "Which languages should the tool support?",
             "options": ["English", "Arabic", "Portuguese", "Spanish", "French", OTHER]},
            {"id": "future_fields", "type": "textarea",
             "label": "Which fields or categories must the daily entry capture "
                      "(names of fields only)?"},
            {"id": "future_outputs", "type": "textarea",
             "label": "Which outputs should it produce automatically, for whom, and by when?"},
            {"id": "future_alerts", "type": "textarea",
             "label": "Which notifications or reminders would help (e.g. missing entry "
                      "by cut-off)?"},
            {"id": "future_integrations", "type": "textarea",
             "label": "Which systems should it connect to (GPS, wellness app, EMR, etc.)?"},
            {"id": "future_must_not", "type": "textarea",
             "label": "What must the future workflow NOT do?"},
        ],
    },
    {
        "id": "s10",
        "title": "10. Sign-off",
        "intro": "Who signs off the agreed process.",
        "questions": [
            {"id": "signoff_owner", "type": "text",
             "label": "Sign-off owner (name and role)"},
            {"id": "signoff_reviewers", "type": "textarea",
             "label": "Who else must review the agreed process before sign-off?"},
            {"id": "signoff_target", "type": "text",
             "label": "Target date for sign-off"},
            {"id": "review_frequency", "type": "radio",
             "label": "How often should the agreed process be reviewed?",
             "options": ["Monthly", "Quarterly", "Each season", "Not defined"]},
            {"id": "final_comments", "type": "textarea",
             "label": "Anything else the audit should capture?"},
        ],
    },
]


def iter_questions():
    """Yield (section, question) pairs in display order."""
    for section in SECTIONS:
        for q in section["questions"]:
            yield section, q


def table_column_labels(table_id: str) -> list[str]:
    return [label for _, label, _, _ in TABLES[table_id]["columns"]]
