"""Writes JSON run manifest — audit trail for every pipeline run."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import MANIFESTS_DIR
from pipeline.logger import logger

MANIFEST_VERSION = "0.2.0"


def write(
    pipeline_status: str,
    started_at: datetime,
    source_repo: str,
    checksum: str | None = None,
    source_row_count: int | None = None,
    valid_rows: int | None = None,
    rejected_rows: int | None = None,
    dead_letter_path: str | None = None,
    bq_table: str | None = None,
    bq_rows_loaded: int | None = None,
    dbt_status: str | None = None,
    dbt_models: int | None = None,
    dbt_tests_passed: int | None = None,
    dbt_tests_failed: int | None = None,
    failure_stage: str | None = None,
    failure_reason: str | None = None,
) -> Path:
    """Write a JSON manifest containing the results of one pipeline run."""

    # Guard against naive datetimes so the duration maths can't raise.
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    completed_at = datetime.now(timezone.utc)
    duration_s = round((completed_at - started_at).total_seconds(), 2)

    reconciled = _reconcile(
        source_row_count=source_row_count,
        valid_rows=valid_rows,
        rejected_rows=rejected_rows,
        bq_rows_loaded=bq_rows_loaded,
    )

    manifest = {
        "version": MANIFEST_VERSION,
        "status": pipeline_status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": duration_s,
        "source": {
            "repo": source_repo,
            "checksum": checksum,
            "rows": source_row_count,
        },
        "validation": {
            "valid": valid_rows,
            "rejected": rejected_rows,
            "dead_letter": dead_letter_path,
        },
        "bigquery": {
            "table": bq_table,
            "rows": bq_rows_loaded,
        },
        "dbt": {
            "status": dbt_status,
            "models": dbt_models,
            "tests_passed": dbt_tests_passed,
            "tests_failed": dbt_tests_failed,
        },
        # True/False when enough numbers exist to check, otherwise None.
        "reconciled": reconciled,
        # Keyed off the data, not the status, so details are never dropped.
        "failure": (
            {
                "stage": failure_stage,
                "reason": failure_reason,
            }
            if failure_stage or failure_reason
            else None
        ),
    }

    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

    # Microseconds in the name avoid collisions between runs in one second.
    stamp = started_at.strftime("%Y-%m-%d_%H%M%S_%f")
    path = MANIFESTS_DIR / f"run_{stamp}.json"

    # Atomic write: a crash mid-write never leaves a truncated manifest.
    tmp_path = path.with_suffix(".json.tmp")

    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, default=str)

    tmp_path.replace(path)

    logger.info(f"Manifest: {path}")

    _log_summary(manifest)

    return path


def _reconcile(
    source_row_count: int | None,
    valid_rows: int | None,
    rejected_rows: int | None,
    bq_rows_loaded: int | None,
) -> bool | None:
    """Check row counts agree across stages.

    Returns None when there are no counts to compare (for example, a run
    that failed before validation).
    """

    checks = []

    if None not in (source_row_count, valid_rows, rejected_rows):
        checks.append(valid_rows + rejected_rows == source_row_count)

    if None not in (valid_rows, bq_rows_loaded):
        checks.append(bq_rows_loaded == valid_rows)

    if not checks:
        return None

    return all(checks)


def _log_summary(manifest: dict) -> None:
    """Log one-block summary to console."""

    status = manifest["status"].upper()
    duration = manifest["duration_seconds"]

    logger.info("─" * 60)
    logger.info(f"PIPELINE {status} in {duration}s")

    source = manifest["source"]

    if source["rows"] is not None:
        if source["checksum"]:
            logger.info(
                f"Source: {source['rows']:,} rows | "
                f"checksum: {str(source['checksum'])[:12]}..."
            )
        else:
            logger.info(f"Source: {source['rows']:,} rows")

    validation = manifest["validation"]

    if validation["valid"] is not None:
        logger.info(
            f"Valid: {validation['valid']:,} | "
            f"Rejected: {validation['rejected'] or 0:,}"
        )

        if validation["dead_letter"]:
            logger.warning(f"Dead-letter: {validation['dead_letter']}")

    bigquery = manifest["bigquery"]

    if bigquery["rows"] is not None:
        logger.info(f"BigQuery: {bigquery['rows']:,} rows → {bigquery['table']}")

    dbt = manifest["dbt"]

    if dbt["status"] and dbt["status"] != "skipped":
        logger.info(
            f"dbt: {dbt['models'] or 0} models | "
            f"{dbt['tests_passed'] or 0} passed | "
            f"{dbt['tests_failed'] or 0} failed"
        )

    if manifest["reconciled"] is False:
        logger.warning("Row counts do NOT reconcile across stages.")

    if manifest["failure"]:
        logger.error(
            f"Failed at [{manifest['failure']['stage']}]: "
            f"{manifest['failure']['reason']}"
        )

    logger.info("─" * 60)