import glob
import re

import anthropic
import pandas as pd

client = anthropic.Anthropic()
MODEL = "claude-sonnet-5-5"
RUNS = 3

PROMPT = """下面是一张部门花销预算与实际支出对照表。指出支出金额差异最大的低于预算和高于预算的花销类别，以及百分比差异最大的低于预算和高于预算的花销类别。写一段分析给财务经理。注意，不要自己计算，也不要自己猜测没有根据的造成差异的原因。输出内容请不要过于模板化，采用偏向白话易懂的方式。输出内容语言请确认为英文"""


def numbers_in(text):
    result = set()
    for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        result.add(float(n.replace(",", "")))
    return result


def make_table(part):
    g = part.groupby("Category", sort=False)[["Budget", "Actual"]].sum()
    lines = ["| Category | Budget | Actual | Variance | Variance % |", "|---|---|---|---|---|"]
    for cat, row in g.iterrows():
        b = int(row["Budget"])
        a = int(row["Actual"])
        v = a - b
        lines.append(f"| {cat} | {b:,} | {a:,} | {v:+,} | {v / b * 100:+.2f}% |")
    tb = int(g["Budget"].sum())
    ta = int(g["Actual"].sum())
    tv = ta - tb
    lines.append(f"| Total | {tb:,} | {ta:,} | {tv:+,} | {tv / tb * 100:+.2f}% |")
    return "\n".join(lines)


def ask(table):
    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": PROMPT + "\n" + table}],
    )
    answer = ""
    for block in message.content:
        if block.type == "text":
            answer += block.text
    return answer


tables = []
for f in sorted(glob.glob("data/*.csv")):
    tables.append(pd.read_csv(f))
df = pd.concat(tables)

results = []
for (month, dept), part in df.groupby(["Month", "Department"]):
    table = make_table(part)
    for run in range(1, RUNS + 1):
        answer = ask(table)
        extra = numbers_in(answer) - numbers_in(table)
        status = "FAIL" if extra else "PASS"
        has_chinese = bool(re.search("[\u4e00-\u9fff]", answer))
        print(month, dept, "run", run, status, sorted(extra), "CHINESE" if has_chinese else "")
        results.append({
            "month": month,
            "department": dept,
            "run": run,
            "numbers_check": status,
            "extra_numbers": sorted(extra),
            "has_chinese": has_chinese,
            "answer": answer,
        })

pd.DataFrame(results).to_csv("results.csv", index=False, encoding="utf-8-sig")
passed = sum(1 for r in results if r["numbers_check"] == "PASS")
print("Passed", passed, "of", len(results))