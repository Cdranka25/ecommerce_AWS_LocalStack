// Visão Geral — Filas SQS
// ══════════════════════════════════
function renderFilas(filas) {
  const tbody = document.querySelector("#tabela-filas tbody");
  if (!filas.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="vazio">Nenhuma fila — rode o Terraform.</td></tr>`;
    return;
  }
  tbody.innerHTML = filas.map(f => {
    const cls = f.erro ? "zero"
      : f.e_dlq ? (f.mensagens_disponiveis > 0 ? "dlq" : "zero")
      : (f.mensagens_disponiveis > 0 ? "ativo" : "zero");
    const tagDlq    = f.e_dlq ? `<span class="tag-dlq">DLQ</span>` : "";
    const linhaErro = f.erro  ? `<div class="erro-linha">${esc(f.erro)}</div>` : "";
    return `<tr>
      <td>${esc(f.nome)}${tagDlq}${linhaErro}</td>
      <td><span class="badge ${cls}">${f.mensagens_disponiveis}</span></td>
      <td>${f.mensagens_em_processamento}</td>
    </tr>`;
  }).join("");

  // Atualiza badge da aba DLQ
  const dlqFila = filas.find(f => f.e_dlq);
  const qtd = dlqFila ? dlqFila.mensagens_disponiveis : 0;
  const badgeEl = document.getElementById("badge-dlq");
  badgeEl.textContent = qtd;
  badgeEl.className = "badge-aba" + (qtd > 0 ? "" : " zero");
}

