"""Pipeline orchestrator: download -> validate -> load -> dbt."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, NoReturn

import typer

from pipeline import downloader, loader, manifests, validator
from pipeline.config import DBT_DIR, HF_REPO_ID, ensure_dirs, validate_env
from pipeline.logger import logger

app = typer.Typer(add_completion=False)

_OK = {"success", "pass"}
_BAD = {"error", "fail"}


@dataclass
class RunState:
    """Accumulates stage results so manifests are built from one place."""

    started: datetime
    dl: dict = field(default_factory=dict)
    vl: dict = field(default_factory=dict)
    ld: dict = field(default_factory=dict)
    db: dict = field(default_factory=dict)


# ── Manifest / failure helpers ────────────────────────────────────────────────


def _write_manifest(state: RunState, status: str, **extra) -> None:
    manifests.write(
        pipeline_status=status,
        started_at=state.started,
        source_repo=HF_REPO_ID,
        checksum=state.dl.get("checksum"),
        source_row_count=state.dl.get("row_count"),
        valid_rows=state.vl.get("valid_rows"),
        rejected_rows=state.vl.get("rejected_rows"),
        dead_letter_path=state.vl.get("dead_letter_path"),
        bq_table=state.ld.get("bq_table"),
        bq_rows_loaded=state.ld.get("rows_loaded"),
        dbt_status=state.db.get("status"),
        dbt_models=state.db.get("models"),
        dbt_tests_passed=state.db.get("tests_passed"),
        dbt_tests_failed=state.db.get("tests_failed"),
        **extra,
    )


def _fail(state: RunState, stage: str, reason: str) -> NoReturn:
    """Write failure manifest and exit non-zero."""
    logger.error(f"Failed at {stage}: {reason}")
    try:
        _write_manifest(
            state, "failed", failure_stage=stage, failure_reason=reason
        )
    except Exception:  # never let manifest errors mask the real failure
        logger.exception("Could not write failure manifest")
    raise typer.Exit(code=1)


def _run_stage(state: RunState, stage: str, fn: Callable, *args) -> dict:
    """Run a stage; any exception becomes a recorded pipeline failure."""
    try:
        return fn(*args)
    except Exception as exc:
        _fail(state, stage, str(exc))


# ── dbt ───────────────────────────────────────────────────────────────────────


def _dbt_failed(error: str, **counts) -> dict:
    return {
        "status": "failed",
        "models": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "error": error,
        **counts,
    }


def _read_run_results(path: Path) -> dict | None:
    """Count models/tests from dbt's run_results.json (more reliable than
    scraping stdout, and it separates models from tests)."""
    try:
        results = json.loads(path.read_text())["results"]
    except (OSError, ValueError, KeyError):
        return None

    models = tests_passed = tests_failed = 0
    failed_nodes: list[str] = []

    for r in results:
        kind = r["unique_id"].split(".", 1)[0]
        status = r["status"]
        is_test = kind in {"test", "unit_test"}

        if status in _BAD:
            failed_nodes.append(r["unique_id"])
            tests_failed += is_test
        elif status in _OK:
            if is_test:
                tests_passed += 1
            elif kind == "model":
                models += 1

    return {
        "models": models,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "failed_nodes": failed_nodes,
    }


def _run_dbt() -> dict:
    """Run dbt build and summarise the result."""
    run_results = Path(DBT_DIR) / "target" / "run_results.json"
    run_results.unlink(missing_ok=True)  # avoid reading a stale file

    try:
        result = subprocess.run(
            ["dbt", "build", "--project-dir", str(DBT_DIR)],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return _dbt_failed("dbt not found - install dbt-bigquery")

    for line in result.stdout.splitlines():
        logger.debug(f"[dbt] {line}")

    counts = _read_run_results(run_results)

    if result.returncode != 0:
        detail = f"dbt exited with code {result.returncode}"
        if counts and counts["failed_nodes"]:
            detail += f"; failed: {', '.join(counts['failed_nodes'][:10])}"
        elif result.stderr.strip():
            detail += f"; {result.stderr.strip()[-500:]}"
        return _dbt_failed(
            detail,
            **({k: counts[k] for k in ("models", "tests_passed", "tests_failed")}
               if counts else {}),
        )

    counts = counts or {"models": 0, "tests_passed": 0, "tests_failed": 0}
    logger.info(
        f"dbt: {counts['models']} models | "
        f"{counts['tests_passed']} tests passed | "
        f"{counts['tests_failed']} failed"
    )
    return {
        "status": "success",
        "error": None,
        **{k: counts[k] for k in ("models", "tests_passed", "tests_failed")},
    }


# ── Entry point ───────────────────────────────────────────────────────────────


@app.command()
def main(
    skip_download: bool = typer.Option(False, "--skip-download"),
    skip_dbt: bool = typer.Option(False, "--skip-dbt"),
) -> None:
    """Run the full pipeline: download -> validate -> load -> dbt."""
    state = RunState(started=datetime.now(timezone.utc))

    logger.info("=" * 60)
    logger.info("Pipeline started")
    logger.info("=" * 60)

    ensure_dirs()
    try:
        validate_env()
    except EnvironmentError as exc:
        _fail(state, "startup", str(exc))

    # Stage 1: download
    if skip_download:
        logger.info("[1/4] Download (skipped)")
    else:
        logger.info("[1/4] Download")
        state.dl = _run_stage(state, "download", downloader.download)

    # Stage 2: validate
    logger.info("[2/4] Validate")
    state.vl = _run_stage(state, "validate", validator.validate)
    if state.vl["status"] == "failed":
        _fail(state, "validate", "; ".join(state.vl["errors"]))
    if state.vl["valid_rows"] == 0:
        _fail(state, "validate", "All rows rejected")

    # Stage 3: load
    logger.info("[3/4] Load to BigQuery")
    state.ld = _run_stage(state, "load", loader.load, state.vl["valid_rows"])
    if state.ld["status"] == "failed":
        _fail(state, "load", state.ld["error"])

    # Stage 4: dbt
    if skip_dbt:
        logger.info("[4/4] dbt build (skipped)")
        state.db = {
            "status": "skipped",
            "models": 0,
            "tests_passed": 0,
            "tests_failed": 0,
        }
    else:
        logger.info("[4/4] dbt build")
        state.db = _run_dbt()
        if state.db["status"] == "failed":
            _fail(state, "dbt", state.db["error"])

    _write_manifest(state, "success")


if __name__ == "__main__":
    app()