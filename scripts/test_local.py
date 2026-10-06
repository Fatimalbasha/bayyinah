# scripts/test_local.py — اختبار البحث التقريبي في اللقطة المحلية بألفاظ غير مطابقة حرفيًا
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.pipeline.dorar_client import _load_local_index, _local_search

TESTS = [
    "الأعمال بالنيات وإنما لكل امرئ ما نوى",
    "تبسمك في وجه أخيك لك صدقة",
    "اطلب العلم ولو في الصين",
    "من شرب القهوة دخل الجنة",
]

print("index size:", len(_load_local_index()))
out = {}
for i, t in enumerate(TESTS, 1):
    res = _local_search(t)
    print(f"test {i}: hits={len(res)}")
    out[t] = [f"{r['matched_text'][:90]} | {r['scholar']} | {r['grade']}" for r in res[:3]]

Path("data/test_local_output.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)