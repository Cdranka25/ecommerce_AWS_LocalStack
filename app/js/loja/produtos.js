// ═══════════════════════════════════════════════════════════
//  PRODUTOS
// ═══════════════════════════════════════════════════════════
let produtos = [];
async function carregarProdutos(){
  const g = document.getElementById('grid-produtos');
  g.innerHTML = '<div class="loading-overlay"><div class="spinner"></div> Carregando...</div>';
  try {
    produtos = await apiFetch('/produtos');
    if(!produtos.length){
      g.innerHTML = '<div class="empty"><div class="empty-icon">📦</div><div class="empty-text">Nenhum produto cadastrado.</div></div>';
      return;
    }
    g.innerHTML = produtos.map(p => `
      <div class="card" onclick="abrirModal('${p.id}')">
        <div class="card-img">
          ${p.imagem_url
            ? `<img src="${p.imagem_url}" alt="${p.nome}" loading="lazy" onerror="this.parentNode.textContent='🖥️'">`
            : '🖥️'}
        </div>
        <div class="card-body">
          <div class="card-categoria">${p.categoria||'Geral'}</div>
          <div class="card-nome">${p.nome}</div>
          <div class="card-desc">${p.descricao||''}</div>
          <div class="card-footer">
            <div class="card-preco">${R(p.preco)}</div>
            <button class="btn-add" ${p.estoque<1?'disabled':''} onclick="event.stopPropagation();addToCart('${p.id}',1)">
              ${p.estoque<1?'Esgotado':'+ Carrinho'}
            </button>
          </div>
        </div>
      </div>
    `).join('');
  } catch(e){
    g.innerHTML = `<div class="empty"><div class="empty-icon">⚠️</div><div class="empty-text">Erro: ${e.message}</div></div>`;
  }
}

function abrirModal(prodId){
  const p = produtos.find(x=>x.id===prodId);
  if(!p) return;
  produtoModal = p; qtdModal = 1;
  document.getElementById('modal-prod-nome').textContent  = p.nome;
  document.getElementById('modal-prod-desc').textContent  = p.descricao||'';
  document.getElementById('modal-prod-preco').textContent = R(p.preco);
  document.getElementById('modal-prod-est').textContent   = `${p.estoque} em estoque`;
  document.getElementById('modal-qtd').textContent        = 1;
  const imgDiv = document.getElementById('modal-prod-img');
  imgDiv.innerHTML = p.imagem_url
    ? `<img src="${p.imagem_url}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentNode.textContent='🖥️'">`
    : '🖥️';
  document.getElementById('modal-produto').classList.add('open');
}
function fecharModal(){ document.getElementById('modal-produto').classList.remove('open') }
function ajustarQtdModal(d){
  qtdModal = Math.max(1, Math.min(produtoModal?.estoque||99, qtdModal+d));
  document.getElementById('modal-qtd').textContent = qtdModal;
}
function adicionarDoModal(){
  addToCart(produtoModal.id, qtdModal);
  fecharModal();
}

