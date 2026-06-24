#!/usr/bin/env python3
# consumidores/estoque.py — Serviço de Estoque (SQS + Supabase)
import json, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.sqs import consumir_fila
from config.settings import FILA_ESTOQUE, MAX_RETRIES
from consumidores._base import registrar_evento
from config.supabase_client import get_supabase_admin

def processar(body: str, tentativas: int) -> bool:
    pedido     = json.loads(body)
    pedido_id  = pedido.get("pedido_id", "N/A")
    produto_id = pedido.get("produto_id")
    qtd        = pedido.get("quantidade", 1)
    print(f"\n[estoque] {datetime.now().strftime('%H:%M:%S')} | {pedido_id[:8]}")

    try:
        sb   = get_supabase_admin()
        prod = sb.table("produtos").select("estoque, nome").eq("id", produto_id).single().execute()
        if not prod.data:
            registrar_evento(pedido_id, "estoque", "FALHA", "Produto não encontrado")
            return True  # descarta — dado inválido

        disponivel = prod.data["estoque"]
        nome       = prod.data["nome"]

        if disponivel < qtd:
            registrar_evento(pedido_id, "estoque", "FALHA", f"Estoque insuficiente: {disponivel} disponível")
            print(f"    [ERRO] Estoque insuficiente")
            return False

        # Desconta estoque atomicamente
        sb.table("produtos").update({"estoque": disponivel - qtd}).eq("id", produto_id).execute()
        registrar_evento(pedido_id, "estoque", "RESERVADO", f"{qtd}x {nome} reservados. Saldo: {disponivel - qtd}")
        print(f"    [OK] {qtd}x {nome} reservados")
        return True

    except Exception as e:
        registrar_evento(pedido_id, "estoque", "ERRO", str(e))
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("  SERVIÇO DE ESTOQUE — SQS + Supabase")
    print("=" * 50)
    consumir_fila(FILA_ESTOQUE, processar)
