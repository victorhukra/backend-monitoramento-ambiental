# Proposta de protocolo temporal e do problema de previsão — estágio 3

Data: 14/10/2026. **Status: proposta para confirmação, não protocolo aprovado.**

## 1. Resumo executivo

O acervo permite propor um estudo retrospectivo do acréscimo de informação do GOES, mas **não comprova uma simulação operacional sem informação indisponível no instante da previsão**. Horário de referência, intervalo representado e horário de disponibilização são conceitos distintos. A ausência de logs afeta tanto o GOES quanto as variáveis meteorológicas históricas.

**Fato observado:** a EDA confirmou a continuidade horária do CSV, imagens posteriores à referência, imagens reutilizadas e duas grades. **Interpretação:** usar diretamente a linha meteorológica e seu `image_link` como entradas disponíveis em tempo real seria uma suposição não sustentada. **Hipótese a verificar:** o CSV preserva a semântica e os horários originais da API, sem deslocamentos durante a exportação. **Decisão proposta:** aprovar primeiro uma convenção temporal condicionada à proveniência, um alvo e uma regra de elegibilidade. Se não houver comprovação de disponibilidade, identificar o estudo como retrospectivo, condicionado a hipóteses, sem afirmar desempenho operacional.

Proposta inicial: emissão na hora cheia t; intervalo previsto de uma hora imediatamente seguinte; classificação de qualquer chuva líquida positiva como pergunta principal; região geográfica fixa em torno de Londrina, com máscara própria de cada grade; treino em 2020–2024, validação em 2025 e avaliação final em janeiro–setembro/2026. Todas essas escolhas dependem da confirmação indicada na seção 11. Não foi criado target, recorte, feature, partição ou modelo.

Este estágio cria somente este documento. Arquivos originais, código, README do projeto, testes e relatórios anteriores permanecem preservados. Não foi relido o acervo de pixels; as evidências numéricas abaixo provêm dos resultados já existentes.

## 2. Fatos confirmados pelos arquivos

Os caminhos relativos abaixo são relativos à raiz `outputs/projeto-goes/`. Os links desta proposta apontam aos arquivos existentes.

| Evidência | Fato observado e limite da evidência |
|---|---|
| [reports/audit_results.json](../audit_results.json), campos `csv.rows`, `columns`, `time_min`, `time_max`, `missing_hours`, duplicatas | 59.160 linhas, 22 colunas, 01/01/2020 00h a 30/09/2026 23h, frequência horária, sem lacunas ou duplicatas identificadas. Isso não demonstra disponibilidade em tempo real. |
| [reports/eda/rain_comparison.json](../eda/rain_comparison.json), `different_rows`; [rain_summary.csv](../eda/rain_summary.csv) | `rain` e `precipitation` são idênticas neste CSV; 49.040 zeros e 10.120 positivos, respectivamente 82,89% e 17,11%. Essa prevalência é descritiva do período inteiro, não a prevalência calculada de um target futuro após elegibilidade. |
| [reports/eda/goes_temporal_pairings.csv](../eda/goes_temporal_pairings.csv), `delta_seconds`, `direction`, `end_minus_csv_seconds`, `creation_minus_csv_seconds` | 203 pares examinados, 195 capturas posteriores e oito anteriores; desvios entre −5.380 e +4.820 s. Não extrapolar frequências: a seleção incluiu extremos intencionalmente. |
| [reports/eda/goes_sample_details.json](../eda/goes_sample_details.json), `metadata`, `valid_pixels`, `errors`; [manifesto da amostra](../eda/goes_sample_manifest.csv) | 192 NPZ únicos examinados; quatro sem pixels válidos. Não é estimativa populacional de falhas. |
| [reports/eda/goes_grids.csv](../eda/goes_grids.csv), `shape`, `grid_signature`, `satellite`, escala/unidade | Duas grades: 885×1217 e 882×1217; GOES-19 nas duas. Nas amostras: int16, K, escala ≈0,06145332, offset ≈89,62000 e fill −1. Não presumir uniformidade no restante do acervo. |
| [reports/eda/image_reuse.csv](../eda/image_reuse.csv), `rows`, `span_hours`; [missing_image_spells.csv](../eda/missing_image_spells.csv) | 67 imagens reutilizadas, 69 referências adicionais; reuso observado até duas horas. 179 linhas sem link e maior bloco de ausência de 39 horas. |
| [reports/eda/satellite_filename_transitions.csv](../eda/satellite_filename_transitions.csv); [sample_grid_periods.csv](../eda/sample_grid_periods.csv) | Transição nominal para G19 em 07/04/2025 16:00:20,8 UTC. A segunda grade aparece nas amostras de maio/2026 em diante; sua data exata de implantação não foi determinada. |
| [reports/eda/additional_diagnostics.json](../eda/additional_diagnostics.json), `metadata_offset_values`, `metadata_vs_filename_*` | Metadados amostrados em UTC explícito; diferença entre metadado e início nominal do nome de −0,9 a 0 s. A perda de fração de segundo é uma interpretação compatível, não código de geração comprovado. |

