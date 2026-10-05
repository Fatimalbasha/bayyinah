# بيّنة — Bayyinah

## العربية

مساعد ذكي للمعرّفين بالإسلام يتحقق من الأحاديث المتداولة ويبيّن درجتها ومصدرها.

مشاركة في **تحدي الذكاء الاصطناعي في خدمة المحتوى الإسلامي** — مسار أدوات المعرفة والتحقق (4).

---

## الفكرة

يلصق المستخدم نصًا عربيًا، مثل منشور أو مسودة محاضرة، فيقوم النظام بـ:

1. استخراج الأحاديث الواردة في النص.
2. البحث عنها في الموسوعة الحديثية بالدرر السنية، وهي المرجعية المعتمدة للتحدي.
3. عرض بطاقة لكل حديث تتضمن:
   - النص في المصدر
   - الكتاب
   - الرقم أو الصفحة
   - حكم المحدث
   - اسم العالم
   - رابط تحقق حقيقي
   - الحالة النهائية:
     - **ثابت**
     - **لا يثبت**
     - **لا يثبت بهذا اللفظ**
     - **يحتاج مراجعة مختص**
     - **لم نعثر على دليل مطابق**

---

## مبدأ الموثوقية ومقاومة الهلوسة

- الحكم والمصدر واسم العالم **تُنقل حرفيًا** من بيانات الدرر السنية، ولا يولّد النموذج حكمًا من عنده.
- لا تُبنى الروابط يدويًا؛ رابط التحقق هو صفحة البحث الفعلية في الدرر السنية باستخدام نص الحديث.
- أي حقل غير متوفر في البيانات يُعرض فارغًا (`null`) ولا يتم اختراعه.
- عند غياب المرجع أو تعارض الأحكام، يمتنع النظام عن إصدار حكم قاطع أو يحيل الحالة إلى مختص.
- يقتصر دور نموذج اللغة الكبير (LLM) على **استخراج** الأحاديث من النص بشكل اختياري.
- يوجد حارس يتحقق من أن النص المستخرج موجود حرفيًا في نص المستخدم.
- يتوفر أيضًا مسار بديل قائم على القواعد اللغوية يعمل حتى بدون استخدام LLM.

---

## البنية — Multi-Agent Pipeline

```text
نص المستخدم
      ↓
وكيل الاستخراج
backend/pipeline/extractor.py
(قواعد لغوية + LLM اختياري)
      ↓
التطبيع العربي
backend/pipeline/normalizer.py
      ↓
وكيل الاسترجاع
backend/pipeline/dorar_client.py
(واجهة الدرر السنية + Cache)
      ↓
وكيل الحكم
backend/pipeline/reviewer.py
(classify_grade + مطابقة)
      ↓
وكيل المراجعة
backend/pipeline/reviewer.py
(ترجيح، مطابقة، حالات الامتناع)
      ↓
JSON API
backend/main.py
(FastAPI)
      ↓
واجهة المستخدم
frontend/index.html
(RTL عربي)
```

---

## التشغيل محليًا

أنشئ بيئة افتراضية وثبّت الاعتماديات:

```bash
python -m venv .venv
```

على Windows:

```powershell
.venv\Scripts\Activate.ps1
```

ثم:

```bash
pip install -r requirements.txt
```

شغّل الخادم:

```bash
uvicorn backend.main:app --reload --port 8000
```

ثم افتح:

```text
http://127.0.0.1:8000
```

واجهة توثيق الـ API متاحة على:

```text
http://127.0.0.1:8000/docs
```

لا يلزم أي مفتاح API لتشغيل النظام الأساسي.

لتفعيل الاستخراج عبر LLM بشكل اختياري، انسخ:

```text
.env.example
```

إلى:

```text
.env
```

ثم أضف:

```env
ANTHROPIC_API_KEY=
```

وضع مفتاح Anthropic الخاص بك بعد علامة `=`.

---

## التقييم

لتشغيل مجموعة الاختبار:

```bash
python evaluation/run_eval.py
```

يتم حفظ النتائج الفعلية في:

```text
evaluation/eval_results.json
```

آخر قياس أُجري على مجموعة أولية من **8 حالات** تغطي أمثلة مثل:

- حديث صحيح
- حديث ضعيف
- حديث موضوع
- حديث مشهور لا يثبت
- نص ليس حديثًا
- طلب اختلاق حديث
- نص يحتوي على أكثر من حديث

### النتائج

| المؤشر | المستهدف | المقاس |
|---|---:|---:|
| Citation Rate | 100% | **100%** |
| Precision (ثابت) | ≥95% | **100%** |
| Macro-F1 | ≥0.85 | **1.0** |
| Abstention Recall | ≥90% | **100%** |

> **ملاحظة:** مجموعة الاختبار الحالية أولية وتتكون من 8 حالات فقط، والتوسعة إلى 100 حالة ضمن خطة التطوير والاستمرار.

> تصنيف ألفاظ أحكام الحديث قائم حاليًا على قوائم كلمات قابلة للمراجعة والتحسين بالتعاون مع مختص شرعي.

---

## مصادر البيانات والتراخيص

