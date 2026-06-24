// ═══════════════════════════════════════════════════════════
//  CARRINHO
// ═══════════════════════════════════════════════════════════
function addToCart(prodId, qtd){
  const p = produtos.find(x=>x.id===prodId);
  if(!p) return;
  const idx = carrinho.findIndex(x=>x.id===prodId);
  if(idx>=0) carrinho[idx].qtd = Math.min(p.estoque, carrinho[idx].qtd+qtd);
  else        carrinho.push({id:p.id, nome:p.nome, preco:p.preco, qtd, estoque:p.estoque, imagem_url:p.imagem_url});
  salvarCarrinho();
  toast(`${p.nome} adicionado ao carrinho 🛒`, 'success');
}

function salvarCarrinho(){
  localStorage.setItem('carrinho', JSON.stringify(carrinho));
  document.getElementById('cart-badge').textContent = carrinho.reduce((s,i)=>s+i.qtd,0);
}

function renderCarrinho(){
  const itemsDiv    = document.getElementById('cart-items');
  const checkoutDiv = document.getElementById('cart-checkout');
  const emptyDiv    = document.getElementById('cart-empty');

  if(!carrinho.length){
    itemsDiv.innerHTML=''; checkoutDiv.style.display='none'; emptyDiv.style.display='';
    return;
  }
  emptyDiv.style.display='none';
  checkoutDiv.style.display='';

  itemsDiv.innerHTML = carrinho.map((item,i) => `
    <div class="cart-item">
      <div style="width:48px;height:48px;border-radius:8px;overflow:hidden;background:var(--bg3);
        flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:24px">
        ${item.imagem_url
          ? `<img src="${item.imagem_url}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentNode.textContent='🖥️'">`
          : '🖥️'}
      </div>
      <div class="cart-item-info">
        <div class="cart-item-nome">${item.nome}</div>
        <div class="cart-item-preco">${R(item.preco)} × ${item.qtd} = <strong style="color:var(--green)">${R(item.preco*item.qtd)}</strong></div>
      </div>
      <div class="cart-qty">
        <button class="qty-btn" onclick="alterarQtd(${i},-1)">−</button>
        <span>${item.qtd}</span>
        <button class="qty-btn" onclick="alterarQtd(${i},1)">+</button>
        <button class="qty-btn" onclick="removerItem(${i})" style="color:var(--red);margin-left:4px">✕</button>
      </div>
    </div>
  `).join('');

  atualizarResumo();
  if(token) carregarEnderecoCarrinho();
  else document.getElementById('cart-enderecos').innerHTML =
    '<p style="color:var(--muted);font-size:.875rem">Faça <a href="#" onclick="showPage(\'auth\')" style="color:var(--accent)">login</a> para selecionar endereço.</p>';
}

function alterarQtd(i, d){
  carrinho[i].qtd = Math.max(1, Math.min(carrinho[i].estoque, carrinho[i].qtd+d));
  salvarCarrinho(); renderCarrinho();
}
function removerItem(i){ carrinho.splice(i,1); salvarCarrinho(); renderCarrinho(); toast('Item removido.') }

function atualizarResumo(){
  const sub = carrinho.reduce((s,i)=>s+i.preco*i.qtd, 0);
  document.getElementById('resumo-subtotal').textContent = R(sub);
  if(fretesSelecionado){
    const total = sub + fretesSelecionado.valor;
    document.getElementById('resumo-frete-label').textContent = `Frete (${fretesSelecionado.servico})`;
    document.getElementById('resumo-frete').textContent = R(fretesSelecionado.valor);
    document.getElementById('resumo-total').textContent  = R(total);
    if(fretesSelecionado.simulado)
      document.getElementById('resumo-frete').innerHTML += ' <span style="font-size:10px;color:var(--amber)">(estimado)</span>';
  } else {
    document.getElementById('resumo-frete').textContent = '—';
    document.getElementById('resumo-total').textContent = '—';
  }
}

