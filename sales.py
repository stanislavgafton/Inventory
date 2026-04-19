import datetime
from tkinter import messagebox

import cart
import products
import state


def chiudi_scontrino():
    if not state.carrello:
        messagebox.showwarning("Atenție", "Coșul e gol")
        return
    totale = 0

    for item in state.carrello:
        idp, nome, prezzo, q = item
        totale += prezzo * q

        state.cursor.execute(
            "UPDATE prodotti SET quantita = quantita - ? WHERE id = ?",
            (q, idp)
        )

        state.cursor.execute(
            "INSERT INTO vendite (totale, data) VALUES (?, ?)",
            (totale, str(datetime.datetime.now()))
        )
        state.cursor.execute(
            "INSERT INTO movimenti (id_prodotto, nome, tipo, quantita, data) VALUES (?, ?, ?, ?, ?)",
            (idp, nome, "vanzare", q, str(datetime.datetime.now()))
        )
        state.conn.commit()

    state.carrello.clear()
    products.aggiorna_tabella()
    cart.aggiorna_carrello_ui()
    cart.aggiorna_totale()

    messagebox.showinfo("OK", f"Total: {totale:.2f} lei")
