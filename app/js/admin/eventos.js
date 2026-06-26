// Eventos dos consumidores
// ══════════════════════════════════
function setFiltro(servico) {
  filtroAtivo = servico;
  document.querySelectorAll(".filtro").forEach(el =>
    el.classList.toggle("ativo", el.dataset.servico === servico));
  renderEventos(ultimosEventos);
}

function togglePausa() {
  pausado = !pausado;
  const btn = document.getElementById("btn-pausa");
  btn.textContent = pausado ? "▶ Retomar" : "⏸ Pausar";
  btn.classList.toggle("pausado", pausado);
}

function chipServico(nome) {
  const cls = {pagamento:"pagamento",estoque:"estoque",fiscal:"fiscal",
               logistica:"logistica",notificacao:"notificacao"}[nome?.toLowerCase()] ?? "outro";
  return `<span class="chip chip-${cls}">${esc(nome ?? "—")}</span>`;
}

function classeStatus(status) {
  const s = (status ?? "").toLowerCase();
  if (s.includes("erro") || s.includes("falha") || s.includes("recusado")) return "status-erro";
  if (s.includes("ok") || s.includes("aprovado") || s.includes("concluido") || s.includes("sucesso")) return "status-ok";
  return "status-info";
}

function renderEventos(eventos) {
  const tbody = document.querySelector("#tabela-eventos tbody");
  const filtrados = filtroAtivo === "todos"
    ? eventos : eventos.filter(e => (e.servico ?? "").toLowerCase() === filtroAtivo);
  document.getElementById("contador-eventos").textContent =
    `Mostrando ${filtrados.length} de ${eventos.length} evento(s)`;
  if (!filtrados.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="vazio">Nenhum evento ainda — finalize um pedido.</td></tr>`;
    return;
  }
  tbody.innerHTML = filtrados.map(e => {
    const isNovo = !idsVistos.has(e.id);
    const hora   = e.criado_em ? new Date(e.criado_em).toLocaleTimeString("pt-BR") : "—";
    const pid    = e.pedido_id ? e.pedido_id.slice(0,8) : "—";
    return `<tr class="${isNovo ? "novo" : ""}">
      <td style="white-space:nowrap">${hora}</td>
      <td>${chipServico(e.servico)}</td>
      <td><span class="pid" title="${esc(e.pedido_id)}">${pid}…</span></td>
      <td><span class="${classeStatus(e.status)}">${esc(e.status ?? "—")}</span></td>
      <td class="msg-cell">
        <div class="msg-text">${esc(e.mensagem ?? "—")}</div>
        ${e.produto_nome && e.produto_nome !== "—"
          ? `<div class="msg-produto"> ${esc(e.produto_nome)}${e.total ? " · R$ "+Number(e.total).toFixed(2) : ""}</div>`
          : ""}
      </td>
    </tr>`;
  }).join("");
  filtrados.forEach(e => idsVistos.add(e.id));
}

