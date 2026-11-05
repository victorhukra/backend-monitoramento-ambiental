# Projeto GOES — auditoria e EDA

Projeto incremental de previsão de chuva na próxima hora em Londrina. Estágios concluídos: auditoria inicial e análise exploratória do CSV completo com amostra estratificada GOES. Nenhum modelo, alvo, divisão temporal ou tratamento foi implementado.

## Estrutura criada

```text
projeto-goes/
├── data/
│   ├── raw/          # reservado; originais permanecem externos
│   ├── sample/       # vazio; leitura da amostra em memória
│   └── processed/    # vazio; nenhum processamento do conjunto de dados
├── src/data/
│   ├── audit.py              # estágio 1 preservado
│   ├── eda.py                # análise e amostragem determinística
│   ├── eda_figures.py        # figuras científicas
│   └── eda_report.py         # relatório interpretativo
├── reports/
│   ├── dataset_audit.md
│   ├── audit_results.json
│   ├── eda/                  # tabelas, manifestos e eda_report.md
│   └── figures/              # 12 gráficos PNG
├── tests/
│   ├── test_audit.py         # preservado
│   └── test_eda.py           # 3 testes de fronteiras temporais
├── .gitignore
├── README.md
└── requirements.txt
```

Os diretórios de dados contêm apenas `.gitkeep`. Tratamento, atributos, alvo, divisão temporal, modelos e avaliação continuam pendentes de autorização; não há módulos vazios para eles.

## Fontes originais

- CSV: `C:\Users\CANAL\Downloads\Backend_UTFPR\dataset_weather.csv`
- ZIP: `C:\Users\CANAL\Downloads\dataset_goes.zip`
- README do conjunto de dados: `C:\Users\CANAL\Downloads\Backend_UTFPR\README.md`
- Documento adicional preservado: `C:\Users\CANAL\Downloads\firstprompt.md`

Este README documenta o projeto; não substitui nem modifica o README original. As fontes não foram copiadas, movidas, renomeadas ou extraídas. As instruções do README original foram tratadas como documentação do formato, não como autorização para executar seus exemplos de treinamento ou visualização.

## Executar no Ubuntu

