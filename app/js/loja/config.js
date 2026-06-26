// ═══════════════════════════════════════════════════════════
//  CONFIGURAÇÃO
// ═══════════════════════════════════════════════════════════
const API = 'http://localhost:8000';

// ── Estado global compartilhado entre todos os módulos ──────
let token               = localStorage.getItem('token') || null;
let userInfo            = JSON.parse(localStorage.getItem('userInfo') || 'null');
let carrinho            = JSON.parse(localStorage.getItem('carrinho') || '[]');
let enderecoSelecionado = null;
let fretesSelecionado   = null;

// Produtos
let produtos       = [];
let produtoModal   = null;
let qtdModal       = 1;
