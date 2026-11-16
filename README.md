# Variance Commentary: Prompt and Automated Evaluation

A small Python project that asks an LLM to write Budget vs Actual variance commentary for a finance manager, then checks the output automatically.

Status: work in progress. The checks below cover two of the quality criteria; the others are still reviewed by hand.

## Why

Variance commentary is a routine month-end task. An LLM can draft it quickly, but in finance a confident sentence with a wrong or invented number is worse than no sentence. This project tests how far a prompt can be trusted, with numbers instead of impressions.

## Design rule

All figures are calculated in code before the model sees them. The script builds each table (Budget, Actual, Variance, Variance %, Total) from the source data with pandas. The model is asked only to report and comment, never to calculate.

## How it works

`run_eval.py` does the following:

1. Reads six monthly CSV files from the `data` folder and appends them (72 rows).
2. Builds one table per department per month: 3 departments x 6 months = 18 test tables.
3. Sends the prompt and each table to the Claude API (`claude-sonnet-5-5`), 3 runs per table = 54 calls.
4. Checks every response:
   - Numbers check: every number in the response must appear in the input table. Any other number is reported.
   - Language check: the response must not contain Chinese characters (the prompt is written in Chinese and asks for English output).
5. Saves every response and its check results to `results.csv`.

## Results (17 November 2026)

| Check | Result |
|---|---|
| Calls | 54 (18 tables x 3 runs) |
| Response in English | 54 of 54 |
| No numbers outside the input table | 53 of 54 |

The one numbers failure (Sales, February, run 2): the model summarised -9.87% and +11.59% as "roughly 10%". The figure 10% is not in the table, so the check flagged it.

### What the evaluation found

- An earlier 18-call run (1 run per table, results file not kept) returned one response in Chinese. Manual testing at 3 runs per prompt version had never shown this. After adding one sentence to the prompt asking for English output, 0 of 54 responses contained Chinese.
- The same prompt behaved differently through the API than in the chat product where it was first developed (for example, some responses were formatted as emails). Results from one environment do not carry over to another without re-testing.

## Limitations

- The numbers check confirms that each number exists in the table. It does not confirm the number is attached to the right category.
- Not yet automated: whether the largest variances are identified correctly, whether the response gives unsupported reasons for a variance, and response length and format.
- Years, counts and similar non-financial numbers in a response would be flagged as false positives.
- The data is synthetic: 3 departments, 4 cost categories, January to June 2026.

## Prompt development

The prompt was developed one change at a time, re-testing after each change:

| Version | Change | Problem it addressed |
|---|---|---|
| V1 | Basic instruction | Baseline |
| V2 | Do not calculate | Model produced figures that were not in the table |
| V3 | Do not guess unsupported reasons | Model suggested possible causes |
| V4 | Report largest variance by amount and by percentage | "Largest" was ambiguous |
| V5 | Report over-budget and under-budget separately | Only the favourable variance was reported |
| V6 | Plain, non-templated wording | Stock phrases |
| V7 | Confirm output language is English | 1 of 18 responses in Chinese |

## How to run

You need a Claude API key in the `ANTHROPIC_API_KEY` environment variable. The key is not stored in this repository.

```
pip install anthropic pandas
python run_eval.py
```

## Notes

The Python code was written with AI coding assistance. I designed the checks, ran the experiments and reviewed the results.
