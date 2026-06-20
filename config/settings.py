# -*- coding: utf-8 -*-
# config/settings.py — Configurações centrais lidas do .env
import os
from dotenv import load_dotenv

load_dotenv()

# ── Supabase ────────────────────────────────────────────────
SUPABASE_URL              = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY         = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
JWT_SECRET                = os.getenv("JWT_SECRET", "")

# ── AWS / LocalStack ────────────────────────────────────────
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION       = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY   = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_KEY   = os.getenv("AWS_SECRET_ACCESS_KEY", "test")

_SQS_BASE        = f"{AWS_ENDPOINT_URL}/000000000000"
FILA_PAGAMENTO   = f"{_SQS_BASE}/sqs-pedidos-pagamento"
FILA_ESTOQUE     = f"{_SQS_BASE}/sqs-pedidos-estoque"
FILA_FISCAL      = f"{_SQS_BASE}/sqs-pedidos-fiscal"
FILA_LOGISTICA   = f"{_SQS_BASE}/sqs-pedidos-logistica"
FILA_NOTIFICACAO = f"{_SQS_BASE}/sqs-pedidos-notificacao"
FILA_DLQ         = f"{_SQS_BASE}/sqs-dead-letter"
TODAS_AS_FILAS   = [FILA_PAGAMENTO, FILA_ESTOQUE, FILA_FISCAL, FILA_LOGISTICA, FILA_NOTIFICACAO]
MAX_RETRIES      = int(os.getenv("MAX_RETRIES", "3"))
S3_BUCKET_NOTAS  = os.getenv("S3_BUCKET_NOTAS", "ecommerce-notas-fiscais")
