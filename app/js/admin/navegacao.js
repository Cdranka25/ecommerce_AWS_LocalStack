// ══════════════════════════════════
// Navegação de abas
// ══════════════════════════════════
function irAba(nome) {
  document.querySelectorAll(".aba").forEach(el => el.classList.remove("ativa"));
  document.querySelectorAll(".pagina").forEach(el => el.classList.remove("ativa"));
  document.querySelector(`[onclick="irAba('${nome}')"]`).classList.add("ativa");
  document.getElementById(`pagina-${nome}`).classList.add("ativa");
  abaAtiva = nome;
  if (nome === 'dlq') iniciarSimuladorDLQ();
}

