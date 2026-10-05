# backend/pipeline/dorar_client.py
# وكيل الاسترجاع: البحث في الموسوعة الحديثية بالدرر السنية عبر الواجهة الرسمية
# https://dorar.net/article/389
# قاعدة صارمة: هذا الملف "ينقل" البيانات كما وردت، ولا يولّد أي حكم أو رابط من عنده.

import hashlib
import json
import re
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

API_URL = "https://dorar.net/dorar_api.json?skey={query}"
SEARCH_PAGE_URL = "https://dorar.net/hadith?skey={query}"  # رابط تحقق حقيقي صيغته موثقة
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Bayyinah; hackathon project; contact: team)"}

# الحقول كما تظهر في hadith-info
FIELD_MAP = {
    "الراوي": "rawi",
    "المحدث": "scholar",
    "المصدر": "book",
    "الصفحة أو الرقم": "number_or_page",
    "خلاصة حكم المحدث": "grade",
}


def _strip_tashkeel(text: str) -> str:
    """إزالة التشكيل لتحسين البحث (لا تغيّر الحروف)."""
    return re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]", "", text)


def _cache_path(query: str) -> Path:
    h = hashlib.md5(query.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"dorar_{h}.json"


def _clean_hadith_text(div) -> str:
    """نص الحديث مع إزالة الترقيم الأول مثل '1 - '."""
    text = div.get_text(" ", strip=True)
    text = re.sub(r"^\d+\s*-\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_info(info_div) -> dict:
    """يحوّل div.hadith-info إلى dict: كل info-subtitle تسمية، وما بعدها حتى التسمية التالية قيمة."""
    out = {v: None for v in FIELD_MAP.values()}
    for label_span in info_div.select("span.info-subtitle"):
        label = label_span.get_text(strip=True).rstrip(":").strip()
        key = FIELD_MAP.get(label)
        if not key:
            continue
        parts = []
        for sib in label_span.next_siblings:
            # نتوقف عند التسمية التالية
            if getattr(sib, "get", None) and "info-subtitle" in (sib.get("class") or []):
                break
            if hasattr(sib, "get_text"):
                parts.append(sib.get_text(" ", strip=True))
            else:
                parts.append(str(sib).strip())
        value = re.sub(r"\s+", " ", " ".join(parts)).strip(" :\u00a0")
        out[key] = value or None
    return out


def parse_dorar_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for hadith_div in soup.select("div.hadith"):
        info_div = hadith_div.find_next_sibling("div", class_="hadith-info")
        record = {
            "matched_text": _clean_hadith_text(hadith_div),
            "rawi": None,
            "scholar": None,
            "book": None,
            "number_or_page": None,
            "grade": None,
        }
        if info_div:
            record.update(_parse_info(info_div))
        results.append(record)
    return results


def search_dorar(query: str, use_cache: bool = True, timeout: int = 20) -> dict:
    """يعيد dict فيه: query, source_url (رابط تحقق حقيقي), results (قائمة سجلات نظيفة).
    أي فشل شبكة يعيد results فارغة مع حقل error — لا استثناءات تكسر الخادم."""
    q = _strip_tashkeel(query).strip()
    cache_file = _cache_path(q)

    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    encoded = urllib.parse.quote(q)
    payload = {
        "query": q,
        "source_url": SEARCH_PAGE_URL.format(query=encoded),
        "results": [],
        "error": None,
    }
    try:
        resp = requests.get(API_URL.format(query=encoded), headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        html = data.get("ahadith", {}).get("result", "") or ""
        payload["results"] = parse_dorar_html(html)
    except Exception as e:  # شبكة/تحليل — نمتنع بدل أن ننهار
        payload["error"] = f"{type(e).__name__}: {e}"

    if use_cache and payload["error"] is None:
        cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload