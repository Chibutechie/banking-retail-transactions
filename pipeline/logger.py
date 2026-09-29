"""Centralized logging configuration for the banking data pipeline."""

import sys

from loguru import logger

from pipeline.config import LOG_DIR


# ── Logging Directory ─────────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)


# ── Reset Default Logger ───────────────────────────────────────────────────────

logger.remove()


# ── Console Logging ────────────────────────────────────────────────────────────

logger.add(
    sys.stdout,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    colorize=True,
)


# ── File Logging ──────────────────────────────────────────────────────────────

logger.add(
    str(LOG_DIR / "pipeline_{time:YYYY-MM-DD}.log"),
    level="DEBUG",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{line} | "
        "{message}"
    ),
    rotation="00:00",
    retention="7 days",
    compression="zip",
    encoding="utf-8",
)


# ── Public API ────────────────────────────────────────────────────────────────

__all__ = ["logger"]