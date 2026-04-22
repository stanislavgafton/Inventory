import datetime
import os
import tkinter as tk
import winsound
from tkinter import messagebox

import ttkbootstrap as ttkb

import cart
import state

_HERE = os.path.dirname(os.path.abspath(__file__))
_BEEP_OK = os.path.join(_HERE, "beep_ok.wav")
_BEEP_ERR = os.path.join(_HERE, "beep_err.wav")


def _play(path):
    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)


def _tree_alive():
    tree = getattr(state, "tree", None)
    if tree is None:
        return False
    try:
        return bool(tree.winfo_exists())
    except Exception:
        return False


def aggiorna_tabella():
    if not _tree_alive():
        return

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
    if not _tree_alive():
        return

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
    if not _tree_alive():
        return

    selezionato = state.tree.focus()
    dati = state.tree.item(selezionato, "values")

    if not dati:
        return

    id_prodotto = dati[0]

    state.cursor.execute("DELETE FROM prodotti WHERE id=?", (id_prodotto,))
    state.conn.commit()
    aggiorna_tabella()


def cerca_prodotto():
    if not _tree_alive() or getattr(state, "entry_ricerca", None) is None:
        return

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
        idp, nome, quantita, prezzo, _barcode = risultato

        for i, (ex_idp, ex_nome, ex_prezzo, ex_q) in enumerate(state.carrello):
            if ex_idp == idp:
                new_q = ex_q + 1
                if new_q > quantita:
                    _play(_BEEP_ERR)
                    messagebox.showwarning("Stock insuficient",
                                           f"Disponibil doar {quantita}")
                else:
                    state.carrello[i] = (ex_idp, ex_nome, ex_prezzo, new_q)
                    _play(_BEEP_OK)
                    cart.aggiorna_carrello_ui()
                    cart.aggiorna_totale()
                state.entry_barcode.delete(0, tk.END)
                state.entry_barcode.focus_set()
                return

        _play(_BEEP_OK)
        preview_prodotto(risultato)
    else:
        _play(_BEEP_ERR)
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
    popup = ttkb.Toplevel()
    popup.title("Produs Nou")
    popup.geometry("360x320")

    wrap = ttkb.Frame(popup, padding=20)
    wrap.pack(fill="both", expand=True)

    ttkb.Label(wrap, text="Produs Nou", font=("Segoe UI", 14, "bold")).pack(pady=(0, 12))

    ttkb.Label(wrap, text="Denumire").pack(anchor="w")
    entry_nome_popup = ttkb.Entry(wrap)
    entry_nome_popup.pack(fill="x", pady=(2, 8))

    ttkb.Label(wrap, text="Cantitate").pack(anchor="w")
    entry_q_popup = ttkb.Entry(wrap)
    entry_q_popup.pack(fill="x", pady=(2, 8))

    ttkb.Label(wrap, text="Preț").pack(anchor="w")
    entry_prezzo_popup = ttkb.Entry(wrap)
    entry_prezzo_popup.pack(fill="x", pady=(2, 8))

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
    ttkb.Button(wrap, text="Salvează", command=salva, bootstyle="info",
                padding=8).pack(pady=14, fill="x")
    popup.after(100, lambda: entry_nome_popup.focus_set())


def preview_prodotto(prodotto):
    state.root.unbind("<Return>")
    state.root.unbind("<KP_Enter>")
    popup = ttkb.Toplevel()
    popup.title("Produs")
    popup.geometry("480x440")

    idp, nome, quantita, prezzo, barcode = prodotto

    wrap = ttkb.Frame(popup, padding=20)
    wrap.pack(fill="both", expand=True)

    ttkb.Label(wrap, text=nome, font=("Segoe UI", 16, "bold")).pack(pady=(0, 8))
    ttkb.Label(wrap, text=f"Disponibil: {quantita}",
               font=("Segoe UI", 11)).pack()
    ttkb.Label(wrap, text=f"Preț: {prezzo} lei",
               font=("Segoe UI", 11)).pack(pady=(0, 12))

    qty_var = tk.IntVar(value=1)

    frame_qty = ttkb.Frame(wrap)
    frame_qty.pack(pady=10)

    def meno():
        if qty_var.get() > 1:
            qty_var.set(qty_var.get() - 1)

    def piu():
        qty_var.set(qty_var.get() + 1)

    ttkb.Button(frame_qty, text="−", width=3, command=meno,
                bootstyle="secondary").pack(side=tk.LEFT, padx=4)

    entry_qty = ttkb.Entry(frame_qty, textvariable=qty_var, width=6, justify="center",
                           font=("Segoe UI", 12, "bold"))
    entry_qty.pack(side=tk.LEFT, padx=4)

    ttkb.Button(frame_qty, text="+", width=3, command=piu,
                bootstyle="secondary").pack(side=tk.LEFT, padx=4)

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

    ttkb.Button(wrap, text="Adaugă în coș", command=aggiungi_carrello,
                bootstyle="info", padding=8).pack(pady=(16, 6), fill="x")
    ttkb.Button(wrap, text="Adaugă în inventar", command=aggiungi_stock,
                bootstyle="secondary", padding=8).pack(pady=4, fill="x")
    ttkb.Button(wrap, text="Elimină în inventar", command=rimuovi_stock,
                bootstyle="danger", padding=8).pack(pady=4, fill="x")

    def riattiva_barcode():
        state.root.bind("<Return>", cerca_barcode)
        state.root.bind("<KP_Enter>", cerca_barcode)
        popup.destroy()

    popup.protocol("WM_DELETE_WINDOW", riattiva_barcode)
    popup.after(100, lambda: entry_qty.focus_set())
