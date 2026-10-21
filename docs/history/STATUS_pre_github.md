# STATUS — Projeto de previsão de chuva com GOES

**Data da revisão: 21/10/2026.** Registro do estado encontrado em disco, após as etapas 1–6 e a preparação do resumo para reunião com o professor.

## 1. Resumo geral

**Avançamos bastante na compreensão dos dados e na construção de ferramentas de diagnóstico. Ainda estamos na fase estrutural e metodológica do projeto de Machine Learning.** Não começamos a fase experimental de treinamento e avaliação preditiva.

O trabalho não se resume a uma estrutura de pastas: há oito arquivos de implementação, quatro arquivos de testes, análises reproduzíveis, tabelas, manifestos, 12 gráficos e relatórios técnicos. Os principais riscos de validade do experimento foram identificados antes da modelagem. Isso é avanço concreto de pesquisa e engenharia.

Por outro lado, não há dataset supervisionado definitivo, região GOES validada, target aprovado, divisão temporal ou modelo treinado. Ainda não sabemos se o GOES melhora a previsão. Não seria honesto atribuir um percentual de conclusão: a recuperação da proveniência e da geolocalização pode mudar o desenho do estudo.

**Objetivo atual:** investigar se características numéricas GOES acrescentam informação à meteorologia para prever ocorrência de chuva em algum momento das próximas **1, 3, 6 ou 7 horas**, na região de Londrina. Esses horizontes são candidatos, não escolhas definitivas. A comparação futura deve usar os mesmos exemplos e alvos para meteorologia isolada e meteorologia + GOES.

### Alcance desta revisão

Foi inventariada a árvore do projeto, incluindo arquivos ocultos, código, testes, documentos e saídas. Arquivos textuais foram lidos para inspeção; JSON/CSV foram verificados quanto à leitura e o código Python quanto à sintaxe. Foram conferidos os metadados das dependências locais e executados os testes unitários. Os PNG foram inventariados; não foi feita nova avaliação visual individual de cada gráfico.

Não foram reexecutados a EDA, o piloto ou o inventário de proveniência, nem relidos os pixels do acervo. Os resultados científicos abaixo são os registrados nos estágios anteriores. Esta revisão cria somente este documento; preserva dados, código e relatórios históricos.

## 2. O que já foi feito

### 2.1 Etapas e resultados

| Etapa | Trabalho concluído | Resultado e limite |
|---|---|---|
| 1 — Auditoria | CSV completo, índice do ZIP, leitura de NPZ, integridade estrutural e preservação | 59.160 linhas × 22 colunas; série horária de janeiro/2020 a setembro/2026; sem lacunas ou timestamps duplicados identificados |
| 2 — EDA | Distribuições, extremos, consistência física, sazonalidade, chuva, cobertura e análise temporal das imagens | 40 arquivos em `reports/eda/`, 12 figuras e 192 NPZ únicos amostrados; não houve limpeza automática |
| 3 — Protocolo | Proposta de definição do problema, disponibilidade, prevenção de vazamento e avaliação cronológica | Documento para discussão; não constitui protocolo integralmente aprovado |
| 4 — Piloto GOES | Leitura seletiva, metadados, máscara de pixels inválidos, reconstrução em Kelvin e repetibilidade | 19 imagens: 15 reconstruções e quatro totalmente inválidas; nenhuma feature regional real |
| 5 — Horizontes | Contagem por timestamps exatos para 1/3/6/7 horas; diagnóstico dos links originais | Janelas estruturalmente completas sob hipótese temporal; nenhum target criado |
| 6 — Proveniência e geolocalização | Busca de código/arquivos de origem, metadados de três representantes e plano de recuperação | Requisição/exportação meteorológica e geolocalização do recorte continuam não comprovadas |
| Apoio à reunião | Síntese breve para o professor | Documento separado, com perguntas prioritárias; não é evidência de aprovação ou retorno da reunião |

**Dados meteorológicos:** 179 linhas sem imagem associada. Não foram encontrados valores ausentes nas colunas meteorológicas ou valores infinitos nas verificações anteriores. `rain` e `precipitation` são numericamente iguais: 49.040 zeros e 10.120 positivos, mas isso não torna suas definições conceitualmente equivalentes.

**Consistência física:** os testes descritivos não encontraram, por exemplo, precipitação negativa ou umidade relativa fora de 0–100%. Foram sinalizados 1.939 registros com radiação positiva e indicador noturno e 131 com rajada inferior à velocidade do vento. São suspeitas a investigar em função das janelas temporais e do modelo de origem, não erros automaticamente confirmados. Extremos estatísticos foram mantidos.

