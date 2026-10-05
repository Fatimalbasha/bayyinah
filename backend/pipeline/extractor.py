# backend/pipeline/extractor.py
# وكيل الاستخراج: يلتقط الأحاديث المرشحة من نص حر.
# الطبقة 1 (دائمة): heuristics — علامات التحديث والأقواس «» والصيغ النبوية.
# الطبقة 2 (اختيارية): LLM للاستخراج فقط — لا يحكم ولا يصحح، يعيد مقاطع حرفية من النص.

import json
import os
import re

MARKERS = [
    r"قال\s+رسول\s+الله", r"قال\s+النبي", r"عن\s+النبي", r"قال\s+عليه\s+الصلاة\s+والسلام",
    r"صلى\s+الله\s+عليه\s+وسلم", r"ﷺ", r"في\s+الحديث", r"ورد\s+عن", r"روى", r"روي",
    r"أخرج\s+البخاري", r"أخرج\s+مسلم", r"رواه",
]
MARKER_RE = re.compile("|".join(MARKERS))
QUOTE_RE = re.compile(r"[«\"']([^»\"']{10,300})[»\"']|[(]([^()]{10,300})[)]")


def _heuristic_extract(text: str) -> list[str]:
    found, seen = [], set()

    def add(c: str):
        c = re.sub(r"\s+", " ", c).strip(" .،:؛")
        if len(c) >= 10 and c not in seen:
            seen.add(c)
            found.append(c)

    # 1) ما بين علامات الاقتباس في كامل النص (الأقوى دلالة)
    for m in QUOTE_RE.finditer(text):
        add(m.group(1) or m.group(2) or "")

    # 2) ما بعد صيغة تحديث حتى نهاية الجملة، إن لم يكن مقتبسًا أصلًا
    for m in MARKER_RE.finditer(text):
        tail = text[m.end(): m.end() + 350]
        tail = re.split(r"[«»\n]", tail)[0]            # لا نكرر المقتبس
        sent = re.split(r"[.؟!؛]", tail)[0]
        sent = re.sub(r"^[\s:،\-–]+", "", sent)
        add(sent)

    return found


def _llm_extract(text: str) -> list[str] | None:
    """استخراج عبر Claude API إن توفر ANTHROPIC_API_KEY. يعيد None عند أي فشل (fallback صامت)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import requests
        prompt = (
            "استخرج من النص التالي كل مقطع يُنسب فيه كلام إلى النبي ﷺ (حديث أو ما يُدّعى أنه حديث). "
            "أعد JSON فقط بهذا الشكل: {\"hadiths\": [\"...\"]} "
            "بشرط أن يكون كل مقطع منسوخًا حرفيًا من النص دون أي تعديل أو تصحيح أو إضافة. "
            "لا تحكم على صحة شيء. إن لم يوجد شيء أعد {\"hadiths\": []}.\n\nالنص:\n" + text
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-5", "max_tokens": 1500,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        resp.raise_for_status()
        out = "".join(b.get("text", "") for b in resp.json().get("content", []))
        out = re.sub(r"```json|```", "", out).strip()
        items = json.loads(out).get("hadiths", [])
        # حارس أمان: نقبل فقط ما هو موجود فعلًا في النص الأصلي (منع أي تحوير من LLM)
        clean = [h.strip() for h in items if h.strip() and h.strip() in text]
        return clean or None
    except Exception:
        return None


def extract_hadiths(text: str) -> dict:
    """يعيد {"method": "llm"|"heuristic", "hadiths": [...]}"""
    llm = _llm_extract(text)
    if llm is not None:
        return {"method": "llm", "hadiths": llm}
    return {"method": "heuristic", "hadiths": _heuristic_extract(text)}