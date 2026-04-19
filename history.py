import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttkb

from openpyxl import Workbook

import state


def mostra_storico():
    win = ttkb.Toplevel()
    win.title("Mișcări Istorice")
    win.geometry("1100x500")

    frame_filtri = ttkb.Frame(win, padding=12)
    frame_filtri.pack(fill="x")

    ttkb.Label(frame_filtri, text="Caută produs").grid(row=0, column=0, sticky="w", padx=4, pady=4)
    entry_search = ttkb.Entry(frame_filtri, width=25)
    entry_search.grid(row=0, column=1, padx=4, pady=4)

    ttkb.Label(frame_filtri, text="De pe (YYYY-MM-DD)").grid(row=1, column=0, sticky="w", padx=4, pady=4)
    entry_da = ttkb.Entry(frame_filtri, width=18)
    entry_da.grid(row=1, column=1, padx=4, pady=4)

    ttkb.Label(frame_filtri, text="Până pe (YYYY-MM-DD)").grid(row=1, column=2, sticky="w", padx=4, pady=4)
    entry_a = ttkb.Entry(frame_filtri, width=18)
    entry_a.grid(row=1, column=3, padx=4, pady=4)

    tree_mov = ttkb.Treeview(win, columns=("ID", "Denumire", "Tip", "Cantitate", "Data"),
                             show="headings", bootstyle="primary")

    for col in ("ID", "Denumire", "Tip", "Cantitate", "Data"):
        tree_mov.heading(col, text=col)

    tree_mov.column("ID", width=60, anchor="center")
    tree_mov.column("Cantitate", anchor="center", width=110)
    tree_mov.column("Tip", anchor="center", width=130)
    tree_mov.column("Data", anchor="center", width=180)

    tree_mov.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    tree_mov.tag_configure("carico", background="#e6f4ea", foreground="#1e7a3c")
    tree_mov.tag_configure("încarcare", background="#e6f4ea", foreground="#1e7a3c")
    tree_mov.tag_configure("scarico", background="#fdecea", foreground="#b02a37")
    tree_mov.tag_configure("descărcare", background="#fdecea", foreground="#b02a37")
    tree_mov.tag_configure("vendita", background="#eaf2fc", foreground="#1c5fa0")
    tree_mov.tag_configure("vanzare", background="#eaf2fc", foreground="#1c5fa0")

    def carica_dati():
        for row in tree_mov.get_children():
            tree_mov.delete(row)

        query = "SELECT id_prodotto, nome, tipo, quantita, data FROM movimenti WHERE 1=1"
        params = []

        if entry_search.get():
            query += " AND nome LIKE ?"
            params.append("%" + entry_search.get() + "%")

        if entry_da.get():
            query += " AND date(data) >= date(?)"
            params.append(entry_da.get())

        if entry_a.get():
            query += " AND date(data) <= date(?)"
            params.append(entry_a.get())

        query += " ORDER BY data DESC"

        state.cursor.execute(query, params)

        for row in state.cursor.fetchall():
            tree_mov.insert("", tk.END, values=row, tags=(row[2],))

    ttkb.Button(frame_filtri, text="Filtrează", command=carica_dati,
                bootstyle="primary", padding=6).grid(row=0, column=2, padx=6, pady=4)

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

    ttkb.Button(frame_filtri, text="Exportă Excel", command=esporta_storico,
                bootstyle="secondary", padding=6).grid(row=0, column=3, padx=6, pady=4)
    carica_dati()
