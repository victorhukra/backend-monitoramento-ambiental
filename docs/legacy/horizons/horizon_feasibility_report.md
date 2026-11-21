# Viabilidade de previsão de chuva em 1, 3, 6 e 7 horas

Data: 15/10/2026. Estágio 5. **Análise de viabilidade, sem construção de alvos ou treinamento.**

## 1. Conclusão e escopo

Os quatro horizontes são compatíveis com a resolução horária **se** a emissão ocorrer na hora cheia e a exportação tiver preservado a convenção de acumulação da hora anterior. Há entre 59.153 e 59.159 janelas estruturalmente completas. Nenhum horizonte pode ainda ser declarado operacionalmente viável: não estão comprovados o alinhamento original dos acumulados, a disponibilidade histórica das entradas e a geolocalização necessária às atributos GOES regionais.

Não há evidência para excluir antecipadamente 3, 6 ou 7 horas, nem para escolher 1 hora como vencedor. A habilidade preditiva e o ganho do GOES continuam não avaliados. A quantidade final de exemplos é **indeterminada**, não zero e não igual às contagens potenciais abaixo.

Foram reutilizados os relatórios da auditoria, EDA, proposta de protocolo e piloto. Nesta etapa foi relido o CSV inteiro e somente o índice de nomes do ZIP, sem leitura de novos pixels, extração, correção ou novas associações de imagens. A proposta de uma hora do estágio 3 passa a ser uma candidata entre quatro; o documento histórico não foi sobrescrito.

## 2. Evidência temporal e definições candidatas

**Fatos locais:** 59.160 linhas, de 01/01/2020 00h a 30/09/2026 23h, ordenadas, sem lacunas horárias. Localização por `America/Sao_Paulo` com erro explícito em horário ambíguo/inexistente; cálculos em UTC. Não há duplicatas no índice aceito pelo cálculo. O README original define mm e horário local, mas não documenta as bordas dos acumulados nem transformações da exportação.

