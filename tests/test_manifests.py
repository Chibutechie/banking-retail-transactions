import json
from datetime import UTC, datetime

from pipeline import manifests


def test_reconcile_checks_source_and_bigquery_counts() -> None:
    assert manifests._reconcile(10, 8, 2, 8) is True
    assert manifests._reconcile(10, 8, 1, 8) is False
    assert manifests._reconcile(None, 8, 2, 8) is True
    assert manifests._reconcile(None, None, None, None) is None


def test_write_creates_reconciled_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(manifests, "MANIFESTS_DIR", tmp_path)

    path = manifests.write(
        pipeline_status="success",
        started_at=datetime.now(UTC),
        source_repo="example/dataset",
        source_revision="abc456",
        checksum="abc123",
        source_row_count=10,
        valid_rows=10,
        rejected_rows=0,
        bq_table="project.raw.transactions",
        bq_rows_loaded=10,
    )

    manifest = json.loads(path.read_text(encoding="utf-8"))

    assert manifest["status"] == "success"
    assert manifest["source"]["revision"] == "abc456"
    assert manifest["source"]["rows"] == 10
    assert manifest["validation"]["rejected"] == 0
    assert manifest["bigquery"]["rows"] == 10
    assert manifest["reconciled"] is True
    assert manifest["failure"] is None
