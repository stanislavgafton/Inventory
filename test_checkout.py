import sqlite3
import unittest
from checkout import record_sale


class DesktopCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.addCleanup(self.conn.close)
        self.conn.executescript('''
            CREATE TABLE prodotti(id INTEGER PRIMARY KEY,quantita INTEGER);
            CREATE TABLE vendite(totale REAL,data TEXT);
            CREATE TABLE movimenti(id_prodotto INTEGER,nome TEXT,tipo TEXT,quantita INTEGER,data TEXT,unit TEXT);
            INSERT INTO prodotti VALUES(1,10),(2,1000);
        ''')

    def test_multi_product_cart_records_one_sale(self):
        total=record_sale(self.conn,[(1,'Pâine',5,2,'buc'),(2,'Brânză',80,250,'g')])
        self.assertEqual(total,30)
        self.assertEqual(self.conn.execute('SELECT totale FROM vendite').fetchall(),[(30,)])
        self.assertEqual(self.conn.execute('SELECT quantita FROM prodotti ORDER BY id').fetchall(),[(8,),(750,)])

    def test_failed_sale_rolls_back(self):
        with self.assertRaises(ValueError):
            record_sale(self.conn,[(1,'Pâine',5,2,'buc'),(2,'Brânză',80,1001,'g')])
        self.assertEqual(self.conn.execute('SELECT quantita FROM prodotti WHERE id=1').fetchone()[0],10)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM vendite').fetchone()[0],0)


if __name__=='__main__': unittest.main()
