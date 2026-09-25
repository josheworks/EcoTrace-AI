"""EcoTrace AI - Hackathon Demo Script.

Demonstrates the core pipeline:
OBSERVE → DETECT → ANALYZE → OPTIMIZE → MEASURE

Simulates a realistic, inefficient AI workload and prints a clean, formatted report.
"""

from __future__ import annotations

import sys
import os

# Add root directory to sys.path so example runs cleanly standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ecotrace import EcoTrace


def run_demo():
    print("=" * 60)
    print("                     ECOTRACE AI                      ")
    print("         AI WORKLOAD OBSERVABILITY & OPTIMIZATION     ")
    print("=" * 60)
    print()

    eco = EcoTrace(project="hackathon-demo-suite")

    print("[1/5] OBSERVE: Simulating AI requests across providers...")

    # Simulated Workload: 10 requests containing duplicates and similar queries
    workload = [
        # Exact Duplicate Pair 1
        ("openai", "gpt-4o", "Explain Python decorators in detail", 120, 250, 450.0),
        ("openai", "gpt-4o", "Explain Python decorators in detail", 120, 250, 420.0),
        ("openai", "gpt-4o", "Explain Python decorators in detail", 120, 250, 410.0),

        # Semantically Similar Query
        ("openai", "gpt-4o", "Can you explain what Python decorators are?", 110, 240, 480.0),

        # Exact Duplicate Pair 2
        ("gemini", "gemini-1.5-flash", "What is quantum computing?", 80, 180, 210.0),
        ("gemini", "gemini-1.5-flash", "What is quantum computing?", 80, 180, 200.0),

        # Semantically Similar Query
        ("gemini", "gemini-1.5-flash", "Tell me about quantum computing basics", 90, 190, 230.0),

        # Large Context Request
        ("groq", "llama-3.1-70b", "Analyze this system log history: " + ("LOG_ENTRY_DEBUG_OK " * 250), 2200, 300, 1850.0),

        # Expensive Model Short Task
        ("openai", "gpt-4", "What is the capital of France?", 15, 10, 850.0),

        # Unique Fast Request
        ("openai", "gpt-4o-mini", "How do I filter a list in Python?", 45, 95, 120.0),
    ]

    for provider, model, prompt, in_tok, out_tok, latency in workload:
        mock_response = {
            "choices": [{"message": {"content": f"Mock response for '{prompt[:20]}...'"}}],
            "usage": {"prompt_tokens": in_tok, "completion_tokens": out_tok, "total_tokens": in_tok + out_tok},
        }
        eco.track(
            provider=provider,
            model=model,
            prompt=prompt,
            response=mock_response,
            latency_ms=latency,
        )

    print(f"      Successfully tracked {len(workload)} requests into EcoTrace pipeline.\n")

    print("[2/5] DETECT & ANALYZE: Running multi-signal workload intelligence...")
    report = eco.analyze(similarity_threshold=0.75)
    print("      Done!\n")

    print("-" * 60)
    print("                 ECOTRACE AI WORKLOAD REPORT                 ")
    print("-" * 60)
    print(f"Project                     : {report.project}")
    print(f"Total Requests Analyzed     : {report.request_metrics.total_requests}")
    print(f"Total Tokens Consumed       : {report.tokens.total_tokens:,}")
    print(f"Exact Duplicate Requests    : {report.duplicates.duplicate_count}")
    print(f"Semantically Similar Pairs  : {report.similarity.similar_pair_count}")
    print("-" * 60)

    print("\nEFFICIENCY METRICS (0-100)")
    print("-" * 60)
    print(f"Request Uniqueness Score    : {report.efficiency.request_efficiency:.1f} / 100")
    print(f"Token Efficiency Score      : {report.efficiency.token_efficiency:.1f} / 100")
    print(f"Latency Efficiency Score    : {report.efficiency.latency_efficiency:.1f} / 100")
    print(f"Redundancy Penalty Deducted : -{report.efficiency.redundancy_penalty:.1f} pts")
    print(f"OVERALL EFFICIENCY SCORE    : {report.efficiency.efficiency_score:.1f} / 100")

    print("\nWASTE DETECTION & QUANTIFICATION")
    print("-" * 60)
    print(f"Exact Duplicate Tokens Wasted: {report.tokens.duplicate_tokens:,}")
    print(f"Potential Semantic Redundancy: {report.tokens.potential_semantic_redundant_tokens:,}")
    print(f"TOTAL POTENTIAL TOKEN WASTE  : {report.tokens.total_wasted_tokens:,}")

    print("\n[3/5] OPTIMIZE: ACTIONABLE RECOMMENDATIONS")
    print("-" * 60)
    for idx, rec in enumerate(report.recommendations, 1):
        print(f" [{idx}] [{rec.priority.upper()}] {rec.description}")

    print("\n[4/5] MEASURE: ESTIMATED OPTIMIZATION SAVINGS & SIMULATION")
    print("-" * 60)
    sim = report.optimization.simulation
    print(f"Original Requests           : {sim.original_requests}")
    print(f"Optimized Requests          : {sim.optimized_requests}")
    print(f"Requests Avoided            : {sim.requests_avoided} ({sim.requests_avoided / sim.original_requests * 100:.1f}%)")
    print(f"Original Tokens             : {sim.original_tokens:,}")
    print(f"Optimized Tokens            : {sim.optimized_tokens:,}")
    print(f"Tokens Avoided              : {sim.tokens_avoided:,}")
    if report.savings.estimated_cost_saved_usd is not None:
        print(f"Estimated Cost Saved        : ${report.savings.estimated_cost_saved_usd:.4f} USD")

    print("\n[5/5] ECOSCORE RATING")
    print("=" * 60)
    print(f"                      ECOSCORE: {report.ecoscore.score} / 100")
    print(f"                      GRADE   : {report.ecoscore.grade}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    run_demo()
