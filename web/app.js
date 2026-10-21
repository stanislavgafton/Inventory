'use strict';
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = n => new Intl.NumberFormat('ro-MD', {minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(n || 0) / 100);
const qty = (n, unit) => `${new Intl.NumberFormat('ro-MD').format(n)} ${unit === 'g' ? 'g' : 'buc'}`;
const localDate = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
const token = () => Array.from(crypto.getRandomValues(new Uint32Array(4)), n=>n.toString(16).padStart(8,'0')).join('');
let products = [], cart = [], count = null, category = '', page = 'casa', cartToken = token(), checkoutBusy = false;
let quantityAction, productEditing, confirmation, toastTimer, configured = false, reportGeneration = 0;

async function api(path, data) {
  let response;
  try {
    response = await fetch('/api/' + path, data === undefined ? {cache:'no-store'} : {
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)
    });
  } catch {
    throw new Error('Conexiunea cu PC-ul s-a întrerupt. Verificați rețeaua și încercați din nou.');
  }
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401 && path !== 'login') {
      $('#app').hidden = true; $('#login').hidden = false;
    }
    throw new Error(result.error || 'Operațiunea nu a reușit.');
  }
  return result;
}

function toast(message, error = false) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message;
  $('#toast').classList.toggle('error-toast', error);
  $('#toast').hidden = false;
  toastTimer = setTimeout(() => $('#toast').hidden = true, error ? 9000 : 5000);
}

function confirmAction(title, message, action) {
  confirmation = action;
  $('#confirm-title').textContent = title;
  $('#confirm-message').textContent = message;
  $('#confirm-dialog').showModal();
}

function saveCart() {
  try { sessionStorage.setItem('magazin-cart', JSON.stringify({cart, cartToken})); } catch { /* Private browser mode. */ }
}
function changedCart() { cartToken = token(); saveCart(); renderCart(); }
function loadCart() {
  try {
    const saved = JSON.parse(sessionStorage.getItem('magazin-cart'));
    if (saved && Array.isArray(saved.cart) && typeof saved.cartToken === 'string') {
      cart = saved.cart.filter(l => Number.isInteger(l.id) && Number.isInteger(l.quantity) && l.quantity > 0 && Number.isFinite(l.price));
      cartToken = saved.cartToken;
    }
  } catch { /* Start with an empty cart. */ }
}

async function refresh() {
  const [nextProducts, nextCount] = await Promise.all([api('products'), api('count')]);
  products = nextProducts; count = nextCount;
  renderCatalog(); renderStock(); renderCount(); renderCart();
  $('#count-banner').hidden = !count;
}

function navigate(next) {
  if (!['casa','stoc','rapoarte'].includes(next)) next = 'casa';
  page = next;
  $$('.page').forEach(el => el.hidden = el.id !== page);
  $$('.nav-button').forEach(el => { el.classList.toggle('active', el.dataset.page === page); el.setAttribute('aria-current', el.dataset.page === page ? 'page' : 'false'); });
  $('#breadcrumb').textContent = {casa:'Casă', stoc:'Stoc', rapoarte:'Rapoarte'}[page];
  history.replaceState(null, '', '#' + page);
  if (page === 'rapoarte') loadReports().catch(e=>toast(e.message,true));
}

function renderCatalog() {
  const categories = [...new Set(products.map(p=>p.category).filter(Boolean))].sort();
  if (category && !categories.includes(category)) category = '';
  $('#categories').innerHTML = ['',...categories].map(c=>`<button class="chip ${c === category?'selected':''}" data-category="${esc(c)}">${esc(c || 'Toate produsele')}</button>`).join('');
  $('#category-options').innerHTML = categories.map(c=>`<option value="${esc(c)}"></option>`).join('');
  const search = $('#product-search').value.toLocaleLowerCase('ro').trim();
  const found = products.filter(p => (!category || p.category === category) && `${p.nome} ${p.barcode || ''}`.toLocaleLowerCase('ro').includes(search));
  $('#product-number').textContent = found.length;
  $('#product-grid').innerHTML = found.length ? found.map(p=>`
    <button class="product-card" data-add="${p.id}" ${p.quantita <= 0 || count ? 'disabled':''} aria-label="Adaugă ${esc(p.nome)}">
      <span class="product-icon" aria-hidden="true">${productIcon(p)}</span>
      <h3>${esc(p.nome)}</h3><span class="stock ${p.quantita <= p.low_stock ? 'low' : ''}">${p.quantita <= 0 ? 'Stoc epuizat' : qty(p.quantita,p.unit)+' în stoc'}</span>
      <span class="price-row"><span>${money(Math.round(p.prezzo*100))} <small>lei/${p.unit === 'g' ? 'kg' : 'buc'}</small></span><span class="add-icon" aria-hidden="true">+</span></span>
    </button>`).join('') : `<div class="empty-state">${products.length ? 'Niciun produs găsit. Încearcă altă denumire sau alt cod.' : 'Rafturile tale încep aici.<br>Adaugă primul produs în stoc, cu sau fără cod de bare.<br><button class="primary" id="first-product">+ Adaugă primul produs</button>'}</div>`;
}

