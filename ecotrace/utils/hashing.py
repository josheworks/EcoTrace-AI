"""Hashing utilities for request deduplication."""

import hashlib
import json
from typing import Any, Dict, List, Optional, Union


def hash_string(value: str) -> str:
    """Generate a SHA-256 hash of a string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_request(
    prompt: Union[str, List[Dict[str, Any]]],
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """Generate a deterministic hash for a request.

    Args:
        prompt: The prompt string or message list.
        model: Optional model name.
        provider: Optional provider name.

    Returns:
        A hex digest string representing the request hash.
    """
    components: Dict[str, Any] = {"prompt": prompt}
    if model is not None:
        components["model"] = model
    if provider is not None:
        components["provider"] = provider
    serialized = json.dumps(components, sort_keys=True, default=str)
    return hash_string(serialized)
