"""Requirement-ID, Roadmap-ID, and Defect-ID uniqueness checker.

Parses canonical specification documents and Roadmap.md to ensure:
1. Every Roadmap Task ID (P#-###) is unique
2. Every Functional/Business Requirement ID (FR-###, BR-###, G-###) is unique
3. Every Defect ID (DEF-###) is unique
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

# ID Regex patterns
ROADMAP_TASK_ID_PATTERN = re.compile(r"\b(P\d{1,2}-\d{3})\b")
REQUIREMENT_ID_PATTERN = re.compile(r"\b((?:FR|BR|G)-\d{3})\b")
DEFECT_ID_PATTERN = re.compile(r"\b(DEF-\d{3})\b")

# Regex to find task declarations in Roadmap.md: e.g. - [ ] **P0-001** or - [x] **P0-001**
DECLARATION_PATTERN = re.compile(r"-\s*\[[ x~!-]\]\s*\*\*(P\d{1,2}-\d{3})\*\*")


def check_id_uniqueness(root_dir: Path) -> list[str]:
    """Extract and check uniqueness of declared Roadmap IDs and Requirement IDs."""
    errors: list[str] = []

    # Map of ID -> list of (file_path, line_number)
    declared_roadmap_ids: dict[str, list[tuple[Path, int]]] = defaultdict(list)
    declared_defect_ids: dict[str, list[tuple[Path, int]]] = defaultdict(list)

    docs_dir = root_dir / "docs" / "project"
    roadmap_file = root_dir / "Roadmap.md"

    files_to_check: list[Path] = []
    if roadmap_file.exists():
        files_to_check.append(roadmap_file)
    if docs_dir.exists():
        for p in docs_dir.glob("*.md"):
            # Avoid scanning docs/project/Roadmap.md if root Roadmap.md is already included
            if p.name == "Roadmap.md" and roadmap_file.exists():
                continue
            files_to_check.append(p)

    for filepath in files_to_check:
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Failed to read {filepath}: {e}")
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            # Check declared roadmap tasks
            match_task = DECLARATION_PATTERN.search(line)
            if match_task:
                task_id = match_task.group(1)
                declared_roadmap_ids[task_id].append((filepath, line_num))

            # Check defect IDs declarations: ### DEF-###
            if line.strip().startswith("### DEF-"):
                match_def = DEFECT_ID_PATTERN.search(line)
                if match_def:
                    def_id = match_def.group(1)
                    declared_defect_ids[def_id].append((filepath, line_num))

    # Validate duplicates in Roadmap IDs
    for task_id, locations in declared_roadmap_ids.items():
        if len(locations) > 1:
            loc_str = ", ".join(f"{loc[0].name}:{loc[1]}" for loc in locations)
            errors.append(f"Duplicate Roadmap Task ID declared: {task_id} at [{loc_str}]")

    # Validate duplicates in Defect IDs
    for def_id, locations in declared_defect_ids.items():
        if len(locations) > 1:
            loc_str = ", ".join(f"{loc[0].name}:{loc[1]}" for loc in locations)
            errors.append(f"Duplicate Defect ID declared: {def_id} at [{loc_str}]")

    return errors


def main() -> int:
    """Run requirement and roadmap ID uniqueness checks."""
    root_dir = Path(__file__).resolve().parent.parent
    print(f"Checking Requirement/Roadmap/Defect ID uniqueness in {root_dir}...")

    errors = check_id_uniqueness(root_dir)

    if errors:
        print(f"\n[ERROR] Found {len(errors)} ID uniqueness violation(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("[SUCCESS] All Requirement and Roadmap ID uniqueness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
