# backend/pipeline/pipeline.py — السلسلة الكاملة: استخراج ← استرجاع ← حكم ← مراجعة
from .dorar_client import search_dorar
from .extractor import extract_hadiths
from .reviewer import review

DISCLAIMER = ("أداة مدعومة بالذكاء الاصطناعي لأغراض التحقق الأولي، تنقل الأحكام من مصادرها، "
              "وليست جهة فتوى ولا تغني عن مراجعة المختصين.")


def verify_text(text: str) -> dict:
    extraction = extract_hadiths(text)
    results = []
    for hadith in extraction["hadiths"][:10]:  # حد أقصى 10 أحاديث للطلب الواحد
        results.append(review(hadith, search_dorar(hadith)))
    return {
        "extraction_method": extraction["method"],
        "hadith_count": len(results),
        "results": results,
        "disclaimer": DISCLAIMER,
    }