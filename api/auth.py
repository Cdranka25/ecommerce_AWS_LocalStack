# -*- coding: utf-8 -*-
# api/auth.py — Validação do JWT emitido pelo Supabase (ES256)
#
# O Supabase usa ES256 (ECDSA) com chaves rotativas.
# A verificação é feita buscando a chave pública via JWKS endpoint.

import httpx
from functools import lru_cache
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from jose.backends import ECKey
from config.settings import SUPABASE_URL

bearer_scheme = HTTPBearer()

JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """
    Busca as chaves públicas do Supabase (JWKS).
    Cache em memória — reinicia junto com a API.
    """
    try:
        r = httpx.get(JWKS_URL, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise RuntimeError(f"Não foi possível buscar JWKS do Supabase: {e}")


def get_public_key(kid: str):
    """Retorna a chave pública correspondente ao kid do token."""
    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    # Se não encontrou, limpa cache e tenta de novo (chave pode ter rotacionado)
    get_jwks.cache_clear()
    jwks = get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Chave pública não encontrada para este token."
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Valida o JWT do Supabase usando ES256 + JWKS.
    Retorna payload com user_id, email e token.
    """
    token = credentials.credentials

    try:
        # Pega o kid do header sem verificar ainda
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg", "ES256")

        # Busca a chave pública correta
        public_key_data = get_public_key(kid)

        # Decodifica e verifica o token
        payload = jwt.decode(
            token,
            public_key_data,
            algorithms=[alg],
            options={"verify_aud": False},
        )

        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: sem user_id."
            )

        return {
            "user_id": user_id,
            "email":   payload.get("email", ""),
            "token":   token,
        }

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token expirado ou inválido: {e}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erro na autenticação: {e}"
        )
