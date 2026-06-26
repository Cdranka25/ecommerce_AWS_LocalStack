// ══════════════════════════════════
// Estado global
// ══════════════════════════════════
let abaAtiva       = "visao-geral";
let pausado        = false;
let filtroAtivo    = "todos";
let ultimosEventos = [];
let idsVistos      = new Set();

// ── Utilitário compartilhado (deve ser o primeiro a carregar) ──
function esc(str) {
  return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
