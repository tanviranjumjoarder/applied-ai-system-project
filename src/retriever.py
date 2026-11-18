"""
Retrieval step: score every song against the parsed profile and the song notes,
then return the top k with reasons and a confidence label.

The structured score (genre, mood, energy, acousticness) is the Module 3 recipe
from recommender.score_song. The new part is the note match: words from the
request ("rainy", "drive", "gym") are looked up in each song's note and
"good for" tags, so requests about a setting or activity can find the right songs.
"""

import json
import re

from src.recommender import WEIGHTS, score_song

NOTE_POINTS_PER_MATCH = 0.5
NOTE_POINTS_CAP = 1.0


def load_notes(path):
    """Read data/song_notes.json into {song_id: {"note": str, "good_for": [str]}}."""
    with open(path, encoding="utf-8") as f:
        return {int(k): v for k, v in json.load(f).items()}


def _stem(word):
    for suffix in ("ing", "ed", "es", "s", "y"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _words(text):
    return {_stem(w) for w in re.findall(r"[a-z]+", text.lower())}


def note_matches(keywords, note):
    """Which request keywords appear in a song's note or good_for tags."""
    if not note:
        return []
    note_words = _words(note["note"] + " " + " ".join(note.get("good_for", [])))
    return sorted({k for k in keywords if _stem(k) in note_words})


def scoring_profile(profile):
    """Only pass the features the listener actually gave to score_song."""
    prefs = {"energy": profile["energy"]}
    if profile.get("genre"):
        prefs["genre"] = profile["genre"]
    if profile.get("mood"):
        prefs["mood"] = profile["mood"]
    if profile.get("likes_acoustic") is not None:
        prefs["likes_acoustic"] = profile["likes_acoustic"]
    return prefs


def max_possible_score(profile, weights=None):
    """Best score a perfect song could get for this profile (used for confidence)."""
    w = weights or WEIGHTS
    total = w["energy"]
    if profile.get("genre"):
        total += w["genre"]
    if profile.get("mood"):
        total += w["mood"]
    if profile.get("likes_acoustic") is not None:
        total += w["acoustic"]
    if profile.get("keywords"):
        total += NOTE_POINTS_CAP
    return total


def retrieve(profile, songs, notes, k=5, weights=None):
    """
    Returns a list of dicts, best first:
        {"song": {...}, "note": {...}, "score": float, "reasons": [str]}
    """
    prefs = scoring_profile(profile)
    keywords = profile.get("keywords", [])
    results = []
    for song in songs:
        score, reasons = score_song(prefs, song, weights)
        note = notes.get(song["id"])
        matched = note_matches(keywords, note)
        if matched:
            bonus = min(NOTE_POINTS_CAP, NOTE_POINTS_PER_MATCH * len(matched))
            score += bonus
            reasons.append(f"notes mention {', '.join(matched)} (+{bonus:.1f})")
        results.append({"song": song, "note": note, "score": round(score, 2), "reasons": reasons})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:k]


def confidence(results, profile, weights=None):
    """
    How sure the system is about its #1 pick, from 0 to 1:
    the top score as a share of the best possible score for this profile.
    """
    if not results:
        return 0.0, "none"
    value = round(results[0]["score"] / max_possible_score(profile, weights), 2)
    label = "high" if value >= 0.75 else "medium" if value >= 0.5 else "low"
    return value, label