function productIcon(p) {
  const n = `${p.nome} ${p.category}`.toLocaleLowerCase('ro');
  if (/pâine|paine|panifica|chifl|covrig/.test(n)) return '🍞';
  if (/lapt|iaurt|smânt|smant|lactat/.test(n)) return '🥛';
  if (/brân|branz|caș|casc|caş/.test(n)) return '🧀';
  if (/mere|fruct|banan|portocal/.test(n)) return '🍎';
  if (/legum|roși|rosii|cartof|ceap/.test(n)) return '🥕';
  if (/apă|apa|suc|băut|baut/.test(n)) return '🧃';
  if (/ouă|oua/.test(n)) return '🥚';
  if (/carne|salam|mezel/.test(n)) return '🥩';
  return '▧';
}

function askQuantity(product, mode, value) {
  quantityAction = {product, mode};
  const unit = product.unit === 'g' ? 'grame' : 'bucăți';
  $('#quantity-title').textContent = product.nome;
  $('#quantity-help').textContent = `${mode === 'restock' ? 'Recepție marfă. ' : ''}Disponibil: ${qty(product.quantita, product.unit)}. Preț: ${money(Math.round(product.prezzo*100))} lei/${product.unit==='g'?'kg':'buc'}.`;
  $('#quantity-label').textContent = `Cantitate (${unit})`;
  $('#quantity-button').textContent = mode === 'restock' ? 'Adaugă în stoc' : mode === 'edit' ? 'Actualizează cantitatea' : 'Adaugă în coș';
  $('#quantity-value').value = value || (product.unit === 'g' ? 100 : 1);
  $('#quantity-value').removeAttribute('max');
  if (mode !== 'restock') $('#quantity-value').max = product.quantita;
  $('#quantity-dialog .form-error').textContent = '';
  $('#quantity-dialog').showModal();
  $('#quantity-value').focus(); $('#quantity-value').select();
}

function addProduct(id) {
  if (count) return toast('Finalizați inventarierea înainte de a vinde.', true);
  const p = products.find(p=>p.id === Number(id));
  if (!p || p.quantita <= 0) return toast('Produsul nu este disponibil.', true);
  if (p.unit === 'g') return askQuantity(p, 'add');
  addToCart(p,1);
}

function addToCart(p, quantity, replace=false) {
  if (checkoutBusy) throw new Error('Așteptați finalizarea vânzării.');
  let line = cart.find(l=>l.id === p.id);
  const total = replace ? quantity : quantity + (line?.quantity || 0);
  if (!Number.isInteger(total) || total < 1 || total > p.quantita) throw new Error(`Stoc disponibil: ${qty(p.quantita,p.unit)}.`);
  if (line) { line.quantity = total; line.price = p.prezzo; line.name = p.nome; }
  else cart.push({id:p.id,name:p.nome,price:p.prezzo,unit:p.unit,quantity});
  changedCart();
}

