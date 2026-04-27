import datetime
import os
import sys
import tkinter as tk
import winsound
from tkinter import messagebox, simpledialog

import ttkbootstrap as ttkb

import cart
import state
from units import (
    UNIT_BUC,
    UNIT_G,
    UNITS,
    format_qty,
    format_unit_price,
    normalize_unit,
    price_label,
    qty_label,
    qty_step,
    stock_thresholds,
)

def _resource_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


_BEEP_OK = _resource_path("beep_ok.wav")
_BEEP_ERR = _resource_path("beep_err.wav")


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


def _row_display(row):
    idp, nome, q, prezzo, bc, unit = row
    unit = normalize_unit(unit)
    return (idp, nome, format_qty(q, unit), format_unit_price(prezzo, unit), bc or "")


def _stock_tag(q, unit):
    low, med = stock_thresholds(unit)
    if q < low:
        return "basso"
    if q <= med:
        return "medio"
    return ""


def _fill_tree(rows):
    for row in rows:
        unit = normalize_unit(row[5])
        tag = _stock_tag(row[2], unit)
        values = _row_display(row)
        if tag:
            state.tree.insert("", tk.END, values=values, tags=(tag,))
        else:
            state.tree.insert("", tk.END, values=values)


def aggiorna_tabella():
    if not _tree_alive():
        return

    for row in state.tree.get_children():
        state.tree.delete(row)

    state.cursor.execute(
        "SELECT id, nome, quantita, prezzo, barcode, unit FROM prodotti"
    )
    _fill_tree(state.cursor.fetchall())


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
    nome = dati[1]

    stock_win = state.tree.winfo_toplevel()

    if not messagebox.askyesno(
        "Confirmare",
        f"Ești sigur că vrei să elimini \"{nome}\"?",
        parent=stock_win
    ):
        stock_win.lift()
        stock_win.focus_force()
        return

    if not messagebox.askyesno(
        "Confirmare finală",
        f"Această acțiune nu poate fi anulată.\nȘtergi definitiv \"{nome}\"?",
        icon="warning",
        parent=stock_win
    ):
        stock_win.lift()
        stock_win.focus_force()
        return

    state.cursor.execute("DELETE FROM prodotti WHERE id=?", (id_prodotto,))
    state.conn.commit()
    aggiorna_tabella()
    messagebox.showinfo("OK", f"Produs \"{nome}\" eliminat", parent=stock_win)
    stock_win.lift()
    stock_win.focus_force()


def cerca_prodotto():
    if not _tree_alive() or getattr(state, "entry_ricerca", None) is None:
        return

    parola = state.entry_ricerca.get()

    for row in state.tree.get_children():
        state.tree.delete(row)

    state.cursor.execute(
        "SELECT id, nome, quantita, prezzo, barcode, unit FROM prodotti WHERE nome LIKE ?",
        ('%' + parola + '%',)
    )
    _fill_tree(state.cursor.fetchall())


def _prompt_grams(parent, nome):
    return simpledialog.askinteger(
        "Cantitate (g)",
        f"Câte grame pentru \"{nome}\"?",
        parent=parent,
        minvalue=1,
    )


