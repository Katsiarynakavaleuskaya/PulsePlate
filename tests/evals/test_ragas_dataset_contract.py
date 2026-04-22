"""Dataset contract tests for the offline RAGAS bootstrap lane."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "evals" / "ragas" / "testset.jsonl"


def test_dataset_file_exists() -> None:
    """The committed bootstrap dataset must exist."""

    assert DATASET_PATH.is_file()


def test_dataset_rows_match_bootstrap_contract() -> None:
    """Each dataset row must satisfy the JSONL bootstrap contract."""

    rows = DATASET_PATH.read_text(encoding="utf-8").splitlines()

    assert rows
    assert len(rows) >= 12

    for index, line in enumerate(rows, start=1):
        payload = json.loads(line)

        assert isinstance(payload, dict)
        assert "question" in payload
        assert isinstance(payload["question"], str)
        assert payload["question"].strip()
        assert "answer" in payload
        assert isinstance(payload["answer"], str)
        assert payload["answer"].strip()
        assert "contexts" in payload
        assert isinstance(payload["contexts"], list)
        assert payload["contexts"]
        assert all(isinstance(item, str) and item.strip() for item in payload["contexts"])
        assert "reference" in payload or "ground_truth" in payload
        reference_value = payload.get("reference", payload.get("ground_truth"))
        assert isinstance(reference_value, str)
        assert reference_value.strip()
