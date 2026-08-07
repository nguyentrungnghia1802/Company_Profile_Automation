"""OpenAPI schema generator script.

Generates and saves the current FastAPI OpenAPI JSON schema to
docs/project/openapi.json.
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


def generate_openapi_schema() -> dict:
    """Generate OpenAPI schema dictionary from the FastAPI application."""
    app = create_app()
    return app.openapi()


def save_openapi_snapshot(output_path: Path) -> None:
    """Save formatted OpenAPI schema snapshot to file."""
    schema = generate_openapi_schema()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"[SUCCESS] Saved OpenAPI snapshot to {output_path}")


def main() -> int:
    """Run OpenAPI schema generation."""
    output_path = root_dir / "docs" / "project" / "openapi.json"
    try:
        save_openapi_snapshot(output_path)
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to generate OpenAPI schema: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
