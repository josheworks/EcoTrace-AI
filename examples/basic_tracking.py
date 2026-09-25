"""Example: Basic request/response tracking with EcoTrace."""

from ecotrace import EcoTrace

def main():
    # Initialize EcoTrace SDK
    eco = EcoTrace(project="demo-project")

    print("Tracking request 1...")
    result1 = eco.track(
        provider="openai",
        model="gpt-4o-mini",
        prompt="Explain quantum computing in simple terms.",
        response="Quantum computing uses quantum bits (qubits) to process information...",
        latency_ms=350.0,
        metadata={"environment": "production", "user_id": "usr_123"},
    )

    print(f"Event Tracked successfully!")
    print(f"Request ID : {result1.event.request_id}")
    print(f"Provider   : {result1.event.provider}")
    print(f"Model      : {result1.event.model}")
    print(f"Latency    : {result1.event.latency_ms} ms")
    print(f"Tokens     : Total={result1.event.total_tokens}")
    print("-" * 50)

    # Track a second request
    print("Tracking request 2...")
    result2 = eco.track(
        provider="gemini",
        model="gemini-1.5-flash",
        prompt="Summarize climate change impact.",
        response="Climate change affects ecosystems, weather patterns, and sea levels...",
        latency_ms=210.0,
    )

    print(f"Request ID : {result2.event.request_id}")

    # Inspect total tracked events in memory
    all_events = eco.get_events()
    print("-" * 50)
    print(f"Total events in session: {len(all_events)}")

if __name__ == "__main__":
    main()
