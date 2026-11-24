# Rota Vital — Função Serverless: Guia de Transporte

**Atividade individual 1 · Serverless** — Infraestrutura de Software, CESAR School (ADS)
**Autor:** Priscila Maciel de Lima
**Vídeo (até 3 min):** [PREENCHER: link do vídeo]

## 1. O que é

Uma função HTTP que recebe uma requisição do **Rota Vital** e devolve a **guia de transporte**.

No Rota Vital, o cruzamento *requisições × estoque* decide qual hospital fornece cada insumo. A guia é o passo seguinte: o documento que acompanha o transporte. A função recebe a decisão (origem, destino, insumo, quantidade, prioridade) e devolve a guia com:

- número único da guia e data/hora de emissão;
- **distância geodésica** entre os hospitais (fórmula de haversine, a mesma ideia do cruzamento do PI);
- indicação de **transporte interestadual** (UF de origem ≠ UF de destino);
- **prazo de SLA** conforme a prioridade e se a entrega prevista **cumpre o SLA**;
- previsão de entrega.

Por ser uma operação curta, sem estado e acionada sob demanda (só quando há uma transferência a emitir), é um bom caso para serverless: não precisa de servidor ligado o tempo todo.

## 2. Provedor e tecnologia

| Item | Escolha |
|---|---|
| Provedor / emulador | **Google Cloud Functions**, emulado localmente com o **Functions Framework** |
| Linguagem | Python 3.12 |
| Dependências | `functions-framework` (traz o Flask) |

Roda 100% no computador; **não foi publicado na nuvem** (opcional na atividade).

## 3. Como rodar

Pré-requisito: Python 3.10+.

```bash
# 1. ambiente virtual e dependências
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. subir o emulador da função (deixe este terminal aberto)
functions-framework --target=emitir_guia --port=8080
```

A função fica em `http://localhost:8080`.

### Chamando a função

Em **outro terminal** (com o ambiente virtual ativo), a forma mais simples, igual em Windows, Linux e macOS:

```bash
python cliente_demo.py
```

