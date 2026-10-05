# scripts/test_pipeline.py — اختبار السلسلة كاملة بنص يحاكي مسودة داعية فيها 3 أحاديث
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.pipeline.pipeline import verify_text

TEXT = """أيها الإخوة، النية أساس كل عمل، وقد صح عن النبي ﷺ أنه قال: «إنما الأعمال بالنيات».
والعلم فريضة، وقد اشتهر على الألسنة: «اطلبوا العلم ولو بالصين».
ويستشهد بعض الناس بقولهم: «النظافة من الإيمان» وينسبونه للنبي عليه الصلاة والسلام."""

out = verify_text(TEXT)
OUT = Path(__file__).resolve().parents[1] / "data" / "test_pipeline_output.json"
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"extraction_method = {out['extraction_method']}")
print(f"hadith_count = {out['hadith_count']} (expected: 3)")
for r in out["results"]:
    print(f"- status set: {r['status'] is not None}")
print(f"Saved to: {OUT}")