# -*- coding: utf-8 -*-
# api/main.py — Servidor principal FastAPI
#
# Rotas:
#   POST   /auth/register          — cadastro de usuário
#   POST   /auth/login             — login (retorna JWT)
#   POST   /auth/logout            — logout
#
#   GET    /produtos                — listar produtos disponíveis
#   GET    /produtos/{id}           — detalhar produto
#
#   GET    /enderecos               — endereços do usuário logado   [auth]
#   POST   /enderecos               — cadastrar endereço            [auth]
#   DELETE /enderecos/{id}          — remover endereço              [auth]
#
#   GET    /frete?cep=XXXXXXXX      — calcular frete (Correios)
#
#   POST   /pedidos                 — criar pedido                  [auth]
#   GET    /pedidos                 — pedidos do usuário logado     [auth]
#   GET    /pedidos/{id}            — detalhe + status              [auth]

import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware

from api.auth    import get_current_user
from api.models  import RegisterRequest, LoginRequest, EnderecoRequest, PedidoRequest, RefreshRequest
from api.viacep  import consultar_cep
from api.correios import calcular_frete
from config.supabase_client import get_supabase, get_supabase_admin
from config.sqs  import publicar_em_todas_filas

app = FastAPI(
    title="E-commerce Distribuído com Supabase",
    description="Auth + BD via Supabase | Frete via Correios | Mensageria via SQS (LocalStack)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════

@app.post("/auth/register", tags=["auth"], status_code=201)
async def register(req: RegisterRequest):
    """
    Cria conta nova. O Supabase envia e-mail de confirmação
    automaticamente (se Email Confirmations estiver ativo).
    """
    sb = get_supabase()
    try:
        res = sb.auth.sign_up({
            "email":    req.email,
            "password": req.senha,
            "options":  {"data": {"nome": req.nome}},
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if res.user is None:
        raise HTTPException(status_code=400, detail="Erro ao criar usuário — verifique o e-mail.")

    return {
        "message": "Usuário criado com sucesso! Verifique seu e-mail para confirmar a conta.",
        "user_id": res.user.id,
        "email":   res.user.email,
    }


@app.post("/auth/login", tags=["auth"])
async def login(req: LoginRequest):
    """
    Autentica o usuário. Retorna access_token (JWT) para ser
    enviado como Bearer token nas rotas protegidas.
    """
    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({
            "email":    req.email,
            "password": req.senha,
        })
    except Exception as e:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

    if res.session is None:
        raise HTTPException(status_code=401, detail="Falha na autenticação.")

    return {
        "access_token":  res.session.access_token,
        "refresh_token": res.session.refresh_token,
        "token_type":    "bearer",
        "user": {
            "id":    res.user.id,
            "email": res.user.email,
            "nome":  res.user.user_metadata.get("nome", ""),
        },
    }


@app.post("/auth/logout", tags=["auth"])
async def logout(user=Depends(get_current_user)):
    sb = get_supabase(user["token"])
    sb.auth.sign_out()
    return {"message": "Logout realizado com sucesso."}

@app.post("/auth/refresh", tags=["auth"])
async def refresh_token(req: RefreshRequest):
    """
    Renova o access_token usando o refresh_token.
    Chamado automaticamente pelo frontend quando recebe 401.
    """
    sb = get_supabase()
    try:
        res = sb.auth.refresh_session(req.refresh_token)
        if not res.session:
            raise HTTPException(status_code=401, detail="Refresh token inválido.")
        return {
            "access_token":  res.session.access_token,
            "refresh_token": res.session.refresh_token,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")


# ═══════════════════════════════════════════════════════════
#  PRODUTOS
# ═══════════════════════════════════════════════════════════

@app.get("/produtos", tags=["produtos"])
async def listar_produtos():
    """Lista todos os produtos ativos. Dados inseridos via SQL no Supabase."""
    sb = get_supabase_admin()
    res = sb.table("produtos").select("*").eq("ativo", True).order("nome").execute()
    return res.data


@app.get("/produtos/{produto_id}", tags=["produtos"])
async def detalhar_produto(produto_id: str):
    sb = get_supabase_admin()
    res = sb.table("produtos").select("*").eq("id", produto_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return res.data


# ═══════════════════════════════════════════════════════════
#  ENDEREÇOS
# ═══════════════════════════════════════════════════════════

@app.get("/enderecos", tags=["enderecos"])
async def listar_enderecos(user=Depends(get_current_user)):
    """Retorna os endereços cadastrados pelo usuário logado."""
    sb = get_supabase_admin()
    res = (
        sb.table("enderecos")
        .select("*")
        .eq("user_id", user["user_id"])
        .order("principal", desc=True)
        .execute()
    )
    return res.data


@app.post("/enderecos", tags=["enderecos"], status_code=201)
async def cadastrar_endereco(req: EnderecoRequest, user=Depends(get_current_user)):
    """
    Cadastra um novo endereço para o usuário.
    Se 'principal=True', desmarca o principal anterior.
    O CEP é validado e enriquecido via ViaCEP.
    """
    # Valida CEP via ViaCEP
    dados_cep = await consultar_cep(req.cep)
    if not dados_cep:
        raise HTTPException(status_code=400, detail=f"CEP '{req.cep}' inválido ou não encontrado.")

    sb = get_supabase_admin()

    # Se marcou como principal, desmarca o anterior
    if req.principal:
        sb.table("enderecos").update({"principal": False}).eq("user_id", user["user_id"]).execute()

    endereco = {
        "id":          str(uuid.uuid4()),
        "user_id":     user["user_id"],
        "apelido":     req.apelido,
        "cep":         dados_cep.get("cep", req.cep),
        "logradouro":  req.logradouro or dados_cep.get("logradouro", ""),
        "numero":      req.numero,
        "complemento": req.complemento or "",
        "bairro":      req.bairro or dados_cep.get("bairro", ""),
        "cidade":      req.cidade or dados_cep.get("localidade", ""),
        "uf":          req.uf or dados_cep.get("uf", ""),
        "principal":   req.principal,
    }

    res = sb.table("enderecos").insert(endereco).execute()
    return {"message": "Endereço cadastrado com sucesso.", "endereco": res.data[0]}


@app.delete("/enderecos/{endereco_id}", tags=["enderecos"])
async def remover_endereco(endereco_id: str, user=Depends(get_current_user)):
    sb = get_supabase_admin()
    sb.table("enderecos").delete().eq("id", endereco_id).eq("user_id", user["user_id"]).execute()
    return {"message": "Endereço removido."}


# ═══════════════════════════════════════════════════════════
#  FRETE
# ═══════════════════════════════════════════════════════════

@app.get("/frete", tags=["frete"])
async def calcular(cep: str = Query(..., description="CEP de destino (somente dígitos)")):
    """
    Calcula frete PAC e SEDEX dos Correios para o CEP informado.
    Retorna valor e prazo estimado para cada modalidade.
    """
    cep_limpo = cep.replace("-", "").strip()
    opcoes = await calcular_frete(cep_limpo)
    return {"cep_destino": cep_limpo, "opcoes_frete": opcoes}


# ═══════════════════════════════════════════════════════════
#  PEDIDOS
# ═══════════════════════════════════════════════════════════

@app.post("/pedidos", tags=["pedidos"], status_code=201)
async def criar_pedido(req: PedidoRequest, user=Depends(get_current_user)):
    """
    Cria um pedido. Fluxo:
      1. Busca produto e endereço no Supabase
      2. Calcula frete via Correios
      3. Persiste pedido no Supabase
      4. Publica nas 5 filas SQS para processamento assíncrono
    """
    sb = get_supabase_admin()

    # 1a. Busca produto
    prod_res = sb.table("produtos").select("*").eq("id", req.produto_id).single().execute()
    if not prod_res.data:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    produto = prod_res.data

    # 1b. Verifica estoque
    if produto["estoque"] < req.quantidade:
        raise HTTPException(
            status_code=400,
            detail=f"Estoque insuficiente. Disponível: {produto['estoque']} unidades."
        )

    # 1c. Busca endereço do usuário
    end_res = (
        sb.table("enderecos")
        .select("*")
        .eq("id", req.endereco_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )
    if not end_res.data:
        raise HTTPException(status_code=404, detail="Endereço não encontrado ou não pertence ao usuário.")
    endereco = end_res.data

    # 2. Calcula frete
    opcoes_frete = await calcular_frete(endereco["cep"])
    frete_escolhido = opcoes_frete[0] if opcoes_frete else {"servico": "PAC", "valor": 0, "prazo_dias": 7}

    # 3. Monta e persiste pedido
    pedido_id   = str(uuid.uuid4())
    subtotal    = round(produto["preco"] * req.quantidade, 2)
    valor_frete = frete_escolhido["valor"]
    total       = round(subtotal + valor_frete, 2)

    pedido_db = {
        "id":              pedido_id,
        "user_id":         user["user_id"],
        "produto_id":      req.produto_id,
        "produto_nome":    produto["nome"],
        "produto_preco":   produto["preco"],
        "quantidade":      req.quantidade,
        "subtotal":        subtotal,
        "frete_servico":   frete_escolhido["servico"],
        "frete_valor":     valor_frete,
        "frete_prazo":     frete_escolhido["prazo_dias"],
        "total":           total,
        "forma_pagamento": req.forma_pagamento,
        "status":          "PENDENTE",
        "endereco_id":     req.endereco_id,
        "endereco_cep":    endereco["cep"],
        "endereco_cidade": endereco["cidade"],
        "endereco_uf":     endereco["uf"],
        "criado_em":       datetime.utcnow().isoformat(),
    }

    sb.table("pedidos").insert(pedido_db).execute()

    # 4. Publica nas filas SQS para processamento assíncrono
    payload_sqs = {
        **pedido_db,
        "cliente": {"email": user["email"]},
        "endereco_entrega": {
            "cep":        endereco["cep"],
            "logradouro": endereco["logradouro"],
            "numero":     endereco["numero"],
            "bairro":     endereco["bairro"],
            "cidade":     endereco["cidade"],
            "uf":         endereco["uf"],
        },
        "pedido_id": pedido_id,
    }
    publicar_em_todas_filas(payload_sqs)

    return {
        "pedido_id":     pedido_id,
        "status":        "PENDENTE",
        "subtotal":      subtotal,
        "frete":         frete_escolhido,
        "total":         total,
        "forma_pagamento": req.forma_pagamento,
        "entrega":       f"{endereco['cidade']}-{endereco['uf']}",
    }


@app.get("/pedidos", tags=["pedidos"])
async def listar_pedidos(user=Depends(get_current_user)):
    """Lista os pedidos do usuário logado."""
    sb = get_supabase_admin()
    res = (
        sb.table("pedidos")
        .select("id, produto_nome, quantidade, subtotal, frete_valor, total, status, forma_pagamento, criado_em, endereco_cidade, endereco_uf, frete_servico, frete_prazo")
        .eq("user_id", user["user_id"])
        .order("criado_em", desc=True)
        .limit(20)
        .execute()
    )
    return res.data


@app.get("/pedidos/{pedido_id}", tags=["pedidos"])
async def detalhar_pedido(pedido_id: str, user=Depends(get_current_user)):
    """Detalhe do pedido + eventos de processamento."""
    sb = get_supabase_admin()

    ped = (
        sb.table("pedidos")
        .select("*")
        .eq("id", pedido_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )
    if not ped.data:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    eventos = (
        sb.table("eventos_pedido")
        .select("*")
        .eq("pedido_id", pedido_id)
        .order("criado_em")
        .execute()
    )

    return {**ped.data, "eventos": eventos.data}


# ── Health check ─────────────────────────────────────────────
@app.get("/", tags=["infra"])
def health():
    return {"status": "ok", "versao": "2.0.0", "timestamp": datetime.utcnow().isoformat()}
