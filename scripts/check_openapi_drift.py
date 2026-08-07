"""OpenAPI contract drift checker script.

Compares runtime FastAPI OpenAPI schema against the committed snapshot
in docs/project/openapi.json. Returns non-zero exit code if schema has drifted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend src to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_src = root_dir / "apps" / "backend" / "src"
if str(backend_src) not in sys.path:
    sys.path.insert(0, str(backend_src))

from company_profile.api.app import create_app


def check_openapi_drift() -> tuple[bool, str]:
    """Compare runtime OpenAPI schema against committed snapshot file."""
    snapshot_path = root_dir / "docs" / "project" / "openapi.json"
    if not snapshot_path.exists():
        return False, f"Committed snapshot file missing: {snapshot_path}"

    try:
        with snapshot_path.open("r", encoding="utf-8") as f:
            committed_schema = json.load(f)
    except Exception as e:
        return False, f"Failed to read committed snapshot: {e}"

    app = create_app()
    runtime_schema = app.openapi()

    if runtime_schema != committed_schema:
        return False, "Runtime OpenAPI schema differs from committed docs/project/openapi.json."

    return True, "OpenAPI schema matches committed snapshot."


def main() -> int:
    """Run OpenAPI drift check."""
    print("Checking for OpenAPI contract drift...")
    passed, message = check_openapi_drift()
    if passed:
        print(f"[SUCCESS] {message}")
        return 0
    print(f"[ERROR] {message}")
    print("Run `python scripts/generate_openapi.py` and commit docs/project/openapi.json.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