O [README original](C:/Users/CANAL/Downloads/Backend_UTFPR/README.md), §§1–5 e §8, informa origem Open-Meteo histórica, região aproximada −23,304°, −51,186°, fuso America/Sao_Paulo, canal C13, pareamento temporal mais próximo e projeções/grades. Ele não informa quando cada registro ou produto ficou acessível ao usuário.

Foram consultados também [reports/dataset_audit.md](../dataset_audit.md), [reports/eda/eda_report.md](../eda/eda_report.md), §§1–12, e os módulos [src/data/audit.py](../../src/data/audit.py), funções `audit`/`inspect_npz`, e [src/data/eda.py](../../src/data/eda.py), funções `name_time`, `csv_analysis`/`sample_goes`. Esses módulos mostram como a auditoria interpretou os dados; **não são o código de aquisição/exportação original** e não provam sua semântica.

## 3. Questões ainda não confirmadas

| Questão | Estado | Evidência necessária |
|---|---|---|
| A exportação preservou timestamps e intervalos originais da API? | Não confirmado. README não descreve transformações anteriores. | Requisição original, resposta com metadados e código de coleta/exportação; rastrear algumas linhas. |
| Qual modelo meteorológico, versão, altitude e configuração de unidades foram usados? | Não confirmado em detalhe. O README fornece descrição geral e m/s para vento. | URL/parâmetros da API, `hourly_units`, coordenadas/célula efetivas, modelo e histórico de versão. |
| Cada variável histórica era acessível em t e na mesma versão que hoje? | Não confirmado. Série retrospectiva não é arquivo de dados disponíveis em cada instante. | Histórico de publicação, ingestão, revisões e/ou arquivo operacional equivalente. |
| Quando o GOES foi publicado, recebido e convertido em NPZ? | Não confirmado. `c` registra criação do produto de origem, não recebimento local. | Logs do distribuidor e de ingestão/processamento; identificação da versão do produto. |
| Qual a precisão geográfica das duas grades? | Há projeção/extensões no README, mas sem validação independente completa. | Coordenadas x/y e atributos de projeção do netCDF de origem, orientação, centros versus bordas e mapeamento da assinatura. |
| Qual latência, idade máxima e fração mínima válida aceitar? | Decisão metodológica pendente, não inferível da taxa de falhas amostrada. | Requisitos de uso e evidência operacional/QA de desenvolvimento. |
| Quanto o GOES melhora a previsão? | Não avaliado. | Experimento temporal futuro, após protocolo aprovado. |

Não se preencherão essas lacunas atribuindo “disponível em t” a tudo que possui timestamp ≤t. Tampouco um atraso fixo de uma hora comprova disponibilidade de reanálises revisadas posteriormente.

## 4. Semântica temporal das variáveis

### 4.1 Separação entre documentação e evidência local

