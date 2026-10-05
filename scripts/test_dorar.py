# scripts/test_dorar.py — فحص أولي لواجهة الدرر السنية الرسمية
import json
import urllib.parse
import urllib.request

QUERY = "إنما الأعمال بالنيات"

url = "https://dorar.net/dorar_api.json?skey=" + urllib.parse.quote(QUERY)
print("URL:", url)

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Bayyinah-Hackathon-Test)"})
with urllib.request.urlopen(req, timeout=20) as resp:
    raw = resp.read().decode("utf-8")

data = json.loads(raw)
ahadith = data.get("ahadith", {})
print("نوع ahadith:", type(ahadith).__name__)

# قد تكون dict فيها مفتاح result أو list — نطبع أول نتيجة كما هي لنرى البنية
if isinstance(ahadith, dict):
    print("المفاتيح:", list(ahadith.keys()))
    result = ahadith.get("result")
    print("\n--- أول 1500 حرف من النتيجة الخام ---\n")
    print(str(result)[:1500])
elif isinstance(ahadith, list) and ahadith:
    print("\n--- أول عنصر ---\n")
    print(json.dumps(ahadith[0], ensure_ascii=False)[:1500])
else:
    print("لا توجد نتائج — أرسلي لي الناتج كاملًا:", raw[:500])