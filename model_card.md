# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

VibeFinder suggests 5 songs from a small catalog based on a user's favorite genre, favorite mood, target energy and acoustic preference. It assumes the user can describe their taste in those four things. It is for classroom exploration only. It is not meant for real listeners or a real music app.

**Not intended for:** ranking real artists, deciding what real people hear, or any use where unfair results could cost someone money or exposure.

---

## 3. How the Model Works

Each song gets points for how well it fits the user:

- 2 points if the genre is the user's favorite.
- 1 point if the mood is the user's favorite.
- Up to 1 point for energy. A song with exactly the energy the user wants gets the full point. The further away it is, the fewer points it gets.
- Up to half a point for acousticness. Users who like acoustic music get points for acoustic songs, and everyone else gets points for non-acoustic songs.

Then it sorts all songs by points and shows the top 5, with a reason for each point it gave. The starter code only had empty functions, so all of this logic is mine. I chose the weights from the recipe in the assignment (genre 2.0, mood 1.0) and added the acoustic rule myself.

---

## 4. Data

The catalog has 20 songs. 10 came with the starter file and I added 10 more (hip hop, classical, country, metal, r&b, reggae, edm, folk, latin, blues) so there are more genres and moods. There are 17 genres. Lofi has 3 songs, pop has 2 and every other genre has 1. Moods include happy, chill, intense, sad, angry, romantic and more.

Missing: lyrics, language, artist popularity, decade, and anything about how people actually listen. Tempo, valence and danceability are in the file but I do not use them. The songs are made up, so the data says nothing about real taste.

---

## 5. Strengths

- It works well for users whose genre and mood both exist in the catalog. Chill Lofi got Library Rain and Midnight Coding on top, and Deep Intense Rock got Storm Runner, which is what I expected.
- Every result comes with reasons, so I can see exactly why a song ranked where it did.
- When the favorite genre is not in the catalog (k-pop), it still gives sensible happy, high-energy songs by using mood and energy.

---

## 6. Limitations and Bias

The biggest weakness I found is that the genre and mood points are large and all-or-nothing, so they can overrule what the user said about energy. The profile "high energy but sad, folk, acoustic" asked for energy 0.9. The #1 song was Porch Light, a quiet folk song with energy 0.30, because the genre match and mood match gave it 3 points before energy was counted. The system also treats "indie pop" as having nothing to do with "pop", and "chill" as unrelated to "relaxed", because it compares exact words. Most genres have only one song, so a user with a rare favorite genre gets one good match and then four songs picked only by energy. Gym Hero (pop, intense) shows up second for a happy pop fan because it matches the genre and the energy, even though the mood is wrong. This favors users whose taste fits the catalog's common labels and gives less useful results to everyone else. There is also no variety rule, so the top 5 can be very similar, which is how a filter bubble starts.

---

## 7. Evaluation

I tested five profiles: High-Energy Pop, Chill Lofi, Deep Intense Rock, a conflicting profile (folk, sad, energy 0.9), and a profile with a genre that is not in the catalog (k-pop). I looked at whether the top results matched my own sense of the vibe and whether the reasons made sense.

Comparisons between profiles:

- **Pop vs Lofi:** pop leads with Sunrise City (energy 0.82) and lofi leads with Library Rain (energy 0.35). The energy target moves the whole list from loud to quiet, which makes sense.
- **Pop vs Rock:** both high energy, so Gym Hero shows up in both lists. For rock it is #2 only because of the "intense" mood, and the rock list then fills with other loud songs from other genres (EDM, metal) because rock has only one song.
- **Lofi vs Conflicting folk:** both want acoustic songs, but the folk profile's high energy target pulled in Storm Runner and Calle Sol, which are not acoustic at all, so its lists below the top two are mostly about energy.
- **Pop vs k-pop:** same happy, high-energy target, but without a genre match the k-pop list has smaller gaps between songs (2.39, 2.36, 2.29), so the order is almost arbitrary.

The experiment (genre 2.0 → 1.0, energy 1.0 → 2.0) kept the pop list in the same order but made the scores closer together, and it moved Spacewalk Thoughts above Focus Flow in the lofi list. I think that was different rather than more accurate.

What surprised me: how often a song that is clearly wrong by mood (Gym Hero) lands near the top just because of genre and energy.

I also wrote tests for the scoring and the CSV loading (5 tests pass).

---

## 8. Future Work

- Count related genres and moods as partial matches (indie pop is close to pop, chill is close to relaxed).
- Use tempo, valence and danceability, and let the user say which features matter most.
- Add a diversity rule so the top 5 are not all the same genre or artist, and add many more songs per genre.

---

## 9. Personal Reflection

My biggest learning moment was seeing that the "high energy but sad" profile got a quiet song at #1. The score looked reasonable on paper, but the weights quietly decided that genre and mood matter more than energy. I used an AI coding assistant to draft the functions from my recipe, to suggest edge-case profiles, and to help explain results. I checked its work by reading the reasons it printed for each song and by running the tests, and the reasons list was what let me catch the problems. What surprised me is how a few additions and a sort already feel like a real recommendation, and also how fast it breaks when the data has only one song per genre. If I kept going, I would add partial matches for similar genres and a variety rule for the top results.
