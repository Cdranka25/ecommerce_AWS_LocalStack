// PEDIDOS

let autoRefreshInterval = null;
let pedidosAbertos      = new Set();

async function carregarPedidos() {
  if (!token) {
    document.getElementById('lista-pedidos').innerHTML =
      '<div class="empty"><div class="empty-icon">?</div><div class="empty-text">Faca login para ver seus pedidos.</div></div>';
    _pararAutoRefresh();
    return;
  }

  try {
    const pedidos = await apiFetch('/pedidos', { headers: authHeader() });
    _renderMetricas(pedidos);
    _renderLista(pedidos);
    _gerenciarAutoRefresh(pedidos);
  } catch (e) {
    document.getElementById('lista-pedidos').innerHTML =
      `<div class="empty"><div class="empty-icon">!</div><div class="empty-text">${e.message}</div></div>`;
  }
}

function _renderMetricas(pedidos) {
  const total      = pedidos.reduce((s, p) => s + (p.total || 0), 0);
  const pendentes  = pedidos.filter(p => p.status === 'PENDENTE').length;
  const transito   = pedidos.filter(p => p.status === 'EM_TRANSITO').length;
  const concluidos = pedidos.filter(p => p.status === 'CONCLUIDO').length;

  document.getElementById('metricas').innerHTML = `
    <div class="metrica-card">
      <div class="metrica-valor">${pedidos.length}</div>
      <div class="metrica-label">Total de pedidos</div>
    </div>
    <div class="metrica-card">
      <div class="metrica-valor" style="color:var(--green)">${R(total)}</div>
      <div class="metrica-label">Valor total</div>
    </div>
    <div class="metrica-card">
      <div class="metrica-valor" style="color:var(--amber)">${pendentes}</div>
      <div class="metrica-label">Pendentes</div>
    </div>
    <div class="metrica-card">
      <div class="metrica-valor" style="color:var(--accent)">${transito}</div>
      <div class="metrica-label">Em transito</div>
    </div>
    <div class="metrica-card">
      <div class="metrica-valor" style="color:var(--green)">${concluidos}</div>
      <div class="metrica-label">Concluidos</div>
    </div>
  `;
}

function _renderLista(pedidos) {
  const lista = document.getElementById('lista-pedidos');

  if (!pedidos.length) {
    lista.innerHTML =
      '<div class="empty"><div class="empty-icon">?</div><div class="empty-text">Nenhum pedido ainda.</div>' +
      '<button class="btn btn-primary" style="margin-top:1rem" onclick="showPage(\'produtos\')">Comprar agora</button></div>';
    return;
  }

  lista.innerHTML = pedidos.map(p => {
    const aberto = pedidosAbertos.has(p.id);
    return `
      <div class="pedido-card" id="ped-${p.id}">
        <div class="pedido-header">
          <div>
            <div class="pedido-id">#${p.id.slice(0, 8).toUpperCase()}</div>
            <div class="pedido-nome">${p.produto_nome} x ${p.quantidade}</div>
          </div>
          <span class="status-badge status-${p.status}">${p.status.replace('_', ' ')}</span>
        </div>
        <div style="font-size:.8rem;color:var(--muted)">
          ${p.frete_servico || 'PAC'} - ${p.endereco_cidade || ''}/${p.endereco_uf || ''} - ${p.frete_prazo || '?'} dias uteis
        </div>
        <div class="pedido-footer">
          <div class="pedido-total">${R(p.total)}</div>
          <div style="font-size:.8rem;color:var(--muted)">${new Date(p.criado_em).toLocaleString('pt-BR')}</div>
          <button class="btn" style="font-size:11px;padding:5px 10px"
            onclick="toggleEventos('${p.id}')">
            ${aberto ? 'Fechar' : 'Ver detalhes'}
          </button>
        </div>
        <div class="eventos-lista" id="ev-${p.id}" style="display:${aberto ? '' : 'none'}">
          ${aberto ? '<div class="loading-overlay" style="padding:1rem"><div class="spinner"></div></div>' : ''}
        </div>
      </div>
    `;
  }).join('');

  // Recarrega eventos dos cards que estavam abertos
  pedidosAbertos.forEach(id => _carregarEventos(id));
}

async function toggleEventos(pedidoId) {
  const div = document.getElementById('ev-' + pedidoId);
  if (!div) return;

  if (div.style.display !== 'none') {
    div.style.display = 'none';
    pedidosAbertos.delete(pedidoId);
    const btn = div.previousElementSibling?.querySelector('button');
    if (btn) btn.textContent = 'Ver detalhes';
    return;
  }

  div.style.display = '';
  pedidosAbertos.add(pedidoId);
  const btn = div.previousElementSibling?.querySelector('button');
  if (btn) btn.textContent = 'Fechar';
  await _carregarEventos(pedidoId);
}

async function _carregarEventos(pedidoId) {
  const div = document.getElementById('ev-' + pedidoId);
  if (!div || div.style.display === 'none') return;

  div.innerHTML = '<div class="loading-overlay" style="padding:1rem"><div class="spinner"></div></div>';
  try {
    const data = await apiFetch(`/pedidos/${pedidoId}`, { headers: authHeader() });
    const evs  = data.eventos || [];

    if (!evs.length) {
      div.innerHTML = '<p style="color:var(--muted);font-size:.8rem;padding:.5rem 0">Aguardando processamento...</p>';
      return;
    }

    const primeiroTs = new Date(evs[0].criado_em).getTime();
    div.innerHTML = evs.map((e, i) => {
      const ts      = new Date(e.criado_em).getTime();
      const delta   = i === 0 ? '' : `+${((ts - primeiroTs) / 1000).toFixed(1)}s`;
      const cor     = e.status.includes('FALHA') || e.status.includes('RECUS') ? 'var(--red)' : 'var(--green)';
      return `
        <div class="evento">
          <div class="evento-servico">${e.servico}</div>
          <div class="evento-status" style="color:${cor}">${e.status}</div>
          <div class="evento-msg">${e.mensagem || ''}</div>
          ${delta ? `<div class="evento-delta">${delta}</div>` : ''}
        </div>
      `;
    }).join('');
  } catch (e) {
    div.innerHTML = `<p style="color:var(--red);font-size:.8rem">${e.message}</p>`;
  }
}

function _gerenciarAutoRefresh(pedidos) {
  const temAtivos = pedidos.some(p => p.status === 'PENDENTE' || p.status === 'EM_TRANSITO');

  if (temAtivos && !autoRefreshInterval) {
    autoRefreshInterval = setInterval(() => {
      if (document.getElementById('page-pedidos').classList.contains('active')) {
        carregarPedidos();
      }
    }, 5000);
    _mostrarIndicadorRefresh(true);
  } else if (!temAtivos && autoRefreshInterval) {
    _pararAutoRefresh();
  }
}

function _pararAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
    _mostrarIndicadorRefresh(false);
  }
}

function _mostrarIndicadorRefresh(ativo) {
  const el = document.getElementById('refresh-indicator');
  if (el) el.style.display = ativo ? '' : 'none';
}
