import tkinter as tk

import ttkbootstrap as ttkb
from ttkbootstrap.constants import LEFT, X

import db
import state
from cart import aggiorna_carrello_ui
from dashboard import mostra_dashboard
from export import esporta_excel
from history import mostra_storico
from import_products import importa_excel
from products import aggiorna_tabella, cerca_barcode, cerca_prodotto, seleziona_prodotto
from sales import chiudi_scontrino

state.conn = db.conn
state.cursor = db.cursor

root = ttkb.Window(themename="cosmo")
root.title("GASTA")
root.geometry("1600x900")
root.state("zoomed")
root.bind("<Return>", cerca_barcode)
root.bind("<KP_Enter>", cerca_barcode)

state.root = root
state.carrello = []
state.totale_var = tk.StringVar()
state.totale_var.set("Total: 0.00 lei")

# Hidden frames kept for compatibility with code that writes to entry_nome/quantita/prezzo
frame_nome = ttkb.Frame(root)
frame_quantita = ttkb.Frame(root)
frame_prezzo = ttkb.Frame(root)

# Barcode input — top of window
frame_barcode = ttkb.Frame(root, padding=12)
frame_barcode.pack(pady=(10, 4))

ttkb.Label(frame_barcode, text="Barcode", font=("Segoe UI", 11, "bold")).pack(side=LEFT, padx=(0, 8))
entry_barcode = ttkb.Entry(frame_barcode, width=30, font=("Segoe UI", 11))
entry_barcode.pack(side=LEFT)
state.entry_barcode = entry_barcode

# Cart section — scrollable list of cards
ttkb.Label(root, text="Coș", font=("Segoe UI", 13, "bold")).pack(pady=(10, 4))

frame_cart_outer = ttkb.Frame(root, padding=(16, 0))
frame_cart_outer.pack(fill=X)

cart_canvas = tk.Canvas(frame_cart_outer, height=260, highlightthickness=0,
                        bg=root.style.colors.bg)
cart_scrollbar = ttkb.Scrollbar(frame_cart_outer, orient="vertical",
                                command=cart_canvas.yview, bootstyle="round")
cart_canvas.configure(yscrollcommand=cart_scrollbar.set)

cart_scrollbar.pack(side="right", fill="y")
cart_canvas.pack(side="left", fill="both", expand=True)

cart_frame = ttkb.Frame(cart_canvas)
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

ttkb.Label(root, textvariable=state.totale_var,
           font=("Segoe UI", 18, "bold")).pack(pady=8)
state.totale_var.set("Total: 0.00 lei")

# Primary action — directly under the cart
frame_bon = ttkb.Frame(root, padding=(10, 0))
frame_bon.pack(pady=(0, 6))
ttkb.Button(frame_bon, text="Eliberează Bonul", command=chiudi_scontrino,
            bootstyle="primary", width=28, padding=10).pack()

# Hidden entries (preserved from original — some code paths touch them)
ttkb.Label(frame_nome, text="Denumire").pack(side=LEFT)
entry_nome = ttkb.Entry(frame_nome)
entry_nome.pack(side=LEFT)
state.entry_nome = entry_nome

ttkb.Label(frame_quantita, text="Cantitate").pack(side=LEFT)
entry_quantita = ttkb.Entry(frame_quantita)
entry_quantita.pack(side=LEFT)
state.entry_quantita = entry_quantita

ttkb.Label(frame_prezzo, text="Preț").pack(side=LEFT)
entry_prezzo = ttkb.Entry(frame_prezzo)
entry_prezzo.pack(side=LEFT)
state.entry_prezzo = entry_prezzo

# Action buttons
frame_bottoni = ttkb.Frame(root, padding=10)
frame_bottoni.pack(pady=10)

btn_opts = dict(width=20, padding=8)

ttkb.Button(frame_bottoni, text="Exportă Excel", command=esporta_excel,
            bootstyle="secondary", **btn_opts).grid(row=0, column=0, padx=6, pady=6)
ttkb.Button(frame_bottoni, text="Importă Excel", command=importa_excel,
            bootstyle="secondary", **btn_opts).grid(row=0, column=1, padx=6, pady=6)
ttkb.Button(frame_bottoni, text="Mișcări Istorice", command=mostra_storico,
            bootstyle="secondary", **btn_opts).grid(row=1, column=0, padx=6, pady=6)
ttkb.Button(frame_bottoni, text="Dashboard", command=mostra_dashboard,
            bootstyle="secondary", **btn_opts).grid(row=1, column=1, padx=6, pady=6)

# Search bar
frame_ricerca = ttkb.Frame(root, padding=(10, 4))
frame_ricerca.pack(pady=6)

ttkb.Label(frame_ricerca, text="Caută", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 8))
entry_ricerca = ttkb.Entry(frame_ricerca, width=40)
entry_ricerca.pack(side=LEFT, padx=(0, 8))
state.entry_ricerca = entry_ricerca
ttkb.Button(frame_ricerca, text="OK", command=cerca_prodotto, bootstyle="primary",
            width=8).pack(side=LEFT)

# Product table
frame_tree = ttkb.Frame(root, padding=(16, 6))
frame_tree.pack(fill="both", expand=True)

tree = ttkb.Treeview(frame_tree, columns=("ID", "Denumire", "Cantitate", "Preț", "Barcode"),
                     show="headings", bootstyle="primary")
tree.tag_configure("basso", background="#fdecea", foreground="#b02a37")
tree.tag_configure("medio", background="#fff4d6", foreground="#8a6d1a")

tree.heading("ID", text="ID")
tree.heading("Denumire", text="Denumire")
tree.heading("Cantitate", text="Cantitate")
tree.heading("Preț", text="Preț")
tree.heading("Barcode", text="Barcode")

tree.column("ID", width=60, anchor="center")
tree.column("Cantitate", anchor="center", width=110)
tree.column("Preț", anchor="e", width=110)
tree.column("Barcode", anchor="center", width=180)

tree.pack(fill="both", expand=True)
tree.bind("<ButtonRelease-1>", seleziona_prodotto)
state.tree = tree

aggiorna_tabella()
aggiorna_carrello_ui()

entry_barcode.focus_set()
root.mainloop()

db.conn.close()
