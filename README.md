# 🕌 Diwan SQL — Arabic-to-English Text-to-SQL

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi)
![Offline](https://img.shields.io/badge/Offline--First-No%20API%20Key%20Needed-gold?style=flat-square)
![Arabic NLP](https://img.shields.io/badge/NLP-Arabic%20%7C%20MSA%20%2B%203%20Dialects-green?style=flat-square)
![CSV](https://img.shields.io/badge/Data-CSV%20%E2%86%94%20SQLite-orange?style=flat-square)

> **Ask in Arabic. Get English SQL + instant answers.**
> Full-dialect support (Egyptian 🇪🇬 / Gulf 🇸🇦 / Levantine 🇱🇧 / MSA), conversation memory, and an offline-first design — no API key required.

---

## ✨ What it does

```
  "اعرض أعلى 5 موظفين في المبيعات حسب المبيعات"      "كام موظف في التسويق؟"
                         │                                          │
                         ▼                                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ① Arabic NLP      ② Memory      ③ SQL Builder      ④ Safe Executor  ⑤ UI      │
│ normalize ─► entities ─► last SQL ─► SELECT only ─► SQLite(CSV) ─► table+chart│
│ dialects    follow-ups  OpenAI / rules  no DROP/DELETE   50 rows    RTL Diwan │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 🖥️ UI preview (RTL "Diwan" theme — charcoal + gold + emerald)

```
┌ TOPBAR: ◈ DIWAN AL-ISTI'LAMAT ............ [50 records] [engine] [connect] ┐
├ SIDEBAR (right)            │  MAIN                                        │
│ 📜 Doors: [Query][Update]  │  ┌ Ask in Arabic ──────────────────────┐      │
│    [Help]                  │  │ أعلى 5 موظفين في المبيعات...  [🔍] │      │
│ 🏛️ Schema: employees       │  └─────────────────────────────────────┘      │
│ ✨ 9 ready-made examples   │  ┌ SQL generated ─────┐┌ Chart ────────┐      │
│ 🕰️ History (20 turns)      │  │ SELECT ... LIMIT 5 ││ ▅▅▃▅▁ bars   │      │
│                            │  └────────────────────┘└──────────────┘      │
│                            │  ┌ Results (sortable, searchable, CSV) ─┐    │
│                            │  │ id │ name │ dept │ salary │ sales ... │    │
└────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 🧠 Deep-context understanding

| Capability | How |
|---|---|
| 🔤 Normalization | Hamza/ta-marbuta/tashkeel unification, Arabic verbal numerals (خمسة → 5) |
| 🗣️ 3 dialects + MSA | `data/synonyms.json` — عايز / أبغى / بدي / اعرض |
| 🔗 Follow-ups | رتبهم، منهم، طب، دول… inherit filters from last SQL |
| 🧩 Ambiguity guard | `أكبر من 13000` = filter (not `MAX`); `مجموع مبيعات` = metric (not dept) |
| 🛡️ Safety | `SELECT`/`WITH` only — `DROP/DELETE/UPDATE` rejected |
| 💾 Memory | Last 10 turns + sticky entities (dept/city/region) |

---

## 🚀 Quickstart

### Option A — Zero install (UI only, 100% offline)
Just open the file — a JS engine inside the page translates + queries the CSV in-browser:

```
arabic-sql-app/frontend/index.html   →   double-click, ask away
```

### Option B — Full backend (FastAPI + optional LLM)

```powershell
cd arabic-sql-app\backend
pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env   # add OPENAI_API_KEY for LLM mode (optional)
python -m uvicorn backend.app:app --port 8000
# → http://localhost:8000
```

Without a key the engine runs **rule-based** (offline). With a key, GPT builds the SQL using a schema-aware system prompt (`backend/llm_engine.py`).

---

## 💬 Try these

| # | Ask (Arabic) | Generated SQL (English) | Result |
|---|---|---|---|
| 1 | اعرض كل الموظفين في قسم المبيعات | `... WHERE department_ar = 'المبيعات'` | 17 rows |
| 2 | كام موظف في التسويق؟ | `SELECT COUNT(*) ... WHERE department_ar = 'التسويق'` | count |
| 3 | متوسط مرتبات تقنية المعلومات | `SELECT AVG(salary_egp) ...` | average |
| 4 | أعلى 5 موظفين في المبيعات حسب المبيعات | `... ORDER BY sales_amount_egp DESC LIMIT 5` | top 5 |
| 5 | ورتبهم حسب المرتب تنازليا ☝️ follow-up | builds on #4 + `ORDER BY salary_egp DESC` | re-ranked |
| 6 | مرتبهم أكبر من 13000 في القاهرة | `WHERE city_ar='القاهرة' AND salary_egp > 13000` | 12 rows |
| 7 | مجموع مبيعات الدلتا | `SELECT SUM(sales_amount_egp) WHERE region_ar='الدلتا'` | sum |

---

## 🔌 API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Status, row count, LLM availability |
| `GET` | `/api/schema` | Table schema + Arabic column aliases |
| `POST` | `/api/ask` | `{question, use_llm}` → `{sql, explanation_ar, confidence, data}` |
| `POST` | `/api/execute` | Run raw `SELECT` (validated) |
| `POST` | `/api/update` | `{updates:[{id, salary_egp:…}]}` → writes into `data/company.csv` |
| `POST` | `/api/reset-memory` | Clear conversation context |

**Update the CSV from the terminal:**

```powershell
curl -X POST http://localhost:8000/api/update `
  -H "Content-Type: application/json" `
  -d '{"updates": [{"id": 1, "salary_egp": 13000}]}'
```

Or use the **Update Data** tab in the UI — edits persist to `data/company.csv` (and `LocalStorage` in offline mode).

---

## 📦 Project layout

```
arabic-sql-app/
├── 📊 data/
│   ├── company.csv        # 50 employees — queried AND updated by the app
│   ├── schema.json        # columns + Arabic aliases + allowed values
│   └── synonyms.json      # dialects, synonyms, follow-up words (the context brain)
├── ⚙️ backend/
│   ├── app.py             # FastAPI: /ask /execute /update /schema
│   ├── nlp_pipeline.py    # normalization + entity extraction
│   ├── llm_engine.py      # huge-context prompt + offline rule builder
│   ├── sql_executor.py    # safe SELECT runner + CSV writer (no pandas needed)
│   └── memory.py          # 10-turn conversation memory
└── 🎨 frontend/           # RTL Diwan UI — works standalone, no server needed
    ├── index.html
    ├── style.css
    └── app.js             # offline Arabic→SQL engine + canvas charts
```

---

## 🛠️ Stack

`Python · FastAPI · SQLite · vanilla JS · canvas charts` — zero build step, zero paid APIs required.

---

## 🗺️ Roadmap

- [ ] Multi-table JOINs (departments, sales)
- [ ] Voice input for dialects (expanded)
- [ ] Ollama local-LLM preset
- [ ] Export to Excel / PDF reports

---

<p align="center">Built with 📜 in Cairo — <b>Arabic in, SQL out.</b></p>
