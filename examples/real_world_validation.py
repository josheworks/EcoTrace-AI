"""Real-world validation of the EcoTrace analysis pipeline."""

from ecotrace import RequestEvent
from ecotrace.analysis.report import WorkloadAnalyzer


def make_event(
    request_id: str,
    prompt: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    model: str = "gpt-4o-mini",
) -> RequestEvent:
    """Create a realistic normalized AI request event."""

    return RequestEvent(
        request_id=request_id,
        provider="openai",
        model=model,
        prompt=prompt,
        response="Example response",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        latency_ms=latency_ms,
    )


def main() -> None:
    """Run a controlled workload through EcoTrace."""

    events = [
        # Original request
        make_event(
            "req-001",
            "Explain binary search in Java with a simple example",
            120,
            250,
            850,
        ),

        # Exact duplicate
        make_event(
            "req-002",
            "Explain binary search in Java with a simple example",
            120,
            250,
            820,
        ),

        # Semantically similar
        make_event(
            "req-003",
            "Can you teach me how binary search works in Java?",
            110,
            230,
            900,
        ),

        # Another semantically similar request
        make_event(
            "req-004",
            "Describe the binary search algorithm using Java code",
            115,
            240,
            1100,
        ),

        # Completely different request
        make_event(
            "req-005",
            "What is polymorphism in object oriented programming?",
            100,
            200,
            700,
        ),

        # Large and slow request
        make_event(
            "req-006",
            "Explain the complete Java collections framework in detail",
            1500,
            2200,
            4200,
        ),
    ]

    analyzer = WorkloadAnalyzer()

    report = analyzer.analyze_events(events)

    print("\n" + "=" * 60)
    print("              ECOTRACE REAL-WORLD VALIDATION")
    print("=" * 60)

    print("\n[1] REQUEST METRICS")
    print("-" * 60)
    print(report.request_metrics)

    print("\n[2] DUPLICATE ANALYSIS")
    print("-" * 60)
    print(report.duplicates)

    print("\n[3] SIMILARITY ANALYSIS")
    print("-" * 60)
    print(report.similarity)

    print("\n[4] TOKEN ANALYSIS")
    print("-" * 60)
    print(report.tokens)

    print("\n[5] LATENCY ANALYSIS")
    print("-" * 60)
    print(report.latency)

    print("\n[6] EFFICIENCY ANALYSIS")
    print("-" * 60)
    print(report.efficiency)

    print("\n[7] OPTIMIZATION")
    print("-" * 60)
    print(report.optimization)

    print("\n[8] ECOSCORE")
    print("-" * 60)
    print(report.ecoscore)

    print("\n[9] RECOMMENDATIONS")
    print("-" * 60)

    if report.recommendations:
        for recommendation in report.recommendations:
            print("-", recommendation)
    else:
        print("No recommendations generated.")

    print("\n" + "=" * 60)
    print("Validation completed.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()