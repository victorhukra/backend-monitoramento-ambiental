# Módulo de Modelagem Preditiva e Inteligência Artificial

**Previsão de chuva em curto prazo — Londrina/PR**

Este repositório implementa o pipeline de preparação de dados, treinamento, validação temporal, calibração probabilística e empacotamento de um ensemble para previsão binária de chuva na próxima hora.

O resultado é um pacote `weather_ensemble.joblib`, acompanhado de `manifest.json`, destinado à integração com o backend da aplicação.

## 1. Visão geral

A previsão recebe cinco valores meteorológicos brutos:

- `temperature_2m`: temperatura em T;
- `relative_humidity_2m`: umidade relativa em T;
- `pressure_msl`: pressão ao nível do mar em T;
- `cloud_cover`: cobertura de nuvens em T;
- `pressure_msl_previous_hour`: pressão ao nível do mar em T-1h.

O pipeline deriva três atributos:

- `temp_humidity = temperature_2m * relative_humidity_2m`;
- `pressure_diff = pressure_msl - pressure_msl_previous_hour`;
- `hour_of_day`: hora local no fuso `America/Sao_Paulo`.

Portanto, o modelo utiliza estas sete features:

```text
temperature_2m
relative_humidity_2m
pressure_msl
cloud_cover
temp_humidity
pressure_diff
hour_of_day
```

O alvo é `rain_next_hour`:

- `0`: sem chuva positiva em T+1h;
- `1`: chuva positiva em T+1h.

O ensemble combina três Random Forests:

- `original`: distribuição natural das classes;
- `balanced`: pesos proporcionais à frequência das classes;
- `balanced_subsample`: pesos balanceados recalculados em cada amostra bootstrap.

Cada modelo possui uma calibração isotônica. A probabilidade final é a média das três probabilidades calibradas. O candidato atual usa limiar provisório `0,50`:

```text
probabilidade >= 0,50 → chuva prevista
probabilidade <  0,50 → chuva não prevista
```

## 2. Dados externos

O CSV meteorológico **não é distribuído pelo GitHub** e deve ser fornecido separadamente.

Ele pode ficar em qualquer pasta da máquina. Antes de executar o projeto, indique o caminho no `.env`:

```dotenv
WEATHER_CSV_PATH=/caminho/externo/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

Exemplo para Windows:

```dotenv
WEATHER_CSV_PATH=C:/dados/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

Exemplo para Linux/macOS:

```dotenv
WEATHER_CSV_PATH=/home/usuario/dados/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

Caminhos relativos são resolvidos a partir da raiz do projeto. O arquivo `.env` é ignorado pelo Git e pode conter uma configuração diferente em cada computador.

O CSV precisa conter pelo menos:

```text
time
temperature_2m
relative_humidity_2m
pressure_msl
cloud_cover
rain
```

Os timestamps devem representar horas completas. Timestamps duplicados, registros fora de hora cheia e valores fora dos critérios físicos são recusados ou registrados como exclusão pela preparação.

Não coloque no Git:

- CSV meteorológico;
- tabelas processadas;
- arquivos GOES, NPZ ou ZIP;
- modelos `.joblib`;
- resultados JSON ou PNG;
- ambientes virtuais;
- credenciais e arquivos `.env`.

## 3. Arquitetura

```text
CSV externo
    |
    v
scripts/prepare_weather.py
    |
    v
data/processed/weather_training.csv
    |
    v
scripts/train_v6.py
    |
    +--> original_leaf10_trees400.joblib
    +--> balanced_leaf10_trees400.joblib
    +--> balanced_subsample_leaf10_trees400.joblib
    +--> predictions_oof.csv
            |
            v
scripts/package_weather_model.py
    |
    v
weather_ensemble.joblib
isotonic_calibrators.joblib
manifest.json
```

## 4. Instalação

Requisitos:

- Git;
- Python 3.13 ou superior;
- CSV meteorológico fornecido externamente.

### Windows — PowerShell

```powershell
git clone https://github.com/victorhukra/backend-monitoramento-ambiental.git
cd backend-monitoramento-ambiental

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
python -m pip check

