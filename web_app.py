"""Run with python web_app.py. No third-party runtime dependencies."""

import argparse
import csv
import hashlib
import hmac
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import secrets
import socket
import sqlite3
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit
import webbrowser

from shop import Shop, ShopError, default_database


ASSETS = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "web"


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, shop):
        super().__init__(address, Handler)
        self.shop = shop
        self.sessions = {}
        self.attempts = {}
        self.auth_lock = threading.Lock()
        self.allowed_hosts = {"localhost", "127.0.0.1", socket.gethostname().lower()}
        self.allowed_hosts.update(local_addresses())


def local_addresses():
    addresses = set()
    try:
        addresses.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return addresses


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Avoid recording credentials or request bodies.
        pass

    def reply(self, data, status=200, content_type="application/json; charset=utf-8", cookie=None, filename=None):
        payload = json.dumps(data, ensure_ascii=False).encode() if content_type.startswith("application/json") else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(payload)

    def valid_host(self):
        host = urlsplit("http://" + self.headers.get("Host", "")).hostname
        if host not in self.server.allowed_hosts:
            self.reply({"error": "Adresă nepermisă."}, 403)
            return False
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host"):
            self.reply({"error": "Origine nepermisă."}, 403)
            return False
        return True

    def authenticated(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookie["magazin_session"].value
        except (KeyError, ValueError):
            return False
        with self.server.auth_lock:
            expires = self.server.sessions.get(token, 0)
            if expires < time.time():
                self.server.sessions.pop(token, None)
                return False
        return True

    def configured(self):
        with self.server.shop.connect() as c:
            return c.execute("SELECT value FROM web_settings WHERE key='password'").fetchone()

    def do_GET(self):
        try:
            self.get()
        except (ShopError, ValueError) as exc:
            self.reply({"error": str(exc)}, 400)
        except (sqlite3.Error, OSError):
            self.reply({"error": "Datele nu pot fi citite. Verificați spațiul pe disc și relansați aplicația."}, 500)

    def get(self):
        if not self.valid_host():
            return
        path = urlsplit(self.path).path
        if path == "/api/status":
            return self.reply({"configured": bool(self.configured()), "authenticated": self.authenticated(),
                               "local": self.client_address[0] in ("127.0.0.1", "::1")})
        if path.startswith("/api/"):
            if not self.authenticated():
                return self.reply({"error": "Autentificați-vă pentru a continua."}, 401)
            shop = self.server.shop
            if path == "/api/products":
                return self.reply(shop.products())
            if path == "/api/count":
                return self.reply(shop.count())
            if path == "/api/reports":
                query = parse_qs(urlsplit(self.path).query)
                return self.reply(shop.reports(query.get("start", [""])[0], query.get("end", [""])[0]))
            if path == "/api/backup":
                target = shop.backup()
                return self.reply(target.read_bytes(), content_type="application/octet-stream", filename=target.name)
            if path == "/api/export":
                query = parse_qs(urlsplit(self.path).query)
                kind = query.get("kind", ["stock"])[0]
                out = io.StringIO(newline="")
                writer = csv.writer(out)
                if kind == "stock":
                    writer.writerow(["ID", "Produs", "Cod de bare", "Unitate", "Stoc", "Preț lei", "Cost lei", "Categorie"])
                    for p in shop.products():
                        writer.writerow([p["id"], p["nome"], p["barcode"] or "", p["unit"], p["quantita"], p["prezzo"], "" if p["cost_bani"] is None else p["cost_bani"] / 100, p["category"]])
                elif kind == "counts":
                    writer.writerow(["Inventar", "Început", "Închis", "Produs", "Unitate", "Stoc anterior", "Numărat", "Diferență"])
                    with shop.connect() as c:
                        for r in c.execute("SELECT c.id,c.created,c.closed,l.name,l.unit,l.expected,l.counted,l.counted-l.expected FROM counts c JOIN count_lines l ON l.count_id=c.id ORDER BY c.id,l.name"):
                            writer.writerow(r)
                elif kind == "sales":
                    start, end = query.get("start", [""])[0], query.get("end", [""])[0]
                    shop.reports(start, end)  # Validate dates.
                    writer.writerow(["Bon", "Data", "Produs", "Unitate", "Cantitate", "Vânzări lei", "Cost lei", "Profit brut lei"])
                    with shop.connect() as c:
                        for r in c.execute("SELECT v.id,v.data,l.name,l.unit,l.quantity,l.total_bani,l.cost_total_bani FROM sale_lines l JOIN vendite v ON v.id=l.sale_id WHERE date(v.data) BETWEEN ? AND ? ORDER BY v.id,l.id", (start, end)):
                            writer.writerow([*r[:5], r[5] / 100, "" if r[6] is None else r[6] / 100, "" if r[6] is None else (r[5] - r[6]) / 100])
                else:
                    raise ShopError("Export necunoscut.")
                # Protect spreadsheet users from formula injection in product names.
                raw = io.StringIO(out.getvalue())
                safe = io.StringIO(newline="")
                w = csv.writer(safe)
                for row in csv.reader(raw):
                    w.writerow(["'" + cell if cell.lstrip().startswith(("=", "+", "-", "@")) else cell for cell in row])
                return self.reply(("\ufeff" + safe.getvalue()).encode(), content_type="text/csv; charset=utf-8", filename=f"magazin-{kind}.csv")
            return self.reply({"error": "Pagina nu există."}, 404)
        files = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
        if path not in files:
            return self.reply({"error": "Pagina nu există."}, 404)
        name, mime = files[path]
        self.reply((ASSETS / name).read_bytes(), content_type=mime)

    def do_POST(self):
        try:
            if not self.valid_host():
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.reply({"error": "Format invalid."}, 415)
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1_000_000:
                return self.reply({"error": "Cerere prea mare sau goală."}, 400)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ShopError("Cerere invalidă.")
            path = urlsplit(self.path).path
            if path in ("/api/setup", "/api/login"):
                return self.login(data, path == "/api/setup")
            if not self.authenticated():
                return self.reply({"error": "Autentificați-vă pentru a continua."}, 401)
            if path == "/api/logout":
                cookie = SimpleCookie(self.headers.get("Cookie", ""))
                with self.server.auth_lock:
                    self.server.sessions.pop(cookie["magazin_session"].value, None)
                return self.reply({"ok": True}, cookie="magazin_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")
            shop = self.server.shop
            routes = {"/api/product": shop.product, "/api/restock": shop.restock, "/api/checkout": shop.checkout,
                      "/api/count/start": lambda _: shop.start_count(), "/api/count/save": shop.save_count,
                      "/api/count/cancel": shop.cancel_count}
            if path not in routes:
                return self.reply({"error": "Operațiune necunoscută."}, 404)
            shop.daily_backup()
            return self.reply(routes[path](data))
        except (ShopError, ValueError, TypeError, AttributeError, KeyError) as exc:
            self.reply({"error": str(exc) if isinstance(exc, ShopError) else "Cerere invalidă."}, 400)
        except (sqlite3.Error, OSError):
            self.reply({"error": "Operațiunea nu a fost salvată. Verificați discul și încercați din nou."}, 500)

    def login(self, data, setup):
        password = str(data.get("password", ""))
        ip = self.client_address[0]
        with self.server.auth_lock:
            failures, since = self.server.attempts.get(ip, (0, time.time()))
            if time.time() - since > 60:
                failures, since = 0, time.time()
            if failures >= 10:
                return self.reply({"error": "Prea multe încercări. Așteptați un minut."}, 429)
            with self.server.shop.connect() as c:
                row = c.execute("SELECT value FROM web_settings WHERE key='password'").fetchone()
                if setup:
                    if row or ip not in ("127.0.0.1", "::1"):
                        return self.reply({"error": "Configurarea inițială se face pe calculatorul magazinului."}, 403)
                    if not 6 <= len(password) <= 128:
                        raise ShopError("Alegeți o parolă cu cel puțin 6 caractere.")
                    salt = secrets.token_hex(16)
                    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 300_000).hex()
                    c.execute("INSERT INTO web_settings VALUES ('password',?)", (salt + ":" + digest,))
                else:
                    if not row or len(password) > 128:
                        return self.reply({"error": "Parolă incorectă sau aplicație neconfigurată."}, 401)
                    salt, digest = row[0].split(":")
                    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 300_000).hex()
                    if not hmac.compare_digest(digest, actual):
                        self.server.attempts[ip] = (failures + 1, since)
                        return self.reply({"error": "Parolă incorectă."}, 401)
            self.server.attempts.pop(ip, None)
            self.server.sessions = {k: v for k, v in self.server.sessions.items() if v > time.time()}
            token = secrets.token_urlsafe(32)
            self.server.sessions[token] = time.time() + 12 * 3600
        return self.reply({"ok": True}, cookie=f"magazin_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Magazin — aplicație locală pentru PC și tabletă")
    parser.add_argument("--db", type=Path, help="Bază de date alternativă")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reset-password", action="store_true", help="Resetează parola local, apoi oprește aplicația")
    args = parser.parse_args()
    shop = Shop(args.db or default_database())
    if args.reset_password:
        with shop.connect() as c:
            c.execute("DELETE FROM web_settings WHERE key='password'")
        print("Parola a fost resetată. Relansați aplicația și configurați parola pe PC.")
        return
    server = Server((args.host, args.port), shop)
    print(f"PC: http://localhost:{server.server_port}")
    if args.host == "0.0.0.0":
        for address in sorted(local_addresses() - {"127.0.0.1"}):
            print(f"Tabletă (aceeași rețea Wi-Fi): http://{address}:{server.server_port}")
    print(f"Date: {shop.path}\nÎnchideți această fereastră pentru a opri aplicația.")
    if not args.no_browser:
        webbrowser.open(f"http://localhost:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
