import ast
import re

import pandas as pd


def numbers_in(text):
    result = set()
    for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        result.add(float(n.replace(",", "")))
    return result


d = pd.read_csv("results.csv")
for _, r in d[d.numbers_check == "FAIL"].iterrows():
    extra = set(ast.literal_eval(r.extra_numbers))
    print(r.month, r.department, "run", r.run, sorted(extra))
    for s in re.split(r"(?<=[.!?])\s+", r.answer):
        if numbers_in(s) & extra:
            print("   ", s)
    print()