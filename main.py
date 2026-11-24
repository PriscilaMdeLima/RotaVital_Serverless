"""Rota Vital - funcao serverless HTTP que emite a guia de transporte.

Fluxo: o Rota Vital ja sabe qual hospital fornecedor atende uma requisicao de
insumo (operacao "cruzamento requisicoes x estoque"). Esta funcao recebe essa
decisao e devolve a guia de transporte, calculando distancia geodesica,
prazo de SLA por prioridade e previsao de entrega.

Rodar local:  functions-framework --target=emitir_guia --port=8080
"""
import json
import math
import uuid
from datetime import datetime, timedelta, timezone

import functions_framework
from flask import Response

# --- Premissas do negocio (documentadas no README) ---------------------------
RAIO_TERRA_KM = 6371.0088
VELOCIDADE_MEDIA_KMH = 60.0
TEMPO_PREPARO_H = 1.0
PRAZO_SLA_H = {"URGENTE": 6, "ALTA": 24, "NORMAL": 72}


class ErroValidacao(ValueError):
    """Requisicao com dados invalidos; guarda a lista de problemas."""

    def __init__(self, erros):
        super().__init__("; ".join(erros))
        self.erros = erros


# --- Regras de negocio (puras, sem HTTP) -------------------------------------
def distancia_km(lat1, lon1, lat2, lon2):
    """Distancia geodesica (haversine) entre dois pontos, em km."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(math.sqrt(min(1.0, a)))


def _texto(v):
    return isinstance(v, str) and v.strip() != ""


def _numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _validar_hospital(nome, h, erros):
    if not isinstance(h, dict):
        erros.append(f"{nome}: objeto obrigatorio com hospital, uf, lat e lon")
        return
    if not _texto(h.get("hospital")):
        erros.append(f"{nome}.hospital: texto obrigatorio")
    uf = h.get("uf")
    if not (isinstance(uf, str) and len(uf.strip()) == 2 and uf.strip().isalpha()):
        erros.append(f"{nome}.uf: sigla com 2 letras (ex.: PE)")
    lat, lon = h.get("lat"), h.get("lon")
    if not (_numero(lat) and -90 <= lat <= 90):
        erros.append(f"{nome}.lat: numero entre -90 e 90")
    if not (_numero(lon) and -180 <= lon <= 180):
        erros.append(f"{nome}.lon: numero entre -180 e 180")


def validar(dados):
    """Devolve a lista de erros (vazia = requisicao valida)."""
    if not isinstance(dados, dict):
        return ["corpo: deve ser um objeto JSON"]
    erros = []
    if not _texto(dados.get("requisicaoId")):
        erros.append("requisicaoId: texto obrigatorio")
    if not _texto(dados.get("insumo")):
        erros.append("insumo: texto obrigatorio")
    q = dados.get("quantidade")
    if not (isinstance(q, int) and not isinstance(q, bool) and q > 0):
        erros.append("quantidade: inteiro maior que zero")
    p = dados.get("prioridade")
    if not (isinstance(p, str) and p.strip().upper() in PRAZO_SLA_H):
        erros.append("prioridade: use URGENTE, ALTA ou NORMAL")
    _validar_hospital("origem", dados.get("origem"), erros)
    _validar_hospital("destino", dados.get("destino"), erros)
    if not erros:
        o, d = dados["origem"]["hospital"], dados["destino"]["hospital"]
        if o.strip().casefold() == d.strip().casefold():
            erros.append("origem e destino nao podem ser o mesmo hospital")
    return erros


def _hospital_saida(h):
    return {
        "hospital": h["hospital"].strip(),
        "uf": h["uf"].strip().upper(),
        "lat": h["lat"],
        "lon": h["lon"],
    }


def gerar_guia(dados, agora=None):
    """Valida a requisicao e monta a guia de transporte."""
    erros = validar(dados)
    if erros:
        raise ErroValidacao(erros)

    agora = agora or datetime.now(timezone.utc)
    origem, destino = _hospital_saida(dados["origem"]), _hospital_saida(dados["destino"])
    prioridade = dados["prioridade"].strip().upper()

    dist = distancia_km(origem["lat"], origem["lon"], destino["lat"], destino["lon"])
    tempo_h = TEMPO_PREPARO_H + dist / VELOCIDADE_MEDIA_KMH
    prazo_h = PRAZO_SLA_H[prioridade]

    return {
        "numeroGuia": f"GT-{agora:%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        "emitidaEm": agora.isoformat(timespec="seconds"),
        "requisicaoId": dados["requisicaoId"].strip(),
        "insumo": dados["insumo"].strip(),
        "quantidade": dados["quantidade"],
        "prioridade": prioridade,
        "origem": origem,
        "destino": destino,
        "distanciaKm": round(dist, 1),
        "interestadual": origem["uf"] != destino["uf"],
        "prazoSlaHoras": prazo_h,
        "tempoEstimadoHoras": round(tempo_h, 2),
        "previsaoEntrega": (agora + timedelta(hours=tempo_h)).isoformat(timespec="seconds"),
        "dentroDoSla": tempo_h <= prazo_h,
    }


# --- Camada HTTP (a funcao serverless) ---------------------------------------
def _json(corpo, status=200, headers=None):
    return Response(
        json.dumps(corpo, ensure_ascii=False, indent=2),
        status=status,
        content_type="application/json; charset=utf-8",
        headers=headers,
    )


@functions_framework.http
def emitir_guia(request):
    """POST /  com JSON da requisicao  ->  201 com a guia de transporte."""
    if request.method != "POST":
        return _json({"erro": "Use POST com um JSON no corpo."}, 405, {"Allow": "POST"})

    dados = request.get_json(silent=True)
    if dados is None:
        return _json({"erro": "Corpo ausente ou JSON invalido."}, 400)

    try:
        guia = gerar_guia(dados)
    except ErroValidacao as e:
        return _json({"erro": "Requisicao invalida.", "detalhes": e.erros}, 400)
    return _json(guia, 201)