const lineTotal = l => Math.round(Math.round(l.price*100) * l.quantity / (l.unit==='g' ? 1000 : 1));
function renderCart() {
  $('#cart-count').textContent = cart.length;
  $('#cart-total').innerHTML = money(cart.reduce((s,l)=>s+lineTotal(l),0)) + ' <small>lei</small>';
  $('#checkout').disabled = checkoutBusy || !cart.length || !!count;
  $('#clear-cart').disabled = !cart.length || checkoutBusy;
  $('#cart-lines').innerHTML = cart.length ? cart.map(l=>`<div class="cart-line"><div class="cart-line-top"><strong>${esc(l.name)}</strong><span>${money(lineTotal(l))} lei</span></div><div class="cart-unit-price">${money(Math.round(l.price*100))} lei/${l.unit==='g'?'kg':'buc'}</div><div class="cart-line-actions"><div class="quantity-control"><button data-cart-minus="${l.id}" aria-label="Scade cantitatea" ${checkoutBusy?'disabled':''}>−</button><button class="qty-value" data-cart-quantity="${l.id}" aria-label="Schimbă cantitatea" ${checkoutBusy?'disabled':''}>${qty(l.quantity,l.unit)}</button><button data-cart-plus="${l.id}" aria-label="Crește cantitatea" ${checkoutBusy?'disabled':''}>+</button></div><button class="remove-line" data-cart-remove="${l.id}" ${checkoutBusy?'disabled':''}>Elimină</button></div></div>`).join('') : `<div class="empty-cart"><span class="empty-symbol" aria-hidden="true">▦</span><strong>Coșul așteaptă primul produs</strong><span>Scanează un cod de bare<br>sau alege un produs din stânga.</span></div>`;
}

function renderStock() {
  const search = $('#stock-search').value.toLocaleLowerCase('ro').trim();
  const found = products.filter(p=>`${p.nome} ${p.barcode || ''}`.toLocaleLowerCase('ro').includes(search));
  $('#stock-rows').innerHTML = found.map(p=>`<tr><td><strong>${esc(p.nome)}</strong><small>${esc(p.category || 'Fără categorie')} · ${esc(p.barcode || 'Fără cod de bare')}</small></td><td><span class="stock-badge ${p.quantita<=p.low_stock?'low':''}">${qty(p.quantita,p.unit)}</span></td><td>${money(Math.round(p.prezzo*100))} lei<small>pe ${p.unit==='g'?'kg':'bucată'}</small></td><td>${p.cost_bani === null ? '<span class="muted">Necompletat</span>' : money(p.cost_bani)+' lei'}</td><td><button class="secondary" data-restock="${p.id}" ${count?'disabled':''}>+ Marfă</button><button class="secondary" data-edit="${p.id}" ${count?'disabled':''}>Editează</button></td></tr>`).join('') || '<tr><td colspan="5"><div class="empty-state">Niciun produs. Adaugă un produs nou pentru a începe.</div></td></tr>';
  $('#new-product').disabled = !!count;
}

function openProduct(id) {
  if (count) return toast('Finalizați inventarierea înainte de a modifica produsele.',true);
  const p = products.find(p=>p.id === Number(id));
  productEditing = p || null;
  const f = $('#product-form'); f.reset();
  $('#product-title').textContent = p ? 'Editează produsul' : 'Produs nou';
  if (p) {
    for (const [key,value] of Object.entries({name:p.nome,category:p.category,barcode:p.barcode || '',unit:p.unit,price:p.prezzo,cost:p.cost_bani===null?'':p.cost_bani/100,low_stock:p.low_stock})) f.elements[key].value = value;
  }
  f.elements.unit.disabled = !!p;
  $('#initial-stock-label').hidden = !!p;
  f.elements.quantity.disabled = !!p;
  $('.form-error',f).textContent = '';
  productUnitLabels();
  $('#product-dialog').showModal(); f.elements.name.focus();
}
function productUnitLabels() {
  const unit = $('#product-form').elements.unit.value;
  $('#price-label').textContent = `Preț vânzare (lei/${unit==='g'?'kg':'buc'})`;
  $('#cost-label').textContent = `Cost achiziție (lei/${unit==='g'?'kg':'buc'})`;
  $$('.quantity-unit').forEach(el=>el.textContent=`(${unit})`);
}

