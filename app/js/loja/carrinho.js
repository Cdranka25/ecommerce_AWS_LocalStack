// CARRINHO

function addToCart(prodId, qtd) {
  const p = produtos.find(x => x.id === prodId);
  if (!p) return;
  const idx = carrinho.findIndex(x => x.id === prodId);
  if (idx >= 0) {
    carrinho[idx].qtd = Math.min(p.estoque, carrinho[idx].qtd + qtd);
  } else {
    carrinho.push({ id: p.id, nome: p.nome, preco: p.preco, qtd, estoque: p.estoque, imagem_url: p.imagem_url });
  }
  salvarCarrinho();
  toast(`${p.nome} adicionado ao carrinho`, 'success');
}

function salvarCarrinho() {
  localStorage.setItem('carrinho', JSON.stringify(carrinho));
  document.getElementById('cart-badge').textContent = carrinho.reduce((s, i) => s + i.qtd, 0);
}

function renderCarrinho() {
  const itemsDiv    = document.getElementById('cart-items');
  const checkoutDiv = document.getElementById('cart-checkout');
  const emptyDiv    = document.getElementById('cart-empty');

  if (!carrinho.length) {
    itemsDiv.innerHTML        = '';
    checkoutDiv.style.display = 'none';
    emptyDiv.style.display    = '';
    return;
  }

  emptyDiv.style.display    = 'none';
  checkoutDiv.style.display = '';

  itemsDiv.innerHTML = carrinho.map((item, i) => `
    <div class="cart-item">
      <div style="width:48px;height:48px;border-radius:8px;overflow:hidden;background:var(--bg3);
        flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:24px">
        ${item.imagem_url
          ? `<img src="${item.imagem_url}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentNode.innerHTML='?'">`
          : '?'}
      </div>
      <div class="cart-item-info">
        <div class="cart-item-nome">${item.nome}</div>
        <div class="cart-item-preco">${R(item.preco)} x ${item.qtd} = <strong style="color:var(--green)">${R(item.preco * item.qtd)}</strong></div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px">${item.estoque} em estoque</div>
        ${item.semEstoque ? '<div style="font-size:11px;color:var(--red);font-weight:600">Estoque insuficiente</div>' : ''}
      </div>
      <div class="cart-qty">
        <button class="qty-btn" onclick="alterarQtd(${i}, -1)">-</button>
        <span>${item.qtd}</span>
        <button class="qty-btn" onclick="alterarQtd(${i}, 1)" ${item.qtd >= item.estoque ? 'disabled style="opacity:.3"' : ''}>+</button>
        <button class="qty-btn" onclick="removerItem(${i})" style="color:var(--red);margin-left:4px">x</button>
      </div>
    </div>
  `).join('');

  atualizarResumo();

  if (token) {
    carregarEnderecoCarrinho();
  } else {
    document.getElementById('cart-enderecos').innerHTML =
      '<p style="color:var(--muted);font-size:.875rem">Faca <a href="#" onclick="showPage(\'auth\')" style="color:var(--accent)">login</a> para selecionar endereco.</p>';
  }
}

function alterarQtd(i, d) {
  carrinho[i].qtd        = Math.max(1, Math.min(carrinho[i].estoque, carrinho[i].qtd + d));
  carrinho[i].semEstoque = false;
  salvarCarrinho();
  renderCarrinho();
}

function removerItem(i) {
  carrinho.splice(i, 1);
  salvarCarrinho();
  renderCarrinho();
  toast('Item removido.');
}

function atualizarResumo() {
  const itensValidos = carrinho.filter(i => !i.semEstoque);
  const sub          = itensValidos.reduce((s, i) => s + i.preco * i.qtd, 0);

  document.getElementById('resumo-subtotal').textContent = R(sub);

  if (fretesSelecionado) {
    const total = sub + fretesSelecionado.valor;
    document.getElementById('resumo-frete-label').textContent = `Frete (${fretesSelecionado.servico})`;
    document.getElementById('resumo-frete').textContent       = R(fretesSelecionado.valor);
    document.getElementById('resumo-total').textContent       = R(total);
    if (fretesSelecionado.simulado) {
      document.getElementById('resumo-frete').innerHTML +=
        ' <span style="font-size:10px;color:var(--amber)">(estimado)</span>';
    }
  } else {
    document.getElementById('resumo-frete').textContent = '-';
    document.getElementById('resumo-total').textContent = '-';
  }
}

