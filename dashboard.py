import matplotlib.pyplot as plt
import ttkbootstrap as ttkb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import state


def mostra_dashboard():
    win = ttkb.Toplevel()
    win.title("Dashboard")
    win.geometry("1100x820")

    wrap = ttkb.Frame(win, padding=16)
    wrap.pack(fill="both", expand=True)

    state.cursor.execute("SELECT SUM(totale) FROM vendite")
    totale = state.cursor.fetchone()[0] or 0

    ttkb.Label(wrap, text=f"Total vânzări: {totale:.2f} lei",
               font=("Segoe UI", 18, "bold"), bootstyle="success").pack(pady=10)

    frame_grafici = ttkb.Frame(wrap)
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

    fig1 = plt.Figure(figsize=(4, 4), facecolor="#f8f9fa")
    ax1 = fig1.add_subplot(111)

    if dati:
        date = [row[0] for row in dati]
        valori = [row[1] for row in dati]
        ax1.plot(date, valori, marker="o", color="#0d6efd", linewidth=2)
        ax1.set_title("Vânzări per zi")
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)

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

    fig2 = plt.Figure(figsize=(4, 4), facecolor="#f8f9fa")
    ax2 = fig2.add_subplot(111)

    if top:
        nomi = [row[0] for row in top]
        quantita = [row[1] for row in top]
        ax2.bar(nomi, quantita, color="#198754")
        ax2.set_title("Top 5 produse vândute")
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, axis="y", alpha=0.3)

    canvas2 = FigureCanvasTkAgg(fig2, master=frame_grafici)
    canvas2.draw()
    canvas2.get_tk_widget().grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
