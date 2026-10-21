# Previsão de chuva com meteorologia e GOES

Projeto de pesquisa para investigar o ganho de informações GOES na previsão de chuva em Londrina, nos horizontes candidatos de 1, 3, 6 e 7 horas. Há auditoria, EDA, piloto e testes; ainda não há target definitivo, região geográfica validada ou modelo treinado. Consulte [STATUS.md](STATUS.md) e os documentos em `reports/temporal/`.

## Política do repositório

**Somente código e documentação. Nenhum NPZ, ZIP, CSV, resultado binário ou ambiente local deve ser versionado, nem mesmo a amostra.** Não usamos Git LFS para os dados. `.gitignore` nega arquivos por padrão e permite Python, Markdown e configurações explicitamente selecionadas. Dados/ambientes continuam bloqueados dentro de suas pastas.

O acervo disponível é um ZIP de aproximadamente 79,2 GB (cerca de 73,8 GiB) contendo 59.033 NPZ. Não é uma única matriz de 73 GB. Não descompacte tudo. O script também aceita um NPZ individual pequeno; rejeita um NPZ gigante em vez de tentar carregá-lo na memória.

`.gitignore` não remove arquivos já rastreados e pode ser contornado com `git add -f`. Por isso, ative o hook e execute a verificação do índice antes de qualquer commit/push. Hooks locais também podem ser contornados; a equipe deve exigir revisão e não usar `--no-verify`. Nenhuma proteção local é uma garantia contra alguém que a desative. Revise segredos inseridos em código/documentação: o verificador limita tipos/tamanho, não detecta todos os segredos possíveis.

## 1. Clonar e instalar

Git e Python 3.12 são necessários. Repositório privado: é necessário que o proprietário conceda acesso à sua conta:

```powershell
git clone https://github.com/victorhukra/backend-monitoramento-ambiental.git
cd backend-monitoramento-ambiental
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
git config core.hooksPath .githooks
Copy-Item .env.example .env
python -B -m unittest discover -s tests -v
```

Linux/macOS: use `python3 -m venv .venv`, `source .venv/bin/activate` e `cp .env.example .env`. Se necessário, `chmod +x .githooks/pre-commit`. Os comandos de instalação e testes seguintes são os mesmos. Não é necessário obter dados reais para os testes unitários.

As versões diretas estão em `requirements.txt`; dependências transitivas não têm lockfile. A instalação limpa dessas versões ainda precisa ser validada pela equipe. Nesta máquina os testes usaram Python 3.12.14, NumPy 2.3.5 e pandas 3.0.1; os pins da EDA são NumPy 2.5.4, pandas 3.0.1 e Matplotlib 3.11.2. Não foram instaladas novas bibliotecas nesta preparação.

## 2. Configurar dados locais

Edite `.env`, que nunca deve ser commitado. `config.py` lê esse arquivo; variáveis já definidas no processo têm prioridade. Caminhos relativos usam a raiz do projeto. Use valores literais, sem expansão `${...}`, comandos de shell ou comentários no final da linha.

```dotenv
DATASET_MODE=sample
SAMPLE_PATH=data/sample/sample.npz
FULL_DATASET_PATH=D:/dados-goes/dataset_goes.zip
WEATHER_CSV_PATH=D:/dados-goes/dataset_weather.csv
DATASET_README_PATH=D:/dados-goes/README.md
GOES_MEMBER=
```

Preferência: armazenar o acervo fora do clone, em uma pasta como `D:/dados-goes/` ou `/dados/goes/`. Alternativamente, coloque o ZIP, CSV e README original em `data/raw/`, que é totalmente ignorada. Não copie os dados para `src/`, `docs/` ou `reports/`. Os diretórios locais são criados conforme necessário e não precisam existir no clone.

## 3. Gerar e usar a amostra

Quem possui o ZIP executa:

```powershell
python scripts/make_sample.py
python scripts/check_dataset.py
```

O gerador escolhe deterministicamente o primeiro nome NPZ ordenado no ZIP, preserva seus bytes e metadados e grava `data/sample/sample.npz`. Pode escolher outro membro com `--member "dataset_goes/samples/.../nome.npz"`. Também aceita `--source caminho/arquivo.npz` e `--output caminho/amostra.npz`.

Não extrai o ZIP inteiro, não sobrescreve fonte/destino existente e exige amostra menor que 50.000.000 bytes. Usa o leitor validado do piloto: limite externo de 32 MiB por NPZ e expansão interna de 128 MiB. Recusa matriz totalmente inválida ou metadados incompatíveis; não procura silenciosamente outra imagem. O limite de arquivo não é garantia de pico de RAM inferior a 50 MB.

**Amostra é uma imagem inteira, não recorte de Londrina nem conjunto representativo de treinamento.** Isso preserva a geografia ainda não comprovada. A amostra real gerada nesta preparação tem 1.455.519 bytes e fica ignorada pelo Git.

