from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq

from pipeline import downloader


def _dataset() -> dict:
    table = pa.table(
        {
            "transaction_id": ["tx-1", "tx-2"],
            "amount_ngn": [100.0, 200.0],
        }
    )
    return {"train": SimpleNamespace(data=SimpleNamespace(table=table))}


def test_download_writes_train_split_to_bronze(tmp_path, monkeypatch) -> None:
    bronze_path = tmp_path / "bronze" / "transactions.parquet"
    monkeypatch.setattr(downloader, "BRONZE_PATH", bronze_path)

    calls = {}

    def load_dataset(repo, *, revision):
        calls["repo"] = repo
        calls["revision"] = revision
        return _dataset()

    monkeypatch.setattr(downloader, "load_dataset", load_dataset)

    result = downloader.download()

    assert result["bronze_path"] == str(bronze_path)
    assert calls["repo"] == downloader.HF_REPO_ID
    assert calls["revision"] == downloader.HF_DATASET_REVISION
    assert result["revision"] == downloader.HF_DATASET_REVISION
    assert result["row_count"] == 2
    assert pq.read_table(bronze_path).num_rows == 2


def test_download_retries_before_succeeding(tmp_path, monkeypatch) -> None:
    bronze_path = tmp_path / "transactions.parquet"
    monkeypatch.setattr(downloader, "BRONZE_PATH", bronze_path)
    monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)

    calls = 0

    def load_dataset(_repo, *, revision):
        nonlocal calls
        assert revision == downloader.HF_DATASET_REVISION
        calls += 1
        if calls == 1:
            raise RuntimeError("temporary failure")
        return _dataset()

    monkeypatch.setattr(downloader, "load_dataset", load_dataset)

    result = downloader.download()

    assert calls == 2
    assert result["row_count"] == 2
