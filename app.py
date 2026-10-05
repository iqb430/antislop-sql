import sys
import json
import urllib.request
import re
from sql_agent import run_agent_loop

def synthesize_answer(user_query: str, db_results: dict, model: str = "llama3") -> str:
    """Mengubah data tabular/baris SQL mentah menjadi bahasa manusia."""
    url = "http://localhost:11434/api/generate"
    
    system_prompt = (
        "You are IronSQL, a direct, no-nonsense data assistant. "
        "You receive a user query and the RAW data output from a SQL database. "
        "Formulate a concise, clear answer for the user based EXCLUSIVELY on the provided data. "
        "Do not invent context. Do not use filler words like 'Here is the data'. "
        "If the data is empty, state that no records were found."
    )
    
    # Memastikan format data mudah dibaca LLM
    data_str = "EMPTY"
    if db_results.get("data"):
        data_str = ""
        cols = db_results.get("columns", [])
        for row in db_results["data"]:
            row_dict = dict(zip(cols, row))
            data_str += json.dumps(row_dict) + "\n"
            
    prompt = (
        f"USER QUERY: {user_query}\n\n"
        f"DATABASE RESULTS:\n{data_str}\n\n"
        "FINAL ANSWER:"
    )
    
    data = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "temperature": 0.2
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"), 
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception:
        # Fallback raw data jika LLM offline
        return f"[WARN: LLM Offline] RAW DATA: \nColumns: {db_results.get('columns')}\nRows: {db_results.get('data')}"

def print_header():
    print("\n" + "="*60)
    print(" 🛡️  IRON-SQL: DETERMINISTIC TEXT-TO-SQL TERMINAL")
    print(" Type your question in plain English (or 'exit' to quit)")
    print("="*60 + "\n")

def main_loop():
    print_header()
    while True:
        try:
            query = input("IronSQL> ").strip()
            if query.lower() in ['exit', 'quit', 'q']:
                print("\n[+] Exiting IronSQL. Session Closed.")
                break
            if not query:
                continue
                
            # 1. Pipeline Utama: Routing, Security, DB Execution (Self-Healing)
            response = run_agent_loop(query)
            
            print("\n" + "-"*40)
            if not response["success"]:
                print(f"[!] KATASTROFE: {response['error']}")
            else:
                # 2. Synthesis (Dari Array Data jadi Jawaban Manusia)
                print("[*] MEMULAI SINTESIS JAWABAN...")
                final_answer = synthesize_answer(query, response)
                
                print("\n✅ SYSTEM RESPONSE:")
                print(final_answer)
                
                # Debugging Info (Membuktikan anti-slop engine bekerja di balik layar)
                print("\n--- [Audit Trail] ---")
                print(f"Executed SQL  : {response['sql']}")
                print(f"Heal Attempts : {response['attempts']}/3")
                print("-" * 40 + "\n")
                
        except KeyboardInterrupt:
            print("\n[+] Exiting IronSQL. Session Closed.")
            break
        except Exception as e:
            print(f"\n[!] TERMINAL ERROR: {e}\n")

if __name__ == "__main__":
    main_loop()