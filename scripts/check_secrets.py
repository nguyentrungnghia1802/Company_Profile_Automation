"""Secret scanning script.

Scans codebase files for hardcoded secrets, private keys, API tokens,
and high-entropy credential patterns.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Regular expressions for sensitive patterns
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS Secret Access Key", re.compile(r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/\+=]{40}['\"]")),
    ("Private Key Header", re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----")),
    ("Generic API Key / Token", re.compile(r"(?i)(api_key|secret_key|auth_token|access_token)\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]")),
    ("Hardcoded Password", re.compile(r"(?i)password\s*=\s*['\"][^'\"]{8,}['\"]")),
    ("Google API Key", re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")),
    ("GitHub Personal Access Token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36}")),
    ("Firebase Server Key", re.compile(r"AAAA[A-Za-z0-9_\-]{7}:[A-Za-z0-9_\-]{140}")),
]

# Patterns that indicate safe placeholder values (allowed)
SAFE_PLACEHOLDERS: set[str] = {
    "your-gemini-api-key-placeholder",
    "your-search-api-key-placeholder",
    "your-search-engine-id-placeholder",
    "your-project-id",
    "your-audience",
    "your-gcs-bucket-placeholder",
    "vcps_dev",
}

# Directories and files to ignore
IGNORED_PATHS: set[str] = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "uv.lock",
    "pnpm-lock.yaml",
}

IGNORED_FILES: set[str] = {
    ".env.example",
    "check_secrets.py",
}


def is_safe_match(matched_text: str) -> bool:
    """Check if the matched text is a safe placeholder."""
    for placeholder in SAFE_PLACEHOLDERS:
        if placeholder in matched_text:
            return True
    return False


def scan_file(file_path: Path) -> list[tuple[int, str, str]]:
    """Scan a single file for secret patterns.

    Returns a list of (line_number, pattern_name, matched_line).
    """
    findings: list[tuple[int, str, str]] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for line_num, line in enumerate(content.splitlines(), start=1):
        for pattern_name, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                if not is_safe_match(match.group(0)):
                    findings.append((line_num, pattern_name, line.strip()))

    return findings


def scan_directory(root_dir: Path) -> list[tuple[Path, int, str, str]]:
    """Recursively scan directory for secret patterns."""
    all_findings: list[tuple[Path, int, str, str]] = []

    for path in root_dir.rglob("*"):
        if path.is_file():
            # Skip ignored directories
            if any(part in IGNORED_PATHS for part in path.parts):
                continue
            if path.name in IGNORED_FILES:
                continue

            file_findings = scan_file(path)
            for line_num, pattern_name, line in file_findings:
                all_findings.append((path, line_num, pattern_name, line))

    return all_findings


def main() -> int:
    """Run secret scanning."""
    # Check if test fixture validation mode requested
    if "--test-fixture" in sys.argv:
        print("Running secret scanner test fixture validation...")
        test_line = "api_key = 'sk_" + "live_1234567890abcdef1234567890'"
        matched = False
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(test_line):
                matched = True
                print(f"[TEST FIXTURE MATCHED] {name}: {test_line}")
                break
        if matched:
            print("Secret scanner test fixture validation passed.")
            return 0
        print("Secret scanner failed to detect test fixture.")
        return 1

    root_dir = Path(__file__).resolve().parent.parent
    print(f"Scanning codebase for secrets in {root_dir}...")
    findings = scan_directory(root_dir)

    if findings:
        print(f"\n[ERROR] Found {len(findings)} potential secret(s):")
        for path, line_num, name, line in findings:
            try:
                rel_path = path.relative_to(root_dir)
            except ValueError:
                rel_path = path
            print(f"  {rel_path}:{line_num} [{name}] -> {line[:80]}")
        return 1

    print("[SUCCESS] No secrets detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
