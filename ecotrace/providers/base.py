"""Base provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture


class BaseProvider(ABC):
    """Abstract base class for all AI provider integrations.

    Every provider must implement methods to normalize raw request/response
    data into EcoTrace's provider-agnostic format.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the canonical provider name (e.g., 'openai')."""
        ...

    @abstractmethod
    def normalize_request(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        model: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RequestCapture:
        """Normalize a raw request into a RequestCapture.

        Args:
            prompt: The user prompt or message list.
            model: The model identifier.
            metadata: Optional extra metadata.

        Returns:
            A normalized RequestCapture instance.
        """
        ...

    @abstractmethod
    def normalize_response(
        self,
        raw_response: Any,
    ) -> ResponseCapture:
        """Normalize a raw provider response into a ResponseCapture.

        Args:
            raw_response: The raw response from the provider's API.

        Returns:
            A normalized ResponseCapture instance.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
