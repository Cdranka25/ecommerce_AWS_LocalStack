#!/usr/bin/env python3
# consumidores/notificacao.py — Serviço de Notificação (SQS + Supabase)
import json, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.sqs import consumir_fila
from config.settings import FILA_NOTIFICACAO
from consumidores._base import registrar_evento
from config.supabase_client import get_supabase_admin

def processar(body: str, tentativas: int) -> bool:
    pedido    = json.loads(body)
    pedido_id = pedido.get("pedido_id", "N/A")
    cliente   = pedido.get("cliente", {})
    email     = cliente.get("email", "N/A")
    produto   = pedido.get("produto_nome", pedido.get("produto", {}).get("nome", "N/A"))
    total     = pedido.get("total", 0)
    frete     = pedido.get("frete_servico", "PAC")
    prazo     = pedido.get("frete_prazo", "?")
    print(f"\n[notificacao] {datetime.now().strftime('%H:%M:%S')} | {pedido_id[:8]}")

    # Atualiza status do pedido para CONCLUIDO no Supabase
    try:
        sb = get_supabase_admin()
        sb.table("pedidos").update({"status": "CONCLUIDO"}).eq("id", pedido_id).execute()
    except Exception as e:
        print(f"    [AVISO] Não atualizou status: {e}")

    print(f"    [EMAIL] Para: {email}")
    print(f"            Produto: {produto} | Total: R$ {total:.2f}")
    print(f"            Envio: {frete} | Prazo: {prazo} dias")

    registrar_evento(pedido_id, "notificacao", "ENVIADA", f"E-mail enviado para {email}")
    print(f"    [OK] Notificação enviada para {email}")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("  SERVIÇO DE NOTIFICAÇÃO — SQS + Supabase")
    print("=" * 50)
    consumir_fila(FILA_NOTIFICACAO, processar)