async function carregarEnderecoCarrinho() {
  try {
    const ends = await apiFetch('/enderecos', { headers: authHeader() });
    const div  = document.getElementById('cart-enderecos');

    if (!ends.length) {
      div.innerHTML = '<p style="color:var(--muted);font-size:.875rem">Nenhum endereco cadastrado.</p>';
      return;
    }

    div.innerHTML = ends.map(e => `
      <div class="end-card ${enderecoSelecionado?.id === e.id ? 'selected' : ''}"
        onclick="selecionarEndereco(${JSON.stringify(e).replace(/"/g, '&quot;')})">
        <div class="end-apelido">${e.apelido} ${e.principal ? '<span class="badge-principal">Principal</span>' : ''}</div>
        <div class="end-logr">${e.logradouro}, ${e.numero}${e.complemento ? ' - ' + e.complemento : ''}<br>
          ${e.bairro} - ${e.cidade}/${e.uf}<br>CEP: ${e.cep}</div>
      </div>
    `).join('');

    if (!enderecoSelecionado) {
      const principal = ends.find(e => e.principal) || ends[0];
      if (principal) selecionarEndereco(principal);
    }
  } catch (e) {
    console.warn(e);
  }
}

async function selecionarEndereco(end) {
  enderecoSelecionado = end;
  fretesSelecionado   = null;
  document.getElementById('frete-resultado').innerHTML =
    '<div class="loading-overlay"><div class="spinner"></div> Calculando frete...</div>';
  renderCarrinho();

  try {
    const data   = await apiFetch(`/frete?cep=${end.cep}`);
    const opcoes = data.opcoes_frete;

    if (!opcoes.length) {
      document.getElementById('frete-resultado').innerHTML =
        '<p style="color:var(--red);font-size:.875rem">Frete indisponivel para este CEP.</p>';
      return;
    }

    fretesSelecionado = opcoes[0];
    document.getElementById('frete-resultado').innerHTML = `
      <div class="frete-box">
        <div class="frete-titulo">Selecione o servico</div>
        ${opcoes.map((o, i) => `
          <label class="frete-opcao">
            <input type="radio" name="frete" value="${i}" ${i === 0 ? 'checked' : ''}
              onchange="fretesSelecionado=${JSON.stringify(o).replace(/"/g, '&quot;')};atualizarResumo()">
            <div>
              <div class="frete-nome">${o.servico}</div>
              <div class="frete-prazo">Prazo estimado: ${o.prazo_dias} dias uteis${o.simulado ? '<span class="frete-simulado">(estimado)</span>' : ''}</div>
            </div>
            <div class="frete-valor">${R(o.valor)}</div>
          </label>
        `).join('')}
      </div>`;
    atualizarResumo();
  } catch (e) {
    document.getElementById('frete-resultado').innerHTML =
      `<p style="color:var(--red);font-size:.875rem">Erro ao calcular frete: ${e.message}</p>`;
  }
}

async function verificarEstoqueCarrinho() {
  const resultados = await Promise.all(
    carrinho.map(item => apiFetch(`/produtos/${item.id}`).catch(() => null))
  );
  let algumSemEstoque = false;
  resultados.forEach((prod, i) => {
    if (!prod) return;
    carrinho[i].estoque    = prod.estoque;
    carrinho[i].semEstoque = prod.estoque < carrinho[i].qtd;
    if (carrinho[i].semEstoque) algumSemEstoque = true;
  });
  return algumSemEstoque;
}

