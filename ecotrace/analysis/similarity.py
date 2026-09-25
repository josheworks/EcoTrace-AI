"""Semantic similarity analysis module.

Provides lightweight, dependency-safe semantic similarity detection for AI prompts
using cosine similarity over embeddings (or TF-IDF / n-gram vectorization fallback).
"""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ecotrace.storage.models import RequestEvent


def extract_prompt_text(event: RequestEvent) -> str:
    """Extract a clean, normalized string representation of an event prompt."""
    if not event or event.prompt is None:
        return ""

    if isinstance(event.prompt, str):
        return event.prompt.strip()

    if isinstance(event.prompt, list):
        parts = []
        for msg in event.prompt:
            if isinstance(msg, dict):
                content = msg.get("content", "")
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    # Handle multimodal content blocks like [{"type": "text", "text": "..."}]
                    for sub in content:
                        if isinstance(sub, dict) and "text" in sub:
                            parts.append(str(sub["text"]))
            elif isinstance(msg, str):
                parts.append(msg)
        return " ".join(parts).strip()

    if isinstance(event.prompt, dict):
        return str(event.prompt.get("content", str(event.prompt))).strip()

    return str(event.prompt).strip()


@dataclass
class SimilarityResult:
    """Result of a single similarity comparison against a corpus.

    Attributes:
        similar_to: Request ID of the most similar event, if any.
        similarity_score: Similarity score normalized between 0.0 and 1.0.
        is_similar: True if score >= threshold.
        source_prompt: Prompt text of the query event.
        target_prompt: Prompt text of the matched event.
    """
    similar_to: Optional[str] = None
    similarity_score: float = 0.0
    is_similar: bool = False
    source_prompt: str = ""
    target_prompt: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "similar_to": self.similar_to,
            "similarity_score": round(self.similarity_score, 4),
            "is_similar": self.is_similar,
            "source_prompt": self.source_prompt,
            "target_prompt": self.target_prompt,
        }


@dataclass
class SimilarityPair:
    """Represents a semantically similar pair of requests.

    Attributes:
        source_request_id: ID of the later request.
        target_request_id: ID of the earlier candidate request.
        similarity_score: Cosine similarity score (0.0 to 1.0).
        is_similar: Whether threshold was met.
        source_prompt: Text of the source request.
        target_prompt: Text of the target request.
        potential_wasted_tokens: Tokens spent on the similar request.
    """
    source_request_id: str
    target_request_id: str
    similarity_score: float
    is_similar: bool = True
    source_prompt: str = ""
    target_prompt: str = ""
    potential_wasted_tokens: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source_request_id": self.source_request_id,
            "target_request_id": self.target_request_id,
            "similarity_score": round(self.similarity_score, 4),
            "is_similar": self.is_similar,
            "source_prompt": self.source_prompt[:100] if self.source_prompt else "",
            "target_prompt": self.target_prompt[:100] if self.target_prompt else "",
            "potential_wasted_tokens": self.potential_wasted_tokens,
        }


@dataclass
class SimilarityAnalysisResult:
    """Batch analysis result across a corpus of events.

    Attributes:
        total_compared: Number of event comparisons evaluated.
        similar_pair_count: Number of semantically similar pairs detected.
        similar_pairs: List of SimilarityPair objects.
        similar_request_ids: Set of request IDs flagged as semantically similar.
        potential_redundant_tokens: Total tokens consumed by similar requests.
        method_used: Description of vectorization algorithm used.
    """
    total_compared: int = 0
    similar_pair_count: int = 0
    similar_pairs: List[SimilarityPair] = field(default_factory=list)
    similar_request_ids: Set[str] = field(default_factory=set)
    potential_redundant_tokens: int = 0
    method_used: str = "built-in tfidf/n-gram"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "total_compared": self.total_compared,
            "similar_pair_count": self.similar_pair_count,
            "similar_pairs": [p.to_dict() for p in self.similar_pairs],
            "similar_request_ids": list(self.similar_request_ids),
            "potential_redundant_tokens": self.potential_redundant_tokens,
            "method_used": self.method_used,
        }


