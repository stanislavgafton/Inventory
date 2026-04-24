from tkinter import filedialog, messagebox

from openpyxl import Workbook

import state


def esporta_excel():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx")],
        title="Salvează file Excel"
    )

    if not file_path:
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventar"

    ws.append(["ID", "Denumire", "Cantitate", "Preț", "Barcode", "UM"])

    state.cursor.execute(
        "SELECT id, nome, quantita, prezzo, barcode, unit FROM prodotti"
    )
    for row in state.cursor.fetchall():
        ws.append(row)

    wb.save(file_path)

    messagebox.showinfo("Succes", "Excel salvat!")
