import tkinter as tk

import matplotlib.pyplot as plt
import ttkbootstrap as ttkb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import state


CARD_BG = "#ffffff"
SPINE = "#dee2e6"
TEXT = "#495057"
ACCENT = "#9954bb"
ACCENT_2 = "#17a2b8"
CANVAS_BG = "#e9ecef"
LIGHT_BG = "#f8f9fa"
MUTED_FG = "#6c757d"
INFO_FG = "#9954bb"

PERIODS = [
    ("Azi", "today"),
    ("Săptămâna aceasta", "week"),
    ("Luna aceasta", "month"),
    ("Anul acesta", "year"),
    ("Total", "all"),
]


def _where_vendite(period):
    if period == "today":
        return "WHERE date(data) = date('now', 'localtime')"
    if period == "week":
        return "WHERE date(data) >= date('now', '-6 days', 'localtime')"
    if period == "month":
        return "WHERE strftime('%Y-%m', data) = strftime('%Y-%m', 'now', 'localtime')"
    if period == "year":
        return "WHERE strftime('%Y', data) = strftime('%Y', 'now', 'localtime')"
    return ""


def _where_movimenti(period):
    w = _where_vendite(period)
    if not w:
        return "AND m.tipo='vanzare'"
    return w.replace("WHERE", "AND") + " AND m.tipo='vanzare'"


def _style_ax(ax):
    for spine in ax.spines.values():
        spine.set_color(SPINE)
    ax.tick_params(colors=TEXT)
    ax.title.set_color(TEXT)


def _empty_ax(ax, title):
    ax.set_title(title)
    ax.text(0.5, 0.5, "Fără date", ha="center", va="center",
            color=TEXT, fontsize=12, transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])


def _kpi_card(parent, caption, value_var):
    card = ttkb.Frame(parent, padding=14, bootstyle="light")
    ttkb.Label(card, textvariable=value_var,
               font=("Segoe UI", 20, "bold"),
               background=LIGHT_BG,
               foreground=INFO_FG).pack(anchor="w")
    ttkb.Label(card, text=caption,
               font=("Segoe UI", 10),
               background=LIGHT_BG,
               foreground=MUTED_FG).pack(anchor="w")
    return card


def _fetch_scalar(sql, params=()):
    state.cursor.execute(sql, params)
    row = state.cursor.fetchone()
    return (row[0] if row and row[0] is not None else 0)


