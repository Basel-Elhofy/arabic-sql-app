# -*- coding: utf-8 -*-
"""Rule-based Arabic->SQL builder (offline) + LLM prompt builder (huge context)."""
import json
from pathlib import Path
from . import nlp_pipeline as nlp

BASE = Path(__file__).resolve().parent.parent / "data"
SCHEMA = json.load(open(BASE / "schema.json", encoding="utf-8"))

TABLE = SCHEMA["table"]

SYSTEM_PROMPT = """أنت مترجم خبير من العربية إلى SQL.
جدول قاعدة البيانات الوحيد هو employees (موظفين) بهذه الأعمدة:
- id (رقم الموظف), first_name_ar, last_name_ar (الأسماء بالعربي),
- department_ar (القسم: المبيعات/التسويق/تقنية المعلومات/الموارد البشرية/المالية),
- city_ar (المدينة), region_ar (المنطقة),
- salary_egp (المرتب بالجنيه), hire_date (تاريخ التعيين YYYY-MM-DD),
- performance_rating (التقييم 0-5), sales_amount_egp (المبيعات بالجنيه).

قواعد صارمة:
1) أخرج SELECT فقط على جدول employees. ممنوع DROP/DELETE/UPDATE/INSERT.
2) استخدم أسماء الأعمدة الإنجليزية كما هي.
3) القيم العربية تبقى بالعربي داخل '...' (مثال: WHERE department_ar = 'المبيعات').
4) لهجات مدعومة: مصري (عايز/كام/بكام/وريني)، خليجي (وش/كم/أبغى)، شامي (بدي/فرجيني)، فصحى.
5) أسئلة المتابعة (رتبهم/منهم/طب اللي في القاهرة) تعني: ابنِ على آخر SQL واحتفظ بالفلاتر السابقة ثم أضف الجديد.
6) عند الغموض اطلب توضيحًا بدل التخمين.
7) أرجع JSON فقط: {"sql": "...", "explanation_ar": "...", "confidence": 0.0-1.0, "needs_clarification": false}
"""

def build_prompt(question: str, history: list, last_sql: str | None) -> str:
    h = "\n".join([f"- س: {x['q']}\n  SQL: {x['sql']}" for x in history[-6:]]) or "(لا يوجد سياق سابق)"
    return f"""{SYSTEM_PROMPT}

السياق السابق (آخر المحادثات):
{h}

آخر SQL ناجح:
{last_sql or '(لا يوجد)'}

السؤال الجديد بالعربية: {question}
تذكر: ابنِ على السياق عند وجود كلمات متابعة مثل (رتبهم، منهم، طب، دول، اللي فاتوا).
أرجع JSON فقط."""

def rule_based_sql(question: str, info: dict, last_sql: str | None = None) -> dict:
    """Deterministic builder covering the common Arabic patterns. Huge-context aware."""
    q = question
    # --- follow-up: inherit WHERE from last_sql ---
    base_where = ""
    if last_sql and any(w in q for w in ["رتبهم", "ورتبهم", "منهم", "دول", "اللي فات", "طب", "طيب", "كمان"]):
        import re
        m = re.search(r'WHERE\s+(.+?)(?:\s+ORDER BY|\s+LIMIT|;?\s*$)', last_sql, re.I | re.S)
        if m:
            base_where = m.group(1).strip()

    wheres = [base_where] if base_where else []
    if info["department"]:
        wheres.append(f"department_ar = '{info['department']}'")
    if info["city"]:
        wheres.append(f"city_ar = '{info['city']}'")
    if info["region"]:
        wheres.append(f"region_ar = '{info['region']}'")
    if info["name_val"] and len(info["name_val"]) > 1:
        nv = info["name_val"].strip(" ,.")
        wheres.append(f"(first_name_ar LIKE '%{nv}%' OR last_name_ar LIKE '%{nv}%')")
    c = info["cmp"]
    if c["col"] and c["op"] and c["val"] is not None:
        v = int(c["val"]) if float(c["val"]).is_integer() else c["val"]
        wheres.append(f"{c['col']} {c['op']} {v}")
    where_sql = ("WHERE " + " AND ".join(w for w in wheres if w)) if wheres else ""

    agg = info["agg"]; nums = info["numbers"]
    order_col = info["order_col"]; direction = info["direction"] or "DESC"
    limit = info["limit"]

    # default target column for agg/order
    target = order_col
    if not target:
        if any(w in q for w in ["مبيعات", "باع", "إيراد", "ايراد"]):
            target = "sales_amount_egp"
        elif any(w in q for w in ["مرتب", "راتب", "أجر", "اجر", "دخل"]):
            target = "salary_egp"
        elif any(w in q for w in ["تقييم", "أداء", "اداء"]):
            target = "performance_rating"
        else:
            target = "salary_egp" if agg in ("AVG","MAX","MIN","SUM") else "id"

    # TOP-N listing beats MAX/MIN agg: "أعلى 5 موظفين" = ORDER+LIMIT, not MAX()
    if limit and agg in ("MAX", "MIN") and any(w in q for w in ["موظف", "عامل", "اعرض", "عايز", "أبغى", "ابغى", "بدي", "وريني", "فرجيني", "أسماء", "اسماء"]):
        agg = None

    conf = 0.85
    expl = ""
    sql = ""
    sel_cols = "id, first_name_ar, last_name_ar, department_ar, city_ar, salary_egp, sales_amount_egp, performance_rating"

    if agg == "COUNT":
        sql = f"SELECT COUNT(*) AS عدد_الموظفين FROM {TABLE} {where_sql};"
        expl = "حساب عدد الموظفين المطابقين للشروط."
    elif agg in ("SUM", "AVG", "MAX", "MIN"):
        fn = {"SUM":"مجموع","AVG":"متوسط","MAX":"أعلى قيمة","MIN":"أقل قيمة"}[agg]
        sql = f"SELECT {agg}({target}) AS النتيجة FROM {TABLE} {where_sql};"
        expl = f"{fn} لعمود {target} مع الفلاتر المذكورة."
    elif info["has_order"] or ("الأعلى" in q or "الاعلى" in q or "الأقل" in q or "الاقل" in q or "أفضل" in q or "افضل" in q or limit):
        if not order_col:
            order_col = target if target != "id" else "salary_egp"
        lim = f" LIMIT {limit}" if limit else (" LIMIT 5" if any(w in q for w in ["الأعلى","الاعلى","الأقل","الاقل","أفضل","افضل"] ) else "")
        sql = f"SELECT {sel_cols} FROM {TABLE} {where_sql} ORDER BY {order_col} {direction}{lim};"
        expl = f"عرض الموظفين مرتبين حسب {order_col} {direction}."
    else:
        lim = f" LIMIT {limit}" if limit else ""
        ob = f" ORDER BY {order_col} {direction}" if (info["has_order"] and order_col) else ""
        sql = f"SELECT {sel_cols} FROM {TABLE} {where_sql}{(' ' + ob) if ob else ''}{lim};"
        sql = sql.replace("  ", " ").strip()
        expl = "عرض بيانات الموظفين المطابقين للشروط."
        if not wheres:
            conf = 0.55

    sql = " ".join(sql.split())
    return {"sql": sql, "explanation_ar": expl, "confidence": conf,
            "needs_clarification": conf < 0.6, "engine": "rule-based",
            "analysis": {k: v for k, v in info.items() if k != "raw"}}
