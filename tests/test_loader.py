import pytest

from pipeline import loader


def test_load_requires_clean_staging_file(tmp_path, monkeypatch) -> None:
    missing_path = tmp_path / "missing.parquet"
    monkeypatch.setattr(loader, "CLEAN_STAGING_PATH", missing_path)

    with pytest.raises(FileNotFoundError, match="Clean staging not found"):
        loader.load(expected_row_count=1)


def test_raw_schema_matches_source_columns() -> None:
    expected_columns = [
        "transaction_id",
        "account_id",
        "customer_id",
        "timestamp",
        "amount_ngn",
        "balance_before_ngn",
        "balance_after_ngn",
        "transaction_type",
        "channel",
        "merchant_category_code",
        "merchant_name",
        "location_lga",
        "location_state",
        "device_id",
        "status",
        "fraud_flag",
    ]

    assert [field.name for field in loader.RAW_SCHEMA] == expected_columns
