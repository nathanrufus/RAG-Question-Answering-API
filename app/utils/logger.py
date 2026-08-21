"""
logger.py — Structured JSON logging for the entire application.

LEARNING NOTE:
  print() is fine for scripts. Production APIs use structured logging.
  Why? Because structured (JSON) logs can be:
    - Searched by field: "show me all requests where latency_ms > 2000"
    - Aggregated: "average latency this hour"
    - Alerted on: "page me if error_count > 10 per minute"
  
  Tools like Datadog, CloudWatch, and Grafana all expect JSON logs.
  Plain text logs are unsearchable noise at scale.
"""

import logging
import json
import time
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats every log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        # If the caller added extra fields (e.g. latency_ms, chunks_retrieved),
        # merge them into the log record.
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with JSON formatting.
    
    Usage:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Ingestion complete", extra={"extra": {"chunks": 24}})
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # prevent duplicate handlers on re-import
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


class Timer:
    """
    Context manager for timing code blocks.
    
    Usage:
        with Timer() as t:
            result = some_slow_operation()
        logger.info("Done", extra={"extra": {"latency_ms": t.elapsed_ms}})
    """
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = round((time.perf_counter() - self._start) * 1000, 2)
