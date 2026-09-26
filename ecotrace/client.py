"""EcoTrace client - Public API.

Provides the primary developer interface for tracking AI requests/responses and
running unified workload analysis reports.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Union, overload

from ecotrace.analysis.report import WorkloadAnalyzer, WorkloadReport
from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.config import EcoTraceConfig
from ecotrace.exceptions import ProviderError
from ecotrace.providers.base import BaseProvider
from ecotrace.providers.gemini import GeminiProvider
from ecotrace.providers.generic import GenericProvider
from ecotrace.providers.groq import GroqProvider
from ecotrace.providers.openai import OpenAIProvider
from ecotrace.storage.base import BaseStorage
from ecotrace.storage.memory import MemoryStorage
from ecotrace.storage.models import RequestEvent, TrackingResult
from ecotrace.storage.sqlite import SQLiteStorage
from ecotrace.tracking.session import Session
from ecotrace.tracking.tracker import Tracker


class EcoTrace:
    """Main EcoTrace SDK entry point.

    Example:
        >>> eco = EcoTrace()
        >>> eco.track(provider="openai", model="gpt-4o-mini", prompt="Hello AI")
        >>> report = eco.analyze()
        >>> print(report.efficiency.score)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project: Optional[str] = None,
        storage: Optional[Union[str, BaseStorage]] = None,
        enabled: bool = True,
        config: Optional[EcoTraceConfig] = None,
    ) -> None:
        if config is not None:
            self._config = config
        else:
            self._config = EcoTraceConfig(
                api_key=api_key,
                project=project,
                storage=storage if isinstance(storage, str) else "memory",
                enabled=enabled,
            )

        # Initialize storage
        if isinstance(storage, BaseStorage):
            self._storage = storage
        elif self._config.storage == "sqlite":
            self._storage = SQLiteStorage(db_path=self._config.storage_path)
        else:
            self._storage = MemoryStorage()

        # Initialize session & tracker
        self._session = Session(project=self._config.project)
        self._tracker = Tracker(storage=self._storage, session=self._session)

        # Register default providers
        self._providers: Dict[str, BaseProvider] = {
            "openai": OpenAIProvider(),
            "gemini": GeminiProvider(),
            "groq": GroqProvider(),
            "generic": GenericProvider(),
        }

    @property
    def config(self) -> EcoTraceConfig:
        """Return current SDK configuration."""
        return self._config

    @property
    def tracker(self) -> Tracker:
        """Return underlying tracker."""
        return self._tracker

    @property
    def storage(self) -> BaseStorage:
        """Return underlying storage backend."""
        return self._storage

    def register_provider(self, provider: BaseProvider) -> None:
        """Register a custom provider implementation."""
        self._providers[provider.name.lower()] = provider

    def get_provider(self, name: str) -> BaseProvider:
        """Get provider by name or return GenericProvider."""
        name_clean = name.lower().strip()
        if name_clean in self._providers:
            return self._providers[name_clean]
        return GenericProvider(provider_name=name)

    def track(
        self,
        provider: str,
        model: str,
        prompt: Union[str, List[Dict[str, Any]]],
        response: Optional[Any] = None,
        latency_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrackingResult:
        """Track an AI request/response pair.

        Args:
            provider: Provider name (e.g. 'openai', 'gemini', 'groq').
            model: Model name (e.g. 'gpt-4o-mini').
            prompt: User prompt string or list of message dicts.
            response: Optional raw API response or response text string.
            latency_ms: Optional request latency in milliseconds.
            metadata: Optional metadata dictionary.

        Returns:
            TrackingResult object containing the persisted event.
        """
        if not self._config.enabled:
            dummy_event = RequestEvent(
                provider=provider,
                model=model,
                prompt=prompt,
                metadata=metadata or {},
            )
            return TrackingResult(event=dummy_event)

        provider_impl = self.get_provider(provider)

        req_capture = provider_impl.normalize_request(
            prompt=prompt, model=model, metadata=metadata
        )

        resp_capture: Optional[ResponseCapture] = None
        if response is not None:
            if isinstance(response, ResponseCapture):
                resp_capture = response
            else:
                resp_capture = provider_impl.normalize_response(response)

        return self._tracker.track(
            request=req_capture,
            response=resp_capture,
            latency_ms=latency_ms,
        )

    def analyze(
        self,
        similarity_threshold: float = 0.60,
        limit: int = 1000,
    ) -> WorkloadReport:


        """Run full multi-signal workload analysis on all tracked events in current session.

        Args:
            similarity_threshold: Cosine similarity threshold for semantic redundancy (default 0.85).
            limit: Maximum number of events to analyze from storage.

        Returns:
            WorkloadReport containing duplicate detection, semantic similarity, token waste,
            latency percentiles, efficiency score, recommendations, savings, and EcoScore.
        """
        events = self.get_events(limit=limit)
        analyzer = WorkloadAnalyzer(similarity_threshold=similarity_threshold)
        return analyzer.analyze_events(events, project=self._config.project)

    def get_events(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 1000,
    ) -> List[RequestEvent]:
        """Retrieve tracked events from storage."""
        return self._storage.get_events(
            session_id=self._session.session_id,
            provider=provider,
            model=model,
            limit=limit,
        )

    def clear(self) -> None:
        """Clear all stored events."""
        self._storage.clear()
