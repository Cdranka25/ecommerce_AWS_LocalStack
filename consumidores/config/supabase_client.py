# -*- coding: utf-8 -*-
# config/supabase_client.py
# Cliente Supabase reutilizado por toda a API.
# supabase_admin usa a service role key (ignora RLS) — só para
# operações internas do backend (consumidores, fiscal etc.).
# supabase_client usa a anon key + token do usuário para operações
# que devem respeitar as Row Level Security policies.

from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY

# Cliente público (anon) — respeita RLS
def get_supabase(token: str | None = None) -> Client:
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    if token:
        client.auth.set_session(token, "")
    return client

# Cliente admin (service role) — ignora RLS, só para uso interno
def get_supabase_admin() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
