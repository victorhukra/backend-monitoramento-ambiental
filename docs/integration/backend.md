# Integração — equipe de retaguarda

**Versão proposta: 1 | 22/10/2026**

MVP: Londrina, meteorologia e ocorrência de chuva na próxima hora. A API, o banco e o serviço ainda serão implementados; o pacote candidato do modelo já está preparado para ser carregado pelo futuro serviço de retaguarda. Enquanto ele não estiver ligado, a simulação histórica deve identificar a resposta como fictícia. GOES fica fora deste contrato inicial.

## Responsabilidade

Receber e validar quatro medidas atuais e a pressão da hora anterior, construir os sete atributos, produzir a resposta, registrar a requisição e o resultado no banco e devolver o JSON à interface. O navegador não acessa o banco diretamente. Até a futura implementação do serviço, manter a resposta fictícia identificada. Na integração, carregar o pacote candidato do modelo sem alterar o formato da API.

## Contrato: POST /predict

`Content-Type: application/json`. Sucesso: **HTTP 201**, após salvar o registro. Local fixo, horizonte fixo de uma hora. Valores abaixo são ilustrativos.

Requisição:

```json
{
  "location": "Londrina-PR",
  "reference_time": "2026-09-01T14:00:00-03:00",
  "weather": {
    "temperature_2m": 24.7,
    "relative_humidity_2m": 74,
    "pressure_msl": 1008.9,
    "cloud_cover": 97,
    "pressure_msl_previous_hour": 1009.4
  }
}
```

Resposta prevista quando o pacote candidato do modelo estiver carregado. Enquanto o serviço de retaguarda retornar uma resposta fictícia, usar `is_mock=true` e `model_version=null`; probabilidade e decisão devem ser identificadas como fictícias.

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
  "is_mock": false,
  "model_version": "weather-v6-simple-mean-isotonic-v1"
}
```

`0.72` é apenas um valor ilustrativo; a API devolve a saída do pacote do modelo carregado. Gerar novo UUID por registro. `rain_predicted = rain_probability >= decision_threshold`. Limiar inicial proposto: 0,5. Ele é um limiar de probabilidade, não quantidade de chuva em mm.

Com o modelo candidato à integração: `is_mock=false` e `model_version="weather-v6-simple-mean-isotonic-v1"`; manter `mode="historical"`. O modelo calcula a probabilidade; não reutilizar 0,72 como previsão real.

## Candidato de modelo para integração

Versão candidata: `weather-v6-simple-mean-isotonic-v1`. O adaptador reutilizável está em `src/models/weather_ensemble.py`; o pacote local do modelo fica em `data/experiments/weather_v6_integration_candidate_20261105T190315Z/weather_ensemble.joblib`. O serviço de retaguarda carrega o pacote do modelo com dependências compatíveis com o manifesto e executa `predict_one(weather, reference_time)`. O pacote do modelo armazena a classe `src.models.weather_ensemble.SimpleMeanCalibratedEnsemble`, portanto esse módulo precisa acompanhar o artefato. Os três Random Forests v6 geram probabilidades; cada uma passa pelo seu calibrador isotônico e então as probabilidades calibradas são combinadas com pesos iguais (1/3). Limiar provisório: 0,50. A resposta deve devolver `rain_probability`, `rain_predicted`, `decision_threshold` e `model_version` do pacote do modelo, sem recalcular a decisão na interface.

O modelo recebe cinco valores meteorológicos: quatro medidas atuais e a pressão ao nível do mar da hora anterior. O adaptador calcula `temp_humidity`, `pressure_diff` e `hour_of_day`. A calibração isotônica é ajustada a partir das previsões fora da amostra da v6; `scripts/package_weather_model.py` registra os hashes e recria o pacote do modelo. A avaliação é retrospectiva; este pacote é candidato de integração, não aprovação operacional independente.

## Validações e horários

- Campos obrigatórios; não aceitar `null`, números não finitos ou valores textuais para as quatro medidas atuais e `pressure_msl_previous_hour`. Rejeitar campos extras para detectar erros de contrato.
- Temperatura em °C; umidade em %; pressão ao nível do mar em hPa; nuvens em %. Umidade/nuvens entre 0 e 100; pressão atual e anterior positivas. Não inventar limites adicionais de qualidade científica nesta integração.
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

Tabela proposta: `predictions`, com ID, data de criação, localização, T, janela, quatro medidas atuais, pressão da hora anterior, probabilidade, decisão, limiar, modo, indicador fictício e versão do modelo. Salvar em uma transação; ver [contrato do Banco](database.md).

A tela deve permitir informar T/entradas, solicitar a previsão e mostrar probabilidade, intervalo, decisão e modo, além dos estados de erro e carregamento. Quando `is_mock=true`, exibir aviso obrigatório de resultado fictício; ver [contrato da interface](frontend.md).

## Entrega mínima e alinhamentos

Implementar primeiro a rota com resposta fictícia identificada e persistência. Testar um sucesso, um 422 e uma indisponibilidade. Demonstrar que o UUID recebido existe no banco com os mesmos valores. Não há garantia de idempotência nesta versão: cada POST bem-sucedido cria um registro; a interface não deve repetir automaticamente a requisição.

Confirmar com a equipe as tecnologias, SGBD, endereço/porta e origem permitida em CORS. URL da API deve ser configurável na interface; credenciais do banco ficam somente no ambiente do serviço de retaguarda. Se a aplicação for exposta fora do desenvolvimento local, combinar autenticação antes da exposição. Histórico/listagem e ingestão em tempo real estão fora desta primeira entrega.
