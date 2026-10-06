# backend/main.py — خادم بيّنة
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from backend.pipeline.dorar_client import search_dorar

from backend.pipeline.pipeline import verify_text

import urllib.parse

from backend.pipeline.dorar_client import parse_dorar_html, SEARCH_PAGE_URL
from backend.pipeline.extractor import extract_hadiths
from backend.pipeline.pipeline import verify_text, DISCLAIMER
from backend.pipeline.reviewer import review

app = FastAPI(title="Bayyinah API", version="1.0.0",
              description="التحقق من الأحاديث المتداولة اعتمادًا على الموسوعة الحديثية بالدرر السنية")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # هاكاثون؛ نضيّقها عند النشر إن لزم
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


class VerifyRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=20000)


@app.get("/health")
def health():
    return {"status": "ok", "service": "bayyinah"}

@app.get("/debug/dorar")
def debug_dorar():
    from backend.pipeline.dorar_client import search_dorar
    out = search_dorar("إنما الأعمال بالنيات", use_cache=False)
    return {"error": out["error"], "results_count": len(out["results"])}


@app.post("/api/verify")
def verify(req: VerifyRequest):
    return verify_text(req.text)

class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=20000)


@app.post("/api/extract")
def extract(req: ExtractRequest):
    """المرحلة 1: استخراج الأحاديث فقط — المتصفح سيجلب نتائج الدرر بنفسه."""
    return extract_hadiths(req.text)


class JudgeItem(BaseModel):
    hadith: str
    dorar_html: str = ""   # ناتج ahadith.result الخام كما أعادته واجهة الدرر للمتصفح
    fetch_failed: bool = False


class JudgeRequest(BaseModel):
    items: list[JudgeItem]


@app.post("/api/judge")
def judge(req: JudgeRequest):
    """المرحلة 2: الحكم والمراجعة على نتائج جلبها المتصفح من واجهة الدرر الرسمية."""
    results = []
    for item in req.items[:10]:
        if item.fetch_failed or not item.dorar_html:
            # المتصفح لم يجلب شيئًا ← نستخدم الكاش المُسبق (أو نمتنع إن لم يوجد)
            payload = search_dorar(item.hadith)
        else:
            encoded = urllib.parse.quote(item.hadith)
            payload = {
                "query": item.hadith,
                "source_url": SEARCH_PAGE_URL.format(query=encoded),
                "results": parse_dorar_html(item.dorar_html),
                "error": None,
            }
        results.append(review(item.hadith, payload))
    return {"hadith_count": len(results), "results": results, "disclaimer": DISCLAIMER}


# تقديم الواجهة (سنضيف ملفاتها في الخطوة القادمة)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Bayyinah API — ضع الواجهة في مجلد frontend/"}