**GOES:** o ZIP tem 59.033 NPZ e aproximadamente 79,2 GB de tamanho de arquivo. A EDA encontrou 67 imagens reutilizadas, com 69 referências adicionais, e 121 NPZ não referenciados pelo CSV. Ausência de referência não foi classificada automaticamente como erro.

Há duas grades: 885×1217 e 882×1217. GOES-19 aparece nas duas; satélite e grade não são categorias equivalentes. Quatro matrizes totalmente inválidas foram encontradas na amostra dirigida. No piloto, uma das 15 reconstruções tinha apenas 1,61% dos pixels válidos. A amostra não estima a taxa de falhas do acervo inteiro.

**Temporalidade:** apenas 50 dos links originais passam a condição nominal de fim de aquisição e criação até o horário de referência. Isso não comprova recebimento ou elegibilidade operacional e não limita uma futura busca de imagens anteriores a 50 exemplos.

| Horizonte candidato | Janelas completas condicionais |
|---|---:|
| 1 hora | 59.159 |
| 3 horas | 59.157 |
| 6 horas | 59.154 |
| 7 horas | 59.153 |

Esses números pressupõem que o registro representa o acumulado da hora anterior, hipótese ainda não comprovada na exportação. Não são quantidades de exemplos finais de treinamento.

### 2.2 Funcionalidades e módulos implementados

| Arquivo | Responsabilidade atual |
|---|---|
| `src/data/audit.py` | Leitura/auditoria do CSV e ZIP; estatísticas básicas; leitura NPZ; interpretação escalar; comparação temporal; fingerprints de fontes; relatório inicial e interface de linha de comando |
| `src/data/eda.py` | Estatísticas numéricas/categóricas, verificações físicas, episódios de chuva/ausência, agregações temporais, reuso/cobertura, amostragem determinística, parsing dos horários NOAA e exportação de resumos |
| `src/data/eda_figures.py` | Geração de histogramas, distribuições de chuva, evolução mensal, sazonalidade, boxplots anuais, vento circular, variáveis especiais, correlação exploratória e diferenças temporais GOES |
| `src/data/eda_report.py` | Consolidação interpretativa da EDA e diagnósticos complementares; conteúdo específico do conjunto examinado |
| `src/data/horizon_feasibility.py` | Verificação de janelas por timestamps exatos; contagens condicionais por horizonte; diagnóstico nominal dos links; salva apenas resumos, sem rótulos |
| `src/data/provenance_inventory.py` | Inventário de arquivos e metadados de até três combinações satélite/grade; registra nomes de origem e URLs candidatos; não materializa pixels |
| `src/features/goes.py` | Leitor e reconstrução C13 reutilizáveis; `PhysicalImage`, validação de metadados/identidade, máscara antes da transformação, unidade Kelvin, estados explícitos de falha, limites de leitura/expansão e `allow_pickle=False` |
| `src/features/pilot.py` | Seleção pequena de janeiro/2023 com casos dirigidos; duas leituras sequenciais; comparação de payload/diagnósticos; medição de tempo/memória rastreada; manifestos, CSV/JSON e relatório |

O nome `features` não significa que a extração regional esteja pronta. Média, desvio padrão populacional, mínimo, máximo e mediana foram verificados em matrizes artificiais. Nas imagens reais, não houve máscara validada de Londrina nem geração das cinco features regionais.

### 2.3 Testes e verificação

| Arquivo | Testes | Cobertura principal |
|---|---:|---|
| `test_audit.py` | 5 | Máscara, Kelvin/unidades, offset temporal, imagem inválida, metadados ausentes |
| `test_eda.py` | 3 | Nomes NOAA, fração de segundo/virada de ano e blocos interrompidos por lacunas |
| `test_goes_pilot.py` | 16 | Reconstrução, sentinelas, não finitos, estatísticas sintéticas, shapes, metadados, falhas e reprodutibilidade |
| `test_horizon_feasibility.py` | 3 | Timestamps exatos, lacunas, ausências, bordas e índices ambíguos |

**Reexecução em 21/10/2026: 27 testes passaram em 0,084 s**, com Python 3.12.14 e `-B`, sem modificar registros históricos de testes. Os testes não dependem do ZIP original. Não há medição de cobertura de código nem certificação da qualidade de todas as imagens.

### 2.4 Tecnologias e dependências

O projeto usa **Python**, **NumPy**, **pandas** e **Matplotlib**. A biblioteca padrão fornece `unittest`, `zipfile`, `io`, `pathlib`, `argparse`, `json`, `hashlib`, `datetime`, `re`, `dataclasses`, `tracemalloc`, entre outros. Não são instalações adicionais.

