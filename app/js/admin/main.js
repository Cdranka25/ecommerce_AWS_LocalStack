// Loop principal
// ══════════════════════════════════
async function atualizar() {
  const statusEl  = document.getElementById("status");
  const statusTxt = document.getElementById("status-txt");

  // Filas (sempre — atualiza badge da aba DLQ)
  try {
    const filas = await (await fetch("/api/aws/filas")).json();
    renderFilas(filas);
    statusEl.classList.remove("erro");
    statusTxt.textContent = "conectado";
  } catch {
    statusEl.classList.add("erro");
    statusTxt.textContent = "erro de conexão";
  }

  // S3 (sempre)
  try {
    const s3 = await (await fetch("/api/aws/s3")).json();
    renderS3(s3);
  } catch {}

  // Eventos (apenas se aba ativa e não pausado)
  if (!pausado) {
    try {
      const ev = await (await fetch("http://localhost:8000/admin/eventos?limit=60")).json();
      ultimosEventos = ev;
      if (abaAtiva === "eventos") renderEventos(ev);
    } catch {}
  }

  // DLQ (sempre — para manter o badge atualizado)
  try {
    const dlq = await (await fetch("/api/aws/dlq")).json();
    if (abaAtiva === "dlq") renderDLQ(dlq);
  } catch {}
}

function esc(str) {
  return String(str ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

atualizar();
setInterval(atualizar, 4000);
