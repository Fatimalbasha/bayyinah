# backend/pipeline/normalizer.py
# تطبيع النص العربي للمقارنة فقط (النص المعروض للمستخدم يبقى كما ورد من المصدر)
import re

TASHKEEL = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")
PUNCT = re.compile(r"[^\w\s\u0600-\u06FF]")

def normalize(text: str) -> str:
    if not text:
        return ""
    t = TASHKEEL.sub("", text)
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    t = t.replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و")
    t = t.replace("ة", "ه")
    t = PUNCT.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()