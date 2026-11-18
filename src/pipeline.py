"""
VibeFinder 2.0 pipeline: request -> guardrail -> parse -> retrieve -> explain -> self-check.

Every step is logged to logs/vibefinder.log so a run can be traced afterwards.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from src.guardrails import (
    REFUSAL_OFF_TOPIC,
    check_explanation,
    check_request,
    template_explanation,
)
from src.llm import LLMUnavailable
from src.parser import parse_request
from src.recommender import load_songs
from src.retriever import confidence, load_notes, retrieve

log = logging.getLogger("vibefinder.pipeline")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPLAIN_PROMPT = """You are VibeFinder, a music recommender. A listener asked:
<<<{request}>>>

Our retrieval step already picked these songs, best first. Use ONLY the facts below.

{songs}

Match confidence: {conf_label} ({conf_value})

Write the answer like this:
- One short opening sentence. If confidence is low, say honestly that the catalog has no strong match.
- Then exactly one line per song, in the same order: "<number>. <Title> by <Artist>: <one sentence why>".
- Explain each pick using its note and the reasons given. Do not invent facts, artists or songs.
- Do not mention any song that is not in the list above.
{feedback}"""


def setup_logging(path=None):
    """Send pipeline logs to logs/vibefinder.log (created if missing)."""
    path = path or os.path.join(ROOT, "logs", "vibefinder.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    root = logging.getLogger("vibefinder")
    if not any(isinstance(h, logging.FileHandler) for h in root.handlers):
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    root.setLevel(logging.INFO)


@dataclass
class Result:
    request: str
    refused: bool = False
    message: str = ""
    profile: Optional[dict] = None
    parser: str = ""
    parse_notes: List[str] = field(default_factory=list)
    recommendations: List[dict] = field(default_factory=list)
    confidence: float = 0.0
    confidence_label: str = "none"
    explanation: str = ""
    explainer: str = ""
    check_passed: Optional[bool] = None
    check_problems: List[str] = field(default_factory=list)


class VibeFinder:
    def __init__(self, llm=None, songs_path=None, notes_path=None, k=5):
        self.llm = llm
        self.k = k
        self.songs = load_songs(songs_path or os.path.join(ROOT, "data", "songs.csv"))
        self.notes = load_notes(notes_path or os.path.join(ROOT, "data", "song_notes.json"))
        self.genres = {s["genre"] for s in self.songs}
        self.moods = {s["mood"] for s in self.songs}
        self.titles = [s["title"] for s in self.songs]

    # ---------- step 4: explain + self-check ----------

    def _song_block(self, results):
        lines = []
        for i, r in enumerate(results, 1):
            s = r["song"]
            note = r["note"]["note"] if r["note"] else "(no note)"
            lines.append(
                f"{i}. {s['title']} by {s['artist']} | genre {s['genre']}, mood {s['mood']}, "
                f"energy {s['energy']:.2f}\n   note: {note}\n   reasons: {'; '.join(r['reasons'])}"
            )
        return "\n".join(lines)

    def explain(self, request, results, conf_value, conf_label):
        """
        Ask the model to explain the picks, then check its work.
        One retry with the problems spelled out; after that, fall back to the template.
        Returns (text, explainer_name, passed, problems).
        """
        retrieved_titles = [r["song"]["title"] for r in results]
        if self.llm is None:
            return template_explanation(results, conf_label), "template (offline)", True, []

        feedback = ""
        problems = []
        for attempt in (1, 2):
            prompt = EXPLAIN_PROMPT.format(
                request=request.replace(">>>", ""),
                songs=self._song_block(results),
                conf_label=conf_label,
                conf_value=conf_value,
                feedback=feedback,
            )
            try:
                text = self.llm.generate(prompt, temperature=0.3)
            except LLMUnavailable as exc:
                log.warning("Explanation call failed (attempt %d): %s", attempt, exc)
                problems = [f"model unavailable: {exc}"]
                break
            passed, problems = check_explanation(text, retrieved_titles, self.titles)
            log.info("Self-check attempt %d: %s %s", attempt, "PASS" if passed else "FAIL", problems)
            if passed:
                return text, "gemini" if attempt == 1 else "gemini (after retry)", True, []
            feedback = (
                "\nYour last answer had these problems, fix them: " + "; ".join(problems)
            )

        log.warning("Falling back to template explanation: %s", problems)
        return template_explanation(results, conf_label), "template (fallback)", False, problems

    # ---------- full pipeline ----------

    def recommend(self, request):
        log.info("Request: %r", request)
        result = Result(request=request)

        ok, message = check_request(request)
        if not ok:
            log.info("Rejected by input guardrail: %s", message)
            result.refused, result.message = True, message
            return result

        profile, parser, notes = parse_request(request, self.llm, self.genres, self.moods)
        result.profile, result.parser, result.parse_notes = profile, parser, notes
        log.info("Parsed with %s: %s", parser, profile)

        if not profile["is_music_request"]:
            log.info("Refused: not a music request")
            result.refused, result.message = True, REFUSAL_OFF_TOPIC
            return result

        results = retrieve(profile, self.songs, self.notes, k=self.k)
        result.recommendations = results
        result.confidence, result.confidence_label = confidence(results, profile)
        log.info(
            "Retrieved: %s | confidence %.2f (%s)",
            [(r["song"]["title"], r["score"]) for r in results],
            result.confidence, result.confidence_label,
        )

        text, explainer, passed, problems = self.explain(
            request, results, result.confidence, result.confidence_label
        )
        result.explanation, result.explainer = text, explainer
        result.check_passed, result.check_problems = passed, problems
        return result
