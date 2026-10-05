# backend/pipeline/reviewer.py
# وكيل الحكم: يصنّف نص حكم المحدث (نقلًا لا توليدًا) مع معالجة النفي أولًا.
# وكيل المراجعة: تصويت أغلبية على النتائج عالية التطابق، وامتناع صريح عند الضعف.
# العتبات مبدئية وتُعاير من evaluation/ قبل التسليم.

from rapidfuzz import fuzz

from .normalizer import normalize

# ترتيب الفحص إلزامي: النفي والوضع قبل أي كلمة إيجابية
NEGATION_KW = [  # صيغ تنفي الصحة/الثبوت صراحةً → تُصنف ضعفًا
    "ليس بصحيح", "لا يصح", "لم يصح", "غير صحيح", "ليس بثابت",
    "لا يثبت", "لم يثبت", "ليس بشيء", "لا يرفعه", "رفعه ليس بصحيح",
]
FABRICATED_KW = ["موضوع", "باطل", "لا اصل له", "ليس له اصل", "مكذوب", "منكر"]
WEAK_KW = ["ضعيف", "واه", "خطأ", "مرسل", "معضل", "منقطع", "اسناده ضعيف", "فيه مقال", "لا يعرف"]
AUTHENTIC_KW = ["صحيح", "ثبت", "متفق عليه", "اسناده صحيح", "حسن", "اسناده حسن",
                "رجاله ثقات", "مجمع علي صحته", "مشهور بالصحه"]

SAHIHAIN = ["صحيح البخاري", "صحيح مسلم"]

EXACT_T = 90      # تطابق لفظي شبه تام بعد التطبيع
PARTIAL_T = 80    # أدنى تداخل كلمات يُعتبر "نفس الحديث"
TOP_CAP = 10      # نصوّت على أفضل 10 نتائج قوية كحد أقصى


def classify_grade(grade_text: str) -> str:
    """authentic / weak / fabricated / unclear — النفي والوضع أولًا."""
    if not grade_text:
        return "unclear"
    g = normalize(grade_text)
    if any(normalize(k) in g for k in NEGATION_KW):
        return "weak"
    if any(normalize(k) in g for k in FABRICATED_KW):
        return "fabricated"
    if any(normalize(k) in g for k in WEAK_KW):
        return "weak"
    if any(normalize(k) in g for k in AUTHENTIC_KW):
        return "authentic"
    return "unclear"


def score_result(user_text: str, result: dict) -> dict:
    u = normalize(user_text)
    m = normalize(result.get("matched_text") or "")
    result = dict(result)
    result["sim_full"] = fuzz.ratio(u, m)
    result["sim_tokens"] = fuzz.token_set_ratio(u, m)
    result["grade_class"] = classify_grade(result.get("grade"))
    result["in_sahihain"] = any(s in (result.get("book") or "") for s in SAHIHAIN)
    return result


def review(user_text: str, dorar_payload: dict) -> dict:
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
        "evidence": [],
    }

    if dorar_payload.get("error"):
        base["status"] = "يحتاج مراجعة مختص"
        base["note"] = "تعذر الوصول إلى المصدر المعتمد حاليًا، فامتنع النظام عن إصدار نتيجة."
        return base

    scored = [score_result(user_text, r) for r in dorar_payload.get("results", [])]
    # لا fallback: فقط المطابقات القوية تدخل التصويت
    strong = [r for r in scored if r["sim_tokens"] >= PARTIAL_T]

    if not strong:
        base["status"] = "لم نعثر على دليل مطابق"
        base["match_type"] = "no_reliable_match"
        base["note"] = ("لا توجد رواية مطابقة في الموسوعة الحديثية بالدرر السنية. "
                        "لا يصح نسبة كلام للنبي ﷺ دون مصدر وحكم معتمد.")
        return base

    strong.sort(key=lambda r: (r["in_sahihain"], r["grade_class"] == "authentic",
                               r["sim_full"], r["sim_tokens"]), reverse=True)
    top = strong[:TOP_CAP]

    n_auth = sum(1 for r in top if r["grade_class"] == "authentic")
    n_fab = sum(1 for r in top if r["grade_class"] == "fabricated")
    n_weak = sum(1 for r in top if r["grade_class"] == "weak")
    n_neg = n_fab + n_weak

    best_auth = next((r for r in top if r["grade_class"] == "authentic"), None)
    sahihain_auth = next((r for r in top if r["in_sahihain"] and r["grade_class"] == "authentic"), None)

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
                 "number_or_page": r["number_or_page"], "sim_full": round(r["sim_full"], 1)}
                for r in top[:5]
            ],
        })

    # القرار بالأغلبية:
    authentic_wins = sahihain_auth is not None or (n_auth > 0 and n_auth > n_neg)
    negative_wins = n_auth == 0 and n_neg > 0

    if authentic_wins:
        chosen = sahihain_auth or best_auth
        if chosen["sim_full"] >= EXACT_T:
            note = "اللفظ مطابق لرواية حكم عليها العلماء بالثبوت في المصدر المذكور."
            if n_neg:
                note += " (توجد في الشواهد انتقادات لبعض الطرق/الأسانيد دون أصل الحديث.)"
            fill(chosen, "ثابت", "exact", min(0.99, chosen["sim_full"] / 100), note)
        else:
            fill(chosen, "لا يثبت بهذا اللفظ", "close", chosen["sim_tokens"] / 100 * 0.8,
                 "يوجد أصل ثابت قريب، لكن اللفظ المُدخل يختلف عن اللفظ الثابت المعروض.")
        return base

    if negative_wins:
        chosen = top[0]
        fill(chosen, "لا يثبت",
             "exact" if chosen["sim_full"] >= EXACT_T else "close",
             min(0.95, chosen["sim_full"] / 100),
             "حكم العلماء المذكورون على هذه الرواية بعدم الثبوت كما هو منقول حرفيًا.")
        return base

    if n_auth > 0 and n_neg >= n_auth:
        fill(top[0], "يحتاج مراجعة مختص", "conflicting_grades", 0.5,
             "وردت أحكام متقاربة العدد بين تصحيح وتضعيف، والفصل بينها يحتاج مختصًا.")
        return base

    fill(top[0], "يحتاج مراجعة مختص", "unclear_grades", 0.4,
         "وُجدت روايات مطابقة لكن دون حكم واضح قابل للتصنيف في البيانات المسترجعة.")
    return base