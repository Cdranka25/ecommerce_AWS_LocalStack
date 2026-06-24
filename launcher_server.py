#!/usr/bin/env python3
# launcher_server.py — Inicia todos os serviços do e-commerce
# Uso: python launcher_server.py

import http.server, socketserver, os, webbrowser, threading
import subprocess, sys, time, socket, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR      = os.path.join(BASE_DIR, "app")
PORT     = 3000
PYTHON   = sys.executable
INFRA    = os.path.join(BASE_DIR, "infra")

# ── Utilitários de log ────────────────────────────────────

def _log(tag: str, msg: str):
    """Imprime uma linha de log com timestamp."""
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}", flush=True)


def _spinner(stop_event: threading.Event, tag: str, msg: str, intervalo: float = 0.8):
    """Exibe um spinner animado enquanto stop_event não for setado."""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    i = 0
    while not stop_event.is_set():
        print(f"\r  {frames[i % len(frames)]}  [{tag}] {msg}...", end="", flush=True)
        time.sleep(intervalo)
        i += 1
    print("\r" + " " * (len(msg) + 20) + "\r", end="", flush=True)  # limpa a linha


# ── Utilitários ───────────────────────────────────────────

def liberar_porta(port: int):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return
        _log("launcher", f"Porta {port} em uso — liberando...")
        resultado = subprocess.check_output(
            f"netstat -ano | findstr :{port}", shell=True
        ).decode()
        pids = set()
        for linha in resultado.strip().splitlines():
            partes = linha.strip().split()
            if len(partes) >= 5 and f":{port}" in partes[1]:
                pids.add(partes[-1])
        for pid in pids:
            if pid and pid != "0":
                subprocess.call(f"taskkill /PID {pid} /F", shell=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        _log("launcher", f"Porta {port} liberada.")
    except Exception as e:
        _log("launcher", f"Aviso ao liberar porta: {e}")


def localstack_pronto() -> bool:
    """Verifica se o LocalStack está respondendo."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", 4566)) == 0
    except Exception:
        return False


def rodar_terraform():
    """Provisiona filas SQS no LocalStack via Terraform (sem abrir janela)."""
    _log("terraform", "Verificando LocalStack na porta 4566...")

    # Aguarda o LocalStack ficar pronto (até 30s)
    aguardou = False
    for i in range(30):
        if localstack_pronto():
            if aguardou:
                print()  # quebra linha do contador
            _log("terraform", "LocalStack respondendo — OK.")
            break
        aguardou = True
        print(f"\r  ⏳  [terraform] Aguardando LocalStack inicializar... ({i+1}s/30s)", end="", flush=True)
        time.sleep(1)
    else:
        print()
        _log("terraform", "AVISO: LocalStack não respondeu em 30s. As filas podem não existir.")
        return

    # Verifica se o terraform está disponível
    _log("terraform", "Verificando instalação do Terraform...")
    try:
        ver = subprocess.check_output(["terraform", "version"], text=True, stderr=subprocess.DEVNULL).splitlines()[0]
        _log("terraform", f"Encontrado: {ver}")
    except FileNotFoundError:
        _log("terraform", "AVISO: Terraform não encontrado no PATH — pulando provisionamento.")
        return
    except Exception as e:
        _log("terraform", f"AVISO: Não foi possível verificar o Terraform: {e}")

    # terraform init (rápido se já foi feito antes)
    _log("terraform", "Executando 'terraform init' (verifica providers)...")
    stop_init = threading.Event()
    t_init = threading.Thread(target=_spinner, args=(stop_init, "terraform", "Inicializando providers"), daemon=True)
    t_init.start()
    try:
        r_init = subprocess.run(
            ["terraform", "init", "-input=false"],
            cwd=INFRA,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        stop_init.set(); t_init.join()
        _log("terraform", "AVISO: 'terraform init' demorou mais de 60s — abortando.")
        return
    finally:
        stop_init.set(); t_init.join()

    if r_init.returncode != 0:
        _log("terraform", f"AVISO: 'terraform init' falhou:\n{r_init.stderr[-400:]}")
        return
    _log("terraform", "'terraform init' concluído.")

    # terraform plan (mostra o que será criado)
    _log("terraform", "Executando 'terraform plan' (calcula mudanças necessárias)...")
    stop_plan = threading.Event()
    t_plan = threading.Thread(target=_spinner, args=(stop_plan, "terraform", "Planejando infraestrutura"), daemon=True)
    t_plan.start()
    try:
        r_plan = subprocess.run(
            ["terraform", "plan", "-input=false", "-no-color"],
            cwd=INFRA,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        stop_plan.set(); t_plan.join()
        _log("terraform", "AVISO: 'terraform plan' demorou mais de 60s — abortando.")
        return
    finally:
        stop_plan.set(); t_plan.join()

    if r_plan.returncode != 0:
        _log("terraform", f"AVISO: 'terraform plan' falhou:\n{r_plan.stderr[-400:]}")
        return

    # Extrai um resumo do plan (linha "Plan: X to add...")
    resumo_plan = next(
        (l.strip() for l in r_plan.stdout.splitlines() if l.strip().startswith("Plan:")),
        "plano calculado."
    )
    _log("terraform", f"Plan: {resumo_plan}")

    # terraform apply
    _log("terraform", "Executando 'terraform apply' (criando/atualizando recursos)...")
    stop_apply = threading.Event()
    t_apply = threading.Thread(target=_spinner, args=(stop_apply, "terraform", "Aplicando infraestrutura no LocalStack"), daemon=True)
    t_apply.start()
    try:
        r_apply = subprocess.run(
            ["terraform", "apply", "-auto-approve", "-no-color"],
            cwd=INFRA,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        stop_apply.set(); t_apply.join()
        _log("terraform", "AVISO: 'terraform apply' demorou mais de 120s — abortando.")
        return
    finally:
        stop_apply.set(); t_apply.join()

    if r_apply.returncode == 0:
        # Extrai o resumo final ("Apply complete! Resources: X added...")
        resumo_apply = next(
            (l.strip() for l in r_apply.stdout.splitlines() if "Apply complete" in l),
            "concluído com sucesso."
        )
        _log("terraform", f"{resumo_apply}")

        # Lista os recursos criados (linhas com "aws_sqs_queue" ou "aws_s3_bucket")
        criados = [l.strip() for l in r_apply.stdout.splitlines()
                   if ": Creation complete" in l or ": Creating..." in l]
        for linha in criados[:10]:  # limita a 10 linhas
            _log("terraform", f"  › {linha}")
    else:
        _log("terraform", f"AVISO Terraform:\n{r_apply.stderr[-400:]}")


def criar_bucket_s3():
    """Cria o bucket S3 de notas fiscais no LocalStack (idempotente)."""
    sys.path.insert(0, BASE_DIR)
    from config.sqs import get_s3_client
    from config.settings import S3_BUCKET_NOTAS

    _log("s3", f"Verificando bucket '{S3_BUCKET_NOTAS}'...")
    try:
        s3 = get_s3_client()
        s3.create_bucket(Bucket=S3_BUCKET_NOTAS)
        _log("s3", f"✔ Bucket '{S3_BUCKET_NOTAS}' criado.")
    except Exception as e:
        msg = str(e)
        if "BucketAlreadyExists" in msg or "BucketAlreadyOwnedByYou" in msg:
            _log("s3", f"Bucket '{S3_BUCKET_NOTAS}' já existe — OK.")
        else:
            _log("s3", f"AVISO ao criar bucket S3: {e}")


def listar_mensagens_dlq() -> dict:
    """Retorna as mensagens presas na DLQ (peek sem deletar)."""
    sys.path.insert(0, BASE_DIR)
    from config.sqs import get_sqs_client
    from config.settings import FILA_DLQ
    import json as _json

    sqs = get_sqs_client()
    mensagens = []
    try:
        ids_vistos = set()
        for _ in range(5):
            resp = sqs.receive_message(
                QueueUrl=FILA_DLQ,
                MaxNumberOfMessages=10,
                VisibilityTimeout=0,
                WaitTimeSeconds=0,
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
            )
            lote = resp.get("Messages", [])
            if not lote:
                break
            for m in lote:
                if m["MessageId"] in ids_vistos:
                    continue
                ids_vistos.add(m["MessageId"])
                body_raw = m.get("Body", "")
                try:
                    body_parsed = _json.loads(body_raw)
                except Exception:
                    body_parsed = None
                attrs = m.get("Attributes", {})
                mensagens.append({
                    "message_id":        m["MessageId"],
                    "body_raw":          body_raw,
                    "body_parsed":       body_parsed,
                    "recebida_em":       attrs.get("ApproximateFirstReceiveTimestamp"),
                    "tentativas":        attrs.get("ApproximateReceiveCount"),
                    "enviada_em":        attrs.get("SentTimestamp"),
                    "fila_origem":       attrs.get("DeadLetterQueueSourceArn", "").split(":")[-1],
                })
        return {"mensagens": mensagens, "total": len(mensagens), "erro": None}
    except Exception as e:
        return {"mensagens": [], "total": 0, "erro": str(e)}


def iniciar_em_background(nome: str, comando: list):
    """Inicia processo em background SEM abrir janela CMD."""
    log_path = os.path.join(BASE_DIR, "logs", f"{nome.lower().replace(' ', '_')}.log")
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as log:
        subprocess.Popen(
            comando,
            cwd=BASE_DIR,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    _log("launcher", f"✔ {nome} iniciado → logs/{nome.lower().replace(' ', '_')}.log")


# ── AWS Explorer: dados das filas SQS e do bucket S3 ──────

def listar_filas_sqs() -> list:
    sys.path.insert(0, BASE_DIR)
    from config.sqs import get_sqs_client
    from config.settings import TODAS_AS_FILAS, FILA_DLQ

    sqs = get_sqs_client()
    filas = []
    for url in TODAS_AS_FILAS + [FILA_DLQ]:
        nome = url.rstrip("/").split("/")[-1]
        item = {"nome": nome, "url": url, "mensagens_disponiveis": 0,
                 "mensagens_em_processamento": 0, "e_dlq": nome == "sqs-dead-letter", "erro": None}
        try:
            attrs = sqs.get_queue_attributes(
                QueueUrl=url,
                AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
            )["Attributes"]
            item["mensagens_disponiveis"] = int(attrs.get("ApproximateNumberOfMessages", 0))
            item["mensagens_em_processamento"] = int(attrs.get("ApproximateNumberOfMessagesNotVisible", 0))
        except Exception as e:
            item["erro"] = str(e)
        filas.append(item)
    return filas


def listar_objetos_s3() -> dict:
    sys.path.insert(0, BASE_DIR)
    from config.sqs import get_s3_client
    from config.settings import S3_BUCKET_NOTAS

    s3 = get_s3_client()
    try:
        resp = s3.list_objects_v2(Bucket=S3_BUCKET_NOTAS, MaxKeys=200)
        objetos = [
            {"chave": obj["Key"], "tamanho_bytes": obj["Size"],
             "modificado_em": obj["LastModified"].isoformat()}
            for obj in resp.get("Contents", [])
        ]
        objetos.sort(key=lambda o: o["modificado_em"], reverse=True)
        return {"bucket": S3_BUCKET_NOTAS, "objetos": objetos, "erro": None}
    except Exception as e:
        return {"bucket": S3_BUCKET_NOTAS, "objetos": [], "erro": str(e)}


def subir_servicos():
    time.sleep(0.5)

    # ── Etapa 1: Terraform ────────────────────────────────
    print("\n" + "─" * 52)
    print("  ETAPA 1/3 — Infraestrutura (LocalStack + Terraform)")
    print("─" * 52)
    rodar_terraform()

    # ── Etapa 1b: Bucket S3 ───────────────────────────────
    criar_bucket_s3()

    # ── Etapa 2: API FastAPI ──────────────────────────────
    print("\n" + "─" * 52)
    print("  ETAPA 2/3 — API FastAPI (porta 8000)")
    print("─" * 52)
    uvicorn_scripts = os.path.join(os.path.dirname(PYTHON), "Scripts", "uvicorn.exe")
    uvicorn_bin     = os.path.join(os.path.dirname(PYTHON), "uvicorn")
    uvicorn_path    = uvicorn_scripts if os.path.exists(uvicorn_scripts) else uvicorn_bin

    iniciar_em_background("API FastAPI", [
        uvicorn_path, "api.main:app", "--reload", "--port", "8000"
    ])

    _log("api", "Aguardando a API ficar disponível na porta 8000...")
    for tentativa in range(20):
        time.sleep(1)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", 8000)) == 0:
                    _log("api", f"✔ API respondendo após {tentativa+1}s.")
                    break
        except Exception:
            pass
        print(f"\r  ⏳  [api] Aguardando API... ({tentativa+1}s/20s)", end="", flush=True)
    else:
        print()
        _log("api", "AVISO: API demorou para responder — verifique logs/api_fastapi.log.")

    # ── Etapa 3: Consumidores ─────────────────────────────
    print("\n" + "─" * 52)
    print("  ETAPA 3/3 — Consumidores SQS (5 workers)")
    print("─" * 52)
    consumidores = ["pagamento", "estoque", "fiscal", "logistica", "notificacao"]
    for nome in consumidores:
        iniciar_em_background(
            f"Consumidor {nome.capitalize()}",
            [PYTHON, os.path.join(BASE_DIR, "consumidores", f"{nome}.py")]
        )
        time.sleep(0.3)

    # ── Resumo final ──────────────────────────────────────
    print("\n" + "=" * 52)
    print("   Todos os serviços foram iniciados com sucesso")
    print("   Acesse o frontend e AWS Explorer através dos links abaixo.")
    print("=" * 52)
    print(f"  API:           http://localhost:8000")
    print(f"  Docs:          http://localhost:8000/docs")
    print(f"  Frontend:      http://localhost:{PORT}")
    print(f"  AWS Explorer:  http://localhost:{PORT}/admin.html")
    print(f"  Logs:          pasta /logs/")
    print(f"")
    print(f"Projeto foi desenvolvido pelos alunos: Caio Dalagnoli Dranka e Vinicius Muller, no curso de Sistemas Distribuídos da FURB")
    print("=" * 52 + "\n")

    time.sleep(0.5)
    webbrowser.open(f"http://localhost:{PORT}")


# ── Servidor HTTP do frontend ─────────────────────────────

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIR, **kw)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/api/aws/filas":
            self._responder_json(listar_filas_sqs())
            return
        if self.path == "/api/aws/s3":
            self._responder_json(listar_objetos_s3())
            return
        if self.path == "/api/aws/dlq":
            self._responder_json(listar_mensagens_dlq())
            return
        super().do_GET()

    def _responder_json(self, dados):
        try:
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
            status = 200
        except Exception as e:
            corpo = json.dumps({"erro": str(e)}).encode("utf-8")
            status = 500
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


liberar_porta(PORT)

print("=" * 52)
print("   Inicializando o Projeto E-commerce")
print("=" * 52)
print(f"[launcher] Python:        {PYTHON}")
print(f"[launcher] Frontend:      http://localhost:{PORT}")
print(f"[launcher] AWS Explorer:  http://localhost:{PORT}/admin.html")
print("[launcher] Pressione CTRL+C para encerrar.\n")

threading.Thread(target=subir_servicos, daemon=True).start()

with socketserver.ThreadingTCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[launcher] Encerrado. Encerrando processos em background...")
        subprocess.call("taskkill /F /FI \"WINDOWTITLE eq API FastAPI\"",
                        shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for nome in ["pagamento", "estoque", "fiscal", "logistica", "notificacao"]:
            subprocess.call(
                f"taskkill /F /FI \"WINDOWTITLE eq Consumidor {nome.capitalize()}\"",
                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        print("[launcher] Pronto.")
