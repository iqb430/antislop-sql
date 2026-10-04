# Architectural Blueprint: Anti-Slop Text-to-SQL Engine (IronSQL)

> **Misi:** Membangun agen Text-to-SQL lokal tanpa LangChain yang tahan terhadap *destructive commands*, menangani database skala ribuan tabel via Schema-RAG, dan memiliki kemampuan memulihkan *syntax error* secara mandiri (*Self-Healing Loop*).

---

## 1. Technical Stack & Dependencies
- **Runtime:** Python 3.10+
- **Database Engine:** SQLite (Lokal, Portabel) dengan enforcement `mode=ro` (Read-Only URI).
- **Security Parser:** `sqlglot` (Menjalankan AST Analysis pada query untuk memvalidasi hanya ada ekspresi `Select`).
- **Vector DB for Schema:** `chromadb` (Memetakan 100+ metadata tabel dan menemukan konteks relevan).
- **LLM Engine:** Local Ollama (LLaMA-3 atau Qwen-2.5 Coder) via REST API murni (`urllib.request`).

---

## 2. Core Architecture Pipeline

```
[User Natural Query] 
        │
        ▼
[Step 1: Schema Router (RAG)] 
- Vector search ke ChromaDB untuk mencocokkan query dengan Schema DDL tabel yang relevan.
- Hanya me-load 2-3 skema tabel yang dibutuhkan (Context Window Saver).
        │
        ▼
[Step 2: Generator Agent]
- Merangkai SQL query deterministik berdasarkan skema tabel yang disuntikkan.
        │
        ▼
[Step 3: Security & Guardrail Filter (AST Analysis)]
- Parse query dengan `sqlglot`.
- Tolak keras jika terdeteksi ekspresi: INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA.
        │
        ▼
[Step 4: Read-Only Database Execution]
- Eksekusi pada koneksi URI `file:data.db?mode=ro`.
        │
   ┌────┴───────────────────────────┐
   │ [SUCCESS]                      │ [ERROR / OperationalError]
   ▼                                ▼
[Step 5: Synthesizer]          [Step 4b: Self-Healing Loop]
- Format hasil tabular data     - Tangkap stacktrace & error message.
  menjadi kalimat natural.      - Kirimkan kembali ke LLM beserta riwayat error.
                                - Retry attempt maksimal 3x.
```

---

## 3. Implementation Phases (Step-by-Step)

### Phase 1: Mock Database & Read-Only Sandbox
- Buat file `db_setup.py` untuk meng-generate database SQLite tiruan:
  - Tabel: `users`, `orders`, `order_items`, `products`, `inventory_logs`.
  - Mengisi ribuan data sintetis.
- Mengunci protokol eksekusi `mode=ro` agar database secara fisik menolak penulisan data.

### Phase 2: Schema Extractor & Schema RAG
- Buat file `schema_indexer.py`:
  - Mengambil DDL (Data Definition Language) dari setiap tabel secara otomatis.
  - Memasukkan DDL + deskripsi tabel ke dalam Vector DB (`chroma_db`).
- Menguji fungsi `get_relevant_tables(user_query)` untuk membuktikan hanya tabel yang dituju yang ditarik.

### Phase 3: The Generator & Security Guardrail
- Buat file `sql_agent.py`:
  - Panggilan API ke Ollama lokal dengan *Strict Persona* untuk hanya mengeluarkan raw SQL (No markdown ticks, no filler words).
  - Integrasi modul `sqlglot` untuk menganalisis *Abstract Syntax Tree (AST)* query.

### Phase 4: The Autonomous Self-Healing Loop
- Menambahkan logika pemulihan mandiri:
  - Jika terjadi `sqlite3.OperationalError: no such column: ...`, kode menangkap error tersebut.
  - LLM dipanggil ulang dengan prompt: *"Your previous query failed with: {error}. Here is the exact schema. Fix the query."*
  - Batas retry: 3 kali.

### Phase 5: Synthesis & Terminal UI
- Mengonversi data mentah (Tuple/Dict) menjadi bahasa manusia yang ringkas.
- Menyusun CLI interaktif `app.py`.

---

## 4. R&D Research Findings & Guardrails

1. **Kenapa AST Analysis (`sqlglot`) Lebih Unggul dari Regex?**
   - Regex mudah dikelabui oleh komentar SQL (contoh: `SELECT /* DELETE */ * FROM users`).
   - AST membaca struktur pohon komputasi query SQL secara matematis, menjamin zero false-negatives pada operasi manipulasi data.
   
2. **Kenapa SQLite `mode=ro` adalah Lapisan Pertahanan Terakhir?**
   - Bahkan jika LLM berhasil mem-bypass AST parser, *OS-level database engine* akan menolak penulisan pada disk secara fisik (`sqlite3.OperationalError: attempt to write a readonly database`).

---

## 5. Definition of Done (DoD)
- [ ] 100% Zero-LangChain, pure Python.
- [ ] Mampu mengeksekusi Text-to-SQL pada minimal 5 tabel relasional.
- [ ] Teruji mampu memperbaiki diri sendiri saat diberikan skenario *intentional schema error*.
- [ ] Teruji memblokir query destruktif (SQL Injection/DROP TABLE).
