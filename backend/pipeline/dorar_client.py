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
from rapidfuzz import fuzz

from .normalizer import normalize

API_URL = "https://dorar.net/dorar_api.json?skey={query}"
SEARCH_PAGE_URL = "https://dorar.net/hadith/search?q={query}"  # يفتح نتائج البحث مباشرة
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ar,en;q=0.9",
    "Referer": "https://dorar.net/hadith",
}

# الحقول كما تظهر في hadith-info
FIELD_MAP = {
    "الراوي": "rawi",
    "المحدث": "scholar",
    "المصدر": "book",
    "الصفحة أو الرقم": "number_or_page",
    "خلاصة حكم المحدث": "grade",
}

# البحث المحلي في اللقطة المخزّنة (يُستخدم فقط عند تعذّر الوصول للدرر)
LOCAL_MIN_SCORE = 85
LOCAL_TOP_K = 15
_LOCAL_INDEX = None


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


def _load_local_index() -> list:
    """يجمع كل السجلات المخزّنة في data/cache مرة واحدة، بلا تكرار.
    السجلات منقولة من ردود الدرر كما هي، ولا يُعدَّل فيها شيء."""
    global _LOCAL_INDEX
    if _LOCAL_INDEX is None:
        seen, index = set(), []
        for f in CACHE_DIR.glob("dorar_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for rec in data.get("results", []):
                text = rec.get("matched_text") or ""
                key = (text, rec.get("scholar"), rec.get("book"), rec.get("number_or_page"))
                if not text or key in seen:
                    continue
                seen.add(key)
                index.append((normalize(text), rec))
        _LOCAL_INDEX = index
    return _LOCAL_INDEX


def _local_search(query: str) -> list[dict]:
    """مطابقة تقريبية بين النص المُدخل وكل الروايات المخزّنة. تعيد الأقرب فقط."""
    nq = normalize(query)
    if not nq:
        return []
    scored = []
    for ntext, rec in _load_local_index():
        score = max(fuzz.token_set_ratio(nq, ntext), fuzz.partial_ratio(nq, ntext))
        if score >= LOCAL_MIN_SCORE:
            scored.append((score, fuzz.ratio(nq, ntext), rec))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [rec for _, _, rec in scored[:LOCAL_TOP_K]]


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

    last_err = None
    for attempt in range(2):  # محاولتان قبل الامتناع
        try:
            resp = requests.get(API_URL.format(query=encoded), headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            html = data.get("ahadith", {}).get("result", "") or ""
            payload["results"] = parse_dorar_html(html)
            last_err = None
            break
        except Exception as e:  # شبكة/تحليل — نعيد المحاولة ثم نمتنع بدل أن ننهار
            last_err = f"{type(e).__name__}: {e}"

    if last_err:
        # تعذّر الوصول للدرر: نبحث في اللقطة المحلية قبل الامتناع
        local = _local_search(q)
        if local:
            payload["results"] = local
            payload["retrieval"] = "local_snapshot"
            return payload  # لا نحفظها في الكاش لأنها ليست ردًّا مباشرًا من الدرر
        payload["error"] = last_err

    if use_cache and payload["error"] is None:
        cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload