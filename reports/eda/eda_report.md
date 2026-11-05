# EDA meteorológica e GOES — estágio 2

## 1. Objetivo, metodologia e limites

Compreender a base antes de definir o problema de previsão de chuva na próxima hora. **Nenhum alvo, divisão de treino/teste, imputação, normalização, remoção de outliers ou modelo foi criado.** O CSV completo foi analisado descritivamente. Colunas auxiliares em memória servem apenas aos agrupamentos e não constituem um conjunto de dados de treino.

O projeto existente foi ampliado; `audit.py`, seus testes e os relatórios do estágio 1 foram preservados. As fontes permanecem externas e somente para leitura. A entrada real é `dataset_goes.zip`, não `dataset.zip`. O ZIP foi consultado por seu índice e por leituras seletivas; nenhuma extração foi realizada. Uma matriz por vez, `allow_pickle=False`, máximo de 32 MiB por NPZ e 128 MiB de expansão interna.

**Tempo:** `time` é ISO-8601 sem offset, localizado explicitamente em **America/Sao_Paulo**, com erro em caso de horário ambíguo ou inexistente, e convertido a UTC para comparação. O período observado tem offset −03:00. Metadados GOES com offset explícito são respeitados. Estatísticas do CSV usam desvio padrão amostral (`ddof=1`); pixels usam populacional (`ddof=0`). Os limiares das checagens estão no manifesto e não são regras de limpeza.

Amostra determinística: ordenar o índice por captura nominal/nome e sortear, com `numpy.default_rng(42)`, duas imagens únicas por estrato **mês UTC × satélite do nome**, restritas a arquivos referenciados. Acrescentar três imagens antes e três a partir de cada troca de satélite; três menores e três maiores NPZ; oito links reutilizados com maior intervalo (desempate lexicográfico); três menores e três maiores desvios nominais; primeiro e último arquivos não referenciados; amostra do estágio 1. Deduplicar nomes antes da leitura. Resultou em **192 imagens únicas**, com **203 pares CSV–imagem** porque todos os registros que usam cada imagem selecionada foram comparados. Há imagens fora do CSV, sem pareamento. O manifesto lista todos os nomes e motivos. A amostra mistura cobertura regular e procura dirigida de anomalias: **suas proporções não estimam prevalência no acervo**.

Foram lidos 242.5 MiB de membros NPZ selecionados, além da releitura da imagem inicial pela auditoria; não 79 GB de pixels. Não foi medido o pico de RAM. Foram usadas dependências existentes e matplotlib instalado em pasta de apoio, sem instalação global.

## 2. Qualidade do CSV e confirmação do estágio 1

**Fatos:** 59160 linhas × 22 colunas; 2020-01-01 00:00:00 a 2026-09-30 23:00:00. Série crescente, intervalo de uma hora, zero timestamps inválidos/duplicados e zero lacunas. Zero registros duplicados. Somente `image_link` tem ausências: 179. Não há valores infinitos nas colunas numéricas. 58981 links preenchidos e 58912 distintos; todos existem no ZIP. Tipos e ausência por coluna constam de `audit_recheck.json` e `numeric_summary.csv`.

Divergências nas métricas comparadas com o JSON anterior: `{}`. A execução atual confirmou os números. As versões de Python/pandas/numpy registradas no relatório anterior diferem do ambiente atual; o manifesto preserva as versões efetivamente usadas agora.

**Correção documental:** o README do projeto e a resposta anterior mencionavam offset −03:00 dentro de `timestamp_utc`. O JSON/relatório histórico disponível registra `2020-01-01T03:00:21+00:00`; a releitura direta confirmou **`2020-01-01T03:00:21+00:00`**. As 192 amostras usam offset UTC zero. A alegação anterior de offset local não é corroborada pelos arquivos atuais e foi corrigida no README do projeto. A diferença de 21 segundos da primeira imagem permanece correta. Não foram alterados metadados nem relatórios históricos.

## 3. Distribuições e variáveis especiais

Tabela resumida; o CSV anexo inclui também quartis, p1/p5/p95/p99, número de únicos, ausentes e infinitos para **todas as 20 variáveis numéricas**. Médias de `weather_code` não têm interpretação contínua e a média aritmética de direção não deve ser usada como direção predominante, embora constem na descrição mecânica dos dtypes.

| variable | unit_readme | mean | median | std | min | 25% | 75% | max | unique | missing |
|---|---|---|---|---|---|---|---|---|---|---|
| temperature_2m | °C | 21.68 | 21.6 | 5.142 | 1.8 | 18.4 | 25.1 | 38.5 | 354 | 0 |
| relative_humidity_2m | % | 71.46 | 74 | 18.9 | 12 | 58 | 87 | 100 | 89 | 0 |
| dew_point_2m | °C | 15.6 | 16.1 | 4.435 | -5 | 12.6 | 19.3 | 24.9 | 281 | 0 |
| apparent_temperature | °C | 22.7 | 23.2 | 6.334 | -1.9 | 18.5 | 27 | 40.9 | 417 | 0 |
| weather_code | código | 10.25 | 2 | 19.93 | 0 | 0 | 3 | 65 | 10 | 0 |
| cloud_cover | % | 49.73 | 44 | 42.06 | 0 | 4 | 99 | 100 | 101 | 0 |
| pressure_msl | hPa | 1015 | 1015 | 4.277 | 999.7 | 1012 | 1018 | 1031 | 285 | 0 |
| surface_pressure | hPa | 947.4 | 947.3 | 3.445 | 933.8 | 945 | 949.7 | 960 | 247 | 0 |
| wind_speed_10m | m/s | 2.392 | 2.28 | 1.036 | 0 | 1.68 | 3 | 8.98 | 685 | 0 |
| wind_direction_10m | graus | 142.1 | 117 | 87.49 | 1 | 81 | 193 | 360 | 360 | 0 |
| wind_gusts_10m | m/s | 5.408 | 5.1 | 2.409 | 0.3 | 3.5 | 7 | 21.3 | 180 | 0 |
| shortwave_radiation | W/m² | 213.9 | 8 | 292 | 0 | 0 | 409 | 1115 | 1097 | 0 |
| direct_radiation | W/m² | 152.6 | 0 | 238.7 | 0 | 0 | 248 | 1021 | 1007 | 0 |
| diffuse_radiation | W/m² | 61.26 | 5 | 87.06 | 0 | 0 | 97 | 501 | 472 | 0 |
| direct_normal_irradiance | W/m² | 243.8 | 0 | 323.8 | 0 | 0 | 531.2 | 1028 | 9139 | 0 |
| is_day | 0/1 | 0.5037 | 1 | 0.5 | 0 | 0 | 1 | 1 | 2 | 0 |
| sunshine_duration | s | 1468 | 0 | 1727 | 0 | 0 | 3600 | 3600 | 4529 | 0 |
| soil_moisture_0_to_7cm | m³/m³ | 0.3484 | 0.346 | 0.09882 | 0.027 | 0.284 | 0.432 | 0.563 | 434 | 0 |
| rain | mm | 0.1625 | 0 | 0.7591 | 0 | 0 | 0 | 18 | 140 | 0 |
| precipitation | mm | 0.1625 | 0 | 0.7591 | 0 | 0 | 0 | 18 | 140 | 0 |

**Fatos e interpretação:** temperatura e pressão têm distribuição central com caudas; umidade e nebulosidade são limitadas, com concentrações próximas dos extremos para nebulosidade. Radiação e insolação têm massa em zero e componente diurna; chuva é fortemente assimétrica. Histogramas usam 40 bins; chuva, 50 bins com eixo de contagem logarítmico e painel separado de valores positivos. Boxplots usam 1,5 IQR, sem exclusão de valores.

`is_day`: 29797 registros diurnos (50.37%) e 29363 noturnos. Somente 0/1. `weather_code` é categórico: códigos 0 e 3 são os mais frequentes. Não foi codificado para treinamento.

Direção do vento é circular: os 16 registros com velocidade zero foram excluídos **somente** do resumo circular/gráfico. Média circular dos demais ≈105,06°, comprimento resultante ≈0,392 (dispersão relevante); distribuição em 16 setores. Isso não atribui significado meteorológico à direção em calmaria e não transforma a base. O CSV original permanece intacto.

Correlação de Pearson calculada apenas para as 17 variáveis quantitativas não circulares; `weather_code`, `wind_direction_10m` e `is_day` foram omitidas da matriz, analisadas separadamente. `rain` e `precipitation` têm correlação 1 porque são iguais. As associações são contemporâneas, descritivas e influenciadas por sazonalidade/autocorrelação; não medem ganho preditivo, causalidade nem justificam seleção de atributos.

## 4. Evolução temporal e sazonalidade

| year | rows | temperature_mean | precipitation_mm | positive_fraction | images | coverage |
|---|---|---|---|---|---|---|
| 2020 | 8784 | 21.66 | 1093 | 0.1471 | 8760 | 0.9973 |
| 2021 | 8760 | 21.38 | 1138 | 0.1572 | 8749 | 0.9987 |
| 2022 | 8760 | 20.75 | 1689 | 0.1881 | 8742 | 0.9979 |
| 2023 | 8760 | 21.62 | 1661 | 0.1879 | 8749 | 0.9987 |
| 2024 | 8784 | 23.05 | 1343 | 0.1638 | 8758 | 0.997 |
| 2025 | 8760 | 21.93 | 1355 | 0.1533 | 8759 | 0.9999 |
| 2026 | 6552 | 21.25 | 1336 | 0.2099 | 6464 | 0.9866 |

**Fatos:** todos os meses entre janeiro/2020 e setembro/2026 estão representados. O número de horas acompanha a duração do mês. 2026 termina em setembro; totais anuais não são diretamente comparáveis com anos completos. `annual_jan_sep.csv` compara a mesma janela jan–set: por exemplo, a média de temperatura de 2024 é 22,71 °C e a de 2022, 20,39 °C nessa janela. Isso é variação observada, não evidência isolada de mudança climática ou de erro na fonte.

| calendar_month | months_observed | temperature_mean | precipitation_month_mean_mm | positive_fraction |
|---|---|---|---|---|
| 1 | 7 | 23.98 | 189.2 | 0.3041 |
| 2 | 7 | 24.12 | 160.5 | 0.2905 |
| 3 | 7 | 24.28 | 136 | 0.2206 |
| 4 | 7 | 22 | 94.9 | 0.1274 |
| 5 | 7 | 19.02 | 72.21 | 0.1077 |
| 6 | 7 | 17.66 | 108 | 0.1347 |
| 7 | 7 | 17.77 | 39.51 | 0.05261 |
| 8 | 7 | 19.56 | 69.87 | 0.09562 |
| 9 | 7 | 22.43 | 101 | 0.1123 |
| 10 | 6 | 22.58 | 166.8 | 0.1942 |
| 11 | 6 | 23.39 | 132.5 | 0.1829 |
| 12 | 6 | 24.29 | 170.2 | 0.2531 |

O mês de janeiro apresenta média de 189,2 mm por mês observado e 30,4% de horas positivas, contra 39,5 mm e 5,3% em julho. Temperaturas médias por mês do calendário variam aproximadamente de 17,66 °C (junho) a 24,29 °C (dezembro). **Limitação:** há sete ocorrências para jan–set e seis para out–dez; não se trata de uma normal climatológica. Hipóteses para mudanças entre anos incluem variabilidade meteorológica e composição da fonte; a base não permite separar essas causas. Não foram aplicados testes de tendência nem inferidas rupturas causais.

Acumulados mensais agrupam o timestamp da linha, sem deslocá-lo. Se esse timestamp representa o fim do intervalo anterior, a primeira linha de um mês inclui a última hora do mês anterior. É uma convenção descritiva explícita, a rever antes do alvo.

## 5. Chuva, precipitação, intensidade e códigos

| variable | zero | positive | negative | zero_fraction | positive_fraction | min | max | unique | positive_mean | q0.5 | q0.9 | q0.95 | q0.99 | q0.999 | positive_q0.25 | positive_q0.5 | positive_q0.75 | positive_q0.95 | positive_q0.99 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rain | 49040 | 10120 | 0 | 0.8289 | 0.1711 | 0 | 18 | 140 | 0.9501 | 0 | 0.2 | 0.8 | 3.6 | 9.8 | 0.1 | 0.3 | 1 | 4 | 8 |
| precipitation | 49040 | 10120 | 0 | 0.8289 | 0.1711 | 0 | 18 | 140 | 0.9501 | 0 | 0.2 | 0.8 | 3.6 | 9.8 | 0.1 | 0.3 | 1 | 4 | 8 |

**Fatos:** ambas são exatamente iguais nas 59160 linhas. Há 49.040 zeros (82,89%) e 10.120 valores positivos (17,11%), com máximo 18 mm, 140 valores distintos e mediana positiva de 0,3 mm. A igualdade neste arquivo não torna suas definições equivalentes em outras bases. O README descreve `rain` como chuva e `precipitation` como precipitação total, ambas em mm.

