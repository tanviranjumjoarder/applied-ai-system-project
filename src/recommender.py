import csv
from typing import List, Dict, Tuple
from dataclasses import dataclass

# Algorithm Recipe: points for each kind of match. Change these to run experiments.
WEIGHTS = {"genre": 2.0, "mood": 1.0, "energy": 1.0, "acoustic": 0.5}


@dataclass
class Song:
    """A song and its attributes (matches the columns in data/songs.csv)."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """A user's taste profile: favorite genre and mood, target energy, acoustic preference."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


def score_song(user_prefs: Dict, song: Dict, weights: Dict = None) -> Tuple[float, List[str]]:
    """Score one song against user preferences; return (score, list of reasons)."""
    w = weights or WEIGHTS
    score = 0.0
    reasons = []

    if song["genre"] == user_prefs.get("genre"):
        score += w["genre"]
        reasons.append(f"genre match (+{w['genre']:.1f})")
    if song["mood"] == user_prefs.get("mood"):
        score += w["mood"]
        reasons.append(f"mood match (+{w['mood']:.1f})")
    if "energy" in user_prefs:
        # Closer to the target earns more points: full weight at a perfect match, 0 at a gap of 1.0.
        points = w["energy"] * (1 - abs(song["energy"] - user_prefs["energy"]))
        score += points
        reasons.append(f"energy {song['energy']:.2f} vs target {user_prefs['energy']:.2f} (+{points:.2f})")
    if "likes_acoustic" in user_prefs:
        # Acoustic fans want high acousticness; everyone else wants low.
        target = 1.0 if user_prefs["likes_acoustic"] else 0.0
        points = w["acoustic"] * (1 - abs(song["acousticness"] - target))
        score += points
        reasons.append(f"acousticness {song['acousticness']:.2f} (+{points:.2f})")

    return score, reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5, weights: Dict = None) -> List[Tuple[Dict, float, str]]:
    """Score every song and return the top k as (song, score, explanation), best first."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, weights)
        scored.append((song, score, "; ".join(reasons)))
    # sorted() returns a new list and leaves the catalog untouched; .sort() would reorder in place.
    return sorted(scored, key=lambda item: item[1], reverse=True)[:k]


def load_songs(csv_path: str) -> List[Dict]:
    """Read the CSV into a list of dicts, converting numeric columns to int/float."""
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["id"] = int(row["id"])
            for col in ("energy", "tempo_bpm", "valence", "danceability", "acousticness"):
                row[col] = float(row[col])
            songs.append(row)
    return songs


class Recommender:
    """Object-oriented wrapper around the same scoring rules, used by the tests."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _prefs(self, user: UserProfile) -> Dict:
        return {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k songs for this user, highest score first."""
        prefs = self._prefs(user)
        ranked = sorted(self.songs, key=lambda s: score_song(prefs, s.__dict__)[0], reverse=True)
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Explain in one line why this song scored the way it did."""
        score, reasons = score_song(self._prefs(user), song.__dict__)
        return f"Score {score:.2f}: " + "; ".join(reasons)
