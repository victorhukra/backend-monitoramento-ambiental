"""Gera relatório interpretativo a partir das tabelas e do manifesto da EDA."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]


def table(df):
    def cell(value):
        if isinstance(value,float): return f"{value:.4g}"
        return str(value).replace("|","/").replace("\n"," ")
    return "\n".join(["| "+" | ".join(map(str,df.columns))+" |","|"+"---|"*len(df.columns)]+[
        "| "+" | ".join(cell(v) for v in row)+" |" for row in df.itertuples(index=False,name=None)])


def build(df,output):
    read=lambda name:pd.read_csv(output/name)
    run=json.loads((output/"run_manifest.json").read_text(encoding="utf-8"))
    audit=json.loads((output/"audit_recheck.json").read_text(encoding="utf-8"))
    details=json.loads((output/"goes_sample_details.json").read_text(encoding="utf-8"))
    summary=read("numeric_summary.csv"); monthly=read("monthly.csv"); annual=read("annual.csv")
    season=read("seasonality.csv"); rains=read("rain_summary.csv"); codes=read("weather_code.csv")
    checks=read("consistency_checks.csv"); pairs=read("goes_temporal_pairings.csv"); grids=read("goes_grids.csv")
    sample=read("goes_sample_summary.csv"); reuse=read("image_reuse.csv"); gaps=read("missing_image_spells.csv")
    events=read("rain_positive_spells.csv"); unref=read("unreferenced_npz.csv")
    time=pd.to_datetime(df.time,format="ISO8601").dt.tz_localize("America/Sao_Paulo")
    ut=pd.to_datetime(unref.capture_filename,utc=True,format="ISO8601")
    unref_counts={"before_csv":int((ut<time.min()).sum()),"after_csv":int((ut>time.max()).sum()),
                  "inside_csv":int(((ut>=time.min())&(ut<=time.max())).sum())}
    night=(df.is_day==0)&(df.shortwave_radiation>0)
    night_hours=time[night].dt.hour.value_counts().sort_index().rename_axis("hour_local").rename("records")
    night_hours.to_csv(output/"night_radiation_hours.csv")
    diagnostics={"unreferenced_position":unref_counts,"night_radiation_max_W_m2":float(df.loc[night,"shortwave_radiation"].max()),
        "max_wind_minus_gust_m_s":float((df.wind_speed_10m-df.wind_gusts_10m).max()),
        "metadata_offset_values":sorted({x.get("timestamp_offset_seconds") for x in details if x.get("timestamp_offset_seconds") is not None}),
        "metadata_vs_filename_min_seconds":float(sample.metadata_minus_filename_seconds.min()),
        "metadata_vs_filename_max_seconds":float(sample.metadata_minus_filename_seconds.max()),
        "metadata_mismatches":{k:sum(x.get(k)==False for x in details) for k in ["filename_satellite_matches","source_filename_matches","source_key_basename_matches"]}}
    (output/"additional_diagnostics.json").write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding="utf-8")
    ranges=sample.groupby(["satellite","grid_signature"]).timestamp_utc.agg(["min","max"]).reset_index()
    ranges.to_csv(output/"sample_grid_periods.csv",index=False)
    invalid=[x for x in details if x.get("valid_pixels")==0]
    invalid_table=pd.DataFrame([{"captura UTC":x.get("capture_utc"),"satélite":x["metadata"]["satellite"],"pixels inválidos":x["invalid_pixels"],"seleção":x["reason"]} for x in invalid])
    test_file=output/"tests.txt"
    test_text=test_file.read_text(encoding="utf-8") if test_file.exists() else "Resultado de testes não registrado."
    fig_names=sorted(p.name for p in (ROOT/"reports"/"figures").glob("*.png"))
    report=f"""# EDA meteorológica e GOES — estágio 2

## 1. Objetivo, metodologia e limites

Compreender a base antes de definir o problema de previsão de chuva na próxima hora. **Nenhum target, divisão de treino/teste, imputação, normalização, remoção de outliers ou modelo foi criado.** O CSV completo foi analisado descritivamente. Colunas auxiliares em memória servem apenas aos agrupamentos e não constituem um dataset de treino.

