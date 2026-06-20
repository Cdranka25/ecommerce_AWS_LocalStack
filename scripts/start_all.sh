#!/bin/bash
echo "====================================================="
echo "  E-commerce Supabase — Iniciando tudo"
echo "====================================================="

echo "[1/3] Subindo LocalStack..."
docker-compose up -d
sleep 12

echo "[2/3] Provisionando via Terraform..."
cd infra && terraform init -upgrade -input=false -no-color > /dev/null 2>&1 && terraform apply -auto-approve && cd ..

echo "[3/3] Iniciando API, frontend e consumidores..."
uvicorn api.main:app --reload --port 8000 &
sleep 2
python launcher_server.py &
python consumidores/pagamento.py   &
python consumidores/estoque.py     &
python consumidores/fiscal.py      &
python consumidores/logistica.py   &
python consumidores/notificacao.py &

echo ""
echo "====================================================="
echo " API:  http://localhost:8000"
echo " Docs: http://localhost:8000/docs"
echo " Para parar: kill \$(jobs -p)"
echo "====================================================="
