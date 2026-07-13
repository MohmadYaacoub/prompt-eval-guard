#!/usr/bin/env python3
"""
run_eval.py — run an OLD and a NEW prompt over a saved test set, score both,
and print a side-by-side verdict. Exits non-zero if any case regressed, so it
drops straight into a pre-commit hook or CI job.

Usage:
    python scripts/run_eval.py --old prompts/old.txt --new prompts/new.txt \
        --cases evals/cases.jsonl

The model call is intentionally pluggable: fill in `call_model` for your
provider (Anthropic, OpenAI, a local model, whatever). Everything else —
running both prompts, grading, and the regression check — is provider-agnostic.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass

from model import call_model  # wire your provider once in scripts/model.py


def judge(rubric: str, user_input: str, output: str) -> bool:
    """LLM-as-judge: return True if `output` satisfies `rubric`. Binary only."""
    verdict = call_model(
        system_prompt=(
            "You are grading one model output against a rubric. Reply with exactly "
            "PASS or FAIL as the first word, then one short justifying sentence."
        ),
        user_input=f"RUBRIC: {rubric}\n\nMODEL INPUT: {user_input}\n\nMODEL OUTPUT: {output}",
    )
    return verdict.strip().upper().startswith("PASS")


# --------------------------------------------------------------------------- #
#  Deterministic graders
# --------------------------------------------------------------------------- #
def grade(check: dict, user_input: str, output: str) -> bool:
    kind = check["type"]
    if kind == "exact":
        return output.strip() == str(check["value"]).strip()
    if kind == "contains":
        return str(check["value"]).lower() in output.lower()
    if kind == "is_json":
        try:
            json.loads(output)
            return True
        except (ValueError, TypeError):
            return False
    if kind == "max_words":
        return len(output.split()) <= int(check["value"])
    if kind == "regex":
        return re.search(str(check["value"]), output) is not None
    if kind == "judge":
        return judge(check["rubric"], user_input, output)
    raise ValueError(f"Unknown check type: {kind!r}")


# --------------------------------------------------------------------------- #
@dataclass
class Row:
    case_id: str
    old_pass: bool
    new_pass: bool

    @property
    def delta(self) -> str:
        if self.old_pass and not self.new_pass:
            return "⚠ REGRESSION"
        if not self.old_pass and self.new_pass:
            return "fixed"
        return "—"


def load_cases(path: str) -> list[dict]:
    cases = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                sys.exit(f"Bad JSON on {path}:{lineno}: {exc}")
    return cases


def read_prompt(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main() -> int:
    ap = argparse.ArgumentParser(description="Regression-check a prompt change.")
    ap.add_argument("--old", required=True, help="path to the current/old prompt")
    ap.add_argument("--new", required=True, help="path to the proposed/new prompt")
    ap.add_argument("--cases", required=True, help="path to evals/cases.jsonl")
    args = ap.parse_args()

    old_prompt = read_prompt(args.old)
    new_prompt = read_prompt(args.new)
    cases = load_cases(args.cases)

    rows: list[Row] = []
    for case in cases:
        inp = case.get("input", "")
        check = case["check"]
        old_out = call_model(old_prompt, inp)
        new_out = call_model(new_prompt, inp)
        rows.append(
            Row(
                case_id=case.get("id", "?"),
                old_pass=grade(check, inp, old_out),
                new_pass=grade(check, inp, new_out),
            )
        )

    # ---- verdict table ---------------------------------------------------- #
    width = max((len(r.case_id) for r in rows), default=4)
    tick = {True: "✅", False: "❌"}
    print(f"{'CASE'.ljust(width)}   OLD   NEW   Δ")
    for r in rows:
        print(f"{r.case_id.ljust(width)}   {tick[r.old_pass]}    {tick[r.new_pass]}    {r.delta}")

    fixed = sum(1 for r in rows if not r.old_pass and r.new_pass)
    regressed = sum(1 for r in rows if r.old_pass and not r.new_pass)
    unchanged = len(rows) - fixed - regressed
    print(f"\nNet: +{fixed} fixed, {regressed} regressed, {unchanged} unchanged")

    if regressed:
        print("\n⚠  DO NOT SHIP — the new prompt regressed at least one case.")
        return 1
    if fixed:
        print("\n✅  Safe to ship — fixes with no regressions.")
    else:
        print("\n–  No measured change from this edit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
