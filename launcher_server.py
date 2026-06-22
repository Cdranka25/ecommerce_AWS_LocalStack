#!/usr/bin/env python3
# launcher_server.py — Inicia todos os serviços do e-commerce
# Uso: python launcher_server.py

import http.server, socketserver, os, webbrowser, threading
import subprocess, sys, time, socket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR      = os.path.join(BASE_DIR, "app")
PORT     = 3000
PYTHON   = sys.executable
INFRA    = os.path.join(BASE_DIR, "infra")

# ── Utilitários ───────────────────────────────────────────

def liberar_porta(port: int):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return
        print(f"[launcher] Porta {port} em uso — liberando...")
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
    except Exception as e:
        print(f"[launcher] Aviso ao liberar porta: {e}")


def localstack_pronto() -> bool:
    """Verifica se o LocalStack está respondendo."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", 4566)) == 0
    except Exception:
        return False


def rodar_terraform():
    """Provisiona filas SQS no LocalStack via Terraform (sem abrir janela)."""
    print("[launcher] Verificando LocalStack...")

    # Aguarda o LocalStack ficar pronto (até 30s)
    for i in range(30):
        if localstack_pronto():
            print("[launcher] LocalStack OK.")
            break
        print(f"[launcher] Aguardando LocalStack... ({i+1}s)")
        time.sleep(1)
    else:
        print("[launcher] AVISO: LocalStack não respondeu. As filas podem não existir.")
        return

    print("[launcher] Provisionando filas SQS via Terraform...")
    try:
        resultado = subprocess.run(
            ["terraform", "apply", "-auto-approve"],
            cwd=INFRA,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if resultado.returncode == 0:
            print("[launcher] Filas SQS criadas com sucesso.")
        else:
            print(f"[launcher] AVISO Terraform: {resultado.stderr[-300:]}")
    except subprocess.TimeoutExpired:
        print("[launcher] AVISO: Terraform demorou mais de 60s — pulando.")
    except FileNotFoundError:
        print("[launcher] AVISO: Terraform não encontrado no PATH.")
    except Exception as e:
        print(f"[launcher] AVISO: {e}")


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
            creationflags=subprocess.CREATE_NO_WINDOW,  # sem janela CMD
        )
    print(f"[launcher] {nome} iniciado → logs/{nome.lower().replace(' ', '_')}.log")


def subir_servicos():
    time.sleep(0.5)

    # 1. Terraform (recria filas se o LocalStack reiniciou)
    rodar_terraform()

    # 2. API FastAPI
    print("\n[launcher] Iniciando API FastAPI...")
    uvicorn_scripts = os.path.join(os.path.dirname(PYTHON), "Scripts", "uvicorn.exe")
    uvicorn_bin     = os.path.join(os.path.dirname(PYTHON), "uvicorn")
    uvicorn_path    = uvicorn_scripts if os.path.exists(uvicorn_scripts) else uvicorn_bin

    iniciar_em_background("API FastAPI", [
        uvicorn_path, "api.main:app", "--reload", "--port", "8000"
    ])

    # Aguarda a API subir
    print("[launcher] Aguardando API subir...")
    for _ in range(20):
        time.sleep(1)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", 8000)) == 0:
                    print("[launcher] API OK.")
                    break
        except Exception:
            pass
    else:
        print("[launcher] AVISO: API demorou para responder.")

    # 3. Consumidores
    consumidores = ["pagamento", "estoque", "fiscal", "logistica", "notificacao"]
    for nome in consumidores:
        iniciar_em_background(
            f"Consumidor {nome.capitalize()}",
            [PYTHON, os.path.join(BASE_DIR, "consumidores", f"{nome}.py")]
        )
        time.sleep(0.3)

    print("\n" + "=" * 52)
    print("  Todos os servicos estao rodando!")
    print("  API:      http://localhost:8000")
    print("  Docs:     http://localhost:8000/docs")
    print(f"  Frontend: http://localhost:{PORT}")
    print("  Logs:     pasta /logs/")
    print("=" * 52 + "\n")

    time.sleep(0.5)
    webbrowser.open(f"http://localhost:{PORT}")


# ── Servidor HTTP do frontend ─────────────────────────────

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIR, **kw)
    def log_message(self, fmt, *args):
        pass


liberar_porta(PORT)

print("=" * 52)
print("   E-commerce Supabase — Iniciando tudo")
print("=" * 52)
print(f"[launcher] Python:   {PYTHON}")
print(f"[launcher] Frontend: http://localhost:{PORT}")
print("[launcher] Pressione CTRL+C para encerrar.\n")

threading.Thread(target=subir_servicos, daemon=True).start()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
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