class SimilarityAnalyzer(ABC):
    """Abstract base class for semantic similarity analysis."""

    def __init__(self, threshold: float = 0.85) -> None:
        self.threshold = threshold

    @abstractmethod
    def analyze(
        self, event: RequestEvent, corpus: List[RequestEvent]
    ) -> SimilarityResult:
        """Analyze similarity of a single event against a corpus."""
        ...

    def analyze_corpus(
        self,
        events: List[RequestEvent],
        exclude_ids: Optional[Set[str]] = None,
    ) -> SimilarityAnalysisResult:
        """Batch analyze a full corpus of events for pairwise similarity.

        Args:
            events: List of RequestEvent objects.
            exclude_ids: Optional set of request IDs to exclude (e.g. exact duplicates).

        Returns:
            SimilarityAnalysisResult object.
        """
        if not events:
            return SimilarityAnalysisResult()

        exclude = exclude_ids or set()
        candidates = [e for e in events if e.request_id not in exclude]

        if len(candidates) < 2:
            return SimilarityAnalysisResult(total_compared=len(candidates))

        similar_pairs: List[SimilarityPair] = []
        similar_ids: Set[str] = set()
        total_compared = 0
        potential_tokens = 0

        # Process sequentially to match newer events against older ones
        for i in range(1, len(candidates)):
            current = candidates[i]
            history = candidates[:i]
            total_compared += len(history)

            res = self.analyze(current, history)
            if res.is_similar and res.similar_to:
                similar_pair = SimilarityPair(
                    source_request_id=current.request_id,
                    target_request_id=res.similar_to,
                    similarity_score=res.similarity_score,
                    is_similar=True,
                    source_prompt=res.source_prompt,
                    target_prompt=res.target_prompt,
                    potential_wasted_tokens=current.total_tokens,
                )
                similar_pairs.append(similar_pair)
                similar_ids.add(current.request_id)
                potential_tokens += current.total_tokens

        return SimilarityAnalysisResult(
            total_compared=total_compared,
            similar_pair_count=len(similar_pairs),
            similar_pairs=similar_pairs,
            similar_request_ids=similar_ids,
            potential_redundant_tokens=potential_tokens,
            method_used=getattr(self, "backend_name", "standard"),
        )


class BuiltInVectorSimilarity:
    """Lightweight TF-IDF + Content-Word & Bigram Cosine Vectorizer.

    Standard library vectorizer used when heavy ML libraries are not present.
    Calculates normalized similarity score between 0.0 and 1.0.
    """

    _STOP_WORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
        "do", "does", "did", "can", "could", "would", "should", "will", "shall", "may", "might",
        "in", "on", "at", "to", "for", "from", "of", "with", "by", "about", "against", "between",
        "into", "through", "during", "before", "after", "above", "below", "up", "down", "out",
        "you", "your", "yours", "me", "my", "mine", "he", "him", "his", "she", "her", "it", "its",
        "we", "us", "our", "they", "them", "their", "which", "who", "whom", "this", "that",
        "these", "those", "am", "or", "and", "if", "because", "as", "until", "while",
        "please", "tell", "give"
    }


    @classmethod
    def _content_words(cls, text: str) -> Set[str]:
        """Extract content words excluding common stopwords."""
        words = re.findall(r"\w+", text.lower())
        return set(w for w in words if w not in cls._STOP_WORDS and len(w) >= 3)

    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        """Generate word tokens, 4-char stems, and word bigrams."""
        words = re.findall(r"\w+", text.lower())
        tokens: List[str] = list(words)

        for w in words:
            if len(w) >= 4 and w not in cls._STOP_WORDS:
                tokens.append(w[:4])

        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")

        return tokens

    @classmethod
    def cosine_similarity(cls, text1: str, text2: str) -> float:
        """Calculate normalized similarity score (0.0 to 1.0) combining Content-Word Overlap & Cosine."""
        t1 = text1.strip()
        t2 = text2.strip()

        if not t1 or not t2:
            return 0.0

        if t1.lower() == t2.lower():
            return 1.0

        cw1 = cls._content_words(t1)
        cw2 = cls._content_words(t2)

        content_overlap = 0.0
        if cw1 and cw2:
            common_cw = cw1 & cw2
            min_cw = min(len(cw1), len(cw2))
            if min_cw > 0:
                content_overlap = len(common_cw) / min_cw

        vec1 = Counter(cls._tokenize(t1))
        vec2 = Counter(cls._tokenize(t2))

        common_tokens = set(vec1.keys()) & set(vec2.keys())
        numerator = sum(vec1[x] * vec2[x] for x in common_tokens)

        sum1 = sum(val**2 for val in vec1.values())
        sum2 = sum(val**2 for val in vec2.values())
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        cosine_score = (float(numerator) / denominator) if denominator else 0.0

        # Weighted combination: 60% Content-Word Overlap + 40% Full Vector Cosine
        combined = (0.6 * content_overlap) + (0.4 * cosine_score)
        return max(0.0, min(1.0, combined))