Copy-Item .env.example .env
git config core.hooksPath .githooks
```

### Linux/macOS

```bash
git clone https://github.com/victorhukra/backend-monitoramento-ambiental.git
cd backend-monitoramento-ambiental

python3.13 -m venv .venv
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m pip check

cp .env.example .env
git config core.hooksPath .githooks
```

O comando `git config core.hooksPath .githooks` ativa o hook que impede o staging de dados, credenciais, ambientes virtuais e artefatos proibidos.

## 5. Configuração em qualquer computador

Depois de copiar o `.env.example`, edite o `.env` e informe o caminho recebido externamente:

```dotenv
WEATHER_CSV_PATH=/caminho/externo/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

Também é possível informar o CSV diretamente na linha de comando:

```bash
python scripts/prepare_weather.py --csv "/caminho/externo/dataset_weather.csv"
```

Caminhos absolutos funcionam em qualquer local da mesma máquina. Caminhos relativos são resolvidos a partir da raiz do repositório.

Variáveis exportadas no ambiente do sistema têm precedência sobre valores definidos no `.env`.

## 6. Execução completa do pipeline

Execute os comandos a partir da raiz do repositório com o ambiente virtual ativo.

### Passo 1 — preparar a tabela

```bash
python scripts/prepare_weather.py --plot
```

Com o CSV em um local externo:

```bash
python scripts/prepare_weather.py --csv "/caminho/externo/dataset_weather.csv" --plot
```

Saída padrão:

```text
data/processed/weather_training.csv
```

O script também pode gerar:

```text
weather_training.json
weather_training_excluded.csv
weather_training_preview.csv
weather_training.png
```

A preparação:

- lê o CSV sem modificá-lo;
- interpreta timestamps em `America/Sao_Paulo`;
- verifica registros em hora cheia e timestamps duplicados;
- valida umidade, cobertura de nuvens e pressão;
- procura exatamente o registro em T+1h;
- cria `rain_next_hour`;
- calcula o SHA-256 da fonte;
- não divide os dados nem treina modelos.

O script não sobrescreve arquivos existentes. Para gerar uma versão alternativa:

```bash
python scripts/prepare_weather.py \
  --csv "/caminho/externo/dataset_weather.csv" \
  --output data/processed/weather_training_v2.csv
```

Nesse caso, todos os passos seguintes devem usar `weather_training_v2.csv`.

### Passo 2 — treinar e validar

Use uma pasta nova para cada execução:

```bash
python scripts/train_v6.py \
  --input data/processed/weather_training.csv \
  --output-dir data/experiments/weather_v6_local
```

O treinamento:

- usa validação cronológica expandida em 2022–2025;
- usa as sementes `17`, `42` e `2025`;
- treina três Random Forests com 400 árvores;
- usa folha mínima de dez registros;
- gera previsões fora da amostra;
- ajusta os modelos finais com dados anteriores a 2026;
- não usa o período de 2026 para seleção;
- gera o relatório em `reports/training/sixth_training_report.md`.

Arquivos gerados pela execução:

```text
manifest.json
experiment_summary.json
metrics_by_fold_seed.csv
strategy_summary.csv
predictions_oof.csv
original_leaf10_trees400.joblib
balanced_leaf10_trees400.joblib
balanced_subsample_leaf10_trees400.joblib
```

A execução pode demorar vários minutos, pois várias famílias de Random Forest são ajustadas em partições temporais e sementes diferentes.

### Passo 3 — avaliar calibração e limiares

Esta etapa é opcional para gerar o ensemble:

```bash
python scripts/evaluate_test.py \
  --input data/experiments/weather_v6_local/predictions_oof.csv \
  --output-dir data/experiments/weather_v7_local
```

A avaliação v7 usa apenas previsões fora da amostra da v6 e verifica calibração, pesos, limiares e custos relativos de erros. Ela não determina automaticamente um limiar operacional aprovado.

