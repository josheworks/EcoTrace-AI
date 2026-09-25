"""Example: Provider normalization usage."""

from ecotrace import EcoTrace
from ecotrace.providers import GeminiProvider, GroqProvider, OpenAIProvider

def main():
    eco = EcoTrace()

    # OpenAI-formatted dictionary response
    openai_mock_response = {
        "choices": [{"message": {"content": "OpenAI mock answer"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 28, "total_tokens": 40},
    }

    print("Tracking OpenAI response format...")
    res1 = eco.track(
        provider="openai",
        model="gpt-4o",
        prompt="Explain deep learning.",
        response=openai_mock_response,
        latency_ms=180.0,
    )
    print(f"Tokens: Input={res1.event.input_tokens}, Output={res1.event.output_tokens}, Total={res1.event.total_tokens}")

    # Gemini-formatted dictionary response
    gemini_mock_response = {
        "candidates": [{"content": {"parts": [{"text": "Gemini mock answer"}]}}],
        "usage_metadata": {
            "prompt_token_count": 15,
            "candidates_token_count": 35,
            "total_token_count": 50,
        },
    }

    print("Tracking Gemini response format...")
    res2 = eco.track(
        provider="gemini",
        model="gemini-1.5-pro",
        prompt="Explain neural networks.",
        response=gemini_mock_response,
        latency_ms=250.0,
    )
    print(f"Tokens: Input={res2.event.input_tokens}, Output={res2.event.output_tokens}, Total={res2.event.total_tokens}")

if __name__ == "__main__":
    main()
