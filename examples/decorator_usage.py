"""Example: Using the @eco.track decorator."""

from ecotrace import EcoTrace, track

eco = EcoTrace(project="decorator-demo")

@track(client=eco, provider="openai", model="gpt-4o-mini")
def generate_headline(topic: str) -> str:

    """Mock LLM function call."""
    return f"Latest Breakthroughs in {topic}"

def main():
    print("Calling decorated function...")
    result = generate_headline("Artificial Intelligence")
    print(f"Function output: '{result}'")

    # Retrieve tracked event from global client
    events = eco.get_events()
    print(f"Events tracked via decorator: {len(events)}")
    if events:
        latest = events[0]
        print(f"Tracked Prompt : {latest.prompt}")
        print(f"Tracked Output : {latest.response}")
        print(f"Tracked Latency: {latest.latency_ms:.2f} ms")

if __name__ == "__main__":
    main()