Blocos exploratórios de horas consecutivas com valor >0 (não são o alvo e não são uma definição definitiva de tempestade): **2607 blocos**, duração mediana 2 h, máxima 79 h, maior soma 113 mm. Uma hora seca ou lacuna quebra o bloco. Os arquivos registram limites e indicam eventual censura nas bordas. Não há inferência de independência entre esses eventos.

| weather_code | rows | rain_min | rain_max | rain_mean | precipitation_mean | positive_fraction | fraction |
|---|---|---|---|---|---|---|---|
| 0 | 22307 | 0 | 0 | 0 | 0 | 0 | 0.3771 |
| 1 | 7230 | 0 | 0 | 0 | 0 | 0 | 0.1222 |
| 2 | 4352 | 0 | 0 | 0 | 0 | 0 | 0.07356 |
| 3 | 15151 | 0 | 0 | 0 | 0 | 0 | 0.2561 |
| 51 | 5902 | 0.1 | 0.4 | 0.1775 | 0.1775 | 1 | 0.09976 |
| 53 | 1527 | 0.5 | 0.9 | 0.6728 | 0.6728 | 1 | 0.02581 |
| 55 | 554 | 1 | 1.2 | 1.093 | 1.093 | 1 | 0.009364 |
| 61 | 1077 | 1.3 | 2.4 | 1.759 | 1.759 | 1 | 0.0182 |
| 63 | 936 | 2.5 | 7.5 | 4.024 | 4.024 | 1 | 0.01582 |
| 65 | 124 | 7.6 | 18 | 10.27 | 10.27 | 1 | 0.002096 |

Os códigos 0/1/2/3 aparecem somente com precipitação zero; 51/53/55/61/63/65, somente com valor positivo. Os intervalos de intensidade por código estão na tabela. Isso mostra uma associação descritiva muito forte entre campos do mesmo horário; não é evidência de capacidade de antecipar a próxima hora.

**Documentação complementar:** a [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), consultada em 13/10/2026, define precipitação como soma da hora anterior e chuva como componente líquida. Radiação é média da hora anterior; `is_day` é indicador do instante. O código meteorológico é derivado de variáveis incluindo precipitação e nebulosidade. A unidade do vento é configurável; os gráficos seguem m/s conforme o README local, mas a requisição original não está disponível. Estas definições ajudam a interpretar os achados, sem certificar a configuração histórica deste CSV.

## 6. Outliers e consistência física

Classes: **A** evidência suficiente de invalidade; **B** suspeita que exige investigação; **C** extremo potencialmente válido; **D** nenhum problema identificado na checagem, sem certificação geral.

