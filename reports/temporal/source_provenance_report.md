# Proveniência e semântica temporal do CSV

Etapa 6 — 15/10/2026. **A semântica local de rain/precipitation continua não confirmada.** A origem é declarada pelo README, mas a cadeia requisição → resposta → transformação → CSV não está disponível nas pastas examinadas.

## Busca realizada e limites

O relatório de viabilidade efetivamente existente está em `reports/horizons/horizon_feasibility_report.md`, e não diretamente em `reports/`. Foram consultados também auditoria, EDA, protocolo e piloto, preservados integralmente.

Busca de arquivos, inclusive ocultos, no projeto `outputs/projeto-goes` e inventário recursivo da pasta original `C:/Users/CANAL/Downloads/Backend_UTFPR`. O workspace contém `outputs` e `work`; `work` contém somente `eda-deps`, dependências instaladas no estágio 2. Bibliotecas e caches de bytecode não são código de aquisição e foram excluídos da busca documental. Não foi pesquisado indiscriminadamente o computador inteiro nem inferida ausência fora desse escopo.

`evidence_inventory.json` registra caminhos, tamanhos, fontes e seleção amostral. `search_hits.txt` registra ocorrências de Open-Meteo, chamadas HTTP, unidades, timezone, exportação, deslocamento/reagregação e conversão espacial no código e README original. Para repetir a busca de conteúdo da raiz do workspace:

```powershell
rg -n -i 'open.?meteo|archive-api|requests\.|hourly_units|utc_offset_seconds|timezone|savez|netcdf|geostationary|grid_signature|shift\(|resample|tz_convert|tz_localize|to_csv' outputs/projeto-goes/src 'C:/Users/CANAL/Downloads/Backend_UTFPR/README.md'
```

**Resultados:** a pasta original contém apenas `dataset_weather.csv` e `README.md`. Não foram encontrados notebook/script de aquisição, URL com parâmetros completos, resposta bruta, metadados de consulta, histórico de versões ou logs de publicação/recebimento. Os JSON e CSV adicionais do projeto são resultados das nossas análises; não são respostas originais da API. Os diretórios `data/raw`, `data/sample` e `data/processed` têm apenas marcadores `.gitkeep`. O índice do ZIP confirma 59.033 membros de arquivo, todos `.npz`, sem resposta meteorológica, script ou NetCDF auxiliar. Nenhum arquivo foi extraído.

Os módulos `audit.py`, `eda.py` e `horizon_feasibility.py` leem o CSV já existente e interpretam timestamps. `to_csv` salva resumos; `shift` em `eda.py` detecta mudanças de grupos, satélites ou continuidade. Não são evidências de deslocamento na geração original. `tz_localize`/`tz_convert` nesses módulos comprovam somente a interpretação adotada nas análises posteriores.

## Classificação das conclusões

Categorias: **C1** confirmada pelo código ou dados originais; **C2** confirmada pela documentação específica da fonte/conjunto de dados, sem comprovar execução; **C3** compatível com a documentação, não confirmada para este CSV; **C4** desconhecida.

| Questão | Categoria | Evidência e limite |
|---|---|---|
| Arquivo contém time sem offset e registros horários | C1 | Auditoria do CSV: 59.160 linhas, 22 colunas, 2020–setembro/2026, sem lacunas/duplicatas identificadas. Isso não define suporte temporal do valor. |
| rain e precipitation são iguais neste arquivo | C1 | EDA e estágio 5: igualdade, valores não negativos, mínimo positivo 0,1 mm. Não prova origem nem janela. |
| Fonte declarada: Open-Meteo Historical Weather API, modelos/reanálises | C2 | README original §1.1. Não identifica modelo, versão, data de consulta ou célula efetiva. |
| Coordenadas aproximadas −23,304°, −51,186°, time em America/Sao_Paulo | C2 | README original §§1–3. É a convenção declarada para o arquivo; não prova o parâmetro enviado à API. |
| Unidade declarada de rain/precipitation: mm no intervalo | C2 | README §3. Não explicita início/fim do intervalo. |
| Requisição exata, endpoint efetivamente chamado, parâmetros e timezone solicitado | C4 | Não há URL, código de coleta nem resposta original. Não reconstruir consulta supostamente histórica a partir do README. |
| Quantidade em u corresponde à hora anterior | C3 | Compatível com a documentação da API consultada nos estágios 3/5; exportação local não rastreada. |
| Preservação da convenção e ausência de shifts na exportação | C4 | Código original ausente. Regularidade horária não demonstra ausência de deslocamento constante. |
| Revisão posterior dos valores locais | C4 | Nenhum par de versões, log de revisão ou data de geração da fonte. Ser reanálise não comprova que este CSV sofreu determinada revisão. |
| Disponibilidade das entradas no instante t | C4 | Não há histórico de publicação/ingestão por variável e versão. Data de download/mtime não prova disponibilidade histórica. |

