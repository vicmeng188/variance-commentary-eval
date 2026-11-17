# Variance Commentary: Prompt and Automated Evaluation

A small Python project that asks an LLM to write Budget vs Actual variance commentary for a finance manager, then checks the output automatically.

Status: work in progress. Three checks are automated; the remaining quality criteria are still reviewed by hand.

## Why

Variance commentary is a routine month-end task. An LLM can draft it quickly, but in finance a confident sentence with a wrong or invented number is worse than no sentence. This project tests how far a prompt can be trusted, with numbers instead of impressions.

## Design rule

All figures are calculated in code before the model sees them. The script builds each table (Budget, Actual, Variance, Variance %, Total) from the source data with pandas. The model is asked only to report and comment, never to calculate.

## How it works

`run_eval.py` does the following:

1. Reads six monthly CSV files from the `data` folder and appends them (72 rows).
2. Builds one table per department per month: 3 departments x 6 months = 18 test tables.
3. Calculates the correct answers in code: for each table, the category with the largest overspend and the largest underspend, by amount and by percentage. If no category is under (or over) budget, the answer is "none".
4. Sends the prompt and each table to the Claude API (`claude-sonnet-5-5`) to write the commentary.
5. Checks every response:
   - **Numbers check:** every number in the response must appear in the input table.
   - **Language check:** the response must not contain Chinese characters (the prompt is written in Chinese and asks for English output).
   - **Largest-variance check:** a second model call (the "judge") reads the commentary and reports, as JSON, which categories it named for the four items. The judge does not decide what is correct. The code compares what the judge reported with the answers calculated in step 3.
6. Saves every response and its check results to `results.csv`.

`show_fails.py` prints only the sentences that failed the numbers check, for error analysis.

## Results

| Run | Prompt | Responses | Numbers check | Largest-variance check | English |
|---|---|---|---|---|---|
| 17 Nov 2026 | V7 | 54 | 53 of 54 | not yet built | 54 of 54 |
| 17 Nov 2026 | V7 | 54 | 53 of 54 | 54 of 54 | 54 of 54 |
| 18 Nov 2026 | V8 | 162 | 160 of 162 | 162 of 162 | 162 of 162 |

Each table was run several times (3 or 9) because the same prompt gives a different response each time. A full V7 run of 54 responses plus 54 judge calls cost about US$0.40.

### Error analysis of the numbers check

Counting failures by type changed the conclusion. The total alone (160 of 162) suggested the V8 change had no effect.

| Failure type | Example | V7 (108 responses) | V8 (162 responses) |
|---|---|---|---|
| Rounded or approximate figure | 1.99% written as "about 2%"; -9.87% and +11.59% as "roughly 10%" | 2 | 0 |
| Figure rewritten in a different format | -6,960 written as "-6.96k in the table's terms" (the table does not use "k") | 0 | 1 |
| Correct threshold comparison | Travel at +6.16% described as "above 6%" | 0 | 1 |

V8 added one sentence asking for figures to be quoted exactly as in the table, without rounding. Rounding errors fell from 2 in 108 to 0 in 162. At the V7 error rate, the chance of seeing no rounding errors in 162 responses by luck alone is about 5%.

The "above 6%" case is a correct statement flagged by a strict check, not a model error.

### Other findings

- An earlier 18-call run returned one response in Chinese. Manual testing at 3 runs per prompt version had never shown this. After a one-sentence prompt change (V7), no response in 270 contained Chinese.
- The same prompt behaved differently through the API than in the chat product where it was first developed: some API responses were formatted as emails. Results from one environment do not carry over to another without re-testing.
- On the hardest table (February, Operations: no category under budget), the largest-variance check passed in every run: the model said there was no under-budget category instead of naming one.

## How the judge was checked

- Given a deliberately wrong commentary, the judge reported the wrong categories as written and did not correct them, and the code flagged them.
- The response for the hardest table was read by hand and matched the judge's result.

This shows the judge works on these cases. It does not prove it is always reliable; more hand-checking is planned.

## Limitations

- The numbers check confirms that each number exists in the table. It does not confirm the number is attached to the right category.
- It cannot catch approximations written in words, such as "about half".
- It flags correct threshold comparisons ("above 6%") as failures.
- The commentary model and the judge are the same model. The judge only extracts what the commentary says, which limits the risk, but a different judge model would be a stronger test.
- Not yet automated: whether the response gives unsupported reasons for a variance, and response length and format (some responses are written as emails).
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
| V8 | Quote figures exactly as in the table, no rounding | Rounded figures such as "about 2%" |

## Files

| File | Contents |
|---|---|
| `run_eval.py` | The evaluation script |
| `show_fails.py` | Prints the sentences that failed the numbers check |
| `results.csv` | V8 run, 162 responses |
| `results_v7.csv` | V7 run with the largest-variance check, 54 responses |
| `results_numbers_language.csv` | V7 run before the largest-variance check, 54 responses |

## How to run

You need a Claude API key in the `ANTHROPIC_API_KEY` environment variable. The key is not stored in this repository.

```
pip install anthropic pandas
python run_eval.py
```

## Notes

The Python code was written with AI coding assistance. I designed the checks, ran the experiments and reviewed the results.
