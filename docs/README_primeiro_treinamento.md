# Primeiro treinamento do MVP meteorológico de Londrina

Guia de implementação e passagem de responsabilidade — **26/10/2026**.

**Escopo decidido:** somente dados meteorológicos tabulares. Imagens ficam fora deste fluxo e não são pré-requisito. Não precisamos implementar API, banco ou tela para treinar.

**Estado verificado:** existe preparação de dados e tabela experimental; não existem divisão cronológica executada, `scripts/train.py` ou modelo treinado. Este guia é documentação: propostas abaixo dependem de decisão da equipe, não são configurações aprovadas nem funcionalidades implementadas.

## 1. Objetivo e primeira entrega

Usar quatro medidas meteorológicas do horário T para estimar se haverá chuva na próxima hora em Londrina. É uma classificação binária: resposta **0 (sem chuva)** ou **1 (com chuva)**, acompanhada de uma probabilidade estimada.

A primeira entrega deve ser pequena: uma tabela conferida, períodos documentados, uma referência simples de comparação, um Random Forest, métricas e um modelo salvo que possa ser carregado novamente. Não incluir busca extensa de parâmetros, novas variáveis, infraestrutura de experimentos ou serviços nesta entrega.

**Experimento retrospectivo** significa testar com dados históricos disponíveis hoje. Isso não demonstra que os mesmos valores estavam acessíveis quando a previsão teria sido emitida. O README do dataset declara dados de modelos/reanálises da Open-Meteo, não medições diretas de uma estação.

## 2. O que aproveitar e o que falta

Todos os caminhos deste guia partem da raiz do repositório.

| Arquivo ou grupo | Estado e uso nesta entrega |
|---|---|
| [config.py](../config.py) | Reutilizar `WEATHER_FEATURES`, `WEATHER_TIMEZONE` e `settings()['training']`. Centraliza caminhos e nomes das entradas. |
| [scripts/prepare_weather.py](../scripts/prepare_weather.py) | Já implementado. `prepare_table` prepara em memória; `run` lê/grava arquivos. Reutilizar, sem recriar o alvo no treino. |
| [tests/test_prepare_weather.py](../tests/test_prepare_weather.py) | Oito testes de preparação: alvo exato, lacunas, valores inválidos, fuso, duplicatas e proteção da fonte. Preservar. |
| [requirements.txt](../requirements.txt) | Contém NumPy, pandas e Matplotlib. Precisa incorporar a dependência de treinamento com versão validada. |
| [.env.example](../.env.example) | Modelo de configuração. Corrigir o `.env` local, não colocar caminhos pessoais no código. |
| `data/processed/weather_training.csv` e arquivos acompanhantes | Já existem nesta máquina, ignorados pelo Git. A tabela não acompanha o clone. |
| `src/data/audit.py`, `eda.py`, `eda_figures.py`, `eda_report.py` | Investigação e relatórios já realizados. Não são etapas obrigatórias a repetir para treinar; alguns fluxos também dependem de imagens. |
| `src/data/horizon_feasibility.py`, `provenance_inventory.py` | Investigação de horizontes e origem. Consultar conclusões, sem executá-los como preparação obrigatória. |
| `src/features/goes.py`, `pilot.py`, `scripts/make_sample.py`, `check_dataset.py` | Relacionados às imagens, fora deste fluxo. Não executar nem exigir seus dados. |
| `scripts/train.py` | **A implementar:** leitura da tabela, verificações, divisão, treino, avaliação e salvamento. |
| `tests/test_train.py` | **A implementar:** testes pequenos das fronteiras, seleção das entradas e recarga do modelo. |
| `docs/integration/` | Contratos propostos da aplicação. A integração acontece depois; não há servidor necessário ao treinamento. |

Não fazer uma refatoração ampla. Um script com funções curtas e comentários explicando o motivo das regras é suficiente. A configuração atual menciona caminhos de imagens, mas a preparação meteorológica não os abre; manter `DATASET_MODE=sample` válido não exige arquivo de amostra.

