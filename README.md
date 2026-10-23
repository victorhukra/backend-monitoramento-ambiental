# Previsão de chuva em Londrina

Nosso objetivo é construir um MVP que receba dados meteorológicos e estime **se vai chover na próxima hora**. A equipe quer integrar dados → modelo → API → banco → tela, com código simples e compreensível.

## Onde estamos

- Auditoria e análise exploratória dos dados concluídas.
- Tabela experimental preparada: **59.159 registros**, com temperatura, umidade, pressão e nebulosidade como entradas.
- Contratos de integração documentados para as equipes.
- **Próximo passo:** revisar a tabela juntos e escolher os períodos de treino, validação e teste.

Ainda não há modelo treinado, API em execução ou integração com banco e tela. As imagens GOES ficam para uma evolução futura; você não precisa baixar o acervo de imagens para trabalhar no MVP atual.

**Limitação importante:** adotamos a hipótese de que a chuva registrada em T+1h representa a hora seguinte a T. Essa interpretação e a disponibilidade dos dados no instante da previsão ainda precisam de confirmação na origem. Por enquanto, o estudo é histórico e experimental.

## 1. Preparar o ambiente

Você precisa de **Git, Python 3.12 e acesso ao repositório privado**. No terminal PowerShell:

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

As dependências principais são pandas, NumPy e Matplotlib. As versões estão em `requirements.txt`; a instalação limpa dessas versões ainda precisa ser validada em outra máquina.

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

Entenda cada passo em [Preparação da tabela](docs/prepare_weather.md). Para nossa próxima conversa, siga o [guia de revisão e escolha dos períodos](reports/project/revisao_tabela_e_periodos.md).

## 4. Executar os testes

```powershell
python -B -m unittest discover -s tests -v
```

Os testes usam exemplos pequenos e não exigem o CSV real nem as imagens GOES.

## Onde encontrar cada coisa

| Local | Conteúdo |
|---|---|
| `config.py` | Caminhos, fuso e nomes das quatro entradas |
| `scripts/prepare_weather.py` | Preparação da tabela do MVP |
| `tests/` | Verificações do código |
| `docs/integration/` | Contratos para Backend, Front-end e Banco |
| `reports/project/` | Propostas e guia para as próximas decisões |
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