O projeto existente foi ampliado; `audit.py`, seus testes e os relatórios do estágio 1 foram preservados. As fontes permanecem externas e somente para leitura. A entrada real é `dataset_goes.zip`, não `dataset.zip`. O ZIP foi consultado por seu índice e por leituras seletivas; nenhuma extração foi realizada. Uma matriz por vez, `allow_pickle=False`, máximo de 32 MiB por NPZ e 128 MiB de expansão interna.

**Tempo:** `time` é ISO-8601 sem offset, localizado explicitamente em **America/Sao_Paulo**, com erro em caso de horário ambíguo ou inexistente, e convertido a UTC para comparação. O período observado tem offset −03:00. Metadados GOES com offset explícito são respeitados. Estatísticas do CSV usam desvio padrão amostral (`ddof=1`); pixels usam populacional (`ddof=0`). Os limiares das checagens estão no manifesto e não são regras de limpeza.

Amostra determinística: ordenar o índice por captura nominal/nome e sortear, com `numpy.default_rng(42)`, duas imagens únicas por estrato **mês UTC × satélite do nome**, restritas a arquivos referenciados. Acrescentar três imagens antes e três a partir de cada troca de satélite; três menores e três maiores NPZ; oito links reutilizados com maior intervalo (desempate lexicográfico); três menores e três maiores desvios nominais; primeiro e último arquivos não referenciados; amostra do estágio 1. Deduplicar nomes antes da leitura. Resultou em **{len(details)} imagens únicas**, com **{len(pairs)} pares CSV–imagem** porque todos os registros que usam cada imagem selecionada foram comparados. Há imagens fora do CSV, sem pareamento. O manifesto lista todos os nomes e motivos. A amostra mistura cobertura regular e procura dirigida de anomalias: **suas proporções não estimam prevalência no acervo**.

Foram lidos {read('goes_sample_manifest.csv').bytes.sum()/1024**2:.1f} MiB de membros NPZ selecionados, além da releitura da imagem inicial pela auditoria; não 79 GB de pixels. Não foi medido o pico de RAM. Foram usadas dependências existentes e matplotlib instalado em pasta de apoio, sem instalação global.

## 2. Qualidade do CSV e confirmação do estágio 1

**Fatos:** {audit['csv']['rows']} linhas × {audit['csv']['columns']} colunas; {audit['csv']['time_min']} a {audit['csv']['time_max']}. Série crescente, intervalo de uma hora, zero timestamps inválidos/duplicados e zero lacunas. Zero registros duplicados. Somente `image_link` tem ausências: {audit['csv']['links_missing']}. Não há valores infinitos nas colunas numéricas. {audit['csv']['links_filled']} links preenchidos e {audit['csv']['links_unique']} distintos; todos existem no ZIP. Tipos e ausência por coluna constam de `audit_recheck.json` e `numeric_summary.csv`.

Divergências nas métricas comparadas com o JSON anterior: `{run['csv_divergences']}`. A execução atual confirmou os números. As versões de Python/pandas/numpy registradas no relatório anterior diferem do ambiente atual; o manifesto preserva as versões efetivamente usadas agora.

**Correção documental:** o README do projeto e a resposta anterior mencionavam offset −03:00 dentro de `timestamp_utc`. O JSON/relatório histórico disponível registra `{run['previous_sample_timestamp']}`; a releitura direta confirmou **`{run['current_first_timestamp']}`**. As {len(details)} amostras usam offset UTC zero. A alegação anterior de offset local não é corroborada pelos arquivos atuais e foi corrigida no README do projeto. A diferença de 21 segundos da primeira imagem permanece correta. Não foram alterados metadados nem relatórios históricos.

## 3. Distribuições e variáveis especiais

Tabela resumida; o CSV anexo inclui também quartis, p1/p5/p95/p99, número de únicos, ausentes e infinitos para **todas as 20 variáveis numéricas**. Médias de `weather_code` não têm interpretação contínua e a média aritmética de direção não deve ser usada como direção predominante, embora constem na descrição mecânica dos dtypes.

{table(summary[['variable','unit_readme','mean','median','std','min','25%','75%','max','unique','missing']])}

**Fatos e interpretação:** temperatura e pressão têm distribuição central com caudas; umidade e nebulosidade são limitadas, com concentrações próximas dos extremos para nebulosidade. Radiação e insolação têm massa em zero e componente diurna; chuva é fortemente assimétrica. Histogramas usam 40 bins; chuva, 50 bins com eixo de contagem logarítmico e painel separado de valores positivos. Boxplots usam 1,5 IQR, sem exclusão de valores.