Quem não possui o acervo pode executar os testes sintéticos imediatamente. Para o smoke test real, solicite `sample.npz` por armazenamento externo autorizado da equipe e coloque-o em `data/sample/`. Não existe URL pública de dados configurada nem download automático. Confira com o responsável a autorização de distribuição.

## 4. Alternar para a fonte completa

Mude `DATASET_MODE=full` e execute `python scripts/check_dataset.py`. Isso verifica **uma imagem** da fonte completa, não processa o acervo inteiro. `GOES_MEMBER` seleciona um membro específico; vazio usa o primeiro nome ordenado.

A configuração nova alimenta os utilitários de desenvolvimento. Os scripts científicos anteriores mantêm seus argumentos explícitos e não passam a aceitar `sample.npz` como se fosse o ZIP/CSV completo. Exemplo de auditoria, com saída local separada:

```powershell
python src/data/audit.py --csv D:/dados-goes/dataset_weather.csv --zip D:/dados-goes/dataset_goes.zip --readme D:/dados-goes/README.md --output data/local-reports/audit
```

EDA, piloto e viabilidade dependem de resultados de etapas anteriores, inclusive JSON/CSV locais deliberadamente excluídos do Git. Um clone contém a documentação histórica, não todos os insumos desses scripts. Para reproduzir a cadeia, gere auditoria, EDA e piloto em ordem, seguindo [o guia histórico](docs/history/README_pre_github.md). Alguns scripts escrevem relatórios Markdown em caminhos fixos; faça reexecuções em branch própria e revise diferenças antes de commitá-las. Não execute `provenance_inventory.py` sem ajustar seus caminhos locais explícitos.

## 5. Estrutura

```text
config.py                  configuração dos utilitários
scripts/make_sample.py     geração local de uma amostra
scripts/check_dataset.py   verificação de uma imagem na fonte selecionada
scripts/check_staged.py    validação do índice antes do commit
src/data/                  auditoria, EDA, viabilidade e proveniência
src/features/              reconstrução GOES e piloto
 tests/                    testes artificiais; não exigem acervo
reports/                   documentação histórica Markdown versionável
 docs/history/             documentação anterior preservada
 data/                     somente local, ignorado
.env.example               exemplo sem credenciais
.githooks/pre-commit        hook que chama o verificador
```

## 6. Primeiro commit e publicação (referência histórica)

Os comandos abaixo devem ser executados **na raiz `projeto-goes`**, não em Downloads ou na pasta que contém o dataset. A preparação não criou commit nem remoto e não fez push. Crie primeiro um repositório vazio no GitHub, sem inicializar README/licença, e substitua nome, email e URL pelos seus valores:

```powershell
git init -b main
git config user.name "SEU NOME"
git config user.email "SEU EMAIL"
git config core.hooksPath .githooks
git add .gitignore .gitattributes .env.example .githooks config.py scripts src tests requirements.txt README.md STATUS.md docs reports
git update-index --chmod=+x .githooks/pre-commit
git status --short
git diff --cached --stat
python scripts/check_staged.py
if ($LASTEXITCODE -ne 0) { throw "Índice bloqueado; não fazer commit" }
git diff --cached
# Revise a lista e o conteúdo antes de prosseguir.
git commit -m "chore: preparar projeto de pesquisa para colaboração"
git remote add origin https://github.com/victorhukra/backend-monitoramento-ambiental.git
git push -u origin main
```

Use autenticação do Git Credential Manager ou SSH; nunca escreva token no remoto, README ou `.env.example`. Caso já exista histórico com dados, pare antes do push: `.gitignore` não apaga blobs antigos. Se apenas estiverem no índice antes do primeiro commit, use `git rm --cached -- caminho/exato` e rode a verificação novamente; isso preserva o arquivo local. Não foi encontrado repositório Git prévio nesta raiz durante a preparação.

## 7. Fluxo da equipe

`main` contém código revisado. Cada tarefa usa `feature/nome-curto` (ou `fix/nome-curto`). Após clonar, cada pessoa deve ativar `.githooks` e seu ambiente Python.

```powershell
git switch main
git pull --ff-only
git switch -c feature/nome-curto
# Faça as alterações.
python -B -m unittest discover -s tests -v
git add caminho/do/arquivo.py
python scripts/check_staged.py
if ($LASTEXITCODE -ne 0) { throw "Índice bloqueado" }
git diff --cached
git commit -m "feat: descrever a alteração"
git push -u origin feature/nome-curto
```

Abra um Pull Request para `main` e peça revisão de outra pessoa. Configure no GitHub proteção de `main` com PR/revisão obrigatórios; isso é recomendação, ainda não configurada. Não faça force-push em branches compartilhadas. Cada pessoa mantém seus próprios caminhos/dados em `.env`. Documente mudanças de protocolo antes de implementar tratamento, target ou modelagem.

## Origem do repositório

O repositório remoto existente já continha um commit com a documentação do dataset. Essa documentação foi preservada em [docs/dataset/README.md](docs/dataset/README.md), sem reescrever o histórico. Para colaborar neste repositório, use o fluxo de clone e branches; os comandos de inicialização acima são referência para uma publicação nova.
