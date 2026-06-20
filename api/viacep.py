# -*- coding: utf-8 -*-
# api/viacep.py — Integração com API pública ViaCEP
import httpx

VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"

async def consultar_cep(cep: str) -> dict | None:
    cep_limpo = cep.replace("-", "").strip()
    if not cep_limpo.isdigit() or len(cep_limpo) != 8:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(VIACEP_URL.format(cep=cep_limpo))
            data = r.json()
            return None if data.get("erro") else data
    except Exception:
        return None
