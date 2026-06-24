// Visão Geral — S3
// ══════════════════════════════════
function renderS3(s3) {
  const tbody = document.querySelector("#tabela-s3 tbody");
  document.getElementById("erro-s3").textContent = s3.erro ? `Bucket "${s3.bucket}": ${s3.erro}` : "";
  if (!s3.objetos.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="vazio">Nenhum objeto ainda — finalize um pedido para gerar uma NF-e.</td></tr>`;
    return;
  }
  tbody.innerHTML = s3.objetos.map(o => `<tr>
    <td>${esc(o.chave)}</td>
    <td>${o.tamanho_bytes} bytes</td>
    <td>${new Date(o.modificado_em).toLocaleString("pt-BR")}</td>
  </tr>`).join("");
}

