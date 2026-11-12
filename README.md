# 🎵 Music Recommender Simulation

## Project Summary

This is a small content-based music recommender written in Python. It reads a catalog of 20 songs from a CSV, compares each song to a user's taste profile (favorite genre, favorite mood, target energy and an acoustic preference), gives every song a score with a short list of reasons, and prints the top 5. I called the model **VibeFinder 1.0**. It runs in the terminal with `python -m src.main`. I tested it with five profiles and one weight experiment, and wrote up the weak spots in `model_card.md`.

---

## How The System Works

**How real apps do it.** Spotify and YouTube mix two ideas. Collaborative filtering looks at what other people did (likes, skips, playlists) and recommends what similar listeners enjoyed. Content-based filtering looks at the song itself (tempo, energy, mood, genre) and recommends songs that are close to ones you already like. My version only does the content-based part, because I have no other users, only a song file.

**Song features used:** `genre`, `mood`, `energy` (0 to 1), `acousticness` (0 to 1). The CSV also has `tempo_bpm`, `valence` and `danceability`, which I load but do not score yet.

**UserProfile:** `favorite_genre`, `favorite_mood`, `target_energy`, `likes_acoustic`.

**Algorithm Recipe (scoring one song):**

| Rule | Points |
|------|--------|
| Genre matches the favorite genre | +2.0 |
| Mood matches the favorite mood | +1.0 |
| Energy closeness: `1.0 x (1 - abs(song energy - target energy))` | 0 to +1.0 |
| Acousticness closeness (to 1.0 if the user likes acoustic, otherwise to 0.0): `0.5 x (1 - abs(difference))` | 0 to +0.5 |

Every rule that fires adds a reason string, so each recommendation says why it was picked. The most a song can score is 4.5.

**Ranking rule.** The score only judges one song. The ranking step runs the score on every song in the catalog and sorts the list from highest to lowest, then keeps the top k. Both are needed: without the score there is nothing to sort by, and without the ranking you only have a pile of numbers.

**Data flow:** user profile → score every song in the CSV → sort by score → top 5 with reasons.

**Biases I expected before testing:** genre is worth twice as much as mood, so I expected the system to push genre too hard and to miss songs that fit the mood and energy but sit in a different genre.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

```bash
pytest
```

There are 5 tests: the 2 starter tests and 3 I added (closer energy scores higher, the score returns reasons, the CSV loads with numbers as floats).

---

## Sample Recommendation Output

Terminal output from `python -m src.main` (first line, then each profile). The data has 20 songs: the 10 starter songs plus 10 I added to cover more genres and moods.

```
Loaded songs: 20
```

```
=== High-Energy Pop ===
Profile: {'genre': 'pop', 'mood': 'happy', 'energy': 0.9, 'likes_acoustic': False}
1. Sunrise City by Neon Echo [pop/happy] - Score: 4.33
   Because: genre match (+2.0); mood match (+1.0); energy 0.82 vs target 0.90 (+0.92); acousticness 0.18 (+0.41)
2. Gym Hero by Max Pulse [pop/intense] - Score: 3.44
   Because: genre match (+2.0); energy 0.93 vs target 0.90 (+0.97); acousticness 0.05 (+0.47)
3. Calle Sol by Los Faroles [latin/happy] - Score: 2.26
   Because: mood match (+1.0); energy 0.80 vs target 0.90 (+0.90); acousticness 0.28 (+0.36)
4. Rooftop Lights by Indigo Parade [indie pop/happy] - Score: 2.19
   Because: mood match (+1.0); energy 0.76 vs target 0.90 (+0.86); acousticness 0.35 (+0.33)
5. Storm Runner by Voltline [rock/intense] - Score: 1.44
   Because: energy 0.91 vs target 0.90 (+0.99); acousticness 0.10 (+0.45)
```