**Documentação externa**, consultada em 14/10/2026: a [Open-Meteo Historical Weather API, Hourly Parameter Definition](https://open-meteo.com/en/docs/historical-weather-api#hourly-parameter-definition) define chuva/precipitação como somas da hora anterior; radiações como médias da hora anterior; insolação como segundos acumulados nessa hora. Temperaturas, umidade, pressões, nebulosidade, vento, direção, umidade do solo e código meteorológico são referidos ao instante indicado; rajadas têm particularidades por modelo. O código meteorológico depende, entre outros campos, da precipitação. São definições da API, **não confirmação de como este CSV foi exportado**.

| Campo/grupo do CSV | Evidência local | Interpretação candidata, condicionada à exportação sem deslocamento |
|---|---|---|
| `time` | README original §2 e §3: hora local; série ISO sem offset | Referência nominal u em America/Sao_Paulo, não um horário de chegada. |
| `rain`, `precipitation` | README §3: quantidade no intervalo, em mm; bordas não especificadas | Registro em u resume (u−1h,u], se preservada a convenção externa. |
| `shortwave_radiation`, `direct_radiation`, `diffuse_radiation`, `direct_normal_irradiance` | README §3: W/m² | Médias de (u−1h,u], sob a mesma condição. |
| `sunshine_duration` | README §3: segundos no intervalo | Soma de duração em (u−1h,u], não medida instantânea. |
| `temperature_2m`, `dew_point_2m`, `apparent_temperature`, `relative_humidity_2m`, `pressure_msl`, `surface_pressure`, `cloud_cover`, `wind_speed_10m`, `wind_direction_10m`, `soil_moisture_0_to_7cm` | Definições/unidades no README §3 | Referência nominal u; periodicidade horária não implica média horária. Disponibilidade ainda desconhecida. |
| `wind_gusts_10m` | README §3; 131 casos suspeitos na EDA §6 | Exige identificação do modelo/janela; não forçar igualdade de janelas com vento médio/instantâneo. |
| `weather_code`, `is_day` | Categórico e binário; EDA §§3/5 | Não são quantidades contínuas. Código tem associação com chuva contemporânea; não pode ser obtido do intervalo alvo para compor entradas. |

**Fato observado:** radiação positiva em alguns horários com indicador noturno e igualdade rain/precipitation. **Interpretação:** esses padrões são compatíveis com convenções distintas de intervalo/instante, mas não as demonstram. **Hipótese:** intervalos preservados da API. **Decisão proposta:** documentar essa hipótese e obter a proveniência antes de materializar o alvo.

Para cálculo, localizar u em America/Sao_Paulo e converter a UTC; manter ambas as representações na rastreabilidade. Não somar/subtrair três horas manualmente nem sobrescrever a fonte. O período 2020–2026 já foi localizado sem ambiguidade na EDA.

### 4.2 GOES: início, fim, criação e disponibilidade

O README original §4 define `timestamp_utc` como início da captura. A documentação oficial [NOAA, About the Data / Filename](https://raw.githubusercontent.com/NOAA-Big-Data-Program/nodd-data-docs/main/GOES/README.md) descreve `s` como início da varredura, `e` como fim e `c` como criação do netCDF. O nome inclui ano, dia do ano, hora, minuto, segundo e décimo de segundo. Essa convenção externa sustenta a leitura de `source_filename`; não prova recebimento pelo usuário.

Exemplo existente, `row_index=0` em `goes_temporal_pairings.csv`:

| Evento | UTC |
|---|---|
| Referência CSV | 01/01/2020 03:00:00 |
| `timestamp_utc` do NPZ | 01/01/2020 03:00:21 |
| Início `s20200010300216` | 01/01/2020 03:00:21,6 |
| Fim `e20200010309529` | 01/01/2020 03:09:52,9 |
| Criação `c20200010310031` | 01/01/2020 03:10:03,1 |
| Recebimento/disponibilidade local | Não confirmado |

**Interpretação:** essa imagem não pode compor uma previsão emitida às 03:00 UTC; esperar 21 segundos também não torna o produto completo disponível. O timestamp do NPZ não é tempo individual de observação de cada pixel. Usar o fim da varredura é uma restrição conservadora para o conteúdo completo, mas insuficiente para provar publicação e ingestão. Datas de arquivos no ZIP ou do download não substituem logs históricos.

### 4.3 Duas alternativas para a pergunta temporal

Notação proposta: t é emissão efetiva; h=1 hora; intervalo alvo I(t)=(t,t+h]. Os parênteses/colchetes são convenção de contabilização, a validar com a origem. O horizonte até o fim é uma hora; a janela começa imediatamente após a emissão, sem antecedência adicional até seu início.

| Alternativa | Significado, variáveis permitidas e compatibilidade | Risco e limite |
|---|---|---|
| **R — retrospectiva condicionada** | Emissão nominal t na hora cheia; meteorologia com referência ≤t e suporte temporal terminado até t, sob hipótese explícita de acesso nessa hora. GOES anterior elegível sob latência assumida. Pergunta: há informação adicional do GOES dadas essas entradas históricas? | Reanálise e revisões podem conter informação indisponível em t. Mesmo sem timestamps futuros, não comprova forecast operacional. Adequada como estudo exploratório retrospectivo, não como promessa de uso em tempo real. |
| **O — operacional com dados disponíveis** | Emissão efetiva t na hora cheia; para cada variável, versão recebida até t e suporte terminado até t; usar última observação elegível, possivelmente defasada. GOES recebido/processado até t. Preserva a pergunta da próxima hora. | Sem logs/arquivo operacional, não é reproduzível com segurança neste acervo. Defasagens e redução de cobertura podem ser relevantes. É a alternativa necessária para alegação operacional. |

**Mapeamento do alvo, ainda condicional:** se o valor em u resume a hora anterior, o alvo para I(t) virá do registro exato u=t+1h. Se evidência da exportação mostrar que u marca início da hora, virá do registro u=t; nesse caso, rain(u), precipitation(u) e quaisquer campos agregados sobre essa hora não podem entrar como features. A segunda possibilidade é uma contingência documental, não uma afirmação de que esse seja o formato. Em ambos os casos, conferir timestamps exatos, não apenas deslocar linhas. Se a semântica continuar incerta, não construir target.

Adiar emissão de t para t+δ e manter o alvo (t,t+1h] prevê parte de um intervalo já iniciado; isso altera a pergunta. Para continuar prevendo a próxima hora inteira, o alvo deve passar a (t+δ,t+δ+1h]. Com δ não inteiro, o CSV horário pode não permitir reconstruí-lo sem dados mais finos. Não adotar interpolação para contornar esse problema.

**Decisão proposta:** manter emissão na hora cheia; escolher R com limitação explícita se a proveniência permitir o alinhamento, ou obter evidência adicional para O. Não resolver a falta de logs supondo atraso operacional arbitrário.

## 5. Alternativas de definição do target

São definições matemáticas candidatas, não colunas calculadas. R(I) denota chuva líquida e P(I), precipitação total, no intervalo I.

| Opção | Interpretação e vantagens | Desvantagens e avaliação proposta | Informação pendente |
|---|---|---|---|
| **A: R(I)>0** | Classificar qualquer chuva líquida positiva registrada; alinhada à pergunta “ocorrência de chuva”. | Sensível à precisão/traços e dominância de zeros. Propor PR-AUC com convenção fixada (por exemplo average precision), precisão, recall, F1, matriz de confusão e Brier/calibração das probabilidades. Acurácia isolada é inadequada. | Semântica do intervalo, resolução efetiva e finalidade prática da detecção. |
| **B: P(I)≥τ**, τ>0 | Classificar intensidade mínima relevante, limiar em mm por hora acumulada. Pode refletir impacto operacional. | Quanto maior τ, menor tende a ser a classe positiva; não estimar sua frequência sem análise própria autorizada. Mesmas métricas de classificação, acrescidas de custos de falsos alarmes/omissões. | Valor de τ, escolha rain versus precipitation e justificativa de domínio. Fixar antes do teste; distinguir ≥ de >. |
| **C: P(I) em mm** | Regressão da quantidade; preserva intensidade e responde pergunta mais ampla. | Zeros e cauda longa dificultam avaliar extremos; MAE e RMSE têm sensibilidades distintas. Propor erros no conjunto todo, em horas positivas e por faixas pré-definidas, com baseline zero e persistência, sem treinar agora. Uma previsão média baixa pode perder picos. | Se o uso exige quantidade ou ocorrência, custos de erros e unidade/intervalo definitivos. |

**Fato observado:** 17,11% de positivos contemporâneos e igualdade das duas colunas, conforme `rain_summary.csv` e `rain_comparison.json`. **Interpretação:** um classificador sempre seco teria acurácia descritiva de 82,89% nessa distribuição, sem habilidade para detectar chuva. Isso é uma referência aritmética, não resultado de avaliação futura. **Hipótese:** essa proporção pode mudar nas partições/coorte elegível. **Decisão proposta:** opção A como estudo principal de ocorrência; B como alternativa apenas se houver necessidade prática de limiar; C como estudo separado, não substituição automática de classificação.

O limiar em mm que define o evento é diferente do limiar de probabilidade que transforma a saída do classificador em decisão. O primeiro deve ser fundamentado na aplicação; o segundo poderá ser escolhido na validação, com critério pré-definido. Nenhum pode ser ajustado para favorecer resultados no teste. Zero observado não é observação ausente.

## 6. Alternativas de seleção temporal das imagens

Definir, por imagem i: sᵢ=início, eᵢ=fim, cᵢ=criação, aᵢ=instante real de disponibilidade utilizável; Amax=idade máxima permitida. A idade proposta é t−eᵢ, não uma diferença entre strings. Verificar coerência dos horários e metadados antes de usar o produto.

| Regra candidata | Vantagem | Limitação/decisão |
|---|---|---|
| Manter o `image_link` original e testar elegibilidade | Preserva associação fornecida e facilita auditoria. | Link mais próximo pode ser futuro; se falhar, marcar inelegível. Não fingir que ele era disponível. Serve como diagnóstico, não regra principal recomendada. |
| Selecionar a imagem mais recente entre as comprovadamente disponíveis | Exigir eᵢ≤t, cᵢ≤t, aᵢ≤t e 0≤t−eᵢ≤Amax; dentre elegíveis, maximizar eᵢ, com desempate determinístico por criação e nome. | Regra recomendada para O; aᵢ não está disponível hoje. Deve incluir tempo de ingestão/processamento e respeitar versão histórica. |
| Selecionar por disponibilidade simulada | Definir aᵢ*=max(eᵢ,cᵢ)+L, com L≥0 como atraso residual assumido após criação/fim, e exigir aᵢ*≤t e idade≤Amax. | Possível apenas como hipótese de R, não evidência operacional. L e Amax devem ser fixados ou comparados em cenários pré-registrados de desenvolvimento, nunca inferidos do desempenho no teste. |
| Aceitar qualquer captura com sᵢ≤t | Implementação aparente simples. | Não recomendada: varredura e criação podem ocorrer depois de t. |

**Fato observado:** a associação original usa proximidade, segundo README §2, e os atrasos amostrais podem ultrapassar uma hora. **Interpretação:** o link fornecido não é filtro causal de disponibilidade. **Hipótese:** pode existir uma imagem anterior elegível no ZIP, mas sua cobertura não foi medida. **Decisão proposta:** no estágio de implementação autorizado, criar um índice derivado e uma nova associação rastreável, preservando `image_link` original. Não limitar a busca apenas à imagem vinculada à linha anterior e não corrigir o CSV.

Não há L nem Amax aprovados nesta proposta. L=0 seria apenas hipótese otimista de publicação imediata após criação, nunca disponibilidade comprovada. Sem comprovação meteorológica, tornar GOES conservador não torna automaticamente o experimento operacional.

Ausente, inválida, temporalmente inelegível e metadado desconhecido serão estados separados. Nenhuma imagem futura poderá substituir falha. Reuso causal da última imagem é aceitável dentro de Amax, com identificação e idade registradas; não é uma nova observação independente. Se uma imagem mais recente falhar em qualidade, eventual recuo para outra anterior deverá ser uma regra determinística aprovada, sem seleção por chuva futura.

## 7. Alternativas de tratamento espacial GOES

| Alternativa | Vantagens | Limitações |
|---|---|---|
| **A: imagem inteira** | Baixo esforço; estatísticas sem reamostragem; útil como referência técnica. | Área extensa pode diluir Londrina; grades/extensões diferentes alteram domínio e pesos dos pixels. Comparabilidade não garantida. |
| **B: região geográfica fixa** | Mesma pergunta espacial ao longo do tempo; foco local; cálculo na grade nativa. | Requer geolocalização validada, tamanho da região e regra de seleção de centros/interseção de pixels. Contagens e áreas de pixels podem variar. |
| **C: grade comum** | Domínio e resolução explicitamente comuns; facilita comparações espaciais. | Introduz interpolação e decisões de resolução, máscara e conservação; maior custo; pode modificar extremos e estatísticas. |

**Fato observado:** duas assinaturas e extensões no README original §8 e em `goes_grids.csv`; GOES-19 usa ambas. **Interpretação:** shape ou nome do satélite não determina localização de um pixel. **Hipótese:** é possível mapear corretamente ambas as grades com os atributos da fonte. **Decisão proposta:** iniciar com B, região fixa centrada nas coordenadas de referência do dataset, após validar a geolocalização. A será comparação técnica opcional; C somente se B não oferecer correspondência suficiente ou se o experimento espacial a exigir.

Raio/contorno não está escolhido. Defini-lo pela escala espacial de interesse e resolução, ou por candidatos pré-definidos examinados somente no desenvolvimento. Nunca selecionar a região que maximiza desempenho no teste. Validar orientação das linhas, centros versus bordas, projeção e unidade das coordenadas com a fonte netCDF; os limites ilustrativos do README sozinhos não certificam uma máscara precisa. Não aplicar índices idênticos às duas grades nem redimensionar para forçar shapes iguais.

Regras numéricas propostas para etapa futura:

- Inspecionar as chaves de cada NPZ e usar seus próprios metadados; unidade/escala desconhecida gera estado explícito, não fallback silencioso.
- Mascarar fill e não finitos **antes** de `raw × scale_factor + add_offset`. Trabalhar em K; Celsius somente quando a unidade for Kelvin. Não confundir temperatura de brilho com temperatura a 2 m.
- Calcular mean, std, min, max e median somente em pixels válidos da região; fixar `ddof=0`, coerente com a PoC. Registrar fração válida e contagem. Nenhum pixel válido significa estatística ausente, nunca zero.
- Definir fração mínima de cobertura espacial como decisão de QA; não derivá-la das quatro falhas direcionadas da EDA. Falhas parciais podem enviesar a média.
- Explicitar se os pesos representam pixels ou área física; para região pequena, média simples pode ser piloto, mas sua adequação deve ser verificada entre grades. Não pressupor áreas iguais.
- Manter satélite e assinatura como metadados de diagnóstico; sua inclusão como preditores seria outra decisão, pois podem identificar período/calibração. Comparar estabilidade por grupo.
- Ausência/invalidade fica registrada; eventual imputação depende de decisão futura e ajuste somente no treino. Sem PNG/JPEG como intermediário numérico.

## 8. Proposta de divisão temporal

**Fato observado:** cobertura 2020–setembro/2026, transição de satélite em 2025 e mudança de grade amostrada em 2026. **Interpretação:** a avaliação recente envolve mudança de distribuição além de sazonalidade. **Hipótese:** os dados elegíveis nesses períodos terão cobertura suficiente, a verificar antes da modelagem. **Decisão proposta:** períodos nominais abaixo, definidos por instante local de emissão e sujeitos às regras de fronteira; nenhuma linha foi atribuída a partições.

| Papel | Período nominal proposto | Uso permitido futuramente |
|---|---|---|
| Treino | 01/01/2020 00h ≤t<01/01/2025 00h | Ajuste dos modelos e das transformações; respeitar disponibilidade do alvo no corte de ajuste. |
| Validação | 01/01/2025 00h ≤t<01/01/2026 00h | Escolhas de desenvolvimento e limiar probabilístico; analisar a transição de satélite. |
| Teste final | 01/01/2026 00h até a última emissão com alvo futuro inteiramente observado | Avaliação única após congelar decisões; último horário de emissão não é automaticamente o último timestamp do CSV. |

Se confirmada a convenção de soma da hora anterior, o último alvo disponível termina em 30/09/2026 23h local; a última emissão possível para uma hora inteira seria 22h. Isso é dedução condicional, não criação de target. O primeiro instante também depende de haver histórico suficiente para as entradas.

Após validação, é possível propor reajuste final em 2020–2025 com escolhas congeladas, antes de avaliar 2026. Assim, GOES-19 pode estar no ajuste final. Não atualizar com alvos de 2026 durante o teste principal. Eventual avaliação com atualização progressiva seria protocolo distinto. Para investigar robustez sazonal durante desenvolvimento, usar janelas cronológicas expansivas em anos anteriores, sem procurar a divisão que oferece melhor teste.

### Fronteiras e prevenção de sobreposição

Em cada corte b, exigir que todo suporte do alvo usado para ajuste termine antes de b e que o rótulo estivesse disponível no momento de ajuste alegado. Com horizonte de uma hora e igualdade excluída por convenção conservadora, isso retira a emissão b−1h do lado anterior. Não é um embargo universal suficiente.

Determinar depois a margem completa com h=1h, maior janela de histórico W, idade máxima Amax, duração da varredura e reuso efetivo. Verificar diretamente intervalos e identificadores: nenhuma imagem deve alimentar lados distintos na comparação principal; eliminar da coorte derivada, por regra pré-fixada, os pares de fronteira conflitantes, sem mexer nos originais. Manter um intervalo sem emissões no começo do bloco posterior pode evitar compartilhamento, mas seu comprimento ainda não é numericamente fixável. Não escolher “duas horas” apenas porque o reuso atual chega a duas horas: o novo pareamento pode mudar esse limite.

Entradas históricas anteriores ao começo de uma partição não são automaticamente vazamento se realmente conhecidas em t; a restrição adicional de não compartilhar imagens serve à avaliação mais conservadora. Separar essa política de independência da regra causal de disponibilidade. Estimar incerteza futuramente em blocos temporais, não tratando horas adjacentes como independentes.

### Comparação justa de A e B

Construir, somente após autorização, uma coorte comum definida por regras independentes do resultado futuro: mesmos instantes, alvo, meteorologia e imagem elegível/qualidade. Ajustar A (meteorologia) e B (mesma meteorologia + GOES) nos **mesmos registros de treino**, e avaliar ambos nos mesmos registros de validação/teste. Usar protocolo e orçamento comparáveis de ajuste, seeds registradas e métricas pré-definidas. Reportar a diferença pareada e cobertura por mês/satélite/grade.

Um modelo A adicional sobre todos os registros meteorológicos pode descrever custo de cobertura, mas não deve ser comparado diretamente ao B de coorte restrita como se a diferença isolasse o GOES. Não selecionar registros pela existência de chuva ou usar dados futuros para preencher falhas. Se for escolhida uma alternativa com indicadores de ausência/imputação, redefinir a comparação e aplicar as mesmas regras pertinentes aos dois modelos.

**Limitação de cegamento:** 2025–2026 já foram examinados descritivamente na EDA. O teste proposto será reservado contra ajuste de modelos daqui em diante, não um teste absolutamente desconhecido. Registrar essa exposição; nenhuma escolha futura será motivada pelo desempenho nele. Uma validação externa realmente intocada exigirá dados ainda não examinados, não existentes nesta entrega. Mudanças de satélite/grade e estação devem ser reportadas como condições do teste; não permitem atribuição causal simples de diferenças ao sensor.

## 9. Desenho do experimento piloto

O piloto proposto é de **engenharia e alinhamento**, não de avaliação de Random Forest.

| Extensão | Vantagem | Limite |
|---|---|---|
| Uma semana (168 emissões nominais) | Depuração rápida e custo pequeno. | Pode não conter chuva, falhas ou trocas de grade; pouco teste de diversidade. |
| Um mês | Mais ciclos diurnos/eventos e oportunidades de reuso; ainda pequeno frente a 59 mil referências. | Não cobre sazonalidade anual ou necessariamente falhas/transições. |
| Blocos pequenos em estações distintas + casos dirigidos | Testa contrastes e erros conhecidos sem acervo inteiro. | Amostra artificial; não serve para inferir prevalência nem estimar habilidade preditiva. |

**Fato observado:** leitura seletiva e sequencial funcionou nos estágios anteriores. **Interpretação:** um mês é viável sem extrair o ZIP. **Hipótese:** a região e a regra temporal estarão definidas antes da execução. **Decisão proposta:** começar com janeiro/2023 (744 horas nominais, dentro do treino proposto), escolhido por calendário e não por desempenho; opcionalmente adicionar a primeira semana de julho/2023 para contraste sazonal. Uma leitura por imagem única, reutilizando apenas resumos, sem manter várias matrizes em RAM. Número final de pares e volume dependerão da elegibilidade, ainda não calculados.

Complementar com os casos já identificados de matriz inválida, reuso, metadados de transição e duas grades em `goes_sample_manifest.csv`, sem uma nova busca orientada por resultados. Casos de 2025/2026 serão **fixtures diagnósticas de formato**, explicitamente expostas, sem alvos ou comparação de habilidade; não usá-los para escolher raio, limiar ou estatísticas por desempenho. Se for exigido teste absolutamente cego, usar exemplos independentes de fonte equivalente ou reservar período futuro em vez desses casos.

Critérios de aceite propostos:

1. Confirmar proveniência e representar corretamente intervalo, referência, emissão e disponibilidade real/assumida.
2. Demonstrar que todas as imagens aceitas satisfazem a regra aprovada; uma captura futura deve falhar explicitamente.
3. Ler NPZ seletivamente, validar metadados, reconstruir unidade e identificar matrizes inválidas sem estatística inventada.
4. Validar geolocalização e máscara separada para cada assinatura; documentar área e contagem de pixels.
5. Calcular futuramente as cinco estatísticas apenas para pixels elegíveis; repetir a execução com resultados idênticos ou tolerância numérica documentada.
6. Registrar motivos de ausência, idade, reuso e falha sem remover fontes; reconciliar totais de elegíveis/inelegíveis com o número de emissões.
7. Verificar fronteiras e compartilhamento de identificadores; medir tempo e pico de memória antes de ampliar o processamento.

Esses passos são um plano. Nenhuma feature, máscara, manifesto de piloto ou target foi criado neste estágio.

## 10. Riscos de vazamento

| Risco | Evidência ou hipótese | Controle proposto |
|---|---|---|
| Captura futura ou produto ainda incompleto | Pares amostrados e exemplo s/e/c | Exigir disponibilidade e fim elegíveis, não só início. |
| Reanálise/revisão publicada depois de t | Logs ausentes; origem histórica declarada | Arquivo operacional/versionado ou limitação explícita de retrospectividade. |
| Uso de rain/precipitation/code do intervalo alvo | Relação contemporânea em `weather_code.csv` | Definir suporte de cada entrada; proibir campos futuros e derivados deles. |
| Misturar início e fim da hora | Exportação não confirmada | Rastrear origem; mapear alvo por timestamp exato, sem inferência pelo nome. |
| Imputação/normalização global | Risco futuro, não implementado | Ajustar somente no treino; não reutilizar parâmetros da EDA global. |
| Escolher features, região, limiar ou latência pelo teste | Risco futuro | Congelar escolhas e orçamento no desenvolvimento. |
| Divisão aleatória, imagem compartilhada, alvo atravessando corte | Reuso observado e horizonte de uma hora | Cortes cronológicos, purga por suporte e verificação de identificadores. |
| Seleção de coorte favorecendo B | Ausências/invalidade não uniformes | Coorte comum, regras sem alvo futuro e relatório de cobertura. |
| Confundir nova grade com sinal de chuva | Mudanças temporais observadas | Diagnóstico estratificado; não imputar causalidade ao sensor. |
| Reclassificar a EDA como teste cego | Todo o período foi descrito | Declarar exposição e reservar desempenho final; confirmação futura independente. |

## 11. Decisões que dependem de confirmação

| Decisão | Proposta para aprovação | O que permanece pendente |
|---|---|---|
| Natureza do estudo | Retrospectivo condicionado, enquanto faltam logs; operacional somente com evidência adicional | Aceitar essa limitação de escopo ou buscar dados de disponibilidade. |
| Semântica do CSV | Usar convenção de fim da hora somente se exportação preservada | Requisição/código de coleta e confirmação do produtor; sem isso, manter hipótese explícita e não construir alvo operacional. |
| Emissão/horizonte | Hora cheia, próxima hora completa | Confirmar objetivo e convenção de bordas. |
| Target principal | Qualquer chuva líquida positiva; rain como definição semântica | Aprovar A ou escolher B/C; para B, fornecer fundamento e τ. |
| Meteorologia permitida | Mesmo conjunto causal para A/B, com versões disponíveis ou hipótese declarada | Disponibilidade por variável, defasagens e eventual exclusão de variáveis não operacionais. |
| Pareamento GOES | Último fim de captura entre produtos elegíveis; associação derivada rastreável | Logs ou L assumido, Amax e regra de recuo quando produto inválido. |
| Região espacial | Região geográfica fixa na grade nativa | Contorno/raio, geolocalização, pesos e cobertura mínima válida. |
| Ausências e matrizes inválidas | Estados explícitos; coorte comum para comparação inicial | Política final de exclusão analítica ou imputação futura, sem alterar originais. |
| Avaliação | Treino 2020–2024, validação 2025, teste jan–set/2026 | Aprovar datas, reajuste final, purga/embargo após W/Amax e exposição da EDA. |
| Piloto | Janeiro/2023 + diagnósticos já conhecidos | Autorizar execução apenas após decisões essenciais; nenhum modelo no piloto técnico. |

L, Amax, W, τ (se aplicável), contorno espacial e limiar de pixels válidos **não receberam valores arbitrários**. As propostas não substituem confirmação. Dependências podem ser resolvidas em sequência: primeiro proveniência/escopo, depois alvo e elegibilidade, depois piloto técnico e só posteriormente treinamento.

## 12. Recomendação técnica final

**Fato observado:** o conjunto suporta análises históricas coerentes, mas contém links não causais para emissão na hora cheia, duas grades, falhas de imagem e ausência de prova de disponibilidade. **Interpretação:** uma comparação A/B pode ser útil para pesquisa se suas hipóteses e coorte forem comuns e transparentes; ainda não demonstraria previsão operacional de chuva observada por estação. O alvo é dado histórico da fonte declarada, não medição independente de estação física.

**Hipótese central a confirmar:** a exportação mantém a semântica temporal documentada e as entradas escolhidas representam informação permitida no instante considerado, real ou assumido. **Decisão proposta:** aprovar condicionalmente o estudo retrospectivo de ocorrência com alvo A, emissão na hora cheia, pareamento GOES apenas para trás sob regra explícita, região fixa validada e comparação cronológica em coorte comum. Para alegação operacional, exigir evidência de disponibilidade e versão também da meteorologia.

Antes de implementação, obter confirmação das decisões da seção 11. A primeira atividade autorizável seria o piloto de alinhamento e qualidade, não processamento em massa ou treinamento.

**Verificação deste estágio:** revisão documental e de referências, sem executar os scripts de auditoria/EDA que regeneram relatórios. Não foram criados testes de código nem repetidos os oito testes anteriores, pois nenhum módulo foi alterado. O resultado histórico dos testes permanece em [reports/eda/tests.txt](../eda/tests.txt); não é apresentado como nova execução. Este é o único arquivo entregue neste estágio.
