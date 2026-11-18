"""
Thin wrapper around Gemini.

Everything that talks to the model goes through GeminiClient.generate(), so
errors are caught and logged in one place. If no API key is set, the rest of the
system runs in offline mode (rule-based parsing and template explanations).
"""

import logging
import os

log = logging.getLogger("vibefinder.llm")

MODEL_NAME = "gemini-flash-lite-latest"


class LLMUnavailable(RuntimeError):
    """Raised when the model cannot be reached or returns nothing usable."""


class GeminiClient:
    def __init__(self, api_key=None, model=MODEL_NAME):
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            raise LLMUnavailable("GEMINI_API_KEY is not set")
        from google import genai  # imported here so offline mode works without the package

        self._genai = genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt, json_mode=False, temperature=0.2):
        """Send one prompt and return the text reply. Raises LLMUnavailable on any failure."""
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
        except Exception as exc:  # network errors, 403/429, bad model name, ...
            log.warning("Gemini call failed: %s: %s", type(exc).__name__, exc)
            raise LLMUnavailable(f"{type(exc).__name__}: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            log.warning("Gemini returned an empty reply")
            raise LLMUnavailable("empty reply")
        return text


def make_client():
    """Return a GeminiClient, or None (offline mode) if it cannot be created."""
    try:
        return GeminiClient()
    except LLMUnavailable as exc:
        log.info("Running offline: %s", exc)
        return None
