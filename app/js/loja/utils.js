// ═══════════════════════════════════════════════════════════
//  UTILITÁRIOS
// ═══════════════════════════════════════════════════════════
function R(v){ return `R$ ${Number(v).toFixed(2).replace('.',',')}` }
function toast(msg, tipo=''){
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = `toast ${tipo} show`;
  clearTimeout(t._t);
  t._t = setTimeout(() => t.className='toast', 3200);
}
function showPage(id){
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-'+id).classList.add('active');
  if(id==='produtos')   carregarProdutos();
  if(id==='carrinho')   renderCarrinho();
  if(id==='enderecos')  carregarEnderecos();
  if(id==='pedidos')    carregarPedidos();
}
function authHeader(){ return {'Authorization':`Bearer ${token}`,'Content-Type':'application/json'} }

async function renovarToken() {
  const refreshToken = localStorage.getItem('refreshToken');
  if (!refreshToken) return false;
  try {
    const r = await fetch(API + '/auth/refresh', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({refresh_token: refreshToken})
    });
    if (!r.ok) return false;
    const data = await r.json();
    token = data.access_token;
    localStorage.setItem('token', token);
    if (data.refresh_token) localStorage.setItem('refreshToken', data.refresh_token);
    return true;
  } catch(e) {
    return false;
  }
}

async function apiFetch(path, opts={}){
  const r = await fetch(API+path, opts);

  // Só tenta renovar token se a requisição era autenticada (tinha Bearer token)
  const eraAutenticada = opts.headers && opts.headers['Authorization'];

  if (r.status === 401 && eraAutenticada) {
    const renovado = await renovarToken();
    if (renovado) {
      opts.headers['Authorization'] = `Bearer ${token}`;
      const r2 = await fetch(API+path, opts);
      if (!r2.ok) {
        const err = await r2.json().catch(()=>({detail:'Erro desconhecido'}));
        throw new Error(err.detail || r2.statusText);
      }
      return r2.json();
    } else {
      token=null; userInfo=null;
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('userInfo');
      atualizarNavAuth();
      toast('Sessão expirada. Faça login novamente.','error');
      showPage('auth');
      throw new Error('Sessão expirada.');
    }
  }

  if(!r.ok){
    const err = await r.json().catch(()=>({detail:'Erro desconhecido'}));
    throw new Error(err.detail || r.statusText);
  }
  return r.json();
}
