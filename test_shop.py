import concurrent.futures
from contextlib import closing
import datetime as dt
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from shop import Shop, ShopError
from web_app import Server


class ShopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "shop.db"
        self.shop = Shop(self.path)
        self.today = dt.date.today().isoformat()

    def product(self, **changes):
        data = dict(name="Pâine", price="5.50", cost="3.25", quantity=10, unit="buc", low_stock=2)
        data.update(changes)
        return self.shop.product(data)["id"]

    def sale(self, pid, quantity=1, token="sale-token-001", price="5.50"):
        return self.shop.checkout(dict(token=token, lines=[dict(id=pid, quantity=quantity, price=price)]))

    def test_weighted_and_piece_products_make_one_receipt(self):
        bread = self.product()
        cheese = self.product(name="Brânză", unit="g", price="80", cost="50", quantity=1000)
        result = self.shop.checkout(dict(token="mixed-receipt", lines=[dict(id=bread, quantity=2, price="5.5"),dict(id=cheese, quantity=250, price=80)]))
        self.assertEqual(result["total_bani"], 3100)
        report = self.shop.reports(self.today,self.today)
        self.assertEqual(report["receipts"],1)
        self.assertEqual(report["profit_bani"],1200)
        self.assertEqual([p["quantita"] for p in sorted(self.shop.products(),key=lambda p:p['id'])],[8,750])

    def test_failed_checkout_rolls_back_every_line(self):
        pid = self.product()
        with self.assertRaises(ShopError):
            self.shop.checkout(dict(token="bad-receipt", lines=[dict(id=pid,quantity=2,price="5.50"),dict(id=pid,quantity=9,price="5.50")]))
        self.assertEqual(self.shop.products()[0]["quantita"],10)
        self.assertEqual(self.shop.reports(self.today,self.today)["receipts"],0)

    def test_retry_is_idempotent(self):
        pid = self.product()
        first, second = self.sale(pid), self.sale(pid)
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(self.shop.products()[0]["quantita"],9)

    def test_two_cashiers_cannot_oversell(self):
        pid = self.product(quantity=1)
        def buy(i):
            try:
                self.sale(pid, token=f"parallel-sale-{i}")
                return True
            except ShopError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(buy, [1,2]))
        self.assertEqual(sum(results),1)
        self.assertEqual(self.shop.products()[0]["quantita"],0)

    def test_invalid_values_and_duplicate_barcodes(self):
        for value in ("NaN", "Infinity", "-1", "1.5"):
            with self.subTest(value=value), self.assertRaises(ShopError):
                self.product(quantity=value)
        self.product(barcode="123")
        with self.assertRaises(ShopError): self.product(barcode="123")
        self.product(name="Mere", barcode="")
        self.product(name="Pere", barcode="")

    def test_historical_prices_and_costs_do_not_change(self):
        pid = self.product()
        self.sale(pid)
        p = self.shop.products()[0]
        self.shop.product(dict(id=pid,version=p['version'],name="Pâine nouă",price=20,cost=19,unit="buc"))
        report = self.shop.reports(self.today,self.today)
        self.assertEqual(report['revenue_bani'],550)
        self.assertEqual(report['profit_bani'],225)
        self.assertEqual(report['top'][0]['name'],"Pâine")

    def test_unknown_cost_is_explicit(self):
        self.sale(self.product(cost=""))
        r = self.shop.reports(self.today,self.today)
        self.assertEqual(r['unknown_cost_lines'],1)
        self.assertEqual(r['unknown_revenue_bani'],550)
        self.assertEqual(r['profit_bani'],0)

    def test_stale_prices_and_edits_are_rejected(self):
        pid = self.product()
        p = self.shop.products()[0]
        self.shop.restock(dict(id=pid,quantity=2))
        with self.assertRaises(ShopError): self.shop.product(dict(id=pid,version=p['version'],name='Pâine',price=10,unit='buc'))
        with self.assertRaises(ShopError): self.sale(pid,price=1)

    def test_inventory_saves_resumes_and_applies_zero(self):
        pid = self.product()
        count = self.shop.start_count()
        self.shop.save_count(dict(id=count['id'],lines=[dict(product_id=pid,counted=0)]))
        resumed = Shop(self.path).count()
        self.assertEqual(resumed['lines'][0]['counted'],0)
        self.assertEqual(self.shop.products()[0]['quantita'],10)
        self.shop.save_count(dict(id=count['id'],finish=True))
        self.assertIsNone(self.shop.count())
        self.assertEqual(self.shop.products()[0]['quantita'],0)
        with self.shop.connect() as c:
            self.assertEqual(c.execute("SELECT quantita FROM movimenti WHERE tipo LIKE 'inventar%' ").fetchone()[0],-10)

    def test_count_requires_all_products_and_blocks_sales_and_restock(self):
        pid = self.product()
        count = self.shop.start_count()
        for action in [lambda:self.sale(pid),lambda:self.shop.restock(dict(id=pid,quantity=1)),lambda:self.product(),lambda:self.shop.save_count(dict(id=count['id'],finish=True))]:
            with self.assertRaises(ShopError): action()
        self.shop.cancel_count(dict(id=count['id']))
        self.assertIsNone(self.shop.count())
        self.assertEqual(self.shop.products()[0]['quantita'],10)

    def test_count_detects_changes_from_old_desktop_app(self):
        pid = self.product()
        count = self.shop.start_count()
        with self.shop.connect() as c: c.execute('UPDATE prodotti SET quantita=9')
        with self.assertRaises(ShopError):
            self.shop.save_count(dict(id=count['id'],lines=[dict(product_id=pid,counted=5)],finish=True))
        self.assertEqual(self.shop.products()[0]['quantita'],9)

    def test_migration_preserves_legacy_and_backup(self):
        path = Path(self.temp.name) / 'old.db'
        with closing(sqlite3.connect(path)) as c, c:
            c.executescript("CREATE TABLE prodotti(id INTEGER PRIMARY KEY,nome TEXT,quantita INTEGER,prezzo REAL); INSERT INTO prodotti VALUES(1,'Lapte',8,10); CREATE TABLE vendite(id INTEGER PRIMARY KEY,totale REAL,data TEXT);")
            c.execute("INSERT INTO vendite VALUES (1,99,?)",(self.today,))
        migrated = Shop(path)
        self.assertEqual(migrated.products()[0]['quantita'],8)
        r=migrated.reports(self.today,self.today)
        self.assertEqual(r['legacy_receipts'],1)
        self.assertEqual(r['revenue_bani'],0)
        backup=path.parent/'backups'/'before-web-upgrade.db'
        self.assertTrue(backup.exists())
        with closing(sqlite3.connect(backup)) as c:
            self.assertNotIn('cost_bani',[r[1] for r in c.execute('PRAGMA table_info(prodotti)')])

    def test_backup_is_readable(self):
        self.product()
        backup = self.shop.backup()
        with closing(sqlite3.connect(backup)) as c:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(c.execute('SELECT quantita FROM prodotti').fetchone()[0],10)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.shop=Shop(Path(self.temp.name)/'http.db')
        self.server=Server(('127.0.0.1',0),self.shop)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.cookie=''

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()

    def request(self,path,data=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        all_headers={'Cookie':self.cookie}
        if data is not None: all_headers['Content-Type']='application/json'
        all_headers.update(headers or {})
        conn.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,all_headers)
        r=conn.getresponse();payload=r.read();cookie=r.getheader('Set-Cookie')
        if cookie:self.cookie=cookie.split(';')[0]
        status=r.status;conn.close()
        return status,payload

    def test_login_protects_data_and_logout_invalidates_session(self):
        self.assertEqual(self.request('/api/products')[0],401)
        self.assertEqual(self.request('/api/setup',{'password':'secret123'})[0],200)
        self.assertEqual(self.request('/api/products')[0],200)
        saved_cookie=self.cookie
        self.assertEqual(self.request('/api/logout',{})[0],200)
        self.cookie=saved_cookie
        self.assertEqual(self.request('/api/products')[0],401)
        self.assertEqual(self.request('/api/login',{'password':'wrong'})[0],401)
        self.assertEqual(self.request('/api/login',{'password':'secret123'})[0],200)

    def test_origin_and_host_checks(self):
        self.assertEqual(self.request('/api/setup',{'password':'secret123'}, {'Origin':'http://malicious.test'})[0],403)
        self.assertEqual(self.request('/',headers={'Host':'malicious.test'})[0],403)

    def test_api_sale_reports_exports_and_static_files(self):
        self.request('/api/setup',{'password':'secret123'})
        status,payload=self.request('/api/product',dict(name='Pâine',unit='buc',quantity=10,price=5,cost=3))
        self.assertEqual(status,200);pid=json.loads(payload)['id']
        status,_=self.request('/api/checkout',dict(token='http-sale-token',lines=[dict(id=pid,price=5,quantity=2)]))
        self.assertEqual(status,200)
        today=dt.date.today().isoformat()
        status,payload=self.request(f'/api/reports?start={today}&end={today}')
        self.assertEqual(json.loads(payload)['profit_bani'],400)
        for path in ['/', '/app.js','/style.css','/api/export?kind=stock','/api/backup',f'/api/export?kind=sales&start={today}&end={today}']:
            with self.subTest(path=path):self.assertEqual(self.request(path)[0],200)
        self.assertEqual(self.request('/api/reports?start=bad&end=bad')[0],400)


if __name__=='__main__':
    unittest.main()
