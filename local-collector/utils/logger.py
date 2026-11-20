"""Structured logging with secret redaction filter to prevent accidental leakage."""

import logging
import re
from typing import Any

# Patterns matching sensitive token structures or key-value pairs
SENSITIVE_PATTERNS = [
    re.compile(r'(?i)(password|passwd|pwd|secret|api_?key|token|auth_?token|bearer)\s*[:=]\s*["\']?([^"\'\s,;]+)["\']?'),
    re.compile(r'ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'), # JWT
    re.compile(r'(?i)AKIA[0-9A-Z]{16}'), # AWS Access Key ID
    re.compile(r'-----BEGIN [A-Z ]+PRIVATE KEY-----'), # Private Keys
]


class SecretRedactionFilter(logging.Filter):
    """Logging filter that scrubs sensitive strings from all log output."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern in SENSITIVE_PATTERNS:
                if pattern.groups >= 1:
                    msg = pattern.sub(r"\1: [REDACTED_SECRET]", msg)
                else:
                    msg = pattern.sub("[REDACTED_SECRET]", msg)
            record.msg = msg
        return True


def get_logger(name: str = "AegisCollector") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactionFilter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
