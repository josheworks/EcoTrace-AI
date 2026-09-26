"""Sanitization utilities for redacting sensitive secrets and API keys."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union

# Common API Key regex patterns
_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}"),  # OpenAI API keys
    re.compile(r"gsk_[a-zA-Z0-9_-]{20,}"),  # Groq API keys
    re.compile(r"AIzaSy[a-zA-Z0-9_-]{20,}"),  # Google/Gemini API keys
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+", re.IGNORECASE),  # Authorization Bearer tokens
]

# Key names to redact regardless of pattern match
_SENSITIVE_KEY_SUBSTRINGS = {
    "api_key",
    "apikey",
    "secret",
    "authorization",
    "auth_token",
    "access_token",
    "token",
    "bearer",
    "password",
}


def redact_secrets(data: Any) -> Any:
    """Recursively redacts secrets and API keys from data structures.

    Args:
        data: Dict, list, string, or primitive to sanitize.

    Returns:
        A sanitized copy of the data.
    """
    if isinstance(data, str):
        sanitized = data
        for pattern in _SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        return sanitized

    if isinstance(data, dict):
        result: Dict[str, Any] = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(sens in key_lower for sens in _SENSITIVE_KEY_SUBSTRINGS):
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_secrets(value)
        return result

    if isinstance(data, list):
        return [redact_secrets(item) for item in data]

    if isinstance(data, tuple):
        return tuple(redact_secrets(item) for item in data)

    return data