| check | count | category | reason |
|---|---|---|---|
| relative_humidity_2m_outside_0_100 | 0 | D | Fora do domínio percentual declarado. |
| cloud_cover_outside_0_100 | 0 | D | Fora do domínio percentual declarado. |
| rain_negative | 0 | D | Magnitude negativa incompatível com a variável declarada. |
| precipitation_negative | 0 | D | Magnitude negativa incompatível com a variável declarada. |
| wind_speed_10m_negative | 0 | D | Magnitude negativa incompatível com a variável declarada. |
| wind_gusts_10m_negative | 0 | D | Magnitude negativa incompatível com a variável declarada. |
| shortwave_radiation_negative | 0 | D | Magnitude negativa incompatível com a variável declarada. |
| direct_radiation_negative | 0 | D | Magnitude negativa incompatível com a variável declarada. |
| diffuse_radiation_negative | 0 | D | Magnitude negativa incompatível com a variável declarada. |
| direct_normal_irradiance_negative | 0 | D | Magnitude negativa incompatível com a variável declarada. |
| sunshine_outside_hour | 0 | D | Segundos de insolação fora de uma hora. |
| soil_moisture_outside_0_1 | 0 | D | Fração volumétrica fora de [0,1]. |
| direction_outside_circle | 0 | D | Direção fora do círculo em graus. |
| is_day_not_binary | 0 | D | Indicador fora de 0/1. |
| dew_above_air | 0 | D | Ponto de orvalho acima da temperatura; tolerância exploratória 0,2 °C para arredondamento, sem correção. |
| rain_above_total | 0 | D | Chuva maior que precipitação total; verificar definição/fonte. |
| radiation_components | 0 | D | Diferença global - direta - difusa >2 W/m²; tolerância exploratória para arredondamento. |
| radiation_at_night | 1939 | B | Comparar média da hora anterior com is_day instantâneo pode explicar valores no crepúsculo; não é prova de erro. |
| gust_below_wind | 131 | B | Janelas/modelos de rajada e vento podem diferir; confirmar configuração da fonte. |
| pressure_order | 0 | D | Ordem inesperada para local elevado; altitude/configuração não verificadas. |
| temperature_2m_iqr | 526 | C | Fora de 1,5 IQR (8.35, 35.15); regra descritiva, não física. Com IQR zero, qualquer chuva positiva é sinalizada. |
| apparent_temperature_iqr | 371 | C | Fora de 1,5 IQR (5.75, 39.75); regra descritiva, não física. Com IQR zero, qualquer chuva positiva é sinalizada. |
| wind_speed_10m_iqr | 1020 | C | Fora de 1,5 IQR (-0.3, 4.98); regra descritiva, não física. Com IQR zero, qualquer chuva positiva é sinalizada. |
| wind_gusts_10m_iqr | 494 | C | Fora de 1,5 IQR (-1.75, 12.25); regra descritiva, não física. Com IQR zero, qualquer chuva positiva é sinalizada. |
| rain_iqr | 10120 | C | Fora de 1,5 IQR (0, 0); regra descritiva, não física. Com IQR zero, qualquer chuva positiva é sinalizada. |
| precipitation_iqr | 10120 | C | Fora de 1,5 IQR (0, 0); regra descritiva, não física. Com IQR zero, qualquer chuva positiva é sinalizada. |

Não houve violação dos domínios físicos básicos testados no CSV (classe A). Há **1.939** horários com `is_day=0` e radiação positiva, todos às 18/19/20 h locais, máximo 69 W/m². **Hipótese:** média da hora anterior pode incluir luminosidade mesmo quando o indicador instantâneo já é noturno; requer confirmação da semântica temporal. Há **131** casos de rajada menor que vento, diferença máxima 2.18 m/s; janelas, parâmetros e origem devem ser investigados. Exemplos com linha e valores estão em `suspect_examples.csv`.

Temperatura de 1,8 a 38,5 °C, rajada até 21,3 m/s e chuva até 18 mm são extremos que, isoladamente, não demonstram erro. Na chuva, Q1=Q3=0, de modo que o critério IQR marca **todos** os valores positivos. Removê-los destruiria o fenômeno a estudar. Nenhuma correção foi aplicada.

## 7. Investigação amostral GOES

192 NPZ examinados sequencialmente, incluindo nomes de origem, chaves, timestamp, grade, satélite, escala, offset, unidade, dtype, máscara e estatísticas. Os detalhes completos estão em `goes_sample_details.json`; os resultados planos, no CSV homônimo de resumo. Metadados ausentes e erros são explícitos, sem inventar estatísticas.

Foram encontradas **4 matrizes inteiramente preenchidas com fill_value**, sem pixels válidos:

| captura UTC | satélite | pixels inválidos | seleção |
|---|---|---|---|
| 2020-06-04 12:40:17+00:00 | GOES-16 | 1077045 | 3_menores_desvios_nome;8_reusos_maior_intervalo |
| 2021-09-04 11:00:21+00:00 | GOES-16 | 1077045 | 3_menores_npz |
| 2026-06-22 23:00:22+00:00 | GOES-19 | 1073394 | 3_menores_npz |
| 2026-08-31 23:00:22+00:00 | GOES-19 | 1073394 | 3_menores_npz |

Essas matrizes são **A para uso numérico naquela observação**: não fornecem informação de brilho válida. Isso não prova corrupção do arquivo, e os originais não foram descartados. Três menores arquivos foram procurados deliberadamente; portanto, não extrapolar a taxa 4/192 para o conjunto. Os demais 188 NPZ amostrados têm zero pixels inválidos pela máscara disponível. Sem flags radiométricas adicionais, pixel diferente do fill não significa qualidade científica garantida.

Todos os metadados esperados foram encontrados nesta amostra. As comparações de satélite/nome de origem/basename da chave com o caminho tiveram estes números de discordâncias: `{'filename_satellite_matches': 0, 'source_filename_matches': 0, 'source_key_basename_matches': 0}`. O início informado pelo metadado fica entre -0.9 e 0 segundo em relação ao nome NOAA, compatível com perda da fração de segundo no metadado; não corrigido.

