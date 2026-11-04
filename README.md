# Previsão de chuva em Londrina

Nosso objetivo é construir um MVP que receba dados meteorológicos e estime **se vai chover na próxima hora**. A equipe quer integrar dados → modelo → API → banco → tela, com código simples e compreensível.

## Onde estamos

- Auditoria e análise exploratória dos dados concluídas.
- Tabela experimental preparada: **59.159 registros**, com temperatura, umidade, pressão e nebulosidade como entradas.
- Cinco ciclos de treinamento documentados. A v5 comparou 12 configurações de Random Forest em quatro folds cronológicos e três sementes.
- Pela regra de seleção da v5, o candidato técnico é o Random Forest original sem pesos, com folha mínima 10 e 400 árvores. O balanceado mantém recall maior, mas também mais alarmes falsos e Brier mais alto.
- O período de 2026 ficou fora da seleção v5. Ele já havia sido consultado em ciclos anteriores e não representa uma avaliação independente.
- Contratos de integração documentados para as equipes; API, banco e tela ainda não estão implementados.

O Random Forest balanceado identifica mais eventos de chuva e também gera mais alarmes falsos. Ainda não há modelo escolhido para operação nem serviço de previsão em tempo real. As imagens GOES ficam para uma evolução futura; você não precisa baixar o acervo para trabalhar no MVP meteorológico atual.

**Limitação importante:** adotamos a hipótese de que a chuva registrada em T+1h representa a hora seguinte a T. Essa interpretação e a disponibilidade dos dados no instante da previsão ainda precisam de confirmação na origem. Por enquanto, o estudo é histórico e experimental.

## 1. Preparar o ambiente

Você precisa de **Git, Python compatível com as dependências fixadas e acesso ao repositório privado**. A execução v4 foi validada com Python 3.13.3. No terminal PowerShell:

```powershell
git clone https://github.com/victorhukra/backend-monitoramento-ambiental.git
cd backend-monitoramento-ambiental
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
git config core.hooksPath .githooks
Copy-Item .env.example .env
```

Se já tem o projeto, use sua pasta existente. Copie `.env.example` somente se ainda não tiver `.env`, para preservar seus caminhos locais.

No Linux/macOS, use `python3 -m venv .venv`, `source .venv/bin/activate` e `cp .env.example .env`. Os comandos Python seguintes são iguais.

As dependências fixadas em `requirements.txt` incluem pandas, NumPy, Matplotlib, scikit-learn e joblib. Os ambientes local e de validação estão com dependências consistentes (`pip check` sem conflitos); a equipe deve repetir a instalação limpa no computador de destino.

## 2. Indicar onde está o CSV

Solicite à equipe o arquivo `dataset_weather.csv`: ele **não vem no GitHub**. Guarde-o fora do repositório, por exemplo em `D:/dados-goes/`, e ajuste estas linhas no seu `.env`:

