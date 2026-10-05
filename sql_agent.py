import sqlite3
import json
import urllib.request
import urllib.error
import re
import sys
from schema_indexer import get_relevant_tables

DB_URI = "file:shop.db?mode=ro"

try:
    import sqlglot
    from sqlglot import exp
    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False

def is_safe_query(sql_query: str) -> tuple[bool, str]:
    """
    Security Guardrail: Menganalisis kueri secara AST/Token.
    Memblokir ekspresi mutasi data (INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA).
    """
    if HAS_SQLGLOT:
        try:
            parsed = sqlglot.parse_one(sql_query)
            if not isinstance(parsed, exp.Select):
                return False, "Query utama wajib berupa ekspresi SELECT"
            
            forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Command)
            for node in parsed.walk():
                if isinstance(node[0], forbidden):
                    return False, f"Terdeteksi AST Node terlarang: {type(node[0]).__name__}"
            return True, "Valid AST"
        except Exception:
            # Fallback ke token scanner jika syntax sqlglot ambigu
            pass
            
    # Token-level strict validator fallback
    tokens = re.findall(r'\b[A-Za-z]+\b', sql_query.upper())
    forbidden_tokens = {"DELETE", "DROP", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "REPLACE", "PRAGMA", "ATTACH", "DETACH"}
    
    for token in tokens:
        if token in forbidden_tokens:
            return False, f"Terdeteksi token terlarang: {token}"
            
    if "SELECT" not in tokens:
        return False, "Query harus mengandung perintah SELECT"
        
    return True, "Valid Tokens"

def call_ollama(prompt: str, model: str = "llama3") -> str:
    import os
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
    
    system_prompt = (
        "You are an expert Text-to-SQL compiler. "
        "Output ONLY the raw SQL query. "
        "NEVER include markdown formatting (no ```sql), no explanation, no filler words. "
        "Strictly adhere to the provided SQLite database schema."
    )
    
    data = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "temperature": 0.0 # Deterministic compilation
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"), 
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            raw_text = result.get("response", "").strip()
            # Bersihkan sisa markdown jika LLM membangkang
            clean_sql = re.sub(r'```(?:sql)?|```', '', raw_text).strip()
            return clean_sql
    except urllib.error.URLError:
        # Emulasi / Mocking response jika Ollama sedang offline
        print("[!] WARN: Ollama offline. Menggunakan Mock Generator untuk demonstrasi pipeline.")
        return "SELECT name, city FROM users WHERE city = 'Bandung';"

def run_agent_loop(user_query: str, max_retries: int = 3) -> dict:
    """
    The Autonomous Self-Healing Loop:
    Mengambil skema relevan -> Compile SQL -> Validasi Security -> Eksekusi DB -> Self-Heal jika gagal.
    """
    print(f"\n{'='*50}")
    print(f"[*] MEMULAI AGENT EXECUTION: '{user_query}'")
    print(f"{'='*50}")
    
    # 1. RAG Schema Routing
    relevant_schemas = get_relevant_tables(user_query, top_k=3)
    schema_context = "\n".join(relevant_schemas)
    
    history_prompt = (
        f"Database Schema:\n{schema_context}\n\n"
        f"User Request: {user_query}\n"
    )
    
    for attempt in range(1, max_retries + 1):
        print(f"\n[Attempt {attempt}/{max_retries}] Mengompilasi SQL via LLM...")
        sql = call_ollama(history_prompt)
        print(f" -> Generated SQL: {sql}")
        
        # 2. Security Guardrail Check
        is_safe, reason = is_safe_query(sql)
        if not is_safe:
            print(f" [!] SECURITY BLOCKED: {reason}")
            history_prompt += f"\nPrevious Output: {sql}\nError: Security Guardrail Blocked this query ({reason}). Write a safe SELECT query only."
            continue
            
        # 3. Read-Only Hardware Execution
        conn = None
        try:
            conn = sqlite3.connect(DB_URI, uri=True)
            cursor = conn.cursor()
            cursor.execute(sql)
            
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data = cursor.fetchall()
            
            print(f" [✔] SUCCESS: Query berhasil dieksekusi!")
            return {
                "success": True,
                "sql": sql,
                "columns": columns,
                "data": data,
                "attempts": attempt
            }
            
        except sqlite3.OperationalError as e:
            # 4. Self-Healing Mechanism
            print(f" [!] EXECUTION ERROR: {e}")
            print(f" [*] SELF-HEALING: Memberikan feedback error kembali ke LLM...")
            history_prompt += (
                f"\nPrevious Generated SQL: {sql}\n"
                f"Database Execution Error: {e}\n"
                "Fix the SQL query by correctly matching the table schema columns."
            )
            
        finally:
            if conn:
                conn.close()
            
    return {
        "success": False,
        "error": f"Gagal mengeksekusi setelah {max_retries} percobaan."
    }

if __name__ == "__main__":
    # Test Normal
    res = run_agent_loop("Tampilkan daftar semua pelanggan dari kota Bandung")
    print("\n--- HASIL DATA TABULAR ---")
    print(f"Columns : {res.get('columns')}")
    print(f"Rows    : {res.get('data')}")
