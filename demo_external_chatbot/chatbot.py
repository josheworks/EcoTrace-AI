"""Sample external chatbot application using EcoTrace AI SDK for workload observability and optimization.

This script demonstrates how any Python LLM application can integrate EcoTrace with
just a few lines of code to track live telemetry, detect duplicates, and monitor costs.

Usage:
    python chatbot.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict

# Import EcoTrace AI SDK
from ecotrace import EcoTrace, RequestCapture, ResponseCapture

# Initialize EcoTrace SDK with SQLite persistence
# Telemetry is stored in 'ecotrace.db' which can be monitored via 'ecotrace dashboard'
ecotrace = EcoTrace(storage="sqlite", storage_path="ecotrace.db")

print("=" * 65)
print("  🤖 External AI Chatbot Application (EcoTrace AI Integrated)")
print("=" * 65)
print(f"Tracking active session: {ecotrace.tracker.session.session_id}")
print(f"Database target: {os.path.abspath('ecotrace.db')}")
print("Run `ecotrace dashboard` in another terminal to see live telemetry at http://localhost:8000/ecotrace-ai/\n")


def simulate_llm_request(prompt: str, model: str = "gpt-4o-mini", provider: str = "openai") -> str:
    """Simulates an LLM call with EcoTrace telemetry tracking.

    In production, replace the simulated response with calls to
    openai.chat.completions.create(...) or google.generativeai.
    """
    start_time = time.time()

    # Sanitization check: pass an API key in metadata to prove automatic redaction
    metadata = {
        "user_id": "user_12345",
        "api_key": "sk-proj-test-secret-key-1234567890abcdef",  # Will be redacted automatically!
        "application": "demo_chatbot",
    }

    # Normalize & capture request
    request = RequestCapture(prompt=prompt, provider=provider, model=model, metadata=metadata)

    # Simulate network latency and response payload
    time.sleep(0.15)
    latency_ms = (time.time() - start_time) * 1000

    # Simulated AI completion & token counts
    completion_text = f"EcoTrace AI processed prompt: '{prompt[:40]}...'"
    input_tokens = len(prompt.split()) * 3 + 15
    output_tokens = len(completion_text.split()) * 3 + 10

    response = ResponseCapture(
        response=completion_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )

    # Track event with EcoTrace Tracker
    result = ecotrace.track(request=request, response=response)

    dup_status = "⚠️ DUPLICATE DETECTED!" if result.is_duplicate else "✨ UNIQUE"
    print(f"[{dup_status}] Model: {model} | Tokens: {response.total_tokens} | Latency: {latency_ms:.1f}ms")
    print(f"   Prompt: '{prompt}'")
    print(f"   Response: '{completion_text}'\n")

    return completion_text


def main():
    prompts = [
        ("What are the best practices for reducing LLM token costs?", "gpt-4o-mini", "openai"),
        ("Explain quantum computing in simple terms.", "gemini-1.5-flash", "gemini"),
        ("What are the best practices for reducing LLM token costs?", "gpt-4o-mini", "openai"),  # Duplicate!
        ("How does SHA-256 fingerprint deduplication work?", "llama-3.3-70b", "groq"),
        ("Explain quantum computing in simple terms.", "gemini-1.5-flash", "gemini"),  # Duplicate!
    ]

    print("🚀 Sending simulated real-world LLM workload traffic...\n")
    for prompt, model, provider in prompts:
        simulate_llm_request(prompt, model=model, provider=provider)
        time.sleep(0.5)

    print("✅ Workload execution complete!")
    print(f"Total events tracked in session: {ecotrace.tracker.count()}")
    print("\nTo inspect analytics, start the dashboard:")
    print("  $ ecotrace dashboard --port 8000\n")


if __name__ == "__main__":
    main()
