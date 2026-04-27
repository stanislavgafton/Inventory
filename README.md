# Magazin

A small-shop point-of-sale and inventory app for Windows. Scan a barcode, build a cart, close the receipt, and keep stock & sales history in a local SQLite database.

Built with Python + Tkinter ([ttkbootstrap](https://ttkbootstrap.readthedocs.io/) "cosmo" theme), `matplotlib` for the dashboard, and `openpyxl` for Excel import/export.

## Features

- **Barcode scan** — type or scan into the top input; products with that barcode are added to the cart, with audible OK / error beeps.
- **Cart & checkout** — adjust quantities, remove lines, and close the receipt to commit the sale.
- **Stock screen** — list, search, edit, and delete products; import/export to Excel.
- **Two units of measure** — pieces (`buc`) and grams (`g`), with the right price label and stock thresholds for each.
- **Dashboard** — sales charts powered by matplotlib.
- **History** — full movement log (entries, sales, manual adjustments) with Excel export.
- **Responsive layout** — desktop / tablet / phone reflow on resize.

## Requirements

- Windows 10 or 11
- Python 3.11+ (development only; end users get the bundled `.exe`)

## Run from source

```bat
py -m pip install ttkbootstrap matplotlib openpyxl
py main.py
```

The database is created automatically at `%APPDATA%\Magazin\inventario.db`.

## Project layout

| File | Purpose |
| --- | --- |
| `main.py` | App entry point — window, header, cart panel, sidebar |
| `db.py` | SQLite connection + schema migrations |
| `state.py` | Shared mutable app state (root window, cart, widgets) |
| `products.py` | Barcode lookup, add/edit product dialogs, beeps |
| `cart.py` | Cart UI + line management |
| `sales.py` | Receipt close & sale recording |
| `stock.py` | Stock browser screen |
| `dashboard.py` | Sales charts |
| `history.py` | Movement history |
| `export.py` / `import_products.py` | Excel I/O |
| `units.py` | `buc` / `g` formatting and thresholds |
| `beep_ok.wav` / `beep_err.wav` | Scan feedback sounds |

## Building a Windows installer

The repo ships with a one-shot build pipeline that produces `MagazinSetup.exe`:

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php) (one-time).
2. Run:
   ```bat
   build_installer.bat
   ```

The script:

1. `pip install`s `pyinstaller`, `ttkbootstrap`, `matplotlib`, `openpyxl`.
2. Freezes the app via `magazin.spec` to `dist\Magazin\Magazin.exe` (onedir, no console window, WAVs bundled).
3. Wraps it with `installer.iss` to produce `output\MagazinSetup.exe`.

The installer creates a Start Menu entry, an optional desktop shortcut, and a clean uninstaller.

## Where is my data?

| Path | What's there |
| --- | --- |
| `%APPDATA%\Magazin\inventario.db` | All products, sales, and movement history |
| `C:\Program Files\Magazin\` | App binaries (read-only; safe to remove via the uninstaller) |

The uninstaller deliberately leaves `%APPDATA%\Magazin` alone, so reinstalling or upgrading preserves your data. To migrate to a new PC, copy that file across.

**Backups:** there is no automatic backup. Either copy `inventario.db` periodically, or use the **Stock → Export Excel** and **History → Export Excel** buttons.

## Development notes

- Bundled read-only assets must be loaded via `_resource_path()` in `products.py` so they resolve under both `python main.py` and the frozen `.exe`.
- New writable user data must go under `DATA_DIR` from `db.py` (i.e. `%APPDATA%\Magazin`), never next to the executable — `Program Files` is read-only for non-admin users.
- When adding a new bundled asset, list it in the `datas=` block of `magazin.spec`.

## License

Proprietary — all rights reserved unless stated otherwise.