## 8. Consistência espacial, grades e satélites

| satellite | grid_signature | formato | dtype | units | scale_factor | add_offset | fill_value | images | invalid_min | invalid_max |
|---|---|---|---|---|---|---|---|---|---|---|
| GOES-16 | 44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876 | [885, 1217] | int16 | K | 0.06145 | 89.62 | -1 | 147 | 0 | 1077045 |
| GOES-19 | 44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876 | [885, 1217] | int16 | K | 0.06145 | 89.62 | -1 | 31 | 0 | 0 |
| GOES-19 | 4d1d681125ac7ad72c9085784ca9d701e44201dd836f5e105230f2542880a4a8 | [882, 1217] | int16 | K | 0.06145 | 89.62 | -1 | 14 | 0 | 1073394 |

Na amostra, dtype int16, Kelvin, scale_factor ≈0,06145332, add_offset ≈89,62000 e fill_value −1 são compartilhados. Há **duas grades**: 885×1217 e 882×1217. O README original já descreve ambas e diferentes extensões de projeção. GOES-19 aparece nas duas grades; trocar o satélite não determina sozinho a grade.

| satellite | grid_signature | min | max |
|---|---|---|---|
| GOES-16 | 44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876 | 2020-01-01T00:00:21+00:00 | 2025-04-07T15:00:20+00:00 |
| GOES-19 | 44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876 | 2025-04-07T16:00:20+00:00 | 2026-05-23T05:10:21+00:00 |
| GOES-19 | 4d1d681125ac7ad72c9085784ca9d701e44201dd836f5e105230f2542880a4a8 | 2026-05-27T22:00:20+00:00 | 2026-10-06T00:00:20+00:00 |

Os limites acima são **apenas primeiras/últimas ocorrências amostradas**, não datas exatas de mudança de grade. A diferença aparece entre as amostras de 23 e 27/05/2026; não foi feito inventário de metadados de todos os NPZ. O índice nominal identifica a passagem de G16 para G19 em **07/04/2025 às 16:00:20,8 UTC**, e as seis imagens próximas à fronteira foram examinadas. Isto descreve a troca neste acervo, não certifica toda a história operacional dos satélites.

As estatísticas são computáveis na mesma unidade, mas **comparabilidade física plena não está estabelecida**: domínio espacial, grade, calibração e máscara podem mudar. A média da imagem inteira cobre área extensa e pode diluir informação de Londrina.

**Alternativas para discussão:** (1) manter estatísticas de domínio inteiro como modelo de referência, com diagnóstico separado por grade/satélite; (2) definir uma região geográfica fixa em torno de Londrina e selecionar pixels pela geolocalização própria de cada grade; (3) reamostrar ambas para grade comum, com método e custos explícitos. Não usar os mesmos índices de linha/coluna como se fossem a mesma região. Nenhuma opção foi implementada.

## 9. Consistência temporal e disponibilidade operacional

Dos 203 pares amostrados, **195** têm captura posterior à referência, **8** anterior e **0** igual. Mediana 20 s; mínimo -5380 s (−89 min 40 s) e máximo 4820 s (+80 min 20 s). O desvio inicial de 21 s está confirmado. As linhas individuais, inclusive reusos, estão em `goes_temporal_pairings.csv`. Selecionamos intencionalmente extremos; esses percentuais não representam todo o conjunto de dados.

Também foram lidos os timestamps nominais dos nomes de todos os arquivos, sem carregar pixels, apenas para inventário e seleção de casos (`filename_delta_summary.csv`). Não equivalem à validação de todos os metadados. O nome NOAA inclui fim da captura e criação do produto; suas diferenças estão na tabela amostral e **não são horários comprovados de chegada ao sistema do usuário**.

**Regra recomendada para discussão:** emitir em um instante t bem definido e aceitar somente imagens cujo produto completo já estivesse recebido em t. Exigir `fim_da_captura + latência documentada ≤ t`, além de um limite de idade da imagem; preferir horário real de disponibilidade, quando existir. A latência e a idade máxima ainda não foram escolhidas. Sem logs, testar futuramente uma hipótese conservadora de latência, claramente declarada, e selecionar apenas imagens anteriores elegíveis. Uma captura que apenas começa antes de t não basta. Não deslocar os timestamps nem trocar os links automaticamente nesta etapa.

