# scripts/debug_case3.py — ماذا قالت الدرر عن "حب الوطن من الإيمان" وكيف صنفناها؟
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.pipeline.dorar_client import search_dorar
from backend.pipeline.reviewer import classify_grade, score_result

data = search_dorar("حب الوطن من الإيمان", use_cache=False)
rows = []
for r in data["results"]:
    s = score_result("حب الوطن من الإيمان", r)
    rows.append({"grade": r["grade"], "class": s["grade_class"],
                 "sim_tokens": round(s["sim_tokens"], 1), "scholar": r["scholar"]})

out = Path(__file__).resolve().parents[1] / "data" / "debug_case3.json"
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"results: {len(rows)} — saved to {out}")