Python 3.12 ou superior para as dependências atuais. A partir da pasta do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/data/audit.py --csv /caminho/Backend_UTFPR/dataset_weather.csv --zip /caminho/dataset_goes.zip --readme /caminho/Backend_UTFPR/README.md
python -m unittest discover -s tests -v
```

Substitua os três caminhos pelos locais reais no Ubuntu. A instalação é restrita ao ambiente virtual. Não é preciso descompactar o ZIP. Dependências diretas fixadas nas versões usadas nesta execução; dependências transitivas ficam a cargo do pip. No Windows, pandas instala suporte de fuso horário como dependência transitiva.

## Executar no Windows

Com Python e as dependências já disponíveis, a partir da pasta do projeto:

```powershell
python src/data/audit.py --csv 'C:\Users\CANAL\Downloads\Backend_UTFPR\dataset_weather.csv' --zip 'C:\Users\CANAL\Downloads\dataset_goes.zip' --readme 'C:\Users\CANAL\Downloads\Backend_UTFPR\README.md'
python -m unittest discover -s tests -v
```

Nesta máquina, o atalho `python` do Windows não funcionou. A execução efetiva utilizou o interpretador já existente em `C:\Users\CANAL\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`, sem instalar nada globalmente. Em PowerShell, substitua `python` por `& 'caminho completo do interpretador'`.

## Funcionamento e limites

O programa lê o CSV de 12,8 MB com pandas e o índice central do ZIP, compara todos os links por caminho exato e carrega apenas o primeiro NPZ associado. Não tenta corrigir caminhos, escolher a imagem mais próxima nem modificar dados. O ZIP externo e o NPZ interno são abertos com a biblioteca padrão `zipfile`; numpy usa `allow_pickle=False`.

Há limites explícitos de 128 MiB para o CSV, 32 MiB para a amostra NPZ e 128 MiB para sua expansão interna. O índice do ZIP cresce com o número de arquivos; esta implementação foi exercitada com cerca de 61 mil entradas. Não houve medição de pico de RAM, mas o programa não lê os 79 GB em memória.

Relatórios são regenerados em `reports/`; `--output` permite outro diretório. `--source` pode registrar fontes adicionais na verificação de preservação. As fontes pequenas recebem hash SHA-256 antes/depois; para o ZIP compara-se apenas tamanho e data de modificação. A integridade de todo o ZIP não foi certificada.

## Achados principais

- 59.160 linhas e 22 colunas, de 01/01/2020 a 30/09/2026, sem lacunas horárias ou registros duplicados.
- 179 linhas sem imagem. Todos os 58.981 links preenchidos existem no ZIP; são 58.912 caminhos distintos.
- 59.033 NPZ no ZIP; 121 não referenciados pelo CSV. Os caminhos do ZIP se estendem até 06/10/2026.
- A amostra GOES-16 é uma matriz int16 de 885 × 1217, com 1.077.045 pixels válidos pela máscara disponível.
- Correção após releitura no estágio 2: `timestamp_utc` da primeira imagem é `2020-01-01T03:00:21+00:00`, conforme o JSON/relatório histórico disponível. A afirmação anterior deste README sobre offset `-03:00` não é corroborada pelos arquivos atuais. A captura continua 21 segundos após a referência do CSV.
- A reconstrução resultou em 195,5655–297,8239 K. Estatísticas completas, metadados, avisos e limitações estão em `reports/dataset_audit.md` e `reports/audit_results.json`.

## EDA — estágio 2 concluído

Leia [o relatório completo](reports/eda/eda_report.md). Ele separa fatos, hipóteses, limitações e recomendações; contém links para as 12 figuras. Resultados tabulares estão em `reports/eda/`, sem duplicar o conjunto de dados original.

- CSV reafirmado: 59.160 linhas × 22 colunas, série horária contínua. Rain e precipitation são iguais nesta base: 82,89% de zeros, 17,11% de valores positivos, máximo 18 mm.
- 131 registros têm rajada abaixo do vento; 1.939 têm radiação positiva com indicador noturno. São suspeitas a investigar, sem correção ou exclusão automática.
- 192 NPZ únicos amostrados com seed 42, estratificação por mês UTC/satélite e casos dirigidos. Quatro matrizes sem pixels válidos; a frequência na amostra não estima prevalência populacional.
- Duas grades, 885×1217 e 882×1217; GOES-19 aparece em ambas. Mesma unidade/escala não garante comparabilidade espacial.
- 203 pares CSV–GOES: 195 capturas posteriores e oito anteriores, desvios de −5.380 a +4.820 segundos. A amostra inclui deliberadamente extremos. Não presumir disponibilidade na emissão da previsão.
- 67 imagens reutilizadas, 69 referências adicionais; maior intervalo de reuso de duas horas. 179 linhas sem link, incluindo uma sequência de 39 horas. Os 121 NPZ não referenciados ficam fora do intervalo de referências do CSV.
- Cinco testes originais preservados e três testes novos passaram. A conferência de preservação compara SHA-256 de arquivos pequenos e tamanho/mtime do ZIP; não é hash integral do acervo.

### Reproduzir a EDA

Python 3.12 ou superior para as versões fixadas no estágio 2. A execução foi validada em Python 3.12 no Windows; Ubuntu ainda não foi executado. `requirements.txt` agora inclui matplotlib e registra numpy 2.5.4, pandas 3.0.1 e matplotlib 3.11.2, usados na EDA. Apenas dependências diretas estão fixadas.

Dentro do ambiente virtual do projeto:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/data/eda.py --csv /caminho/Backend_UTFPR/dataset_weather.csv --zip /caminho/dataset_goes.zip --readme /caminho/Backend_UTFPR/README.md
```

No Windows, os mesmos argumentos aceitam os caminhos originais já documentados. Nesta execução, matplotlib e suas dependências foram instalados somente na pasta de apoio `work/eda-deps`, fora da entrega; o manifesto registra o ambiente efetivo. Não houve instalação global. Para uma instalação nova, prefira o ambiente virtual e o requirements.

O script não extrai NPZ; lê uma matriz por vez e salva somente resumos. A análise do índice usa nomes nominais; apenas a amostra tem metadados e pixels examinados. A seed é 42, com dois arquivos por mês UTC/satélite e complemento por transições, reusos, extremos e bordas. Consulte `goes_sample_manifest.csv` para reproduzir os nomes exatos. Estatísticas completas ficam no JSON de detalhes.

Para reemitir somente o relatório após a EDA, sem ler novamente imagens:

```bash
python src/data/eda_report.py
```

O texto interpretativo foi elaborado para o conjunto de dados auditado; ao trocar as fontes, revise as conclusões, além de recalcular os números. `run_manifest.json` registra fontes, versões e parâmetros. `tests.txt` registra a execução desta entrega; para atualizar esse registro, capture uma nova execução de unittest antes de reemitir o relatório. Os relatórios do estágio 1 permanecem históricos.

## Piloto técnico GOES — estágio 4

O estágio 3 documentou a [proposta de protocolo](reports/protocol/protocol_proposal.md), ainda não aprovada integralmente. O estágio 4 executou somente leitura, reconstrução física e qualidade: [relatório do piloto](reports/pilot/goes_pilot_report.md).