async function carregarEnderecoCarrinho(){
  try{
    const ends = await apiFetch('/enderecos',{headers:authHeader()});
    const div  = document.getElementById('cart-enderecos');
    if(!ends.length){
      div.innerHTML = '<p style="color:var(--muted);font-size:.875rem">Nenhum endereço cadastrado.</p>';
      return;
    }
    div.innerHTML = ends.map(e=>`
      <div class="end-card ${enderecoSelecionado?.id===e.id?'selected':''}"
        onclick="selecionarEndereco(${JSON.stringify(e).replace(/"/g,'&quot;')})">
        <div class="end-apelido">${e.apelido} ${e.principal?'<span class="badge-principal">Principal</span>':''}</div>
        <div class="end-logr">${e.logradouro}, ${e.numero}${e.complemento?' - '+e.complemento:''}<br>
        ${e.bairro} — ${e.cidade}/${e.uf}<br>CEP: ${e.cep}</div>
      </div>
    `).join('');

    // Seleciona o principal automaticamente se nenhum ainda selecionado
    if(!enderecoSelecionado){
      const principal = ends.find(e=>e.principal) || ends[0];
      if(principal) selecionarEndereco(principal);
    }
  } catch(e){ console.warn(e) }
}

async function selecionarEndereco(end){
  enderecoSelecionado = end;
  fretesSelecionado = null;
  document.getElementById('frete-resultado').innerHTML =
    '<div class="loading-overlay"><div class="spinner"></div> Calculando frete...</div>';
  renderCarrinho(); // rerender para atualizar seleção

  try{
    const data = await apiFetch(`/frete?cep=${end.cep}`);
    const opcoes = data.opcoes_frete;
    if(!opcoes.length){
      document.getElementById('frete-resultado').innerHTML = '<p style="color:var(--red);font-size:.875rem">Frete indisponível para este CEP.</p>';
      return;
    }
    // Seleciona primeiro automaticamente
    fretesSelecionado = opcoes[0];
    document.getElementById('frete-resultado').innerHTML = `
      <div class="frete-box">
        <div class="frete-titulo">Selecione o serviço</div>
        ${opcoes.map((o,i)=>`
          <label class="frete-opcao">
            <input type="radio" name="frete" value="${i}" ${i===0?'checked':''}
              onchange="fretesSelecionado=${JSON.stringify(o).replace(/"/g,'&quot;')};atualizarResumo()">
            <div>
              <div class="frete-nome">${o.servico}</div>
              <div class="frete-prazo">Prazo estimado: ${o.prazo_dias} dias úteis${o.simulado?'<span class="frete-simulado">(estimado)</span>':''}</div>
            </div>
            <div class="frete-valor">${R(o.valor)}</div>
          </label>
        `).join('')}
      </div>`;
    atualizarResumo();
  } catch(e){
    document.getElementById('frete-resultado').innerHTML = `<p style="color:var(--red);font-size:.875rem">Erro ao calcular frete: ${e.message}</p>`;
  }
}

async function finalizarPedido(){
  if(!token){ toast('Faça login para continuar.','error'); showPage('auth'); return; }
  if(!carrinho.length){ toast('Carrinho vazio.','error'); return; }
  if(!enderecoSelecionado){ toast('Selecione um endereço.','error'); return; }
  if(!fretesSelecionado){ toast('Aguarde o cálculo do frete.','error'); return; }
  if(carrinho.length > 1){ toast('Por ora, finalize um produto por vez.','error'); return; }

  const item  = carrinho[0];
  const forma = document.querySelector('input[name="pagto"]:checked').value;
  const btn   = document.getElementById('btn-finalizar');
  btn.disabled = true; btn.textContent = 'Processando...';

  try{
    const data = await apiFetch('/pedidos',{
      method:'POST', headers:authHeader(),
      body: JSON.stringify({
        produto_id:      item.id,
        quantidade:      item.qtd,
        endereco_id:     enderecoSelecionado.id,
        forma_pagamento: forma,
      })
    });
    carrinho=[]; salvarCarrinho();
    enderecoSelecionado=null; fretesSelecionado=null;
    toast(`Pedido ${data.pedido_id.slice(0,8)}... criado! Total: ${R(data.total)} 🎉`, 'success');
    showPage('pedidos');
  } catch(e){
    toast(`Erro: ${e.message}`, 'error');
  } finally {
    btn.disabled=false; btn.textContent='✅ Finalizar Pedido';
  }
}
