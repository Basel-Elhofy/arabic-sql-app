# -*- coding: utf-8 -*-
"""FastAPI backend: Arabic NL -> SQL -> execute over CSV."""
import os, json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from . import nlp_pipeline as nlp
from . import llm_engine as eng
from . import sql_executor as ex
from .memory import ConversationMemory

load_dotenv()
app = FastAPI(title="Arabic-to-SQL (NLP+LLM)", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
MEM = ConversationMemory()

class AskIn(BaseModel):
    question: str
    use_llm: bool = True

class UpdateIn(BaseModel):
    updates: list[dict]
    key: str = "id"

def try_llm(question: str) -> dict | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": eng.SYSTEM_PROMPT},
                {"role": "user", "content": eng.build_prompt(question, MEM.history(), MEM.last_sql)},
            ],
            temperature=0.1, max_tokens=500,
        )
        txt = resp.choices[0].message.content.strip()
        # extract JSON block
        import re
        m = re.search(r'\{.*\}', txt, re.S)
        data = json.loads(m.group(0) if m else txt)
        data["engine"] = "openai:" + os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return data
    except Exception as e:
        return {"_llm_error": str(e)}

@app.get("/api/health")
def health():
    return {"ok": True, "rows": len(ex.get_dataframe()), "llm": bool(os.getenv("OPENAI_API_KEY", "").strip())}

@app.get("/api/schema")
def schema():
    return json.load(open(Path(__file__).resolve().parent.parent / "data" / "schema.json", encoding="utf-8"))

@app.post("/api/ask")
def ask(body: AskIn):
    q = body.question.strip()
    if not q:
        raise HTTPException(400, "السؤال فارغ.")
    info = nlp.analyze(q)
    # merge persistent entities for follow-ups (huge context)
    if not info["department"] and MEM.last_entities.get("department"):
        if any(w in q for w in ["رتبهم", "منهم", "دول", "طب", "طيب", "كمان", "اللي"]):
            info["department"] = MEM.last_entities["department"]
    if not info["city"] and MEM.last_entities.get("city"):
        if any(w in q for w in ["رتبهم", "منهم", "دول", "طب", "طيب", "كمان", "اللي"]):
            info["city"] = MEM.last_entities["city"]

    out = None
    if body.use_llm:
        llm = try_llm(q)
        if llm and "sql" in llm:
            out = llm
        elif llm and "_llm_error" in llm:
            out = eng.rule_based_sql(q, info, MEM.last_sql)
            out["llm_error"] = llm["_llm_error"]
        else:
            out = eng.rule_based_sql(q, info, MEM.last_sql)
    else:
        out = eng.rule_based_sql(q, info, MEM.last_sql)

    try:
        result = ex.execute(out["sql"])
    except Exception as e:
        raise HTTPException(400, f"SQL مرفوض/فشل: {e}")

    MEM.add(q, out["sql"], {"department": info["department"], "city": info["city"], "region": info["region"]})
    return {"question": q, "analysis": info, "sql": out.get("sql"),
            "explanation_ar": out.get("explanation_ar", ""), "confidence": out.get("confidence", 0.8),
            "engine": out.get("engine", "rule-based"), "needs_clarification": out.get("needs_clarification", False),
            "data": result}

@app.post("/api/execute")
def execute_raw(body: dict):
    try:
        return ex.execute(body.get("sql", ""))
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/update")
def update_csv(body: UpdateIn):
    """Apply updates to the CSV file (program usage + updates)."""
    try:
        return ex.update_csv(body.updates, body.key)
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/api/reset-memory")
def reset():
    MEM.clear()
    return {"ok": True}

# serve frontend
FRONT = Path(__file__).resolve().parent.parent / "frontend"
if FRONT.exists():
    app.mount("/", StaticFiles(directory=str(FRONT), html=True), name="ui")