`is_day`: {int(df.is_day.eq(1).sum())} registros diurnos ({df.is_day.eq(1).mean():.2%}) e {int(df.is_day.eq(0).sum())} noturnos. Somente 0/1. `weather_code` é categórico: códigos 0 e 3 são os mais frequentes. Não foi codificado para treinamento.

Direção do vento é circular: os 16 registros com velocidade zero foram excluídos **somente** do resumo circular/gráfico. Média circular dos demais ≈105,06°, comprimento resultante ≈0,392 (dispersão relevante); distribuição em 16 setores. Isso não atribui significado meteorológico à direção em calmaria e não transforma a base. O CSV original permanece intacto.

Correlação de Pearson calculada apenas para as 17 variáveis quantitativas não circulares; `weather_code`, `wind_direction_10m` e `is_day` foram omitidas da matriz, analisadas separadamente. `rain` e `precipitation` têm correlação 1 porque são iguais. As associações são contemporâneas, descritivas e influenciadas por sazonalidade/autocorrelação; não medem ganho preditivo, causalidade nem justificam seleção de features.

## 4. Evolução temporal e sazonalidade

{table(annual)}

**Fatos:** todos os meses entre janeiro/2020 e setembro/2026 estão representados. O número de horas acompanha a duração do mês. 2026 termina em setembro; totais anuais não são diretamente comparáveis com anos completos. `annual_jan_sep.csv` compara a mesma janela jan–set: por exemplo, a média de temperatura de 2024 é 22,71 °C e a de 2022, 20,39 °C nessa janela. Isso é variação observada, não evidência isolada de mudança climática ou de erro na fonte.

{table(season)}

O mês de janeiro apresenta média de 189,2 mm por mês observado e 30,4% de horas positivas, contra 39,5 mm e 5,3% em julho. Temperaturas médias por mês do calendário variam aproximadamente de 17,66 °C (junho) a 24,29 °C (dezembro). **Limitação:** há sete ocorrências para jan–set e seis para out–dez; não se trata de uma normal climatológica. Hipóteses para mudanças entre anos incluem variabilidade meteorológica e composição da fonte; a base não permite separar essas causas. Não foram aplicados testes de tendência nem inferidas rupturas causais.

Acumulados mensais agrupam o timestamp da linha, sem deslocá-lo. Se esse timestamp representa o fim do intervalo anterior, a primeira linha de um mês inclui a última hora do mês anterior. É uma convenção descritiva explícita, a rever antes do target.

## 5. Rain, precipitation, intensidade e códigos

{table(rains)}

**Fatos:** ambas são exatamente iguais nas {len(df)} linhas. Há 49.040 zeros (82,89%) e 10.120 valores positivos (17,11%), com máximo 18 mm, 140 valores distintos e mediana positiva de 0,3 mm. A igualdade neste arquivo não torna suas definições equivalentes em outras bases. O README descreve `rain` como chuva e `precipitation` como precipitação total, ambas em mm.

Blocos exploratórios de horas consecutivas com valor >0 (não são o target e não são uma definição definitiva de tempestade): **{len(events)} blocos**, duração mediana {events.hours.median():g} h, máxima {events.hours.max():g} h, maior soma {events.total_mm.max():g} mm. Uma hora seca ou lacuna quebra o bloco. Os arquivos registram limites e indicam eventual censura nas bordas. Não há inferência de independência entre esses eventos.

{table(codes)}

Os códigos 0/1/2/3 aparecem somente com precipitação zero; 51/53/55/61/63/65, somente com valor positivo. Os intervalos de intensidade por código estão na tabela. Isso mostra uma associação descritiva muito forte entre campos do mesmo horário; não é evidência de capacidade de antecipar a próxima hora.

**Documentação complementar:** a [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), consultada em 13/10/2026, define precipitação como soma da hora anterior e chuva como componente líquida. Radiação é média da hora anterior; `is_day` é indicador do instante. O código meteorológico é derivado de variáveis incluindo precipitação e nebulosidade. A unidade do vento é configurável; os gráficos seguem m/s conforme o README local, mas a requisição original não está disponível. Estas definições ajudam a interpretar os achados, sem certificar a configuração histórica deste CSV.

