# Piloto técnico GOES — estágio 4

## 1. Escopo e amostra

Piloto de engenharia, executado em 15/10/2026. Nenhum alvo, conjunto de dados de modelagem, associação a previsão, elegibilidade temporal definitiva, imputação ou modelo foi criado. Fontes abertas somente para leitura. O ZIP real é `C:\Users\CANAL\Downloads\dataset_goes.zip`, confirmado no ambiente, com 79201181103 bytes. Foram usados `ZipFile.read(ZipInfo)` e `numpy.load(..., allow_pickle=False)`, sem extração em disco.

Seleção: **até 12 links únicos de janeiro/2023**, ordenados por time/nome e escolhidos em posições equiespaçadas por linspace inteiro entre primeiro e último. Nenhuma amostragem aleatória/seed é necessária. Janeiro contém 744 linhas com link e 744 links únicos; não foram lidas as 744 imagens do mês. Acrescentados os quatro casos totalmente inválidos já identificados na EDA, dois casos de maior intervalo de reuso (desempate por nome), e o primeiro exemplo válido de cada assinatura da EDA. Nomes são deduplicados antes da leitura.

Resultado: **19 imagens únicas selecionadas**. `sample_manifest.json` registra cada nome, motivos e referências locais do CSV. São referências para inspeção, não emissões de previsão. O resultado não estima frequência de falhas do acervo. Exemplos de metadados ausentes/inconsistentes conhecidos no manifesto da EDA: **0**. Não foi realizada busca de pixels por todo o ZIP; esses cenários foram exercitados em matrizes artificiais nos testes.

## 2. Implementação e reuso

`src/features/goes.py` separa leitura seletiva, diagnóstico de identidade e reconstrução física. Reutiliza `scalar` e `stats` de `src/data/audit.py`; `stats` é usado nos testes artificiais, não para gerar atributos regionais reais. Reutiliza-se também `fingerprint` no executor `src/features/pilot.py`. Os módulos anteriores não foram modificados.

A função histórica `inspect_npz` faz estatísticas da imagem inteira e falha para matriz totalmente inválida. Por isso não foi utilizada como extrator deste estágio: o novo contrato retorna estados explícitos e não emite cinco atributos para o domínio inteiro. `reconstructed` significa apenas que a leitura/transformação física funcionou; não certifica geolocalização, QA radiométrico completo ou disponibilidade temporal.

Limites: 30 imagens únicas no piloto, 32 MiB por membro externo e 128 MiB de expansão interna do NPZ. Uma imagem por vez; arrays liberados ao final da inspeção. Nenhum PNG/JPEG criado. Dependências efetivamente usadas: numpy/pandas e biblioteca padrão; nenhuma instalação nova.

## 3. Metadados e reconstrução física

Inspecionados `satellite`, `grid_signature`, `timestamp_utc`, `source_filename`, `source_key`, `units`, `scale_factor`, `add_offset` e `fill_value`. Chaves, formato/dtype e diagnósticos individuais estão em `image_diagnostics.json`. A tabela resumida está em `image_diagnostics.csv`.

| Satélite | Assinatura | Formato | Dtype | Imagens |
|---|---|---|---|---|
| GOES-19 | 4d1d681125ac7ad72c9085784ca9d701e44201dd836f5e105230f2542880a4a8 | [882, 1217] | int16 | 3 |
| GOES-16 | 44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876 | [885, 1217] | int16 | 16 |

Problemas de metadados/identidade registrados nesta execução: 0 arquivos. O manifesto e os detalhes preservam os valores reais por arquivo, sem propagar defaults de uma imagem para outra.

O preenchimento é obtido de cada arquivo, não fixado em −1. Para inteiros, um fill incompatível com o dtype é rejeitado, sem reinterpretar sinais. Fill NaN em matriz flutuante é explicitamente tratado. A máscara combina finitude e ausência de fill antes da multiplicação. Contagens de fill e não finitos podem se sobrepor; `invalid_pixels` conta a união, e a sobreposição é registrada.

Escala e offset devem ser escalares numéricos finitos. Este leitor C13 aceita escala positiva e unidade K/Kelvin; outras unidades ficam como não suportadas, sem valores inventados. Metadados físicos ausentes impedem reconstrução. Falhas de identidade são registradas separadamente e impedem considerar o arquivo plenamente validado, mesmo que sua transformação numérica seja possível. Timestamps sem offset são sinalizados sem assumir fuso.

