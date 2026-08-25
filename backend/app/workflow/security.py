"""Boundary guards applied before untrusted content reaches an agent provider."""

from __future__ import annotations

import json
import re
from typing import Any

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*\S+", re.IGNORECASE),
)


def contains_likely_secret(value: Any) -> bool:
    """Report whether a payload looks like it carries a credential."""
    text = json.dumps(value, default=str)
    return any(pattern.search(text) for pattern in _SECRET_PATTERNS)
