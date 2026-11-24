"""Cliente de demonstracao: envia os JSONs de exemplos/ para a funcao local.

Uso:  python cliente_demo.py                 (usa http://localhost:8080)
      python cliente_demo.py http://localhost:8080
Funciona igual no Windows, Linux e macOS (so biblioteca padrao).
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
ARQUIVOS = [
    "requisicao_valida.json",
    "requisicao_interestadual.json",
    "requisicao_invalida.json",
]


def enviar(caminho):
    corpo = Path(caminho).read_bytes()
    req = urllib.request.Request(
        URL, data=corpo, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


for nome in ARQUIVOS:
    status, texto = enviar(Path(__file__).parent / "exemplos" / nome)
    print(f"\n=== POST {nome} -> HTTP {status} ===")
    print(json.dumps(json.loads(texto), ensure_ascii=False, indent=2))