## 6. Outliers e consistência física

Classes: **A** evidência suficiente de invalidade; **B** suspeita que exige investigação; **C** extremo potencialmente válido; **D** nenhum problema identificado na checagem, sem certificação geral.

{table(checks)}

Não houve violação dos domínios físicos básicos testados no CSV (classe A). Há **1.939** horários com `is_day=0` e radiação positiva, todos às 18/19/20 h locais, máximo {diagnostics['night_radiation_max_W_m2']:g} W/m². **Hipótese:** média da hora anterior pode incluir luminosidade mesmo quando o indicador instantâneo já é noturno; requer confirmação da semântica temporal. Há **131** casos de rajada menor que vento, diferença máxima {diagnostics['max_wind_minus_gust_m_s']:g} m/s; janelas, parâmetros e origem devem ser investigados. Exemplos com linha e valores estão em `suspect_examples.csv`.

Temperatura de 1,8 a 38,5 °C, rajada até 21,3 m/s e chuva até 18 mm são extremos que, isoladamente, não demonstram erro. Na chuva, Q1=Q3=0, de modo que o critério IQR marca **todos** os valores positivos. Removê-los destruiria o fenômeno a estudar. Nenhuma correção foi aplicada.

## 7. Investigação amostral GOES

{len(details)} NPZ examinados sequencialmente, incluindo nomes de origem, chaves, timestamp, grade, satélite, escala, offset, unidade, dtype, máscara e estatísticas. Os detalhes completos estão em `goes_sample_details.json`; os resultados planos, no CSV homônimo de resumo. Metadados ausentes e erros são explícitos, sem inventar estatísticas.

Foram encontradas **{len(invalid)} matrizes inteiramente preenchidas com fill_value**, sem pixels válidos:

{table(invalid_table)}

Essas matrizes são **A para uso numérico naquela observação**: não fornecem informação de brilho válida. Isso não prova corrupção do arquivo, e os originais não foram descartados. Três menores arquivos foram procurados deliberadamente; portanto, não extrapolar a taxa 4/192 para o conjunto. Os demais {len(details)-len(invalid)} NPZ amostrados têm zero pixels inválidos pela máscara disponível. Sem flags radiométricas adicionais, pixel diferente do fill não significa qualidade científica garantida.

Todos os metadados esperados foram encontrados nesta amostra. As comparações de satélite/nome de origem/basename da chave com o caminho tiveram estes números de discordâncias: `{diagnostics['metadata_mismatches']}`. O início informado pelo metadado fica entre {diagnostics['metadata_vs_filename_min_seconds']:g} e {diagnostics['metadata_vs_filename_max_seconds']:g} segundo em relação ao nome NOAA, compatível com perda da fração de segundo no metadado; não corrigido.

## 8. Consistência espacial, grades e satélites

{table(grids)}

Na amostra, dtype int16, Kelvin, scale_factor ≈0,06145332, add_offset ≈89,62000 e fill_value −1 são compartilhados. Há **duas grades**: 885×1217 e 882×1217. O README original já descreve ambas e diferentes extensões de projeção. GOES-19 aparece nas duas grades; trocar o satélite não determina sozinho a grade.

{table(ranges)}

Os limites acima são **apenas primeiras/últimas ocorrências amostradas**, não datas exatas de mudança de grade. A diferença aparece entre as amostras de 23 e 27/05/2026; não foi feito inventário de metadados de todos os NPZ. O índice nominal identifica a passagem de G16 para G19 em **07/04/2025 às 16:00:20,8 UTC**, e as seis imagens próximas à fronteira foram examinadas. Isto descreve a troca neste acervo, não certifica toda a história operacional dos satélites.

As estatísticas são computáveis na mesma unidade, mas **comparabilidade física plena não está estabelecida**: domínio espacial, grade, calibração e máscara podem mudar. A média da imagem inteira cobre área extensa e pode diluir informação de Londrina.

**Alternativas para discussão:** (1) manter estatísticas de domínio inteiro como baseline, com diagnóstico separado por grade/satélite; (2) definir uma região geográfica fixa em torno de Londrina e selecionar pixels pela geolocalização própria de cada grade; (3) reamostrar ambas para grade comum, com método e custos explícitos. Não usar os mesmos índices de linha/coluna como se fossem a mesma região. Nenhuma opção foi implementada.

