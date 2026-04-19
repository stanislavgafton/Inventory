import datetime
import tkinter as tk
import winsound
from tkinter import messagebox

import cart
import state


def aggiorna_tabella():
    for row in state.tree.get_children():
        state.tree.delete(row)

    state.cursor.execute("SELECT * FROM prodotti")
    for row in state.cursor.fetchall():
        q = row[2]

        if q < 5:
            state.tree.insert("", tk.END, values=row, tags=("basso",))
        elif q <= 20:
            state.tree.insert("", tk.END, values=row, tags=("medio",))
        else:
            state.tree.insert("", tk.END, values=row)


def seleziona_prodotto(event):
    selezionato = state.tree.focus()
    dati = state.tree.item(selezionato, "values")

    if dati:
        state.entry_nome.delete(0, tk.END)
        state.entry_nome.insert(0, dati[1])

        state.entry_quantita.delete(0, tk.END)
        state.entry_quantita.insert(0, dati[2])

        state.entry_prezzo.delete(0, tk.END)
        state.entry_prezzo.insert(0, dati[3])

        state.entry_barcode.delete(0, tk.END)
        state.entry_barcode.insert(0, dati[4])


def elimina_prodotto():
    selezionato = state.tree.focus()
    dati = state.tree.item(selezionato, "values")

    if not dati:
        return

    id_prodotto = dati[0]

    state.cursor.execute("DELETE FROM prodotti WHERE id=?", (id_prodotto,))
    state.conn.commit()
    aggiorna_tabella()


def cerca_prodotto():
    parola = state.entry_ricerca.get()

    for row in state.tree.get_children():
        state.tree.delete(row)

    state.cursor.execute(
        "SELECT * FROM prodotti WHERE nome LIKE ?",
        ('%' + parola + '%',)
    )

    for row in state.cursor.fetchall():
        q = row[2]

        if q < 5:
            state.tree.insert("", tk.END, values=row, tags=("basso",))
        elif q <= 20:
            state.tree.insert("", tk.END, values=row, tags=("medio",))
        else:
            state.tree.insert("", tk.END, values=row)


def cerca_barcode(event=None):
    codice = state.entry_barcode.get()

    state.cursor.execute("SELECT * FROM prodotti WHERE barcode = ?", (codice,))
    risultato = state.cursor.fetchone()

    if risultato:
        winsound.Beep(1000, 150)
        preview_prodotto(risultato)
    else:
        winsound.Beep(300, 300)
        risposta = messagebox.askyesno("Nou Produs", "Produs nu a fost găsit. Vreai să îl adaugi?")
        if risposta:
            popup_nuovo_prodotto(codice)

    state.entry_barcode.delete(0, tk.END)
    state.entry_barcode.focus_set()


def rimetti_focus(event=None):
    state.entry_barcode.focus_set()


def reset_focus(event=None):
    state.entry_barcode.focus_set()


def pulisci_campi():
    state.entry_nome.delete(0, tk.END)
    state.entry_quantita.delete(0, tk.END)
    state.entry_prezzo.delete(0, tk.END)
    state.entry_barcode.delete(0, tk.END)


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

        state.cursor.execute(
            "INSERT INTO prodotti (nome, quantita, prezzo, barcode) VALUES (?, ?, ?, ?)",
            (nome, int(quantita), float(prezzo), barcode)
        )
        state.conn.commit()

        aggiorna_tabella()
        popup.destroy()

    entry_nome_popup.bind("<Return>", lambda e: entry_q_popup.focus_set())
    entry_q_popup.bind("<Return>", lambda e: entry_prezzo_popup.focus_set())
    entry_prezzo_popup.bind("<Return>", salva)
    tk.Button(popup, text="OK", command=salva).pack(pady=10)
    popup.after(100, lambda: entry_nome_popup.focus_set())


def preview_prodotto(prodotto):
    state.root.unbind("<Return>")
    state.root.unbind("<KP_Enter>")
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

        state.carrello.append((idp, nome, prezzo, q))
        cart.aggiorna_carrello_ui()
        cart.aggiorna_totale()
        riattiva_barcode()

    def aggiungi_stock():
        q = qty_var.get()

        if q <= 0:
            messagebox.showwarning("Erroare", "Cantitate greșită")
            return

        state.cursor.execute(
            "UPDATE prodotti SET quantita = quantita + ? WHERE id = ?",
            (q, idp)
        )
        state.cursor.execute(
            "INSERT INTO movimenti (id_prodotto, nome, tipo, quantita, data) VALUES (?, ?, ?, ?, ?)",
            (idp, nome, "încarcare", q, str(datetime.datetime.now()))
        )
        state.conn.commit()

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

        state.cursor.execute(
            "UPDATE prodotti SET quantita = quantita - ? WHERE id = ?",
            (q, idp)
        )
        state.cursor.execute(
            "INSERT INTO movimenti (id_prodotto, nome, tipo, quantita, data) VALUES (?, ?, ?, ?, ?)",
            (idp, nome, "descărcare", q, str(datetime.datetime.now()))
        )
        state.conn.commit()

        aggiorna_tabella()

        messagebox.showinfo("OK", f"Eliminate {q} {nome}")

        riattiva_barcode()

    tk.Button(popup, text="Adaugă în coș", command=aggiungi_carrello).pack(pady=20)
    tk.Button(popup, text="Adaugă în inventar", command=aggiungi_stock).pack(pady=5)
    tk.Button(popup, text="Elimină în inventar", command=rimuovi_stock).pack(pady=5)

    def riattiva_barcode():
        state.root.bind("<Return>", cerca_barcode)
        state.root.bind("<KP_Enter>", cerca_barcode)
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", riattiva_barcode)
    popup.after(100, lambda: entry_qty.focus_set())
