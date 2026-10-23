# Integração — equipe Banco de Dados

**Versão proposta: 1 | 22/10/2026**

Objetivo: persistir entradas e resultados do MVP meteorológico para Londrina. Uma tabela inicial é suficiente; não armazenar os NPZ ou o acervo GOES nela. SGBD ainda a combinar. Os tipos abaixo usam PostgreSQL apenas como referência e devem ser adaptados caso a equipe escolha outro banco.

## Tabela proposta: predictions

Todos os campos são obrigatórios, exceto `model_version`, que fica nulo quando a resposta é fictícia.

| Campo | Tipo sugerido | Regra |
|---|---|---|
| prediction_id | UUID | Chave primária; gerado pelo Backend |
| created_at | TIMESTAMPTZ | Instante real da gravação; padrão CURRENT_TIMESTAMP |
| location | VARCHAR(40) | `Londrina-PR` |
| reference_time | TIMESTAMPTZ | T histórico; não confundir com created_at |
| forecast_start | TIMESTAMPTZ | Igual a reference_time |
| forecast_end | TIMESTAMPTZ | reference_time + 1 hora |
| horizon_hours | SMALLINT | Igual a 1 |
| temperature_2m | DOUBLE PRECISION | °C, finito |
| relative_humidity_2m | DOUBLE PRECISION | %, finito, entre 0 e 100 |
| pressure_msl | DOUBLE PRECISION | hPa, finito e positivo |
| cloud_cover | DOUBLE PRECISION | %, finito, entre 0 e 100 |
| rain_probability | DOUBLE PRECISION | Finito, entre 0 e 1 |
| rain_predicted | BOOLEAN | probability >= decision_threshold |
| decision_threshold | DOUBLE PRECISION | Finito, entre 0 e 1; proposta inicial 0,5 |
| mode | VARCHAR(20) | `historical` nesta versão |
| is_mock | BOOLEAN | Distingue resultado fictício de resultado do modelo |
| model_version | VARCHAR(80), nullable | Nulo no mock; preenchido quando is_mock=false |

Implementar `NOT NULL`, chave primária e restrições compatíveis com essas regras. Validar finitude também no Backend; não confiar somente no intervalo do tipo numérico. Se necessário para consultas, adicionar índice em `reference_time`. **Não criar UNIQUE por localização/T:** podemos repetir o mesmo instante com modelos ou entradas diferentes. Um POST bem-sucedido corresponde a uma linha.

Guardar instantes de forma consistente em UTC; o front-end exibe `America/Sao_Paulo`. Tipos com fuso preservam o instante, não necessariamente a zona original como texto. O contrato fixa a zona de apresentação.

## Contrato recebido pelo Backend

**POST /predict**, JSON. Os campos de `weather` são mapeados para as quatro colunas numéricas.

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

## Resposta após persistir — HTTP 201

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

Exemplo inteiramente ilustrativo. `created_at` é interno ao registro e não precisa aparecer nesta resposta. O UUID e a probabilidade devolvidos devem ser os mesmos persistidos. Com modelo real: `is_mock=false`, versão preenchida, probabilidade calculada. Não comparar resultados fictícios como desempenho de modelo.

## Fluxo de gravação e falhas

1. Backend valida a entrada e calcula/mocka a resposta.
2. Backend grava todos os campos em uma transação usando consultas parametrizadas.
3. Somente após confirmação da gravação, retorna HTTP 201.
4. Se persistência/modelo falhar, retorna HTTP 503 com `error.code="PREDICTION_UNAVAILABLE"`, mensagem legível e `error.field=null`, sem dados internos de conexão. Entrada inválida retorna HTTP 422; não cria linha.

O front-end não possui credenciais do banco. Requisições não têm garantia de idempotência neste MVP; retries podem criar outro registro e não devem ocorrer automaticamente. Não é necessário criar tabela de erros ou usuários nesta primeira integração.

## Tela e entrega da equipe

A tela informa T e quatro medidas; exibe probabilidade, decisão, janela prevista e aviso de mock/histórico. Essa indicação deve corresponder aos campos persistidos, nunca à interpretação do Front-End.

Entregar um script de criação/migração para o SGBD acordado, instruções locais de conexão e um teste de inserção/consulta. Configurações reais e senhas ficam fora do Git; fornecer apenas exemplo sem segredos. Aceite: o UUID devolvido pela API encontra uma linha com os mesmos valores e instantes, e combinações inválidas são rejeitadas. Alinhar conexão com o Backend; não implementar diretamente chamadas do navegador.

Este documento é uma proposta de esquema. Não cria banco, migração ou serviço. Referências: [Backend](backend.md) e [Front-End](frontend.md).