### Passo 4 — empacotar o ensemble

Use o diretório gerado pelo treinamento:

```bash
python scripts/package_weather_model.py \
  --v6-dir data/experiments/weather_v6_local \
  --output-dir data/experiments/weather_v6_ensemble_local
```

Saída esperada:

```text
data/experiments/weather_v6_ensemble_local/
├── weather_ensemble.joblib
├── isotonic_calibrators.joblib
└── manifest.json
```

O empacotador:

- verifica o SHA-256 da tabela processada;
- verifica o SHA-256 dos modelos;
- confirma o contrato das sete features;
- ajusta os calibradores isotônicos;
- cria `SimpleMeanCalibratedEnsemble`;
- executa uma verificação de paridade das features;
- gera o bundle serializado e o manifesto.

Se o CSV ou a tabela processada mudar depois do treinamento, o empacotamento deve detectar divergência no hash. Nesse caso, realize novamente o treinamento com a mesma tabela que será usada no empacotamento.

## 7. Teste da inferência

Depois de empacotar o modelo:

```python
import joblib

bundle = joblib.load(
    "data/experiments/weather_v6_ensemble_local/weather_ensemble.joblib"
)

weather = {
    "temperature_2m": 22.5,
    "relative_humidity_2m": 80.0,
    "pressure_msl": 1012.0,
    "cloud_cover": 60.0,
    "pressure_msl_previous_hour": 1010.0,
}

result = bundle.predict_one(
    weather=weather,
    reference_time="2025-06-01T15:00:00-03:00",
)

print(result)
```

A saída contém:

- `rain_probability`;
- `rain_predicted`;
- `decision_threshold`;
- `model_version`.

O timestamp precisa incluir timezone. Os cinco campos brutos devem existir e possuir valores finitos. Campos extras ou campos ausentes são rejeitados.

## 8. Testes automatizados

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem preparação temporal, timestamps UTC, lacunas, domínio físico, proteção contra sobrescrita, features derivadas, limites temporais, contrato do ensemble e regras do pre-commit.

Os testes usam dados sintéticos e não exigem o CSV externo.

## 9. Estrutura do repositório

```text
.
├── config.py
├── requirements.txt
├── README.md
├── .env.example
├── scripts/
│   ├── prepare_weather.py
│   ├── train_v6.py
│   ├── evaluate_test.py
│   ├── package_weather_model.py
│   └── check_staged.py
├── src/
│   └── models/
│       └── weather_ensemble.py
├── tests/
├── reports/
│   └── training/
├── docs/
└── .githooks/
```

Os diretórios locais `data/` e seus resultados são ignorados pelo Git.

## 10. Integração com a API

O backend separado pode carregar o bundle:

```python
import joblib

bundle = joblib.load("weather_ensemble.joblib")
```

Antes da integração, o serviço deve conferir:

- SHA-256 do bundle;
- versão do modelo;
- nome e ordem das sete features;
- campos meteorológicos obrigatórios;
- limiar registrado no manifesto.

A API, o banco de dados e a interface não são implementados neste repositório. É necessário um serviço separado para consultar dados em T e T-1h, chamar `predict_one(...)` e persistir o resultado.

## 11. Limitações

Este projeto é um candidato experimental, não um sistema meteorológico aprovado para operação pública.

Limitações atuais:

- a semântica exata da variável `rain` ainda não foi confirmada na fonte;
- não está comprovado que os dados históricos estavam disponíveis no instante da previsão;
- o conjunto é retrospectivo;
- o período de 2026 não deve ser usado para selecionar parâmetros;
- não há avaliação independente em dados futuros;
- os custos de falsos positivos e falsos negativos ainda não foram aprovados;
- o limiar atual é provisório;
- não há API, banco ou interface neste repositório;
- imagens GOES não integram o modelo atual.

Os dados GOES são uma linha exploratória separada e não são necessários para executar o pipeline meteorológico descrito neste README.