As categorias não devem ser promovidas pelo simples fato de repetir uma hipótese em vários relatórios. A [documentação Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api#hourly-parameter-definition), consultada e registrada no estágio 5, permanece referência geral, não prova da exportação. Não foi realizada nova consulta meteorológica nesta etapa.

## Instantâneos e agregações: inventário condicionado à origem

| Campos | Convenção da fonte registrada no protocolo | Estado neste CSV |
|---|---|---|
| rain, precipitation | Acumulados da hora anterior | C3; bordas locais não comprovadas |
| shortwave_radiation, direct_radiation, diffuse_radiation, direct_normal_irradiance | Médias da hora anterior | C3 |
| sunshine_duration | Duração acumulada na hora anterior | C3 |
| temperature_2m, relative_humidity_2m, dew_point_2m, apparent_temperature, cloud_cover, pressure_msl, surface_pressure, wind_speed_10m, wind_direction_10m, soil_moisture_0_to_7cm | Valores referidos ao instante indicado, não necessariamente médias horárias | C3; modelo/configuração não recuperados |
| wind_gusts_10m | Convenção depende do modelo; há fontes com máximo na hora anterior | C4 para a janela específica deste CSV |
| weather_code | Código derivado de outras variáveis; não uma grandeza contínua | Natureza categórica C2; suporte temporal/proveniência exata C3/C4 |
| is_day | Indicador dia/noite associado ao horário | Natureza binária C1/C2; geração exata C4 |

As definições acima não atestam medição direta por estação, publicação no instante indicado ou independência de análises posteriores. Unidades declaradas, inclusive m/s para vento, precisam ser confrontadas com `hourly_units` da resposta original.

## Pacote mínimo ausente e validação proposta

Solicitar ao produtor **uma requisição original completa, sua resposta bruta e o trecho de código que produziu o CSV**, com versão/commit e data de execução. Preservar endpoint, latitude/longitude, datas, timezone, timeformat, lista hourly, modelo e unidades, inclusive defaults documentados. Na resposta, obter `hourly.time`, rain, precipitation, `hourly_units`, timezone/offset e coordenadas/célula/altitude efetivas, quando disponíveis.

Rastrear um trecho com transição seco→chuva→seco e uma virada de dia: timestamp da resposta → conversão de fuso → eventuais shifts/resample/joins → linha exportada. Comparar valores e suporte temporal sem corrigir dados automaticamente. Uma amostra valida somente o caminho de transformação coberto; confirmar que o mesmo código/configuração gerou o restante ou documentar versões distintas. Recuperar somente uma nova resposta atual não demonstra que ela foi a origem histórica nem exclui revisões.

Separar dois impedimentos: a semântica do intervalo impede construir **alvos definitivos**; falta de disponibilidade das entradas impede alegar **avaliação operacional**, mesmo depois de resolver os alvos. Geolocalização bloqueia os atributos GOES regionais, não a definição matemática isolada do alvo meteorológico.

## Preservação e reprodução

`python -B src/data/provenance_inventory.py`, da raiz do projeto, reproduz o inventário e lê somente metadados de três NPZ selecionados por critérios fixos. Caminhos de entrada estão explícitos no script e no manifesto. O payload NPZ é lido em memória, mas `cmi_c13_raw` não é materializado; não há inspeção nova de pixels. Arquivos pequenos têm SHA-256 antes/depois; ZIP tem tamanho/mtime, não hash integral. Fontes inalteradas nesta verificação. Relatórios históricos e funções anteriores não foram editados.

Não foram adicionadas funções de transformação ou elegibilidade. O diagnóstico é um script independente, com validações explícitas de tamanho de membro, escalar e limite de três combinações. A suíte existente foi executada; resultado em `tests.txt`.

## Evidência adicional — semântica das variáveis na Open-Meteo

**Verificação realizada em:** 27/10/2026
**Fonte:** [Open-Meteo — Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)

A documentação oficial descreve a variável horária `rain` como a precipitação líquida acumulada durante a hora anterior ao horário indicado. Também descreve `temperature_2m`, `relative_humidity_2m`, `pressure_msl` e `cloud_cover` como valores instantâneos.

Essa definição é compatível com a hipótese adotada na preparação da tabela: utilizar `rain` no horário `t+1` para determinar se houve chuva no intervalo seguinte a `t`.

**Limitação da evidência:** a documentação da API confirma a semântica da variável quando obtida por esse serviço, mas não comprova que o CSV analisado tenha sido exportado exatamente desse endpoint, com esses parâmetros e essa configuração. A requisição original, o modelo meteorológico selecionado e o fuso horário da exportação ainda precisam ser identificados.

**Implicação para o projeto:** a hipótese temporal é compatível com a documentação oficial, mas permanece condicional à confirmação da procedência do arquivo. A utilização de dados históricos de reanálise também não comprova a disponibilidade das mesmas entradas no momento de uma previsão operacional.

**Status:** evidência documental obtida; procedência específica do CSV e viabilidade operacional ainda não confirmadas.
