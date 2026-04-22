import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttkb

from openpyxl import Workbook

import state


CARD_BG = "#ffffff"
TEXT = "#495057"
MUTED_BG = "#f8f9fa"

TIP_COLORS = {
    "încarcare": ("#e6f4ea", "#1e7a3c"),
    "descărcare": ("#fdecea", "#b02a37"),
    "vanzare": ("#eaf2fc", "#1c5fa0"),
}

TIP_CHOICES = ["Toate", "încarcare", "descărcare", "vanzare"]


def _caption(parent, text):
    return ttkb.Label(parent, text=text,
                      font=("Segoe UI", 9),
                      bootstyle="secondary")


def mostra_storico():
    win = ttkb.Toplevel()
    win.title("Mișcări Istorice")
    win.geometry("1200x640")
    win.minsize(1000, 520)

    header = ttkb.Frame(win, padding=(16, 14, 16, 4))
    header.pack(fill="x")
    ttkb.Label(header, text="Mișcări Istorice",
               font=("Segoe UI", 16, "bold"),
               bootstyle="primary").pack(anchor="w")
    ttkb.Label(header, text="Istoricul încărcărilor, descărcărilor și vânzărilor",
               font=("Segoe UI", 10),
               bootstyle="secondary").pack(anchor="w")

    card = ttkb.Frame(win, padding=14, bootstyle="light")
    card.pack(fill="x", padx=16, pady=(8, 8))

    filters_left = ttkb.Frame(card, bootstyle="light")
    filters_left.pack(side="left", anchor="w")

    actions_right = ttkb.Frame(card, bootstyle="light")
    actions_right.pack(side="right", anchor="e")

    # --- Filters ---
    col_produs = ttkb.Frame(filters_left, bootstyle="light")
    col_produs.pack(side="left", padx=(0, 14))
    _caption(col_produs, "Produs").pack(anchor="w")
    entry_search = ttkb.Entry(col_produs, width=22)
    entry_search.pack(anchor="w", pady=(2, 0))

    col_da = ttkb.Frame(filters_left, bootstyle="light")
    col_da.pack(side="left", padx=(0, 14))
    _caption(col_da, "De pe").pack(anchor="w")
    date_da = ttkb.DateEntry(col_da, width=12, dateformat="%Y-%m-%d",
                             bootstyle="primary")
    date_da.pack(anchor="w", pady=(2, 0))
    date_da.entry.delete(0, "end")

    col_a = ttkb.Frame(filters_left, bootstyle="light")
    col_a.pack(side="left", padx=(0, 14))
    _caption(col_a, "Până pe").pack(anchor="w")
    date_a = ttkb.DateEntry(col_a, width=12, dateformat="%Y-%m-%d",
                            bootstyle="primary")
    date_a.pack(anchor="w", pady=(2, 0))
    date_a.entry.delete(0, "end")

    col_tip = ttkb.Frame(filters_left, bootstyle="light")
    col_tip.pack(side="left", padx=(0, 14))
    _caption(col_tip, "Tip").pack(anchor="w")
    tip_var = tk.StringVar(value="Toate")
    combo_tip = ttkb.Combobox(col_tip, textvariable=tip_var,
                              values=TIP_CHOICES, state="readonly", width=14)
    combo_tip.pack(anchor="w", pady=(2, 0))

    # --- Treeview (defined before buttons so handlers can close over it) ---
    tree_frame = ttkb.Frame(win)
    tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

    tree_mov = ttkb.Treeview(tree_frame,
                             columns=("ID", "Denumire", "Tip", "Cantitate", "Data"),
                             show="headings", bootstyle="primary")

    for col in ("ID", "Denumire", "Tip", "Cantitate", "Data"):
        tree_mov.heading(col, text=col)

    tree_mov.column("ID", width=60, anchor="center")
    tree_mov.column("Denumire", width=360, anchor="w")
    tree_mov.column("Tip", anchor="center", width=130)
    tree_mov.column("Cantitate", anchor="center", width=110)
    tree_mov.column("Data", anchor="center", width=180)

    vsb = ttkb.Scrollbar(tree_frame, orient="vertical", command=tree_mov.yview)
    tree_mov.configure(yscrollcommand=vsb.set)
    tree_mov.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    tree_mov.tag_configure("odd", background=MUTED_BG)
    for tipo, (bg, fg) in TIP_COLORS.items():
        tree_mov.tag_configure(tipo, background=bg, foreground=fg)
    # Legacy Italian tags still coloured for old rows
    tree_mov.tag_configure("carico", background="#e6f4ea", foreground="#1e7a3c")
    tree_mov.tag_configure("scarico", background="#fdecea", foreground="#b02a37")
    tree_mov.tag_configure("vendita", background="#eaf2fc", foreground="#1c5fa0")

    count_var = tk.StringVar(value="0 mișcări")

    def carica_dati():
        for row in tree_mov.get_children():
            tree_mov.delete(row)

        query = "SELECT id_prodotto, nome, tipo, quantita, data FROM movimenti WHERE 1=1"
        params = []

        if entry_search.get():
            query += " AND nome LIKE ?"
            params.append("%" + entry_search.get() + "%")

        da_val = date_da.entry.get().strip()
        if da_val:
            query += " AND date(data) >= date(?)"
            params.append(da_val)

        a_val = date_a.entry.get().strip()
        if a_val:
            query += " AND date(data) <= date(?)"
            params.append(a_val)

        tip_val = tip_var.get()
        if tip_val and tip_val != "Toate":
            query += " AND tipo = ?"
            params.append(tip_val)

        query += " ORDER BY data DESC"

        state.cursor.execute(query, params)

        n = 0
        for i, row in enumerate(state.cursor.fetchall()):
            tags = [row[2]]
            if i % 2 == 1:
                tags.append("odd")
            tree_mov.insert("", tk.END, values=row, tags=tuple(tags))
            n += 1

        count_var.set(f"{n} mișcări")

    def reset_filtre():
        entry_search.delete(0, "end")
        date_da.entry.delete(0, "end")
        date_a.entry.delete(0, "end")
        tip_var.set("Toate")
        carica_dati()

    def esporta_storico():
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx")

        if not file_path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Mișcări"

        ws.append(["ID", "Denumire", "Tip", "Cantitate", "Dată"])

        for row in tree_mov.get_children():
            ws.append(tree_mov.item(row)["values"])

        wb.save(file_path)

        messagebox.showinfo("OK", "Mișcări exportate!")

    # --- Action buttons ---
    btn_spacer = ttkb.Frame(actions_right, bootstyle="light", height=14)
    btn_spacer.pack(anchor="e")
    btn_row = ttkb.Frame(actions_right, bootstyle="light")
    btn_row.pack(anchor="e", pady=(2, 0))

    ttkb.Button(btn_row, text="Filtrează", command=carica_dati,
                bootstyle="primary", padding=8).pack(side="left", padx=4)
    ttkb.Button(btn_row, text="Resetează", command=reset_filtre,
                bootstyle="secondary-outline", padding=8).pack(side="left", padx=4)
    ttkb.Button(btn_row, text="Exportă Excel", command=esporta_storico,
                bootstyle="success-outline", padding=8).pack(side="left", padx=4)

    entry_search.bind("<Return>", lambda _e: carica_dati())

    # --- Footer: count + legend ---
    footer = ttkb.Frame(win, padding=(16, 4, 16, 12))
    footer.pack(fill="x")

    ttkb.Label(footer, textvariable=count_var,
               font=("Segoe UI", 10),
               bootstyle="secondary").pack(side="left")

    legend = ttkb.Frame(footer)
    legend.pack(side="right")

    for tipo, (bg, fg) in TIP_COLORS.items():
        item = ttkb.Frame(legend)
        item.pack(side="left", padx=(10, 0))
        dot = tk.Canvas(item, width=14, height=14,
                        highlightthickness=0, bd=0)
        dot.create_oval(2, 2, 12, 12, fill=fg, outline=fg)
        dot.pack(side="left")
        ttkb.Label(item, text=tipo,
                   font=("Segoe UI", 9),
                   bootstyle="secondary").pack(side="left", padx=(6, 0))

    carica_dati()
