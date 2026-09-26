"""Seed utility to populate realistic developer LLM observability workloads."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import List

from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.storage.models import RequestEvent
from ecotrace.storage.sqlite import SQLiteStorage
from ecotrace.tracking.tracker import Tracker
from ecotrace.utils.hashing import hash_request


SAMPLE_WORKLOADS = [
    # Workload 1: High frequency repeated classification prompt (Duplicate candidate)
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "prompt": "Classify the sentiment of the following support message: 'The payment failed twice with error code 5002.' Options: Positive, Neutral, Negative.",
        "response": "Negative. The user is experiencing recurring payment failures.",
        "input_tokens": 32,
        "output_tokens": 12,
        "base_latency": 140.0,
        "repetitions": 14,
    },
    # Workload 2: Repeated SQL generation prompt (Duplicate candidate)
    {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "prompt": "Write a PostgreSQL query to calculate the 7-day moving average of user signups from table 'users(id, created_at)'.",
        "response": "SELECT created_at::date AS day, COUNT(*), AVG(COUNT(*)) OVER (ORDER BY created_at::date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg FROM users GROUP BY 1 ORDER BY 1;",
        "input_tokens": 45,
        "output_tokens": 68,
        "base_latency": 210.0,
        "repetitions": 8,
    },
    # Workload 3: Code review on large diff
    {
        "provider": "openai",
        "model": "gpt-4o",
        "prompt": "Review this Python refactoring pull request for security vulnerabilities and race conditions in concurrent connection handling.",
        "response": "1. In connection_pool.py: line 42 lacks a threading lock when acquiring pooled handles.\n2. In auth.py: timing attack vulnerability in token comparison; use hmac.compare_digest.",
        "input_tokens": 820,
        "output_tokens": 210,
        "base_latency": 1150.0,
        "repetitions": 2,
    },
    # Workload 4: Fast entity extraction on Groq
    {
        "provider": "groq",
        "model": "llama-3.1-70b",
        "prompt": "Extract person names, organizations, and monetary values from the quarterly earnings disclosure text.",
        "response": "Organizations: [Acme Corp, Nova Holdings]\nPersons: [Jane Doe (CEO), Mark Smith (CFO)]\nMonetary Values: [$45.2M, $12.8M EBITDA]",
        "input_tokens": 310,
        "output_tokens": 48,
        "base_latency": 88.0,
        "repetitions": 5,
    },
    # Workload 5: Architectural question on Gemini
    {
        "provider": "gemini",
        "model": "gemini-1.5-pro",
        "prompt": "Explain the architectural trade-offs between Event Sourcing with CQRS vs Change Data Capture (CDC) via Debezium for an e-commerce order workflow.",
        "response": "Event Sourcing maintains a full audit log of state mutations but increases schema evolution complexity. CDC offloads audit capture to WAL tailing with lower application-level coupling.",
        "input_tokens": 412,
        "output_tokens": 290,
        "base_latency": 860.0,
        "repetitions": 3,
    },
    # Workload 6: Repeated health check query (Duplicate candidate)
    {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "prompt": "System ping. Return JSON {'status': 'healthy'}.",
        "response": "{\"status\": \"healthy\"}",
        "input_tokens": 14,
        "output_tokens": 6,
        "base_latency": 92.0,
        "repetitions": 22,
    },
    # Workload 7: High latency outlier prompt
    {
        "provider": "openai",
        "model": "gpt-4o",
        "prompt": "Analyze edge-case deadlocks in multi-region CockroachDB distributed transactions under serializable isolation level.",
        "response": "Under Serializable isolation, distributed transactions that encounter concurrent conflicting read/write intents will induce transaction aborts or push transaction timestamps...",
        "input_tokens": 1250,
        "output_tokens": 640,
        "base_latency": 3200.0,
        "repetitions": 1,
    },
    # Workload 8: Unit test generation
    {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "prompt": "Generate pytest test cases for an exponential backoff retry decorator with jitter.",
        "response": "import pytest\nimport time\n\ndef test_retry_eventual_success():\n    attempts = 0\n    @retry(max_retries=3)\n    def flaky():\n        nonlocal attempts\n        attempts += 1\n        if attempts < 3: raise ValueError()\n        return True\n    assert flaky() == True",
        "input_tokens": 240,
        "output_tokens": 185,
        "base_latency": 270.0,
        "repetitions": 4,
    },
]


def seed_database(db_path: str = "ecotrace.db", clear_first: bool = False) -> int:
    """Populate database with sample developer LLM observability telemetry.

    Returns the number of created events.
    """
    storage = SQLiteStorage(db_path=db_path)
    if clear_first:
        storage.clear()

    now = datetime.now(timezone.utc)
    created_count = 0

    for item in SAMPLE_WORKLOADS:
        reps = item["repetitions"]
        prompt = item["prompt"]
        model = item["model"]
        provider = item["provider"]
        response = item["response"]
        in_tok = item["input_tokens"]
        out_tok = item["output_tokens"]
        base_lat = item["base_latency"]

        req_hash = hash_request(prompt=prompt, model=model, provider=provider)

        for i in range(reps):
            # Spread timestamps across the last 6 days
            days_ago = random.uniform(0.05, 5.8)
            evt_time = now - timedelta(days=days_ago)

            # Jitter latency slightly (+/- 15%)
            jitter = random.uniform(0.88, 1.14)
            lat = round(base_lat * jitter, 1)

            event = RequestEvent(
                provider=provider,
                model=model,
                prompt=prompt,
                response=response,
                input_tokens=in_tok,
                output_tokens=out_tok,
                total_tokens=in_tok + out_tok,
                latency_ms=lat,
                timestamp=evt_time,
                request_hash=req_hash,
                metadata={
                    "environment": "production" if i % 2 == 0 else "staging",
                    "user_agent": "ecotrace-python-sdk/0.1.0",
                },
            )
            storage.save_event(event)
            created_count += 1

    storage.close()
    return created_count


if __name__ == "__main__":
    count = seed_database()
    print(f"Successfully seeded {count} events into ecotrace.db")
