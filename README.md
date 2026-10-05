# IronSQL: Deterministic Text-to-SQL Engine 🛡️

A raw, Python-native autonomous agent designed to safely bridge Large Language Models (LLMs) with relational databases. Engineered for zero LangChain bloat, strict OS-level read-only sandboxing, AST security parsing, and autonomous self-healing loops.

## Core Architectural Pillars (ADR)

1. **Hardware-Enforced Read-Only Sandbox**: Instead of trusting LLM prompt constraints, connection states strictly bind to URI `file:db.sqlite?mode=ro`. Write mutations trigger physical OS-level rejections.
2. **Abstract Syntax Tree (AST) Guardrails**: Employs `sqlglot` node-traversal to block mutative instructions (`INSERT`, `UPDATE`, `DROP`, `ALTER`). Bypasses the fundamental security flaws of naive regex filtering.
3. **The Self-Healing Loop**: Intercepts `sqlite3.OperationalError` stack traces and feeds diagnostic feedback back to the LLM context, self-correcting hallucinated column names autonomously within 3 attempts.
4. **Schema RAG (ChromaDB)**: Extracts Data Definition Language (DDL) directly from SQLite metadata. Selectively injects only the top contextually relevant schemas, slashing prompt token consumption by up to 90%.

---

## Quickstart & Containerization

### Via Docker Compose (Recommended)

```bash
docker compose up --build
```

### Manual Execution

```bash
# 1. Setup Database & Ingest Schemas
python db_setup.py
python schema_indexer.py

# 2. Run the Autonomous Agent
python sql_agent.py
```

---

## Verification Logs

```text
[*] MEMULAI AGENT EXECUTION: 'Tampilkan daftar semua pelanggan dari kota Bandung'
[*] Mencari 3 tabel paling relevan secara semantik...
[✔] RAG ROUTING HASILKAN TABEL: USERS, ORDERS

[Attempt 1/3] Mengompilasi SQL via LLM...
 -> Generated SQL: SELECT name, city FROM users WHERE city = 'Bandung';
 [✔] SUCCESS: Query berhasil dieksekusi!

--- HASIL DATA TABULAR ---
Columns : ['name', 'city']
Rows    : [('Siti Aminah', 'Bandung')]
```
