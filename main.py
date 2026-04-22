import tkinter as tk

import ttkbootstrap as ttkb

import db
import state
from cart import aggiorna_carrello_ui
from dashboard import mostra_dashboard
from export import esporta_excel
from history import mostra_storico
from import_products import importa_excel
from products import cerca_barcode
from sales import chiudi_scontrino
from stock import mostra_stock

state.conn = db.conn
state.cursor = db.cursor

CANVAS_BG = "#e9ecef"  # grey canvas so light-colored panels visually float

root = ttkb.Window(themename="cosmo")
root.title("MAGAZIN")
root.geometry("1400x860")
root.state("zoomed")
root.configure(bg=CANVAS_BG)
root.style.configure("TFrame", background=CANVAS_BG)
root.style.configure("TLabel", background=CANVAS_BG)
root.bind("<Return>", cerca_barcode)
root.bind("<KP_Enter>", cerca_barcode)

state.root = root
state.carrello = []
state.totale_var = tk.StringVar()
state.totale_var.set("Total: 0.00 lei")
state.tree = None
state.entry_ricerca = None

# Hidden entries kept so popup_nuovo_prodotto / edit flows can still read/write them
_hidden = ttkb.Frame(root)
entry_nome = ttkb.Entry(_hidden)
entry_quantita = ttkb.Entry(_hidden)
entry_prezzo = ttkb.Entry(_hidden)
state.entry_nome = entry_nome
state.entry_quantita = entry_quantita
state.entry_prezzo = entry_prezzo


def _card(parent, padding=16):
    """Panel with a visible accent-colored border."""
    border = tk.Frame(parent, bg="#9954bb")
    inner = ttkb.Frame(border, padding=padding, bootstyle="light")
    inner.pack(padx=2, pady=2, fill="both", expand=True)
    border.inner = inner
    return border


# ---------------- Header ----------------
header = ttkb.Frame(root, padding=(24, 18, 24, 6))
header.pack(fill="x")
ttkb.Label(header, text="MAGAZIN",
           font=("Segoe UI", 22, "bold"),
           background=CANVAS_BG,
           foreground=root.style.colors.info).pack(anchor="center")

# ---------------- Barcode card ----------------
bc_card = _card(root)
bc_card.pack(fill="x", padx=24, pady=(4, 12))

ttkb.Label(bc_card.inner, text="Scanează",
           font=("Segoe UI", 10, "bold"),
           background=root.style.colors.light,
           foreground="#495057").pack(anchor="center")
_violet = "#9954bb"
root.style.configure("Violet.TEntry",
                     bordercolor=_violet, lightcolor=_violet,
                     darkcolor=_violet, insertcolor=_violet,
                     fieldbackground="white")
root.style.map("Violet.TEntry",
               bordercolor=[("focus", _violet), ("!focus", _violet)],
               lightcolor=[("focus", _violet), ("!focus", _violet)],
               darkcolor=[("focus", _violet), ("!focus", _violet)])
entry_barcode = ttkb.Entry(bc_card.inner,
                           font=("Segoe UI", 16),
                           style="Violet.TEntry")
entry_barcode.pack(fill="x", pady=(4, 0), ipady=4)
state.entry_barcode = entry_barcode

# ---------------- Body: cart (left) + sidebar (right) ----------------
body = ttkb.Frame(root, padding=(24, 0, 24, 16))
body.pack(fill="both", expand=True)

# ---- Cart column ----
cart_col = ttkb.Frame(body)
cart_col.pack(side="left", fill="both", expand=True, padx=(0, 16))

ttkb.Label(cart_col, text="Coș",
           font=("Segoe UI", 14, "bold"),
           background=CANVAS_BG,
           foreground=root.style.colors.info).pack(anchor="center", pady=(0, 6))

cart_wrap_border = _card(cart_col, padding=8)
cart_wrap_border.pack(fill="both", expand=True)
cart_wrap = cart_wrap_border.inner
state.cart_wrap = cart_wrap

cart_canvas = tk.Canvas(cart_wrap, highlightthickness=0,
                        bg=root.style.colors.light)
cart_scrollbar = ttkb.Scrollbar(cart_wrap, orient="vertical",
                                command=cart_canvas.yview, bootstyle="round")
cart_canvas.configure(yscrollcommand=cart_scrollbar.set)

cart_scrollbar.pack(side="right", fill="y")
cart_canvas.pack(side="left", fill="both", expand=True)

cart_frame = ttkb.Frame(cart_canvas, bootstyle="light")
cart_window = cart_canvas.create_window((0, 0), window=cart_frame, anchor="nw")


def _on_cart_configure(_e=None):
    cart_canvas.configure(scrollregion=cart_canvas.bbox("all"))


def _on_canvas_configure(event):
    cart_canvas.itemconfigure(cart_window, width=event.width)


cart_frame.bind("<Configure>", _on_cart_configure)
cart_canvas.bind("<Configure>", _on_canvas_configure)


def _on_mousewheel(event):
    cart_canvas.yview_scroll(int(-event.delta / 120), "units")


