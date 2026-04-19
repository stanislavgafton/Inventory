import ttkbootstrap as ttkb

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


def aggiorna_totale():
    totale = sum(prezzo * q for _, _, prezzo, q in state.carrello)
    state.totale_var.set(f"Total: {totale:.2f} lei")


def aggiorna_carrello_ui():
    container = state.cart_frame
    for child in container.winfo_children():
        child.destroy()

    if not state.carrello:
        ttkb.Label(container, text="Coșul este gol",
                   font=("Segoe UI", 11, "italic"),
                   bootstyle="secondary").pack(pady=20)
        return

    for idx, (idp, nome, prezzo, q) in enumerate(state.carrello):
        _build_card(container, idx, nome, prezzo, q)


def _build_card(parent, idx, nome, prezzo, q):
    card = ttkb.Frame(parent, padding=10, bootstyle="light")
    card.pack(fill="x", pady=4, padx=2)

    # Left: product name + unit price
    left = ttkb.Frame(card, bootstyle="light")
    left.pack(side="left", fill="x", expand=True)

    ttkb.Label(left, text=nome, font=("Segoe UI", 11, "bold"),
               bootstyle="inverse-light").pack(anchor="w")
    ttkb.Label(left, text=f"{prezzo:.2f} lei / buc",
               font=("Segoe UI", 9), bootstyle="secondary").pack(anchor="w")

    # Right: qty controls + line total + delete
    right = ttkb.Frame(card, bootstyle="light")
    right.pack(side="right")

    ttkb.Button(right, text="−", width=2, bootstyle="outline-secondary",
                command=lambda: modifica_qta(idx, -1)).pack(side="left", padx=2)

    ttkb.Label(right, text=str(q), width=3, anchor="center",
               font=("Segoe UI", 11, "bold")).pack(side="left", padx=4)

    ttkb.Button(right, text="+", width=2, bootstyle="outline-secondary",
                command=lambda: modifica_qta(idx, +1)).pack(side="left", padx=2)

    ttkb.Label(right, text=f"{prezzo * q:.2f} lei",
               font=("Segoe UI", 11, "bold"), bootstyle="success",
               width=12, anchor="e").pack(side="left", padx=10)

    ttkb.Button(right, text="🗑", width=2, bootstyle="danger-outline",
                command=lambda: rimuovi(idx)).pack(side="left", padx=2)


def modifica_qta(index, delta):
    idp, nome, prezzo, q = state.carrello[index]
    q += delta
    if q <= 0:
        state.carrello.pop(index)
    else:
        state.carrello[index] = (idp, nome, prezzo, q)

    aggiorna_carrello_ui()
    aggiorna_totale()


def rimuovi(index):
    state.carrello.pop(index)
    aggiorna_carrello_ui()
    aggiorna_totale()
