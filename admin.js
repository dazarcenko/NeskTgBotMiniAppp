const $ = id => document.getElementById(id);
const login = $('login'), panel = $('panel'), logout = $('logout');

async function api(url, options={}) {
  const r = await fetch(url, options);
  const data = await r.json().catch(()=>({}));
  if (r.status === 401) showLogin();
  if (!r.ok) throw new Error(data.detail || data.error || 'Ошибка');
  return data;
}
function showLogin(){ login.classList.remove('hidden'); panel.classList.add('hidden'); logout.classList.add('hidden'); }
function showPanel(){ login.classList.add('hidden'); panel.classList.remove('hidden'); logout.classList.remove('hidden'); }

$('loginBtn').onclick = async () => {
  try {
    const fd = new FormData(); fd.append('password', $('password').value);
    await api('/api/admin/login',{method:'POST',body:fd});
    $('password').value=''; showPanel(); await loadAll();
  } catch(e){ $('loginError').textContent=e.message; }
};
logout.onclick = async()=>{ await api('/api/admin/logout',{method:'POST'}); showLogin(); };

async function loadAll(){ await loadCategories(); await loadProducts(); }
async function loadCategories(){
  const data = await api('/api/admin/categories');
  const box=$('categories'), select=$('categorySelect'); box.innerHTML=''; select.innerHTML='';
  data.forEach(c=>{
    const opt=document.createElement('option'); opt.value=c.id; opt.textContent=c.name; select.appendChild(opt);
    const row=document.createElement('div'); row.className='row';
    row.innerHTML=`${c.image?`<img src="${c.image}">`:''}<div class="grow"><b>${esc(c.name)}</b><div class="small">ID: ${c.id}</div></div><button class="danger" data-id="${c.id}">Удалить</button>`;
    row.querySelector('button').onclick=async()=>{if(!confirm('Удалить категорию?'))return; try{await api('/api/admin/categories/'+c.id,{method:'DELETE'});await loadAll()}catch(e){alert(e.message)}};
    box.appendChild(row);
  });
}
$('categoryForm').onsubmit=async e=>{e.preventDefault();try{await api('/api/admin/categories',{method:'POST',body:new FormData(e.target)});e.target.reset();await loadCategories()}catch(x){alert(x.message)}};
$('productForm').onsubmit=async e=>{e.preventDefault();try{await api('/api/admin/products',{method:'POST',body:new FormData(e.target)});e.target.reset();await loadProducts()}catch(x){alert(x.message)}};

async function loadProducts(){
  const data=await api('/api/admin/products'); const box=$('products'); box.innerHTML='';
  if(!data.length){box.innerHTML='<p class="small">Товаров пока нет.</p>';return;}
  data.forEach(p=>{
    const row=document.createElement('div');row.className='row';
    row.innerHTML=`${p.image?`<img src="${p.image}">`:''}<div class="grow"><b>${esc(p.name)}</b><div class="small">${esc(p.category_name)} · ${Number(p.price).toFixed(2)} ₽</div><div>${esc(p.description||'')}</div></div><div class="actions"><button class="danger">Удалить</button></div>`;
    row.querySelector('.danger').onclick=async()=>{if(!confirm('Удалить товар?'))return;try{await api('/api/admin/products/'+p.id,{method:'DELETE'});await loadProducts()}catch(e){alert(e.message)}};
    box.appendChild(row);
  });
}
function esc(v){return String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')}

api('/api/admin/categories').then(()=>{showPanel();loadAll()}).catch(()=>showLogin());
