"""Token budget and redaction helpers for RelayCore."""

import json
import re
from typing import Any, Dict, Iterable, List

TOKEN_REDACTION = "[REDACTED]"
SENSITIVE_KEYWORDS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "set-cookie",
    "private_key",
    "client_secret",
)
SENSITIVE_VALUE_RE = re.compile(
    r"(?i)\b(bearer\s+[A-Za-z0-9._-]+|ghp_[A-Za-z0-9]+|sk-[A-Za-z0-9]+|xox[baprs]-[A-Za-z0-9-]+)\b"
)


def estimate_tokens(value: Any) -> int:
    if value is None:
        return 0
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=True, sort_keys=True)
    return max(1, len(str(value).split()))


def is_sensitive_key(key: Any) -> bool:
    text = str(key).lower()
    return any(keyword in text for keyword in SENSITIVE_KEYWORDS)


def redact_text(value: str) -> str:
    if not value:
        return value
    return SENSITIVE_VALUE_RE.sub(TOKEN_REDACTION, value)


def redact_structure(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: TOKEN_REDACTION if is_sensitive_key(key) else redact_structure(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_structure(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_structure(item) for item in value)
    if isinstance(value, str):
        return redact_text(value)
    return value


def estimate_payload_tokens(*values: Any) -> int:
    return sum(estimate_tokens(value) for value in values)


def redact_json_payload(value: Any) -> str:
    return json.dumps(redact_structure(value), ensure_ascii=True, sort_keys=True)
