# Previsão de chuva em curto prazo — Londrina/PR

Pipeline em Python que prepara dados meteorológicos horários, treina e avalia um ensemble de Random Forests e gera um pacote de modelo para inferência. O CSV é fornecido separadamente; imagens GOES não são necessárias para o pipeline atual.

## Executar do zero

### 1. Clonar e instalar

Requer Git e Python 3.13 ou superior. Para reproduzir o ambiente registrado, use Python 3.13.3.

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

### 2. Informar onde está o CSV

O CSV meteorológico é fornecido por outros meios e pode ficar em qualquer diretório. Edite `.env` e substitua o caminho de exemplo:

```dotenv
WEATHER_CSV_PATH=/caminho/para/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

No Windows, por exemplo, `WEATHER_CSV_PATH=C:/dados/dataset_weather.csv`. O arquivo precisa conter `time`, `temperature_2m`, `relative_humidity_2m`, `pressure_msl`, `cloud_cover` e `rain`. Não é necessário baixar dados GOES.

### 3. Preparar os dados

Execute a partir da raiz do repositório:

```bash
python scripts/prepare_weather.py --plot
```

O script valida timestamps e valores, associa cada registro ao horário exato T+1h e cria `data/processed/weather_training.csv` com o alvo `rain_next_hour`. Também grava um resumo, as exclusões e uma prévia. Não sobrescreve saídas existentes; para outra execução, use `--output data/processed/weather_training_v2.csv` e informe esse mesmo arquivo nos próximos passos.

### 4. Treinar e gerar o ensemble

Use nomes de saída novos se executar novamente:

```bash
python scripts/train_v6.py --input data/processed/weather_training.csv --output-dir data/experiments/weather_v6_local
python scripts/package_weather_model.py --v6-dir data/experiments/weather_v6_local --output-dir data/experiments/weather_v6_ensemble_local
```

O treinamento faz validação temporal em 2022–2025, produz previsões fora da amostra e ajusta três modelos finais com dados anteriores a 2026. Pode levar vários minutos. O empacotador ajusta calibradores isotônicos a partir das previsões OOF e verifica os hashes e as features.

O resultado fica em `data/experiments/weather_v6_ensemble_local/`, incluindo `weather_ensemble.joblib` e `manifest.json`. Os diretórios `data/` e os artefatos são locais e ignorados pelo Git; portanto, não aparecem em um clone novo.

### 5. Verificar a instalação e testar inferência

Os testes usam dados sintéticos e não precisam do CSV:

```bash
python -m unittest discover -s tests -v
```

Para testar o bundle, execute na raiz do projeto:

```bash
python -c "import joblib; b=joblib.load('data/experiments/weather_v6_ensemble_local/weather_ensemble.joblib'); w={'temperature_2m':22.5,'relative_humidity_2m':80.0,'pressure_msl':1012.0,'cloud_cover':60.0,'pressure_msl_previous_hour':1010.0}; print(b.predict_one(w,'2025-06-01T15:00:00-03:00'))"
```

A previsão recebe quatro medidas em T, a pressão em T-1h e um horário com fuso. Retorna probabilidade, decisão, limiar e versão do modelo.

## Sobre o modelo

As sete features são temperatura, umidade, pressão, cobertura de nuvens, produto temperatura×umidade, variação da pressão e hora local. Os três Random Forests são `original`, `balanced` e `balanced_subsample`, cada um com 400 árvores e folha mínima de 10. Suas probabilidades são calibradas individualmente por regressão isotônica e combinadas por média simples; o limiar do pacote é provisoriamente 0,50.

`rain_next_hour` vale 1 quando a chuva registrada em T+1h é positiva. Essa definição pressupõe que `rain` em um timestamp represente a precipitação acumulada na hora anterior; essa semântica ainda precisa ser confirmada na fonte.

A avaliação v7 é opcional e compara calibração, combinações e limiares com diferentes custos de falsos positivos e falsos negativos:

```bash
python scripts/evaluate_test.py --input data/experiments/weather_v6_local/predictions_oof.csv --output-dir data/experiments/weather_v7_local
```

## Estrutura principal

```text
config.py                         Configuração e caminhos
scripts/prepare_weather.py        Preparação e criação do alvo
scripts/train_v6.py               Treinamento e validação temporal
scripts/evaluate_test.py          Avaliação v7 opcional
scripts/package_weather_model.py  Calibração e empacotamento
src/models/weather_ensemble.py    Engenharia de features e inferência
tests/                            Testes automatizados
reports/training/                 Relatórios v6 e v7
```

## Escopo e limitações

Este é um pipeline experimental e retrospectivo, não um serviço de previsão operacional. A API, o banco de dados e a interface pertencem a outro projeto. A disponibilidade dos dados no instante da previsão, a semântica exata da chuva, os custos dos erros e um limiar operacional ainda precisam ser validados. O teste de 2026 não foi usado para seleção na v6; não deve ser reutilizado para escolher parâmetros. As imagens GOES são uma linha exploratória separada e não entram neste modelo.