def mostra_dashboard():
    win = ttkb.Toplevel()
    win.title("Dashboard")
    win.geometry("1300x950")
    win.minsize(760, 600)
    win.state("zoomed")
    win.configure(bg=CANVAS_BG)

    scroll_outer = ttkb.Frame(win)
    scroll_outer.pack(fill="both", expand=True)

    scroll_canvas = tk.Canvas(scroll_outer, highlightthickness=0, bg=CANVAS_BG)
    scroll_vsb = ttkb.Scrollbar(scroll_outer, orient="vertical",
                                command=scroll_canvas.yview, bootstyle="round")
    scroll_canvas.configure(yscrollcommand=scroll_vsb.set)
    scroll_vsb.pack(side="right", fill="y")
    scroll_canvas.pack(side="left", fill="both", expand=True)

    wrap = ttkb.Frame(scroll_canvas, padding=16)
    wrap_window = scroll_canvas.create_window((0, 0), window=wrap, anchor="nw")

    def _on_wrap_configure(_e=None):
        scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

    def _on_canvas_configure(event):
        scroll_canvas.itemconfigure(wrap_window, width=event.width)

    wrap.bind("<Configure>", _on_wrap_configure)
    scroll_canvas.bind("<Configure>", _on_canvas_configure)

    def _on_mousewheel(event):
        scroll_canvas.yview_scroll(int(-event.delta / 120), "units")

    scroll_canvas.bind("<Enter>",
                       lambda e: scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel))
    scroll_canvas.bind("<Leave>",
                       lambda e: scroll_canvas.unbind_all("<MouseWheel>"))

    header = ttkb.Frame(wrap)
    header.pack(fill="x", pady=(0, 10))
    ttkb.Label(header, text="Dashboard Magazin",
               font=("Segoe UI", 20, "bold"),
               background=CANVAS_BG,
               foreground=INFO_FG).pack(side="left")

    ttkb.Label(header, text="Perioadă:",
               font=("Segoe UI", 11),
               background=CANVAS_BG,
               foreground=TEXT).pack(side="left", padx=(24, 6))
    period_var = ttkb.StringVar(value=PERIODS[2][0])
    combo = ttkb.Combobox(header, textvariable=period_var,
                          values=[p[0] for p in PERIODS],
                          state="readonly", width=22)
    combo.pack(side="left")

    kpi_row = ttkb.Frame(wrap)
    kpi_row.pack(fill="x", pady=(0, 12))

    rev_today = ttkb.StringVar(value="0.00 lei")
    rev_week = ttkb.StringVar(value="0.00 lei")
    rev_month = ttkb.StringVar(value="0.00 lei")
    rev_total = ttkb.StringVar(value="0.00 lei")
    n_sales = ttkb.StringVar(value="0")
    avg_basket = ttkb.StringVar(value="0.00 lei")

    kpi_defs = [
        ("Venit azi", rev_today),
        ("Venit săptămână", rev_week),
        ("Venit lună", rev_month),
        ("Venit total", rev_total),
        ("Număr bonuri (perioadă)", n_sales),
        ("Valoare medie bon (perioadă)", avg_basket),
    ]
    kpi_widgets = [_kpi_card(kpi_row, caption, var) for caption, var in kpi_defs]

    charts = ttkb.Frame(wrap)
    charts.pack(fill="both", expand=True)

    chart_cells = {}
    _chart_cols = [2]  # mutable so _cell_pos can read current layout

    def _apply_chart_grid(cols):
        for c in range(2):
            charts.columnconfigure(c, weight=0, uniform="")
        for r in range(6):
            charts.rowconfigure(r, weight=0)
        for c in range(cols):
            charts.columnconfigure(c, weight=1, uniform="chart")
        rows = 5 if cols == 1 else 3
        for r in range(rows):
            charts.rowconfigure(r, weight=1)

    _apply_chart_grid(2)

    def _clear_cell(key):
        old = chart_cells.get(key)
        if old is not None:
            old.destroy()
        cell = ttkb.Frame(charts)
        cell.grid(**_cell_pos(key), sticky="nsew", padx=8, pady=8)
        chart_cells[key] = cell
        return cell

    def _cell_pos(key):
        if _chart_cols[0] == 1:
            order = ["day", "month", "top_qty", "top_rev", "hour"]
            return dict(row=order.index(key), column=0)
        return {
            "day": dict(row=0, column=0),
            "month": dict(row=0, column=1),
            "top_qty": dict(row=1, column=0),
            "top_rev": dict(row=1, column=1),
            "hour": dict(row=2, column=0, columnspan=2),
        }[key]

    def _mount_fig(cell, fig):
        canvas = FigureCanvasTkAgg(fig, master=cell)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def refresh_kpis():
        q_today = "SELECT SUM(totale) FROM vendite WHERE date(data)=date('now','localtime')"
        q_week = "SELECT SUM(totale) FROM vendite WHERE date(data)>=date('now','-6 days','localtime')"
        q_month = "SELECT SUM(totale) FROM vendite WHERE strftime('%Y-%m',data)=strftime('%Y-%m','now','localtime')"
        rev_today.set(f"{_fetch_scalar(q_today):.2f} lei")
        rev_week.set(f"{_fetch_scalar(q_week):.2f} lei")
        rev_month.set(f"{_fetch_scalar(q_month):.2f} lei")
        rev_total.set(f"{_fetch_scalar('SELECT SUM(totale) FROM vendite'):.2f} lei")

    def refresh_period_kpis(period):
        w = _where_vendite(period)
        n = _fetch_scalar(f"SELECT COUNT(*) FROM vendite {w}")
        s = _fetch_scalar(f"SELECT SUM(totale) FROM vendite {w}")
        n_sales.set(str(int(n)))
        avg_basket.set(f"{(s / n if n else 0):.2f} lei")

    def draw_day_chart(period):
        cell = _clear_cell("day")
        w = _where_vendite(period)
        state.cursor.execute(f"""
            SELECT substr(data,1,10) AS d, SUM(totale)
            FROM vendite {w}
            GROUP BY d ORDER BY d
        """)
        rows = state.cursor.fetchall()
        fig = plt.Figure(figsize=(5, 3.2), facecolor=CARD_BG, layout="constrained")
        ax = fig.add_subplot(111, facecolor=CARD_BG)
        _style_ax(ax)
        if rows:
            ax.plot([r[0] for r in rows], [r[1] for r in rows],
                    marker="o", color=ACCENT, linewidth=2)
            ax.set_title("Vânzări per zi")
            ax.tick_params(axis="x", rotation=45, colors=TEXT)
            ax.grid(True, alpha=0.2, color=TEXT)
        else:
            _empty_ax(ax, "Vânzări per zi")
        _mount_fig(cell, fig)

    def draw_month_chart():
        cell = _clear_cell("month")
        state.cursor.execute("""
            SELECT strftime('%Y-%m', data) AS m, SUM(totale)
            FROM vendite
            GROUP BY m
            ORDER BY m DESC
            LIMIT 12
        """)
        rows = list(reversed(state.cursor.fetchall()))
        fig = plt.Figure(figsize=(5, 3.2), facecolor=CARD_BG, layout="constrained")
        ax = fig.add_subplot(111, facecolor=CARD_BG)
        _style_ax(ax)
        if rows:
            ax.bar([r[0] for r in rows], [r[1] for r in rows], color=ACCENT_2)
            ax.set_title("Vânzări per lună (ultimele 12)")
            ax.tick_params(axis="x", rotation=45, colors=TEXT)
            ax.grid(True, axis="y", alpha=0.2, color=TEXT)
        else:
            _empty_ax(ax, "Vânzări per lună")
        _mount_fig(cell, fig)

    def draw_top_qty(period):
        cell = _clear_cell("top_qty")
        w = _where_movimenti(period)
        state.cursor.execute(f"""
            SELECT m.nome, m.unit,
                   SUM(CASE WHEN m.unit='g' THEN m.quantita/1000.0
                            ELSE m.quantita END) AS qty
            FROM movimenti m
            WHERE 1=1 {w}
            GROUP BY m.nome, m.unit
            ORDER BY qty DESC
            LIMIT 5
        """)
        rows = state.cursor.fetchall()
        fig = plt.Figure(figsize=(5, 3.2), facecolor=CARD_BG, layout="constrained")
        ax = fig.add_subplot(111, facecolor=CARD_BG)
        _style_ax(ax)
        if rows:
            labels = [f"{r[0]} ({'kg' if r[1] == 'g' else 'buc'})" for r in rows]
            values = [r[2] for r in rows]
            ax.bar(labels, values, color=ACCENT)
            ax.set_title("Top 5 produse (cantitate, buc / kg)")
            ax.tick_params(axis="x", rotation=30, colors=TEXT)
            ax.grid(True, axis="y", alpha=0.2, color=TEXT)
        else:
            _empty_ax(ax, "Top 5 produse (cantitate)")
        _mount_fig(cell, fig)

    def draw_top_rev(period):
        cell = _clear_cell("top_rev")
        w = _where_movimenti(period)
        state.cursor.execute(f"""
            SELECT m.nome,
                   SUM(CASE WHEN m.unit='g' THEN m.quantita * p.prezzo / 1000.0
                            ELSE m.quantita * p.prezzo END) AS rev
            FROM movimenti m
            JOIN prodotti p ON p.id = m.id_prodotto
            WHERE 1=1 {w}
            GROUP BY m.nome
            ORDER BY rev DESC
            LIMIT 5
        """)
        rows = state.cursor.fetchall()
        fig = plt.Figure(figsize=(5, 3.2), facecolor=CARD_BG, layout="constrained")
        ax = fig.add_subplot(111, facecolor=CARD_BG)
        _style_ax(ax)
        if rows:
            ax.bar([r[0] for r in rows], [r[1] for r in rows], color="#f39c12")
            ax.set_title("Top 5 produse (venit)")
            ax.tick_params(axis="x", rotation=30, colors=TEXT)
            ax.grid(True, axis="y", alpha=0.2, color=TEXT)
        else:
            _empty_ax(ax, "Top 5 produse (venit)")
        _mount_fig(cell, fig)

    def draw_hour_chart(period):
        cell = _clear_cell("hour")
        w = _where_vendite(period)
        state.cursor.execute(f"""
            SELECT strftime('%H', data) AS h, SUM(totale)
            FROM vendite {w}
            GROUP BY h ORDER BY h
        """)
        data_map = {r[0]: r[1] for r in state.cursor.fetchall()}
        fig = plt.Figure(figsize=(10, 3), facecolor=CARD_BG, layout="constrained")
        ax = fig.add_subplot(111, facecolor=CARD_BG)
        _style_ax(ax)
        if data_map:
            hours = [f"{h:02d}" for h in range(24)]
            values = [data_map.get(h, 0) for h in hours]
            ax.bar(hours, values, color=ACCENT)
            ax.set_title("Venit pe ore (ora zilei)")
            ax.tick_params(colors=TEXT)
            ax.grid(True, axis="y", alpha=0.2, color=TEXT)
        else:
            _empty_ax(ax, "Venit pe ore (ora zilei)")
        _mount_fig(cell, fig)

    def current_period():
        label = period_var.get()
        for lbl, key in PERIODS:
            if lbl == label:
                return key
        return "month"

    def refresh_all(*_):
        period = current_period()
        refresh_kpis()
        refresh_period_kpis(period)
        draw_day_chart(period)
        draw_month_chart()
        draw_top_qty(period)
        draw_top_rev(period)
        draw_hour_chart(period)

    combo.bind("<<ComboboxSelected>>", refresh_all)

    _last_layout = [None]

    def _layout_kpis(cols):
        for w in kpi_widgets:
            w.grid_forget()
        for i in range(6):
            kpi_row.columnconfigure(i, weight=0, uniform="")
        for c in range(cols):
            kpi_row.columnconfigure(c, weight=1, uniform="kpi")
        for i, w in enumerate(kpi_widgets):
            w.grid(row=i // cols, column=i % cols,
                   sticky="nsew", padx=4, pady=4)

    def _reflow(event):
        if event.widget is not win:
            return
        w = win.winfo_width()
        if w < 760:
            key = "xs"
            kpi_cols, chart_cols = 2, 1
        elif w < 1080:
            key = "sm"
            kpi_cols, chart_cols = 3, 1
        else:
            key = "lg"
            kpi_cols, chart_cols = 6, 2
        if key == _last_layout[0]:
            return
        _last_layout[0] = key
        _layout_kpis(kpi_cols)
        if chart_cols != _chart_cols[0]:
            _chart_cols[0] = chart_cols
            _apply_chart_grid(chart_cols)
            refresh_all()

    win.bind("<Configure>", _reflow)

    _layout_kpis(6)
    refresh_all()
