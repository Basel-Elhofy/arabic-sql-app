# -*- coding: utf-8 -*-
"""Arabic NLP pipeline: normalization, dialect mapping, entity extraction."""
import json, re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data"
with open(BASE / "synonyms.json", encoding="utf-8") as f:
    SYN = json.load(f)
with open(BASE / "schema.json", encoding="utf-8") as f:
    SCHEMA = json.load(f)

AR_NUMS = {"صفر":0,"واحد":1,"واحدة":1,"واحد":1,"اثنين":2,"اتنين":2,"اثنان":2,"ثلاثة":3,"تلاتة":3,
"أربعة":4,"اربعة":4,"خمسة":5,"ستة":6,"سبعة":7,"ثمانية":8,"تمانية":8,"تسعة":9,"عشرة":10,"عشره":10,
"عشرين":20,"ثلاثين":30,"خمسين":50,"مائة":100,"مئة":100}

def normalize(text: str) -> str:
    t = text.strip()
    t = re.sub(r'[أإآا]', 'ا', t)
    t = re.sub(r'ة', 'ه', t)
    t = re.sub(r'ى', 'ي', t)
    t = re.sub(r'[ؤئ]', 'ء', t)
    t = re.sub(r'[\u064B-\u0652\u0670]', '', t)  # tashkeel
    t = re.sub(r'[؟?،؛!.,\-_]+', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def normalize_keep(text: str) -> str:
    """Lighter normalize that keeps ة for value matching."""
    t = text.strip()
    t = re.sub(r'[أإآ]', 'ا', t)
    t = re.sub(r'[\u064B-\u0652\u0670]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def extract_numbers(text: str):
    nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', text)]
    for w, v in AR_NUMS.items():
        if w in text:
            nums.append(float(v))
    return nums

def extract_department(text: str):
    has_ctx = any(w in text for w in ["قسم", "إدارة", "ادارة", "موظف", "عاملين", "فريق"])
    has_agg_metric = any(w in text for w in ["مجموع", "متوسط", "إجمالي", "اجمالي"]) and "مبيعات" in text
    for alias, canon in SYN.get("departments_alias", {}).items():
        if alias in text:
            # bare "مبيعات/تسويق/مالية" without قسم/موظف context + with metric agg = metric, not dept
            if not has_ctx and has_agg_metric and canon in ("المبيعات",):
                continue
            # bare single-word dept aliases need context; full canonical names ok
            if not has_ctx and alias in ("مبيعات", "تسويق", "مالية", "التسويق", "المبيعات", "المالية"):
                # allow if question is clearly about counting/listing that group
                if not any(w in text for w in ["موظف", "عدد", "كام", "كم", "أعلى", "اعلى", "أفضل", "افضل", "متوسط", "مجموع"]):
                    continue
            return canon
    for d in SCHEMA.get("sample_values", {}).get("department_ar", []):
        if d in text:
            if not has_ctx and has_agg_metric and d == "المبيعات":
                continue
            return d
    return None

def extract_city(text: str):
    cands = SCHEMA.get("sample_values", {}).get("city_ar", [])
    for c in cands:
        if c in text:
            return c
    for alias, canon in SYN.get("cities_alias", {}).items():
        if alias in text:
            return canon
    return None

def extract_region(text: str):
    for r in SCHEMA.get("sample_values", {}).get("region_ar", []):
        if r in text:
            return r
    return None

def detect_agg(text: str):
    # "أكبر من 13000" / "أعلى من 4.5" are comparisons, NOT aggregations
    if re.search(r'(أكبر|اكبر|أعلى|اعلى|أقل|اقل|أصغر|اصغر|أكثر|اكثر)\s+من\s+\d', text):
        n2 = normalize(text)
        # still allow COUNT/SUM/AVG
        for k, v in SYN.get("aggregations", {}).items():
            if v in ("COUNT", "SUM", "AVG") and normalize(k) in n2:
                return v, k
        return None, None
    n = normalize(text)
    for k, v in SYN.get("aggregations", {}).items():
        if normalize(k) in n:
            return v, k
    return None, None

def detect_order(text: str):
    n = normalize(text)
    direction = None
    if any(normalize(k) in n for k in ["تنازلي", "من الكبير للصغير", "الاعلي", "الأعلى", "الاكبر"]):
        direction = "DESC"
    elif any(normalize(k) in n for k in ["تصاعدي", "من الصغير للكبير", "الاقل", "الأقل"]):
        direction = "ASC"
    has_order = any(normalize(k) in n for k in ["رتب", "ترتيب", "مرتب", "الاعلي", "الاقل", "الأعلى", "الأقل", "اعلي", "اقل"])
    col = None
    if "مرتب" in n or "راتب" in n or "اجر" in n or "قبض" in n:
        col = "salary_egp"
    elif "مبيعات" in n or "بيع" in n or "ايراد" in n:
        col = "sales_amount_egp"
    elif "تقييم" in n or "اداء" in n:
        col = "performance_rating"
    elif "تعيين" in n or "توظيف" in n:
        col = "hire_date"
    return (has_order, direction, col)

def detect_limit(text: str):
    # comparison "أكبر من 13000" is a filter, NOT a limit
    if re.search(r'(أكبر|اكبر|أصغر|اصغر|أعلى|اعلى|أقل|اقل|أكثر|اكثر)\s+من\s+\d', text):
        # could still be top-N if also has أول/اعرض أول N — check that explicitly
        m0 = re.search(r'(?:أول|اول)\s*(\d+)', text)
        if m0:
            return int(m0.group(1))
        return None
    m = re.search(r'(?:أول|اول|اعلي|أعلي|اكبر|أكبر|افضل|أفضل)\s*(\d+)', text)
    if m:
        return int(m.group(1))
    m2 = re.search(r'(\d+)\s*(?:موظف|موظفين|نتائج|نتيجه|صفوف|اشخاص)?', text)
    # only treat as limit if words like أول/أعلى/أفضل present
    if any(w in text for w in ["أول", "اول", "أعلى", "اعلى", "أفضل", "افضل", "أكبر", "اكبر", "top"]):
        if m2:
            return int(m2.group(1))
        for w, v in AR_NUMS.items():
            if w in text:
                return int(v)
        return 5
    if "كل" in text or "جميع" in text or "ليست" in text or "اعرض" in text:
        return None
    return None

def detect_comparison(text: str):
    """Return (column, operator, value) for salary/sales/rating filters."""
    nums = extract_numbers(text)
    val = nums[0] if nums else None
    col = None
    if any(w in text for w in ["مرتب", "راتب", "أجر", "اجر", "القبض", "الدخل"]):
        col = "salary_egp"
    elif any(w in text for w in ["مبيعات", "باع", "إيراد", "ايراد"]):
        col = "sales_amount_egp"
    elif any(w in text for w in ["تقييم", "أداء", "اداء", "تقدير"]):
        col = "performance_rating"
    op = None
    if any(w in text for w in ["أكبر من", "اكبر من", "أكثر من", "اكثر من", "أعلى من", "اعلى من", "فوق", "يزيد عن", "عدى", "يتجاوز"]):
        op = ">"
    elif any(w in text for w in ["أقل من", "اقل من", "أصغر من", "اصغر من", "تحت", "لا يتجاوز", "أدنى من"]):
        op = "<"
    elif any(w in text for w in ["يساوي", "يساوى", "=", "هو"]):
        op = "="
    if col and op and val is not None:
        return col, op, val
    return None, None, None

def analyze(question: str) -> dict:
    q = question.strip()
    dept = extract_department(q)
    city = extract_city(q)
    region = extract_region(q)
    agg, agg_w = detect_agg(q)
    has_order, direction, order_col = detect_order(q)
    limit = detect_limit(q)
    cmp_col, cmp_op, cmp_val = detect_comparison(q)
    # name search: اسمه X / اسمها
    name_m = re.search(r'اسم[هها]?\s+(\S+)', q)
    name_val = name_m.group(1) if name_m else None
    return {
        "raw": q, "norm": normalize(q),
        "department": dept, "city": city, "region": region,
        "agg": agg, "agg_word": agg_w,
        "has_order": has_order, "direction": direction, "order_col": order_col,
        "limit": limit, "cmp": {"col": cmp_col, "op": cmp_op, "val": cmp_val},
        "name_val": name_val, "numbers": extract_numbers(q),
    }
