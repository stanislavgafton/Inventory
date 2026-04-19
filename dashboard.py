import tkinter as tk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import state


def mostra_dashboard():
    win = tk.Toplevel()
    win.title("Dashboard")
    win.geometry("1000x800")

    state.cursor.execute("SELECT SUM(totale) FROM vendite")
    totale = state.cursor.fetchone()[0] or 0

    tk.Label(win, text=f"Totale vendite: {totale:.2f} lei",
             font=("Arial", 16)).pack(pady=10)

    frame_grafici = tk.Frame(win)
    frame_grafici.columnconfigure(0, weight=1)
    frame_grafici.columnconfigure(1, weight=1)
    frame_grafici.rowconfigure(0, weight=1)
    frame_grafici.pack(fill="both", expand=True)

    state.cursor.execute("""
        SELECT substr(data, 1, 10), SUM(totale)
        FROM vendite
        GROUP BY substr(data, 1, 10)
        ORDER BY substr(data, 1, 10)
    """)

    dati = state.cursor.fetchall()

    fig1 = plt.Figure(figsize=(3, 3))
    ax1 = fig1.add_subplot(111)

    if dati:
        date = [row[0] for row in dati]
        valori = [row[1] for row in dati]

        ax1.plot(date, valori)
        ax1.set_title("Vendite per giorno")
        ax1.tick_params(axis='x', rotation=45)

    canvas1 = FigureCanvasTkAgg(fig1, master=frame_grafici)
    canvas1.draw()
    canvas1.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    state.cursor.execute("""
        SELECT nome, SUM(quantita)
        FROM movimenti
        WHERE tipo = 'vendita'
        GROUP BY nome
        ORDER BY SUM(quantita) DESC
        LIMIT 5
    """)

    top = state.cursor.fetchall()

    fig2 = plt.Figure(figsize=(3, 3))
    ax2 = fig2.add_subplot(111)

    if top:
        nomi = [row[0] for row in top]
        quantita = [row[1] for row in top]

        ax2.bar(nomi, quantita)
        ax2.set_title("Top prodotti venduti")
        ax2.tick_params(axis='x', rotation=45)

    canvas2 = FigureCanvasTkAgg(fig2, master=frame_grafici)
    canvas2.draw()
    canvas2.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
