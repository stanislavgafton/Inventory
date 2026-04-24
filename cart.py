import ttkbootstrap as ttkb

import state
from units import (
    format_qty,
    format_unit_price,
    line_total,
    normalize_unit,
    qty_step,
)


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
    totale = sum(line_total(prezzo, q, unit)
                 for _, _, prezzo, q, unit in state.carrello)
    state.totale_var.set(f"Total: {totale:.2f} lei")


def aggiorna_carrello_ui():
    container = state.cart_frame
    for child in container.winfo_children():
        child.destroy()

    empty = getattr(state, "cart_empty_label", None)
    if empty is not None:
        try:
            empty.destroy()
        except Exception:
            pass
        state.cart_empty_label = None

    if not state.carrello:
        overlay_parent = getattr(state, "cart_wrap", container)
        lbl = ttkb.Label(overlay_parent, text="Coșul este gol",
                         font=("Segoe UI", 14, "bold"),
                         background="#ffffff",
                         foreground="#495057")
        lbl.place(relx=0.5, rely=0.5, anchor="center")
        state.cart_empty_label = lbl
        return

    for idx, (idp, nome, prezzo, q, unit) in enumerate(state.carrello):
        _build_card(container, idx, nome, prezzo, q, unit)


def _build_card(parent, idx, nome, prezzo, q, unit):
    unit = normalize_unit(unit)
    card = ttkb.Frame(parent, padding=12)
    card.pack(fill="x", pady=3, padx=2)

    left = ttkb.Frame(card)
    left.pack(side="left", fill="x", expand=True)

    ttkb.Label(left, text=nome, font=("Segoe UI", 11, "bold")).pack(anchor="w")
    ttkb.Label(left, text=format_unit_price(prezzo, unit),
               font=("Segoe UI", 9)).pack(anchor="w")

    right = ttkb.Frame(card)
    right.pack(side="right")

    ttkb.Button(right, text="−", width=2, bootstyle="secondary",
                command=lambda: modifica_qta(idx, -qty_step(unit))).pack(side="left", padx=2)

    ttkb.Label(right, text=format_qty(q, unit), width=8, anchor="center",
               font=("Segoe UI", 12, "bold")).pack(side="left", padx=4)

    ttkb.Button(right, text="+", width=2, bootstyle="secondary",
                command=lambda: modifica_qta(idx, +qty_step(unit))).pack(side="left", padx=2)

    ttkb.Label(right, text=f"{line_total(prezzo, q, unit):.2f} lei",
               font=("Segoe UI", 11, "bold"),
               width=12, anchor="e").pack(side="left", padx=10)

    ttkb.Button(right, text="🗑", width=2, bootstyle="danger",
                command=lambda: rimuovi(idx)).pack(side="left", padx=2)

    ttkb.Separator(parent, orient="horizontal").pack(fill="x", padx=2)


def modifica_qta(index, delta):
    idp, nome, prezzo, q, unit = state.carrello[index]
    q += delta
    if q <= 0:
        state.carrello.pop(index)
    else:
        state.carrello[index] = (idp, nome, prezzo, q, unit)

    aggiorna_carrello_ui()
    aggiorna_totale()


def rimuovi(index):
    state.carrello.pop(index)
    aggiorna_carrello_ui()
    aggiorna_totale()
