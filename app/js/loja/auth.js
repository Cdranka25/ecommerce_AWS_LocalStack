// ═══════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════
function switchAuthTab(tab){
  document.getElementById('form-login').style.display    = tab==='login'    ? '' : 'none';
  document.getElementById('form-register').style.display = tab==='register' ? '' : 'none';
  document.getElementById('tab-login').className    = 'auth-tab'+(tab==='login'   ?' active':'');
  document.getElementById('tab-register').className = 'auth-tab'+(tab==='register'?' active':'');
  document.getElementById('auth-msg').innerHTML = '';
}

async function doLogin(){
  const email = document.getElementById('login-email').value.trim();
  const senha = document.getElementById('login-senha').value;
  document.getElementById('auth-msg').innerHTML = '';
  try {
    const data = await apiFetch('/auth/login',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email, senha})
    });
    token    = data.access_token;
    userInfo = data.user;
    localStorage.setItem('token', token);
    localStorage.setItem('refreshToken', data.refresh_token);
    localStorage.setItem('userInfo', JSON.stringify(userInfo));
    atualizarNavAuth();
    toast(`Bem-vindo, ${userInfo.nome || userInfo.email}! 👋`, 'success');
    showPage('produtos');
  } catch(e){
    document.getElementById('auth-msg').innerHTML = `<div class="auth-error">⚠️ ${e.message}</div>`;
  }
}

async function doRegister(){
  const nome  = document.getElementById('reg-nome').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const senha = document.getElementById('reg-senha').value;
  document.getElementById('auth-msg').innerHTML = '';
  try {
    await apiFetch('/auth/register',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nome, email, senha})
    });
    document.getElementById('auth-msg').innerHTML = `<div class="auth-success">✅ Conta criada! Faça login.</div>`;
    switchAuthTab('login');
    document.getElementById('login-email').value = email;
  } catch(e){
    document.getElementById('auth-msg').innerHTML = `<div class="auth-error">⚠️ ${e.message}</div>`;
  }
}

async function logout(){
  try{ await apiFetch('/auth/logout',{method:'POST',headers:authHeader()}) } catch(e){}
  token=null; userInfo=null;
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('userInfo');
  atualizarNavAuth();
  showPage('produtos');
  toast('Logout realizado.');
}

function atualizarNavAuth(){
  const logado = !!token;
  document.getElementById('btn-auth').style.display      = logado ? 'none' : '';
  document.getElementById('btn-logout').style.display    = logado ? '' : 'none';
  document.getElementById('nav-enderecos').style.display = logado ? '' : 'none';
  document.getElementById('nav-pedidos').style.display   = logado ? '' : 'none';
  document.getElementById('nav-carrinho').style.display  = logado ? '' : 'none';
  document.getElementById('nav-user').textContent        = logado ? (userInfo?.nome || userInfo?.email || '') : '';
}
