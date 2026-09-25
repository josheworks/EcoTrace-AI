"""Tests for provider implementations and abstractions."""

import unittest
from ecotrace.providers.gemini import GeminiProvider
from ecotrace.providers.generic import GenericProvider
from ecotrace.providers.groq import GroqProvider
from ecotrace.providers.openai import OpenAIProvider


class TestProviders(unittest.TestCase):
    def test_provider_instantiation_without_keys(self):
        """Verify that providers can be instantiated without API keys or credentials."""
        openai_p = OpenAIProvider()
        gemini_p = GeminiProvider()
        groq_p = GroqProvider()
        generic_p = GenericProvider()

        self.assertEqual(openai_p.name, "openai")
        self.assertEqual(gemini_p.name, "gemini")
        self.assertEqual(groq_p.name, "groq")
        self.assertEqual(generic_p.name, "generic")

    def test_openai_provider_normalization(self):
        """Test OpenAI provider request and response normalization."""
        p = OpenAIProvider()

        req = p.normalize_request(
            prompt="Hello world",
            model="gpt-4o-mini",
            metadata={"key": "val"},
        )
        self.assertEqual(req.provider, "openai")
        self.assertEqual(req.model, "gpt-4o-mini")
        self.assertEqual(req.prompt, [{"role": "user", "content": "Hello world"}])
        self.assertEqual(req.metadata, {"key": "val"})

        dict_response = {
            "choices": [{"message": {"content": "Hello back!"}}],
            "usage": {
                "prompt_tokens": 8,
                "completion_tokens": 12,
                "total_tokens": 20,
            },
        }
        resp = p.normalize_response(dict_response)
        self.assertEqual(resp.response, "Hello back!")
        self.assertEqual(resp.input_tokens, 8)
        self.assertEqual(resp.output_tokens, 12)
        self.assertEqual(resp.total_tokens, 20)

    def test_gemini_provider_normalization(self):
        """Test Gemini provider request and response normalization."""
        p = GeminiProvider()

        req = p.normalize_request(
            prompt="Gemini prompt",
            model="gemini-1.5-flash",
        )
        self.assertEqual(req.provider, "gemini")
        self.assertEqual(req.model, "gemini-1.5-flash")

        dict_response = {
            "candidates": [
                {"content": {"parts": [{"text": "Gemini response text"}]}}
            ],
            "usage_metadata": {
                "prompt_token_count": 15,
                "candidates_token_count": 25,
                "total_token_count": 40,
            },
        }
        resp = p.normalize_response(dict_response)
        self.assertEqual(resp.response, "Gemini response text")
        self.assertEqual(resp.input_tokens, 15)
        self.assertEqual(resp.output_tokens, 25)
        self.assertEqual(resp.total_token_count if hasattr(resp, "total_token_count") else resp.total_tokens, 40)

    def test_groq_provider_normalization(self):
        """Test Groq provider request and response normalization."""
        p = GroqProvider()

        req = p.normalize_request(
            prompt="Groq prompt",
            model="llama-3.1-70b",
        )
        self.assertEqual(req.provider, "groq")

        dict_response = {
            "choices": [{"message": {"content": "Groq output"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        }
        resp = p.normalize_response(dict_response)
        self.assertEqual(resp.response, "Groq output")
        self.assertEqual(resp.input_tokens, 5)
        self.assertEqual(resp.output_tokens, 10)
        self.assertEqual(resp.total_tokens, 15)


if __name__ == "__main__":
    unittest.main()

