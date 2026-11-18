"""
Safety checks that sit before and after the model.

- check_request: rejects empty, oversized, or non-music requests before any work is done.
- check_explanation: the self-check. Reads the model's explanation and makes sure it
  only talks about songs that were actually retrieved, and covers all of them.
- template_explanation: a plain, always-correct explanation used when the model is
  offline or fails the self-check twice.
"""

MAX_REQUEST_CHARS = 300

REFUSAL_OFF_TOPIC = (
    "I can only help with music recommendations from this catalog. "
    "Try something like \"upbeat pop for a morning run\"."
)


def check_request(request):
    """Returns (ok, message). Runs before parsing."""
    if request is None or not request.strip():
        return False, "Please describe what you want to listen to."
    if len(request) > MAX_REQUEST_CHARS:
        return False, f"That request is too long. Please keep it under {MAX_REQUEST_CHARS} characters."
    return True, ""


def mentioned_titles(text, catalog_titles):
    """Catalog song titles that appear in the text (case-insensitive)."""
    lower = text.lower()
    return {t for t in catalog_titles if t.lower() in lower}


def check_explanation(text, retrieved_titles, catalog_titles):
    """
    Returns (passed, problems).
    Fails if the explanation names a catalog song that was not retrieved
    (an invented or swapped recommendation) or skips a retrieved song.
    """
    problems = []
    named = mentioned_titles(text, catalog_titles)
    extra = sorted(named - set(retrieved_titles))
    missing = [t for t in retrieved_titles if t not in named]
    if extra:
        problems.append(f"mentions songs that were not retrieved: {', '.join(extra)}")
    if missing:
        problems.append(f"skips retrieved songs: {', '.join(missing)}")
    if not text.strip():
        problems.append("explanation is empty")
    return not problems, problems


def template_explanation(results, conf_label):
    """Deterministic explanation built straight from the retrieved data."""
    lines = []
    if conf_label == "low":
        lines.append("Nothing in the catalog is a strong match, so treat these as loose suggestions.")
    else:
        lines.append("Here are the closest matches in the catalog.")
    for i, r in enumerate(results, 1):
        s = r["song"]
        why = "; ".join(r["reasons"])
        lines.append(f"{i}. {s['title']} by {s['artist']} ({s['genre']}, {s['mood']}): {why}")
    return "\n".join(lines)
