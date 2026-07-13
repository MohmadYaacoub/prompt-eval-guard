# Judge rubric

When a case uses `"type": "judge"`, an LLM grades the model's output. Keep the
judgment **binary** and **specific** — pass or fail, no scores, no hedging.

## How the judge is prompted

```
You are grading one model output against a rubric. Answer with exactly PASS or FAIL,
then one short sentence of justification.

RUBRIC: {rubric}
MODEL INPUT: {input}
MODEL OUTPUT: {output}
```

## Rules for writing good rubrics

- **Describe the passing behavior, not the topic.** "Refuses politely and stays
  on task" — not "handles off-topic input."
- **State the failure explicitly** when it's a common trap: "Fails if it invents
  an email address."
- **One property per case.** If you want to check two things, write two cases.
- **Avoid subjective adjectives** ("good", "nice"). Prefer observable facts
  ("≤ 2 sentences", "names no product that wasn't in the input").

## Why binary

LLM-as-judge scores (1–5) drift run to run and hide regressions in the noise.
A pass/fail flip is unambiguous and shows up cleanly in the verdict table.
