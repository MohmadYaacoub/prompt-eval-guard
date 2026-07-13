#!/usr/bin/env python3
"""gen_cases.py — propose candidate eval cases straight from a prompt itself.

This kills the biggest friction in prompt evaluation: staring at a blank
cases.jsonl and not knowing what to write. Point it at the prompt you're about
to change and it derives a starter test set that covers the happy path, every
explicit rule stated in the prompt, the required output format, empty/malformed
input, and an adversarial/off-task input.

Usage:
    python scripts/gen_cases.py --prompt prompts/system.txt
    python scripts/gen_cases.py --prompt prompts/system.txt --out evals/cases.jsonl --n 10

Generated cases are a STARTING POINT, not ground truth. Read them, fix the ones
that are wrong, delete the ones that don't matter, then commit. The runner
(run_eval.py) consumes the same JSONL schema this emits.
"""
from __future__ import annotations

import argparse
import json
import sys

from model import call_model  # wire your provider once in scripts/model.py

VALID_CHECKS = {"exact", "contains", "is_json", "max_words", "regex", "judge"}

GEN_SYSTEM = """You design regression test cases for an LLM prompt.

You are given the prompt that is under test. Derive a set of test cases that
would catch a regression if the prompt were changed carelessly.

Output ONLY JSON Lines: one JSON object per line, no prose, no code fences.
Each line has exactly:
  {"id": "<kebab-case-id>", "input": "<the user input to send>", "check": {...}}

check.type must be one of:
  {"type": "exact",     "value": "<exact expected output>"}
  {"type": "contains",  "value": "<substring the output must contain>"}
  {"type": "is_json"}                                  # output must parse as JSON
  {"type": "max_words", "value": <int>}                # output <= N words
  {"type": "regex",     "value": "<python regex>"}
  {"type": "judge",     "rubric": "<binary pass/fail behavior, state the failure>"}

Coverage requirements — include at least one case for each that applies:
  1. Happy path: a clear, typical input the prompt is meant to handle well.
  2. One case per explicit rule or constraint stated in the prompt.
  3. Any required output format (JSON shape, length limit, required phrase).
  4. Empty or malformed input.
  5. An adversarial / off-task input that tries to derail the prompt.

Rules:
  - Prefer the cheapest valid grader: deterministic (exact/contains/is_json/
    max_words/regex) over judge. Use judge only for open-ended behavior.
  - For judge rubrics, describe the PASSING behavior and name the failure
    ("Fails if it invents a value"). Keep it binary.
  - Make inputs realistic, not placeholders.
  - Give each case a short, descriptive kebab-case id."""


def parse_jsonl(text: str) -> list:
    cases = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("```"):
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # tolerate stray prose the model may add
    return cases


def problem_with(obj) -> str | None:
    if not isinstance(obj, dict):
        return "not a JSON object"
    if "input" not in obj:
        return "missing 'input'"
    check = obj.get("check")
    if not isinstance(check, dict) or check.get("type") not in VALID_CHECKS:
        return "missing or unknown 'check.type'"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Propose eval cases from a prompt.")
    ap.add_argument("--prompt", required=True, help="path to the prompt under test")
    ap.add_argument("--out", help="append cases to this file (else print to stdout)")
    ap.add_argument("--n", type=int, default=8, help="roughly how many cases to ask for")
    args = ap.parse_args()

    with open(args.prompt, encoding="utf-8") as fh:
        prompt = fh.read()

    raw = call_model(
        GEN_SYSTEM,
        f"PROMPT UNDER TEST:\n\n{prompt}\n\nPropose about {args.n} cases now.",
    )

    good = []
    for i, obj in enumerate(parse_jsonl(raw)):
        err = problem_with(obj)
        if err:
            print(f"# skipped a candidate ({err})", file=sys.stderr)
            continue
        obj.setdefault("id", f"case-{i + 1}")
        # keep only the keys the runner understands, in a stable order
        good.append({"id": obj["id"], "input": obj.get("input", ""), "check": obj["check"]})

    if not good:
        print("No valid cases produced. Check that call_model is wired up.", file=sys.stderr)
        return 1

    rendered = "\n".join(json.dumps(o, ensure_ascii=False) for o in good)
    if args.out:
        with open(args.out, "a", encoding="utf-8") as fh:
            fh.write(rendered + "\n")
        print(f"Appended {len(good)} candidate case(s) to {args.out}.")
        print("Review them before trusting — generated cases are a starting point.")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
