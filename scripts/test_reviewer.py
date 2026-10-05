# scripts/test_reviewer.py — اختبار القرار النهائي على 4 حالات مفصلية
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.pipeline.dorar_client import search_dorar
from backend.pipeline.reviewer import review

CASES = [
    "إنما الأعمال بالنيات",                       # متوقع: ثابت
    "اطلبوا العلم ولو بالصين",                    # متوقع: لا يثبت
    "النظافة من الإيمان",                          # متوقع: لا يثبت بهذا اللفظ (الثابت: الطُّهور شطر الإيمان)
    "من شرب الشاي بنية صالحة دخل الجنة",          # متوقع: لم نعثر على دليل مطابق
]

OUT = Path(__file__).resolve().parents[1] / "data" / "test_reviewer_output.json"
results = []
for text in CASES:
    verdict = review(text, search_dorar(text))
    results.append(verdict)
    print(f"case done: status set = {verdict['status'] is not None}")

OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved to: {OUT}")