cart_canvas.bind("<Enter>", lambda e: cart_canvas.bind_all("<MouseWheel>", _on_mousewheel))
cart_canvas.bind("<Leave>", lambda e: cart_canvas.unbind_all("<MouseWheel>"))

state.cart_frame = cart_frame

# ---- Sidebar column ----
side_col = ttkb.Frame(body, width=340)
side_col.pack(side="right", fill="y")
side_col.pack_propagate(False)

# Phone-only scroll pieces — built now, packed only in phone mode.
side_scroll_canvas = tk.Canvas(side_col, highlightthickness=0, bg=CANVAS_BG)
side_scroll_vsb = ttkb.Scrollbar(side_col, orient="vertical",
                                 command=side_scroll_canvas.yview,
                                 bootstyle="round")
side_scroll_canvas.configure(yscrollcommand=side_scroll_vsb.set)
side_scroll_inner = ttkb.Frame(side_scroll_canvas)
side_scroll_window = side_scroll_canvas.create_window(
    (0, 0), window=side_scroll_inner, anchor="nw")

side_scroll_inner.bind(
    "<Configure>",
    lambda _e: side_scroll_canvas.configure(scrollregion=side_scroll_canvas.bbox("all")))
side_scroll_canvas.bind(
    "<Configure>",
    lambda e: side_scroll_canvas.itemconfigure(side_scroll_window, width=e.width))


def _side_wheel(event):
    side_scroll_canvas.yview_scroll(int(-event.delta / 120), "units")


side_scroll_canvas.bind(
    "<Enter>", lambda e: side_scroll_canvas.bind_all("<MouseWheel>", _side_wheel))
side_scroll_canvas.bind(
    "<Leave>", lambda e: side_scroll_canvas.unbind_all("<MouseWheel>"))

# Total card
total_card = _card(side_col, padding=18)
total_card.pack(fill="x", pady=(0, 12))
ttkb.Label(total_card.inner, textvariable=state.totale_var,
           font=("Segoe UI", 22, "bold"),
           background=root.style.colors.light,
           foreground=root.style.colors.info).pack(anchor="center", pady=(0, 12))
ttkb.Button(total_card.inner, text="Eliberează Bonul", command=chiudi_scontrino,
            bootstyle="info", padding=12).pack(fill="x")

# Tools card
tools_card = _card(side_col, padding=16)
tools_card.pack(fill="x")
ttkb.Label(tools_card.inner, text="Instrumente",
           font=("Segoe UI", 10, "bold"),
           background=root.style.colors.light,
           foreground="#495057").pack(anchor="center", pady=(0, 8))

tool_buttons = [
    ("Stock",           mostra_stock,     "info-outline"),
    ("Dashboard",       mostra_dashboard, "info-outline"),
    ("Mișcări Istorice", mostra_storico,  "info-outline"),
    ("Importă Excel",   importa_excel,    "info-outline"),
    ("Exportă Excel",   esporta_excel,    "info-outline"),
]
for text, cmd, style in tool_buttons:
    ttkb.Button(tools_card.inner, text=text, command=cmd,
                bootstyle=style, padding=10).pack(fill="x", pady=4)

NARROW = 820
PHONE = 520
_last_mode = [None]


def _mount_cards_direct():
    side_scroll_canvas.pack_forget()
    side_scroll_vsb.pack_forget()
    total_card.pack_forget()
    tools_card.pack_forget()
    total_card.pack(in_=side_col, fill="x", pady=(0, 12))
    tools_card.pack(in_=side_col, fill="x")


def _mount_cards_scroll():
    total_card.pack_forget()
    tools_card.pack_forget()
    side_scroll_vsb.pack(side="right", fill="y")
    side_scroll_canvas.pack(side="left", fill="both", expand=True)
    total_card.pack(in_=side_scroll_inner, fill="x", pady=(0, 12))
    tools_card.pack(in_=side_scroll_inner, fill="x")


def _reflow(event):
    if event.widget is not root:
        return
    w = root.winfo_width()
    if w < PHONE:
        mode = "phone"
    elif w < NARROW:
        mode = "tablet"
    else:
        mode = "desktop"
    if mode == _last_mode[0]:
        return
    _last_mode[0] = mode

    cart_col.pack_forget()
    side_col.pack_forget()

    if mode == "desktop":
        _mount_cards_direct()
        side_col.pack_propagate(False)
        side_col.configure(width=340)
        cart_col.pack(side="left", fill="both", expand=True, padx=(0, 16))
        side_col.pack(side="right", fill="y")
    elif mode == "tablet":
        _mount_cards_direct()
        side_col.configure(width=0)
        side_col.pack_propagate(True)
        cart_col.pack(side="top", fill="both", expand=True, pady=(0, 12))
        side_col.pack(side="top", fill="x")
    else:  # phone
        _mount_cards_scroll()
        side_col.configure(width=0)
        side_col.pack_propagate(True)
        cart_col.pack(side="top", fill="both", expand=True, pady=(0, 12))
        side_col.pack(side="top", fill="both", expand=True)


root.bind("<Configure>", _reflow)

aggiorna_carrello_ui()
entry_barcode.focus_set()
root.mainloop()

db.conn.close()
