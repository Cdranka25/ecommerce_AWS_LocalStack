#!/usr/bin/env python3
# consumidores/pagamento.py — Serviço de Pagamento (SQS + Supabase)
import json, random, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.sqs import consumir_fila
from config.settings import FILA_PAGAMENTO, MAX_RETRIES
from consumidores._base import registrar_evento

def validar_pagamento(pedido):
    forma  = pedido.get("forma_pagamento", "")
    total  = pedido.get("total", 0)
    if random.random() < 0.05:             # 5% recusa aleatória
        return False, "Recusado pela operadora (simulação)"
    if forma == "pix":
        return True, "PIX confirmado instantaneamente"
    if forma == "boleto":
        return True, "Boleto gerado — aguardando compensação"
    if forma == "cartao_credito":
        if total > 5000:
            return False, "Limite de crédito insuficiente"
        return True, f"Cartão aprovado — R$ {total:.2f}"
    return False, f"Forma desconhecida: {forma}"

def processar(body: str, tentativas: int) -> bool:
    pedido    = json.loads(body)
    pedido_id = pedido.get("pedido_id", "N/A")
    total     = pedido.get("total", 0)
    print(f"\n[pagamento] {datetime.now().strftime('%H:%M:%S')} | {pedido_id[:8]} | tentativa {tentativas}/{MAX_RETRIES}")
    ok, motivo = validar_pagamento(pedido)
    registrar_evento(pedido_id, "pagamento", "APROVADO" if ok else "RECUSADO", motivo)
    print(f"    {'[OK]' if ok else '[ERRO]'} {motivo}")
    return ok

if __name__ == "__main__":
    print("=" * 50)
    print("  SERVIÇO DE PAGAMENTO — SQS + Supabase")
    print("=" * 50)
    consumir_fila(FILA_PAGAMENTO, processar)
