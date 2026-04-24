import tkinter as tk

import ttkbootstrap as ttkb

import state
from export import esporta_excel
from import_products import importa_excel
from products import (
    aggiorna_tabella,
    cerca_barcode_stock,
    cerca_prodotto,
    elimina_prodotto,
    preview_stock_prodotto,
    seleziona_prodotto,
)
from units import UNIT_BUC, UNIT_G, stock_thresholds


def _fmt_g(q):
    if q >= 1000:
        kg = q / 1000.0
        s = f"{kg:.3f}".rstrip("0").rstrip(".")
        return f"{s} kg"
    return f"{q} g"


CANVAS_BG = "#e9ecef"
LIGHT_BG = "#f8f9fa"
MUTED_FG = "#6c757d"
INFO_FG = "#9954bb"

_win = None


def mostra_stock():
    global _win

    if _win is not None and _win.winfo_exists():
        _win.deiconify()
        _win.lift()
        _win.focus_force()
        return

    win = ttkb.Toplevel()
    _win = win
    win.title("Stock")
    win.geometry("1100x640")
    win.minsize(700, 440)
    win.configure(bg=CANVAS_BG)

    # --- Header ---
    header = ttkb.Frame(win, padding=(16, 14, 16, 4))
    header.pack(fill="x")
    ttkb.Label(header, text="Stock",
               font=("Segoe UI", 16, "bold"),
               background=CANVAS_BG,
               foreground=INFO_FG).pack(anchor="w")
    ttkb.Label(header, text="Produsele din inventar — caută, filtrează, selectează",
               font=("Segoe UI", 10),
               background=CANVAS_BG,
               foreground=MUTED_FG).pack(anchor="w")

    style = ttkb.Style()
    style.configure("Violet.TEntry",
                    bordercolor=INFO_FG, lightcolor=INFO_FG, darkcolor=INFO_FG)
    style.map("Violet.TEntry",
              bordercolor=[("focus", INFO_FG), ("!focus", INFO_FG)],
              lightcolor=[("focus", INFO_FG), ("!focus", INFO_FG)],
              darkcolor=[("focus", INFO_FG), ("!focus", INFO_FG)])

    # --- Barcode card ---
    bc_card = ttkb.Frame(win, padding=14, bootstyle="light")
    bc_card.pack(fill="x", padx=16, pady=(8, 0))

    ttkb.Label(bc_card, text="Scanează barcode",
               font=("Segoe UI", 9),
               background=LIGHT_BG,
               foreground=MUTED_FG).pack(anchor="w")
    entry_barcode_stock = ttkb.Entry(bc_card,
                                     font=("Segoe UI", 16),
                                     style="Violet.TEntry")
    entry_barcode_stock.pack(fill="x", pady=(4, 0), ipady=4)
    state.entry_barcode_stock = entry_barcode_stock

    entry_barcode_stock.bind("<Return>", cerca_barcode_stock)
    entry_barcode_stock.bind("<KP_Enter>", cerca_barcode_stock)

    # --- Search card ---
    card = ttkb.Frame(win, padding=14, bootstyle="light")
    card.pack(fill="x", padx=16, pady=(8, 8))

    card.columnconfigure(0, weight=1)

    search_col = ttkb.Frame(card, bootstyle="light")
    search_col.grid(row=0, column=0, sticky="ew")
    ttkb.Label(search_col, text="Caută produs",
               font=("Segoe UI", 9),
               background=LIGHT_BG,
               foreground=MUTED_FG).pack(anchor="w")

    search_row = ttkb.Frame(search_col, bootstyle="light")
    search_row.pack(anchor="w", fill="x", pady=(2, 0))

    entry_ricerca = ttkb.Entry(search_row, width=40, style="Violet.TEntry")
    entry_ricerca.pack(side="left")
    state.entry_ricerca = entry_ricerca

    def _reset_search():
        entry_ricerca.delete(0, "end")
        aggiorna_tabella()

    ttkb.Button(search_row, text="Caută", command=cerca_prodotto,
                bootstyle="info", padding=8).pack(side="left", padx=(8, 4))
    ttkb.Button(search_row, text="Resetează", command=_reset_search,
                bootstyle="secondary-outline", padding=8).pack(side="left", padx=4)
    ttkb.Button(search_row, text="Elimină", command=elimina_prodotto,
                bootstyle="danger", padding=8).pack(side="left", padx=4)

    actions = ttkb.Frame(card, bootstyle="light")
    actions.grid(row=0, column=1, sticky="e")
    # Spacer to align buttons with entry (entry has caption above)
    ttkb.Frame(actions, bootstyle="light", height=14).pack(anchor="e")
    btn_row = ttkb.Frame(actions, bootstyle="light")
    btn_row.pack(anchor="e", pady=(2, 0))

    ttkb.Button(btn_row, text="Importă Excel", command=importa_excel,
                bootstyle="info-outline", padding=8).pack(side="left", padx=4)
    ttkb.Button(btn_row, text="Exportă Excel", command=esporta_excel,
                bootstyle="info-outline", padding=8).pack(side="left", padx=4)

    entry_ricerca.bind("<Return>", lambda _e: cerca_prodotto())

    # --- Treeview ---
    tree_frame = ttkb.Frame(win)
    tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

    tree = ttkb.Treeview(tree_frame,
                         columns=("ID", "Denumire", "Cantitate", "Preț", "Barcode"),
                         show="headings", bootstyle="info")
    tree.tag_configure("basso", background="#fdecea", foreground="#b02a37")
    tree.tag_configure("medio", background="#fff4d6", foreground="#8a6d1a")
    tree.tag_configure("odd", background="#f8f9fa")

    tree.heading("ID", text="ID")
    tree.heading("Denumire", text="Denumire")
    tree.heading("Cantitate", text="Cantitate")
    tree.heading("Preț", text="Preț")
    tree.heading("Barcode", text="Barcode")

    tree.column("ID", width=60, anchor="center")
    tree.column("Denumire", width=360, anchor="w", stretch=True)
    tree.column("Cantitate", anchor="center", width=110)
    tree.column("Preț", anchor="e", width=150)
    tree.column("Barcode", anchor="center", width=200)

    vsb = ttkb.Scrollbar(tree_frame, orient="vertical",
                         command=tree.yview, bootstyle="round")
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    tree.bind("<ButtonRelease-1>", seleziona_prodotto)

    def _on_double_click(event):
        item = tree.identify_row(event.y)
        if not item:
            return
        values = tree.item(item, "values")
        if not values:
            return
        try:
            idp = int(values[0])
        except (TypeError, ValueError):
            return
        state.cursor.execute(
            "SELECT id, nome, quantita, prezzo, barcode, unit FROM prodotti WHERE id = ?",
            (idp,),
        )
        row = state.cursor.fetchone()
        if row:
            preview_stock_prodotto(row)

    tree.bind("<Double-1>", _on_double_click)
    state.tree = tree

    # --- Footer: stock legend ---
    footer = ttkb.Frame(win, padding=(16, 4, 16, 12))
    footer.pack(fill="x")

    low_b, med_b = stock_thresholds(UNIT_BUC)
    low_g, med_g = stock_thresholds(UNIT_G)
    legend_items = [
        (f"stoc scăzut (<{low_b} buc / <{_fmt_g(low_g)})", "#b02a37"),
        (f"stoc mediu ({low_b}–{med_b} buc / {_fmt_g(low_g)}–{_fmt_g(med_g)})", "#8a6d1a"),
        (f"stoc normal (>{med_b} buc / >{_fmt_g(med_g)})", "#1e7a3c"),
    ]
    for text, color in legend_items:
        item = ttkb.Frame(footer)
        item.pack(side="left", padx=(0, 16))
        dot = tk.Canvas(item, width=14, height=14,
                        highlightthickness=0, bd=0, bg=CANVAS_BG)
        dot.create_oval(2, 2, 12, 12, fill=color, outline=color)
        dot.pack(side="left")
        ttkb.Label(item, text=text,
                   font=("Segoe UI", 9),
                   background=CANVAS_BG,
                   foreground=MUTED_FG).pack(side="left", padx=(6, 0))

    def _on_close():
        global _win
        state.tree = None
        state.entry_ricerca = None
        state.entry_barcode_stock = None
        _win = None
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close)

    NARROW = 820
    _last_narrow = [None]

    def _reflow(event):
        if event.widget is not win:
            return
        narrow = win.winfo_width() < NARROW
        if narrow == _last_narrow[0]:
            return
        _last_narrow[0] = narrow
        if narrow:
            actions.grid_configure(row=1, column=0, sticky="w", pady=(8, 0))
        else:
            actions.grid_configure(row=0, column=1, sticky="e", pady=0)

    win.bind("<Configure>", _reflow)

    aggiorna_tabella()
    entry_barcode_stock.focus_set()
