UNIT_BUC = "buc"
UNIT_G = "g"
UNITS = (UNIT_BUC, UNIT_G)


def normalize_unit(u):
    if u is None:
        return UNIT_BUC
    u = str(u).strip().lower()
    if u in ("g", "gr", "gram", "grame", "grams", "kg"):
        return UNIT_G
    return UNIT_BUC


def format_qty(q, unit):
    try:
        q = int(q)
    except (TypeError, ValueError):
        q = 0
    if unit == UNIT_G:
        if abs(q) >= 1000:
            kg = q / 1000.0
            s = f"{kg:.3f}".rstrip("0").rstrip(".")
            return f"{s} kg"
        return f"{q} g"
    return f"{q} buc"


def format_unit_price(prezzo, unit):
    try:
        prezzo = float(prezzo)
    except (TypeError, ValueError):
        prezzo = 0.0
    suffix = "kg" if unit == UNIT_G else "buc"
    return f"{prezzo:.2f} lei/{suffix}"


def line_total(prezzo, q, unit):
    if unit == UNIT_G:
        return float(prezzo) * int(q) / 1000.0
    return float(prezzo) * int(q)


def qty_step(unit):
    return 50 if unit == UNIT_G else 1


def qty_label(unit):
    return "Cantitate (g)" if unit == UNIT_G else "Cantitate"


def price_label(unit):
    return "Preț (lei/kg)" if unit == UNIT_G else "Preț (lei/buc)"


def stock_thresholds(unit):
    # (low, medium) — values strictly below `low` are critical, up to `medium` are warning
    if unit == UNIT_G:
        return (500, 2000)
    return (5, 20)
