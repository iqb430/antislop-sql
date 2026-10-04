import sqlite3
import os

DB_NAME = "shop.db"

def setup_mock_database():
    """Membuat database E-Commerce relasional dan menyuntikkan dummy data."""
    # Hapus DB lama kalau ada biar bersih tiap kali run
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        
    print(f"[*] Inisialisasi Database {DB_NAME} (Mode Read-Write)...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabel Users
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        registered_at DATE DEFAULT CURRENT_DATE
    )''')
    
    # 2. Tabel Products
    cursor.execute('''
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER NOT NULL
    )''')
    
    # 3. Tabel Orders
    cursor.execute('''
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_date DATE DEFAULT CURRENT_DATE,
        total_amount REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Masukkan Data Manipulasi (Dummy)
    print("[*] Menyuntikkan Dummy Data...")
    users = [("Budi Santoso", "Jakarta"), ("Siti Aminah", "Bandung"), ("Alex", "Surabaya")]
    cursor.executemany("INSERT INTO users (name, city) VALUES (?, ?)", users)
    
    products = [
        ("Laptop Pro", "Electronics", 1500.00, 10),
        ("Mechanical Keyboard", "Accessories", 120.50, 50),
        ("Kopi Robusta", "Groceries", 15.00, 200),
        ("Headphone ANC", "Electronics", 250.00, 30)
    ]
    cursor.executemany("INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)", products)
    
    orders = [(1, '2024-01-15', 1500.00), (2, '2024-02-10', 135.50), (1, '2024-03-05', 250.00)]
    cursor.executemany("INSERT INTO orders (user_id, order_date, total_amount) VALUES (?, ?, ?)", orders)
    
    conn.commit()
    conn.close()
    print("[+] Database selesai dibangun dan dikunci!")

def test_readonly_sandbox():
    """Menguji kekuatan OS-Level Security: Bisakah kita menghancurkan DB ini lewat Python?"""
    db_uri = f"file:{DB_NAME}?mode=ro"
    print(f"\n[*] Menguji Protokol READ-ONLY SANDBOX: mencoba DELETE table lewat URI ({db_uri})...")
    
    # Gunakan URI parameter dan setting uri=True
    conn = sqlite3.connect(db_uri, uri=True)
    cursor = conn.cursor()
    
    try:
        # Mengetes melakukan operasi destruktif
        cursor.execute("DROP TABLE users;")
        print("[!] BENCANA FATAL: Security Guardrail GAGAL! Database bisa dimodifikasi.")
    except sqlite3.OperationalError as e:
        print(f"[+] KEAMANAN TERUJI: Database Engine OS menolak mentah-mentah -> Error: '{e}'")
        
    conn.close()

if __name__ == "__main__":
    setup_mock_database()
    test_readonly_sandbox()
