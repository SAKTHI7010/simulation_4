"""Single-command launcher for both local development and Render deployment."""

from __future__ import annotations

import os

import uvicorn

from backend.data_audit import audit_dataset
from backend.data_generator import CSV_PATH, generate_synthetic_dataset


def main() -> None:
    if not CSV_PATH.exists():
        print("Generating labelled SYNTHETIC dataset...")
        generate_synthetic_dataset()
        audit_dataset()

    is_cloud = bool(os.environ.get("RENDER") or os.environ.get("PORT"))
    host = os.environ.get("HOST", "0.0.0.0" if is_cloud else "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))

    print(f"Starting Thickener Digital Twin at http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
