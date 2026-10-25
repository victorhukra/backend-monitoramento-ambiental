# Guia de Execução Passo a Passo
## MVP meteorológico de Londrina — Dados → Treino → API

**Atualizado em 25/10/2026**

O objetivo do projeto é prever a ocorrência de chuva na próxima hora usando quatro informações: temperatura, umidade, pressão atmosférica e nebulosidade.

**Situação atual:** a preparação dos dados está implementada. O arquivo `train.py` e a API ainda não existem no projeto. Portanto, as etapas de treinamento e API abaixo indicam o que falta implementar; seus comandos propostos ainda não podem ser executados com sucesso.

## 1. Pré-requisitos e instalação

Precisamos de:

- Python 3.12.
- Git e acesso ao repositório privado.
- Arquivo `dataset_weather.csv`, fornecido separadamente pela equipe.

### 1.1. Abrir o projeto

Se ainda não tiver o repositório:

```powershell
git clone https://github.com/victorhukra/backend-monitoramento-ambiental.git
cd backend-monitoramento-ambiental
```

Se já tiver, abra o terminal na pasta que contém `README.md`, `config.py` e `requirements.txt`.

### 1.2. Criar e ativar o ambiente virtual

O ambiente virtual mantém os pacotes deste projeto separados dos demais projetos.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se `.venv` já existir, basta ativá-lo. Nos próximos terminais, execute novamente o comando de ativação.

### 1.3. Instalar os pacotes

```powershell
python -m pip install -r requirements.txt
```

As dependências atuais são pandas, NumPy e Matplotlib. As dependências de treinamento e da API serão adicionadas quando essas etapas forem implementadas.

### 1.4. Executar os testes

```powershell
python -B -m unittest discover -s tests -v
```

Na versão atual, o resultado esperado é:

```text
Ran 38 tests
OK
```

Esses testes não exigem os dados reais e não avaliam a qualidade de um modelo.

## 2. Preparar os dados

### 2.1. Configurar os caminhos

Se ainda não existir um `.env`, crie uma cópia:

```powershell
Copy-Item .env.example .env
```

Se ele já existir, apenas edite-o para não perder configurações.

No computador em que o projeto foi preparado, os caminhos são:

