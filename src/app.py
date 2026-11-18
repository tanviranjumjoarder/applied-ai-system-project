"""
VibeFinder 2.0 command line app.

    python -m src.app "something calm for a rainy study night"
    python -m src.app                      # interactive mode
    python -m src.app --offline "..."      # skip Gemini (rules + template)
"""

import argparse
import os

from src.llm import make_client
from src.pipeline import ROOT, VibeFinder, setup_logging


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, ".env"))
    except ImportError:
        pass


def format_result(r):
    out = [f"Request: {r.request}"]
    if r.refused:
        out.append(f"VibeFinder: {r.message}")
        if r.profile is not None:
            out.append(f"(parser: {r.parser})")
        return "\n".join(out)

    p = r.profile
    acoustic = {True: "yes", False: "no", None: "no preference"}[p["likes_acoustic"]]
    out.append(
        f"Understood as: genre={p['genre'] or 'any'}, mood={p['mood'] or 'any'}, "
        f"energy={p['energy']}, acoustic={acoustic}, keywords={p['keywords']}  (parser: {r.parser})"
    )
    for note in r.parse_notes:
        out.append(f"  ! {note}")
    out.append(f"Confidence: {r.confidence:.2f} ({r.confidence_label})")
    out.append("")
    out.append(r.explanation)
    out.append("")
    check = "passed" if r.check_passed else "FAILED -> used template" if r.check_passed is False else "n/a"
    out.append(f"[explainer: {r.explainer} | grounding self-check: {check}]")
    for prob in r.check_problems:
        out.append(f"  ! {prob}")
    out.append("Scores: " + ", ".join(f"{x['song']['title']} {x['score']:.2f}" for x in r.recommendations))
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="VibeFinder 2.0 music recommender")
    parser.add_argument("request", nargs="*", help="what you want to listen to")
    parser.add_argument("--offline", action="store_true", help="do not call Gemini")
    args = parser.parse_args()

    load_env()
    setup_logging()
    llm = None if args.offline else make_client()
    if llm is None:
        print("(offline mode: rule-based parser and template explanations)\n")
    bot = VibeFinder(llm=llm)

    if args.request:
        print(format_result(bot.recommend(" ".join(args.request))))
        return

    print("VibeFinder 2.0. Describe what you want to hear, or press Enter to quit.")
    while True:
        try:
            request = input("\n> ").strip()
        except EOFError:
            break
        if not request:
            break
        print(format_result(bot.recommend(request)))


if __name__ == "__main__":
    main()
