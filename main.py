import tkinter as tk
from tkinter import ttk

import db
import state
from cart import click_carrello
from dashboard import mostra_dashboard
from export import esporta_excel
from history import mostra_storico
from products import aggiorna_tabella, cerca_barcode, cerca_prodotto, seleziona_prodotto
from sales import chiudi_scontrino

state.conn = db.conn
state.cursor = db.cursor

root = tk.Tk()
root.title("GASTA")
root.geometry("1600x800")
root.bind("<Return>", cerca_barcode)
root.bind("<KP_Enter>", cerca_barcode)

state.root = root
state.carrello = []
state.totale_var = tk.StringVar()
state.totale_var.set("Total: 0.00 lei")

frame_nome = tk.Frame(root)
frame_quantita = tk.Frame(root)
frame_prezzo = tk.Frame(root)
frame_barcode = tk.Frame(root)
frame_nome.pack_forget()
frame_quantita.pack_forget()
frame_prezzo.pack_forget()
frame_barcode.pack(pady=10)

tk.Label(root, text="Coș").pack()

tree_carrello = ttk.Treeview(root, columns=("Denumire", "Cantitate", "Total", "Actiuni"), show="headings")
tree_carrello.heading("Denumire", text="Denumire")
tree_carrello.heading("Cantitate", text="Cantitate")
tree_carrello.heading("Total", text="Total")
tree_carrello.heading("Actiuni", text="Actiuni")
tree_carrello.bind("<Button-1>", click_carrello)
tree_carrello.pack()
state.tree_carrello = tree_carrello

frame_carrello_btn = tk.Frame(root)
frame_carrello_btn.pack(pady=5)

tk.Label(root, textvariable=state.totale_var, font=("Arial", 14)).pack()
state.totale_var.set("Total: 0.00 lei")

tk.Label(frame_nome, text="Denumire").pack(side=tk.LEFT)
entry_nome = tk.Entry(frame_nome)
entry_nome.pack(side=tk.LEFT)
state.entry_nome = entry_nome

tk.Label(frame_quantita, text="Cantitate").pack(side=tk.LEFT)
entry_quantita = tk.Entry(frame_quantita)
entry_quantita.pack(side=tk.LEFT)
state.entry_quantita = entry_quantita

tk.Label(frame_prezzo, text="Preț").pack(side=tk.LEFT)
entry_prezzo = tk.Entry(frame_prezzo)
entry_prezzo.pack(side=tk.LEFT)
state.entry_prezzo = entry_prezzo

tk.Label(frame_barcode, text="Barcode").pack(side=tk.LEFT)
entry_barcode = tk.Entry(frame_barcode)
entry_barcode.pack(side=tk.LEFT)
state.entry_barcode = entry_barcode

frame_bottoni = tk.Frame(root)
frame_bottoni.pack(pady=10)

tk.Button(frame_bottoni, text="Eliberează Bonul", width=18, command=chiudi_scontrino)\
    .grid(row=0, column=0, padx=5, pady=5)

tk.Button(frame_bottoni, text="Exportă Excel", width=18, command=esporta_excel)\
    .grid(row=0, column=1, padx=5, pady=5)

tk.Button(frame_bottoni, text="Mișcări Istorice", width=18, command=mostra_storico)\
    .grid(row=1, column=0, padx=5, pady=5)

tk.Button(frame_bottoni, text="Dashboard", width=18, command=mostra_dashboard)\
    .grid(row=1, column=1, padx=5, pady=5)

frame_ricerca = tk.Frame(root)
frame_ricerca.pack(pady=5)

tk.Label(frame_ricerca, text="Caută").pack(side=tk.LEFT)
entry_ricerca = tk.Entry(frame_ricerca)
entry_ricerca.pack(side=tk.LEFT)
state.entry_ricerca = entry_ricerca

tk.Button(frame_ricerca, text="OK", command=cerca_prodotto).pack(side=tk.LEFT)

tree = ttk.Treeview(root, columns=("ID", "Denumire", "Cantitate", "Preț", "Barcode"), show="headings")
tree.tag_configure("basso", background="#ffcccc")
tree.tag_configure("basso", background="#ffcccc")
tree.tag_configure("medio", background="#fff2cc")

tree.heading("ID", text="ID")
tree.heading("Denumire", text="Denumire")
tree.heading("Cantitate", text="Cantitate")
tree.heading("Preț", text="Preț")
tree.heading("Barcode", text="Barcode")

tree.pack(fill="both", expand=True)

tree.bind("<ButtonRelease-1>", seleziona_prodotto)
state.tree = tree

aggiorna_tabella()

entry_barcode.focus_set()
root.mainloop()

db.conn.close()
