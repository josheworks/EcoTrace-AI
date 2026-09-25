"""Semantic similarity analysis.

This module defines the interface for detecting semantically similar
(but not identical) AI requests. The actual similarity algorithm
(e.g. embeddings, cosine similarity) will be implemented in a future phase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from ecotrace.storage.models import RequestEvent


@dataclass
class SimilarityResult:
    """Result of a similarity comparison.

    Attributes:
        similar_to: Request ID of the most similar event, if any.
        similarity_score: Similarity score between 0.0 and 1.0.
        is_similar: Whether the score exceeds the threshold.
    """
    similar_to: Optional[str] = None
    similarity_score: float = 0.0
    is_similar: bool = False


class SimilarityAnalyzer(ABC):
    """Abstract interface for semantic similarity analysis.

    Concrete implementations will plug in different similarity
    algorithms (e.g., embedding-based, TF-IDF, etc.).
    """

    @abstractmethod
    def analyze(
        self, event: RequestEvent, corpus: List[RequestEvent]
    ) -> SimilarityResult:
        """Analyze similarity of an event against a corpus.

        Args:
            event: The new event to compare.
            corpus: Existing events to compare against.

        Returns:
            SimilarityResult with the closest match.
        """
        ...


class BasicSimilarityAnalyzer(SimilarityAnalyzer):
    """Placeholder similarity analyzer using simple string matching.

    This is a minimal placeholder. Real similarity analysis
    will use embeddings in a future phase.
    """

    def __init__(self, threshold: float = 0.9) -> None:
        self._threshold = threshold

    def analyze(
        self, event: RequestEvent, corpus: List[RequestEvent]
    ) -> SimilarityResult:
        """Basic placeholder: only flags exact string matches."""
        prompt_str = self._extract_prompt_text(event)

        for existing in corpus:
            if existing.request_id == event.request_id:
                continue
            existing_str = self._extract_prompt_text(existing)
            if prompt_str == existing_str:
                return SimilarityResult(
                    similar_to=existing.request_id,
                    similarity_score=1.0,
                    is_similar=True,
                )

        return SimilarityResult()

    @staticmethod
    def _extract_prompt_text(event: RequestEvent) -> str:
        """Extract a plain text string from the prompt field."""
        if isinstance(event.prompt, str):
            return event.prompt.strip().lower()
        if isinstance(event.prompt, list):
            parts = []
            for msg in event.prompt:
                if isinstance(msg, dict):
                    parts.append(str(msg.get("content", "")))
            return " ".join(parts).strip().lower()
        return str(event.prompt).strip().lower()
