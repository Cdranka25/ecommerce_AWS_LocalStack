# -*- coding: utf-8 -*-
# api/correios.py — Cálculo de frete via API pública dos Correios (v2)
#
# A API dos Correios v2 (melhor disponibilidade, sem autenticação para
# consultas básicas de preço/prazo) retorna opções de serviço com
# valor e prazo de entrega por CEP de origem e destino.
#
# Endpoint: https://brasilapi.com.br/api/cep/v2/{cep}
# Frete:    https://ws.correios.com.br/calculador/CalcPrecoPrazo.aspx
#
# Usamos a BrasilAPI como proxy de frete para evitar o WSDL legado.
# Fallback: simulação determinística quando a API estiver offline.

import httpx
from typing import Optional

# CEP de origem (CD Blumenau, como exemplo; troque pelo seu)
CEP_ORIGEM = "89010000"

# Serviços dos Correios
SERVICOS = {
    "PAC":   "04510",   # PAC convencional
    "SEDEX": "04014",   # SEDEX
}


async def calcular_frete(cep_destino: str, peso_gramas: int = 300) -> list[dict]:
    """
    Calcula frete PAC e SEDEX dos Correios.

    Usa a BrasilAPI (https://brasilapi.com.br) como intermediária,
    que por sua vez consome o webservice dos Correios.

    Retorna lista de opções de envio:
        [
          {"servico": "PAC",   "valor": 18.50, "prazo_dias": 7},
          {"servico": "SEDEX", "valor": 32.90, "prazo_dias": 2},
        ]
    """
    cep_limpo = cep_destino.replace("-", "").strip()
    resultado = []

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            for nome, codigo in SERVICOS.items():
                url = (
                    f"https://ws.correios.com.br/calculador/CalcPrecoPrazo.aspx"
                    f"?nCdEmpresa=&sDsSenha=&sCepOrigem={CEP_ORIGEM}"
                    f"&sCepDestino={cep_limpo}&nVlPeso=0.3"
                    f"&nCdFormato=1&nVlComprimento=16&nVlAltura=5&nVlLargura=11"
                    f"&nVlDiametro=0&sCdMaoPropria=n&nVlValorDeclarado=0"
                    f"&sCdAvisoRecebimento=n&nCdServico={codigo}&nVlValorDeclarado=0"
                    f"&StrRetorno=xml&nIndicaCalculo=3"
                )
                r = await client.get(url)

                # Parse simples do XML retornado pelos Correios
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(r.text)
                    servico = root.find(".//cServico")
                    if servico is not None:
                        erro = servico.findtext("Erro", "0")
                        if erro == "0":
                            valor_str = servico.findtext("Valor", "0").replace(",", ".")
                            prazo_str = servico.findtext("PrazoEntrega", "0")
                            resultado.append({
                                "servico": nome,
                                "codigo":  codigo,
                                "valor":   float(valor_str),
                                "prazo_dias": int(prazo_str),
                            })
                        else:
                            resultado.append(_fallback(nome, codigo, cep_limpo))
                except ET.ParseError:
                    resultado.append(_fallback(nome, codigo, cep_limpo))

    except (httpx.TimeoutException, httpx.RequestError):
        # Fallback simulado quando os Correios estiverem offline
        resultado = [
            _fallback("PAC",   SERVICOS["PAC"],   cep_limpo),
            _fallback("SEDEX", SERVICOS["SEDEX"], cep_limpo),
        ]

    return resultado


def _fallback(nome: str, codigo: str, cep: str) -> dict:
    """
    Fallback simulado quando a API dos Correios não responde.
    O valor é estimado com base no DDD do CEP (primeiros 2 dígitos).
    """
    regiao = int(cep[:2])
    # CEPs do Sul: 80000-89999 → mais barato; Norte/Nordeste → mais caro
    multiplicador = 1.0 if 80000 <= regiao * 1000 <= 89999 else 1.6

    if nome == "PAC":
        return {"servico": "PAC",   "codigo": codigo, "valor": round(15.90 * multiplicador, 2), "prazo_dias": 7,  "simulado": True}
    else:
        return {"servico": "SEDEX", "codigo": codigo, "valor": round(29.90 * multiplicador, 2), "prazo_dias": 2,  "simulado": True}
