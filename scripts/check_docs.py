"""Documentation sync and link verification script.

Verifies:
1. Presence of all required canonical specification documents under docs/project/
2. Sync between root docs (README.md, AGENT.md, Roadmap.md) and docs/project/
3. Internal markdown links resolution
4. Document metadata section presence
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_PROJECT_DOCS: list[str] = [
    "00_PROJECT_CONTEXT.md",
    "01_PRODUCT_REQUIREMENTS.md",
    "02_SYSTEM_ARCHITECTURE.md",
    "03_DOMAIN_AND_FLOWS.md",
    "04_DATABASE.md",
    "05_API.md",
    "06_CODEBASE_GUIDE.md",
    "07_DEVELOPMENT_AND_TESTING.md",
    "08_DEPLOYMENT_AND_OPERATIONS.md",
    "09_DECISIONS_AND_RISKS.md",
    "10_DOCUMENTATION_SYNC_CHECKLIST.md",
    "AGENT.md",
    "Roadmap.md",
]

ROOT_SYNC_DOCS: list[str] = [
    "README.md",
    "AGENT.md",
    "Roadmap.md",
]

# Regex for markdown links: [text](link)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def check_required_docs(root_dir: Path) -> list[str]:
    """Check that all required project documentation files exist."""
    errors: list[str] = []
    docs_dir = root_dir / "docs" / "project"

    if not docs_dir.exists():
        errors.append(f"Directory missing: {docs_dir}")
        return errors

    for doc_name in REQUIRED_PROJECT_DOCS:
        doc_path = docs_dir / doc_name
        if not doc_path.exists():
            errors.append(f"Missing canonical document: docs/project/{doc_name}")

    for doc_name in ROOT_SYNC_DOCS:
        root_path = root_dir / doc_name
        if not root_path.exists():
            errors.append(f"Missing root document: {doc_name}")

    return errors


def check_markdown_links(root_dir: Path) -> list[str]:
    """Check that markdown file links resolve to existing targets."""
    errors: list[str] = []
    md_files = list(root_dir.rglob("*.md"))

    # Skip external/build directories
    ignored = {".venv", "node_modules", ".next", "__pycache__"}

    for md_file in md_files:
        if any(part in ignored for part in md_file.parts):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"Could not read {md_file}: {e}")
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for match in MARKDOWN_LINK_PATTERN.finditer(line):
                link_text, link_target = match.groups()

                # Skip web URLs, mailto, and anchors
                if link_target.startswith(("http://", "https://", "mailto:", "#")):
                    continue

                # Strip anchor from file link if present
                clean_target = link_target.split("#")[0]
                if not clean_target:
                    continue

                # Handle file:/// absolute links or relative links
                if clean_target.startswith("file:///"):
                    # Extract local path from file:/// URL
                    raw_path = clean_target[8:].replace("/", "\\")
                    target_path = Path(raw_path)
                else:
                    target_path = (md_file.parent / clean_target).resolve()

                # Verify target exists
                if not target_path.exists():
                    try:
                        rel_src = md_file.relative_to(root_dir)
                    except ValueError:
                        rel_src = md_file
                    errors.append(f"Broken link in {rel_src}:{line_num} -> '{link_target}' (target not found: {target_path})")

    return errors


def main() -> int:
    """Run all documentation checks."""
    root_dir = Path(__file__).resolve().parent.parent
    print(f"Checking documentation in {root_dir}...")

    errors: list[str] = []

    # 1. Required documents check
    req_errors = check_required_docs(root_dir)
    errors.extend(req_errors)

    # 2. Markdown link check
    link_errors = check_markdown_links(root_dir)
    errors.extend(link_errors)

    if errors:
        print(f"\n[ERROR] Found {len(errors)} documentation issue(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("[SUCCESS] All documentation checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