### Resultado já documentado e conferido anteriormente

- Original: 59.160 linhas, de 01/01/2020 00h a 30/09/2026 23h.
- Derivado: **59.159 linhas, sete colunas**, com T até 30/09/2026 22h.
- Alvos: 49.039 zeros e 10.120 positivos (aproximadamente 17,11%).
- Sem ausências, horários duplicados ou lacunas internas na tabela conferida.
- Única exclusão: T = 30/09/2026 23h, sem registro em T+1h para definir a resposta.
- Última execução registrada: **38 testes passaram**, incluindo os oito da preparação. Não é resultado de modelo.

O resumo local `weather_training.json` registra `split_created=false`. A auditoria e EDA antigas podem dizer que ainda não havia alvo: são retratos anteriores à preparação de 22/10, não uma instrução para recomeçar.

## 3. Pendências indispensáveis e seus limites

### 3.1. Significado dos horários e da chuva

O original contém horários sem offset. O código associa **America/Sao_Paulo** conforme o README e exporta timestamps com offset. Neste período, 14h local corresponde a 17h UTC. Associar um fuso a um horário local e converter um horário já em UTC são operações diferentes.

O alvo atual é `rain(T+1h) > 0 mm`, sob a **hipótese de que rain(u) representa (u−1h,u]**. Assim, rain às 15h representa chuva entre 14h e 15h. O código encontra T+1h pelo timestamp exato, não pela posição da próxima linha.

A associação matemática foi conferida. Porém, o relatório de proveniência não encontrou a requisição original, resposta bruta ou código de exportação capazes de confirmar a janela e eventuais deslocamentos. O README informa mm no intervalo, sem fechar as bordas temporais. `rain` e `precipitation` são iguais neste arquivo, mas isso não prova equivalência conceitual nem a janela.

**Como resolver:** solicitar ao produtor esses materiais; acompanhar uma virada de dia e uma sequência seco–chuva–seco da resposta original até o CSV. Verificar fuso, unidades, deslocamentos e se o mesmo processo cobriu todo o período. Uma consulta nova não comprova a exportação antiga.

**Dependência:** para afirmar alvo definitivo, precisamos dessa confirmação. Para o MVP experimental, a equipe pode registrar a hipótese e aceitar explicitamente a limitação. Se surgirem evidências contrárias, revisar os alvos antes de interpretar os resultados.

### 3.2. Disponibilidade em T

Timestamp da variável é sua referência temporal, não prova de publicação ou recebimento. Mesmo as quatro medidas em T podem vir de análises produzidas depois. Não há logs históricos suficientes no material consultado para demonstrar disponibilidade operacional.

**Decisão necessária:** seguir como experimento retrospectivo condicionado às hipóteses, ou exigir comprovação operacional antes do treino. A proposta para esta primeira versão é a primeira opção, registrada no relatório, sem prometer desempenho em tempo real.

Para uma versão operacional posterior, definir fonte e registrar horários de referência, publicação/recebimento e versão das entradas. Acrescentar um atraso arbitrário não comprova que reanálises estavam disponíveis.

### 3.3. Impedimentos práticos

| Pendência | Etapa afetada | Critério de resolução |
|---|---|---|
| Caminho do CSV configurado aponta para arquivo inexistente | Regeneração da tabela | `settings()['csv'].is_file()` retorna `True` para a fonte correta |
| Datas e regra de fronteira não aprovadas | Divisão e avaliação | Decisões registradas antes de comparar modelos |
| Dependência e script de treino ausentes | Treinamento | Instalação compatível, script e testes funcionando |
| Hipótese do alvo e escopo retrospectivo não registrados para o experimento | Interpretação dos resultados | Equipe aceita a limitação ou confirma a origem antes de seguir |

