import unittest
import time
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.services.llm_engine import (
    generate_reading_text,
    validate_and_generate,
    OVERLOAD_MESSAGE,
    PROVIDER_TIMEOUT,
    CHAIN_TIMEOUT,
)

class TestLLMFallbackChain(unittest.TestCase):

    @patch("app.services.llm_engine._call_gemini_with_timeout")
    def test_gemini_success_primary(self, mock_gemini):
        mock_gemini.return_value = "Der Arzt untersucht den Patienten im Krankenhaus."
        
        result = generate_reading_text(["Arzt", "Krankenhaus"], "untersuchen", domain="HEALTH", level="B1")
        
        self.assertEqual(result, "Der Arzt untersucht den Patienten im Krankenhaus.")
        mock_gemini.assert_called_once()

    @patch("app.services.llm_engine._call_nim_with_timeout")
    @patch("app.services.llm_engine._call_gemini_with_timeout")
    def test_gemini_503_fallback_to_nim_success(self, mock_gemini, mock_nim):
        # Gemini raises 503 / Service Unavailable Exception
        mock_gemini.side_effect = Exception("503 Service Unavailable / Model Overloaded")
        mock_nim.return_value = "Der Software-Entwickler behebt den Fehler vor dem Release."
        
        start = time.time()
        result = generate_reading_text(["Entwickler", "Fehler"], "beheben", domain="IT", level="B1")
        duration = time.time() - start
        
        self.assertEqual(result, "Der Software-Entwickler behebt den Fehler vor dem Release.")
        mock_gemini.assert_called_once()
        mock_nim.assert_called_once()
        self.assertLess(duration, CHAIN_TIMEOUT)

    @patch("app.services.llm_engine._call_nim_with_timeout")
    @patch("app.services.llm_engine._call_gemini_with_timeout")
    def test_gemini_generic_exception_fallback_to_nim(self, mock_gemini, mock_nim):
        # Any exception (e.g. 429, ConnectionError, ValueError, Timeout)
        mock_gemini.side_effect = RuntimeError("429 ResourceExhausted: Quota exceeded")
        mock_nim.return_value = "Die Pflegekraft misst den Blutdruck am Morgen."
        
        result = generate_reading_text(["Pflegekraft"], "messen", domain="PFLEGE", level="A2")
        
        self.assertEqual(result, "Die Pflegekraft misst den Blutdruck am Morgen.")
        mock_gemini.assert_called_once()
        mock_nim.assert_called_once()

    @patch.dict("os.environ", {"NIM_API_KEY": "invalid-nim-api-key-test-12345"})
    @patch("app.services.llm_engine._call_gemini_with_timeout")
    def test_gemini_503_and_invalid_nim_key_env_var(self, mock_gemini):
        # Gemini throws 503
        mock_gemini.side_effect = Exception("503 Service Unavailable")
        
        start = time.time()
        with patch("app.services.llm_engine._call_nim_raw") as mock_nim_raw:
            # Simulate NIM rejecting the invalid API key
            mock_nim_raw.side_effect = Exception("401 Client Error: Unauthorized for url: https://integrate.api.nvidia.com/v1/chat/completions")
            
            with self.assertRaises(HTTPException) as ctx:
                generate_reading_text(["Wort"], "Ziel", domain="CORE", level="A2")
            
            # Verify fallback was triggered to NIM
            mock_nim_raw.assert_called_once()
        
        duration = time.time() - start
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail, "Der Dienst ist gerade überlastet. Bitte versuche es gleich erneut.")
        self.assertLess(duration, 45.0)

    @patch("app.services.llm_engine._call_nim_with_timeout")
    @patch("app.services.llm_engine._call_gemini_with_timeout")
    def test_both_providers_fail_raises_503_overload_message(self, mock_gemini, mock_nim):
        # Gemini throws 503
        mock_gemini.side_effect = Exception("503 Backend Overloaded")
        # NIM fails with invalid API key or server error
        mock_nim.side_effect = Exception("401 Unauthorized: Invalid NIM_API_KEY")
        
        start = time.time()
        with self.assertRaises(HTTPException) as ctx:
            generate_reading_text(["Wort"], "Ziel", domain="CORE", level="A2")
        duration = time.time() - start
        
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail, OVERLOAD_MESSAGE)
        self.assertEqual(ctx.exception.detail, "Der Dienst ist gerade überlastet. Bitte versuche es gleich erneut.")
        self.assertLess(duration, CHAIN_TIMEOUT)

    @patch("app.services.llm_engine._call_nim_with_timeout")
    @patch("app.services.llm_engine._call_gemini_with_timeout")
    def test_validate_and_generate_propagates_503(self, mock_gemini, mock_nim):
        mock_gemini.side_effect = Exception("503 Service Unavailable")
        mock_nim.side_effect = Exception("NIM Connection Timeout")
        
        with self.assertRaises(HTTPException) as ctx:
            validate_and_generate(
                anchor_lemmas=["haus"],
                target_lemma="baum",
                all_known_lemmas=["haus", "baum"],
                domain="CORE",
                level="A2",
                max_retries=1
            )
        
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.detail, OVERLOAD_MESSAGE)

    @patch("app.services.llm_engine._call_nim_raw")
    @patch("app.services.llm_engine._call_gemini_raw")
    def test_chain_timeout_constraint_under_slow_providers(self, mock_gemini_raw, mock_nim_raw):
        # Simulate Gemini taking 2 seconds then failing, NIM succeeding
        def slow_gemini(prompt, timeout):
            time.sleep(0.05)
            raise Exception("503 Gemini Slow Overload")
            
        def slow_nim(prompt, timeout):
            time.sleep(0.05)
            return "NIM generated text within total deadline."
            
        mock_gemini_raw.side_effect = slow_gemini
        mock_nim_raw.side_effect = slow_nim
        
        start = time.time()
        result = generate_reading_text(["test"], "test", domain="CORE", level="A2")
        duration = time.time() - start
        
        self.assertEqual(result, "NIM generated text within total deadline.")
        self.assertLess(duration, 45.0)


if __name__ == '__main__':
    unittest.main()
