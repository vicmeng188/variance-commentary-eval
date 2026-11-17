import glob
import json
import re

import anthropic
import pandas as pd

client = anthropic.Anthropic()
MODEL = "claude-sonnet-5-5"
RUNS = 9

PROMPT = """下面是一张部门花销预算与实际支出对照表。指出支出金额差异最大的低于预算和高于预算的花销类别，以及百分比差异最大的低于预算和高于预算的花销类别。写一段分析给财务经理。注意，不要自己计算，也不要自己猜测没有根据的造成差异的原因。输出内容请不要过于模板化，采用偏向白话易懂的方式。输出内容语言请确认为英文。引用数字时必须与表中完全一致，不要四舍五入，也不要概括成约数"""


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

def champions(part):
    g = part.groupby("Category", sort=False)[["Budget", "Actual"]].sum()
    g["Variance"] = g["Actual"] - g["Budget"]
    g["Pct"] = g["Variance"] / g["Budget"]
    over = g[g["Variance"] > 0]
    under = g[g["Variance"] < 0]
    return {
        "over_amount": over["Variance"].idxmax() if len(over) > 0 else "none",
        "over_pct": over["Pct"].idxmax() if len(over) > 0 else "none",
        "under_amount": under["Variance"].idxmin() if len(under) > 0 else "none",
        "under_pct": under["Pct"].idxmin() if len(under) > 0 else "none",
    }


JUDGE_PROMPT = """You will read a short variance commentary written for a finance manager.
Report which cost category the commentary identifies for each of the four items below.
Use the category name exactly as written (Salaries, Travel, Software or Advertising).
If the commentary says no category fits an item, or does not identify one, use "none".
Do not judge whether the commentary is correct. Only report what it says.

- over_amount: largest overspend in dollars
- over_pct: largest overspend in percentage terms
- under_amount: largest underspend in dollars
- under_pct: largest underspend in percentage terms

Reply with JSON only, in this form:
{"over_amount": "...", "over_pct": "...", "under_amount": "...", "under_pct": "..."}

Commentary:
"""


def judge(answer):
    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": JUDGE_PROMPT + answer}],
    )
    text = ""
    for block in message.content:
        if block.type == "text":
            text += block.text
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])

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
    expected = champions(part)
    for run in range(1, RUNS + 1):
        answer = ask(table)
        extra = numbers_in(answer) - numbers_in(table)
        status = "FAIL" if extra else "PASS"
        has_chinese = bool(re.search("[\u4e00-\u9fff]", answer))
        try:
            said = judge(answer)
        except Exception:
            said = {}
        wrong = [k for k in expected if said.get(k) != expected[k]]
        champ_status = "FAIL" if wrong else "PASS"
        print(month, dept, "run", run, "numbers", status, "champions", champ_status, wrong, "CHINESE" if has_chinese else "")
        results.append({
            "month": month,
            "department": dept,
            "run": run,
            "numbers_check": status,
            "extra_numbers": sorted(extra),
            "has_chinese": has_chinese,
            "champions_check": champ_status,
            "wrong_items": wrong,
            "expected": expected,
            "judge_said": said,
            "answer": answer,
        })

pd.DataFrame(results).to_csv("results.csv", index=False, encoding="utf-8-sig")
n = len(results)
print("Numbers check passed", sum(1 for r in results if r["numbers_check"] == "PASS"), "of", n)
print("Champions check passed", sum(1 for r in results if r["champions_check"] == "PASS"), "of", n)
print("Contain Chinese", sum(1 for r in results if r["has_chinese"]), "of", n)