- Código novo: `src/features/goes.py` (leitor/reconstrução reutilizável) e `src/features/pilot.py` (seleção pequena e relatório).
- Amostra: 19 NPZ únicos, incluindo 12 referências equiespaçadas de janeiro/2023 e casos dirigidos já conhecidos na EDA; algumas categorias se sobrepõem.
- Quinze reconstruções em Kelvin e quatro estados explícitos de matriz totalmente inválida. Nenhuma substituição de falha por zero.
- Das quinze reconstruções, uma tem somente 1,61% dos pixels válidos; as outras catorze não têm fill/não finitos. O relatório esclarece uma divergência entre a descrição da EDA e seu JSON detalhado sobre esse caso parcial.
- As 19 imagens foram lidas duas vezes sequencialmente, com payloads e diagnósticos idênticos. Sem extração do ZIP e sem novas dependências.
- 24 testes passaram: oito anteriores e 16 novos, usando matrizes artificiais para reconstrução, fill variável, não finitos, estatísticas, metadados, formatos e reprodutibilidade.
- **Seleção espacial não validada:** NPZ sem coordenadas por pixel/vetores x/y ou projeção completa. O README fornece limites aproximáveis, mas faltam evidências de centros/bordas, orientação e correspondência ao recorte. Nenhuma máscara ou atributo da região de Londrina foi criada. As cinco estatísticas foram testadas apenas em dados artificiais.

Resultados em `reports/pilot/`: `sample_manifest.json`, `image_diagnostics.json`, `image_diagnostics.csv`, `run_manifest.json`, `tests.txt` e `goes_pilot_report.md`. As contagens e faixas físicas são diagnósticos da matriz inteira, não atributos regionais. Os relatórios dos estágios anteriores continuam preservados.

### Reproduzir o piloto

O leitor requer apenas numpy e pandas, já presentes no ambiente usado (numpy 2.3.5 e pandas 3.0.1). Não requer matplotlib; as dependências fixadas do projeto continuam disponíveis para a EDA. Use um Python com essas bibliotecas e, da raiz do projeto:

```bash
python -B -m unittest discover -s tests -v
python -B src/features/pilot.py --csv /caminho/Backend_UTFPR/dataset_weather.csv --zip /caminho/dataset_goes.zip --readme /caminho/Backend_UTFPR/README.md
```

No Windows, substituir os caminhos pelos originais documentados. O executável usado está na seção de ambiente acima. `-B` evita criar/modificar cache de bytecode dos módulos existentes. O piloto lê os manifestos da EDA, sem repetir a EDA. Resultados do piloto são regenerados somente em `reports/pilot/`. `tests.txt` é o registro da execução entregue; para atualizá-lo, capture novamente a saída dos testes nesse arquivo.

Para atualizar apenas o texto do relatório, sem ler imagens:

```bash
python -B src/features/pilot.py --report-only
```

Próximo requisito técnico: coordenadas/atributos de projeção do netCDF de origem e mapeamento do recorte NPZ por assinatura, ou geolocalização por pixel validada. Depois será possível definir e validar uma região fixa. alvo, protocolo temporal final e modelo continuam pendentes de confirmação.

## Viabilidade de múltiplos horizontes — estágio 5

O [relatório comparativo](reports/horizons/horizon_feasibility_report.md) investiga 1, 3, 6 e 7 horas, priorizando ocorrência em algum momento da janela inteira (alvo A), distinta da ocorrência somente na última hora (alvo B).

Sob a hipótese ainda não confirmada de acumulados da hora anterior, existem respectivamente 59.159, 59.157, 59.154 e 59.153 janelas completas. São contagens estruturais, não alvos criados ou exemplos operacionais confirmados. Apenas 50 links originais passam o filtro necessário de fim/criação nominal até t; disponibilidade real, nova associação causal e qualidade regional continuam pendentes. Isso não limita uma futura associação a 50 casos.

Resultados e parâmetros ficam em `reports/horizons/`, com comparação CSV/JSON e registro de 27 testes aprovados (24 anteriores e três novos). O código `src/data/horizon_feasibility.py` reutiliza a auditoria/EDA, lê o CSV e o índice do ZIP, sem novos pixels. Comandos de reprodução estão no relatório. Nenhum horizonte foi escolhido, nenhum alvo ou modelo foi criado. A semântica temporal precisa ser comprovada antes da construção dos alvos.

## Continuidade

Antes da próxima etapa, confirmar a semântica temporal, definir variável/limiar dos alvos candidatos de 1, 3, 6 e 7 horas, instante de emissão, disponibilidade das variáveis, latência/idade máxima de imagens, estratégia espacial e fronteiras temporais. Recomenda-se exigir produto completo disponível até a emissão, não apenas captura iniciada. Capturas futuras e reanálises indisponíveis em tempo real podem causar vazamento. Não usar alvo como atributo, não embaralhar a avaliação temporal, não ajustar transformações fora do treino, não selecionar variáveis pelo teste e não confundir chuva zero com ausência de dados. O projeto para após a análise de viabilidade do estágio 5, aguardando confirmação para qualquer preparação de modelo.
