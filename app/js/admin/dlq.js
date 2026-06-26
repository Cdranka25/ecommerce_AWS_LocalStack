// DLQ
// ══════════════════════════════════
function fmtTs(ms) {
  if (!ms) return "—";
  return new Date(Number(ms)).toLocaleString("pt-BR");
}

function renderDLQ(dados) {
  const counter   = document.getElementById("dlq-counter");
  const label     = document.getElementById("dlq-counter-label");
  const erroEl    = document.getElementById("dlq-erro");
  const tbody     = document.querySelector("#tabela-dlq tbody");

  erroEl.textContent = dados.erro ? `Erro ao ler DLQ: ${dados.erro}` : "";

  const total = dados.total ?? 0;
  counter.textContent  = total;
  counter.className    = "dlq-counter" + (total === 0 ? " zero" : "");
  label.textContent    = total === 1 ? "mensagem presa na DLQ" : "mensagens presas na DLQ";

  if (!dados.mensagens?.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="vazio">Nenhuma mensagem na DLQ — tudo processando normalmente. </td></tr>`;
    return;
  }

  tbody.innerHTML = dados.mensagens.map((m, i) => {
    const bodyFormatado = m.body_parsed
      ? JSON.stringify(m.body_parsed, null, 2)
      : m.body_raw ?? "—";
    const corBody = m.body_parsed ? "body-parsed" : "body-raw";
    const origemLabel = m.fila_origem
      ? `<div class="fila-origem"> ${esc(m.fila_origem)}</div>` : "";
    return `<tr>
      <td style="color:var(--muted);font-size:11px">#${i+1}<br><span class="msg-id">${esc(m.message_id?.slice(0,8))}…</span></td>
      <td><span class="tentativas">${esc(m.tentativas ?? "?")}×</span></td>
      <td class="ts">${fmtTs(m.enviada_em)}</td>
      <td>${origemLabel || "<span style='color:var(--muted)'>—</span>"}</td>
      <td>
        <details>
          <summary>ver conteúdo</summary>
          <div class="${corBody}">${esc(bodyFormatado)}</div>
        </details>
      </td>
    </tr>`;
  }).join("");
}

