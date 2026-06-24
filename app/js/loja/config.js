// ═══════════════════════════════════════════════════════════
//  CONFIGURAÇÃO
// ═══════════════════════════════════════════════════════════
const API = 'http://localhost:8000';

// ── Estado global ──────────────────────────────────────────
let token        = localStorage.getItem('token') || null;
let userInfo     = JSON.parse(localStorage.getItem('userInfo') || 'null');
let carrinho     = JSON.parse(localStorage.getItem('carrinho') || '[]');
let enderecoSelecionado = null;
let fretesSelecionado   = null;
let produtoModal = null;
let qtdModal     = 1;
