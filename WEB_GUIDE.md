# Magazin pentru PC și tabletă

Aplicație în limba română, pentru o băcănie sau un magazin alimentar. Calculatorul magazinului păstrează baza de date; PC-ul și tabletele folosesc aceeași aplicație în browser. Nu sunt necesare internetul, un abonament sau instalarea unei aplicații pe tabletă.

## Pornire pe Windows

1. Pe PC este necesar Python 3.11 sau mai nou. Versiunea web nu necesită biblioteci Python suplimentare.
2. Deschide **Start Magazin.bat**. Browserul se deschide automat la **http://localhost:8765**.
3. La prima pornire, alege o parolă de minimum șase caractere. Configurarea inițială se face pe PC, la adresa `localhost`.
4. Lasă fereastra Magazin deschisă cât timp se lucrează. Pentru oprire, închide acea fereastră sau apasă Ctrl+C.

### Conectarea unei tablete

- Conectează tableta la aceeași rețea Wi-Fi ca PC-ul.
- În fereastra Magazin apare adresa pentru tabletă, de exemplu `http://192.168.1.20:8765`. Deschide adresa în Safari sau Chrome și introdu parola magazinului.
- Dacă Windows întreabă despre firewall, permite accesul în rețeaua privată a magazinului. PC-ul trebuie să fie pornit și să nu intre în repaus.
- Poți salva adresa ca scurtătură pe ecranul principal al tabletei. Dacă adresa PC-ului se schimbă, folosește noua adresă afișată la pornire; o rezervare DHCP în router o poate menține stabilă.
- Aplicația este destinată rețelei locale de încredere. Nu configura redirecționare de port din internet; conexiunea locală folosește HTTP.

## Cele trei ecrane

### Casă

Scanează codul în câmpul de căutare (scanner USB/Bluetooth care funcționează ca tastatură, cu Enter la final). Sau caută după denumire și atinge produsul. Camera tabletei nu este folosită ca scanner în această versiune.

Pentru produse fără cod, alegerea după denumire funcționează identic. Pentru produse vrac, introdu cantitatea în **grame**: 250 pentru 250 g, 1000 pentru 1 kg. Prețurile și costurile acestora sunt pe kilogram.

Schimbă cantitățile, elimină o poziție sau golește coșul. După ce ai primit plata, apasă **Finalizează vânzarea** și confirmă. O singură tranzacție salvează bonul și toate scăderile de stoc. Dacă lipsește stoc pentru orice poziție, întreaga vânzare este refuzată, iar coșul rămâne disponibil. Reîncercarea aceleiași vânzări după o întrerupere de rețea nu dublează bonul.

Coșul este păstrat în sesiunea browserului la reîncărcarea paginii. **Actualizează** reîncarcă produsele și prețurile din coș. Pentru scannere, revino la câmpul de căutare înainte de scanare.

Bonul este o înregistrare internă a vânzării. Versiunea aceasta nu integrează o casă fiscală, imprimantă fiscală, terminal bancar sau cântar electronic.

### Stoc

**Produs nou**: completează denumirea, unitatea, prețul, stocul inițial și pragul de alertă. Categoria, codul și costul de achiziție sunt opționale. Un cod completat trebuie să fie unic.

**+ Marfă** adaugă cantitatea unei livrări la stoc. **Editează** schimbă denumirea, categoria, codul, prețul, costul și pragul. Stocul existent nu se rescrie prin editarea produsului. Unitatea nu se schimbă după creare, pentru a păstra corecte cantitățile istorice.

**Începe inventarierea** pentru numărătoarea anuală sau pentru o verificare completă:

1. Termină vânzările în curs și începe inventarierea. Vânzările, recepțiile și modificările de produse sunt blocate pe toate dispozitivele până la finalizare sau anulare.
2. Numără toate produsele și introdu cantitățile reale. Pentru produsele lipsă, scrie **0**. Un câmp gol înseamnă „încă nenumărat”.
3. Folosește **Salvează progresul** înainte de pauză, schimbarea dispozitivului sau închiderea browserului. Progresul salvat se poate relua ulterior.
4. Verifică diferențele afișate, apoi apasă **Revizuiește și finalizează**. După confirmare, stocul este înlocuit cu cantitățile numărate și diferențele sunt salvate în istoricul mișcărilor.

Inventarierea este comună magazinului. Folosește un singur dispozitiv pentru introducerea numărătorii, pentru a evita suprascrierea reciprocă a progresului. **Anulează inventarierea** deblochează magazinul fără să schimbe stocul. Inventarele, inclusiv cele anulate și progresul lor salvat, se pot exporta în CSV.