class EmbeddingSimilarityAnalyzer(SimilarityAnalyzer):
    """Semantic similarity analyzer with pluggable embeddings.

    Uses `sentence_transformers` if installed, otherwise falls back gracefully
    to `BuiltInVectorSimilarity` (TF-IDF + Cosine Similarity).
    """

    def __init__(
        self,
        threshold: float = 0.85,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        super().__init__(threshold=threshold)
        self.model_name = model_name
        self._encoder = None
        self.backend_name = "built-in tfidf/n-gram"

        # Try loading optional sentence_transformers dependency
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._encoder = SentenceTransformer(model_name)
            self.backend_name = f"sentence-transformers ({model_name})"
        except ImportError:
            self._encoder = None
            self.backend_name = "built-in tfidf/n-gram fallback"

    def analyze(
        self, event: RequestEvent, corpus: List[RequestEvent]
    ) -> SimilarityResult:
        """Analyze similarity of an event against a corpus.

        Args:
            event: The query RequestEvent.
            corpus: Candidate RequestEvent corpus.

        Returns:
            SimilarityResult object.
        """
        source_text = extract_prompt_text(event)
        if not source_text or not corpus:
            return SimilarityResult(source_prompt=source_text)

        best_score = 0.0
        best_match_id: Optional[str] = None
        best_target_prompt = ""

        # Filter out self-comparison
        valid_corpus = [e for e in corpus if e.request_id != event.request_id]

        if not valid_corpus:
            return SimilarityResult(source_prompt=source_text)

        # If sentence-transformers is available
        if self._encoder is not None:
            try:
                corpus_texts = [extract_prompt_text(e) for e in valid_corpus]
                embeddings = self._encoder.encode([source_text] + corpus_texts)
                query_vec = embeddings[0]
                corpus_vecs = embeddings[1:]

                import numpy as np  # type: ignore
                norm_query = np.linalg.norm(query_vec)
                for idx, c_vec in enumerate(corpus_vecs):
                    norm_c = np.linalg.norm(c_vec)
                    if norm_query > 0 and norm_c > 0:
                        sim = float(np.dot(query_vec, c_vec) / (norm_query * norm_c))
                        if sim > best_score:
                            best_score = sim
                            best_match_id = valid_corpus[idx].request_id
                            best_target_prompt = corpus_texts[idx]
            except Exception:
                # Fallback to built-in vectorizer on runtime error
                self._encoder = None

        # Fallback to built-in vectorizer if sentence-transformers is unavailable or errored
        if self._encoder is None:
            for target_event in valid_corpus:
                target_text = extract_prompt_text(target_event)
                sim = BuiltInVectorSimilarity.cosine_similarity(source_text, target_text)
                if sim > best_score:
                    best_score = sim
                    best_match_id = target_event.request_id
                    best_target_prompt = target_text

        is_similar = best_score >= self.threshold

        return SimilarityResult(
            similar_to=best_match_id if is_similar else None,
            similarity_score=round(best_score, 4),
            is_similar=is_similar,
            source_prompt=source_text,
            target_prompt=best_target_prompt if is_similar else "",
        )


class BasicSimilarityAnalyzer(SimilarityAnalyzer):
    """Simple baseline similarity analyzer relying on string & token overlap.

    Useful for lightweight tests or deterministic baseline benchmarking.
    """

    def analyze(
        self, event: RequestEvent, corpus: List[RequestEvent]
    ) -> SimilarityResult:
        """Analyze similarity using string and token overlap."""
        source_text = extract_prompt_text(event)
        if not source_text or not corpus:
            return SimilarityResult(source_prompt=source_text)

        best_score = 0.0
        best_match_id: Optional[str] = None
        best_target_prompt = ""

        for candidate in corpus:
            if candidate.request_id == event.request_id:
                continue
            cand_text = extract_prompt_text(candidate)
            score = BuiltInVectorSimilarity.cosine_similarity(source_text, cand_text)

            if score > best_score:
                best_score = score
                best_match_id = candidate.request_id
                best_target_prompt = cand_text

        is_similar = best_score >= self.threshold

        return SimilarityResult(
            similar_to=best_match_id if is_similar else None,
            similarity_score=round(best_score, 4),
            is_similar=is_similar,
            source_prompt=source_text,
            target_prompt=best_target_prompt if is_similar else "",
        )