| Dependência direta | `requirements.txt` | Evidência de ambiente |
|---|---|---|
| NumPy | 2.5.4 | Presente na pasta de apoio da EDA; runtime usado agora nos testes contém 2.3.5 |
| pandas | 3.0.1 | Confirmado no runtime atual e nos manifestos anteriores |
| Matplotlib | 3.11.2 | Instalação local em `work/eda-deps`; não detectado no ambiente padrão usado agora para os testes |

Pacotes auxiliares encontrados em `work/eda-deps`: contourpy 1.4.0, cycler 0.12.1, fonttools 4.66.1, kiwisolver 1.5.1, packaging 26.3, Pillow 12.3.0, pyparsing 3.3.3, python-dateutil 2.9.0.post0 e six 1.17.0, além de NumPy e Matplotlib citados acima. Esses registros confirmam a instalação local, não uma instalação global do sistema.

**Pendência de reprodução:** requirements e runtime não são um ambiente único idêntico. Não foi feita nova instalação, atualização ou validação de instalação limpa nesta revisão. A suíte passando não garante que os gráficos rodem no mesmo ambiente sem incluir as dependências da EDA.

Não há uso implementado de scikit-learn, Random Forest, TensorFlow/PyTorch, Cartopy, netCDF4 ou xarray no projeto. Alguns nomes aparecem como propostas ou exemplos do README original; isso não comprova instalação ou implementação. O runtime conferido não detectou scikit-learn. Também não há API web, frontend, banco de dados, serviço de inferência, Docker ou configuração de CI no diretório examinado. O nome do projeto “Backend” não corresponde ainda a um backend de aplicação.

## 3. Estrutura de pastas e arquitetura

### 3.1 Localização efetiva

O código e os relatórios técnicos estão em:

`C:/Users/CANAL/Documents/Codex/2026-10-13/files-mentioned-by-the-user-firstprompt/outputs/projeto-goes`

Este `STATUS.md` foi salvo nessa raiz, ao lado do README. O diretório de trabalho atual do chat é outro:

`C:/Users/CANAL/.codex/.chatgpt-projects/g-p-6ace62a79ce88191a858e81af40b14f3`

Nele estão `AGENTS.md`, `sources/` e `reports/project/meeting_summary.md`. `sources/` não apresentou arquivos nesta inspeção e é reservado a referências sincronizadas somente para leitura. O resumo da reunião não está dentro da árvore principal de código. Nenhum arquivo foi movido para ocultar essa separação.

### 3.2 Árvore principal

```text
projeto-goes/
├── STATUS.md                       # este retrato histórico
├── README.md                       # execução e histórico incremental
├── requirements.txt                # três dependências diretas fixadas
├── .gitignore
├── data/
│   ├── raw/.gitkeep                 # reservado; fontes externas
│   ├── sample/.gitkeep              # reservado; amostras lidas em memória
│   └── processed/.gitkeep           # sem dataset tratado/supervisionado
├── src/
│   ├── data/                       # seis arquivos de análise/diagnóstico
│   └── features/                   # leitor GOES e piloto, dois arquivos
├── tests/                          # quatro arquivos, 27 testes
└── reports/
    ├── dataset_audit.md
    ├── audit_results.json
    ├── eda/                        # 40 arquivos
    ├── figures/                    # 12 PNG
    ├── protocol/                   # uma proposta
    ├── pilot/                      # seis arquivos
    ├── horizons/                   # quatro arquivos
    └── temporal/                   # sete arquivos
```

Os números excluem caches de bytecode e referem-se à inspeção atual. Os diretórios de dados contêm somente `.gitkeep`. `work/eda-deps` está fora da raiz principal, como apoio de execução.

Fontes originais permanecem externas: `C:/Users/CANAL/Downloads/Backend_UTFPR/dataset_weather.csv`, o README dessa pasta e `C:/Users/CANAL/Downloads/dataset_goes.zip`. Nenhuma cópia integral do dataset está no projeto.

### 3.3 Como os componentes se conectam

Os scripts leem CSV/ZIP e geram tabelas, manifestos e relatórios separados. A EDA reutiliza funções da auditoria; a viabilidade reutiliza o parser temporal da EDA; o piloto reutiliza a auditoria e o leitor GOES. A leitura é seletiva, sem extrair o ZIP inteiro. Não há fluxo de treinamento ou execução operacional contínua.