Resultado por estado: `{'reconstructed': 15, 'all_invalid': 4}`. Nos arquivos reconstruídos, a faixa global dos **diagnósticos de leitura da matriz inteira**, em Kelvin, foi 181.73852955549955 a 331.07009736448526 K. Esses extremos não são estatísticas de Londrina, não são atributos e não demonstram qualidade de todos os pixels. Não houve conversão para Celsius ou confusão com temperatura do ar a 2 m.

| ID | Timestamp do NPZ | Satélite | Formato | Estado físico | Válidos | Inválidos | Mínimo diagnóstico K | Máximo diagnóstico K |
|---|---|---|---|---|---|---|---|---|
| 1 | 2020-01-01T00:00:21+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 190.15763440728188 | 300.8965172022581 |
| 2 | 2020-06-04T12:40:17+00:00 | GOES-16 | [885, 1217] | all_invalid | 0 | 1077045 | — | — |
| 3 | 2021-09-04T11:00:21+00:00 | GOES-16 | [885, 1217] | all_invalid | 0 | 1077045 | — | — |
| 4 | 2023-01-01T03:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 204.72207126766443 | 300.8965172022581 |
| 5 | 2023-01-03T22:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 188.2525814846158 | 309.56143533438444 |
| 6 | 2023-01-06T18:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 191.44815412908792 | 325.90801847726107 |
| 7 | 2023-01-09T13:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 202.87847166508436 | 314.2318876609206 |
| 8 | 2023-01-12T09:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 191.63251408934593 | 295.9187982752919 |
| 9 | 2023-01-15T04:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 198.8840058594942 | 298.25402443856 |
| 10 | 2023-01-18T00:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 186.65479516237974 | 302.30994356423616 |
| 11 | 2023-01-20T19:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 191.93978068977594 | 331.07009736448526 |
| 12 | 2023-01-23T15:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 190.4649010077119 | 324.125872194767 |
| 13 | 2023-01-26T10:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 186.28607524186373 | 297.823851197958 |
| 14 | 2023-01-29T06:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 181.73852955549955 | 296.59478479623795 |
| 15 | 2023-02-01T02:00:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 1077045 | 0 | 193.168847091496 | 301.1423304826021 |
| 16 | 2024-09-09T00:30:20+00:00 | GOES-16 | [885, 1217] | reconstructed | 17346 | 1059699 | 246.14160900563002 | 293.2763055115938 |
| 17 | 2026-05-27T22:00:20+00:00 | GOES-19 | [882, 1217] | reconstructed | 1073394 | 0 | 217.44290852546692 | 296.96350471675396 |
| 18 | 2026-06-22T23:00:22+00:00 | GOES-19 | [882, 1217] | all_invalid | 0 | 1073394 | — | — |
| 19 | 2026-08-31T23:00:22+00:00 | GOES-19 | [882, 1217] | all_invalid | 0 | 1073394 | — | — |

## 4. Seleção espacial: não validada

**Fatos observados:** todos os conjuntos de chaves lidos estão no JSON. Os NPZ examinados contêm matriz e metadados escalares; não contêm vetores x/y, latitude/longitude por pixel ou objeto completo de projeção. A listagem do ZIP não encontrou arquivos auxiliares não NPZ: 0. Essa listagem não é leitura de todas as matrizes. `grid_signature` é identificador, não função de geolocalização.

O README original, §8 “Informações da projeção”, fornece longitude central −75°, altura 35.786.023 m, sweep x e limites distintos de cada assinatura:

| Grade | Formato | x_min / x_max (m conforme exemplo) | y_min / y_max (m conforme exemplo) |
|---|---|---|---|
| 44738571… | 885×1217 | 710424,5721944869 / 3147309,4861819297 | −3299614,6266644895 / −1528063,4525660723 |
| 4d1d6811… | 882×1217 | 712428,538085401 / 3149313,452072844 | −3283582,3662838787 / −1518043,6231115013 |

**Interpretação:** esses valores permitem uma visualização aproximada documentada, mas não fecham a correspondência inequívoca entre centros dos pixels e coordenadas. Não há declaração suficiente de centros versus bordas, vetores/ordem da grade, elipsoide e correspondência ao recorte original. Inferir tudo com linspace e defaults de projeção criaria hipóteses não validadas.

**Decisão do piloto:** não construir máscara, não escolher raio/contorno, não redimensionar e não calcular estatísticas regionais reais. O futuro centro de referência do README é aproximadamente −23,304°, −51,186°; isso não define sozinho a região. Não assumir que índices iguais nas duas grades indicam o mesmo lugar.

