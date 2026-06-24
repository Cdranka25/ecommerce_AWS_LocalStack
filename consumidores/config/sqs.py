# -*- coding: utf-8 -*-
# config/sqs.py — Cliente SQS (LocalStack) e utilitários de mensageria
import boto3
import json
from config.settings import (
    AWS_ENDPOINT_URL, AWS_REGION, AWS_ACCESS_KEY, AWS_SECRET_KEY,
    TODAS_AS_FILAS, MAX_RETRIES,
)

def get_sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
    )

def publicar_em_todas_filas(pedido: dict) -> None:
    sqs  = get_sqs_client()
    body = json.dumps(pedido, ensure_ascii=False)
    for url in TODAS_AS_FILAS:
        sqs.send_message(QueueUrl=url, MessageBody=body)
    print(f"[>>] Pedido {pedido['pedido_id'][:8]} publicado em {len(TODAS_AS_FILAS)} filas")

def consumir_fila(fila_url: str, callback) -> None:
    sqs = get_sqs_client()
    print(f"[*] Aguardando mensagens em: {fila_url.split('/')[-1]}")
    while True:
        try:
            resp = sqs.receive_message(
                QueueUrl=fila_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10,
                AttributeNames=["ApproximateReceiveCount"],
            )
        except KeyboardInterrupt:
            print("\n[!] Consumidor encerrado.")
            break
        except Exception as e:
            print(f"[ERRO] {e}")
            continue

        for msg in resp.get("Messages", []):
            tentativas = int(msg.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
            try:
                sucesso = callback(msg["Body"], tentativas)
            except Exception as e:
                print(f"[ERRO callback] {e}")
                sucesso = False
            if sucesso:
                sqs.delete_message(QueueUrl=fila_url, ReceiptHandle=msg["ReceiptHandle"])
            else:
                if tentativas >= MAX_RETRIES:
                    print(f"[DLQ] Máximo de tentativas — SQS enviará para DLQ")
