# consumidores/_base.py — utilitário compartilhado
import json
from datetime import datetime
from config.supabase_client import get_supabase_admin

def registrar_evento(pedido_id: str, servico: str, status: str, mensagem: str):
    """Insere um evento na tabela eventos_pedido do Supabase."""
    try:
        sb = get_supabase_admin()
        sb.table("eventos_pedido").insert({
            "pedido_id":  pedido_id,
            "servico":    servico,
            "status":     status,
            "mensagem":   mensagem,
            "criado_em":  datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        print(f"[AVISO] Falha ao registrar evento no Supabase: {e}")