function renderCount() {
  $('#start-count').hidden = !!count;
  $('#count-panel').hidden = !count;
  if (!count) return;
  $('#count-panel').innerHTML = `<div class="count-heading"><div><p class="eyebrow">INVENTARIERE #${count.id}</p><h2>Numără produsele de pe raft</h2><p class="muted">Vânzările și recepțiile sunt oprite în timpul inventarului. Introdu 0 pentru produsele lipsă.<br>Salvează progresul înainte de a schimba ecranul sau de a închide aplicația.</p></div><button class="text-button" id="cancel-count">Anulează inventarierea</button></div><div class="count-table-wrap"><table><thead><tr><th>Produs</th><th>Stoc în aplicație</th><th>Numărat</th><th>Diferență</th></tr></thead><tbody>${count.lines.map(l=>`<tr><td><strong>${esc(l.name)}</strong><small>${l.unit==='g'?'Cantitate în grame':'Cantitate în bucăți'}</small></td><td>${qty(l.expected,l.unit)}</td><td><input class="count-input" data-count-id="${l.product_id}" type="number" min="0" step="1" inputmode="numeric" aria-label="Numărat: ${esc(l.name)}" value="${l.counted ?? ''}"></td><td id="difference-${l.product_id}"></td></tr>`).join('')}</tbody></table></div><p id="count-summary" class="count-summary"></p><div class="count-actions"><button class="secondary" id="save-count">Salvează progresul</button><button class="primary" id="finish-count">Revizuiește și finalizează →</button></div>`;
  updateCountSummary();
}
function countValues() {
  return $$('.count-input').map(el=>({product_id:Number(el.dataset.countId),counted:el.value}));
}
function updateCountSummary() {
  if (!count) return;
  let completed = 0, differences = 0;
  for (const item of countValues()) {
    const l = count.lines.find(l=>l.product_id===item.product_id);
    const hasValue = item.counted !== '' && Number.isInteger(Number(item.counted)) && Number(item.counted)>=0;
    const diff = Number(item.counted)-l.expected;
    $(`#difference-${item.product_id}`).textContent = hasValue ? `${diff>0?'+':''}${qty(diff,l.unit)}` : '—';
    if (hasValue) { completed++; if (diff!==0) differences++; }
  }
  $('#count-summary').textContent = `${completed} din ${count.lines.length} produse numărate · ${differences} produse cu diferențe de stoc.`;
}
function unsavedCount() {
  if (!count || !$('#count-panel').children.length) return false;
  return countValues().some(v=>String(v.counted) !== String(count.lines.find(l=>l.product_id===v.product_id)?.counted ?? ''));
}