O CSV original foi localizado em Downloads; a tabela preparada existe. Portanto, o caminho incorreto não impede ler a tabela existente, mas deve ser corrigido na passagem do projeto. Novos gráficos, mais entradas, ajuste fino, validação operacional e integração com API podem ficar para depois.

## 4. Decisões a fechar antes do primeiro experimento

Preencher responsável, data e decisão final em um pequeno registro Markdown. A tabela abaixo contém **propostas**, não decisões tomadas por este guia.

| Decisão | Importância e evidência disponível | Proposta inicial |
|---|---|---|
| Escopo temporal | Origem histórica declarada; disponibilidade em T não comprovada | Retrospectivo experimental, com hipótese temporal explícita |
| Definição de chuva | Código usa `rain > 0`; mínimo positivo documentado é 0,1 mm | Manter qualquer chuva líquida positiva; não trocar coluna ou limiar silenciosamente |
| Horizonte | Preparação e contrato usam uma hora | Manter T → (T,T+1h], condicionado à semântica da fonte |
| Entradas | Quatro colunas já preparadas e alinhadas ao contrato da API | Manter exatamente `WEATHER_FEATURES`, na mesma ordem |
| Períodos | Seis anos completos e janeiro–setembro/2026 | Treino 2020–2024; validação 2025; teste janeiro–setembro/2026 |
| Alternativa de calendário | Teste 2026 não cobre outubro–dezembro | Se ciclo completo for prioritário: treino 2020–2023, validação 2024, teste 2025; reservar 2026 para avaliação adicional futura |
| Fronteiras | Alvo está uma hora após T | Exigir `target_time < início do conjunto seguinte` |
| Intervalo adicional | Sem janelas móveis; horizonte de uma hora | Sem intervalo extra além da exclusão de fronteira, salvo evidência de latência ou mudança do objetivo |
| Ausências e inválidos | Preparação rejeita linhas inelegíveis e registra motivos; tabela atual sem ausências | Manter política atual, sem imputação; parar se a tabela recebida divergir e investigar |
| Modelo e referência | Nenhum modelo implementado | Referência sempre seca e Random Forest pequeno, configuração fixa |
| Limiar de decisão | Contrato propõe 0,5; não houve validação | Começar com 0,5, distinto do limiar de chuva em mm; eventual ajuste só na validação |
| Métricas | Cerca de 83% das linhas são secas | Matriz de confusão, precisão, recall, F1 da chuva e acurácia; decidir peso de alarmes falsos versus chuvas perdidas |
| Reprodutibilidade | Preparação já registra hash e versões | Semente proposta 42; salvar parâmetros, versões, datas e hashes |

Escolher uma proposta de calendário antes de treinar. Não testar alternativas e selecionar a que produz o melhor resultado de teste. Não equalizar artificialmente as classes da validação ou do teste.

## 5. Ambiente e arquivos necessários

### 5.1. Instalar o ambiente atual

No PowerShell, dentro da pasta com `config.py` e `requirements.txt`:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

Se o ambiente já existe, apenas ativá-lo. As versões declaradas hoje são NumPy 2.5.4, pandas 3.0.1 e Matplotlib 3.11.2. A instalação limpa dessas versões na máquina do colega ainda precisa ser conferida; a execução anterior usou ambientes locais já disponíveis. Se houver incompatibilidade ou pacote indisponível, registrar o erro e ajustar versões compatíveis em conjunto, sem atualizar tudo silenciosamente.

### 5.2. Configurar a fonte

Copiar `.env.example` para `.env` **somente se `.env` ainda não existir**:

```powershell
Copy-Item .env.example .env
```

Na máquina atual, editar estas linhas:

