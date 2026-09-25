"""Input validation utilities."""

from typing import Any, Dict, List, Optional, Union

from ecotrace.exceptions import ValidationError


def validate_prompt(prompt: Union[str, List[Dict[str, Any]], None]) -> None:
    """Validate that a prompt is a non-empty string or message list."""
    if prompt is None:
        raise ValidationError("Prompt cannot be None.")
    if isinstance(prompt, str):
        if not prompt.strip():
            raise ValidationError("Prompt string cannot be empty.")
    elif isinstance(prompt, list):
        if len(prompt) == 0:
            raise ValidationError("Prompt message list cannot be empty.")
    else:
        raise ValidationError(
            f"Prompt must be a string or list of messages, got {type(prompt).__name__}."
        )


def validate_provider(provider: Optional[str]) -> None:
    """Validate that a provider name is specified."""
    if not provider or not provider.strip():
        raise ValidationError("Provider name cannot be empty.")


def validate_model(model: Optional[str]) -> None:
    """Validate that a model name is specified."""
    if not model or not model.strip():
        raise ValidationError("Model name cannot be empty.")


def validate_positive_number(value: Any, name: str) -> None:
    """Validate that a value is a positive number."""
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {type(value).__name__}.")
    if value < 0:
        raise ValidationError(f"{name} must be non-negative, got {value}.")
