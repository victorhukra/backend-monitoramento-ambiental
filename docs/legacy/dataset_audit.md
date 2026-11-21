# Auditoria inicial do conjunto de dados GOES

## Objetivo e método
Validar a estrutura, os vínculos e uma leitura numérica. Sem alvo, tratamento, EDA aprofundada ou treinamento.
CSV lido com pandas; ZIP aberto somente para leitura do índice e de um NPZ em memória. Nenhum arquivo extraído. Estatísticas populacionais (ddof=0).
## Fontes e preservação
| Arquivo original | Bytes |
|---|---:|
| `C:\Users\CANAL\Downloads\Backend_UTFPR\dataset_weather.csv` | 12822924 |
| `C:\Users\CANAL\Downloads\dataset_goes.zip` | 79201181103 |
| `C:\Users\CANAL\Downloads\Backend_UTFPR\README.md` | 17638 |
Verificação antes/depois sem alterações: **True**. SHA-256 para arquivos pequenos; tamanho e mtime para o ZIP. Não foi calculado hash integral do ZIP nem testado o CRC de todas as imagens.
A pasta original Backend_UTFPR contém README.md e dataset_weather.csv. O ZIP permanece na pasta Downloads. O projeto foi criado separadamente em outputs/projeto-goes. firstprompt.md é material fornecido, não uma autorização adicional; o escopo vem do pedido colado.
## Estrutura e qualidade do CSV
59160 linhas × 22 colunas. Memória pandas estimada: 22695376 bytes.
Período local America/Sao_Paulo: **2020-01-01 00:00:00 a 2026-09-30 23:00:00**.
Formato ISO sem offset com segundos: 59160 registros. Datas inválidas: 0. Ordem crescente: True.
Duplicatas completas adicionais: 0; timestamps duplicados adicionais: 0; horas ausentes: 0; horários fora da hora cheia: 0.
Diferenças consecutivas: `{'0 days 01:00:00': 59159}`. Lacunas verificadas na sequência local ingênua; o período observado começa após o último horário de verão brasileiro.
| Coluna | dtype pandas | Ausentes |
|---|---|---:|
| time | str | 0 |
| image_link | str | 179 |
| temperature_2m | float64 | 0 |
| relative_humidity_2m | int64 | 0 |
| dew_point_2m | float64 | 0 |
| apparent_temperature | float64 | 0 |
| weather_code | int64 | 0 |
| cloud_cover | int64 | 0 |
| pressure_msl | float64 | 0 |
| surface_pressure | float64 | 0 |
| wind_speed_10m | float64 | 0 |
| wind_direction_10m | int64 | 0 |
| wind_gusts_10m | float64 | 0 |
| shortwave_radiation | float64 | 0 |
| direct_radiation | float64 | 0 |
| diffuse_radiation | float64 | 0 |
| direct_normal_irradiance | float64 | 0 |
| is_day | int64 | 0 |
| sunshine_duration | float64 | 0 |
| soil_moisture_0_to_7cm | float64 | 0 |
| rain | float64 | 0 |
| precipitation | float64 | 0 |
Valores infinitos numéricos: `{'temperature_2m': 0, 'relative_humidity_2m': 0, 'dew_point_2m': 0, 'apparent_temperature': 0, 'weather_code': 0, 'cloud_cover': 0, 'pressure_msl': 0, 'surface_pressure': 0, 'wind_speed_10m': 0, 'wind_direction_10m': 0, 'wind_gusts_10m': 0, 'shortwave_radiation': 0, 'direct_radiation': 0, 'diffuse_radiation': 0, 'direct_normal_irradiance': 0, 'is_day': 0, 'sunshine_duration': 0, 'soil_moisture_0_to_7cm': 0, 'rain': 0, 'precipitation': 0}`.
Numéricas: temperature_2m, relative_humidity_2m, dew_point_2m, apparent_temperature, weather_code, cloud_cover, pressure_msl, surface_pressure, wind_speed_10m, wind_direction_10m, wind_gusts_10m, shortwave_radiation, direct_radiation, diffuse_radiation, direct_normal_irradiance, is_day, sunshine_duration, soil_moisture_0_to_7cm, rain, precipitation.
Texto: time, image_link. weather_code é código categórico apesar do dtype numérico; is_day é binário; wind_direction_10m é circular. time e image_link são referências e exigem tratamento específico. rain e precipitation exigem definição do horizonte/alvo e da disponibilidade operacional antes de decidir seu uso.
### Primeiras cinco linhas
```text
               time                                                                                                  image_link  temperature_2m  relative_humidity_2m  dew_point_2m  apparent_temperature  weather_code  cloud_cover  pressure_msl  surface_pressure  wind_speed_10m  wind_direction_10m  wind_gusts_10m  shortwave_radiation  direct_radiation  diffuse_radiation  direct_normal_irradiance  is_day  sunshine_duration  soil_moisture_0_to_7cm  rain  precipitation
2020-01-01T00:00:00 dataset_goes/samples/2020/01/01/OR_ABI-L2-MCMIPF-M6_G16_s20200010300216_e20200010309529_c20200010310031.npz            24.7                    74          19.9                  27.3             3           97        1008.9             942.3            2.27                 229             4.0                  0.0               0.0                0.0                       0.0       0                0.0                   0.293   0.0            0.0
2020-01-01T01:00:00 dataset_goes/samples/2020/01/01/OR_ABI-L2-MCMIPF-M6_G16_s20200010400216_e20200010409535_c20200010410032.npz            24.3                    77          20.0                  26.9             3           96        1008.3             941.7            2.42                 232             4.2                  0.0               0.0                0.0                       0.0       0                0.0                   0.293   0.0            0.0
2020-01-01T02:00:00 dataset_goes/samples/2020/01/01/OR_ABI-L2-MCMIPF-M6_G16_s20200010500218_e20200010509537_c20200010510030.npz            24.2                    78          20.0                  26.8             3           96        1007.9             941.3            2.22                 234             4.3                  0.0               0.0                0.0                       0.0       0                0.0                   0.293   0.0            0.0
2020-01-01T03:00:00 dataset_goes/samples/2020/01/01/OR_ABI-L2-MCMIPF-M6_G16_s20200010600218_e20200010609537_c20200010610032.npz            24.1                    77          19.9                  26.7             3           94        1007.6             941.0            2.33                 239             4.2                  0.0               0.0                0.0                       0.0       0                0.0                   0.293   0.0            0.0
2020-01-01T04:00:00 dataset_goes/samples/2020/01/01/OR_ABI-L2-MCMIPF-M6_G16_s20200010700218_e20200010709532_c20200010710033.npz            23.7                    81          20.1                  26.5             3           98        1007.5             940.8            2.06                 231             4.1                  0.0               0.0                0.0                       0.0       0                0.0                   0.293   0.0            0.0
```
### Últimas cinco linhas
```text
               time                                                                                                  image_link  temperature_2m  relative_humidity_2m  dew_point_2m  apparent_temperature  weather_code  cloud_cover  pressure_msl  surface_pressure  wind_speed_10m  wind_direction_10m  wind_gusts_10m  shortwave_radiation  direct_radiation  diffuse_radiation  direct_normal_irradiance  is_day  sunshine_duration  soil_moisture_0_to_7cm  rain  precipitation
2026-09-30T19:00:00 dataset_goes/samples/2026/09/30/OR_ABI-L2-MCMIPF-M6_G19_s20262732200204_e20262732209518_c20262732210004.npz            23.7                    86          21.2                  27.6             0           16        1011.5             944.5            1.12                 280             1.9                  5.0               1.0                4.0                      15.7       0                0.0                   0.444   0.0            0.0
2026-09-30T20:00:00 dataset_goes/samples/2026/09/30/OR_ABI-L2-MCMIPF-M6_G19_s20262732300204_e20262732309524_c20262732310008.npz            22.7                    91          21.1                  25.7            53          100        1012.0             944.8            2.55                 270             5.6                  0.0               0.0                0.0                       0.0       0                0.0                   0.450   0.7            0.7
2026-09-30T21:00:00 dataset_goes/samples/2026/10/01/OR_ABI-L2-MCMIPF-M6_G19_s20262740000204_e20262740009518_c20262740009599.npz            24.1                    74          19.1                  26.1            51           94        1011.5             944.6            2.55                 298             4.6                  0.0               0.0                0.0                       0.0       0                0.0                   0.403   0.1            0.1
2026-09-30T22:00:00 dataset_goes/samples/2026/10/01/OR_ABI-L2-MCMIPF-M6_G19_s20262740100204_e20262740109513_c20262740110003.npz            24.0                    74          19.1                  26.3             2           73        1011.7             944.8            2.13                 300             4.6                  0.0               0.0                0.0                       0.0       0                0.0                   0.402   0.0            0.0
2026-09-30T23:00:00 dataset_goes/samples/2026/10/01/OR_ABI-L2-MCMIPF-M6_G19_s20262740200204_e20262740209524_c20262740210004.npz            23.6                    76          19.1                  25.7             2           52        1012.0             945.0            2.36                 302             4.3                  0.0               0.0                0.0                       0.0       0                0.0                   0.402   0.0            0.0
```
## ZIP e correspondência dos links
Entradas: 61595; diretórios: 2562; arquivos: 59033; NPZ: 59033. Extensões: `{'.npz': 59033}`.
Soma dos tamanhos compactados: 79178610267 bytes; descompactados: 79217953080 bytes. NPZ individual: 4424 a 1594356 bytes.
Estrutura dataset_goes/samples/ANO/MES/DIA/*.npz em todos os NPZ: True. Datas dos caminhos: 2020/01/01 a 2026/10/06. São datas de diretórios, não uma validação dos timestamps de todas as capturas.
Contagem por ano: `{'2020': 8752, '2021': 8740, '2022': 8730, '2023': 8741, '2024': 8736, '2025': 8757, '2026': 6577}`. Contagens mensais no JSON anexo.
Links preenchidos: 58981; ausentes: 179; distintos: 58912. Correspondências exatas: 58981; links preenchidos sem arquivo: 0; NPZ não referenciados: 121.
Reuso de imagens: 67 links aparecem em mais de uma linha, com 69 referências adicionais. Isso não é duplicação de registros meteorológicos; exige atenção futura ao pareamento e às fronteiras de divisão temporal.
Nomes duplicados no ZIP: 0. Exemplos de links sem arquivo: `[]`.
image_link usa caminhos relativos à pasta que conteria dataset_goes. No ZIP, o caminho é o nome completo da entrada, sem depender do diretório atual do Python. O pacote está compactado, enquanto o README ilustra a árvore extraída; o acesso direto exemplificado no README precisa ser adaptado para ZipFile.
## Prova de conceito
Registro (índice base zero): 0. Conteúdo completo e resultados:
```json
{
  "row_index_zero_based": 0,
  "record": {
    "time": "2020-01-01T00:00:00",
    "image_link": "dataset_goes/samples/2020/01/01/OR_ABI-L2-MCMIPF-M6_G16_s20200010300216_e20200010309529_c20200010310031.npz",
    "temperature_2m": 24.7,
    "relative_humidity_2m": 74,
    "dew_point_2m": 19.9,
    "apparent_temperature": 27.3,
    "weather_code": 3,
    "cloud_cover": 97,
    "pressure_msl": 1008.9,
    "surface_pressure": 942.3,
    "wind_speed_10m": 2.27,
    "wind_direction_10m": 229,
    "wind_gusts_10m": 4.0,
    "shortwave_radiation": 0.0,
    "direct_radiation": 0.0,
    "diffuse_radiation": 0.0,
    "direct_normal_irradiance": 0.0,
    "is_day": 0,
    "sunshine_duration": 0.0,
    "soil_moisture_0_to_7cm": 0.293,
    "rain": 0.0,
    "precipitation": 0.0
  },
  "member_bytes": 1452623,
  "member_compressed_bytes": 1452012,
  "sha256": "0b1e6bba56297fc401919a144cf5d7a4c94f63e9d5c0e8cdf7ad307e7eab8c5d",
  "warnings": [],
  "keys": [
    "cmi_c13_raw",
    "scale_factor",
    "add_offset",
    "fill_value",
    "units",
    "timestamp_utc",
    "satellite",
    "source_filename",
    "source_key",
    "grid_signature"
  ],
  "metadata": {
    "scale_factor": 0.06145332008600235,
    "add_offset": 89.62000274658203,
    "fill_value": -1,
    "units": "K",
    "timestamp_utc": "2020-01-01T03:00:21+00:00",
    "satellite": "GOES-16",
    "source_filename": "OR_ABI-L2-MCMIPF-M6_G16_s20200010300216_e20200010309529_c20200010310031.nc",
    "source_key": "ABI-L2-MCMIPF/2020/001/03/OR_ABI-L2-MCMIPF-M6_G16_s20200010300216_e20200010309529_c20200010310031.nc",
    "grid_signature": "44738571aeb9849026fae60a7e0cca4369474a4f1097b01a4e2726ccca746876"
  },
  "missing_metadata": [],
  "shape": [
    885,
    1217
  ],
  "dtype": "int16",
  "pixels": 1077045,
  "nonfinite": 0,
  "fill_pixels": 0,
  "valid_pixels": 1077045,
  "invalid_pixels": 0,
  "raw_range_including_fill": {
    "mean": 2916.12880148926,
    "std_ddof0": 338.879682409145,
    "min": 1724.0,
    "max": 3388.0,
    "median": 2967.0
  },
  "raw_valid": {
    "mean": 2916.12880148926,
    "std_ddof0": 338.879682409145,
    "min": 1724.0,
    "max": 3388.0,
    "median": 2967.0
  },
  "transformation": "raw * scale_factor + add_offset; máscara aplicada antes",
  "physical": {
    "mean": 268.82579939651197,
    "std_ddof0": 20.825281593732008,
    "min": 195.56552657485008,
    "max": 297.823851197958,
    "median": 271.952003441751
  },
  "celsius": {
    "mean": -4.324200603488047,
    "std_ddof0": 20.825281593732008,
    "min": -77.5844734251499,
    "max": 24.673851197958015,
    "median": -1.197996558248974
  },
  "csv_local": "2020-01-01 00:00:00-03:00",
  "csv_utc": "2020-01-01 03:00:00+00:00",
  "capture_utc": "2020-01-01 03:00:21+00:00",
  "capture_minus_csv_seconds": 21.0
}
```
Os valores físicos são temperatura de brilho, não temperatura do ar a 2 m. A reconstrução usa os metadados reais e a fórmula documentada no README original.
Diferença captura − referência: **21.0 segundos**. O desvio deve ser interpretado em conjunto com a tolerância de pareamento, não como prova automática de erro. Se positivo, a imagem começa depois da referência e pode ainda não estar disponível numa previsão emitida exatamente naquela hora.
## Problemas, limitações e decisões pendentes
- Apenas uma imagem teve conteúdo e CRC de leitura verificados. Correspondência de todos os links no índice não prova integridade ou coerência temporal de todo o acervo.
- Ausência de image_link não equivale a ausência de chuva. Não houve imputação ou exclusão.
- A máscara considera fill_value e não finitos. Sem flags de qualidade adicionais, não se garante validade radiométrica de todos os pixels restantes.
- O README descreve grades e satélites distintos. A amostra não estabelece homogeneidade espacial ou temporal do conjunto. Estatísticas da área inteira podem diluir sinais locais de Londrina.
- Definir horizonte, limiar de chuva, instante de emissão, tolerância e latência de disponibilidade das imagens. O pareamento pelo vizinho temporal mais próximo pode escolher uma captura futura.
- Dados meteorológicos são históricos de modelos/reanálises conforme o README. Verificar quais variáveis estariam disponíveis no instante real de previsão e quais representam acumulações do intervalo.
- As unidades meteorológicas seguem o README; o CSV sozinho não permite verificar a configuração original da API (inclusive unidade do vento).
## Protocolo contra vazamento de informação
Não usar informação futura nem o alvo como atributo. Não criar alvo neste estágio. Não embaralhar nem dividir aleatoriamente a avaliação temporal final. Ajustar imputadores, normalizadores e demais transformações apenas no treino. Não usar estatísticas globais de outros períodos para transformar o treino, nem resultados do teste para selecionar variáveis. Não equiparar chuva zero e dado ausente. A EDA descritiva futura pode observar todo o período, mas decisões de modelagem devem respeitar o protocolo temporal.
## Próximos passos, sujeitos a autorização
Revisar estes achados; definir disponibilidade operacional, horizonte e limiar; depois autorizar a EDA aprofundada, a análise de cobertura temporal e das grades. Só em etapas posteriores: recorte/amostragem, tratamento, atributos, alvo, divisão temporal e comparação com modelo de referência meteorológico. Nenhuma dessas etapas foi executada.
## Ambiente
```json
{
  "python": "3.14.7 (tags/v3.14.7:823f032, Aug  5 2026, 10:51:32) [MSC v.1944 64 bit (AMD64)]",
  "platform": "Windows-11-10.0.26200-SP0",
  "pandas": "3.0.6",
  "numpy": "2.5.4"
}
```
A execução foi feita no Windows com o Python já disponível no ambiente do aplicativo, sem instalações globais. Código parametrizado para Ubuntu; execução no Ubuntu ainda não testada.
