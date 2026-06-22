from dotenv import load_dotenv
import os, json, base64
load_dotenv()

secret = os.getenv('JWT_SECRET', '')
print('JWT_SECRET (primeiros 30):', repr(secret[:30]))

# Pega o token do arquivo de log ou cole um token real aqui
token = input("Cole o access_token aqui: ")

# Decodifica o payload sem verificar assinatura
try:
    parts = token.split('.')
    payload = parts[1] + '=='
    decoded = json.loads(base64.b64decode(payload))
    print('\nPayload do token:')
    for k, v in decoded.items():
        print(f'  {k}: {v}')
except Exception as e:
    print('Erro ao decodificar:', e)