A organização é adequada a uma pesquisa incremental, mas ainda baseada em scripts: imports com ajustes de `sys.path`, alguns caminhos locais fixos, ausência de configuração central e de empacotamento (`pyproject.toml`). `provenance_inventory.py` executa o diagnóstico no corpo do arquivo; não deve ser tratado como biblioteca sem efeitos ao importar. Alguns geradores de relatório contêm interpretações/datas específicas da execução original e exigem revisão ao trocar dados.

## 4. Pendências e próximos passos

### 4.1 Bloqueios científicos prioritários

1. **Comprovar o significado temporal do CSV.** Recuperar requisição, resposta e código de exportação; rastrear timestamps e acumulados. A documentação genérica Open-Meteo não comprova a transformação local. Esse é o bloqueio principal para alvos definitivos.
2. **Validar geolocalização.** Recuperar navegação/projeção e código ou índices do recorte para as duas grades e os sensores envolvidos. Três produtos originais já foram identificados; as tentativas anteriores de HEAD falharam por DNS, não por inexistência comprovada. Não houve nova tentativa nesta revisão.
3. **Definir disponibilidade das entradas.** Início, fim, criação, publicação e recebimento são eventos distintos. Sem logs, uma latência simulada pode fundamentar apenas um cenário retrospectivo declarado. A meteorologia histórica também requer avaliação de versões/revisões.
4. **Aprovar escolhas metodológicas.** Variável e limiar de chuva, horizontes, região fixa, idade máxima da imagem, qualidade regional mínima, tratamento de ausência e modalidade retrospectiva/operacional. Não há confirmação registrada dessas decisões.

**Menor próxima tarefa útil:** obter do produtor um exemplo completo de requisição/resposta meteorológica e o trecho de exportação, preferencialmente cobrindo chuva e virada de dia. Em paralelo, solicitar o código de conversão/recorte GOES. Repetir estatísticas sobre o mesmo CSV não resolve essas lacunas de proveniência.

### 4.2 Organização e reprodução a melhorar

- Unificar/documentar o ambiente de execução, reconciliando as versões efetivas e fixadas e verificando instalação limpa. Não atualizar bibliotecas indiscriminadamente.
- Atualizar futuramente o início e a árvore do README: ainda destacam auditoria/EDA e horizonte de uma hora, embora seções posteriores já cubram o estágio 5. A etapa 6 está documentada em relatórios separados.
- Definir uma localização oficial para documentação de reunião e código, preservando as referências sincronizadas e os históricos.
- Centralizar caminhos/parâmetros e reduzir dependência de caminhos Windows específicos; Ubuntu está descrito, mas não foi executado nas verificações registradas.
- Distinguir texto histórico de texto regenerável nos relatórios. O piloto já corrige a generalização da EDA sobre zero pixels inválidos nas demais imagens; o JSON detalhado continha o caso parcial.
- Considerar versionamento e automação de verificações quando houver necessidade: não há `.git` ou pipeline de CI dentro da raiz principal examinada. Isso não afirma ausência de Git em diretórios externos/ancestrais.

### 4.3 Trabalho ainda não implementado

Permanecem ausentes: máscara geográfica validada, extração regional em escala, associação causal definitiva de imagens, tabela supervisionada, target, tratamento/imputação/normalização de treino, divisão treino/validação/teste, modelos, busca de hiperparâmetros, métricas preditivas e comparação meteorologia versus meteorologia + GOES.

Essas ausências são em grande parte **limites deliberados das etapas anteriores**, não funcionalidades prometidas e esquecidas. Depois de resolver os bloqueios e aprovar o protocolo, será possível construir o dataset com rastreabilidade, verificar fronteiras temporais e iniciar experimentos. Os ajustes aprendidos deverão usar somente treino e a avaliação deverá preservar a cronologia e o controle de imagens/janelas compartilhadas.

## Referências principais para acompanhar o histórico

- [Auditoria](reports/dataset_audit.md) e [EDA](reports/eda/eda_report.md).
- [Proposta de protocolo](reports/protocol/protocol_proposal.md).
- [Piloto GOES](reports/pilot/goes_pilot_report.md).
- [Viabilidade dos horizontes](reports/horizons/horizon_feasibility_report.md).
- [Proveniência temporal](reports/temporal/source_provenance_report.md), [geolocalização](reports/temporal/goes_geolocation_report.md) e [plano de continuidade](reports/temporal/next_steps.md).
- Resumo da reunião: `C:/Users/CANAL/.codex/.chatgpt-projects/g-p-6ace62a79ce88191a858e81af40b14f3/reports/project/meeting_summary.md`.

Este documento registra o estado em 21/10/2026; propostas citadas não devem ser interpretadas como decisões aprovadas ou resultados de modelos.