async function finalizarPedido() {
  if (!token)               { toast('Faca login para continuar.', 'error'); showPage('auth'); return; }
  if (!carrinho.length)     { toast('Carrinho vazio.', 'error'); return; }
  if (!enderecoSelecionado) { toast('Selecione um endereco.', 'error'); return; }
  if (!fretesSelecionado)   { toast('Aguarde o calculo do frete.', 'error'); return; }

  const btn        = document.getElementById('btn-finalizar');
  btn.disabled     = true;
  btn.textContent  = 'Verificando estoque...';

  const semEstoque = await verificarEstoqueCarrinho();
  if (semEstoque) {
    renderCarrinho();
    toast('Alguns itens estao sem estoque suficiente. Ajuste as quantidades.', 'error');
    btn.disabled    = false;
    btn.textContent = 'Finalizar Pedido';
    return;
  }

  const forma          = document.querySelector('input[name="pagto"]:checked').value;
  const itensValidos   = carrinho.filter(i => !i.semEstoque);
  const pedidosCriados = [];
  const erros          = [];

  btn.textContent = `Criando ${itensValidos.length} pedido(s)...`;

  // Envia todos os pedidos em paralelo
  const resultados = await Promise.all(
    itensValidos.map(item =>
      apiFetch('/pedidos', {
        method:  'POST',
        headers: authHeader(),
        body:    JSON.stringify({
          produto_id:      item.id,
          quantidade:      item.qtd,
          endereco_id:     enderecoSelecionado.id,
          forma_pagamento: forma,
        }),
      }).catch(e => ({ _erro: true, msg: `${item.nome}: ${e.message}` }))
    )
  );

  resultados.forEach(r => {
    if (r._erro) erros.push(r.msg);
    else         pedidosCriados.push(r);
  });

  btn.disabled    = false;
  btn.textContent = 'Finalizar Pedido';

  if (pedidosCriados.length > 0) {
    const total         = pedidosCriados.reduce((s, p) => s + p.total, 0);
    carrinho            = [];
    enderecoSelecionado = null;
    fretesSelecionado   = null;
    salvarCarrinho();
    toast(`${pedidosCriados.length} pedido(s) criado(s)! Total: ${R(total)}`, 'success');
    showPage('confirmacao');
    renderConfirmacao(pedidosCriados);
  }

  if (erros.length > 0) {
    toast(`Erro: ${erros.join(' | ')}`, 'error');
  }
}

function renderConfirmacao(pedidos) {
  const total = pedidos.reduce((s, p) => s + p.total, 0);
  document.getElementById('confirmacao-content').innerHTML = `
    <div style="text-align:center;padding:2rem 0">
      <div style="font-size:3rem;margin-bottom:1rem">?</div>
      <h2 style="color:#fff;margin-bottom:.5rem">Pedido realizado!</h2>
      <p style="color:var(--muted);margin-bottom:2rem">
        ${pedidos.length} pedido(s) criado(s) com sucesso.<br>
        Os servicos de pagamento, estoque e logistica estao sendo processados.
      </p>
    </div>
    <div style="display:grid;gap:.75rem;margin-bottom:2rem">
      ${pedidos.map(p => `
        <div style="background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:1rem;display:flex;justify-content:space-between;align-items:center">
          <div>
            <div style="font-size:.75rem;color:var(--muted);font-family:monospace">#${p.pedido_id.slice(0,8).toUpperCase()}</div>
            <div style="font-weight:600;color:#fff">${p.entrega}</div>
            <div style="font-size:.8rem;color:var(--muted)">${p.forma_pagamento.toUpperCase()} - Frete ${p.frete?.servico || ''}</div>
          </div>
          <div style="font-size:1.1rem;font-weight:700;color:var(--green)">${R(p.total)}</div>
        </div>
      `).join('')}
    </div>
    <div style="text-align:center;padding:1rem;background:var(--bg2);border-radius:10px;margin-bottom:1.5rem">
      <div style="color:var(--muted);font-size:.875rem">Total geral</div>
      <div style="font-size:1.5rem;font-weight:700;color:var(--green)">${R(total)}</div>
    </div>
    <div style="display:flex;gap:.75rem;justify-content:center">
      <button class="btn btn-primary" onclick="showPage('pedidos')">Ver meus pedidos</button>
      <button class="btn" onclick="showPage('produtos')">Continuar comprando</button>
    </div>
  `;
}