```
=== Chill Lofi ===
Profile: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.35, 'likes_acoustic': True}
1. Library Rain by Paper Lanterns [lofi/chill] - Score: 4.43
   Because: genre match (+2.0); mood match (+1.0); energy 0.35 vs target 0.35 (+1.00); acousticness 0.86 (+0.43)
2. Midnight Coding by LoRoom [lofi/chill] - Score: 4.29
   Because: genre match (+2.0); mood match (+1.0); energy 0.42 vs target 0.35 (+0.93); acousticness 0.71 (+0.35)
3. Focus Flow by LoRoom [lofi/focused] - Score: 3.34
   Because: genre match (+2.0); energy 0.40 vs target 0.35 (+0.95); acousticness 0.78 (+0.39)
4. Spacewalk Thoughts by Orbit Bloom [ambient/chill] - Score: 2.39
   Because: mood match (+1.0); energy 0.28 vs target 0.35 (+0.93); acousticness 0.92 (+0.46)
5. Coffee Shop Stories by Slow Stereo [jazz/relaxed] - Score: 1.43
   Because: energy 0.37 vs target 0.35 (+0.98); acousticness 0.89 (+0.45)
```

```
=== Deep Intense Rock ===
Profile: {'genre': 'rock', 'mood': 'intense', 'energy': 0.92, 'likes_acoustic': False}
1. Storm Runner by Voltline [rock/intense] - Score: 4.44
   Because: genre match (+2.0); mood match (+1.0); energy 0.91 vs target 0.92 (+0.99); acousticness 0.10 (+0.45)
2. Gym Hero by Max Pulse [pop/intense] - Score: 2.46
   Because: mood match (+1.0); energy 0.93 vs target 0.92 (+0.99); acousticness 0.05 (+0.47)
3. Laser Cathedral by Pulse Nine [edm/euphoric] - Score: 1.46
   Because: energy 0.95 vs target 0.92 (+0.97); acousticness 0.03 (+0.48)
4. Iron Tide by Blackfurnace [metal/angry] - Score: 1.43
   Because: energy 0.97 vs target 0.92 (+0.95); acousticness 0.04 (+0.48)
5. Sunrise City by Neon Echo [pop/happy] - Score: 1.31
   Because: energy 0.82 vs target 0.92 (+0.90); acousticness 0.18 (+0.41)
```

```
=== Conflicting (high energy but sad) ===
Profile: {'genre': 'folk', 'mood': 'sad', 'energy': 0.9, 'likes_acoustic': True}
1. Porch Light by Hollis Reed [folk/sad] - Score: 3.86
   Because: genre match (+2.0); mood match (+1.0); energy 0.30 vs target 0.90 (+0.40); acousticness 0.93 (+0.47)
2. Rain On Glass by Elena Voss [classical/sad] - Score: 1.75
   Because: mood match (+1.0); energy 0.18 vs target 0.90 (+0.28); acousticness 0.95 (+0.47)
3. Storm Runner by Voltline [rock/intense] - Score: 1.04
   Because: energy 0.91 vs target 0.90 (+0.99); acousticness 0.10 (+0.05)
4. Calle Sol by Los Faroles [latin/happy] - Score: 1.04
   Because: energy 0.80 vs target 0.90 (+0.90); acousticness 0.28 (+0.14)
5. Rooftop Lights by Indigo Parade [indie pop/happy] - Score: 1.03
   Because: energy 0.76 vs target 0.90 (+0.86); acousticness 0.35 (+0.17)
```

```
=== Genre not in catalog (k-pop) ===
Profile: {'genre': 'k-pop', 'mood': 'happy', 'energy': 0.8, 'likes_acoustic': False}
1. Sunrise City by Neon Echo [pop/happy] - Score: 2.39
   Because: mood match (+1.0); energy 0.82 vs target 0.80 (+0.98); acousticness 0.18 (+0.41)
2. Calle Sol by Los Faroles [latin/happy] - Score: 2.36
   Because: mood match (+1.0); energy 0.80 vs target 0.80 (+1.00); acousticness 0.28 (+0.36)
3. Rooftop Lights by Indigo Parade [indie pop/happy] - Score: 2.29
   Because: mood match (+1.0); energy 0.76 vs target 0.80 (+0.96); acousticness 0.35 (+0.33)
4. Concrete Crown by Kid Meridian [hip hop/confident] - Score: 1.42
   Because: energy 0.78 vs target 0.80 (+0.98); acousticness 0.12 (+0.44)
5. Gym Hero by Max Pulse [pop/intense] - Score: 1.34
   Because: energy 0.93 vs target 0.80 (+0.87); acousticness 0.05 (+0.47)
```

**Screenshot or video** *(optional)*: not included.