## 10. Cobertura, ausências e reuso

Cobertura global por link: 99.697%. Há **28 blocos de ausência**, maior de **39 horas**, de 24/05/2026 21h a 26/05/2026 11h locais. Meses de menor cobertura:

| month | rows | images | coverage |
|---|---|---|---|
| 2026-05 | 744 | 675 | 0.9073 |
| 2020-06 | 720 | 702 | 0.975 |
| 2026-07 | 744 | 726 | 0.9758 |
| 2024-09 | 720 | 709 | 0.9847 |
| 2022-09 | 720 | 712 | 0.9889 |

Cobertura por ano e satélite inferido do nome (contagem de links, não de matrizes úteis):

| year | G16 | G19 | sem_imagem |
|---|---|---|---|
| 2020 | 8760 | 0 | 24 |
| 2021 | 8749 | 0 | 11 |
| 2022 | 8742 | 0 | 18 |
| 2023 | 8749 | 0 | 11 |
| 2024 | 8758 | 0 | 26 |
| 2025 | 2316 | 6443 | 1 |
| 2026 | 0 | 6464 | 88 |

Há 67 imagens reutilizadas: 65 são usadas em duas linhas adjacentes e duas em três linhas, abrangendo duas horas. São 69 referências adicionais. Nenhum reuso ultrapassa dois intervalos horários nesta auditoria. `image_reuse.csv` registra cada caso. Imagens compartilhadas podem contaminar fronteiras futuras de treino/validação/teste e precisam de regra por grupo/tempo, sem divisão aleatória.

Dos 121 NPZ não referenciados, **3** têm captura nominal anterior ao primeiro horário do CSV, **118** posterior ao último e **0** dentro do intervalo. Portanto, todos estão fora do intervalo de referências do CSV. **Interpretação:** a diferença de cobertura e os fusos explicam a existência de arquivos extras nas bordas; não é evidência de erro. Todos foram preservados.

Cobertura por link superestima disponibilidade útil quando a matriz é inválida ou chega tarde. Selecionar apenas registros com imagem pode alterar a distribuição temporal; manter ausências explícitas até decidir o protocolo e reportar cobertura por período. Não excluir automaticamente períodos de falha.

## 11. Riscos de vazamento e protocolo a definir

- Imagens capturadas ou disponibilizadas após a emissão não são atributos elegíveis, mesmo que o link já esteja no CSV histórico.
- Reanálises e variáveis acumuladas podem só existir após o instante previsto; confirmar disponibilidade real e versões da fonte. O conjunto de dados não contém esse histórico de disponibilização.
- Nunca usar `rain`/`precipitation` do intervalo futuro como atributo. A forte ligação de weather_code com chuva do mesmo registro exige o mesmo cuidado temporal.
- Ajustar imputadores, escalas e demais transformações somente no treino; nenhuma estatística global desta EDA deve virar parâmetro de transformação do treino.
- Não selecionar atributos pelos resultados do teste. Não embaralhar a avaliação temporal ou dividir aleatoriamente.
- Impedir que imagens compartilhadas e janelas sobrepostas atravessem partições; estabelecer margem na fronteira compatível com horizonte, janelas e reuso.

O protocolo deverá registrar emissão t, horizonte de uma hora, informações comprovadamente disponíveis em t, definição do alvo e fronteiras temporais. Nenhuma partição foi feita.

## 12. Decisões pendentes e opções de alvo

As opções abaixo são **propostas, não colunas criadas**. Para previsão emitida em t, definir primeiro o intervalo (t,t+1h] e confirmar se o registro em t+1h representa essa acumulação:

| Opção | Interpretação | Implicação |
|---|---|---|
| rain > 0 no intervalo futuro | Qualquer chuva líquida registrada | Sensível à resolução/traços; prevalência depende da fonte. |
| precipitation > 0 no intervalo futuro | Qualquer precipitação total | Igual ao primeiro nesta base, mas conceitualmente inclui outros componentes. |
| rain ou precipitation ≥ limiar τ | Evento com intensidade mínima relevante | Exige escolher variável, valor, unidade e convenção ≥/>, justificados pela aplicação. Não escolher pelo teste. |

