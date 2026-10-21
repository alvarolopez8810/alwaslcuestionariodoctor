"""
Load the fictional sample submissions into the configured storage and write
their XLSX exports.

    python scripts/load_samples.py                 # save to storage + write XLSX
    python scripts/load_samples.py --export-only   # only write XLSX, no storage

XLSX files are written to samples/exports/. A third run step saves a second
revision of sample 1 to demonstrate revision numbering.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit.export import build_xlsx, xlsx_filename  # noqa: E402
from audit.privacy import scan_answers  # noqa: E402
from audit.storage import build_record, get_storage  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-only", action="store_true")
    args = ap.parse_args()

    out_dir = ROOT / "samples" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    storage = None if args.export_only else get_storage()

    for path in sorted((ROOT / "samples").glob("sample_submission_*.json")):
        sample = json.loads(path.read_text())
        answers = sample["answers"]
        flagged = scan_answers(answers, {})
        if flagged:
            raise SystemExit(f"{path.name} trips the privacy guard: {flagged}")

        record = build_record(storage, submission_id=None, submitter=sample["submitter"],
                              submitter_role=sample["submitter_role"], answers=answers)
        if storage:
            storage.save(record)
            # Demonstrate revisioning on the first sample.
            if path.name.endswith("_1.json"):
                answers2 = dict(answers, final_comments="Test submission 1 - revision 2 (fictional).")
                rev2 = build_record(storage, submission_id=record["submission_id"],
                                    submitter=sample["submitter"],
                                    submitter_role=sample["submitter_role"], answers=answers2)
                storage.save(rev2)
                print(f"saved {rev2['submission_id']} rev {rev2['revision']}")
        out = out_dir / xlsx_filename(record)
        out.write_bytes(build_xlsx(record, answers))
        print(f"{'saved ' + record['submission_id'] if storage else 'exported'} -> {out}")


if __name__ == "__main__":
    main()
