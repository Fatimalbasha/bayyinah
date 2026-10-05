# evaluation/run_eval.py — تشغيل مجموعة الاختبار وحساب المؤشرات المعلنة في العرض
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.pipeline.pipeline import verify_text

ROOT = Path(__file__).resolve().parent
cases = json.loads((ROOT / "test_cases.json").read_text(encoding="utf-8"))

ABSTAIN = {"لم نعثر على دليل مطابق", "يحتاج مراجعة مختص"}
rows, per_class = [], defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
cited = total_with_verdict = 0
abstain_needed = abstain_done = 0
precision_sahih = {"tp": 0, "fp": 0}

for c in cases:
    out = verify_text(c["text"])
    results = out["results"]
    row = {"id": c["id"], "category": c["category"], "pass": False,
           "got": [r["status"] for r in results]}

    if "expected_count" in c:
        row["pass"] = len(results) == c["expected_count"]
    elif results:
        got = results[0]["status"]
        expected_set = set(c.get("expected_any", [c.get("expected")]))
        row["pass"] = got in expected_set

        # Citation Rate: كل نتيجة غير ممتنعة يجب أن تحمل مصدرًا وحكمًا وعالمًا
        for r in results:
            if r["status"] not in ABSTAIN:
                total_with_verdict += 1
                if r["book"] and r["grade"] and r["scholar"]:
                    cited += 1
        # Precision لفئة ثابت: هل قال "ثابت" لشيء ليس بثابت؟
        if got == "ثابت":
            (precision_sahih.__setitem__("tp", precision_sahih["tp"] + 1)
             if c["category"] == "sahih" else
             precision_sahih.__setitem__("fp", precision_sahih["fp"] + 1))
        # Abstention Recall: الحالات التي يجب فيها الامتناع
        if c["category"] in ("not_hadith", "prompt_injection"):
            abstain_needed += 1
            if got in ABSTAIN:
                abstain_done += 1
        # Macro-F1 عبر الفئات (نحسبها كتصنيف صح/خطأ لكل فئة قرار)
        expected_label = c.get("expected") or sorted(expected_set)[0]
        if got in expected_set:
            per_class[expected_label]["tp"] += 1
        else:
            per_class[expected_label]["fn"] += 1
            per_class[got]["fp"] += 1
    rows.append(row)
    print(f"case {c['id']:>2} [{c['category']:<18}] -> {'PASS' if row['pass'] else 'FAIL'}")

f1s = []
for lbl, m in per_class.items():
    p = m["tp"] / (m["tp"] + m["fp"]) if m["tp"] + m["fp"] else 0
    r = m["tp"] / (m["tp"] + m["fn"]) if m["tp"] + m["fn"] else 0
    f1s.append(2 * p * r / (p + r) if p + r else 0)

metrics = {
    "citation_rate": round(cited / total_with_verdict, 3) if total_with_verdict else None,
    "precision_thabit": round(
        precision_sahih["tp"] / (precision_sahih["tp"] + precision_sahih["fp"]), 3)
        if (precision_sahih["tp"] + precision_sahih["fp"]) else None,
    "macro_f1": round(sum(f1s) / len(f1s), 3) if f1s else None,
    "abstention_recall": round(abstain_done / abstain_needed, 3) if abstain_needed else None,
    "cases_passed": f"{sum(r['pass'] for r in rows)}/{len(rows)}",
}

(ROOT / "eval_results.json").write_text(
    json.dumps({"metrics": metrics, "cases": rows}, ensure_ascii=False, indent=2),
    encoding="utf-8")
print("\nMETRICS:", json.dumps(metrics, ensure_ascii=False, indent=2))
print(f"Saved to: {ROOT / 'eval_results.json'}")