Não foi escolhido τ nem criada `rain_next_hour`. Zero observado, ausência de observação e imagem sem pixels válidos são estados distintos. Decidir também latência e idade máxima da imagem, janela espacial, critérios de qualidade de pixels, tratamento futuro de ausências e regra para imagens reutilizadas nas fronteiras. A regra espacial deve lidar com as duas grades antes de comparar atributos em massa.

## 13. Recomendações e próximos passos

1. Validar a semântica temporal e a disponibilidade operacional das fontes com a requisição original e logs, se existirem.
2. Escolher formalmente alvo, instante de emissão, horizonte e regra de elegibilidade da imagem. Documentar as decisões antes de montar treino.
3. Decidir região espacial e tratamento de grades, matrizes totalmente inválidas e ausências. Investigar os 131 casos vento/rajada e as convenções de radiação.
4. Somente após autorização, planejar tratamento e construção do conjunto de dados; depois comparação temporal entre modelo de referência meteorológico e alternativa com GOES.

**Limitações:** uma localidade, período relativamente curto, origem em reanálise conforme README, unidades do vento não verificadas pela requisição, amostra GOES direcionada, ausência de flags radiométricas e de logs de disponibilidade. Não se sabe ainda se as estatísticas de imagem acrescentam informação preditiva. A EDA não responde essa pergunta.

## Reprodutibilidade, preservação e testes

`src/data/eda.py` reproduz tabelas, amostragem, figuras e este relatório; `eda_report.py` permite reemitir o relatório sem ler novamente os NPZ. A seed e todos os parâmetros estão em `run_manifest.json`. Nomes/detalhes individuais da amostra foram salvos. As figuras são estáticas, sem imagens decorativas ou conversões de matrizes GOES em PNG para treinamento.

Fontes e arquivos protegidos inalterados durante a execução: **True**. SHA-256 para arquivos pequenos; somente tamanho/mtime para o ZIP. Isso não certifica o hash integral de 79 GB. A leitura verifica os membros acessados, não o CRC de todo o acervo.

Ambiente efetivo:

```json
{
  "python": "3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]",
  "platform": "Windows-11-10.0.26200-SP0",
  "pandas": "3.0.1",
  "numpy": "2.5.4",
  "matplotlib": "3.11.2"
}
```

Resultado dos testes registrado em `tests.txt`:

```text
test_all_invalid_fails_clearly (test_audit.ImageTests.test_all_invalid_fails_clearly) ... ok
test_explicit_offset (test_audit.ImageTests.test_explicit_offset) ... ok
test_mask_and_kelvin (test_audit.ImageTests.test_mask_and_kelvin) ... ok
test_missing_metadata_does_not_invent_reconstruction (test_audit.ImageTests.test_missing_metadata_does_not_invent_reconstruction) ... ok
test_other_unit_is_not_celsius_converted (test_audit.ImageTests.test_other_unit_is_not_celsius_converted) ... ok
test_noaa_fractional_second_and_year_boundary (test_eda.TemporalTests.test_noaa_fractional_second_and_year_boundary) ... ok
test_spells_break_on_gap_and_dry_hour (test_eda.TemporalTests.test_spells_break_on_gap_and_dry_hour) ... ok
test_unknown_name_is_not_invented (test_eda.TemporalTests.test_unknown_name_is_not_invented) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.013s

OK
```

## Figuras e arquivos

Tabelas estão nesta pasta: resumo numérico/ano/mês, sazonalidade/ciclo horário, frequências, blocos positivos, checagens, reuso/ausências, inventário resumido, amostra GOES e pareamentos. Os nomes são autoexplicativos; manifesto e JSONs guardam evidências e parâmetros.

- [correlation_exploratory.png](../figures/correlation_exploratory.png)
- [goes_temporal_offsets.png](../figures/goes_temporal_offsets.png)
- [histograms_1.png](../figures/histograms_1.png)
- [histograms_2.png](../figures/histograms_2.png)
- [histograms_3.png](../figures/histograms_3.png)
- [monthly_evolution.png](../figures/monthly_evolution.png)
- [precipitation_distribution.png](../figures/precipitation_distribution.png)
- [rain_distribution.png](../figures/rain_distribution.png)
- [seasonality.png](../figures/seasonality.png)
- [special_variables.png](../figures/special_variables.png)
- [wind_direction.png](../figures/wind_direction.png)
- [yearly_boxplots.png](../figures/yearly_boxplots.png)

A EDA termina aqui. Tratamento, alvo, extração em massa, divisão temporal e treinamento aguardam confirmação.