### Rapoarte

Alege azi, luna aceasta, anul acesta sau un interval de date. Vezi vânzările, numărul de bonuri, valoarea medie, profitul brut, produsele cele mai vândute și vânzările pe zile. Stocul mic și valoarea stocului arată situația curentă, indiferent de intervalul ales.

**Profit brut = vânzări − costul produselor vândute.** Nu reprezintă profitul net; nu sunt incluse chiria, salariile, taxele sau alte cheltuieli. Costul folosit este costul unitar completat la produs în momentul vânzării, nu un calcul FIFO sau o medie ponderată a livrărilor. Actualizează costul când este necesar.

Vânzările fără cost cunoscut sunt semnalate și excluse din calculul profitului cunoscut. Completarea costului mai târziu nu rescrie profitul vânzărilor anterioare. Prețurile, denumirile și costurile sunt salvate separat pe fiecare poziție de bon.

**Exportă vânzările** descarcă toate pozițiile din perioada selectată, cu cost și profit brut. Lista de pe ecran afișează ultimele 100 de bonuri; exportul nu are această limită. CSV-urile se deschid în Excel; cantitățile produselor vrac sunt în grame.

## Datele existente și copiile de siguranță

- La pornire normală se folosește `%APPDATA%\Magazin\inventario.db`, aceeași locație ca aplicația Windows existentă.
- Dacă acel fișier lipsește, se copiază baza `inventario.db` din proiect, dacă există. Produsele nu sunt înlocuite cu exemple.
- Înaintea primei migrări a unei baze existente se păstrează o copie `backups\before-web-upgrade.db`, lângă baza folosită. Schema este extinsă, fără ștergerea produselor, vânzărilor sau mișcărilor existente.
- Datele istorice din vechea aplicație sunt păstrate. Vechiul checkout putea înregistra mai multe totaluri pentru un singur coș; de aceea rapoartele web separă acele înregistrări și nu încearcă să le „corecteze” prin presupuneri. Același indicator separă și vânzările făcute în aplicația desktop păstrată în proiect. Folosește versiunea web pentru toate vânzările noi.
- O copie zilnică este creată la pornire și înaintea primei modificări din fiecare zi. **Descarcă o copie de siguranță** creează și descarcă un backup SQLite consistent, chiar în timpul folosirii aplicației.
- Copiile zilnice rămân pe același PC. Păstrează periodic un backup descărcat și pe un stick USB sau pe alt dispozitiv.
- Pentru restaurare: oprește aplicația pe PC, păstrează o copie a bazei curente, înlocuiește `inventario.db` cu backupul ales și pornește din nou. Backupul include parola magazinului de la data respectivă.

Nu lucra simultan în vechea aplicație desktop și în versiunea web: vechiul program nu cunoaște blocarea magazinului în timpul inventarierii.

## Administrare și dezvoltare

```powershell
# Pornire fără launcher
python3.14 web_app.py

# Bază separată pentru încercări; nu modifică baza magazinului
python3.14 web_app.py --db .local-data/demo.db --port 8766

# Doar pe PC, fără acces de pe tabletă
python3.14 web_app.py --host 127.0.0.1

# Dacă ai uitat parola: oprește serverul, rulează comanda, apoi repornește
python3.14 web_app.py --reset-password

# Teste
python3.14 -m unittest -v test_shop test_checkout
node --check web/app.js
```

Înlocuiește `python3.14` cu `py` sau `python` dacă așa se numește interpreterul instalat. Sesiunile expiră după 12 ore și la repornirea serverului. Parola este păstrată sub formă de hash; autentificarea limitează încercările repetate. Toate persoanele care au parola au acces la toate cele trei ecrane.

Pentru o aplicație Windows care nu necesită Python pe PC-ul final, dezvoltatorul poate construi executabilul:

```powershell
python -m pip install pyinstaller
python -m PyInstaller --noconfirm magazin_web.spec
```

Rezultatul este `dist\MagazinWeb.exe`; acesta deschide browserul și servește aplicația în rețeaua locală. Baza existentă din AppData are prioritate. Fișierul `inventario.db` din proiect este inclus ca bază inițială, deci verifică datele incluse înainte de distribuirea către alte magazine. Executabilul nu a fost construit în această modificare.

Fișiere principale: `web_app.py` (server local și autentificare), `shop.py` (operațiuni SQLite și rapoarte), `web/` (interfață fără dependențe externe). Vechea intrare `main.py` și installerul desktop rămân disponibile separat.
