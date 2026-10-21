import sqlite3
from tkinter import messagebox

import cart
import products
import state
from checkout import record_sale


def chiudi_scontrino():
    if not state.carrello:
        messagebox.showwarning("Atenție", "Coșul e gol")
        return
    try:
        totale = record_sale(state.conn, state.carrello)
    except (ValueError, sqlite3.Error) as exc:
        messagebox.showerror("Vânzare nesalvată", str(exc))
        return

    state.carrello.clear()
    products.aggiorna_tabella()
    cart.aggiorna_carrello_ui()
    cart.aggiorna_totale()

    messagebox.showinfo("OK", f"Total: {totale:.2f} lei")