```dotenv
WEATHER_CSV_PATH=D:/dados-goes/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

Substitua o caminho pelo da sua máquina. Caminhos relativos partem da raiz do projeto. As opções GOES do `.env` podem ficar como estão para esta etapa.

## 3. Preparar a tabela

Na raiz do projeto, com o ambiente ativo:

```powershell
python -B scripts/prepare_weather.py --plot
```

O script lê o CSV original, associa cada horário à chuva de **exatamente uma hora depois** e grava os resultados em `data/processed/`:

| Arquivo | Para que serve |
|---|---|
| `weather_training.csv` | Quatro entradas, horário de referência, horário do alvo e classe de chuva |
| `weather_training.json` | Contagens, parâmetros e identificação da fonte |
| `weather_training_excluded.csv` | Linhas que não puderam entrar e seus motivos |
| `weather_training_preview.csv` | Dez primeiras linhas para conferência |
| `weather_training.png` | Gráfico das quantidades com e sem chuva |

O original permanece intacto. O script não divide períodos nem treina um modelo. Sem `--plot`, não gera o gráfico.

**Se a tabela já existe, não é necessário gerá-la novamente.** O script evita sobrescritas; para uma nova versão, use `--output data/processed/weather_training_v2.csv`.

Entenda cada passo em [Preparação da tabela](docs/prepare_weather.md). A preparação não treina modelos; ela só constrói e documenta a tabela de exemplos.

## 4. Treinar e comparar os modelos

O fluxo atual está no script v5. A v4 foi arquivada em `scripts/archive/` junto às versões anteriores. Com a tabela disponível e o ambiente ativado, execute:

```powershell
python -B scripts/train_v5.py
```

A v5 compara 12 configurações nos anos 2022-2025 com três sementes e grava previsões out-of-fold, métricas, joblibs e manifesto. Os quatro modelos finais também foram avaliados uma vez no teste de 2026 depois de congelados; esses resultados retrospectivos não foram usados para selecionar modelos ou limiares. Consulte o [relatório v5](reports/training/fifth_training_report.md) para critérios, resultados e limites da recomendação. Os artefatos e joblibs ficam localmente em `data/experiments/`, ignorados pelo Git.

Para fazer a avaliação retrospectiva dos joblibs salvos de uma execução v5, o comando explícito é:

```powershell
python -B scripts/train_v5.py --evaluate-test --output-dir data/experiments/weather_v5_20261104T120000Z
```

O script registra métricas e previsões no experimento e impede a repetição da avaliação na mesma pasta. Este período já foi consultado em ciclos anteriores, então seus resultados não são independentes nem devem orientar a seleção.

Cada execução exige uma pasta de saída nova e não sobrescreve experimentos existentes. A execução completa pode levar vários minutos. As pastas em `data/experiments/` são locais e excluídas do Git; não tente adicioná-las ao repositório.

Relatórios dos treinamentos:

- [Relatório da comparação v5 em Markdown](reports/training/fifth_training_report.md)
- [Detalhe técnico da v4 em Markdown](reports/training/fourth_training_report.md)
- [Código de comparação v5](scripts/train_v5.py)
- [Treinamento histórico v4 arquivado](scripts/archive/train_v4.py)

## 5. Executar os testes

```powershell
python -B -m unittest discover -s tests -v
```

Os testes usam exemplos pequenos e não exigem o CSV real nem as imagens GOES.

Na revisão de 04/11/2026, a suíte completa passou em **51 testes**; `pip check` também passou nos ambientes `.venv` e `.venv-validacao`. Os testes não validam a semântica meteorológica da fonte nem demonstram desempenho operacional.

## Onde encontrar cada coisa

| Local | Conteúdo |
|---|---|
| `config.py` | Caminhos, fuso e nomes das quatro entradas |
| `scripts/prepare_weather.py` | Preparação da tabela do MVP |
| `scripts/train_v5.py` | Comparação temporal repetida e registro de artefatos |
| `scripts/archive/` | Versões históricas dos scripts de treinamento |
| `tests/` | Verificações do código |
| `docs/integration/` | Contratos para Backend, Front-end e Banco |
| `reports/project/` | Propostas e guia para as próximas decisões |
| `reports/training/` | Relatórios dos ciclos experimentais |
| `src/data/` | Auditoria, análise exploratória e investigação da origem |
| `src/features/` | Investigação e piloto GOES |
| `data/` | Dados e resultados locais, ignorados pelo Git |

Para alinhar as equipes: [Backend](docs/integration/backend.md), [Front-end](docs/integration/frontend.md) e [Banco de Dados](docs/integration/database.md). Esses documentos são contratos propostos; não significam que os serviços já estejam implementados. A tabela `predictions` proposta para o banco guarda previsões da API e é diferente da tabela de treinamento.

## Colaborar sem misturar as tarefas

Use `main` para código revisado e uma branch `feature/nome-curto` para cada tarefa:

```powershell
git switch main
git pull --ff-only
git switch -c feature/nome-curto
# Faça suas alterações e execute os testes.
git add caminho/do/arquivo.py
python scripts/check_staged.py
# Só continue se a verificação passar; confira o conteúdo abaixo.
git diff --cached
git commit -m "feat: descrever a alteração"
git push -u origin feature/nome-curto
```

Abra um Pull Request para `main` e peça a revisão de um colega. Cada pessoa mantém seus próprios caminhos no `.env`.

**No Git entram somente código e documentação.** CSV, NPZ, ZIP, amostras, resultados gerados, ambientes e credenciais ficam fora. O `.gitignore` e o hook ajudam a conferir isso; não use `git add -f` para incluir dados nem desative o hook para contornar uma rejeição. Tokens e senhas nunca devem entrar no código ou na documentação.

## Material de apoio

- [Estado detalhado e histórico do projeto](STATUS.md).
- [README original do dataset](docs/dataset/README.md), preservado.
- [Utilitários GOES](docs/goes_development.md): amostra local e leitura seletiva, para quem precisar investigar imagens. O acervo tem cerca de 73,8 GiB; não descompacte tudo.
- [Documentação histórica](docs/history/README_pre_github.md): reprodução das análises anteriores. Alguns resultados locais citados não acompanham o clone.
