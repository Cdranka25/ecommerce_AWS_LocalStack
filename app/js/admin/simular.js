// ══════════════════════════════════
// Simulação de DLQ
// ══════════════════════════════════

const FILAS_DISPONIVEIS = [
  "sqs-pedidos-pagamento",
  "sqs-pedidos-estoque",
  "sqs-pedidos-fiscal",
  "sqs-pedidos-logistica",
  "sqs-pedidos-notificacao",
];

const MENSAGENS_PRESET = [
  { label: "JSON inválido",             valor: "isto nao e um json valido {{{" },
  { label: "Corpo vazio",               valor: "" },
  { label: "Campo produto_id faltando", valor: '{"pedido_id":"fake-123","quantidade":1}' },
  { label: "Tipo errado (número)",      valor: "99999" },
  { label: "HTML injetado",             valor: "<script>alert('xss')<\/script>" },
];

// Escape local — não depende do esc() do main.js
function _e(str) {
  return String(str ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function iniciarSimuladorDLQ() {
  const container = document.getElementById("simulador-dlq");
  if (!container) return;

  const opcoesFilas   = FILAS_DISPONIVEIS.map(f => `<option value="${_e(f)}">${_e(f)}</option>`).join("");
  const botoesPreset  = MENSAGENS_PRESET.map((p, i) =>
    `<button class="sim-preset${i===0?" ativo":""}" onclick="selecionarPreset(${i})">${_e(p.label)}</button>`
  ).join("");

  container.innerHTML = `
    <div class="sim-card">
      <div class="sim-titulo"> Simular mensagem na DLQ</div>
      <div class="sim-desc">
        Envia uma mensagem inválida para a fila escolhida. O consumidor vai tentar processá-la
        <strong>3 vezes</strong>, falhar em todas e movê-la automaticamente para a
        <strong>sqs-dead-letter</strong>.
      </div>

      <div class="sim-linha">
        <label class="sim-label">Fila de destino</label>
        <select id="sim-fila" class="sim-select">${opcoesFilas}</select>
      </div>

      <div class="sim-linha">
        <label class="sim-label">Mensagem preset</label>
        <div class="sim-presets">${botoesPreset}</div>
      </div>

      <div class="sim-linha">
        <label class="sim-label">
          Conteúdo da mensagem
          <span style="color:var(--muted);text-transform:none;font-size:11px">(editável)</span>
        </label>
        <textarea id="sim-corpo" class="sim-textarea" rows="3"></textarea>
      </div>

      <div class="sim-acoes">
        <button class="sim-btn" id="sim-enviar" onclick="enviarSimulacao()">
          ⚡ Enviar para a fila
        </button>
        <span class="sim-tempo">⏱ Cai na DLQ em ~90s após 3 falhas</span>
      </div>

      <div id="sim-resultado"></div>
    </div>`;

  // Preenche o textarea com o primeiro preset depois do innerHTML estar no DOM
  document.getElementById("sim-corpo").value = MENSAGENS_PRESET[0].valor;
}

function selecionarPreset(idx) {
  document.getElementById("sim-corpo").value = MENSAGENS_PRESET[idx].valor;
  document.querySelectorAll(".sim-preset").forEach((el, i) =>
    el.classList.toggle("ativo", i === idx));
}

async function enviarSimulacao() {
  const fila     = document.getElementById("sim-fila").value;
  const mensagem = document.getElementById("sim-corpo").value;
  const btnEl    = document.getElementById("sim-enviar");
  const resEl    = document.getElementById("sim-resultado");

  btnEl.disabled    = true;
  btnEl.textContent = "Enviando...";
  resEl.innerHTML   = "";

  try {
    const resp  = await fetch("/api/aws/simular-dlq", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ fila, mensagem }),
    });
    const dados = await resp.json();

    if (dados.ok) {
      resEl.innerHTML = `
        <div class="sim-ok">
          <div> <strong>Mensagem enviada com sucesso!</strong></div>
          <div class="sim-detalhe">Fila: <code>${_e(dados.fila)}</code></div>
          <div class="sim-detalhe">Message ID: <code>${_e(dados.message_id)}</code></div>
          <div class="sim-info">${_e(dados.info)}</div>
          <div class="sim-progresso">
            <div class="sim-step"      id="step-1"> Tentativa 1 — aguardando...</div>
            <div class="sim-step dim"  id="step-2"> Tentativa 2</div>
            <div class="sim-step dim"  id="step-3"> Tentativa 3</div>
            <div class="sim-step dim"  id="step-dlq"> DLQ</div>
          </div>
        </div>`;
      iniciarProgressoDLQ();
    } else {
      resEl.innerHTML = `<div class="sim-erro"> Erro: ${_e(dados.erro)}</div>`;
    }
  } catch (e) {
    resEl.innerHTML = `<div class="sim-erro"> Falha na requisição: ${_e(String(e))}</div>`;
  } finally {
    btnEl.disabled    = false;
    btnEl.textContent = " Enviar para a fila";
  }
}

function iniciarProgressoDLQ() {
  const passos = [
    { id: "step-1",   delay: 5000,  texto: "✖ Tentativa 1 — falhou" },
    { id: "step-2",   delay: 35000, texto: "✖ Tentativa 2 — falhou" },
    { id: "step-3",   delay: 65000, texto: "✖ Tentativa 3 — falhou" },
    { id: "step-dlq", delay: 90000, texto: "💀 Mensagem movida para DLQ!" },
  ];
  passos.forEach(({ id, delay, texto }) => {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = texto;
      el.classList.remove("dim");
      el.classList.add(id === "step-dlq" ? "dlq-chegou" : "falhou");
    }, delay);
  });
}

// iniciarSimuladorDLQ() é chamada por navegacao.js ao entrar na aba DLQ.