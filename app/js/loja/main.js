// ═══════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════
document.getElementById('cart-badge').textContent = carrinho.reduce((s,i)=>s+i.qtd,0);
atualizarNavAuth();
carregarProdutos();
