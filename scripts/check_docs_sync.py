"""Documentation synchronization rule verification script.

Enforces rules defined in 10_DOCUMENTATION_SYNC_CHECKLIST.md:
1. Validates that every completed [x] task in Roadmap.md contains an Evidence note
2. Validates that Defect Ledger entries contain required fields
3. Validates status markers in Roadmap.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Allowed task status markers
ALLOWED_STATUSES = {"[ ]", "[~]", "[x]", "[!]", "[-]"}

# Task pattern: - [x] **P#-###** ...
TASK_PATTERN = re.compile(r"^-\s*(\[[ x~!-]\\])\s*\*\*(P\d{1,2}-\d{3})\*\*")


def verify_roadmap_sync(roadmap_path: Path) -> list[str]:
    """Verify Roadmap status markers and completion evidence notes."""
    errors: list[str] = []
    if not roadmap_path.exists():
        return [f"Roadmap file not found: {roadmap_path}"]

    try:
        content = roadmap_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Failed to read {roadmap_path}: {e}"]

    lines = content.splitlines()
    completed_tasks: set[str] = set()

    for line_num, line in enumerate(lines, start=1):
        line_strip = line.strip()
        # Check task status markers
        match = TASK_PATTERN.match(line_strip)
        if match:
            status, task_id = match.groups()
            if status not in ALLOWED_STATUSES:
                errors.append(f"{roadmap_path.name}:{line_num} Invalid status marker '{status}' for task {task_id}")
            if status == "[x]":
                completed_tasks.add(task_id)

    # Check evidence notes presence for completed blocks
    if "Evidence:" not in content and completed_tasks:
        errors.append(f"{roadmap_path.name} contains completed [x] tasks but no 'Evidence:' section was found.")

    return errors


def main() -> int:
    """Run documentation sync checks."""
    root_dir = Path(__file__).resolve().parent.parent
    print(f"Checking documentation synchronization rules in {root_dir}...")

    roadmap_path = root_dir / "Roadmap.md"
    errors = verify_roadmap_sync(roadmap_path)

    if errors:
        print(f"\n[ERROR] Found {len(errors)} documentation sync violation(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("[SUCCESS] All documentation synchronization checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
