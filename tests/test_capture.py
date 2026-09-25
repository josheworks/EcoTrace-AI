"""Tests for request and response capture modules."""

import unittest
from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture


class TestCapture(unittest.TestCase):
    def test_request_capture_string_prompt(self):
        """Test RequestCapture with a string prompt."""
        req = RequestCapture(
            prompt="Hello AI",
            provider="openai",
            model="gpt-4o-mini",
            metadata={"user_id": "123"},
        )
        self.assertEqual(req.prompt, "Hello AI")
        self.assertEqual(req.provider, "openai")
        self.assertEqual(req.model, "gpt-4o-mini")
        self.assertEqual(req.metadata["user_id"], "123")

        d = req.to_dict()
        self.assertEqual(d["prompt"], "Hello AI")
        self.assertEqual(d["provider"], "openai")

    def test_request_capture_messages_prompt(self):
        """Test RequestCapture with a list of message dicts."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is Python?"},
        ]
        req = RequestCapture(
            prompt=messages,
            provider="openai",
            model="gpt-4o",
        )
        self.assertEqual(len(req.prompt), 2)
        self.assertEqual(req.prompt[0]["role"], "system")

    def test_response_capture_token_calculation(self):
        """Test ResponseCapture automatic total_tokens calculation."""
        resp = ResponseCapture(
            response="Python is a programming language.",
            input_tokens=10,
            output_tokens=15,
            latency_ms=85.0,
        )
        self.assertEqual(resp.total_tokens, 25)
        self.assertEqual(resp.latency_ms, 85.0)

        d = resp.to_dict()
        self.assertEqual(d["response"], "Python is a programming language.")
        self.assertEqual(d["total_tokens"], 25)


if __name__ == "__main__":
    unittest.main()

