# 🕌 مستكشف SQL بالعربية — Arabic-to-English SQL with NLP + LLM

واجهة عربية كاملة (RTL) بتصميم **ديوان / مخطوطة عربية**: كحلي-فحمي + ذهبي + زمردي، بخطوط Cairo و Amiri، وزخرفة هندسية — مختلف تمامًا عن القوالب البنفسجية المعتادة.

## المميزات (فهم سياقي ضخم)
- **NLP عربي**: توحيد همزات/تاء مربوطة/تشكيل، أرقام عربية لفظية، مرادفات + لهجات (مصري/خليجي/شامي/فصحى) في `data/synonyms.json`
- **ذاكرة محادثة**: آخر 10 أدوار + كيانات ثابتة (القسم/المدينة) + أسئلة متابعة (رتبهم، منهم، طب اللي في القاهرة...)
- **LLM**: برومبت ضخم واعٍ بالسكيمة (`SYSTEM_PROMPT` في `backend/llm_engine.py`) + دمج OpenAI، و fallback قاعدي يعمل **بدون إنترنت**
- **أمان SQL**: SELECT فقط، رفض DROP/DELETE/UPDATE
- **تطبيق عملي على CSV**: `data/company.csv` (50 موظف) + endpoint تحديث `/api/update` يعدّل الملف فعليًا
- **واجهة تعمل أوفلاين**: `frontend/app.js` فيه محرك JS مدمج يولّد SQL وينفذه على CSV في المتصفح بدون سيرفر

## التشغيل السريع (بدون سيرفر — UI فقط)
افتح `frontend/index.html` مباشرة في المتصفح. كل شيء يعمل: اكتب بالعربية → SQL إنجليزي → نتائج + رسم بياني.

## التشغيل الكامل (FastAPI + LLM)
```powershell
cd arabic-sql-app\backend
pip install -r requirements.txt
copy ..\.env.example ..\.env   # ثم ضع OPENAI_API_KEY إن وجد
uvicorn backend.app:app --reload --port 8000
# افتح http://localhost:8000
```

## أمثلة جرّبها
| بالعربية | المعنى |
|---|---|
| اعرض كل الموظفين في قسم المبيعات | `WHERE department_ar = 'المبيعات'` |
| كام موظف في التسويق؟ | `COUNT` + فلتر |
| متوسط مرتبات تقنية المعلومات | `AVG(salary_egp)` |
| أعلى 5 موظفين في المبيعات حسب المبيعات | `ORDER BY sales_amount_egp DESC LIMIT 5` |
| ورتبهم حسب المرتب تنازليا | متابعة: يبني على آخر SQL |
| الموظفين اللي مرتبهم أكبر من 13000 في القاهرة | فلتر عددي + مدينة |
| مجموع مبيعات الدلتا | `SUM` + منطقة |

## تحديث CSV (program usage + updates)
```powershell
curl -X POST http://localhost:8000/api/update -H "Content-Type: application/json" -d "{\"updates\": [{\"id\": 1, \"salary_egp\": 13000}]}"
```
أو من الواجهة: تبويب **تحديث البيانات** ← عدّل مرتب/مبيعات ← حفظ في CSV.

## البنية
```
arabic-sql-app/
├── data/company.csv        # ملف البيانات (50 صف) — يُنفَّذ عليه و يُحدَّث
├── data/schema.json        # السكيمة + الأسماء العربية للأعمدة
├── data/synonyms.json      # المرادفات واللهجات (قلب الفهم السياقي)
├── backend/
│   ├── app.py              # FastAPI: /ask /execute /update /schema
│   ├── nlp_pipeline.py     # تطبيع + استخراج كيانات + لهجات
│   ├── llm_engine.py       # البرومبت الضخم + المولّد القاعدي
│   ├── sql_executor.py     # تنفيذ آمن + تحديث CSV
│   └── memory.py           # ذاكرة المحادثة
└── frontend/               # واجهة الديوان (RTL) — تعمل مستقلة
    ├── index.html
    ├── style.css
    └── app.js
```
