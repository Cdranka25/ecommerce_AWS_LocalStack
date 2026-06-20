#!/usr/bin/env python3
# consumidores/logistica.py — Serviço de Logística (SQS + Supabase)
import json, uuid, random, sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.sqs import consumir_fila
from config.settings import FILA_LOGISTICA
from consumidores._base import registrar_evento
from config.supabase_client import get_supabase_admin

TRANSPORTADORAS = ["Correios PAC", "Correios SEDEX", "Jadlog", "Mercado Envios"]

def processar(body: str, tentativas: int) -> bool:
    pedido    = json.loads(body)
    pedido_id = pedido.get("pedido_id", "N/A")
    prazo     = pedido.get("frete_prazo", random.randint(3, 10))
    servico   = pedido.get("frete_servico", "PAC")
    previsao  = (datetime.now() + timedelta(days=prazo)).strftime("%d/%m/%Y")
    rastreio  = f"BR{uuid.uuid4().hex[:9].upper()}BR"
    endereco  = pedido.get("endereco_entrega", {})
    print(f"\n[logistica] {datetime.now().strftime('%H:%M:%S')} | {pedido_id[:8]}")

    # Atualiza status do pedido para EM_TRANSITO no Supabase
    try:
        sb = get_supabase_admin()
        sb.table("pedidos").update({"status": "EM_TRANSITO"}).eq("id", pedido_id).execute()
    except Exception as e:
        print(f"    [AVISO] Não atualizou status: {e}")

    registrar_evento(
        pedido_id, "logistica", "AGENDADA",
        f"{servico} | Rastreio: {rastreio} | Previsão: {previsao} | Destino: {endereco.get('cidade','?')}-{endereco.get('uf','?')}"
    )
    print(f"    [OK] Entrega agendada — {rastreio} | {previsao}")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("  SERVIÇO DE LOGÍSTICA — SQS + Supabase")
    print("=" * 50)
    consumir_fila(FILA_LOGISTICA, processar)
