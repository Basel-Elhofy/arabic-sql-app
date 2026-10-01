# -*- coding: utf-8 -*-
"""Conversation memory: keeps huge context (entities + last SQL)."""
from collections import deque

class ConversationMemory:
    def __init__(self, max_turns: int = 10):
        self.turns = deque(maxlen=max_turns)
        self.last_sql = None
        self.last_entities = {}

    def add(self, q: str, sql: str, entities: dict):
        # merge entities (huge-context: persist dept/city unless overridden)
        for k, v in entities.items():
            if v:
                self.last_entities[k] = v
        self.turns.append({"q": q, "sql": sql})
        self.last_sql = sql

    def history(self):
        return list(self.turns)

    def clear(self):
        self.turns.clear()
        self.last_sql = None
        self.last_entities = {}