def cerca_barcode(event=None):
    codice = state.entry_barcode.get()

    state.cursor.execute(
        "SELECT id, nome, quantita, prezzo, barcode, unit FROM prodotti WHERE barcode = ?",
        (codice,),
    )
    risultato = state.cursor.fetchone()

    if not risultato:
        _play(_BEEP_ERR)
        messagebox.showwarning("Produs inexistent", "Barcode necunoscut")
        state.entry_barcode.delete(0, tk.END)
        state.entry_barcode.focus_set()
        return

    idp, nome, quantita, prezzo, _bc, unit = risultato
    unit = normalize_unit(unit)

    if unit == UNIT_G:
        grams = _prompt_grams(state.root, nome)
        if not grams:
            state.entry_barcode.delete(0, tk.END)
            state.entry_barcode.focus_set()
            return
        add_qty = int(grams)
    else:
        add_qty = 1

    for i, item in enumerate(state.carrello):
        ex_idp, ex_nome, ex_prezzo, ex_q, ex_unit = item
        if ex_idp == idp:
            new_q = ex_q + add_qty
            if new_q > quantita:
                _play(_BEEP_ERR)
                messagebox.showwarning(
                    "Stock insuficient",
                    f"Disponibil doar {format_qty(quantita, unit)}",
                )
            else:
                state.carrello[i] = (ex_idp, ex_nome, ex_prezzo, new_q, ex_unit)
                _play(_BEEP_OK)
                cart.aggiorna_carrello_ui()
                cart.aggiorna_totale()
            state.entry_barcode.delete(0, tk.END)
            state.entry_barcode.focus_set()
            return

    if quantita <= 0 or add_qty > quantita:
        _play(_BEEP_ERR)
        messagebox.showwarning(
            "Stock insuficient",
            f"Disponibil doar {format_qty(quantita, unit)}",
        )
    else:
        state.carrello.append((idp, nome, prezzo, add_qty, unit))
        _play(_BEEP_OK)
        cart.aggiorna_carrello_ui()
        cart.aggiorna_totale()

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
    popup.geometry("380x500")

    wrap = ttkb.Frame(popup, padding=20)
    wrap.pack(fill="both", expand=True)

    ttkb.Label(wrap, text="Produs Nou", font=("Segoe UI", 14, "bold")).pack(pady=(0, 12))

    ttkb.Label(wrap, text="Denumire").pack(anchor="w")
    entry_nome_popup = ttkb.Entry(wrap)
    entry_nome_popup.pack(fill="x", pady=(2, 8))

    ttkb.Label(wrap, text="Unitate de măsură").pack(anchor="w")
    unit_var = tk.StringVar(value=UNIT_BUC)
    combo_unit = ttkb.Combobox(wrap, textvariable=unit_var,
                               values=[UNIT_BUC, UNIT_G, "kg"], state="readonly")
    combo_unit.pack(fill="x", pady=(2, 8))

    def _qty_label_for(choice):
        if choice == "kg":
            return "Cantitate (kg)"
        return qty_label(normalize_unit(choice))

    lbl_q = ttkb.Label(wrap, text=_qty_label_for(UNIT_BUC))
    lbl_q.pack(anchor="w")
    entry_q_popup = ttkb.Entry(wrap)
    entry_q_popup.pack(fill="x", pady=(2, 8))

    lbl_p = ttkb.Label(wrap, text=price_label(UNIT_BUC))
    lbl_p.pack(anchor="w")
    entry_prezzo_popup = ttkb.Entry(wrap)
    entry_prezzo_popup.pack(fill="x", pady=(2, 8))

    def _on_unit_change(*_):
        choice = unit_var.get()
        lbl_q.configure(text=_qty_label_for(choice))
        lbl_p.configure(text=price_label(normalize_unit(choice)))

    unit_var.trace_add("write", _on_unit_change)

    def salva(event=None):
        nome = entry_nome_popup.get().strip()
        quantita = entry_q_popup.get().strip()
        prezzo = entry_prezzo_popup.get().strip()
        choice = unit_var.get()
        unit = normalize_unit(choice)

        if not nome or not quantita or not prezzo:
            messagebox.showwarning("Erroare", "Completează toate datele!", parent=popup)
            return

        try:
            q_val = float(quantita)
            if choice == "kg":
                q_int = int(round(q_val * 1000))
            else:
                q_int = int(q_val)
            prezzo_f = float(prezzo)
        except ValueError:
            messagebox.showwarning("Erroare", "Cantitate sau preț invalid", parent=popup)
            return

        state.cursor.execute(
            "INSERT INTO prodotti (nome, quantita, prezzo, barcode, unit) VALUES (?, ?, ?, ?, ?)",
            (nome, q_int, prezzo_f, barcode, unit),
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


def cerca_barcode_stock(event=None):
    entry = getattr(state, "entry_barcode_stock", None)
    if entry is None:
        return

    codice = entry.get()

    state.cursor.execute(
        "SELECT id, nome, quantita, prezzo, barcode, unit FROM prodotti WHERE barcode = ?",
        (codice,),
    )
    risultato = state.cursor.fetchone()

    if risultato:
        _play(_BEEP_OK)
        preview_stock_prodotto(risultato)
    else:
        _play(_BEEP_ERR)
        risposta = messagebox.askyesno("Nou Produs", "Produs nu a fost găsit. Vreai să îl adaugi?")
        if risposta:
            popup_nuovo_prodotto(codice)

    entry.delete(0, tk.END)
    entry.focus_set()


def preview_stock_prodotto(prodotto):
    popup = ttkb.Toplevel()
    popup.title("Stock produs")
    popup.geometry("480x440")

    idp, nome, quantita, prezzo, barcode, unit = prodotto
    unit = normalize_unit(unit)
    step = qty_step(unit)

    wrap = ttkb.Frame(popup, padding=20)
    wrap.pack(fill="both", expand=True)

    ttkb.Label(wrap, text=nome, font=("Segoe UI", 16, "bold")).pack(pady=(0, 8))
    ttkb.Label(wrap, text=f"Disponibil: {format_qty(quantita, unit)}",
               font=("Segoe UI", 11)).pack()
    ttkb.Label(wrap, text=f"Preț: {format_unit_price(prezzo, unit)}",
               font=("Segoe UI", 11)).pack(pady=(0, 12))

    qty_var = tk.IntVar(value=step)

    ttkb.Label(wrap, text=qty_label(unit),
               font=("Segoe UI", 9)).pack(anchor="center")

    frame_qty = ttkb.Frame(wrap)
    frame_qty.pack(pady=6)

    def meno():
        v = qty_var.get() - step
        if v >= step:
            qty_var.set(v)

    def piu():
        qty_var.set(qty_var.get() + step)

    ttkb.Button(frame_qty, text="−", width=3, command=meno,
                bootstyle="secondary").pack(side=tk.LEFT, padx=4)

    entry_qty = ttkb.Entry(frame_qty, textvariable=qty_var, width=8, justify="center",
                           font=("Segoe UI", 12, "bold"))
    entry_qty.pack(side=tk.LEFT, padx=4)

    ttkb.Button(frame_qty, text="+", width=3, command=piu,
                bootstyle="secondary").pack(side=tk.LEFT, padx=4)

    def chiudi():
        popup.destroy()
        entry = getattr(state, "entry_barcode_stock", None)
        if entry is not None:
            try:
                entry.focus_set()
            except Exception:
                pass

    def _read_qty():
        try:
            return int(qty_var.get())
        except Exception:
            return 0

    def aggiungi_stock():
        q = _read_qty()

        if q <= 0:
            messagebox.showwarning("Erroare", "Cantitate greșită", parent=popup)
            return

        state.cursor.execute(
            "UPDATE prodotti SET quantita = quantita + ? WHERE id = ?",
            (q, idp)
        )
        state.cursor.execute(
            "INSERT INTO movimenti (id_prodotto, nome, tipo, quantita, data, unit) VALUES (?, ?, ?, ?, ?, ?)",
            (idp, nome, "încarcare", q, str(datetime.datetime.now()), unit)
        )
        state.conn.commit()

        aggiorna_tabella()
        messagebox.showinfo("OK", f"Adăugate {format_qty(q, unit)} la {nome}", parent=popup)
        chiudi()

    def rimuovi_stock():
        q = _read_qty()

        if q <= 0:
            messagebox.showwarning("Erroare", "Cantitate greșită", parent=popup)
            return

        if q > quantita:
            messagebox.showwarning("Erroare", f"Disponibil doar {format_qty(quantita, unit)}", parent=popup)
            return

        state.cursor.execute(
            "UPDATE prodotti SET quantita = quantita - ? WHERE id = ?",
            (q, idp)
        )
        state.cursor.execute(
            "INSERT INTO movimenti (id_prodotto, nome, tipo, quantita, data, unit) VALUES (?, ?, ?, ?, ?, ?)",
            (idp, nome, "descărcare", q, str(datetime.datetime.now()), unit)
        )
        state.conn.commit()

        aggiorna_tabella()
        messagebox.showinfo("OK", f"Eliminate {format_qty(q, unit)} din {nome}", parent=popup)
        chiudi()

    ttkb.Button(wrap, text="Adaugă în stoc", command=aggiungi_stock,
                bootstyle="info", padding=8).pack(pady=(16, 6), fill="x")
    ttkb.Button(wrap, text="Elimină din stoc", command=rimuovi_stock,
                bootstyle="danger", padding=8).pack(pady=4, fill="x")

    popup.protocol("WM_DELETE_WINDOW", chiudi)
    popup.after(100, lambda: entry_qty.focus_set())
