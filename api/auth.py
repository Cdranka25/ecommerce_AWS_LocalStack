# -*- coding: utf-8 -*-
# api/auth.py — Validação do JWT emitido pelo Supabase Auth
#
# O Supabase emite tokens JWT a cada login. O FastAPI valida
# o token em cada requisição protegida via Depends(get_current_user).
# Não precisamos armazenar senhas — o Supabase gerencia tudo isso.

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from config.settings import JWT_SECRET

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Extrai e valida o JWT do header Authorization: Bearer <token>.
    Retorna o payload com user_id (sub), email etc.
    Lança 401 se o token for inválido ou expirado.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Supabase não usa audience padrão
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        return {"user_id": user_id, "email": payload.get("email", ""), "token": token}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado ou inválido")