Ele envia os três JSONs da pasta `exemplos/` e mostra o status e a resposta de cada um. Também dá para usar `curl`:

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d @exemplos/requisicao_valida.json
```

## 4. Contrato da função

**`POST /`** com corpo JSON:

| Campo | Tipo | Regra |
|---|---|---|
| `requisicaoId` | texto | obrigatório |
| `insumo` | texto | obrigatório |
| `quantidade` | inteiro | maior que zero |
| `prioridade` | texto | `URGENTE`, `ALTA` ou `NORMAL` (aceita minúsculas) |
| `origem` / `destino` | objeto | `hospital` (texto), `uf` (2 letras), `lat` (−90 a 90), `lon` (−180 a 180) |

Origem e destino não podem ser o mesmo hospital.

| Situação | Resposta |
|---|---|
| Requisição válida | `201` + guia em JSON |
| Dados inválidos | `400` + lista de problemas em `detalhes` |
| Corpo ausente ou JSON malformado | `400` |
| Método diferente de POST | `405` (header `Allow: POST`) |

### Exemplo — requisição válida (`exemplos/requisicao_valida.json`) → `201`

```json
{
  "numeroGuia": "GT-20261124-58AB7A",
  "emitidaEm": "2026-11-24T16:12:24+00:00",
  "requisicaoId": "REQ-1001",
  "insumo": "Concentrado de hemacias O-",
  "quantidade": 10,
  "prioridade": "URGENTE",
  "origem":  { "hospital": "Hospital da Restauracao", "uf": "PE", "lat": -8.0476, "lon": -34.877 },
  "destino": { "hospital": "Hospital Regional do Agreste", "uf": "PE", "lat": -8.276, "lon": -35.976 },
  "distanciaKm": 123.6,
  "interestadual": false,
  "prazoSlaHoras": 6,
  "tempoEstimadoHoras": 3.06,
  "previsaoEntrega": "2026-11-24T19:16:00+00:00",
  "dentroDoSla": true
}
```

O exemplo `requisicao_interestadual.json` (Recife → Fortaleza, URGENTE) devolve `distanciaKm: 627.0`, `interestadual: true` e **`dentroDoSla: false`** (11,45 h estimadas para um prazo de 6 h). O `requisicao_invalida.json` devolve `400` com quatro problemas listados. As respostas completas estão em [`docs/evidencias/respostas_dos_exemplos.txt`](docs/evidencias/respostas_dos_exemplos.txt).

## 5. Premissas de negócio

São valores de **demonstração** (simplificações assumidas, não dados oficiais):

| Premissa | Valor |
|---|---|
| Velocidade média de transporte | 60 km/h |
| Tempo de preparo/separação | 1 h |
| Tempo estimado | preparo + distância ÷ velocidade |
| Prazo de SLA | URGENTE 6 h · ALTA 24 h · NORMAL 72 h |
| Distância | geodésica (haversine, raio da Terra 6371,0088 km), em linha reta, não rota por estrada |

## 6. Testes automatizados

```bash
python -m unittest discover -v
```

30 testes (`tests/`): distância (ponto igual, simetria, Recife–Fortaleza ≈ 630 km), montagem da guia (campos, formato do número, interestadual, SLA dentro e fora do prazo, normalização), validações (campos obrigatórios, quantidade, prioridade, coordenadas, UF, origem = destino) e a camada HTTP (201, 400, 405, JSON malformado). Saída em [`docs/evidencias/saida_testes.txt`](docs/evidencias/saida_testes.txt): **30 testes, OK**.

> Os testes de HTTP usam o Flask diretamente (sem subir o emulador), o que os deixa rápidos. O emulador real é exercitado com `cliente_demo.py`.

## 7. Evidências

- [x] Print do emulador rodando (`functions-framework ... --port=8080`) → `docs/evidencias/01_emulador_rodando.png`
- [x] Print do `python cliente_demo.py` com as três respostas (201, 201, 400) → `docs/evidencias/02_cliente_demo.png`
- [x] Print dos testes passando → `docs/evidencias/03_testes_ok.png`
- [x] Saída textual dos testes → `docs/evidencias/saida_testes.txt`
- [x] Respostas dos exemplos → `docs/evidencias/respostas_dos_exemplos.txt`

Depois de tirar os prints, inclua-os aqui, por exemplo: `![emulador](docs/evidencias/01_emulador_rodando.png)`.

## 8. Decisões

| Decisão | Alternativas | Justificativa |
|---|---|---|
| Google Cloud Functions + Functions Framework | AWS Lambda (SAM), Azure Functions, Cloudflare Workers | Emulador local de um comando, sem conta nem cartão; o mesmo código roda na nuvem sem mudanças. |
| Python | Java (stack do PI), Node.js | Função pequena: Python reduz o código de configuração. A regra (haversine + SLA) é simples de portar para Java depois. |
| Lógica de negócio separada da camada HTTP | Tudo dentro do handler | Regras testáveis sem HTTP; o handler só traduz entrada e saída. |
| Rodar só local | Publicar na nuvem | Publicar é opcional na atividade; evita custo e configuração de credenciais. |
| Biblioteca padrão (`unittest`, `urllib`) | pytest, requests | Nenhuma dependência extra além do Functions Framework. |
| Guia sem persistência | Gravar a guia em banco | Função sem estado, como o serverless pede; a persistência ficaria no sistema que chama. |

## 9. Uso de IA

Usei o Claude para gerar o esqueleto do projeto, a partir do enunciado da atividade. Eu executei os testes e o emulador, conferi as respostas e revisei o código. Prompt principal: 'prepare essa entrega de Serverless de forma simples mas completa com tudo que foi solicitado'

## 10. Publicar na nuvem (opcional, não executado)

Com a Google Cloud CLI configurada, o mesmo código poderia ser publicado com algo como:

```bash
gcloud functions deploy emitir-guia --gen2 --runtime=python312 \
  --region=southamerica-east1 --source=. --entry-point=emitir_guia \
  --trigger-http --allow-unauthenticated
```

## Estrutura

```
main.py               função emitir_guia + regras de negócio
requirements.txt      functions-framework
cliente_demo.py       envia os exemplos para o emulador
exemplos/             requisições de exemplo (válida, interestadual, inválida)
tests/                30 testes automatizados
docs/evidencias/      saídas de teste e respostas (adicione aqui seus prints)
docs/roteiro_video.md roteiro do vídeo de 3 minutos
```
