"""
Soft guardrail against player-level medical data.

This is a process audit: it must never hold player names, diagnoses, injury
details, VAS/RPE values or clinical notes. We cannot detect everything
automatically (names especially), so this module only flags obvious
patterns. Flagged text blocks submission until the submitter either edits it
or confirms it describes a process, not a player.
"""

import re

PRIVACY_NOTICE = (
    "**About how we work, not about players.** Please do not enter player names, "
    "diagnoses, injury details, VAS or RPE values, clinical notes or any other "
    "player-level medical data. Staff names and positions are welcome; player names "
    "are not. If an example helps, make it fictional. Medical data needs and access rules come later, in Phase 4."
)

_PATTERNS = [
    # A VAS/RPE followed by a single number ("VAS 7", "RPE: 8"), but not a
    # scale description such as "VAS 0-10" or "RPE 6-20".
    (re.compile(r"\b(VAS|RPE)\b\s*(score|value|of|was|=|:)?\s*\d+(\.\d+)?(?!\s*(-|–|to)\s*\d)",
                re.IGNORECASE),
     "a VAS/RPE value"),
    (re.compile(
        r"\b(hamstring|adductor|quadriceps|calf strain|ACL|MCL|PCL|menisc\w*|fracture\w*|"
        r"sprain\w*|rupture\w*|concussion|tendinopath\w*|tendinitis|tendonitis|contusion|"
        r"grade [123]\b)",
        re.IGNORECASE),
     "a clinical / diagnosis term"),
    (re.compile(r"\b(player|patient)\s*(name|#|no\.?)?\s*[:=]\s*\S+", re.IGNORECASE),
     "what looks like a named player"),
]


def scan_text(text: str) -> list[str]:
    """Return human-readable reasons this text looks player-level. Empty = clean."""
    if not text:
        return []
    reasons = []
    for pattern, reason in _PATTERNS:
        m = pattern.search(text)
        if m:
            reasons.append(f"{reason} (\"{m.group(0).strip()}\")")
    return reasons


def _iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _iter_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _iter_strings(v)


def scan_answers(answers: dict, labels: dict[str, str]) -> list[tuple[str, str]]:
    """Scan every free-text value. Returns [(question label, reason), ...]."""
    findings = []
    for qid, value in answers.items():
        for s in _iter_strings(value):
            for reason in scan_text(s):
                findings.append((labels.get(qid, qid), reason))
    return findings
