# Previsão de chuva em curto prazo — Londrina/PR

Este repositório prepara dados meteorológicos horários, treina e avalia modelos de classificação e disponibiliza o código do ensemble para estimar chuva na próxima hora.

## Executar o pipeline

Requisitos: Git, Python 3.13+ e o CSV meteorológico, fornecido separadamente.

### 1. Instalar

**Windows (PowerShell):**

```powershell
git clone https://github.com/victorhukra/backend-monitoramento-ambiental.git
cd backend-monitoramento-ambiental
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

**Linux/macOS:**

```bash
git clone https://github.com/victorhukra/backend-monitoramento-ambiental.git
cd backend-monitoramento-ambiental
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

### 2. Configurar o CSV

Edite `.env` e informe o caminho local do CSV recebido:

```dotenv
WEATHER_CSV_PATH=/caminho/para/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

No Windows, use, por exemplo, `C:/dados/dataset_weather.csv`. O CSV deve conter `time`, `temperature_2m`, `relative_humidity_2m`, `pressure_msl`, `cloud_cover` e `rain`. Não é necessário baixar imagens GOES para este pipeline.

### 3. Preparar os dados e treinar

Execute a partir da raiz do repositório, com o ambiente virtual ativado:

```bash
python scripts/prepare_weather.py
python scripts/train_v6.py
```

A preparação valida timestamps e valores meteorológicos, associa cada hora ao registro exato de T+1h e cria `data/processed/weather_training.csv` com o alvo `rain_next_hour`.

O treinamento v6 executa validação temporal expansiva para os anos de 2022 a 2025, compara três variantes de Random Forest com três sementes e gera métricas, previsões fora da amostra (OOF), modelos `.joblib`, manifesto e relatório em `reports/training/`. Os artefatos do experimento são gravados em um diretório com timestamp dentro de `data/experiments/`.

### 4. Testes

```bash
python -m unittest discover -s tests -v
```

Os testes usam dados sintéticos e não dependem do CSV externo.

> A avaliação v7 (`scripts/evaluate_test.py`) é uma etapa opcional de análise de calibração, pesos e limiares. O empacotamento para integração é feito por `scripts/package_weather_model.py`.

## Como funciona o treinamento

O alvo é `rain_next_hour`: 1 quando a chuva registrada em T+1h é positiva, 0 quando não é. A preparação faz o pareamento pelo horário exato, não pela linha seguinte do arquivo. O código assume que a chuva registrada em cada timestamp representa a hora anterior; essa interpretação ainda precisa ser confirmada na fonte.

O modelo usa sete atributos:

- quatro medidas em T: temperatura, umidade relativa, pressão ao nível do mar e cobertura de nuvens;
- `temp_humidity`: temperatura multiplicada pela umidade;
- `pressure_diff`: pressão em T menos pressão em T-1h;
- `hour_of_day`: hora local em `America/Sao_Paulo`.

A v6 compara três Random Forests com 400 árvores e folha mínima de 10:

- `original`: sem pesos de classe;
- `balanced`: pesos inversos à frequência das classes;
- `balanced_subsample`: pesos recalculados em cada amostra bootstrap.

Os folds são cronológicos: cada ano de validação é previsto usando somente anos anteriores. O conjunto de 2026 não é usado na validação v6 nem na seleção de modelos. As previsões OOF da v6 também permitem à avaliação v7 comparar calibração isotônica, combinações e limiares sob diferentes custos de falsos positivos e falsos negativos.

O adaptador `SimpleMeanCalibratedEnsemble`, em `src/models/weather_ensemble.py`, aplica a engenharia de atributos, obtém as probabilidades dos três modelos, calibra cada uma e calcula a média simples, com pesos de 1/3. O limiar 0,50 do pacote é provisório.

## Organização do código

```text
config.py                         Configuração e caminhos locais
scripts/prepare_weather.py        Preparação da tabela e do alvo
scripts/train_v6.py               Treinamento e validação temporal
scripts/evaluate_test.py          Avaliação v7 opcional
scripts/package_weather_model.py  Empacotamento do modelo e manifesto
src/models/weather_ensemble.py    Engenharia de atributos e inferência
tests/                            Testes automatizados
reports/training/                 Relatórios v6 e v7
```

## Limitações

Este é um pipeline experimental retrospectivo, não um serviço de previsão operacional. A semântica temporal de `rain`, a disponibilidade das entradas no momento da previsão, os custos dos erros e um limiar operacional ainda precisam ser validados. O repositório não implementa a API, o banco de dados ou a interface. As imagens GOES são exploratórias e não entram no modelo atual.

Os dados e artefatos locais ficam sob `data/`, ignorado pelo Git; portanto, cada pessoa precisa receber o CSV separadamente e configurar seu próprio caminho no `.env`.
