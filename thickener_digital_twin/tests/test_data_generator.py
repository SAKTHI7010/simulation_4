"""Tests for synthetic dataset generation and physics/range audit."""

from pathlib import Path

import pandas as pd

from backend.data_audit import REQUIRED_COLUMNS, audit_dataset
from backend.data_generator import generate_synthetic_dataset


def test_generate_and_audit_synthetic_dataset(tmp_path: Path):
    res = generate_synthetic_dataset(n_rows=80, seed=42, output_dir=tmp_path)
    csv_path = Path(res["csv_path"])
    assert csv_path.exists()

    df = pd.read_csv(csv_path)
    assert len(df) == 80
    for col in REQUIRED_COLUMNS:
        assert col in df.columns
    assert (df["data_source_label"] == "SYNTHETIC").all()

    audit = audit_dataset(csv_path=csv_path, output_path=tmp_path / "audit.json")
    assert audit["passed"] is True
    assert audit["duplicate_record_ids"] == 0
