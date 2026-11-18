"""
Evaluation harness for VibeFinder 2.0.

Runs every case in evaluation/test_cases.json through the full pipeline and checks:
- refusal:   refused exactly when it should
- genre:     the parsed genre matches the expected one (when the case gives one)
- top-1:     the #1 song is one a human marked as acceptable
- grounded:  the explanation passed the self-check (no invented or skipped songs)
It also re-runs a few requests to check the ranking is consistent.

    python -m src.evaluate            # uses Gemini if a key is set
    python -m src.evaluate --offline  # rules + template only

Results are printed and saved to evaluation/results_<mode>.md
"""

import argparse
import json
import os
import time

from src.app import load_env
from src.guardrails import check_explanation
from src.llm import make_client
from src.pipeline import ROOT, VibeFinder, setup_logging

CASES_PATH = os.path.join(ROOT, "evaluation", "test_cases.json")
CONSISTENCY_REQUESTS = [
    "something calm for a rainy study night",
    "hype rap for the gym",
    "music for a beach day with friends",
]


def mark(ok):
    return "Pass" if ok else "**Fail**"


def evaluate_case(bot, case):
    r = bot.recommend(case["request"])
    row = {"request": case["request"] or "(empty)", "checks": {}, "result": r}

    row["checks"]["refusal"] = r.refused == case["expect_refusal"]
    if case["expect_refusal"] or r.refused:
        row["top1"] = "(refused)"
        return row

    if "expect_genre" in case:
        row["checks"]["genre"] = r.profile["genre"] == case["expect_genre"]
    top1 = r.recommendations[0]["song"]["title"]
    row["top1"] = top1
    row["checks"]["top-1"] = top1 in case["acceptable_top1"]
    # Grounded = the explanation the user actually sees names only retrieved songs.
    # (A template fallback is grounded by construction; the Explainer column shows when it was used.)
    retrieved = [x["song"]["title"] for x in r.recommendations]
    row["checks"]["grounded"] = check_explanation(r.explanation, retrieved, bot.titles)[0]
    return row


def run(offline, pause):
    load_env()
    setup_logging()
    llm = None if offline else make_client()
    mode = "offline" if llm is None else "live"
    bot = VibeFinder(llm=llm)
    cases = json.load(open(CASES_PATH, encoding="utf-8"))

    rows = []
    for case in cases:
        rows.append(evaluate_case(bot, case))
        if llm is not None:
            time.sleep(pause)  # stay under the free-tier rate limit

    consistency = []
    for request in CONSISTENCY_REQUESTS:
        first = [x["song"]["title"] for x in bot.recommend(request).recommendations]
        if llm is not None:
            time.sleep(pause)
        second = [x["song"]["title"] for x in bot.recommend(request).recommendations]
        consistency.append((request, first == second, first, second))
        if llm is not None:
            time.sleep(pause)

    return mode, rows, consistency


def to_markdown(mode, rows, consistency):
    lines = [f"# Evaluation results ({mode})", ""]
    lines.append("| # | Request | Parser | Top pick | Confidence | Explainer | Checks | Result |")
    lines.append("|---|---------|--------|----------|------------|-----------|--------|--------|")
    totals = {}
    for i, row in enumerate(rows, 1):
        r = row["result"]
        for name, ok in row["checks"].items():
            passed, seen = totals.get(name, (0, 0))
            totals[name] = (passed + ok, seen + 1)
        all_ok = all(row["checks"].values())
        checks = ", ".join(f"{k} {'ok' if v else 'FAIL'}" for k, v in row["checks"].items())
        conf = "-" if r.refused else f"{r.confidence:.2f} {r.confidence_label}"
        parser = r.parser or "guardrail"
        explainer = r.explainer or "-"
        lines.append(
            f"| {i} | {row['request']} | {parser} | {row['top1']} | {conf} | {explainer} | {checks} | {mark(all_ok)} |"
        )

    passed_cases = sum(all(row["checks"].values()) for row in rows)
    lines += ["", "## Summary", ""]
    lines.append(f"- Cases fully passed: **{passed_cases} / {len(rows)}**")
    for name, (passed, seen) in totals.items():
        lines.append(f"- {name}: {passed} / {seen}")
    answered = [row["result"] for row in rows if not row["result"].refused]
    if answered:
        avg = sum(r.confidence for r in answered) / len(answered)
        lines.append(f"- Average confidence on answered requests: {avg:.2f}")
        retries = sum(1 for r in answered if "retry" in r.explainer or "fallback" in r.explainer)
        lines.append(f"- Explanations that needed a retry or fallback: {retries} / {len(answered)}")
    same = sum(1 for c in consistency if c[1])
    lines.append(f"- Consistency (same top 5 on a repeat run): {same} / {len(consistency)}")
    for request, ok, first, second in consistency:
        if not ok:
            lines.append(f"  - \"{request}\": {first} vs {second}")

    failures = [row for row in rows if not all(row["checks"].values())]
    if failures:
        lines += ["", "## Failures in detail", ""]
        for row in failures:
            r = row["result"]
            lines.append(f"- **{row['request']}**: profile {r.profile}; top 3 "
                         f"{[(x['song']['title'], x['score']) for x in r.recommendations[:3]]}; "
                         f"notes {r.parse_notes or 'none'}; self-check problems {r.check_problems or 'none'}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--pause", type=float, default=4.5, help="seconds between live calls (free tier allows 15 per minute)")
    args = parser.parse_args()

    mode, rows, consistency = run(args.offline, args.pause)
    report = to_markdown(mode, rows, consistency)
    out = os.path.join(ROOT, "evaluation", f"results_{mode}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"Saved to {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
