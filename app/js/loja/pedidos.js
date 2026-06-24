// ═══════════════════════════════════════════════════════════
//  PEDIDOS
// ═══════════════════════════════════════════════════════════
async function carregarPedidos(){
  if(!token){
    document.getElementById('lista-pedidos').innerHTML = '<div class="empty"><div class="empty-icon">🔒</div><div class="empty-text">Faça login para ver seus pedidos.</div></div>';
    return;
  }
  document.getElementById('lista-pedidos').innerHTML = '<div class="loading-overlay"><div class="spinner"></div> Carregando pedidos...</div>';
  try{
    const pedidos = await apiFetch('/pedidos',{headers:authHeader()});
    if(!pedidos.length){
      document.getElementById('lista-pedidos').innerHTML = '<div class="empty"><div class="empty-icon">📦</div><div class="empty-text">Nenhum pedido ainda.</div><button class="btn btn-primary" style="margin-top:1rem" onclick="showPage(\'produtos\')">Comprar agora</button></div>';
      return;
    }
    document.getElementById('lista-pedidos').innerHTML = pedidos.map(p=>`
      <div class="pedido-card" id="ped-${p.id}">
        <div class="pedido-header">
          <div>
            <div class="pedido-id">#${p.id.slice(0,8).toUpperCase()}</div>
            <div class="pedido-nome">${p.produto_nome} × ${p.quantidade}</div>
          </div>
          <span class="status-badge status-${p.status}">${p.status.replace('_',' ')}</span>
        </div>
        <div style="font-size:.8rem;color:var(--muted)">
          ${p.frete_servico||'PAC'} • ${p.endereco_cidade||''}/${p.endereco_uf||''} • ${p.frete_prazo||'?'} dias úteis
        </div>
        <div class="pedido-footer">
          <div class="pedido-total">${R(p.total)}</div>
          <div style="font-size:.8rem;color:var(--muted)">${new Date(p.criado_em).toLocaleString('pt-BR')}</div>
          <button class="btn" style="font-size:11px;padding:5px 10px" onclick="carregarEventos('${p.id}')">Ver detalhes</button>
        </div>
        <div class="eventos-lista" id="ev-${p.id}" style="display:none"></div>
      </div>
    `).join('');
  } catch(e){
    document.getElementById('lista-pedidos').innerHTML = `<div class="empty"><div class="empty-icon">⚠️</div><div class="empty-text">${e.message}</div></div>`;
  }
}

async function carregarEventos(pedidoId){
  const div = document.getElementById('ev-'+pedidoId);
  if(div.style.display!=='none'){ div.style.display='none'; return; }
  div.style.display='';
  div.innerHTML = '<div class="loading-overlay" style="padding:1rem"><div class="spinner"></div></div>';
  try{
    const data = await apiFetch(`/pedidos/${pedidoId}`,{headers:authHeader()});
    const evs  = data.eventos || [];
    div.innerHTML = evs.length
      ? evs.map(e=>`
          <div class="evento">
            <div class="evento-servico">${e.servico}</div>
            <div class="evento-status" style="color:${e.status.includes('FALHA')||e.status.includes('RECUS')?'var(--red)':'var(--green)'}">${e.status}</div>
            <div class="evento-msg">${e.mensagem||''}</div>
          </div>
        `).join('')
      : '<p style="color:var(--muted);font-size:.8rem;padding:.5rem 0">Aguardando processamento pelos consumidores...</p>';
  } catch(e){ div.innerHTML = `<p style="color:var(--red);font-size:.8rem">${e.message}</p>` }
}