```dotenv
WEATHER_CSV_PATH=C:/Users/CANAL/Downloads/Backend_UTFPR/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

Em outro computador, substitua o caminho do CSV pelo local correto.

**Pendência identificada no último teste:** a configuração ainda procurava o CSV em `data/raw/dataset_weather.csv`. É necessário ajustar `WEATHER_CSV_PATH` antes de executar a preparação.

### 2.2. Confirmar os caminhos

```powershell
python -B -c "from config import settings; c=settings(); print('CSV encontrado:', c['csv'].is_file()); print('Tabela encontrada:', c['training'].is_file())"
```

O CSV deve apresentar `True`. Antes da primeira preparação, é normal que a tabela apresente `False`.

### 2.3. Executar a preparação

```powershell
python -B scripts/prepare_weather.py --plot
```

O script:

1. Lê o CSV original.
2. Interpreta os horários no fuso de São Paulo.
3. Separa as quatro entradas meteorológicas do horário T.
4. Consulta a chuva registrada exatamente em T+1h.
5. Cria o alvo: `1` para chuva positiva e `0` para zero.
6. Salva a tabela e os arquivos de conferência em `data/processed/`.

**Exemplo:** os dados das 14h são usados para prever chuva entre 14h e 15h, sob a hipótese temporal adotada pelo projeto.

O script não modifica o CSV original, não divide os períodos e não treina o modelo.

**Neste computador, a tabela já existe. Não é necessário gerá-la novamente.** Para evitar perda de resultados, o script recusa sobrescrever arquivos. Se houver motivo para criar uma nova versão:

```powershell
python -B scripts/prepare_weather.py --plot --output data/processed/weather_training_v2.csv
```

### 2.4. Conferir o resultado

```powershell
python -B -c "import pandas as pd; from config import settings; d=pd.read_csv(settings()['training']); print('Dimensões:', d.shape); print('Ausentes:', d.isna().sum().sum()); print(d['rain_next_hour'].value_counts())"
```

Para a tabela atual, esperamos:

| Verificação | Resultado |
|---|---:|
| Linhas | 59.159 |
| Colunas | 7 |
| Valores ausentes | 0 |
| Sem chuva — classe 0 | 49.039 |
| Com chuva — classe 1 | 10.120 |

Uma linha do original ficou fora porque não existe a hora seguinte para definir sua resposta.

## 3. Treinar o modelo — etapa ainda pendente

**O arquivo `train.py` ainda não foi implementado.**

Antes de criá-lo, precisamos escolher e registrar os períodos cronológicos de treino, validação e teste. Não devemos embaralhar a série.

Uma proposta para discussão é:

| Conjunto | Período | Uso |
|---|---|---|
| Treino | 2020–2024 | Aprender a relação entre entradas e chuva |
| Validação | 2025 | Comparar escolhas e ajustar parâmetros |
| Teste | Janeiro–setembro de 2026 | Fazer a avaliação final |

Essa proposta ainda não é uma divisão aprovada. O teste cobre apenas nove meses.

O futuro script deverá:

1. Ler a tabela preparada.
2. Separar os períodos escolhidos, verificando também o horário do alvo nas fronteiras.
3. Usar somente as quatro variáveis meteorológicas como entradas.
4. Usar `rain_next_hour` como resposta.
5. Treinar e avaliar o modelo sem usar o teste para fazer ajustes.
6. Salvar o modelo e registrar as métricas.

**Comando proposto para quando existir `scripts/train.py`:**

```powershell
python scripts/train.py
```

O nome, as opções e o local de saída serão confirmados na implementação. Hoje, esse comando falhará porque o arquivo não existe.

Para considerar essa etapa concluída, precisamos ter um modelo salvo que possa ser carregado novamente, métricas registradas e identificação das entradas e dos períodos utilizados.

## 4. Subir a API e testar as rotas — etapa ainda pendente

**A API ainda não foi implementada.** Existe um contrato proposto para `/predict`, mas não há servidor para iniciar.

Antes de executar esta etapa, será necessário implementar as rotas, carregar o modelo e adicionar as dependências da API ao projeto.

### 4.1. Iniciar o servidor

Se a equipe adotar FastAPI, com um arquivo `app/main.py` contendo a aplicação `app`, o comando de desenvolvimento poderá ser:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Esse é um **exemplo de organização futura**, não um comando funcional na versão atual. O caminho será confirmado quando a API for criada.

Com essa configuração, o endereço local será:

```text
http://127.0.0.1:8000
```

Mantenha o terminal do servidor aberto e use outro terminal para os testes.

### 4.2. Testar `/health`

A rota deverá informar se a API está pronta para atender previsões.

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

Resposta sugerida para quando o modelo estiver carregado:

```json
{
  "status": "ok",
  "model_loaded": true
}
```

Esse formato ainda precisa ser implementado. A API não deve indicar que está pronta para prever se o modelo necessário não foi carregado.

### 4.3. Testar `/predict`

O exemplo abaixo segue o contrato de entrada já documentado:

```powershell
$body = @{
    location = "Londrina-PR"
    reference_time = "2026-09-01T14:00:00-03:00"
    weather = @{
        temperature_2m = 24.7
        relative_humidity_2m = 74
        pressure_msl = 1008.9
        cloud_cover = 97
    }
} | ConvertTo-Json -Depth 3

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/predict" `
    -ContentType "application/json" `
    -Body $body
```

Quando implementada, a resposta deverá informar a probabilidade de chuva, a decisão, o intervalo previsto e a versão do modelo.

Na conferência, verificar:

- O intervalo começa às 14h e termina às 15h.
- A probabilidade está entre 0 e 1.
- A decisão corresponde ao limiar informado.
- Uma previsão real identifica a versão do modelo e usa `is_mock=false`.
- Uma resposta fictícia usa `is_mock=true`.
- Entradas inválidas, como umidade de 150%, são rejeitadas.

O contrato atual prevê **HTTP 201 após salvar a previsão**. Se a primeira API funcionar sem persistência, essa mudança precisa ser alinhada com as equipes antes da integração.

## 5. Ordem prática de execução

1. Configurar o ambiente e corrigir o caminho do CSV no `.env`.
2. Conferir a tabela existente; preparar novamente apenas se necessário.
3. Aprovar os períodos e as regras temporais.
4. Implementar e executar `train.py`.
5. Implementar a API e carregar o modelo salvo.
6. Testar `/health` e `/predict`.

**Limitação do MVP:** usamos dados históricos. A interpretação do acumulado de chuva e a disponibilidade das entradas no instante T ainda precisam de confirmação na origem. Uma demonstração integrada não comprova, por si só, qualidade de previsão em tempo real.
