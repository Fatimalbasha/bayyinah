# scripts/test_parser.py — اختبار الـ parser وحفظ النتائج في ملف لقراءة العربية بوضوح
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.pipeline.dorar_client import search_dorar

OUT_FILE = Path(__file__).resolve().parents[1] / "data" / "test_parser_output.json"

output = []
for query in ["إنما الأعمال بالنيات", "اطلبوا العلم ولو بالصين"]:
    data = search_dorar(query, use_cache=False)
    output.append({
        "query": query,
        "source_url": data["source_url"],
        "error": data["error"],
        "results_count": len(data["results"]),
        "first_3_results": data["results"][:3],
    })
    # في الطرفية نطبع فقط أرقامًا وإنجليزية (تظهر صحيحة)
    print(f"query #{len(output)}: results={len(data['results'])}, error={data['error']}")

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to: {OUT_FILE}")
print("Open this file in VS Code to read Arabic properly.")