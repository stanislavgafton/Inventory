"""Atomic receipt writer for the retained desktop app."""
import datetime
import math
from units import line_total


def record_sale(conn, items):
    items = list(items)
    if not items:
        raise ValueError("Coșul e gol")
    timestamp = datetime.datetime.now().isoformat(sep=" ")
    total = 0
    with conn:
        for pid, name, price, quantity, unit in items:
            if not isinstance(quantity, int) or quantity <= 0 or not math.isfinite(float(price)) or float(price) < 0:
                raise ValueError("Cantitate sau preț invalid")
            result = conn.execute("UPDATE prodotti SET quantita=quantita-? WHERE id=? AND quantita>=?", (quantity,pid,quantity))
            if result.rowcount != 1:
                raise ValueError(f"Stoc insuficient sau produs șters: {name}")
            total += line_total(price,quantity,unit)
            conn.execute("INSERT INTO movimenti (id_prodotto,nome,tipo,quantita,data,unit) VALUES (?,?,?,?,?,?)",(pid,name,"vanzare",quantity,timestamp,unit))
        total = round(total,2)
        conn.execute("INSERT INTO vendite (totale,data) VALUES (?,?)",(total,timestamp))
    return total
