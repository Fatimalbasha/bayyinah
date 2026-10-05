# backend/main.py — خادم بيّنة
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.pipeline.pipeline import verify_text

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


@app.post("/api/verify")
def verify(req: VerifyRequest):
    return verify_text(req.text)


# تقديم الواجهة (سنضيف ملفاتها في الخطوة القادمة)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Bayyinah API — ضع الواجهة في مجلد frontend/"}