Para destravar, obter pelo menos um netCDF de origem de cada assinatura com coordenadas x/y (unidades, centros e ordem), atributos completos da projeção geoestacionária (altura, longitude de origem, sweep, eixos do elipsoide), e código/índices de recorte que relacionem a matriz NPZ ao netCDF; alternativamente, fornecer matrizes lat/lon validadas por assinatura. Confirmar limites de pixel e orientação. Validar o ponto de Londrina e uma região geográfica fixa nas duas grades. Depois definir contorno, critério de pixels e cobertura mínima, sem desempenho preditivo como critério. Não foi feito download de dados adicionais.

## 5. Estatísticas e qualidade

Entre as reconstruções, **14 matrizes têm todos os pixels válidos segundo fill/finitude e 1 é parcialmente inválida**. Isso não certifica qualidade radiométrica. Casos parciais:

- `dataset_goes/samples/2024/09/09/OR_ABI-L2-MCMIPF-M6_G16_s20242530030204_e20242530039512_c20242530045310.npz`: 17346 pixels válidos e 1059699 inválidos; fração válida 1.6105%.

O caso parcial de setembro/2024 já está no JSON detalhado da EDA, com a mesma contagem de inválidos, e foi confirmado pelo piloto. A generalização no texto da EDA de que os demais arquivos tinham zero pixels inválidos não corresponde a esse registro detalhado. O relatório anterior foi preservado; esta ressalva corrige sua interpretação. Nenhum limiar mínimo de cobertura foi escolhido: reconstrução bem-sucedida não implica imagem elegível para atributos.

**As cinco atributos regionais não foram extraídas**, porque a condição de validação espacial do pedido não foi atendida. `region_statistics` permanece null e `spatial_status` é `not_validated`. As contagens e frações registradas referem-se exclusivamente à matriz lida, como diagnóstico de máscara. Não foram apresentadas como qualidade de uma região de Londrina.

Média, desvio padrão populacional, mínimo, máximo e mediana foram verificados somente em pequenas matrizes artificiais de valores físicos com máscara conhecida, reutilizando a função `stats`. Isso testa a aritmética sem fabricar uma máscara geográfica. Em matriz totalmente inválida: estado `all_invalid`, nenhuma matriz física retornada, extremos físicos ausentes, nenhuma substituição por zeros. Casos de metadados físicos inválidos são distintos de ausência de pixels válidos.

## 6. Limitações, falhas e temporalidade

Os casos totalmente inválidos da EDA foram incluídos deliberadamente. Metadados ausentes ou identidade incompatível não tinham exemplos reais identificados disponíveis; os testes sintéticos não são evidências de que esses problemas ocorram no acervo. Um fill diferente do esperado ou campo ausente nunca aciona preenchimento silencioso.

Formatos distintos são suportados como matrizes numéricas; a compatibilidade entre assinatura e formato é conferida com o mapa do README apenas como diagnóstico, não validação geográfica. Unidade e escala compartilhadas não provam equivalência espacial ou calibração entre sensores.

O piloto registra referências do CSV e timestamps do NPZ sem estabelecer emissão, alvo, tolerância temporal, nova associação ou elegibilidade definitiva. Não transforma as capturas futuras em entradas autorizadas. Permanecem pendentes a semântica do CSV e logs históricos de disponibilidade. Não é um fluxo operacional em tempo real.

## 7. Testes e reprodutibilidade

Cada membro real foi lido e reconstruído **duas vezes sequencialmente**; compararam-se SHA-256 do payload e representação determinística de todos os diagnósticos (sem tempos). Resultado: 19 de 19 arquivos com resultados idênticos nas duas leituras. Isso verifica reexecução no ambiente atual, não identidade bit a bit entre plataformas. Os testes unitários também comparam arrays físicos, máscaras e diagnósticos, sem depender do ZIP original.

Testes originais preservados. Saída da execução em `tests.txt`:

