import tkinter as tk

import state


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


def aggiungi_al_carrello(prodotto):
    idp, nome, q, prezzo = prodotto
    aggiorna_totale()


def aggiorna_totale():
    totale = sum(prezzo * q for _, _, prezzo, q in state.carrello)
    state.totale_var.set(f"Total: {totale:.2f} lei")


def aggiorna_carrello_ui():
    for row in state.tree_carrello.get_children():
        state.tree_carrello.delete(row)

    for item in state.carrello:
        idp, nome, prezzo, q = item
        totale = prezzo * q

        state.tree_carrello.insert(
            "",
            tk.END,
            values=(nome, q, f"{totale:.2f}", " +                           |                          - ")
        )


def click_carrello(event):
    item = state.tree_carrello.identify_row(event.y)
    col = state.tree_carrello.identify_column(event.x)

    if not item:
        return

    index = state.tree_carrello.index(item)

    if col == "#4":
        bbox = state.tree_carrello.bbox(item, column="#4")

        if not bbox:
            return

        x_click = event.x - bbox[0]
        width = bbox[2]

        if x_click < width / 2:
            modifica_qta(index, +1)
        else:
            modifica_qta(index, -1)


def modifica_qta(index, delta):
    idp, nome, prezzo, q = state.carrello[index]

    q += delta

    if q <= 0:
        state.carrello.pop(index)
    else:
        state.carrello[index] = (idp, nome, prezzo, q)

    aggiorna_carrello_ui()
    aggiorna_totale()


def modifica_quantita(delta):
    selezionato = state.tree_carrello.focus()
    if not selezionato:
        return

    index = state.tree_carrello.index(selezionato)

    idp, nome, prezzo, q = state.carrello[index]

    q += delta

    if q <= 0:
        state.carrello.pop(index)
    else:
        state.carrello[index] = (idp, nome, prezzo, q)

    aggiorna_carrello_ui()
    aggiorna_totale()
