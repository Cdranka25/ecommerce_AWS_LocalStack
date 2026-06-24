// ═══════════════════════════════════════════════════════════
//  ENDEREÇOS
// ═══════════════════════════════════════════════════════════
async function carregarEnderecos(){
  if(!token){ document.getElementById('lista-enderecos').innerHTML='<p style="color:var(--muted)">Faça login para ver seus endereços.</p>'; return; }
  try{
    const ends = await apiFetch('/enderecos',{headers:authHeader()});
    const div  = document.getElementById('lista-enderecos');
    if(!ends.length){ div.innerHTML='<p style="color:var(--muted);margin-bottom:1rem">Nenhum endereço cadastrado ainda.</p>'; return; }
    div.innerHTML = ends.map(e=>`
      <div class="end-card">
        <div class="end-apelido">${e.apelido} ${e.principal?'<span class="badge-principal">Principal</span>':''}</div>
        <div class="end-logr">${e.logradouro}, ${e.numero}${e.complemento?' — '+e.complemento:''}<br>
          ${e.bairro} — ${e.cidade}/${e.uf}<br>CEP: ${e.cep}</div>
        <button class="end-delete" onclick="deletarEndereco('${e.id}')" title="Remover">✕</button>
      </div>
    `).join('');
  } catch(e){ toast(e.message,'error') }
}

async function buscarCEP(){
  const cep = document.getElementById('end-cep').value.replace(/\D/g,'');
  if(cep.length!==8){ toast('CEP deve ter 8 dígitos','error'); return; }

  const btnBuscar = document.querySelector('[onclick="buscarCEP()"]');
  if(btnBuscar){ btnBuscar.textContent='Buscando...'; btnBuscar.disabled=true; }

  let d = null;

  // Tenta BrasilAPI primeiro (mais rápida)
  try {
    const r = await fetch(`https://brasilapi.com.br/api/cep/v2/${cep}`);
    if(r.ok){
      const data = await r.json();
      if(data.city){
        d = {
          logradouro: data.street || '',
          bairro:     data.neighborhood || '',
          localidade: data.city || '',
          uf:         data.state || '',
        };
      }
    }
  } catch(e){}

  // Fallback: ViaCEP
  if(!d){
    try {
      const r = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      if(r.ok){
        const data = await r.json();
        if(!data.erro) d = data;
      }
    } catch(e){}
  }

  if(btnBuscar){ btnBuscar.textContent='Buscar'; btnBuscar.disabled=false; }

  if(!d){ toast('CEP não encontrado','error'); return; }

  document.getElementById('end-logr').value   = d.logradouro || '';
  document.getElementById('end-bairro').value = d.bairro     || '';
  document.getElementById('end-cidade').value = d.localidade || '';
  document.getElementById('end-uf').value     = d.uf         || '';
  document.getElementById('end-numero').focus();
  toast('Endereço preenchido ✅','success');
}

function formatCEP(el){
  let v = el.value.replace(/\D/g,'');
  if(v.length>5) v = v.slice(0,5)+'-'+v.slice(5,8);
  el.value = v;
}

async function salvarEndereco(){
  if(!token){ toast('Faça login primeiro.','error'); return; }
  const body = {
    apelido:    document.getElementById('end-apelido').value.trim() || 'Casa',
    cep:        document.getElementById('end-cep').value.replace(/\D/g,''),
    logradouro: document.getElementById('end-logr').value.trim(),
    numero:     document.getElementById('end-numero').value.trim(),
    complemento:document.getElementById('end-comp').value.trim(),
    bairro:     document.getElementById('end-bairro').value.trim(),
    cidade:     document.getElementById('end-cidade').value.trim(),
    uf:         document.getElementById('end-uf').value.trim().toUpperCase(),
    principal:  document.getElementById('end-principal').checked,
  };
  if(!body.cep||!body.logradouro||!body.numero||!body.cidade){
    toast('Preencha todos os campos obrigatórios.','error'); return;
  }
  try{
    await apiFetch('/enderecos',{method:'POST',headers:authHeader(),body:JSON.stringify(body)});
    toast('Endereço salvo! ✅','success');
    ['apelido','cep','logr','numero','comp','bairro','cidade','uf'].forEach(f=>{
      const el = document.getElementById('end-'+f);
      if(el) el.value='';
    });
    document.getElementById('end-principal').checked=false;
    carregarEnderecos();
  } catch(e){ toast(e.message,'error') }
}

async function deletarEndereco(id){
  if(!confirm('Remover este endereço?')) return;
  try{
    await apiFetch(`/enderecos/${id}`,{method:'DELETE',headers:authHeader()});
    toast('Endereço removido.','success');
    carregarEnderecos();
  } catch(e){ toast(e.message,'error') }
}