```text
test_all_invalid_fails_clearly (test_audit.ImageTests.test_all_invalid_fails_clearly) ... ok
test_explicit_offset (test_audit.ImageTests.test_explicit_offset) ... ok
test_mask_and_kelvin (test_audit.ImageTests.test_mask_and_kelvin) ... ok
test_missing_metadata_does_not_invent_reconstruction (test_audit.ImageTests.test_missing_metadata_does_not_invent_reconstruction) ... ok
test_other_unit_is_not_celsius_converted (test_audit.ImageTests.test_other_unit_is_not_celsius_converted) ... ok
test_noaa_fractional_second_and_year_boundary (test_eda.TemporalTests.test_noaa_fractional_second_and_year_boundary) ... ok
test_spells_break_on_gap_and_dry_hour (test_eda.TemporalTests.test_spells_break_on_gap_and_dry_hour) ... ok
test_unknown_name_is_not_invented (test_eda.TemporalTests.test_unknown_name_is_not_invented) ... ok
test_identity_mismatch_and_naive_time_are_not_corrected (test_goes_pilot.NPZTests.test_identity_mismatch_and_naive_time_are_not_corrected) ... ok
test_individual_member_without_extraction (test_goes_pilot.NPZTests.test_individual_member_without_extraction) ... ok
test_missing_identity_metadata_is_explicit (test_goes_pilot.NPZTests.test_missing_identity_metadata_is_explicit) ... ok
test_nonscalar_metadata_is_recorded (test_goes_pilot.NPZTests.test_nonscalar_metadata_is_recorded) ... ok
test_same_payload_same_arrays_and_diagnostics (test_goes_pilot.NPZTests.test_same_payload_same_arrays_and_diagnostics) ... ok
test_all_invalid_is_not_zero (test_goes_pilot.PhysicalTests.test_all_invalid_is_not_zero) ... ok
test_bad_matrix (test_goes_pilot.PhysicalTests.test_bad_matrix) ... ok
test_five_statistics_on_known_synthetic_region (test_goes_pilot.PhysicalTests.test_five_statistics_on_known_synthetic_region) ... ok
test_inconsistent_physical_metadata (test_goes_pilot.PhysicalTests.test_inconsistent_physical_metadata) ... ok
test_kelvin_bytes_and_different_formatos (test_goes_pilot.PhysicalTests.test_kelvin_bytes_and_different_formatos) ... ok
test_mask_applied_before_multiplication (test_goes_pilot.PhysicalTests.test_mask_applied_before_multiplication) ... ok
test_missing_physical_metadata (test_goes_pilot.PhysicalTests.test_missing_physical_metadata) ... ok
test_nonfinite_union_not_double_counted (test_goes_pilot.PhysicalTests.test_nonfinite_union_not_double_counted) ... ok
test_physical_overflow_fails (test_goes_pilot.PhysicalTests.test_physical_overflow_fails) ... ok
test_reconstruction_and_nonminusone_fill (test_goes_pilot.PhysicalTests.test_reconstruction_and_nonminusone_fill) ... ok
test_unsigned_fill_is_not_wrapped (test_goes_pilot.PhysicalTests.test_unsigned_fill_is_not_wrapped) ... ok

----------------------------------------------------------------------
Ran 24 tests in 0.110s

OK
```

## 8. Tempo, memória e preservação

Tempo da execução completa do piloto antes da escrita dos relatórios: **3.140 s**, incluindo índice, seleção, duas leituras por imagem e fingerprints. Total de bytes de membros selecionados, por passagem: 19838743 bytes; não representa tráfego físico exato do disco/cache. Pico rastreado por tracemalloc: **77.68 MiB**. Essa medida não é RSS total do processo e pode omitir alocações nativas; não se afirma um limite máximo total de RAM. O JSON guarda limite inferior de bytes de arrays vivos por imagem, excluindo temporários. Leituras sequenciais evitam acumular matrizes.

Fontes e evidências de entrada inalteradas na verificação antes/depois: **True**. SHA-256 para arquivos pequenos, tamanho/mtime para ZIP; sem hash integral de 79 GB. Relatórios anteriores e código original não são regenerados. O ambiente efetivo é registrado no manifesto: `{'python': '3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]', 'platform': 'Windows-11-10.0.26200-SP0', 'numpy': '2.3.5', 'pandas': '3.0.1'}`.

## 9. Recomendação para a próxima etapa

**Concluído:** seleção pequena reproduzível, leitura NPZ, inspeção de metadados, reconstrução em Kelvin, máscara de fill/não finitos, estados de falha e testes independentes do acervo.

**Limitação confirmada neste piloto:** metadados geográficos insuficientes para validar a região fixa sem hipóteses adicionais. Portanto, a etapa condicional de atributos regionais não foi executada. Obter a correspondência de geolocalização por assinatura e definir a região antes de ampliar o processamento. Não avançar para conjunto de dados de treinamento, alvo ou modelo. O protocolo temporal continua sujeito à confirmação.

Fontes: `reports/dataset_audit.md`; `reports/eda/eda_report.md`, §§7–10; `reports/eda/goes_sample_details.json`; `reports/eda/image_reuse.csv`; `reports/protocol/protocol_proposal.md`, §§3, 7 e 9; README original, §§4, 5 e 8. Os caminhos absolutos e fingerprints usados nesta execução constam de `run_manifest.json`.
