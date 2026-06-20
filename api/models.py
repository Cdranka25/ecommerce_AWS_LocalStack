# -*- coding: utf-8 -*-
# api/models.py — Modelos Pydantic para validação de entrada
from pydantic import BaseModel, field_validator
from typing import Literal, Optional


class RegisterRequest(BaseModel):
    email: str
    senha: str
    nome:  str

class LoginRequest(BaseModel):
    email: str
    senha: str

class EnderecoRequest(BaseModel):
    """Endereço que o usuário cadastra no perfil dele."""
    apelido:    str            # ex: "Casa", "Trabalho"
    cep:        str
    logradouro: str
    numero:     str
    complemento: Optional[str] = ""
    bairro:     str
    cidade:     str
    uf:         str
    principal:  bool = False   # endereço padrão do usuário

    @field_validator("cep")
    @classmethod
    def cep_formato(cls, v):
        limpo = v.replace("-", "").strip()
        if not limpo.isdigit() or len(limpo) != 8:
            raise ValueError("CEP deve ter 8 dígitos")
        return limpo

class PedidoRequest(BaseModel):
    """Corpo do POST /pedidos."""
    produto_id:      str
    quantidade:      int = 1
    endereco_id:     str           # UUID do endereço salvo no Supabase
    forma_pagamento: Literal["pix", "boleto", "cartao_credito"] = "pix"

    @field_validator("quantidade")
    @classmethod
    def quantidade_positiva(cls, v):
        if v < 1:
            raise ValueError("Quantidade deve ser pelo menos 1")
        return v