**Documentação externa:** a [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api#hourly-parameter-definition), consultada em 15/10/2026, define `rain` e `precipitation` como somas da hora anterior; distingue chuva líquida de precipitação total e informa precisão de 0,1 mm para esta última. Isso sustenta uma hipótese de alinhamento, mas não prova que o CSV manteve essa convenção.

**Hipótese C, não confirmada:** o registro em u contém a quantidade referente a (u−1h,u]. Nesse caso, para emissão efetiva t em hora cheia, definir Q_k como a quantidade registrada no timestamp exato t+k horas, k=1,...,H. Esses valores seriam exclusivamente informações do alvo, jamais atributos disponíveis em t.

| Tipo | Pergunta | Expressão candidata, sob C |
|---|---|---|
| A, prioritário | Choveu em algum momento nas próximas H horas? | Algum Q_k > 0 em k=1,...,H; união dos intervalos (t,t+Hh] |
| B, futuro | Choveu somente no intervalo situado entre H−1 e H horas à frente? | Q_H > 0, referente a (t+(H−1)h,t+Hh] |

Em H=1, A e B coincidem. Em H=7, por exemplo, chuva na segunda hora e ausência na sétima fariam A positivo e B negativo. Isso é um exemplo conceitual, não um rótulo calculado do CSV.

**Definição de chuva pendente:** usar `rain` para chuva líquida ou `precipitation` para precipitação total. Ambas são iguais no CSV, finitas e não negativas; o menor positivo observado é 0,1 mm. Igualdade numérica não elimina a diferença conceitual. “Mensurável” aqui significa quantidade positiva registrada pelo produto histórico, não medição de pluviômetro nem comprovação de chuva em cada ponto de Londrina.

Alternativas para discussão: (i) algum acumulado horário >0; (ii) algum acumulado horário ≥τ, com τ positivo e justificado; (iii) soma no intervalo ≥τ, que pergunta por volume acumulado e não pelo mesmo evento de (ii). Não fixamos τ. Para quantidades não negativas, soma >0 e algum valor >0 são equivalentes em uma janela completa, mas essa equivalência não resolve a semântica temporal. A ausência de registro nunca equivale a zero.

Se a proveniência mostrar timestamps de início de intervalo, o mapeamento muda para t,...,t+(H−1)h. Não usamos esse cenário como verdade alternativa nem misturamos os dois. É necessário obter requisição, resposta com unidades/fuso e código de exportação, e rastrear linhas até os intervalos de origem antes de criar qualquer alvo.

## 3. Comparação dos horizontes

As contagens seguintes são **condicionais à hipótese C**. O cálculo procura todos os timestamps exatos t+1,...,t+H; não desloca linhas arbitrariamente. Exige as duas colunas de quantidade finitas e não negativas e verifica a finitude das 20 variáveis numéricas em t. Esse último teste é de completude, não certificação física, seleção de atributos ou prova de disponibilidade. Os casos suspeitos da EDA continuam pendentes e não foram excluídos.

| H | Alvo A candidato | Resolução | Janelas completas / quantidades utilizáveis | Também com meteorologia finita em t | Com link original existente | Sem link | Link passa somente fim/criação nominal ≤t |
|---|---|---|---:|---:|---:|---:|---:|
| 1 h | Alguma chuva em (t,t+1h] | 1 intervalo horário | 59.159 | 59.159 | 58.980 | 179 | 50 |
| 3 h | Alguma chuva em (t,t+3h] | 3 intervalos horários | 59.157 | 59.157 | 58.978 | 179 | 50 |
| 6 h | Alguma chuva em (t,t+6h] | 6 intervalos horários | 59.154 | 59.154 | 58.975 | 179 | 50 |
| 7 h | Alguma chuva em (t,t+7h] | 7 intervalos horários | 59.153 | 59.153 | 58.974 | 179 | 50 |

As diferenças N−H resultam da borda final, depois de verificar continuidade e quantidades; não foram presumidas a partir do número de linhas. A última emissão potencial é 30/09/2026 às 22h, 20h, 17h e 16h, respectivamente, no fuso local. Não há período de aquecimento por lags: esses ainda não foram escolhidos. Lags futuros aprovados poderão reduzir a borda inicial.

| Horizonte | Evidência disponível | Quantidade sem ambiguidade temporal comprovada | Limitações específicas | Questões a resolver |
|---|---|---|---|---|
| 1 h | Uma hora seguinte completa em 59.159 posições | Indeterminada | Não localiza minuto de início da chuva | Confirmar C, variável/limiar e disponibilidade |
| 3 h | Três horas seguintes completas em 59.157 posições | Indeterminada | Janelas adjacentes compartilham até 2 horas | Mesmas confirmações; controlar sobreposição de 3 h |
| 6 h | Seis horas seguintes completas em 59.154 posições | Indeterminada | Janelas adjacentes compartilham até 5 horas | Mesmas confirmações; controlar sobreposição de 6 h |
| 7 h | Sete horas seguintes completas em 59.153 posições | Indeterminada | Janelas adjacentes compartilham até 6 horas | Mesmas confirmações; controlar sobreposição de 7 h |

Em **todos** os horizontes, as quantidades de exemplos com meteorologia comprovadamente disponível, GOES efetivamente elegível e coorte final comparável são indeterminadas. Estão representadas por `null` no JSON e `NA` no CSV, nunca por zero. Não são 50 exemplos confirmados.

## 4. Aquisição, criação e disponibilidade do GOES

| Evento | Evidência | O que permite concluir |
|---|---|---|
| Timestamp meteorológico | `time` local | Referência nominal; não publicação/recebimento |
| Início GOES | `s` no nome; `timestamp_utc` nas amostras anteriores | Início da aquisição, não disponibilidade de imagem completa |
| Fim GOES | `e` no nome | Fim nominal da aquisição |
| Criação do produto | `c` no nome | Criação do netCDF de origem; não conversão/recebimento do NPZ |
| Disponibilidade utilizável | Logs históricos ausentes | Não determinada |

A [convenção NOAA de nomes](https://raw.githubusercontent.com/NOAA-Big-Data-Program/nodd-data-docs/main/GOES/README.md), consultada em 15/10/2026, identifica s/e/c e os décimos de segundo. Reutilizamos o leitor `name_time` da EDA. A leitura integral de nomes não valida metadados internos de todos os NPZ.

**Fatos calculados:** o índice contém 59.033 membros; todos os links preenchidos existem. Nenhum nome vinculado falhou na leitura de s/e/c ou na ordem s≤e≤c. Nas 58.981 linhas com imagem, 58.931 têm início, fim e criação posteriores a t. Só 50 passam o filtro necessário e≤t e c≤t. A diferença de 21 segundos observada na primeira imagem continua incompatível com emissão naquela hora: aquisição e criação ainda estavam no futuro.

Os 50 casos permanecem nas quatro populações condicionais. Dois referenciam imagens já conhecidas como totalmente inválidas; 42 têm qualidade de pixels não examinada nos manifestos consultados. Os seis restantes têm algum pixel válido na matriz, mas não possuem validação regional ou prova de disponibilidade. Não se deve chamar 48 de “amostra válida”.

**Limites:** este filtro testa somente os links fornecidos, sem idade máxima, latência real, recebimento, QA regional ou nova busca por imagens anteriores. Portanto, não mede a cobertura de uma futura associação causal. Os 179 links ausentes não demonstram inexistência de qualquer imagem anterior elegível. O número igual a 50 nos horizontes é uma coincidência deste diagnóstico em t, não garantia de amostras finais iguais.

**Regra recomendada para discussão:** exigir fim de aquisição, criação e disponibilidade utilizável ≤t, mais idade máxima e qualidade regional aprovadas. Selecionar a última imagem que atenda a todos esses critérios, preservando o link original e a rastreabilidade. Sem logs, uma latência simulada deve ser explicitamente hipótese de estudo retrospectivo, não prova de operação. Nenhuma regra definitiva foi aplicada nem associação nova criada.

## 5. Ausências, qualidade e resolução

Não há quantidades ausentes/não finitas/negativas nas duas colunas nem valores não finitos nas variáveis numéricas em t. Isso não resolve suspeitas físicas já registradas na EDA, revisões da reanálise ou atraso de publicação. O conjunto é histórico derivado de modelos/reanálises, não observação direta de uma estação.

Em cada população condicional, seis referências apontam às quatro matrizes totalmente inválidas conhecidas, devido a reuso. São contagens de linhas, não seis imagens únicas. Não estimamos falhas no restante do acervo. O piloto também identificou uma imagem com apenas 1,61% de pixels válidos; fração da matriz inteira não garante cobertura útil sobre Londrina. As duas grades ainda precisam de geolocalização validada. Nenhum registro foi removido.

Uma futura falta em qualquer hora da janela impediria afirmar ausência de chuva na janela toda. Uma hora positiva conhecida pode demonstrar ocorrência apesar de outra ausente, mas introduzir essa regra assimétrica exige protocolo explícito. Para este diagnóstico, exigimos todas as horas para positivos e negativos, sem calcular nenhum deles.

Todos os H inteiros cabem na resolução horária; 7 horas não exige interpolação. Porém, os dados não localizam início, duração ou intensidade sub-horária. Se t for 10h15, a janela até 11h15 ou 17h15 não pode ser reconstruída exatamente a partir de acumulados em horas cheias. Adiar t para esperar uma imagem altera a janela futura; não manter silenciosamente o alvo antigo.

O ponto/região de Londrina não representa a chuva ao longo de uma rota de caminhão. A aplicação agrícola exigiria validação local e requisitos agronômicos específicos. Os exemplos motivadores não são capacidades demonstradas pelo conjunto de dados. Chuva positiva registrada não define automaticamente risco ou segurança nessas aplicações.

## 6. Avaliação cronológica e comparação futura

**Viabilidade estrutural:** a série contínua de vários anos permite propor avaliação cronológica para os quatro H. **Viabilidade efetiva:** ainda depende da coorte elegível, contagem de eventos por período, sazonalidade e cobertura de satélites/grades. Não foram criadas partições. As datas sugeridas no estágio 3 permanecem proposta, não aprovação.

Para cada H, comparar futuramente modelo A (meteorologia) e B (mesma meteorologia + GOES) usando exatamente os mesmos instantes, alvos, partições e critérios de qualidade. Uma análise meteorológica em coorte mais ampla pode ser complementar, mas não estima isoladamente o ganho do GOES. As coortes podem diferir entre horizontes; comparações entre H devem explicitar isso ou usar uma interseção comum para análise controlada.

Antes de uma fronteira b entre períodos, exigir que a janela do alvo do período anterior termine até b e que nenhum intervalo-alvo seja compartilhado pelos dois lados. Sob a convenção proposta, t+Hh≤b para exemplos anteriores; exemplos seguintes começam em b. Conferir as bordas efetivamente, sem remover cegamente um número de linhas. A separação deve considerar também suporte dos lags, imagens reutilizadas e revisões dos dados. Caso necessário, aplicar embargo adicional justificado, não escolhido pelo teste.

Janelas sobrepostas dentro de um período compartilham observações de chuva e não são exemplos independentes. H maior altera essa dependência e a distribuição do evento; isso não prova que prever seja mais fácil ou difícil. Futuramente usar avaliação e incerteza que respeitem blocos temporais, comparar baselines e examinar estabilidade por estação/ano/sensor. Não selecionar H por desempenho no teste final.

Riscos obrigatórios a controlar:

- Imagens iniciadas, concluídas, criadas ou recebidas depois da emissão; proximidade temporal não basta.
- Meteorologia/reanálise cuja versão só foi publicada ou revisada depois de t; timestamp antigo não prova disponibilidade.
- Rain, precipitation, weather_code ou outros campos referentes ao intervalo futuro como entradas.
- Imputação, normalização e escolha de atributos, região, limiar ou hiperparâmetros usando validação indevida ou teste final; ajustes aprendidos apenas no treino, decisões pelo desenvolvimento permitido.
- Divisão aleatória, duplicatas, janelas-alvo compartilhadas e imagens reutilizadas em períodos diferentes.
- Comparar modelos em amostras diferentes, confundindo ganho do GOES com seleção de cobertura/qualidade.

## 7. Reprodutibilidade, testes e preservação

Código: `src/data/horizon_feasibility.py`, reutilizando `fingerprint` da auditoria e `name_time` da EDA. O cálculo salva somente contagens, nunca coluna de alvo, tabela por emissão ou atributos. Sem instalações novas, sem nova leitura de pixels e sem cópia do conjunto de dados. Os relatórios anteriores permanecem históricos.

Da raiz do projeto, com Python, numpy e pandas já disponíveis:

```text
python -B src/data/horizon_feasibility.py --csv C:/Users/CANAL/Downloads/Backend_UTFPR/dataset_weather.csv --zip C:/Users/CANAL/Downloads/dataset_goes.zip
python -B -m unittest discover -s tests -v
```

Saídas: `feasibility_counts.json` (fontes, parâmetros, versões e contagens), `horizon_comparison.csv` (comparação numérica), este relatório interpretativo e `tests.txt`. Reexecutar o cálculo regenera JSON/CSV; mudanças de fontes exigem revisão deste texto e novo registro dos testes.

**27 testes passaram**, sendo 24 preservados e três novos: lacuna temporal não tratada como linha consecutiva; quantidade ausente/borda final; rejeição de timestamps duplicados ou sem fuso. Testes artificiais independem do ZIP. A conferência de fontes antes/depois passou: SHA-256 para arquivos pequenos, tamanho/mtime para ZIP, sem hash integral de 79 GB. Versões efetivas constam do JSON.

## 8. Decisões e evidências necessárias

1. Confirmar a semântica dos acumulados e transformação dos timestamps com o código/requisição/resposta original. Essa é a condição para materializar alvos de qualquer H.
2. Escolher chuva líquida versus precipitação total e definição de mensurável; aprovar o alvo A como prioridade, mantendo B separado.
3. Fixar emissão, inventário de entradas, versões disponíveis e modalidade retrospectiva ou operacional. Obter logs ou arquivo operacional para alegar elegibilidade real.
4. Resolver geolocalização nas duas grades e definir região, idade máxima e qualidade mínima sem usar resultados de teste.
5. Só então medir cobertura por associação causal e coortes por H, eventos por período e fronteiras cronológicas. Não extrapolar a qualidade da amostra de pixels para todo o acervo.
6. Aprovar o desenho antes de construir conjunto de dados de treino ou treinar modelos. Não escolher antecipadamente um horizonte.

Fontes locais: README original, §§1–4; `reports/dataset_audit.md`; `reports/eda/eda_report.md`; `reports/eda/goes_sample_details.json`; `reports/protocol/protocol_proposal.md`; `reports/pilot/goes_pilot_report.md` e `image_diagnostics.json`. A ressalva do piloto sobre a imagem parcialmente inválida prevalece sobre a generalização textual anterior da EDA. Fontes externas estão vinculadas junto às definições; não comprovam a proveniência da exportação local.
