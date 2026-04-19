import sqlite3

conn = sqlite3.connect("inventario.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movimenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_prodotto INTEGER,
    nome TEXT,
    tipo TEXT,
    quantita INTEGER,
    data TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS vendite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    totale REAL,
    data TEXT
)
""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS prodotti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    quantita INTEGER,
    prezzo REAL,
    barcode TEXT
)
""")
conn.commit()

# Self-heal: older DBs may lack the barcode column.
_cols = [r[1] for r in cursor.execute("PRAGMA table_info(prodotti)")]
if "barcode" not in _cols:
    cursor.execute("ALTER TABLE prodotti ADD COLUMN barcode TEXT")
    conn.commit()
