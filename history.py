import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from openpyxl import Workbook

import state


def mostra_storico():
    win = tk.Toplevel()
    win.title("Mișcări Istorice")
    win.geometry("1000x400")

    frame_filtri = tk.Frame(win)
    frame_filtri.pack(pady=5)

    tk.Label(frame_filtri, text="Cauta Produs").grid(row=0, column=0)
    entry_search = tk.Entry(frame_filtri)
    entry_search.grid(row=0, column=1)

    tk.Label(frame_filtri, text="De pe (YYYY-MM-DD)").grid(row=1, column=0)
    entry_da = tk.Entry(frame_filtri)
    entry_da.grid(row=1, column=1)

    tk.Label(frame_filtri, text="Pana pe (YYYY-MM-DD)").grid(row=1, column=2)
    entry_a = tk.Entry(frame_filtri)
    entry_a.grid(row=1, column=3)

    tree_mov = ttk.Treeview(win, columns=("ID", "Denumire", "Tip", "Cantitate", "Data"), show="headings")

    for col in ("ID", "Denumire", "Tip", "Cantitate", "Data"):
        tree_mov.heading(col, text=col)

    tree_mov.pack(fill="both", expand=True)

    tree_mov.tag_configure("carico", background="#ccffcc")
    tree_mov.tag_configure("scarico", background="#ffcccc")
    tree_mov.tag_configure("vendita", background="#cce5ff")

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

    tk.Button(frame_filtri, text="Filtra", command=carica_dati).grid(row=0, column=2, padx=5)

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

    tk.Button(frame_filtri, text="Exportă Excel", command=esporta_storico).grid(row=0, column=3, padx=5)
    carica_dati()