---

## Experiments You Tried

**Weight shift: genre 2.0 → 1.0 and energy 1.0 → 2.0.** Output:

```
##### EXPERIMENT: genre weight 2.0 -> 1.0, energy weight 1.0 -> 2.0 #####

=== High-Energy Pop (shifted weights) ===
Profile: {'genre': 'pop', 'mood': 'happy', 'energy': 0.9, 'likes_acoustic': False}
1. Sunrise City by Neon Echo [pop/happy] - Score: 4.25
   Because: genre match (+1.0); mood match (+1.0); energy 0.82 vs target 0.90 (+1.84); acousticness 0.18 (+0.41)
2. Gym Hero by Max Pulse [pop/intense] - Score: 3.42
   Because: genre match (+1.0); energy 0.93 vs target 0.90 (+1.94); acousticness 0.05 (+0.47)
3. Calle Sol by Los Faroles [latin/happy] - Score: 3.16
   Because: mood match (+1.0); energy 0.80 vs target 0.90 (+1.80); acousticness 0.28 (+0.36)
4. Rooftop Lights by Indigo Parade [indie pop/happy] - Score: 3.04
   Because: mood match (+1.0); energy 0.76 vs target 0.90 (+1.72); acousticness 0.35 (+0.33)
5. Storm Runner by Voltline [rock/intense] - Score: 2.43
   Because: energy 0.91 vs target 0.90 (+1.98); acousticness 0.10 (+0.45)

=== Chill Lofi (shifted weights) ===
Profile: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.35, 'likes_acoustic': True}
1. Library Rain by Paper Lanterns [lofi/chill] - Score: 4.43
   Because: genre match (+1.0); mood match (+1.0); energy 0.35 vs target 0.35 (+2.00); acousticness 0.86 (+0.43)
2. Midnight Coding by LoRoom [lofi/chill] - Score: 4.21
   Because: genre match (+1.0); mood match (+1.0); energy 0.42 vs target 0.35 (+1.86); acousticness 0.71 (+0.35)
3. Spacewalk Thoughts by Orbit Bloom [ambient/chill] - Score: 3.32
   Because: mood match (+1.0); energy 0.28 vs target 0.35 (+1.86); acousticness 0.92 (+0.46)
4. Focus Flow by LoRoom [lofi/focused] - Score: 3.29
   Because: genre match (+1.0); energy 0.40 vs target 0.35 (+1.90); acousticness 0.78 (+0.39)
5. Coffee Shop Stories by Slow Stereo [jazz/relaxed] - Score: 2.40
   Because: energy 0.37 vs target 0.35 (+1.96); acousticness 0.89 (+0.45)
```

What I saw:

- **High-Energy Pop:** the same five songs in the same order. The scores moved, though. The gap between Gym Hero (pop, intense) and Calle Sol (latin, happy) shrank from 1.18 to 0.26, so the order is much less certain than it looks.
- **Chill Lofi:** the order changed. Spacewalk Thoughts (ambient, chill) moved above Focus Flow (lofi, focused), because the mood match and the energy match are now worth more than the lofi label. I think this list is slightly better, since it is less stuck on one genre. It is different, not clearly more accurate, because I have no listener to check against.

I also reasoned through removing the mood check: Gym Hero would stay near the top for the happy pop user, because it wins on genre and energy alone.

---

## Limitations and Risks

- The catalog is tiny. Most genres have one song, so a genre match only helps the single user whose favorite genre has a song.
- Genre and mood are exact text matches. "indie pop" gets no credit for "pop", and "chill" gets no credit for "relaxed", so Rooftop Lights (indie pop, happy) is treated as a non-pop song for a pop fan.
- Genre and mood points are so large that they can beat the energy preference. The "high energy but sad" folk profile got a 0.30-energy song at #1 even though the target was 0.9.
- It cannot see lyrics, language, artist, or anything about the listener's history, and it never adds variety, so it can create a filter bubble.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

I learned that a recommender is just a score plus a sort, and that most of the behavior comes from the weights I chose. When I read my own reasons lists, the cause of every surprising result was visible in the numbers, which made problems easy to find. Bias showed up in places I did not plan for: the way I wrote genre as exact text, and how many songs I had per genre, decided who got good recommendations.
