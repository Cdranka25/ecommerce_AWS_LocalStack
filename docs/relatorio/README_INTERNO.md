# Guia interno do código — E-commerce SD

Este documento explica **por que** cada decisão foi tomada e **como** cada parte funciona.
Guarde-o para estudar antes da defesa.

---

## 1. Por que migramos do RabbitMQ para o SQS?

O projeto anterior usava **pika + RabbitMQ** com exchange topic para fazer fan-out.
A migração para **boto3 + SQS (LocalStack)** atende o requisito de "uso de nuvem" e
permite usar Terraform para provisionar a infra — algo impossível com RabbitMQ local.

A troca não muda a lógica dos consumidores: o callback ainda recebe o body e retorna
`True` (ACK) ou `False` (NACK). Só a camada de transporte mudou.

---

## 2. Estrutura de arquivos e responsabilidades

```
config/settings.py   → variáveis centrais (URLs, senhas, limites)
config/sqs.py        → conexão boto3, publicar, consumir
api/database.py      → criação de tabelas, salvar pedido, registrar evento
api/viacep.py        → chamada HTTP ao ViaCEP (API externa)
api/models.py        → validação Pydantic do corpo do POST
api/main.py          → FastAPI: endpoints e orquestração do fluxo
consumidores/*.py    → um arquivo por serviço, lógica de negócio isolada
infra/main.tf        → Terraform: SQS, S3, SSM no LocalStack
docker-compose.yml   → LocalStack e PostgreSQL em containers
```

---

## 3. Como o SQS substitui o RabbitMQ

### Antes (RabbitMQ)
```
produtor → exchange (topic) → binding → 5 filas
```
O exchange fazia o fan-out automaticamente com uma routing key.

### Agora (SQS)
```
API → publicar_em_todas_filas() → loop envia para cada URL
```
O SQS padrão não tem fan-out nativo. A função `publicar_em_todas_filas` em
`config/sqs.py` publica manualmente em cada uma das 5 filas.

Em produção real, usaríamos **SNS + SQS**: publicamos no SNS uma vez e ele
faz o fan-out automaticamente para todas as filas assinadas.

### Long polling
```python
sqs.receive_message(WaitTimeSeconds=10)
```
Em vez de perguntar ao servidor a cada milissegundo se há mensagem (short polling,
que desperdiça CPU e, em produção, cobra por chamada), o long polling aguarda até
10 segundos na mesma chamada. Muito mais eficiente.

### DLQ automática
No Terraform definimos `redrive_policy` com `maxReceiveCount = 3`.
Isso significa: se a mesma mensagem for recebida 3 vezes sem ser deletada
(ou seja, o consumidor retornou `False` 3 vezes), o **próprio SQS** a move
para a fila `sqs-dead-letter`. Não precisamos escrever esse código.

---

## 4. O fluxo completo de um pedido

```
1. Cliente faz POST /pedidos com JSON

2. FastAPI (api/main.py) orquestra:
   a. Pydantic valida o corpo (api/models.py)
   b. Consulta ViaCEP com o CEP informado (api/viacep.py)
      → Se CEP inválido: retorna HTTP 400
   c. Salva pedido no PostgreSQL com status PENDENTE (api/database.py)
   d. Publica payload nas 5 filas SQS (config/sqs.py)
   e. Retorna {pedido_id, status: PENDENTE, total, endereco}

3. Os 5 consumidores processam em paralelo (processos separados):
   pagamento.py   → valida pagamento → registra_evento(status=APROVADO/RECUSADO)
   estoque.py     → reserva item    → registra_evento(status=RESERVADO/FALHA)
   fiscal.py      → gera NF-e       → salva JSON no S3 → registra_evento(status=EMITIDA)
   logistica.py   → agenda entrega  → registra_evento(status=AGENDADA)
   notificacao.py → simula e-mail   → registra_evento(status=ENVIADA)

4. Se um consumidor falhar:
   → retorna False → SQS mantém a mensagem visível
   → após 3 falhas → SQS move para sqs-dead-letter (DLQ)
```

---

## 5. Por que FastAPI e não Flask?

- **Validação automática** com Pydantic: o JSON inválido é rejeitado antes de chegar
  ao código de negócio, com mensagem de erro clara.
- **Documentação automática** em `/docs`: o professor pode testar os endpoints
  sem precisar de Postman.
- **Async nativo**: a chamada ao ViaCEP usa `httpx` assíncrono — a API não trava
  enquanto espera a resposta do ViaCEP.

---

## 6. O que o Terraform faz exatamente?