```dotenv
WEATHER_CSV_PATH=C:/Users/CANAL/Downloads/Backend_UTFPR/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

No computador do colega, usar a localização real da cópia recebida. Caminhos relativos partem da raiz do projeto; variáveis do processo prevalecem sobre `.env`. O clone não contém CSVs: compartilhar o CSV original e, se útil, os derivados por armazenamento da equipe. Não copiar dados para pastas de código.

Conferência existente, executada nesta inspeção:

```powershell
python -B -c "from config import settings; c=settings(); print('CSV:', c['csv'], c['csv'].is_file()); print('Tabela:', c['training'], c['training'].is_file())"
```

Nesta máquina, antes de corrigir a configuração, o primeiro resultado foi `False` e o segundo `True`. O original em Downloads existe. Para quem vai preparar do zero, o primeiro deve ser `True`; o segundo só será `True` após gerar a tabela.

### 5.3. Conferir o código existente

```powershell
python -B scripts/prepare_weather.py --help
python -B -m unittest discover -s tests -v
```

O `--help` foi verificado nesta inspeção e aceita `--csv`, `--output` e `--plot`. A suíte teve 38 testes aprovados na última execução, em 25/10; não foi executada novamente para escrever este guia. Os testes usam exemplos sintéticos e não exigem acervo real de imagens.

### 5.4. Adicionar o necessário para treinar — tarefa futura

Se a proposta Random Forest for aceita, adicionar **scikit-learn** ao ambiente e fixar em `requirements.txt` a versão validada. Instalação inicial a ser executada pelo implementador, não realizada nesta tarefa:

```powershell
python -m pip install scikit-learn
python -m pip check
python -c "import sklearn; print(sklearn.__version__)"
```

Esse comando não fixa uma versão: depois de verificar compatibilidade e testes, registrar a versão exata no arquivo de dependências para os demais repetirem o ambiente. Se usar `joblib` diretamente para salvar o modelo, declarar também sua versão como dependência direta. Não instalar servidor web, bibliotecas de imagens ou ferramentas de acompanhamento de experimentos para este treino.

## 6. Roteiro de implementação, em ordem

### 6.1. Conferir a entrada e a tabela existente

**Arquivos:** `config.py`, CSV original, tabela derivada e seu JSON. **Entrada:** arquivos recebidos e decisões registradas. **Saída:** resumo da conferência e hashes, sem editar a fonte.

Conferir nomes/tipos de colunas, datas mínima/máxima, ordem crescente, duplicatas de T, horas ausentes, ausências/não finitos e domínio das medidas. Repetições de valores em horários diferentes não são automaticamente duplicatas erradas.

A tabela esperada contém, nesta ordem: `time`, `temperature_2m`, `relative_humidity_2m`, `pressure_msl`, `cloud_cover`, `target_time`, `rain_next_hour`. Validar alvo somente 0/1 e diferença de uma hora em todas as linhas. Os timestamps do derivado já têm offset: lê-los como instantes e converter para São Paulo, sem localizar novamente como se fossem horários ingênuos.

**Verificação:** conferir a versão recebida contra o JSON e os números da seção 2. Divergências não devem ser escondidas removendo registros até as contagens coincidirem.

### 6.2. Reutilizar a criação do alvo futuro

**Arquivo existente:** `scripts/prepare_weather.py`. **Entrada:** CSV original. **Saída:** tabela experimental, JSON, CSV de exclusões, prévia e gráfico opcional.

Somente se ainda não houver tabela ou se houver mudança aprovada no protocolo:

```powershell
python -B scripts/prepare_weather.py --plot
```

Para nova versão, sem sobrescrever:

```powershell
python -B scripts/prepare_weather.py --output data/processed/weather_training_v2.csv --plot
```

Ao usar outro nome, atualizar `WEATHER_TRAINING_PATH` para que o futuro treino não leia a versão antiga. A saída deve ficar dentro de `data/processed/`. O script não sobrescreve arquivos existentes.

O código já faz a junção por T+1h exato e rejeita futuro ausente, chuva futura negativa/não finita e entradas inválidas. Não preencher um alvo ausente com zero. Não aplicar um segundo deslocamento ao alvo no treino.

**Verificação:** comparar respostas ao original por timestamp e inspecionar uma virada de dia. Exemplo real já conferido: T = 01/01/2020 14h tem entradas 33,3 °C, 42%, 1005,3 hPa, 93%; a chuva às 15h gera alvo 1. Isso confirma alinhamento no arquivo, não a hipótese sobre a origem.

### 6.3. Preparar X e y

**Arquivo a criar:** `scripts/train.py`. **Entrada:** tabela conferida. **Saída:** entradas X, alvo y e horários mantidos separadamente para divisão/auditoria.

- X: somente a lista explícita `WEATHER_FEATURES`, preservando sua ordem.
- y: `rain_next_hour`.
- Horários: `time` e `target_time`, usados para selecionar conjuntos, não como entradas deste MVP.

Não usar “todas as colunas exceto o alvo”. Não normalizar ou imputar por hábito: a tabela atual não precisa de preenchimento, e a proposta de árvores não exige padronização de escala para este fluxo básico. Se a tabela tiver ausências inesperadas, interromper e revisar a preparação.

### 6.4. Dividir cronologicamente

**Arquivo a criar:** função simples dentro de `scripts/train.py`, coberta por `tests/test_train.py`. **Entrada:** datas aprovadas e tabela com horários. **Saída:** seleções separadas em memória e manifesto com contagens/exclusões; não é obrigatório gravar três cópias de CSV.

Para a proposta principal, B1 = `2025-01-01T00:00:00-03:00` e B2 = `2026-01-01T00:00:00-03:00`:

- Treino: T desde 01/01/2020, `time < B1` e `target_time < B1`.
- Validação: `time >= B1`, `time < B2` e `target_time < B2`.
- Teste: `time >= B2`, até o fim elegível da tabela, com alvo até 30/09/2026 23h.

Não usar divisão aleatória ou embaralhamento global. A regra estrita retira do conjunto anterior inclusive o alvo que termina exatamente na fronteira. Por exemplo, T = 31/12/2024 23h consulta 01/01/2025 00h e deve ficar fora do treino. Fazer o mesmo em 31/12/2025 23h, preservando os registros na tabela original e anotando o motivo de não selecioná-los.

**Contagens esperadas somente se essas datas e regras forem aprovadas e a tabela permanecer igual:** 43.847 treino, 8.759 validação, 6.551 teste e duas linhas excluídas nas fronteiras. São deduções das contagens existentes, não resultado de uma divisão executada.

**Verificação:** conjuntos não vazios, horários sem interseção, máximo `target_time` anterior menor que início seguinte, soma de selecionados e excluídos igual ao total. Contar classes em cada período; métricas dependentes de duas classes precisam sinalizar quando uma estiver ausente.

Um intervalo extra de dias não é requisito estrutural para as quatro entradas instantâneas e horizonte de uma hora. Reavaliar se houver latência comprovada, janelas móveis ou necessidade de separar eventos de chuva completos. Horas próximas continuam correlacionadas; não prometer independência total.

### 6.5. Treinar referência e modelo

**Arquivo a criar:** `scripts/train.py`. **Entrada:** apenas X/y de treino para o ajuste. **Saída:** referência e modelo ajustados, parâmetros e previsão na validação.

Implementar funções pequenas para carregar/verificar, separar, treinar, avaliar e salvar. Não criar hierarquias de classes ou um sistema de plugins. Reutilizar as constantes existentes em vez de repetir nomes de colunas.

Proposta de primeiro experimento, sujeita a aprovação:

- **Baseline (referência):** sempre prever classe 0, por exemplo `DummyClassifier(strategy='constant', constant=0)`. Mostra o que acontece ao nunca avisar chuva. [Documentação oficial](https://scikit-learn.org/stable/modules/generated/sklearn.dummy.DummyClassifier.html).
- **Modelo:** `RandomForestClassifier` com `n_estimators=100`, `max_depth=8`, `min_samples_leaf=10`, `random_state=42`, `n_jobs=1`, `class_weight=None`. É uma combinação de árvores com tamanho limitado; proposta inicial simples, não parâmetros otimizados. Registrar todos os parâmetros efetivos. [Documentação oficial](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html).

Sem busca em grade, reamostragem ou balanceamento automático inicialmente. Usar probabilidade da classe **1**, identificando a coluna por `classes_`, e não supondo sua posição sem conferir. Proposta inicial: chuva prevista quando probabilidade ≥ 0,5. Isso é diferente de definir chuva observada como quantidade > 0 mm.

### 6.6. Avaliar primeiro na validação

**Entrada:** previsões da referência e do modelo, comparadas aos mesmos alvos de validação. **Saída:** métricas identificadas como validação, matriz de confusão e breve interpretação.

| Medida | Pergunta que responde |
|---|---|
| Matriz de confusão, rótulos `[0, 1]` | Quantas horas secas/chuvas acertamos, quantos alarmes falsos e quantas chuvas perdemos? |
| Precisão da chuva | Dos avisos de chuva, quantos estavam certos? |
| Recall (sensibilidade) da chuva | Das horas com chuva, quantas detectamos? |
| F1 da chuva | Como resumir o equilíbrio entre precisão e recall? |
| Acurácia | Que fração de todas as horas acertamos? |
| Contagem e proporção de positivos | Em que distribuição essas métricas foram obtidas? |

A referência sempre seca pode parecer boa em acurácia: no conjunto total, aproximadamente 82,89% das linhas são secas. Isso é contexto descritivo, não métrica de teste já obtida. Se houver chuva no período, essa referência terá recall de chuva zero. Se não houver nenhum aviso positivo, precisão tem denominador zero: registrar a convenção adotada, por exemplo zero com aviso, em vez de esconder a situação. Se não houver chuva observada, marcar recall/F1 como não informativos para a tarefa nesse recorte.

Escolher alterações de parâmetros ou limiar **somente na validação**, mantendo poucas tentativas registradas. Antes de escolher por F1 ou priorizar recall, combinar o custo de alarmes falsos e chuvas perdidas. Não há meta mínima de desempenho aprovada.

### 6.7. Congelar escolhas e avaliar no teste

**Entrada:** mesmo modelo salvo, escolhas fechadas e teste reservado. **Saída:** avaliação final claramente separada da validação.

Para simplificar o primeiro ciclo, manter o modelo ajustado apenas no treino; não adicionar um reajuste em treino+validação nesta entrega. Congelar entradas, parâmetros, limiar e regras antes de calcular métricas finais. Se o resultado for baixo, relatá-lo; não alterar datas ou parâmetros para melhorar aquele teste.

A EDA já examinou descritivamente todos os anos. Não afirmar que o teste nunca foi visto. A reserva significa não usá-lo para seleção baseada em desempenho a partir de agora. Se ele orientar mudanças posteriores, será necessária outra avaliação independente para confirmar essas mudanças.

## 7. Regras para não usar informações do futuro

1. **Alvo futuro é resposta, não entrada.** `rain(T+1h)` pode definir y, mas nunca X da previsão em T. Também não usar médias que incluam essa hora, `rain_next_hour` ou `target_time` como entrada.
2. **Chuva passada não é proibida por definição.** `rain(T)` ou valores anteriores poderiam ser entradas se sua janela terminasse até T e estivessem disponíveis até a emissão. Isso precisa ser verificado. A primeira versão mantém as quatro entradas e não inclui chuva passada; adicioná-la exigiria nova tabela e contrato de entrada, não uma alteração silenciosa.
3. **Timestamp ≤ T não basta.** A disponibilidade real também depende de publicação/recebimento e versão. No estudo retrospectivo, isso permanece limitação explícita.
4. **Não usar código meteorológico como atalho para a resposta.** Ele não está no conjunto de entradas aprovado para preparação. Qualquer ampliação exige justificativa e revisão temporal.
5. **Aprender transformações só no treino.** Se futuramente houver imputação, escala ou seleção de variáveis, ajustar no treino e aplicar sem reaprender à validação/teste. Uma `Pipeline` pode ajudar, caso essas operações sejam necessárias; não precisamos adicioná-las agora. [Orientação oficial sobre vazamento](https://scikit-learn.org/stable/common_pitfalls.html).
6. **Não preencher com dados posteriores.** Interpolação usando os dois lados ou preenchimento a partir da próxima observação pode trazer futuro para T. Ausência do alvo não é ausência de chuva.
7. **Respeitar as fronteiras pelo alvo**, não somente pela data das entradas. Testes automatizados devem proteger essa regra.

## 8. Verificação rápida antes do treino completo

**Esta etapa depende da implementação futura; não existe opção `--smoke` atualmente.**

Primeiro, criar testes sintéticos que confirmem: ordenação e fuso; nenhuma entrada futura; junção exata preservada; exclusão da hora anterior à fronteira; conjuntos disjuntos; rejeição de esquema inválido. Preservar os testes existentes.

Depois, fazer uma execução pequena usando somente o período destinado ao treino, com blocos cronológicos internos de desenvolvimento e ambas as classes quando disponíveis. Usar poucas árvores apenas para verificar leitura → ajuste → previsão → gravação → recarga. Não buscar exemplos no teste para completar a amostra. Não interpretar métricas desse ensaio como resultado científico; marcar a execução como técnica.

Verificar: nenhuma exceção, quatro entradas na ordem correta, uma previsão por linha, probabilidades finitas entre 0 e 1 e resultados reproduzidos após recarregar o modelo no mesmo ambiente. Em seguida executar a configuração completa aprovada, avaliando primeiro a validação.

**Comando futuro, somente depois de criar e documentar o arquivo:**

```powershell
python -B scripts/train.py
```

Hoje esse comando falha porque o arquivo não existe. O implementador deve definir e documentar como fornecer datas, destino e seleção de avaliação final; não há opções de linha de comando prontas neste guia. A execução padrão proposta não deve consumir o teste automaticamente. Preferir uma ação explícita para a avaliação final.

## 9. Salvar o necessário para repetir o experimento

Sugestão de saída futura: `data/experiments/<identificador-da-execucao>/`, com diretório novo por execução. Esses artefatos ficam fora do Git pela política atual.

| Artefato proposto | Conteúdo mínimo |
|---|---|
| `config.json` | Hipótese temporal, alvo, horizonte, fuso, entradas ordenadas/unidades, datas e regra de fronteira, limiar, semente e parâmetros completos |
| `manifest.json` | Hashes do original/derivado, caminho de entrada, versão do código/commit e alterações locais, versões Python/pacotes, horário da execução |
| `split_summary.json` | Limites efetivos de T e alvo, linhas/classes por conjunto e exclusões por motivo |
| `metrics_validation.json` | Referência e modelo, matriz de confusão rotulada e convenção para métricas indefinidas |
| `metrics_test.json` | Somente após avaliação final explícita; indicar quais escolhas já estavam congeladas |
| `model.joblib` | Modelo e, se existirem, transformações ajustadas, junto do esquema e limiar necessários à previsão |
| `predictions_validation.csv` | T, alvo verdadeiro, probabilidade e decisão para auditoria; arquivo do teste somente na avaliação final |

Esses arquivos ainda não são produzidos por nenhum script de treino. Não copiar o dataset inteiro em cada execução: hashes e horários selecionados permitem rastrear a fonte. Recarregar apenas modelos gerados pela equipe e confiáveis. A repetição deve usar as mesmas versões, não apenas a mesma semente.

Hashes registrados na revisão da tabela, para identificar a versão esperada:

- CSV original: `4e83a5248ee7008b0ea4dffb4bba28a80023b1892c4d38ff54cba41b6ee01f4c`.
- Tabela preparada: `a3ea57e03c9b66e575cecbcc47a673a9af69c7c6aeeb5d6f07a18b0e69b609d3`.

O script de preparação já registra hash do original, versões e hipótese em `weather_training.json`; o treinamento deve acrescentar a identificação do derivado, configuração e resultados. Salvar um resumo humano em `reports/project/` para versionar. CSV, JSON, modelo e ambiente permanecem locais; não usar `git add -f` para incluí-los.

## 10. Checklist de passagem de responsabilidade

### O que quem entrega o projeto deve preparar

- [ ] Dar acesso ao repositório e compartilhar este guia e os relatórios citados.
- [ ] Entregar o CSV original e seu README por canal separado do Git; opcionalmente entregar tabela, JSON e exclusões já gerados.
- [ ] Informar os hashes/versões e ajudar a corrigir o caminho no `.env` do colega.
- [ ] Explicar que não há treino, divisão ou API implementados e que as métricas ainda não existem.
- [ ] Encaminhar ao produtor as dúvidas de origem, ou indicar quem dará continuidade à investigação.

### O deve ser decidido com a equipe

- [ ] Aceitar explicitamente o escopo retrospectivo e a hipótese temporal, ou obter evidência da origem antes de seguir.
- [ ] Confirmar alvo, horizonte, quatro entradas e política de ausência.
- [ ] Escolher datas e regra de fronteira; registrar cobertura parcial de 2026, se usada.
- [ ] Confirmar referência, modelo inicial, limiar e métricas para comparar na validação.

### O deve ser implementado e executado

- [ ] Validar ambiente/dependências e caminhos sem exigir imagens.
- [ ] Reutilizar a tabela ou gerar nova versão quando necessário, sem sobrescrever fonte.
- [ ] Implementar `scripts/train.py` e testes pequenos, preservando a preparação existente.
- [ ] Conferir fronteiras e contagens; executar o ensaio técnico sem abrir o teste final.
- [ ] Treinar referência e modelo, avaliar validação e registrar cada escolha.
- [ ] Congelar a configuração; avaliar o teste uma vez para encerrar o ciclo.
- [ ] Salvar artefatos, recarregar o modelo e verificar que as previsões se reproduzem.

### Como reconhecer que o primeiro treino funcionou

O fluxo técnico funcionou quando lê a versão correta dos dados, separa períodos sem sobreposição indevida de alvos, ajusta somente no treino, produz probabilidades/decisões válidas e salva um modelo recarregável com resultados rastreáveis. **Desempenho baixo não invalida a execução**, mas pode mostrar que o modelo ainda não tem utilidade. Não confundir “rodou corretamente” com “prevê bem”.

Apresentar à equipe: decisões e limitações; datas e contagens por conjunto; exclusões de fronteira; comparação baseline × modelo na validação e, quando concluído, no teste; matriz de confusão; parâmetros/limiar; versões/hashes; caminho do modelo; comando final realmente implementado; teste de recarga e próximos passos justificados pelos resultados. Não inventar uma taxa de acerto antes da execução.

## 11. Referências e alcance desta revisão

- [Preparação didática](prepare_weather.md) e [código de preparação](../scripts/prepare_weather.py).
- [Auditoria](../reports/dataset_audit.md), [EDA](../reports/eda/eda_report.md) e [README original preservado](dataset/README.md).
- [Proveniência e semântica temporal](../reports/temporal/source_provenance_report.md).
- [Revisão da tabela e dos períodos](../reports/project/revisao_tabela_e_periodos.md).
- [Protocolo anterior, ainda propositivo](../reports/protocol/protocol_proposal.md).

Nesta tarefa foram inspecionados arquivos, código, testes e relatórios existentes, conferida a existência das fontes e executada a ajuda do preparador. Não foram instaladas dependências, regenerados dados, executadas divisões, treinados modelos ou alteradas decisões científicas. Somente este guia foi criado.
