# -*- coding: utf-8 -*-
"""Safe SQL execution over the CSV (loaded into SQLite in-memory)."""
import sqlite3, re, csv
try:
    import pandas as pd
    _HAS_PD = True
except ImportError:
    _HAS_PD = False
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "company.csv"

def _load_rows():
    with open(DATA, encoding="utf-8") as f:
        return list(csv.DictReader(f))

if _HAS_PD:
    _df = pd.read_csv(DATA)

FORBIDDEN = re.compile(r'\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|ATTACH|DETACH)\b', re.I)

def get_dataframe():
    if _HAS_PD:
        return _df.copy()
    return _load_rows()

def _to_sql(con, rows):
    if not rows:
        return
    cols = list(rows[0].keys())
    con.execute(f"CREATE TABLE employees ({', '.join([c+' TEXT' for c in cols])})")
    # fix numeric types via CAST at query time; store raw
    con.executemany(f"INSERT INTO employees VALUES ({', '.join(['?']*len(cols))})",
                    [[r[c] for c in cols] for r in rows])

def validate_select_only(sql: str):
    s = sql.strip().rstrip(";")
    if FORBIDDEN.search(s):
        raise ValueError("مسموح فقط باستعلامات SELECT للقراءة.")
    if not re.match(r'(?is)^\s*(SELECT|WITH)\b', s):
        raise ValueError("مسموح فقط باستعلامات SELECT.")
    return s

def execute(sql: str, limit: int = 100):
    safe = validate_select_only(sql)
    con = sqlite3.connect(":memory:")
    try:
        if _HAS_PD:
            _df.to_sql("employees", con, index=False, if_exists="replace")
        else:
            _to_sql(con, _load_rows())
        cur = con.cursor()
        cur.execute(safe)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchmany(limit)
        return {"columns": cols, "rows": [list(r) for r in rows], "row_count": len(rows)}
    finally:
        con.close()

def update_csv(updates: list[dict], key: str = "id"):
    """Apply program usage updates: e.g. [{"id": 1, "salary_egp": 13000}]."""
    rows = _load_rows()
    cols = list(rows[0].keys())
    applied = 0
    for u in updates:
        if key not in u:
            continue
        for r in rows:
            if str(r[key]) == str(u[key]):
                for col, val in u.items():
                    if col == key or col not in cols:
                        continue
                    r[col] = val
                    applied += 1
    with open(DATA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
    global _df
    if _HAS_PD:
        _df = pd.read_csv(DATA)
    return {"applied_cells": applied, "rows": len(rows)}
