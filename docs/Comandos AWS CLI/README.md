# Ver filas criadas
aws --endpoint-url=http://localhost:4566 sqs list-queues

# Ver mensagens na DLQ
aws --endpoint-url=http://localhost:4566 sqs receive-message \
  --queue-url http://localhost:4566/000000000000/sqs-dead-letter

# Ver objetos no bucket S3 (notas fiscais)
aws --endpoint-url=http://localhost:4566 s3 ls s3://ecommerce-notas-fiscais

# Ver quantas mensagens estão esperando em cada fila (sem "roubar" mensagem dos consumidores)
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/sqs-pedidos-pagamento \
  --attribute-names ApproximateNumberOfMessages

# Ver o que caiu na Dead Letter Queue
aws --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/sqs-dead-letter \
  --attribute-names ApproximateNumberOfMessages

# Listar as notas fiscais salvas no S3
aws --endpoint-url=http://localhost:4566 s3 ls s3://ecommerce-notas-fiscais/

# Baixar/ver o conteúdo de uma nota fiscal específica
aws --endpoint-url=http://localhost:4566 s3 cp s3://ecommerce-notas-fiscais/<nome-do-arquivo> -