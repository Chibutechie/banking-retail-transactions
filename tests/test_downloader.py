"""Download the Hugging Face dataset and save an immutable Bronze Parquet snapshot."""

import time

import pyarrow.parquet as pq
from datasets import load_dataset

from pipeline.config import BRONZE_PATH, HF_REPO_ID
from pipeline.logger import logger


_MAX_RETRIES = 3
_RETRY_DELAY_SECS = 5


def download() -> dict:
    """Download the dataset and save it to the Bronze layer."""

    logger.info(f"Downloading dataset: {HF_REPO_ID}")

    dataset = None
    last_err = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            dataset = load_dataset(HF_REPO_ID)
            break

        except Exception as error:
            last_err = error

            if attempt < _MAX_RETRIES:
                logger.warning(
                    f"Attempt {attempt} failed. "
                    f"Retrying in {_RETRY_DELAY_SECS} seconds."
                )
                time.sleep(_RETRY_DELAY_SECS)

    if dataset is None:
        raise RuntimeError(
            f"Download failed after {_MAX_RETRIES} attempts: {last_err}"
        )

    # Use the train split when available.
    if "train" in dataset:
        table = dataset["train"].data.table
    else:
        tables = [split.data.table for split in dataset.values()]
        table = tables[0]

        for additional_table in tables[1:]:
            table = table.append_table(additional_table)

    BRONZE_PATH.parent.mkdir(parents=True, exist_ok=True)

    pq.write_table(
        table,
        BRONZE_PATH,
        compression="snappy",
    )

    file_size_mb = round(
        BRONZE_PATH.stat().st_size / (1024 * 1024),
        2,
    )

    row_count = len(table)

    logger.info(
        f"Bronze saved: {row_count:,} rows | "
        f"{file_size_mb} MB"
    )

    return {
        "bronze_path": str(BRONZE_PATH),
        "row_count": row_count,
        "file_size_mb": file_size_mb,
    }