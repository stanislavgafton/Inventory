"""Local shop service. Quantities are pieces or grams; money uses integer bani."""

import datetime as dt
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
from pathlib import Path
import sqlite3


class ShopError(ValueError):
    pass


def number(value, *, integer=False, minimum=0):
    try:
        n = Decimal(str(value).replace(",", "."))
        if not n.is_finite() or n < minimum or n > 1_000_000_000:
            raise ValueError()
        if integer and n != n.to_integral_value():
            raise ValueError()
        return int(n) if integer else n
    except (InvalidOperation, ValueError, TypeError):
        raise ShopError("Introduceți o valoare validă, pozitivă. Bucățile și gramele trebuie să fie întregi.") from None


def bani(value):
    return int((number(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def amount(price, quantity, unit):
    return int((Decimal(price) * quantity / (1000 if unit == "g" else 1)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def now():
    return dt.datetime.now().isoformat(sep=" ", timespec="seconds")


class Shop:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.backup("before-web-upgrade", once=True)
        with self.connect() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS prodotti (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT,
                    quantita INTEGER, prezzo REAL, barcode TEXT,
                    unit TEXT NOT NULL DEFAULT 'buc');
                CREATE TABLE IF NOT EXISTS vendite (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, totale REAL, data TEXT);
                CREATE TABLE IF NOT EXISTS movimenti (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, id_prodotto INTEGER,
                    nome TEXT, tipo TEXT, quantita INTEGER, data TEXT);
            """)
            for table, name, definition in [
                ("prodotti", "barcode", "TEXT"), ("prodotti", "unit", "TEXT NOT NULL DEFAULT 'buc'"),
                ("prodotti", "cost_bani", "INTEGER"), ("prodotti", "low_stock", "INTEGER NOT NULL DEFAULT 5"),
                ("prodotti", "category", "TEXT NOT NULL DEFAULT ''"),
                ("prodotti", "version", "INTEGER NOT NULL DEFAULT 0"),
                ("movimenti", "unit", "TEXT NOT NULL DEFAULT 'buc'"),
                ("vendite", "web_receipt", "INTEGER NOT NULL DEFAULT 0"),
            ]:
                if name not in {r[1] for r in c.execute(f"PRAGMA table_info({table})")}:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
            c.executescript("""
                CREATE TABLE IF NOT EXISTS sale_lines (
                    id INTEGER PRIMARY KEY, sale_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL, name TEXT NOT NULL, unit TEXT NOT NULL,
                    quantity INTEGER NOT NULL, price_bani INTEGER NOT NULL,
                    cost_bani INTEGER, total_bani INTEGER NOT NULL, cost_total_bani INTEGER);
                CREATE TABLE IF NOT EXISTS sale_requests (token TEXT PRIMARY KEY, sale_id INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS counts (
                    id INTEGER PRIMARY KEY, created TEXT NOT NULL, closed TEXT);
                CREATE TABLE IF NOT EXISTS count_lines (
                    count_id INTEGER, product_id INTEGER, name TEXT, unit TEXT,
                    expected INTEGER, counted INTEGER, version INTEGER,
                    PRIMARY KEY(count_id, product_id));
                CREATE TABLE IF NOT EXISTS web_settings (key TEXT PRIMARY KEY, value TEXT);
            """)
        self.daily_backup()

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        try:
            with c:
                yield c
        finally:
            c.close()

    def backup(self, label=None, once=False):
        folder = self.path.parent / "backups"
        folder.mkdir(exist_ok=True)
        name = label or dt.datetime.now().strftime("manual-%Y%m%d-%H%M%S-%f")
        target = folder / f"{name}.db"
        if once and target.exists():
            return target
        source, dest = sqlite3.connect(self.path), sqlite3.connect(target)
        try:
            with dest:
                source.backup(dest)
        finally:
            source.close()
            dest.close()
        return target

    def daily_backup(self):
        return self.backup(f"daily-{dt.date.today().isoformat()}", once=True)

    def products(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM prodotti ORDER BY nome COLLATE NOCASE")]

    def product(self, data):
        name = str(data.get("name", "")).strip()
        barcode = str(data.get("barcode", "")).strip() or None
        unit = data.get("unit", "buc")
        if not name or len(name) > 150 or unit not in ("buc", "g"):
            raise ShopError("Completați denumirea și unitatea produsului.")
        price = bani(data.get("price"))
        cost = None if data.get("cost") in (None, "") else bani(data["cost"])
        low = number(data.get("low_stock", 5), integer=True)
        category = str(data.get("category", "")).strip()[:80]
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT id FROM counts WHERE closed IS NULL").fetchone():
                raise ShopError("Finalizați inventarierea înainte de a modifica produsele.")
            pid = data.get("id")
            if barcode and c.execute("SELECT id FROM prodotti WHERE barcode=? AND id != ?", (barcode, pid or -1)).fetchone():
                raise ShopError("Acest cod de bare aparține deja altui produs.")
            if pid:
                old = c.execute("SELECT * FROM prodotti WHERE id=?", (pid,)).fetchone()
                if not old:
                    raise ShopError("Produsul nu mai există.")
                if old["unit"] != unit:
                    raise ShopError("Unitatea unui produs existent nu poate fi schimbată. Creați un produs nou.")
                if number(data.get("version"), integer=True) != old["version"]:
                    raise ShopError("Produs modificat între timp. Reîncărcați lista.")
                c.execute("UPDATE prodotti SET nome=?, prezzo=?, barcode=?, cost_bani=?, low_stock=?, category=?, version=version+1 WHERE id=?",
                          (name, price / 100, barcode, cost, low, category, pid))
            else:
                qty = number(data.get("quantity", 0), integer=True)
                pid = c.execute("INSERT INTO prodotti (nome, quantita, prezzo, barcode, unit, cost_bani, low_stock, category) VALUES (?,?,?,?,?,?,?,?)",
                                (name, qty, price / 100, barcode, unit, cost, low, category)).lastrowid
                self.movement(c, pid, name, "stoc inițial", qty, unit)
        return {"id": pid}

    @staticmethod
    def movement(c, pid, name, kind, qty, unit):
        c.execute("INSERT INTO movimenti (id_prodotto,nome,tipo,quantita,data,unit) VALUES (?,?,?,?,?,?)",
                  (pid, name, kind, qty, now(), unit))

    def restock(self, data):
        qty = number(data.get("quantity"), integer=True, minimum=1)
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT id FROM counts WHERE closed IS NULL").fetchone():
                raise ShopError("Finalizați inventarierea înainte de recepția mărfii.")
            p = c.execute("SELECT * FROM prodotti WHERE id=?", (data.get("id"),)).fetchone()
            if not p:
                raise ShopError("Produsul nu există.")
            c.execute("UPDATE prodotti SET quantita=quantita+?, version=version+1 WHERE id=?", (qty, p["id"]))
            self.movement(c, p["id"], p["nome"], "recepție", qty, p["unit"])
        return {"ok": True}

    def checkout(self, data):
        lines = data.get("lines")
        token = str(data.get("token", ""))
        if not isinstance(lines, list) or not lines or len(lines) > 500 or not 8 <= len(token) <= 100:
            raise ShopError("Coșul este gol sau invalid.")
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            existing = c.execute("SELECT sale_id FROM sale_requests WHERE token=?", (token,)).fetchone()
            if existing:
                return {"id": existing[0], "repeated": True}
            if c.execute("SELECT id FROM counts WHERE closed IS NULL").fetchone():
                raise ShopError("Inventariere în curs. Finalizați inventarul înainte de vânzare.")
            prepared = []
            for line in lines:
                qty = number(line.get("quantity"), integer=True, minimum=1)
                p = c.execute("SELECT * FROM prodotti WHERE id=?", (line.get("id"),)).fetchone()
                if not p or p["quantita"] < qty:
                    raise ShopError(f"Stoc insuficient: {p['nome'] if p else 'produs inexistent'}.")
                price = bani(p["prezzo"])
                if bani(line.get("price")) != price:
                    raise ShopError(f"Preț schimbat pentru {p['nome']}. Actualizați coșul.")
                total = amount(price, qty, p["unit"])
                cost = None if p["cost_bani"] is None else amount(p["cost_bani"], qty, p["unit"])
                result = c.execute("UPDATE prodotti SET quantita=quantita-?, version=version+1 WHERE id=? AND quantita>=?", (qty, p["id"], qty))
                if result.rowcount != 1:
                    raise ShopError("Stoc insuficient.")
                prepared.append((p, qty, price, total, cost))
            total = sum(x[3] for x in prepared)
            sale = c.execute("INSERT INTO vendite (totale,data,web_receipt) VALUES (?,?,1)", (total / 100, now())).lastrowid
            for p, qty, price, subtotal, cost in prepared:
                c.execute("INSERT INTO sale_lines (sale_id,product_id,name,unit,quantity,price_bani,cost_bani,total_bani,cost_total_bani) VALUES (?,?,?,?,?,?,?,?,?)",
                          (sale, p["id"], p["nome"], p["unit"], qty, price, p["cost_bani"], subtotal, cost))
                self.movement(c, p["id"], p["nome"], "vanzare", qty, p["unit"])
            c.execute("INSERT INTO sale_requests VALUES (?,?)", (token, sale))
        return {"id": sale, "total_bani": total}

    def count(self):
        with self.connect() as c:
            session = c.execute("SELECT * FROM counts WHERE closed IS NULL").fetchone()
            if not session:
                return None
            result = dict(session)
            result["lines"] = [dict(r) for r in c.execute("SELECT * FROM count_lines WHERE count_id=? ORDER BY name", (session["id"],))]
            return result

    def start_count(self):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT id FROM counts WHERE closed IS NULL").fetchone():
                raise ShopError("Există deja o inventariere deschisă.")
            if not c.execute("SELECT id FROM prodotti LIMIT 1").fetchone():
                raise ShopError("Adăugați produse înainte de inventariere.")
            cid = c.execute("INSERT INTO counts(created) VALUES (?)", (now(),)).lastrowid
            c.execute("INSERT INTO count_lines (count_id,product_id,name,unit,expected,version) SELECT ?,id,nome,unit,quantita,version FROM prodotti", (cid,))
        return self.count()

    def save_count(self, data):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            cid = data.get("id")
            if not c.execute("SELECT id FROM counts WHERE id=? AND closed IS NULL", (cid,)).fetchone():
                raise ShopError("Inventarierea nu mai este deschisă.")
            for line in data.get("lines", []):
                qty = None if line.get("counted") in (None, "") else number(line["counted"], integer=True)
                if c.execute("UPDATE count_lines SET counted=? WHERE count_id=? AND product_id=?", (qty, cid, line.get("product_id"))).rowcount != 1:
                    raise ShopError("Produs invalid în inventar.")
            if data.get("finish"):
                lines = c.execute("SELECT * FROM count_lines WHERE count_id=?", (cid,)).fetchall()
                if any(r["counted"] is None for r in lines):
                    raise ShopError("Numărați toate produsele. Introduceți 0 pentru cele care lipsesc.")
                current = c.execute("SELECT id,version,quantita FROM prodotti ORDER BY id").fetchall()
                expected = {r["product_id"]: r for r in lines}
                if len(current) != len(lines) or any(r["id"] not in expected or r["version"] != expected[r["id"]]["version"] or r["quantita"] != expected[r["id"]]["expected"] for r in current):
                    raise ShopError("Stocul sau produsele s-au schimbat. Anulați inventarierea și începeți una nouă.")
                for r in lines:
                    c.execute("UPDATE prodotti SET quantita=?, version=version+1 WHERE id=?", (r["counted"], r["product_id"]))
                    self.movement(c, r["product_id"], r["name"], f"inventar #{cid}", r["counted"] - r["expected"], r["unit"])
                c.execute("UPDATE counts SET closed=? WHERE id=?", (now(), cid))
        return {"ok": True}

    def cancel_count(self, data):
        with self.connect() as c:
            c.execute("UPDATE counts SET closed=? WHERE id=? AND closed IS NULL", ("anulat " + now(), data.get("id")))
        return {"ok": True}

    def reports(self, start, end):
        try:
            first, last = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
            if first > last:
                raise ValueError()
        except (ValueError, TypeError):
            raise ShopError("Selectați o perioadă validă.") from None
        args = (start, end)
        with self.connect() as c:
            totals = dict(c.execute("""SELECT COUNT(*) receipts, COALESCE(SUM(ROUND(totale*100)),0) revenue_bani
                FROM vendite WHERE web_receipt=1 AND date(data) BETWEEN ? AND ?""", args).fetchone())
            totals.update(dict(c.execute("""SELECT COALESCE(SUM(l.total_bani-l.cost_total_bani),0) profit_bani,
                COALESCE(SUM(CASE WHEN l.cost_bani IS NULL THEN l.total_bani ELSE 0 END),0) unknown_revenue_bani,
                COUNT(CASE WHEN l.cost_bani IS NULL THEN 1 END) unknown_cost_lines
                FROM sale_lines l JOIN vendite v ON v.id=l.sale_id WHERE date(v.data) BETWEEN ? AND ?""", args).fetchone()))
            totals["legacy_receipts"] = c.execute("SELECT COUNT(*) FROM vendite WHERE web_receipt=0 AND date(data) BETWEEN ? AND ?", args).fetchone()[0]
            totals["daily"] = [dict(r) for r in c.execute("SELECT date(data) day, SUM(ROUND(totale*100)) total_bani FROM vendite WHERE web_receipt=1 AND date(data) BETWEEN ? AND ? GROUP BY date(data) ORDER BY day", args)]
            totals["top"] = [dict(r) for r in c.execute("""SELECT l.name,l.unit,SUM(l.quantity) quantity,SUM(l.total_bani) total_bani
                FROM sale_lines l JOIN vendite v ON v.id=l.sale_id WHERE date(v.data) BETWEEN ? AND ?
                GROUP BY l.product_id,l.name,l.unit ORDER BY total_bani DESC LIMIT 10""", args)]
            totals["receipts_list"] = [dict(r) for r in c.execute("SELECT id,data,ROUND(totale*100) total_bani FROM vendite WHERE web_receipt=1 AND date(data) BETWEEN ? AND ? ORDER BY id DESC LIMIT 100", args)]
            totals["low_stock"] = [dict(r) for r in c.execute("SELECT id,nome,quantita,unit,low_stock FROM prodotti WHERE quantita<=low_stock ORDER BY nome")]
            totals["stock_value_bani"] = sum(amount(r["cost_bani"], r["quantita"], r["unit"]) for r in c.execute("SELECT * FROM prodotti WHERE cost_bani IS NOT NULL"))
            totals["unknown_stock_costs"] = c.execute("SELECT COUNT(*) FROM prodotti WHERE cost_bani IS NULL").fetchone()[0]
            return totals


def default_database():
    """Reuse the installed app's data; otherwise copy the original project DB."""
    import sys
    target = Path(os.environ.get("APPDATA", str(Path.home()))) / "Magazin" / "inventario.db"
    source = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "inventario.db"
    if not target.exists() and source.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        old, new = sqlite3.connect(source), sqlite3.connect(target)
        try:
            with new:
                old.backup(new)
        finally:
            old.close()
            new.close()
    return target