O arquivo `infra/main.tf` descreve os recursos que queremos existir no LocalStack.
O Terraform compara o que existe com o que foi descrito e aplica só a diferença.

Recursos criados:
- `aws_sqs_queue.dlq` — Dead Letter Queue
- `aws_sqs_queue.filas` — 5 filas (loop `for_each` evita repetição)
- `aws_s3_bucket.notas_fiscais` — bucket para JSONs de NF-e
- `aws_ssm_parameter.*` — configurações dos serviços no Parameter Store

O bloco `endpoints` no provider diz ao Terraform para chamar `localhost:4566`
em vez da AWS real. As credenciais `test/test` são fictícias e aceitas pelo LocalStack.

---

## 7. O banco de dados (PostgreSQL)

### Tabela `pedidos`
Criada no startup da API. Guarda o estado atual do pedido.

```sql
SELECT id, cliente_nome, produto_nome, total, status, cidade, criado_em
FROM pedidos
ORDER BY criado_em DESC;
```

### Tabela `eventos_pedido`
Linha do tempo de processamento. Cada consumidor insere uma linha.

```sql
SELECT servico, status, mensagem, criado_em
FROM eventos_pedido
WHERE pedido_id = 'UUID-DO-PEDIDO'
ORDER BY criado_em;
```

Resultado esperado após processamento completo:
```
pagamento   | APROVADO  | PIX confirmado instantaneamente
estoque     | RESERVADO | 1 un. reservadas. Saldo: 49
fiscal      | EMITIDA   | NF-e ABC123... | R$ 4599.90
logistica   | AGENDADA  | Correios PAC | BR1A2B3C4D5E | 05/07/2026
notificacao | ENVIADA   | E-mail enviado para joao@email.com
```

---

## 8. O ViaCEP (API externa)

URL chamada: `https://viacep.com.br/ws/{CEP}/json/`

Duas situações de "CEP inválido":
1. Formato errado (não tem 8 dígitos) → detectado localmente antes da chamada
2. CEP com formato correto mas inexistente → ViaCEP retorna `{"erro": true}`

O timeout de 5 segundos garante que a API não trava se o ViaCEP estiver lento.

---

## 9. O que cada consumidor retorna e por quê

```python
def processar(body: str, tentativas: int) -> bool:
    ...
    return True   # deleta a mensagem da fila (ACK)
    return False  # mantém na fila para novo processamento (NACK)
```

O loop `consumir_fila` em `config/sqs.py` chama `sqs.delete_message()` apenas
se o retorno for `True`. Se for `False`, a mensagem fica invisível por 30 segundos
(visibility_timeout) e depois reaparece para reprocessamento.

---

## 10. Perguntas que o professor pode fazer — e as respostas

**Por que usar SQS em vez de continuar com RabbitMQ?**
O SQS é gerenciado pela AWS (não precisamos administrar o broker), integra com
outros serviços AWS (SNS, Lambda, CloudWatch) e é provisionável via Terraform.

**O que é o LocalStack?**
Um emulador de serviços AWS que roda localmente via Docker. Permite desenvolver
e testar sem criar conta na AWS nem pagar nada.

**O que o Terraform provisiona aqui?**
As filas SQS (incluindo DLQ e redrive policy), o bucket S3 para notas fiscais e
parâmetros no SSM Parameter Store. Tudo que seria criado no console AWS.

**O que acontece se um consumidor falhar?**
A mensagem não é deletada da fila (retorno `False`). Após 30 segundos ela fica
visível novamente e é reprocessada. Após 3 falhas, o SQS a move automaticamente
para a DLQ pelo redrive policy configurado no Terraform.

**Por que publicar em 5 filas separadas em vez de uma fila única?**
Com filas separadas cada serviço consome no seu próprio ritmo, sem afetar os outros.
Se o serviço fiscal ficar lento, isso não atrasa o pagamento. Com uma fila única,
teríamos um único consumidor processando sequencialmente.

**O que é long polling?**
Em vez de perguntar ao SQS "tem mensagem?" a cada milissegundo, aguardamos até
10 segundos na mesma chamada. Reduz o número de chamadas de API e o custo em produção.

**O ViaCEP pode falhar. O que acontece?**
O `httpx` tem timeout de 5 segundos. Se o ViaCEP não responder, a exceção é
capturada e a função retorna `None`. A API retorna HTTP 400 ao cliente.

**Por que PostgreSQL e não SQLite?**
O SQLite é um arquivo local — não escala para múltiplos serviços gravando ao mesmo
tempo. O PostgreSQL suporta conexões concorrentes, transações ACID e é o padrão
em sistemas distribuídos em produção.
