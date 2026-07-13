#!/usr/bin/env python3
"""model.py — the single place to wire prompt-eval-guard to your LLM provider.

Both run_eval.py (scoring) and gen_cases.py (auto-generating test cases) import
`call_model` from here, so you wire your provider ONCE.

For a zero-setup demo, set the env var PROMPT_EVAL_MODEL=mock to use a tiny
offline stand-in (see `_mock_model`). Drop it for real evals.
"""
from __future__ import annotations

import os


def call_model(system_prompt: str, user_input: str) -> str:
    """Return the model's text output for (system_prompt, user_input)."""
    if os.environ.get("PROMPT_EVAL_MODEL", "").lower() == "mock":
        return _mock_model(system_prompt, user_input)
    return _live_model(system_prompt, user_input)


def _live_model(system_prompt: str, user_input: str) -> str:
    """Replace the body with a real call.

    Example for the Anthropic SDK (`pip install anthropic`, set ANTHROPIC_API_KEY):

        from anthropic import Anthropic
        _client = Anthropic()
        msg = _client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_input}],
        )
        return msg.content[0].text

    Example for the OpenAI SDK (`pip install openai`, set OPENAI_API_KEY):

        from openai import OpenAI
        _client = OpenAI()
        resp = _client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
        )
        return resp.choices[0].message.content
    """
    raise NotImplementedError(
        "Wire _live_model() in scripts/model.py to your LLM provider, "
        "or set PROMPT_EVAL_MODEL=mock to try the offline demo. See the docstring."
    )


def _mock_model(system_prompt: str, user_input: str) -> str:
    """A tiny deterministic stand-in used ONLY for the zero-setup demo
    (PROMPT_EVAL_MODEL=mock). It is NOT a real model — it follows two obvious
    rules so the example test-drive produces a genuine regression table:

      - On empty input, it emits the "Please provide input." reply ONLY if the
        system prompt explicitly defines that rule. A prompt that dropped the
        rule therefore regresses the empty-input case.
      - Otherwise it answers "tersely" by echoing the first 20 words of input.
    """
    text = user_input.strip()
    if not text:
        if "please provide input" in system_prompt.lower():
            return "Please provide input."
        return ""
    return " ".join(text.split()[:20])
