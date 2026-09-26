"""Tests for secret sanitization and API key redaction."""

import unittest

from ecotrace.capture.request import RequestCapture
from ecotrace.capture.response import ResponseCapture
from ecotrace.utils.sanitization import redact_secrets


class TestSanitization(unittest.TestCase):

    def test_redact_secrets_patterns(self):
        sample_openai = "sk-1234567890abcdef1234567890"
        sample_groq = "gsk_1234567890abcdef1234567890"
        sample_gemini = "AIzaSy1234567890abcdef1234567890abcdef"
        sample_bearer = "Bearer token_abc_123"

        self.assertEqual(redact_secrets(sample_openai), "[REDACTED]")
        self.assertEqual(redact_secrets(sample_groq), "[REDACTED]")
        self.assertEqual(redact_secrets(sample_gemini), "[REDACTED]")
        self.assertEqual(redact_secrets(sample_bearer), "[REDACTED]")

    def test_redact_sensitive_dict_keys(self):
        metadata = {
            "user_id": "usr_99",
            "api_key": "custom_key_val",
            "authorization": "Bearer secret_header",
            "nested": {"token": "sub_token_val", "env": "prod"},
        }
        sanitized = redact_secrets(metadata)
        self.assertEqual(sanitized["user_id"], "usr_99")
        self.assertEqual(sanitized["api_key"], "[REDACTED]")
        self.assertEqual(sanitized["authorization"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["token"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["env"], "prod")

    def test_request_capture_auto_sanitizes_metadata(self):
        req = RequestCapture(
            prompt="Hello world",
            provider="openai",
            model="gpt-4o-mini",
            metadata={"api_key": "sk-1234567890abcdef1234567890", "client_ip": "127.0.0.1"},
        )
        self.assertEqual(req.metadata["api_key"], "[REDACTED]")
        self.assertEqual(req.metadata["client_ip"], "127.0.0.1")

    def test_response_capture_auto_sanitizes_provider_metadata(self):
        resp = ResponseCapture(
            response="Hello back",
            input_tokens=10,
            output_tokens=5,
            provider_metadata={"auth_header": "Bearer secret123"},
        )
        self.assertEqual(resp.provider_metadata["auth_header"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