async function loadReports() {
  const generation = ++reportGeneration;
  const start = $('#report-start').value, end = $('#report-end').value;
  $('#report-content').innerHTML = '<div class="empty-state">Se încarcă rapoartele…</div>';
  try {
    const r = await api(`reports?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
    if (generation !== reportGeneration) return;
    $('#export-sales').href = `/api/export?kind=sales&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
    const maximum = Math.max(1,...r.daily.map(d=>d.total_bani));
    $('#report-content').innerHTML = `
      ${r.legacy_receipts ? `<div class="notice">${r.legacy_receipts} înregistrări din aplicația veche sunt păstrate în baza de date, dar excluse din aceste totaluri: vechiul sistem putea înregistra aceeași vânzare de mai multe ori.</div>`:''}
      ${r.unknown_cost_lines ? `<div class="notice">${r.unknown_cost_lines} poziții vândute nu au cost de achiziție (${money(r.unknown_revenue_bani)} lei încasări). Profitul de mai jos include doar produsele cu cost cunoscut.</div>`:''}
      <div class="kpi-grid"><div class="kpi"><p class="kpi-label">Vânzări în perioada aleasă</p><p class="kpi-value">${money(r.revenue_bani)} <small>lei</small></p><p class="kpi-note">Totalul vânzărilor finalizate</p></div><div class="kpi"><p class="kpi-label">${r.unknown_cost_lines?'Profit brut cunoscut':'Profit brut'}</p><p class="kpi-value">${money(r.profit_bani)} <small>lei</small></p><p class="kpi-note">Vânzări minus costul produselor</p></div><div class="kpi"><p class="kpi-label">Vânzări finalizate</p><p class="kpi-value">${r.receipts}</p><p class="kpi-note">Un bon pentru fiecare coș finalizat</p></div><div class="kpi"><p class="kpi-label">Valoare medie bon</p><p class="kpi-value">${money(r.receipts ? Math.round(r.revenue_bani/r.receipts) : 0)} <small>lei</small></p><p class="kpi-note">Cât se cumpără, în medie</p></div></div>
      <p class="muted report-footnote">Profitul brut nu include chiria, salariile, taxele și alte cheltuieli. Costul folosit este cel salvat la momentul vânzării.</p>
      <div class="report-grid"><div class="panel"><div class="panel-heading"><h2>Vânzări pe zile</h2><span class="muted">lei</span></div>${r.daily.length?r.daily.map(d=>`<div class="bar-row"><span>${esc(d.day)}</span><meter min="0" max="${maximum}" value="${d.total_bani}" aria-label="Vânzări ${esc(d.day)}"></meter><span>${money(d.total_bani)}</span></div>`).join(''):'<div class="empty-state">Încă nu sunt vânzări în această perioadă.</div>'}</div><div class="panel"><div class="panel-heading"><h2>Produse preferate</h2><span class="muted">după vânzări</span></div><ul class="simple-list">${r.top.map((p,i)=>`<li><span>${i+1}. ${esc(p.name)}<small>${qty(p.quantity,p.unit)} vândute</small></span><strong>${money(p.total_bani)} lei</strong></li>`).join('') || '<li>Nicio vânzare încă.</li>'}</ul></div>
      <div class="panel"><div class="panel-heading"><h2>De completat pe raft</h2><span class="pill">${r.low_stock.length}</span></div><ul class="simple-list">${r.low_stock.map(p=>`<li><span>${esc(p.nome)}</span><strong class="stock-badge low">${qty(p.quantita,p.unit)}</strong></li>`).join('') || '<li>Stocul este peste pragurile de alertă.</li>'}</ul><p class="muted help-line">Valoarea stocului la cost cunoscut: <strong>${money(r.stock_value_bani)} lei</strong>. ${r.unknown_stock_costs ? `${r.unknown_stock_costs} produse au cost necompletat.`:''} Stocul afișat este cel de acum.</p></div>
      <div class="panel"><div class="panel-heading"><h2>Ultimele vânzări</h2><span class="muted">maximum 100</span></div><ul class="simple-list">${r.receipts_list.map(s=>`<li><span>Bon #${s.id}<small>${esc(s.data)}</small></span><strong>${money(s.total_bani)} lei</strong></li>`).join('') || '<li>Nicio vânzare în perioada aleasă.</li>'}</ul></div></div>`;
  } catch (e) {
    if (generation === reportGeneration) $('#report-content').innerHTML = `<div class="notice">${esc(e.message)}</div>`;
    throw e;
  }
}

function setPeriod(period) {
  const end = new Date(), start = new Date();
  if (period === 'month') start.setDate(1);
  if (period === 'year') { start.setMonth(0); start.setDate(1); }
  $('#report-start').value = localDate(start); $('#report-end').value = localDate(end);
  $$('[data-period]').forEach(el=>el.classList.toggle('selected',el.dataset.period===period));
}

async function boot() {
  const status = await api('status'); configured = status.configured;
  $('#today').textContent = new Intl.DateTimeFormat('ro-MD',{weekday:'long',day:'numeric',month:'long',year:'numeric'}).format(new Date());
  if (!configured) {
    $('#login-title').textContent = 'Magazinul tău, pregătit de lucru.';
    $('#login-help').textContent = status.local ? 'Alege o parolă de minimum 6 caractere. O vei folosi și pe tabletă.' : 'Deschide aplicația pe PC-ul magazinului pentru a configura parola inițială.';
    $('#password').autocomplete = 'new-password';
    $('#login-button').textContent = 'Configurează magazinul →';
    $('#login-button').disabled = !status.local;
  } else {
    $('#login-title').textContent = 'O zi bună începe simplu.';
    $('#login-help').textContent = 'Introduceți parola magazinului pentru a începe.';
    $('#password').autocomplete = 'current-password';
    $('#login-button').textContent = 'Intră în magazin →';
    $('#login-button').disabled = false;
  }
  $('#app').hidden = !status.authenticated; $('#login').hidden = status.authenticated;
  if (status.authenticated) {
    loadCart(); await refresh(); setPeriod('today'); navigate(location.hash.slice(1));
  }
}

$('#login-form').addEventListener('submit',async e=>{
  e.preventDefault(); const button = $('#login-button'); button.disabled = true; $('#login-error').textContent='';
  try { await api(configured?'login':'setup',{password:$('#password').value}); $('#password').value=''; await boot(); }
  catch(e) { $('#login-error').textContent=e.message; }
  finally { button.disabled=false; }
});
for (const logout of [$('#logout'),$('#tablet-logout')]) logout.addEventListener('click',()=>confirmAction('Închizi sesiunea?', 'Coșul curent va fi golit. Datele salvate rămân în magazin.',async()=>{
  if (unsavedCount()) throw new Error('Salvați progresul inventarului înainte de ieșire.');
  await api('logout',{}); cart=[]; changedCart(); await boot();
}));
document.addEventListener('click',async e=>{
  const button = e.target.closest('button'); if (!button || button.disabled) return;
  try {
    if (button.matches('[data-close]')) return button.closest('dialog').close();
    if (button.matches('[data-page]')) return navigate(button.dataset.page);
    if (button.matches('[data-category]')) { category=button.dataset.category; return renderCatalog(); }
    if (button.matches('[data-add]')) return addProduct(button.dataset.add);
    if (button.matches('[data-edit]')) return openProduct(button.dataset.edit);
    if (button.matches('[data-restock]')) return askQuantity(products.find(p=>p.id===Number(button.dataset.restock)),'restock');
    if (button.matches('[data-cart-remove]')) { cart=cart.filter(l=>l.id!==Number(button.dataset.cartRemove)); return changedCart(); }
    if (button.matches('[data-cart-plus],[data-cart-minus],[data-cart-quantity]')) {
      const id = Number(button.dataset.cartPlus || button.dataset.cartMinus || button.dataset.cartQuantity);
      const p=products.find(p=>p.id===id), l=cart.find(l=>l.id===id);
      if (!p) throw new Error('Produsul nu mai există. Eliminați-l din coș.');
      if (button.matches('[data-cart-quantity]') || p.unit==='g') return askQuantity(p,'edit',l.quantity);
      if (button.matches('[data-cart-minus]') && l.quantity===1) { cart=cart.filter(l=>l.id!==id); return changedCart(); }
      return addToCart(p,l.quantity+(button.matches('[data-cart-minus]')?-1:1),true);
    }
    if (button.matches('.refresh')) {
      if (unsavedCount()) throw new Error('Salvați mai întâi progresul inventarului.');
      await refresh();
      for (const l of cart) { const p=products.find(p=>p.id===l.id); if(p) {l.price=p.prezzo;l.name=p.nome;} }
      changedCart(); return toast('Produsele și prețurile au fost actualizate.');
    }
    if (button.id==='first-product' || button.id==='new-product') return openProduct();
    if (button.id==='clear-cart') return confirmAction('Golești coșul?', 'Produsele vor fi eliminate din vânzarea curentă.',()=>{cart=[]; changedCart();});
    if (button.id==='checkout') return confirmAction('Finalizezi vânzarea?', `Total de încasat: ${money(cart.reduce((s,l)=>s+lineTotal(l),0))} lei.\nConfirmă după ce ai primit plata.`,completeCheckout);
    if (button.id==='start-count') return confirmAction('Începi inventarierea?', 'Vânzările și recepțiile vor fi oprite până la finalizare. Numără toate produsele, apoi confirmă diferențele.',async()=>{await api('count/start',{});await refresh();});
    if (button.id==='save-count') { await api('count/save',{id:count.id,lines:countValues()}); count=await api('count'); return toast('Progresul inventarului a fost salvat.'); }
    if (button.id==='finish-count') {
      const lines=countValues();
      if (lines.some(l=>l.counted==='' || !Number.isInteger(Number(l.counted)) || Number(l.counted)<0)) throw new Error('Numărați toate produsele. Introduceți 0 pentru cele care lipsesc.');
      const diffs=lines.filter(l=>Number(l.counted)!==count.lines.find(p=>p.product_id===l.product_id).expected);
      const preview=diffs.slice(0,8).map(l=>{const p=count.lines.find(p=>p.product_id===l.product_id);return `${p.name}: ${qty(p.expected,p.unit)} → ${qty(Number(l.counted),p.unit)}`;}).join('\n');
      return confirmAction('Confirmi stocul numărat?',`${diffs.length} produse cu diferențe. Stocul va fi înlocuit cu cantitățile numărate.\n${preview}${diffs.length>8?'\n… și alte diferențe afișate în tabel.':''}`,async()=>{await api('count/save',{id:count.id,lines,finish:true});count=null;await refresh();toast('Inventar finalizat. Stocul este actualizat.');});
    }
    if (button.id==='cancel-count') return confirmAction('Anulezi inventarierea?', 'Cantitățile numărate sunt păstrate în istoricul inventarelor dacă au fost salvate. Stocul nu va fi modificat.',async()=>{await api('count/cancel',{id:count.id});count=null;await refresh();});
    if (button.matches('[data-period]')) {setPeriod(button.dataset.period);await loadReports();}
  } catch(e) { toast(e.message,true); }
});

async function completeCheckout() {
  if (checkoutBusy || !cart.length) return;
  checkoutBusy=true; renderCart();
  let result;
  try {
    result = await api('checkout',{token:cartToken,lines:cart.map(l=>({id:l.id,quantity:l.quantity,price:l.price}))});
    cart=[]; cartToken=token(); saveCart(); renderCart();
    toast(`Vânzare salvată. Bon #${result.id}${result.total_bani!==undefined?' · '+money(result.total_bani)+' lei':''}.`);
    await refresh();
  } catch(e) { throw new Error((result?'Vânzarea a fost salvată. ':'')+e.message); }
  finally {checkoutBusy=false;renderCart();}
}

$('#confirm-form').addEventListener('submit',async e=>{
  e.preventDefault(); const action=confirmation; $('#confirm-dialog').close();
  try {await action();} catch(e) {toast(e.message,true);}
});
$('#product-search').addEventListener('input',renderCatalog);
$('#stock-search').addEventListener('input',renderStock);
$('#scan-form').addEventListener('submit',e=>{
  e.preventDefault(); const value=$('#product-search').value.trim(); if (!value) return;
  const exact=products.filter(p=>p.barcode && p.barcode===value);
  const names=products.filter(p=>p.nome.toLocaleLowerCase('ro').includes(value.toLocaleLowerCase('ro')));
  const p=exact.length===1?exact[0]:names.length===1?names[0]:null;
  if (!p) return toast(exact.length>1?'Codul este duplicat. Corectați produsele în Stoc.':'Alege un produs din rezultate sau adaugă-l în Stoc.',true);
  try {addProduct(p.id);$('#product-search').value='';category='';renderCatalog();} catch(e){toast(e.message,true);}
});
$('#product-form').elements.unit.addEventListener('change',()=>{
  productUnitLabels(); if(!productEditing) $('#product-form').elements.low_stock.value=$('#product-form').elements.unit.value==='g'?500:5;
});
$('#product-form').addEventListener('submit',async e=>{
  e.preventDefault(); const form=e.currentTarget, button=$('button[type=submit]',form); button.disabled=true;
  try {
    const data=Object.fromEntries(new FormData(form));
    if(productEditing) Object.assign(data,{id:productEditing.id,version:productEditing.version,unit:productEditing.unit});
    await api('product',data); $('#product-dialog').close(); await refresh(); toast('Produsul a fost salvat.');
  } catch(e){$('.form-error',form).textContent=e.message;} finally{button.disabled=false;}
});
$('#quantity-form').addEventListener('submit',async e=>{
  e.preventDefault(); const button=$('#quantity-button');button.disabled=true;
  try {
    const n=Number($('#quantity-value').value),{product,mode}=quantityAction;
    if (!Number.isInteger(n)||n<1) throw new Error('Introduceți o cantitate întreagă, mai mare decât 0.');
    if(mode==='restock') {await api('restock',{id:product.id,quantity:n});await refresh();toast('Marfa a fost adăugată în stoc.');}
    else addToCart(product,n,mode==='edit');
    $('#quantity-dialog').close(); if(page==='casa') $('#product-search').focus();
  } catch(e){$('#quantity-dialog .form-error').textContent=e.message;} finally{button.disabled=false;}
});
$('#count-panel').addEventListener('input',updateCountSummary);
$('#report-filter').addEventListener('submit',e=>{e.preventDefault();$$('[data-period]').forEach(el=>el.classList.remove('selected'));loadReports().catch(e=>toast(e.message,true));});
window.addEventListener('beforeunload',e=>{if(checkoutBusy || unsavedCount()){e.preventDefault();e.returnValue='';}});
boot().catch(e=>{ $('#login').hidden=false;$('#login-error').textContent=e.message;toast(e.message,true); });
