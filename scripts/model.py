#!/usr/bin/env python3
"""model.py — the single place to wire prompt-eval-guard to your LLM provider.

Both run_eval.py (scoring) and gen_cases.py (auto-generating test cases) import
`call_model` from here, so you only wire your provider ONCE.
"""
from __future__ import annotations


def call_model(system_prompt: str, user_input: str) -> str:
    """Return the model's text output for (system_prompt, user_input).

    Replace the body with a real call. Example for the Anthropic SDK
    (`pip install anthropic`, set ANTHROPIC_API_KEY):

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
        "Wire call_model() in scripts/model.py to your LLM provider. See the docstring."
    )