## 9. Consistência temporal e disponibilidade operacional

Dos {len(pairs)} pares amostrados, **{pairs.direction.eq('depois').sum()}** têm captura posterior à referência, **{pairs.direction.eq('antes').sum()}** anterior e **{pairs.direction.eq('igual').sum()}** igual. Mediana {pairs.delta_seconds.median():g} s; mínimo {pairs.delta_seconds.min():g} s (−89 min 40 s) e máximo {pairs.delta_seconds.max():g} s (+80 min 20 s). O desvio inicial de 21 s está confirmado. As linhas individuais, inclusive reusos, estão em `goes_temporal_pairings.csv`. Selecionamos intencionalmente extremos; esses percentuais não representam todo o dataset.

Também foram lidos os timestamps nominais dos nomes de todos os arquivos, sem carregar pixels, apenas para inventário e seleção de casos (`filename_delta_summary.csv`). Não equivalem à validação de todos os metadados. O nome NOAA inclui fim da captura e criação do produto; suas diferenças estão na tabela amostral e **não são horários comprovados de chegada ao sistema do usuário**.

**Regra recomendada para discussão:** emitir em um instante t bem definido e aceitar somente imagens cujo produto completo já estivesse recebido em t. Exigir `fim_da_captura + latência documentada ≤ t`, além de um limite de idade da imagem; preferir horário real de disponibilidade, quando existir. A latência e a idade máxima ainda não foram escolhidas. Sem logs, testar futuramente uma hipótese conservadora de latência, claramente declarada, e selecionar apenas imagens anteriores elegíveis. Uma captura que apenas começa antes de t não basta. Não deslocar os timestamps nem trocar os links automaticamente nesta etapa.

## 10. Cobertura, ausências e reuso

Cobertura global por link: {df.image_link.notna().mean():.3%}. Há **28 blocos de ausência**, maior de **39 horas**, de 24/05/2026 21h a 26/05/2026 11h locais. Meses de menor cobertura:

{table(monthly.nsmallest(5,'coverage')[['month','rows','images','coverage']])}

Cobertura por ano e satélite inferido do nome (contagem de links, não de matrizes úteis):

{table(read('coverage_year_satellite_filename.csv'))}

Há {len(reuse)} imagens reutilizadas: 65 são usadas em duas linhas adjacentes e duas em três linhas, abrangendo duas horas. São 69 referências adicionais. Nenhum reuso ultrapassa dois intervalos horários nesta auditoria. `image_reuse.csv` registra cada caso. Imagens compartilhadas podem contaminar fronteiras futuras de treino/validação/teste e precisam de regra por grupo/tempo, sem divisão aleatória.

Dos 121 NPZ não referenciados, **{unref_counts['before_csv']}** têm captura nominal anterior ao primeiro horário do CSV, **{unref_counts['after_csv']}** posterior ao último e **{unref_counts['inside_csv']}** dentro do intervalo. Portanto, todos estão fora do intervalo de referências do CSV. **Interpretação:** a diferença de cobertura e os fusos explicam a existência de arquivos extras nas bordas; não é evidência de erro. Todos foram preservados.

Cobertura por link superestima disponibilidade útil quando a matriz é inválida ou chega tarde. Selecionar apenas registros com imagem pode alterar a distribuição temporal; manter ausências explícitas até decidir o protocolo e reportar cobertura por período. Não excluir automaticamente períodos de falha.

## 11. Riscos de vazamento e protocolo a definir

- Imagens capturadas ou disponibilizadas após a emissão não são features elegíveis, mesmo que o link já esteja no CSV histórico.
- Reanálises e variáveis acumuladas podem só existir após o instante previsto; confirmar disponibilidade real e versões da fonte. O dataset não contém esse histórico de disponibilização.
- Nunca usar `rain`/`precipitation` do intervalo futuro como feature. A forte ligação de weather_code com chuva do mesmo registro exige o mesmo cuidado temporal.
- Ajustar imputadores, escalas e demais transformações somente no treino; nenhuma estatística global desta EDA deve virar parâmetro de transformação do treino.
- Não selecionar features pelos resultados do teste. Não embaralhar a avaliação temporal ou dividir aleatoriamente.
- Impedir que imagens compartilhadas e janelas sobrepostas atravessem partições; estabelecer margem na fronteira compatível com horizonte, janelas e reuso.

