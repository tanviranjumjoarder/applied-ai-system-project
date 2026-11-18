"""
Tests for the VibeFinder 2.0 pipeline. A FakeLLM stands in for Gemini so the
tests run offline and can force the failure cases (junk JSON, invented songs,
API errors) that are hard to trigger with the real model.
"""

import json

import pytest

from src.guardrails import check_explanation, check_request
from src.llm import LLMUnavailable
from src.parser import parse_with_rules, validate_profile
from src.pipeline import VibeFinder

GENRES = {"pop", "lofi", "rock", "hip hop", "indie pop"}
MOODS = {"happy", "chill", "intense"}


class FakeLLM:
    """Returns canned replies in order: JSON replies for parsing, text for explanations."""

    def __init__(self, json_replies=(), text_replies=(), fail=False):
        self.json_replies = list(json_replies)
        self.text_replies = list(text_replies)
        self.fail = fail
        self.calls = 0

    def generate(self, prompt, json_mode=False, temperature=0.2):
        self.calls += 1
        queue = self.json_replies if json_mode else self.text_replies
        if self.fail or not queue:
            raise LLMUnavailable("simulated outage")
        return queue.pop(0)


def profile_json(**overrides):
    base = {"is_music_request": True, "genre": None, "mood": "chill", "energy": 0.3,
            "likes_acoustic": None, "keywords": ["rainy", "study"]}
    base.update(overrides)
    return json.dumps(base)


def explanation_for(result_titles, extra=""):
    lines = ["Here you go."] + [f"{i}. {t} by someone: fits." for i, t in enumerate(result_titles, 1)]
    return "\n".join(lines) + extra


def top_titles(bot, request, profile=None):
    """
    Titles the retriever will pick, used to build fake answers.
    With `profile` (a JSON string) the songs come from that fake model profile;
    otherwise from the offline rule parser.
    """
    if profile is None:
        result = VibeFinder(llm=None).recommend(request)
    else:
        # The explanation call fails, so the pipeline uses the template, but retrieval still runs.
        result = VibeFinder(llm=FakeLLM(json_replies=[profile], text_replies=[])).recommend(request)
    return [r["song"]["title"] for r in result.recommendations]


# ---------- input guardrail ----------

def test_rejects_empty_and_too_long_requests():
    assert check_request("   ")[0] is False
    assert check_request("x" * 301)[0] is False
    assert check_request("chill lofi")[0] is True


# ---------- parsing and validation ----------

def test_rules_parser_reads_genre_alias_and_energy():
    p = parse_with_rules("hype rap for the gym")
    assert p["genre"] == "hip hop"
    assert p["energy"] >= 0.8
    assert p["is_music_request"] is True


def test_rules_parser_prefers_longer_genre_name():
    assert parse_with_rules("some indie pop please")["genre"] == "indie pop"


def test_rules_parser_does_not_read_k_pop_as_pop():
    # Found by the evaluation harness: "k-pop" used to be parsed as "pop".
    assert parse_with_rules("k-pop for dancing")["genre"] is None
    assert parse_with_rules("some hip-hop")["genre"] == "hip hop"


def test_rules_parser_flags_off_topic():
    assert parse_with_rules("what is the capital of france")["is_music_request"] is False


def test_validate_clamps_energy_and_drops_unknown_genre():
    profile, fixes = validate_profile(
        {"is_music_request": True, "genre": "k-pop", "mood": "happy", "energy": 1.7}, GENRES, MOODS
    )
    assert profile["genre"] is None
    assert profile["energy"] == 1.0
    assert len(fixes) == 2


def test_validate_rejects_missing_music_flag():
    with pytest.raises(ValueError):
        validate_profile({"genre": "pop"}, GENRES, MOODS)


def test_junk_json_falls_back_to_rules():
    llm = FakeLLM(json_replies=["not json at all"], text_replies=["ignored"])
    bot = VibeFinder(llm=llm)
    titles = top_titles(bot, "chill lofi for studying")
    llm.text_replies = [explanation_for(titles)]
    result = bot.recommend("chill lofi for studying")
    assert result.parser == "rules (fallback)"
    assert result.profile["genre"] == "lofi"


def test_invented_genre_is_dropped():
    llm = FakeLLM(json_replies=[profile_json(genre="ambient")])
    bot = VibeFinder(llm=llm)
    request = "something calm for a rainy study night"
    llm.text_replies = [explanation_for(top_titles(bot, request, profile_json(genre="ambient")))]
    result = bot.recommend(request)
    assert result.profile["genre"] is None
    assert any("never names it" in n for n in result.parse_notes)


# ---------- retrieval ----------

def test_note_keywords_pull_in_matching_song():
    result = VibeFinder(llm=None).recommend("something calm for a rainy study night")
    assert result.recommendations[0]["song"]["title"] == "Library Rain"
    assert any("notes mention" in r for r in result.recommendations[0]["reasons"])


def test_confidence_is_low_when_nothing_fits():
    result = VibeFinder(llm=None).recommend("sad metal for a beach party")
    assert result.confidence_label in ("low", "medium")
    strong = VibeFinder(llm=None).recommend("chill lofi for studying")
    assert strong.confidence > result.confidence


# ---------- self-check on the explanation ----------

def test_self_check_catches_invented_and_missing_songs():
    catalog = ["Library Rain", "Gym Hero", "Focus Flow"]
    ok, problems = check_explanation("1. Library Rain\n2. Gym Hero", ["Library Rain", "Focus Flow"], catalog)
    assert ok is False
    assert any("not retrieved: Gym Hero" in p for p in problems)
    assert any("skips retrieved songs: Focus Flow" in p for p in problems)


def test_retry_fixes_a_bad_explanation():
    bot = VibeFinder(llm=None)
    request = "chill lofi for studying"
    fake_profile = profile_json(genre="lofi")
    titles = top_titles(bot, request, fake_profile)
    assert "Gym Hero" not in titles
    bad = explanation_for(titles[:4]) + "\n5. Gym Hero: bonus pick!"
    llm = FakeLLM(json_replies=[fake_profile], text_replies=[bad, explanation_for(titles)])
    bot.llm = llm
    result = bot.recommend(request)
    assert result.explainer == "gemini (after retry)"
    assert result.check_passed is True


def test_two_bad_explanations_fall_back_to_template():
    bot = VibeFinder(llm=None)
    request = "chill lofi for studying"
    bad = "Try Gym Hero and Iron Tide!"
    bot.llm = FakeLLM(json_replies=[profile_json(genre="lofi")], text_replies=[bad, bad])
    result = bot.recommend(request)
    assert result.explainer == "template (fallback)"
    assert result.check_passed is False
    assert "Gym Hero" not in result.explanation


def test_api_outage_still_returns_recommendations():
    bot = VibeFinder(llm=FakeLLM(fail=True))
    result = bot.recommend("upbeat pop for a morning run")
    assert result.parser == "rules (fallback)"
    assert len(result.recommendations) == 5
    assert result.explainer.startswith("template")


def test_off_topic_request_is_refused_before_retrieval():
    result = VibeFinder(llm=None).recommend("what is the capital of france")
    assert result.refused is True
    assert result.recommendations == []
