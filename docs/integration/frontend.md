# Integração — equipe responsável pela interface

**Versão proposta: 1 | 22/10/2026**

Objetivo: uma tela simples para solicitar e visualizar previsão de chuva na próxima hora em Londrina. MVP histórico, inicialmente com resposta fictícia. API ainda a implementar; manter o formato alinhado ao [serviço de retaguarda](backend.md).

## Componentes mínimos da tela

1. Título “Previsão de chuva — Londrina” e indicação “Simulação histórica”.
2. Data e hora de referência T, com horas inteiras e fuso `America/Sao_Paulo` identificado.
3. Cinco campos numéricos: temperatura (°C), umidade (%), pressão atual ao nível do mar (hPa), cobertura de nuvens (%) e pressão ao nível do mar da hora anterior (hPa).
4. Botão “Calcular previsão”, desabilitado enquanto a solicitação estiver em andamento.
5. Resultado: probabilidade em porcentagem, “Chuva prevista”/“Sem chuva prevista” e início/fim do intervalo.
6. Aviso destacado **“Demonstração — resultado fictício”** quando `is_mock=true`. Mesmo com modelo real, manter a indicação histórica quando `mode="historical"`.
7. Mensagem de erro legível; nunca mostrar erro ou ausência como “0% de chuva”.

Pode existir botão “Preencher exemplo”, mas seus valores devem ser identificados como ilustrativos. Não precisamos de mapa, radar ou gráficos complexos para esta versão. Não apresentar “72% de acurácia”: o valor retornado é uma probabilidade, não avaliação do modelo.

## Requisição

**POST /predict**, `Content-Type: application/json`. URL-base configurável, acordada com o serviço de retaguarda; nenhuma credencial de banco no navegador.

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

Enviar números JSON, não strings com unidades. `pressure_msl_previous_hour` representa T-1h e é necessário para reproduzir `pressure_diff`. Umidade/nuvens: 0–100; pressões atual/anterior: positivas; todos os campos obrigatórios. Não enviar `rain` futuro, `rain_predicted`, `is_mock` ou probabilidade na requisição: são responsabilidades do serviço de retaguarda.

Converter corretamente o horário escolhido em `America/Sao_Paulo` para ISO 8601 com offset. Um campo de data/hora sem fuso não deve ser enviado diretamente nem interpretado automaticamente no fuso do computador do usuário. T é histórico, diferente da hora atual do clique.

## Resposta prevista quando o serviço de retaguarda usar o modelo candidato — HTTP 201. Enquanto retornar uma resposta fictícia, o serviço de retaguarda deve enviar `is_mock=true` e `model_version=null`, e a interface deve exibir o aviso de resultado fictício.

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

Exibir `rain_probability × 100`: neste exemplo ilustrativo, 72%. Usar `rain_predicted` para o texto de decisão, sem inventar outro limiar na tela. Mostrar a janela “das 14h às 15h” em horário de Londrina. Um resultado positivo indica ocorrência em algum momento da janela, não chuva contínua durante toda a hora.

Com modelo real, o formato permanece: `is_mock=false`, versão preenchida e valores calculados. Remover somente o aviso de resultado fictício; não remover a indicação histórica.

## Erros e comportamento

**HTTP 422**, por exemplo:

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "relative_humidity_2m deve estar entre 0 e 100.",
    "field": "weather.relative_humidity_2m"
  }
}
```

Destacar o campo indicado. **HTTP 503** usa o mesmo envelope com `PREDICTION_UNAVAILABLE` e `field: null`; mostrar indisponibilidade. Em erro de rede, informar que não foi possível confirmar a resposta; não repetir POST automaticamente. Evitar duplo clique, pois cada POST bem-sucedido gera um registro.

Ao editar entradas ou fazer nova solicitação, não deixar resultado antigo parecer calculado para os novos valores. Limpar o resultado ou identificá-lo como anterior.

## Relação com o banco e aceite

O serviço de retaguarda grava uma linha em `predictions` com entradas, resultado, horários e versão, e devolve seu UUID. A interface não grava diretamente no banco. Detalhes em [Banco de Dados](database.md).

Entrega aceita quando a tela envia o exemplo, mostra resposta/aviso fictício, trata 422/503, respeita o fuso e não mistura resultados antigos com entradas novas. URL/CORS e estrutura tecnológica visual ainda precisam ser combinados. Não há rota de histórico ou promessa de previsão em tempo real nesta versão.
