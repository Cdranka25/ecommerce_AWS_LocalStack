#!/usr/bin/env python3
# consumidores/fiscal.py — Serviço Fiscal (SQS + Supabase + S3)
import json, uuid, sys, os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.sqs import consumir_fila, get_s3_client
from config.settings import FILA_FISCAL, MAX_RETRIES, S3_BUCKET_NOTAS
from consumidores._base import registrar_evento

def processar(body: str, tentativas: int) -> bool:
    pedido    = json.loads(body)
    pedido_id = pedido.get("pedido_id", "N/A")
    total     = pedido.get("total", 0)
    print(f"\n[fiscal] {datetime.now().strftime('%H:%M:%S')} | {pedido_id[:8]}")

    nfe = {
        "nfe_id":      str(uuid.uuid4()),
        "chave":       uuid.uuid4().hex[:44].upper(),
        "emissao":     datetime.utcnow().isoformat(),
        "pedido_id":   pedido_id,
        "valor_total": total,
        "status":      "autorizada",
    }

    # Salva NF-e no S3 (LocalStack)
    try:
        s3  = get_s3_client()
        key = f"notas-fiscais/{pedido_id}/{nfe['nfe_id']}.json"
        s3.put_object(
            Bucket=S3_BUCKET_NOTAS,
            Key=key,
            Body=json.dumps(nfe).encode(),
            ContentType="application/json",
        )
        registrar_evento(pedido_id, "fiscal", "EMITIDA", f"NF-e {nfe['chave'][:20]}... | R$ {total:.2f}")
        print(f"    [OK] NF-e emitida — salva em S3: {key}")
    except Exception as e:
        registrar_evento(pedido_id, "fiscal", "EMITIDA", f"NF-e {nfe['chave'][:20]}... (S3 offline)")
        print(f"    [OK] NF-e emitida (S3 offline: {e})")

    return True

if __name__ == "__main__":
    print("=" * 50)
    print("  SERVIÇO FISCAL — SQS + Supabase + S3")
    print("=" * 50)
    consumir_fila(FILA_FISCAL, processar)
