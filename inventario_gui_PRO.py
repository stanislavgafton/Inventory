from openpyxl import Workbook
import sqlite3
import tkinter as tk
import datetime
import winsound
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from tkinter import ttk, messagebox
from tkinter import filedialog
from tkinter import simpledialog


# DB
conn = sqlite3.connect("inventario.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movimenti (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_prodotto INTEGER,
    nome TEXT,
    tipo TEXT,           -- carico / scarico / vendita
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
    prezzo REAL
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
# CLASSI
class Carrello(list):
    def __init__(self, callback=None):
        super().__init__()
        self.callback = callback

    def _notify(self):
        if self.callback:
            self.callback()

    def append(self, item):
        super().append(item)
        self._notify()

    def remove(self, item):
        super().remove(item)
        self._notify()

    def clear(self):
        super().clear()
        self._notify()

    def pop(self, index=-1):
        item = super().pop(index)
        self._notify()
        return item

# FUNZIONI
# def aggiorna_stato_bottone():
#     if carrello:
#         btn_chiudi_scontrino.config(state="normal")
#     else:
#         btn_chiudi_scontrino.config(state="disabled")
def mostra_dashboard():
    win = tk.Toplevel()
    win.title("Dashboard")
    win.geometry("1000x800")

    cursor.execute("SELECT SUM(totale) FROM vendite")
    totale = cursor.fetchone()[0] or 0

    tk.Label(win, text=f"Totale vendite: {totale:.2f} lei",
             font=("Arial", 16)).pack(pady=10)

    frame_grafici = tk.Frame(win)
    frame_grafici.columnconfigure(0, weight=1)
    frame_grafici.columnconfigure(1, weight=1)
    frame_grafici.rowconfigure(0, weight=1)
    frame_grafici.pack(fill="both", expand=True)

    # ===== GRAFICO 1: vendite per giorno =====
    cursor.execute("""
        SELECT substr(data, 1, 10), SUM(totale)
        FROM vendite
        GROUP BY substr(data, 1, 10)
        ORDER BY substr(data, 1, 10)
    """)

    dati = cursor.fetchall()

    fig1 = plt.Figure(figsize=(3, 3))
    ax1 = fig1.add_subplot(111)

    if dati:
        date = [row[0] for row in dati]
        valori = [row[1] for row in dati]

        ax1.plot(date, valori)
        ax1.set_title("Vendite per giorno")
        ax1.tick_params(axis='x', rotation=45)

    canvas1 = FigureCanvasTkAgg(fig1, master=frame_grafici)
    canvas1.draw()
    canvas1.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    # ===== GRAFICO 2: top prodotti =====
    cursor.execute("""
        SELECT nome, SUM(quantita)
        FROM movimenti
        WHERE tipo = 'vendita'
        GROUP BY nome
        ORDER BY SUM(quantita) DESC
        LIMIT 5
    """)

    top = cursor.fetchall()

    fig2 = plt.Figure(figsize=(3, 3))
    ax2 = fig2.add_subplot(111)

    if top:
        nomi = [row[0] for row in top]
        quantita = [row[1] for row in top]

        ax2.bar(nomi, quantita)
        ax2.set_title("Top prodotti venduti")
        ax2.tick_params(axis='x', rotation=45)

    canvas2 = FigureCanvasTkAgg(fig2, master=frame_grafici)
    canvas2.draw()
    canvas2.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

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

    ws.append(["ID", "Denumire", "Cantitate", "Preț","Barcode"])

    cursor.execute("SELECT * FROM prodotti")
    for row in cursor.fetchall():
        ws.append(row)

    wb.save(file_path)

    messagebox.showinfo("Succes", "Excel salvat!")

def aggiorna_tabella():
    for row in tree.get_children():
        tree.delete(row)

    cursor.execute("SELECT * FROM prodotti")
    for row in cursor.fetchall():
        q = row[2]  # quantità

        if q < 5:
            tree.insert("", tk.END, values=row, tags=("basso",))
        elif q <= 20:
            tree.insert("", tk.END, values=row, tags=("medio",))
        else:
            tree.insert("", tk.END, values=row)

def seleziona_prodotto(event):
    selezionato = tree.focus()
    dati = tree.item(selezionato, "values")

    if dati:
        entry_nome.delete(0, tk.END)
        entry_nome.insert(0, dati[1])

        entry_quantita.delete(0, tk.END)
        entry_quantita.insert(0, dati[2])

        entry_prezzo.delete(0, tk.END)
        entry_prezzo.insert(0, dati[3])
        
        entry_barcode.delete(0, tk.END)
        entry_barcode.insert(0, dati[4])

def elimina_prodotto():
    selezionato = tree.focus()
    dati = tree.item(selezionato, "values")

    if not dati:
        return

    id_prodotto = dati[0]

    cursor.execute("DELETE FROM prodotti WHERE id=?", (id_prodotto,))
    conn.commit()
    aggiorna_tabella()

def cerca_prodotto():
    parola = entry_ricerca.get()

    for row in tree.get_children():
        tree.delete(row)

    cursor.execute(
        "SELECT * FROM prodotti WHERE nome LIKE ?",
        ('%' + parola + '%',)
    )

    for row in cursor.fetchall():
        q = row[2]

        if q < 5:
            tree.insert("", tk.END, values=row, tags=("basso",))
        elif q <= 20:
            tree.insert("", tk.END, values=row, tags=("medio",))
        else:
            tree.insert("", tk.END, values=row)

def cerca_barcode(event=None):
    codice = entry_barcode.get()

    cursor.execute("SELECT * FROM prodotti WHERE barcode = ?", (codice,))
    risultato = cursor.fetchone()

    if risultato:
        winsound.Beep(1000, 150)
        preview_prodotto(risultato)
    else:
        winsound.Beep(300, 300)
        risposta = messagebox.askyesno("Nou Produs", "Produs nu a fost găsit. Vreai să îl adaugi?")
        if risposta:
            popup_nuovo_prodotto(codice)

    entry_barcode.delete(0, tk.END)
    entry_barcode.focus_set()

def rimetti_focus(event=None):
    entry_barcode.focus_set()

def chiudi_scontrino():
    global carrello

    if not carrello:
        messagebox.showwarning("Atenție", "Coșul e gol")
        return
    totale = 0

    for item in carrello:
        idp, nome, prezzo, q = item
        totale += prezzo * q

        cursor.execute(
            "UPDATE prodotti SET quantita = quantita - ? WHERE id = ?",
            (q, idp)
        )

        cursor.execute(
            "INSERT INTO vendite (totale, data) VALUES (?, ?)",
            (totale, str(datetime.datetime.now()))
        )
        cursor.execute(
            "INSERT INTO movimenti (id_prodotto, nome, tipo, quantita, data) VALUES (?, ?, ?, ?, ?)",
            (idp, nome, "vanzare", q, str(datetime.datetime.now()))
        )
        conn.commit()

    carrello.clear()
    aggiorna_tabella()
    aggiorna_carrello_ui()

    messagebox.showinfo("OK", f"Total: {totale:.2f} lei")

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

        cursor.execute(query, params)

        for row in cursor.fetchall():
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


def popup_nuovo_prodotto(barcode):
    popup = tk.Toplevel()
    popup.title("Produs Nou")
    popup.geometry("300x250")

    tk.Label(popup, text="Denumire").pack()
    entry_nome_popup = tk.Entry(popup)
    entry_nome_popup.pack()

    tk.Label(popup, text="Cantitate").pack()
    entry_q_popup = tk.Entry(popup)
    entry_q_popup.pack()

    tk.Label(popup, text="Preț").pack()
    entry_prezzo_popup = tk.Entry(popup)
    entry_prezzo_popup.pack()

    def salva(event=None):
        nome = entry_nome_popup.get()
        quantita = entry_q_popup.get()
        prezzo = entry_prezzo_popup.get()

        if not nome or not quantita or not prezzo:
            messagebox.showwarning("Erroare", "Completează toate datele!")
            return

        cursor.execute(
            "INSERT INTO prodotti (nome, quantita, prezzo, barcode) VALUES (?, ?, ?, ?)",
            (nome, int(quantita), float(prezzo), barcode)
        )
        conn.commit()

        aggiorna_tabella()
        popup.destroy()

    entry_nome_popup.bind("<Return>", lambda e: entry_q_popup.focus_set())
    entry_q_popup.bind("<Return>", lambda e: entry_prezzo_popup.focus_set())
    entry_prezzo_popup.bind("<Return>", salva)
    tk.Button(popup, text="OK", command=salva).pack(pady=10)
    popup.after(100, lambda: entry_nome_popup.focus_set())

def aggiungi_al_carrello(prodotto):
    idp, nome, q, prezzo = prodotto
    aggiorna_totale()

def aggiorna_totale():
    totale = sum(prezzo * q for _, _, prezzo, q in carrello)
    totale_var.set(f"Total: {totale:.2f} lei")


def preview_prodotto(prodotto):
    root.unbind("<Return>")
    root.unbind("<KP_Enter>")
    popup = tk.Toplevel()
    popup.title("Produs")
    popup.geometry("450x350")

    idp, nome, quantita, prezzo, barcode = prodotto

    tk.Label(popup, text=nome, font=("Arial", 14)).pack(pady=5)
    tk.Label(popup, text=f"Disponibil: {quantita}").pack()
    tk.Label(popup, text=f"Preț: {prezzo} lei").pack()

    qty_var = tk.IntVar(value=1)

    frame_qty = tk.Frame(popup)
    frame_qty.pack(pady=10)

    def meno():
        if qty_var.get() > 1:
            qty_var.set(qty_var.get() - 1)

    def piu():
        if qty_var.get() < quantita:
            qty_var.set(qty_var.get() + 1)

    tk.Button(frame_qty, text="-", width=3, command=meno).pack(side=tk.LEFT)

    entry_qty = tk.Entry(frame_qty, textvariable=qty_var, width=5, justify="center")
    entry_qty.pack(side=tk.LEFT)

    tk.Button(frame_qty, text="+", width=3, command=piu).pack(side=tk.LEFT)

    def aggiungi_carrello(event=None):
        q = qty_var.get()

        if q <= 0:
            messagebox.showwarning("Erroare", "Cantitate greșită")
            return

        if q > quantita:
            messagebox.showwarning("Stock insuficient", f"Disponibil doar {quantita}")
            return

        carrello.append((idp, nome, prezzo, q))
        aggiorna_carrello_ui()
        aggiorna_totale()
        riattiva_barcode()

    def aggiungi_stock():
        q = qty_var.get()

        if q <= 0:
            messagebox.showwarning("Erroare", "Cantitate greșită")
            return

        cursor.execute(
            "UPDATE prodotti SET quantita = quantita + ? WHERE id = ?",
            (q, idp)
        )
        cursor.execute(
            "INSERT INTO movimenti (id_prodotto, nome, tipo, quantita, data) VALUES (?, ?, ?, ?, ?)",
            (idp, nome, "încarcare", q, str(datetime.datetime.now()))
        )
        conn.commit()

        aggiorna_tabella()

        messagebox.showinfo("OK", f"Adăugate {q} la {nome}")

        riattiva_barcode()
    def rimuovi_stock():
        q = qty_var.get()

        if q <= 0:
            messagebox.showwarning("Erroare", "Cantitate greșită")
            return

        if q > quantita:
            messagebox.showwarning("Erroare", f"Disponibil doar {quantita}")
            return

        cursor.execute(
            "UPDATE prodotti SET quantita = quantita - ? WHERE id = ?",
            (q, idp)
        )
        cursor.execute(
            "INSERT INTO movimenti (id_prodotto, nome, tipo, quantita, data) VALUES (?, ?, ?, ?, ?)",
            (idp, nome, "descărcare", q, str(datetime.datetime.now()))
        )
        conn.commit()

        aggiorna_tabella()

        messagebox.showinfo("OK", f"Eliminate {q} {nome}")

        riattiva_barcode()    

    tk.Button(popup, text="Adaugă în coș", command=aggiungi_carrello).pack(pady=20)
    tk.Button(popup, text="Adaugă în inventar", command=aggiungi_stock).pack(pady=5)
    tk.Button(popup, text="Elimină în inventar", command=rimuovi_stock).pack(pady=5)

    def riattiva_barcode():
        root.bind("<Return>", cerca_barcode)
        root.bind("<KP_Enter>", cerca_barcode)
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", riattiva_barcode)
    popup.after(100, lambda: entry_qty.focus_set())

def aggiorna_carrello_ui():
    for row in tree_carrello.get_children():
        tree_carrello.delete(row)

    for item in carrello:
        idp, nome, prezzo, q = item
        totale = prezzo * q

        tree_carrello.insert(
            "",
            tk.END,
            values=(nome, q, f"{totale:.2f}", " +                           |                          - ")
        )

def click_carrello(event):
    item = tree_carrello.identify_row(event.y)
    col = tree_carrello.identify_column(event.x)

    if not item:
        return

    index = tree_carrello.index(item)

    if col == "#4":
        bbox = tree_carrello.bbox(item, column="#4")

        if not bbox:
            return

        x_click = event.x - bbox[0]
        width = bbox[2]

        # metà sinistra = +
        if x_click < width / 2:
            modifica_qta(index, +1)
        else:
            modifica_qta(index, -1)

def modifica_qta(index, delta):
    idp, nome, prezzo, q = carrello[index]

    q += delta

    if q <= 0:
        carrello.pop(index)
    else:
        carrello[index] = (idp, nome, prezzo, q)

    aggiorna_carrello_ui()
    aggiorna_totale()

def modifica_quantita(delta):
    selezionato = tree_carrello.focus()
    if not selezionato:
        return

    index = tree_carrello.index(selezionato)

    idp, nome, prezzo, q = carrello[index]

    q += delta

    if q <= 0:
        carrello.pop(index)  # ❌ elimina riga
    else:
        carrello[index] = (idp, nome, prezzo, q)

    aggiorna_carrello_ui()
    aggiorna_totale()

def reset_focus(event=None):
    entry_barcode.focus_set()

def pulisci_campi():
    entry_nome.delete(0, tk.END)
    entry_quantita.delete(0, tk.END)
    entry_prezzo.delete(0, tk.END)
    entry_barcode.delete(0, tk.END)

# GUI
root = tk.Tk()
root.title("GASTA")
root.geometry("1600x800")
root.bind("<Return>", cerca_barcode)
root.bind("<KP_Enter>", cerca_barcode)
# carrello = Carrello(callback=aggiorna_stato_bottone)
carrello = []
totale_var = tk.StringVar()
totale_var.set("Total: 0.00 lei")

# INPUT
frame_nome = tk.Frame(root)
frame_quantita = tk.Frame(root)
frame_prezzo = tk.Frame(root)
frame_barcode = tk.Frame(root)
frame_nome.pack_forget()
frame_quantita.pack_forget()
frame_prezzo.pack_forget()
frame_barcode.pack(pady=10)
# aggiorna_stato_bottone()

tk.Label(root, text="Coș").pack()

tree_carrello = ttk.Treeview(root, columns=("Denumire", "Cantitate", "Total","Actiuni"), show="headings")

tree_carrello.heading("Denumire", text="Denumire")
tree_carrello.heading("Cantitate", text="Cantitate")
tree_carrello.heading("Total", text="Total")
tree_carrello.heading("Actiuni", text="Actiuni")
tree_carrello.bind("<Button-1>", click_carrello)
tree_carrello.pack()
frame_carrello_btn = tk.Frame(root)
frame_carrello_btn.pack(pady=5)


tk.Label(root, textvariable=totale_var, font=("Arial", 14)).pack()
totale_var.set("Total: 0.00 lei")

tk.Label(frame_nome, text="Denumire").pack(side=tk.LEFT)
entry_nome = tk.Entry(frame_nome)
entry_nome.pack(side=tk.LEFT)

tk.Label(frame_quantita, text="Cantitate").pack(side=tk.LEFT)
entry_quantita = tk.Entry(frame_quantita)
entry_quantita.pack(side=tk.LEFT)

tk.Label(frame_prezzo, text="Preț").pack(side=tk.LEFT)
entry_prezzo = tk.Entry(frame_prezzo)
entry_prezzo.pack(side=tk.LEFT)

tk.Label(frame_barcode, text="Barcode").pack(side=tk.LEFT)
entry_barcode = tk.Entry(frame_barcode)
entry_barcode.pack(side=tk.LEFT)

# BOTTONI
frame_bottoni = tk.Frame(root)
frame_bottoni.pack(pady=10)

tk.Button(frame_bottoni, text="Eliberează Bonul", width=18, command=chiudi_scontrino)\
    .grid(row=0, column=0, padx=5, pady=5)

tk.Button(frame_bottoni, text="Exportă Excel", width=18, command=esporta_excel)\
    .grid(row=0, column=1, padx=5, pady=5)

tk.Button(frame_bottoni, text="Mișcări Istorice", width=18, command=mostra_storico)\
    .grid(row=1, column=0, padx=5, pady=5)

tk.Button(frame_bottoni, text="Dashboard", width=18, command=mostra_dashboard)\
    .grid(row=1, column=1, padx=5, pady=5)

# RICERCA
frame_ricerca = tk.Frame(root)
frame_ricerca.pack(pady=5)

tk.Label(frame_ricerca, text="Caută").pack(side=tk.LEFT)
entry_ricerca = tk.Entry(frame_ricerca)
entry_ricerca.pack(side=tk.LEFT)

tk.Button(frame_ricerca, text="OK", command=cerca_prodotto).pack(side=tk.LEFT)

# TABELLA (tipo Excel)
tree = ttk.Treeview(root, columns=("ID", "Denumire", "Cantitate", "Preț","Barcode"), show="headings")
tree.tag_configure("basso", background="#ffcccc")  # rosso chiaro
tree.tag_configure("basso", background="#ffcccc")  # rosso
tree.tag_configure("medio", background="#fff2cc")  # giallo

tree.heading("ID", text="ID")
tree.heading("Denumire", text="Denumire")
tree.heading("Cantitate", text="Cantitate")
tree.heading("Preț", text="Preț")
tree.heading("Barcode", text="Barcode")

tree.pack(fill="both", expand=True)

tree.bind("<ButtonRelease-1>", seleziona_prodotto)

aggiorna_tabella()

entry_barcode.focus_set()
root.mainloop()

conn.close()