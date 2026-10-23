# Integração — equipe Backend

**Versão proposta: 1 | 22/10/2026**

MVP: Londrina, meteorologia e ocorrência de chuva na próxima hora. Inicialmente, simulação histórica com resposta fictícia identificada. Este documento define o acordo de integração; não indica que a API, o banco ou o modelo já estão implementados. GOES fica fora deste contrato inicial.

## Responsabilidade

Receber e validar as quatro entradas, produzir a resposta, registrar request/resultado no banco e devolver o JSON ao Front-End. O navegador não acessa o banco diretamente. Quando o modelo ficar pronto, substituir a resposta fictícia sem mudar o formato da API.

## Contrato: POST /predict

`Content-Type: application/json`. Sucesso: **HTTP 201**, após salvar o registro. Local fixo, horizonte fixo de uma hora. Valores abaixo são ilustrativos.

Request:

```json
{
  "location": "Londrina-PR",
  "reference_time": "2026-09-01T14:00:00-03:00",
  "weather": {
    "temperature_2m": 24.7,
    "relative_humidity_2m": 74,
    "pressure_msl": 1008.9,
    "cloud_cover": 97
  }
}
```

Response:

```json
{
  "prediction_id": "550e8400-e29b-41d4-a716-446655440000",
  "location": "Londrina-PR",
  "reference_time": "2026-09-01T14:00:00-03:00",
  "forecast_start": "2026-09-01T14:00:00-03:00",
  "forecast_end": "2026-09-01T15:00:00-03:00",
  "horizon_hours": 1,
  "rain_probability": 0.72,
  "rain_predicted": true,
  "decision_threshold": 0.5,
  "mode": "historical",
  "is_mock": true,
  "model_version": null
}
```

`0.72` é fictício. Gerar novo UUID por registro. `rain_predicted = rain_probability >= decision_threshold`. Limiar inicial proposto: 0,5. Ele é um limiar de probabilidade, não quantidade de chuva em mm.

Com modelo: `is_mock=false` e `model_version="weather-v1"`; manter `mode="historical"` enquanto as entradas forem históricas. O modelo calcula a probabilidade; não reutilizar 0,72 como previsão real.

## Validações e horários

- Campos obrigatórios; não aceitar `null`, números não finitos ou valores textuais para as quatro medidas. Rejeitar campos extras para detectar erros de contrato.
- Temperatura em °C; umidade em %; pressão ao nível do mar em hPa; nuvens em %. Umidade/nuvens entre 0 e 100; pressão positiva. Não inventar limites adicionais de qualidade científica nesta integração.
- `location` deve ser `Londrina-PR`. `reference_time` deve conter offset e corresponder à hora cheia em `America/Sao_Paulo`.
- T é o horário de referência histórico. A janela prevista é **(T, T+1h]**. `created_at` no banco é a hora atual da requisição, diferente de T.
- Normalizar instantes para UTC no banco e devolver timestamps com offset. Exibir na tela em `America/Sao_Paulo`.
- Na preparação do modelo, o alinhamento de rain à hora anterior permanece hipótese documentada. A interface não comprova disponibilidade histórica das entradas nem operação em tempo real.

Erro de entrada — **HTTP 422**:

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "relative_humidity_2m deve estar entre 0 e 100.",
    "field": "weather.relative_humidity_2m"
  }
}
```

Falha de modelo ou persistência — **HTTP 503**: mesmo envelope, código `PREDICTION_UNAVAILABLE`, mensagem legível e `field: null`. Não retornar probabilidade zero nem sucesso sem salvar. Não expor detalhes internos ou credenciais.

## Banco e tela

Tabela proposta: `predictions`, com ID, data de criação, localização, T, janela, quatro entradas, probabilidade, decisão, limiar, modo, indicador fictício e versão do modelo. Salvar em uma transação; ver [contrato do Banco](database.md).

A tela deve permitir informar T/entradas, solicitar a previsão e mostrar probabilidade, intervalo, decisão, modo e erro/carregamento. Quando `is_mock=true`, aviso obrigatório de resultado fictício; ver [contrato do Front-End](frontend.md).

## Entrega mínima e alinhamentos

Implementar primeiro a rota com mock identificado e persistência. Testar um sucesso, um 422 e uma indisponibilidade. Demonstrar que o UUID recebido existe no banco com os mesmos valores. Não há garantia de idempotência nesta versão: cada POST bem-sucedido cria um registro; o Front-End não deve repetir automaticamente a requisição.

Confirmar com a equipe o framework, SGBD, endereço/porta e origem permitida em CORS. URL da API deve ser configurável no Front-End; credenciais do banco ficam somente no ambiente do Backend. Se a aplicação for exposta fora do desenvolvimento local, combinar autenticação antes da exposição. Histórico/listagem e ingestão em tempo real estão fora desta primeira entrega.
