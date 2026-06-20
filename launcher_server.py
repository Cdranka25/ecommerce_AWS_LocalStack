#!/usr/bin/env python3
# launcher_server.py — Inicia todos os serviços do e-commerce
# Uso: python launcher_server.py

import http.server, socketserver, os, webbrowser, threading
import subprocess, sys, time, socket

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR      = os.path.join(BASE_DIR, "app")
PORT     = 3000
PYTHON   = sys.executable  # usa o mesmo Python que está rodando este script

processos = []


def liberar_porta(port: int):
    """Encerra qualquer processo usando a porta antes de subir."""
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


def iniciar_processo(nome: str, comando: list):
    """Abre um processo em nova janela CMD visível."""
    cmd_str = " ".join(f'"{c}"' if " " in c else c for c in comando)
    subprocess.Popen(
        f'start "{nome}" cmd /k "{cmd_str}"',
        shell=True,
        cwd=BASE_DIR,
    )
    print(f"[launcher] {nome} iniciado.")


def subir_servicos():
    """Aguarda um pouco e sobe API + consumidores em janelas separadas."""
    time.sleep(1)

    print("\n[launcher] Iniciando API FastAPI...")
    uvicorn_path = os.path.join(os.path.dirname(PYTHON), "Scripts", "uvicorn")
    if not os.path.exists(uvicorn_path + ".exe"):
        uvicorn_path = os.path.join(os.path.dirname(PYTHON), "uvicorn")
    iniciar_processo("API FastAPI", [
        uvicorn_path, "api.main:app", "--reload", "--port", "8000"
    ])

    time.sleep(3)

    consumidores = ["pagamento", "estoque", "fiscal", "logistica", "notificacao"]
    for nome in consumidores:
        iniciar_processo(f"Consumidor {nome.capitalize()}", [
            PYTHON, os.path.join(BASE_DIR, "consumidores", f"{nome}.py")
        ])
        time.sleep(0.5)

    print("\n[launcher] Todos os servicos iniciados!")
    print("  API:      http://localhost:8000")
    print("  Docs:     http://localhost:8000/docs")
    print(f"  Frontend: http://localhost:{PORT}\n")

    time.sleep(1)
    webbrowser.open(f"http://localhost:{PORT}")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIR, **kw)
    def log_message(self, fmt, *args):
        pass


liberar_porta(PORT)

print("=" * 52)
print("   E-commerce Supabase — Iniciando tudo")
print("=" * 52)
print(f"[launcher] Python: {PYTHON}")
print(f"[launcher] Pasta app: {DIR}")
print(f"[launcher] Frontend: http://localhost:{PORT}")
print("[launcher] Pressione CTRL+C para encerrar o frontend.\n")

threading.Thread(target=subir_servicos, daemon=True).start()

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[launcher] Frontend encerrado.")
        print("[launcher] Feche as outras janelas manualmente.")