O protocolo deverá registrar emissão t, horizonte de uma hora, informações comprovadamente disponíveis em t, definição do alvo e fronteiras temporais. Nenhuma partição foi feita.

## 12. Decisões pendentes e opções de target

As opções abaixo são **propostas, não colunas criadas**. Para previsão emitida em t, definir primeiro o intervalo (t,t+1h] e confirmar se o registro em t+1h representa essa acumulação:

| Opção | Interpretação | Implicação |
|---|---|---|
| rain > 0 no intervalo futuro | Qualquer chuva líquida registrada | Sensível à resolução/traços; prevalência depende da fonte. |
| precipitation > 0 no intervalo futuro | Qualquer precipitação total | Igual ao primeiro nesta base, mas conceitualmente inclui outros componentes. |
| rain ou precipitation ≥ limiar τ | Evento com intensidade mínima relevante | Exige escolher variável, valor, unidade e convenção ≥/>, justificados pela aplicação. Não escolher pelo teste. |

Não foi escolhido τ nem criada `rain_next_hour`. Zero observado, ausência de observação e imagem sem pixels válidos são estados distintos. Decidir também latência e idade máxima da imagem, janela espacial, critérios de qualidade de pixels, tratamento futuro de ausências e regra para imagens reutilizadas nas fronteiras. A regra espacial deve lidar com as duas grades antes de comparar features em massa.

## 13. Recomendações e próximos passos

1. Validar a semântica temporal e a disponibilidade operacional das fontes com a requisição original e logs, se existirem.
2. Escolher formalmente alvo, instante de emissão, horizonte e regra de elegibilidade da imagem. Documentar as decisões antes de montar treino.
3. Decidir região espacial e tratamento de grades, matrizes totalmente inválidas e ausências. Investigar os 131 casos vento/rajada e as convenções de radiação.
4. Somente após autorização, planejar tratamento e construção do dataset; depois comparação temporal entre baseline meteorológico e alternativa com GOES.

**Limitações:** uma localidade, período relativamente curto, origem em reanálise conforme README, unidades do vento não verificadas pela requisição, amostra GOES direcionada, ausência de flags radiométricas e de logs de disponibilidade. Não se sabe ainda se as estatísticas de imagem acrescentam informação preditiva. A EDA não responde essa pergunta.

## Reprodutibilidade, preservação e testes

`src/data/eda.py` reproduz tabelas, amostragem, figuras e este relatório; `eda_report.py` permite reemitir o relatório sem ler novamente os NPZ. A seed e todos os parâmetros estão em `run_manifest.json`. Nomes/detalhes individuais da amostra foram salvos. As figuras são estáticas, sem imagens decorativas ou conversões de matrizes GOES em PNG para treinamento.

Fontes e arquivos protegidos inalterados durante a execução: **{run['protected_unchanged']}**. SHA-256 para arquivos pequenos; somente tamanho/mtime para o ZIP. Isso não certifica o hash integral de 79 GB. A leitura verifica os membros acessados, não o CRC de todo o acervo.

Ambiente efetivo:

```json
{json.dumps(run['environment'],ensure_ascii=False,indent=2)}
```

Resultado dos testes registrado em `tests.txt`:

```text
{test_text.strip()}
```

## Figuras e arquivos

Tabelas estão nesta pasta: resumo numérico/ano/mês, sazonalidade/ciclo horário, frequências, blocos positivos, checagens, reuso/ausências, inventário resumido, amostra GOES e pareamentos. Os nomes são autoexplicativos; manifesto e JSONs guardam evidências e parâmetros.

"""
    report += "\n".join(f"- [{name}](../figures/{name})" for name in fig_names)
    report += "\n\nA EDA termina aqui. Tratamento, target, extração em massa, divisão temporal e treinamento aguardam confirmação.\n"
    (output/"eda_report.md").write_text(report,encoding="utf-8")


if __name__=="__main__":
    output=ROOT/"reports"/"eda"
    manifest=json.loads((output/"run_manifest.json").read_text(encoding="utf-8"))
    build(pd.read_csv(manifest["sources_before"][0]["path"]),output)
