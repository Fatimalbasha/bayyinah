# backend/pipeline/reviewer.py
# وكيل الحكم + وكيل المراجعة:
# - الحكم: يصنّف نص "خلاصة حكم المحدث" إلى فئات (نقلًا، لا توليدًا).
# - المراجعة: يجمّع الأحكام عبر النتائج عالية التطابق ويصدر الحالة النهائية أو يمتنع.
# العتبات أدناه مبدئية وستُعاير من مجموعة الاختبار (evaluation/) قبل التسليم.

from rapidfuzz import fuzz

from .normalizer import normalize

# --- تصنيف نص الحكم كما ورد (قوائم كلمات، بلا LLM) ---
FABRICATED_KW = ["موضوع", "باطل", "لا اصل له", "لا أصل له", "مكذوب", "منكر"]
WEAK_KW = ["ضعيف", "لا يصح", "لا يثبت", "واه", "خطأ", "غريب لا يصح", "مرسل", "معضل", "منقطع", "اسناده ضعيف"]
AUTHENTIC_KW = ["صحيح", "ثبت", "متفق عليه", "اسناده صحيح", "حسن", "اسناده حسن", "رجاله ثقات", "مجمع علي صحته"]

SAHIHAIN = ["صحيح البخاري", "صحيح مسلم"]

# --- عتبات المطابقة (مبدئية) ---
EXACT_T = 90      # تطابق لفظي شبه تام بعد التطبيع
PARTIAL_T = 80    # تداخل كلمات عالٍ مع اختلاف في اللفظ/الترتيب
MIN_CANDIDATE = 60  # أقل من هذا: النتيجة لا تُعد مرشحًا أصلًا


def classify_grade(grade_text: str) -> str:
    """authentic / weak / fabricated / unclear — بترتيب أولوية: الوضع ثم الضعف ثم الصحة."""
    if not grade_text:
        return "unclear"
    g = normalize(grade_text)
    if any(normalize(k) in g for k in FABRICATED_KW):
        return "fabricated"
    if any(normalize(k) in g for k in WEAK_KW):
        return "weak"
    if any(normalize(k) in g for k in AUTHENTIC_KW):
        return "authentic"
    return "unclear"


def score_result(user_text: str, result: dict) -> dict:
    """يضيف لكل نتيجة: درجتي تشابه + فئة الحكم."""
    u = normalize(user_text)
    m = normalize(result.get("matched_text") or "")
    result = dict(result)
    result["sim_full"] = fuzz.ratio(u, m)            # تطابق اللفظ كاملًا
    result["sim_tokens"] = fuzz.token_set_ratio(u, m)  # تداخل الكلمات بغضّ النظر عن الترتيب/الزيادات
    result["grade_class"] = classify_grade(result.get("grade"))
    result["in_sahihain"] = any(s in (result.get("book") or "") for s in SAHIHAIN)
    return result


def review(user_text: str, dorar_payload: dict) -> dict:
    """القرار النهائي لحديث واحد. يعيد سجلًا بصيغة الاستجابة المتفق عليها."""
    base = {
        "input_hadith": user_text,
        "matched_text": None,
        "status": None,
        "book": None,
        "hadith_number": None,
        "grade": None,
        "scholar": None,
        "source_url": dorar_payload.get("source_url"),
        "match_type": None,
        "confidence": 0.0,
        "note": None,
        "evidence": [],  # نعرض أهم الأحكام المؤيدة للقرار (شفافية أمام المستخدم واللجنة)
    }

    if dorar_payload.get("error"):
        base["status"] = "يحتاج مراجعة مختص"
        base["note"] = "تعذر الوصول إلى المصدر المعتمد حاليًا، فامتنع النظام عن إصدار نتيجة."
        return base

    scored = [score_result(user_text, r) for r in dorar_payload.get("results", [])]
    candidates = [r for r in scored if r["sim_tokens"] >= MIN_CANDIDATE]

    if not candidates:
        base["status"] = "لم نعثر على دليل مطابق"
        base["match_type"] = "no_reliable_match"
        base["note"] = "لا توجد رواية مطابقة في الموسوعة الحديثية بالدرر السنية. لا يصح نسبة هذا الكلام للنبي ﷺ دون مصدر."
        return base

    # نرتب: الصحيحان أولًا، ثم قوة التطابق اللفظي
    candidates.sort(key=lambda r: (r["in_sahihain"], r["sim_full"], r["sim_tokens"]), reverse=True)
    top = [r for r in candidates if r["sim_tokens"] >= PARTIAL_T] or candidates[:3]

    n_auth = sum(1 for r in top if r["grade_class"] == "authentic")
    n_weak = sum(1 for r in top if r["grade_class"] in ("weak", "fabricated"))
    n_fab = sum(1 for r in top if r["grade_class"] == "fabricated")

    best_auth = next((r for r in top if r["grade_class"] == "authentic"), None)
    best = best_auth or top[0]

    def fill(from_r, status, match_type, conf, note):
        base.update({
            "matched_text": from_r["matched_text"],
            "status": status,
            "book": from_r["book"],
            "hadith_number": from_r["number_or_page"],
            "grade": from_r["grade"],
            "scholar": from_r["scholar"],
            "match_type": match_type,
            "confidence": round(conf, 2),
            "note": note,
            "evidence": [
                {"grade": r["grade"], "scholar": r["scholar"], "book": r["book"],
                 "number_or_page": r["number_or_page"], "sim_full": r["sim_full"]}
                for r in top[:5]
            ],
        })

    # تعارض حقيقي بين صحة ووضع في نفس اللفظ → لا نحسمه آليًا
    if n_auth > 0 and n_fab > 0:
        fill(best, "يحتاج مراجعة مختص", "conflicting_grades", 0.5,
             "وردت أحكام متعارضة (تصحيح وتضعيف شديد) على روايات متقاربة، والفصل بينها يحتاج مختصًا.")
        return base

    if n_auth > 0:
        if best_auth["sim_full"] >= EXACT_T:
            fill(best_auth, "ثابت", "exact", min(0.99, best_auth["sim_full"] / 100),
                 "اللفظ مطابق لرواية حكم عليها العلماء بالثبوت في المصدر المذكور.")
        else:
            fill(best_auth, "لا يثبت بهذا اللفظ", "close", best_auth["sim_tokens"] / 100 * 0.8,
                 "يوجد أصل ثابت قريب، لكن اللفظ المُدخل يختلف عن اللفظ الثابت المعروض.")
        return base

    if n_weak > 0:
        fill(top[0], "لا يثبت", "exact" if top[0]["sim_full"] >= EXACT_T else "close",
             min(0.95, top[0]["sim_full"] / 100),
             "حكم العلماء المذكورون على هذه الرواية بعدم الثبوت كما هو منقول حرفيًا.")
        return base

    fill(top[0], "يحتاج مراجعة مختص", "unclear_grades", 0.4,
         "وُجدت روايات متقاربة لكن دون حكم واضح قابل للتصنيف في البيانات المسترجعة.")
    return base