"""
Command line runner for the Music Recommender Simulation.
Run from the project root with: python -m src.main
"""

from src.recommender import load_songs, recommend_songs, WEIGHTS

PROFILES = {
    "High-Energy Pop": {"genre": "pop", "mood": "happy", "energy": 0.9, "likes_acoustic": False},
    "Chill Lofi": {"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True},
    "Deep Intense Rock": {"genre": "rock", "mood": "intense", "energy": 0.92, "likes_acoustic": False},
    # Edge cases meant to trick the scoring
    "Conflicting (high energy but sad)": {"genre": "folk", "mood": "sad", "energy": 0.9, "likes_acoustic": True},
    "Genre not in catalog (k-pop)": {"genre": "k-pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False},
}

# Experiment: energy counts double, genre counts half.
SHIFTED_WEIGHTS = {**WEIGHTS, "genre": 1.0, "energy": 2.0}


def show(title, user_prefs, songs, k=5, weights=None):
    print(f"=== {title} ===")
    print(f"Profile: {user_prefs}")
    for i, (song, score, why) in enumerate(recommend_songs(user_prefs, songs, k, weights), 1):
        print(f"{i}. {song['title']} by {song['artist']} [{song['genre']}/{song['mood']}] - Score: {score:.2f}")
        print(f"   Because: {why}")
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    for name, prefs in PROFILES.items():
        show(name, prefs, songs)

    print("##### EXPERIMENT: genre weight 2.0 -> 1.0, energy weight 1.0 -> 2.0 #####\n")
    for name in ("High-Energy Pop", "Chill Lofi"):
        show(name + " (shifted weights)", PROFILES[name], songs, weights=SHIFTED_WEIGHTS)


if __name__ == "__main__":
    main()
