"""
Thin wrapper around Gemini.

Everything that talks to the model goes through GeminiClient.generate(), so
errors are caught and logged in one place. If no API key is set, the rest of the
system runs in offline mode (rule-based parsing and template explanations).
"""

import logging
import os
import re
import time

log = logging.getLogger("vibefinder.llm")

MODEL_NAME = "gemini-flash-lite-latest"
MAX_RATE_LIMIT_WAIT = 40  # seconds we are willing to wait once on a 429


def short_error(exc):
    """One-line version of an API error (the raw 429 message is several hundred characters)."""
    text = str(exc).split("{")[0].strip() or type(exc).__name__
    return f"{type(exc).__name__}: {text[:120]}"


def suggested_wait(exc):
    """Seconds the API asked us to wait, if this is a rate-limit error."""
    text = str(exc)
    if "429" not in text and "RESOURCE_EXHAUSTED" not in text:
        return None
    match = re.search(r"retry in ([0-9.]+)s", text)
    return min(MAX_RATE_LIMIT_WAIT, float(match.group(1)) + 1) if match else 20.0


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
        for attempt in (1, 2):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                break
            except Exception as exc:  # network errors, 403/429, bad model name, ...
                wait = suggested_wait(exc)
                if attempt == 1 and wait is not None:
                    log.warning("Rate limited, waiting %.0fs then retrying once", wait)
                    time.sleep(wait)
                    continue
                log.warning("Gemini call failed: %s", short_error(exc))
                raise LLMUnavailable(short_error(exc)) from exc

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
