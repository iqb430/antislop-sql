import sqlite3
import re

try:
    import chromadb
except ImportError:
    print("[!] Modul chromadb belum terpasang. Jalankan pip install chromadb")
    exit(1)

DB_NAME = "shop.db"
CHROMA_PATH = "./chroma_db"

def extract_schemas():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    
    tables = cursor.fetchall()
    conn.close()
    
    schemas = []
    for name, sql in tables:
        clean_sql = re.sub(r'\s+', ' ', sql).strip()
        schemas.append({"name": name, "ddl": clean_sql})
        
    return schemas

def index_to_vector_db():
    print("[*] Menarik DDL Schema dari SQLite...")
    schemas = extract_schemas()
    
    print(f"[*] Menemukan {len(schemas)} tabel. Melakukan Injeksi ke ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="schema_registry")
    
    docs = [s["ddl"] for s in schemas]
    ids = [s["name"] for s in schemas]
    
    collection.upsert(
        documents=docs,
        ids=ids
    )
    print("[+] Indexing Selesai (Idempotent: Aman untuk di-run berulang kali).")

def get_relevant_tables(query: str, top_k: int = 3) -> list:
    print(f"\n[*] QUERY USER: '{query}'")
    print(f"[*] Mencari {top_k} tabel paling relevan secara semantik...")
    
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(name="schema_registry")
    
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    
    docs = results['documents'][0]
    names = results['ids'][0]
    
    print("\n[✔] RAG ROUTING HASILKAN TABEL:")
    for name, doc in zip(names, docs):
        print(f" -> [{name.upper()}] DDL: {doc}")
        
    return docs

if __name__ == "__main__":
    # 1. Jalankan Indexer
    index_to_vector_db()
    
    # 2. Uji Skema Routing
    test_1 = "Tolong hitung total belanja di tanggal 15 Januari"
    test_2 = "Siapa nama pelanggan dari Bandung?"
    
    get_relevant_tables(test_1)
    get_relevant_tables(test_2)
