import tkinter as tk

import ttkbootstrap as ttkb

import state
from products import aggiorna_tabella, cerca_prodotto, seleziona_prodotto


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
    win.minsize(900, 500)
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

    # --- Search card ---
    card = ttkb.Frame(win, padding=14, bootstyle="light")
    card.pack(fill="x", padx=16, pady=(8, 8))

    search_col = ttkb.Frame(card, bootstyle="light")
    search_col.pack(side="left", anchor="w")
    ttkb.Label(search_col, text="Caută produs",
               font=("Segoe UI", 9),
               background=LIGHT_BG,
               foreground=MUTED_FG).pack(anchor="w")
    style = ttkb.Style()
    style.configure("Violet.TEntry",
                    bordercolor=INFO_FG, lightcolor=INFO_FG, darkcolor=INFO_FG)
    style.map("Violet.TEntry",
              bordercolor=[("focus", INFO_FG), ("!focus", INFO_FG)],
              lightcolor=[("focus", INFO_FG), ("!focus", INFO_FG)],
              darkcolor=[("focus", INFO_FG), ("!focus", INFO_FG)])
    entry_ricerca = ttkb.Entry(search_col, width=40, style="Violet.TEntry")
    entry_ricerca.pack(anchor="w", pady=(2, 0))
    state.entry_ricerca = entry_ricerca

    actions = ttkb.Frame(card, bootstyle="light")
    actions.pack(side="right", anchor="e")
    # Spacer to align buttons with entry (entry has caption above)
    ttkb.Frame(actions, bootstyle="light", height=14).pack(anchor="e")
    btn_row = ttkb.Frame(actions, bootstyle="light")
    btn_row.pack(anchor="e", pady=(2, 0))

    def _reset_search():
        entry_ricerca.delete(0, "end")
        aggiorna_tabella()

    ttkb.Button(btn_row, text="Caută", command=cerca_prodotto,
                bootstyle="info", padding=8).pack(side="left", padx=4)
    ttkb.Button(btn_row, text="Resetează", command=_reset_search,
                bootstyle="secondary-outline", padding=8).pack(side="left", padx=4)

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
    tree.column("Denumire", width=360, anchor="w")
    tree.column("Cantitate", anchor="center", width=110)
    tree.column("Preț", anchor="e", width=110)
    tree.column("Barcode", anchor="center", width=200)

    vsb = ttkb.Scrollbar(tree_frame, orient="vertical",
                         command=tree.yview, bootstyle="round")
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    tree.bind("<ButtonRelease-1>", seleziona_prodotto)
    state.tree = tree

    # --- Footer: stock legend ---
    footer = ttkb.Frame(win, padding=(16, 4, 16, 12))
    footer.pack(fill="x")

    legend_items = [
        ("stoc scăzut (<5)", "#b02a37"),
        ("stoc mediu (5–20)", "#8a6d1a"),
        ("stoc normal (>20)", "#1e7a3c"),
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
        _win = None
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _on_close)

    aggiorna_tabella()
    entry_ricerca.focus_set()