| المصدر | الاستخدام | الملاحظات |
|---|---|---|
| [الموسوعة الحديثية — الدرر السنية](https://dorar.net/hadith) | مصدر الأحكام والمصادر والأعلام | عبر [واجهة API الرسمية](https://dorar.net/article/389) |
| [AhmedElTabarani/dorar-hadith-api](https://github.com/AhmedElTabarani/dorar-hadith-api) | الاستئناس بمنهجية تحليل حقول نتائج الدرر | ترخيص MIT — لم يُستخدم كودها مباشرة |

---

## تنبيه

الأداة مدعومة بالذكاء الاصطناعي لأغراض **التحقق الأولي** من الأحاديث المتداولة.

الأداة تنقل الأحكام من مصادرها ولا تُصدر فتوى أو حكمًا شرعيًا مستقلًا، ولا تغني عن مراجعة المختصين عند الحاجة.

---

# English

## Bayyinah

An AI-powered assistant designed to help Islamic educators and content creators verify commonly circulated hadiths and identify their grading and source.

Developed for the **AI Challenge for Serving Islamic Content**, under the **Knowledge and Verification Tools Track (4)**.

---

## Idea

The user provides Arabic text, such as a social media post or lecture draft, and the system:

1. Extracts hadiths mentioned in the text.
2. Searches for them in the Dorar Al-Sunnah Hadith Encyclopedia, the reference source adopted for the challenge.
3. Displays a verification card for each detected hadith containing:
   - Source text
   - Book
   - Number or page
   - Scholar's ruling
   - Scholar's name
   - A real verification link
   - Final verification status:
     - **Authentic / Established**
     - **Not established**
     - **Not established with this exact wording**
     - **Requires specialist review**
     - **No matching evidence found**

---

## Reliability and Hallucination Resistance

Bayyinah is designed around a source-grounded verification approach:

- Hadith rulings, sources, and scholar names are **copied directly** from Dorar Al-Sunnah data.
- The language model does not independently generate religious rulings.
- Verification links are not fabricated manually. They point to real Dorar Al-Sunnah search pages.
- Any field unavailable in the source data is returned as `null` rather than invented.
- When no reliable reference is found or when rulings conflict, the system avoids producing a definitive judgment and can refer the case for specialist review.
- The Large Language Model (LLM) is used only as an optional component for **hadith extraction**.
- A validation guard checks that extracted text appears verbatim in the original user input.
- A rule-based fallback extraction pipeline allows the system to operate without an LLM.

---

## Architecture — Multi-Agent Pipeline

```text
User Text
    ↓
Extraction Agent
backend/pipeline/extractor.py
(Rule-based extraction + optional LLM)
    ↓
Arabic Normalization
backend/pipeline/normalizer.py
    ↓
Retrieval Agent
backend/pipeline/dorar_client.py
(Dorar Al-Sunnah API + Cache)
    ↓
Grading Agent
backend/pipeline/reviewer.py
(classify_grade + matching)
    ↓
Review Agent
backend/pipeline/reviewer.py
(conflict handling, matching, abstention)
    ↓
JSON API
backend/main.py
(FastAPI)
    ↓
User Interface
frontend/index.html
(Arabic RTL)
```

---

## Local Installation

Create a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Run the FastAPI server:

```bash
uvicorn backend.main:app --reload --port 8000
```

Open the application at:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

No API key is required for the core system.

To optionally enable LLM-based extraction, copy:

```text
.env.example
```

to:

```text
.env
```

and provide:

```env
ANTHROPIC_API_KEY=
```

with your Anthropic API key.

---

## Evaluation

Run the evaluation suite using:

```bash
python evaluation/run_eval.py
```

Evaluation results are saved to:

```text
evaluation/eval_results.json
```

The current preliminary evaluation set contains **8 test cases**, covering scenarios such as:

- Authentic hadith
- Weak hadith
- Fabricated hadith
- Commonly circulated but unverified wording
- Text that is not a hadith
- A request to fabricate a hadith
- Text containing multiple hadiths

### Current Results

| Metric | Target | Measured |
|---|---:|---:|
| Citation Rate | 100% | **100%** |
| Precision (Established) | ≥95% | **100%** |
| Macro-F1 | ≥0.85 | **1.0** |
| Abstention Recall | ≥90% | **100%** |

> **Limitation:** The current evaluation set is preliminary and contains only 8 test cases. Expanding the benchmark to approximately 100 cases is part of the planned future work.

> The mapping of Arabic hadith grading terminology currently relies on reviewable keyword lists and can be further validated with domain specialists.

---

## Data Sources and Licenses

| Source | Usage | Notes |
|---|---|---|
| [Dorar Al-Sunnah Hadith Encyclopedia](https://dorar.net/hadith) | Primary source for hadith rulings, references, and scholars | Uses the [official Dorar API](https://dorar.net/article/389) |
| [AhmedElTabarani/dorar-hadith-api](https://github.com/AhmedElTabarani/dorar-hadith-api) | Used as a reference for understanding Dorar result-field parsing | MIT licensed — no source code was directly copied |

---

## Disclaimer

Bayyinah is an AI-assisted tool intended for **preliminary hadith verification**.

The system reports rulings from referenced sources and does not independently issue religious rulings or fatwas. It should not replace qualified scholarly review when specialist judgment is required.