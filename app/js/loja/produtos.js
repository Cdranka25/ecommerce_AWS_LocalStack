// PRODUTOS
// produtoModal e qtdModal são declarados em config.js

let termoBusca    = '';
let categoriaAtiva = 'Todas';

async function carregarProdutos() {
  const g = document.getElementById('grid-produtos');
  g.innerHTML = '<div class="loading-overlay"><div class="spinner"></div> Carregando...</div>';
  try {
    produtos = await apiFetch('/produtos');
    renderProdutos();
  } catch (e) {
    g.innerHTML = `<div class="empty" style="grid-column:1/-1"><div class="empty-icon">!</div><div class="empty-text">Erro: ${e.message}</div></div>`;
  }
}

function renderProdutos() {
  const g = document.getElementById('grid-produtos');
  const f = document.getElementById('filtros-produtos');

  const categorias = ['Todas', ...new Set(produtos.map(p => p.categoria || 'Geral'))];
  f.innerHTML = `
    <div class="filtros-bar" id="filtros-bar">
      <input class="busca-input" id="busca-input" placeholder="Buscar produto..."
        value="${termoBusca}" oninput="termoBusca=this.value;renderProdutos()">
      <div class="categorias-chips">
        ${categorias.map(c => `
          <button class="categoria-chip ${c === categoriaAtiva ? 'active' : ''}"
            onclick="categoriaAtiva='${c}';renderProdutos()">${c}</button>
        `).join('')}
      </div>
    </div>
  `;

  const filtrados = produtos.filter(p => {
    const bate_busca     = !termoBusca || p.nome.toLowerCase().includes(termoBusca.toLowerCase())
                                        || (p.descricao || '').toLowerCase().includes(termoBusca.toLowerCase());
    const bate_categoria = categoriaAtiva === 'Todas' || (p.categoria || 'Geral') === categoriaAtiva;
    return bate_busca && bate_categoria;
  });

  if (!filtrados.length) {
    g.innerHTML = '<div class="empty" style="grid-column:1/-1;margin-top:2rem"><div class="empty-icon">?</div><div class="empty-text">Nenhum produto encontrado.</div></div>';
    return;
  }

  const cards = filtrados.map(p => {
    const esgotado    = p.estoque < 1;
    const estoqueBaixo = p.estoque > 0 && p.estoque <= 5;
    return `
      <div class="card ${esgotado ? 'card-esgotado' : ''}" onclick="abrirModal('${p.id}')">
        <div class="card-img">
          ${p.imagem_url
            ? `<img src="${p.imagem_url}" alt="${p.nome}" loading="lazy" onerror="this.parentNode.innerHTML='?'">`
            : '?'}
          ${esgotado    ? '<div class="card-badge badge-esgotado">Esgotado</div>' : ''}
          ${estoqueBaixo ? `<div class="card-badge badge-baixo">Ultimas ${p.estoque} un.</div>` : ''}
        </div>
        <div class="card-body">
          <div class="card-categoria">${p.categoria || 'Geral'}</div>
          <div class="card-nome">${p.nome}</div>
          <div class="card-desc">${p.descricao || ''}</div>
          <div class="card-footer">
            <div class="card-preco">${R(p.preco)}</div>
            <button class="btn-add" ${esgotado ? 'disabled' : ''}
              onclick="event.stopPropagation();addToCart('${p.id}',1)">
              ${esgotado ? 'Esgotado' : '+ Carrinho'}
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  g.innerHTML = cards;
}

function abrirModal(prodId) {
  const p = produtos.find(x => x.id === prodId);
  if (!p) return;
  produtoModal = p;
  qtdModal     = 1;

  const esgotado    = p.estoque < 1;
  const estoqueBaixo = p.estoque > 0 && p.estoque <= 5;

  document.getElementById('modal-prod-nome').textContent  = p.nome;
  document.getElementById('modal-prod-desc').textContent  = p.descricao || '';
  document.getElementById('modal-prod-preco').textContent = R(p.preco);
  document.getElementById('modal-prod-est').textContent   = esgotado
    ? 'Produto esgotado'
    : estoqueBaixo
      ? `Ultimas ${p.estoque} unidades!`
      : `${p.estoque} em estoque`;
  document.getElementById('modal-prod-est').style.color   = esgotado ? 'var(--red)' : estoqueBaixo ? 'var(--amber)' : 'var(--muted)';
  document.getElementById('modal-qtd').textContent        = 1;

  const imgDiv = document.getElementById('modal-prod-img');
  imgDiv.innerHTML = p.imagem_url
    ? `<img src="${p.imagem_url}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentNode.innerHTML='?'">`
    : '?';

  const btnAdd = document.getElementById('modal-btn-add');
  if (btnAdd) {
    btnAdd.disabled    = esgotado;
    btnAdd.textContent = esgotado ? 'Esgotado' : 'Adicionar ao carrinho';
  }

  document.getElementById('modal-produto').classList.add('open');
}

function fecharModal() {
  document.getElementById('modal-produto').classList.remove('open');
}

function ajustarQtdModal(d) {
  qtdModal = Math.max(1, Math.min(produtoModal?.estoque || 99, qtdModal + d));
  document.getElementById('modal-qtd').textContent = qtdModal;
}

function adicionarDoModal() {
  addToCart(produtoModal.id, qtdModal);
  fecharModal();
}
