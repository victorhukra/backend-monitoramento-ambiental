# MVP meteorológico — preparar a tabela, passo a passo

**Etapa executada em 22/10/2026.** Escopo: Londrina, próxima hora, quatro variáveis meteorológicas. Nenhum modelo foi treinado e nenhuma separação de períodos foi feita.

## O que entra e o que sai

Entrada: CSV original, somente para leitura. Saída: `data/processed/weather_training.csv`, uma tabela experimental com estas colunas:

| Coluna | Papel |
|---|---|
| time | T, horário de referência com offset; rastreabilidade, não entrada do modelo |
| temperature_2m | Entrada: temperatura em °C |
| relative_humidity_2m | Entrada: umidade em % |
| pressure_msl | Entrada: pressão ao nível do mar em hPa |
| cloud_cover | Entrada: nebulosidade em % |
| target_time | T+1h, fim do intervalo previsto; rastreabilidade |
| rain_next_hour | Alvo: 1 para chuva positiva na hora seguinte, 0 para zero registrado |

**Hipótese adotada para executar o MVP:** `rain(u)` representa a quantidade em (u−1h,u]. Assim, `rain` às 15h define a resposta da previsão emitida às 14h. A documentação da fonte é compatível com essa leitura, mas a transformação original do CSV ainda não foi comprovada. A tabela não certifica previsão operacional ou disponibilidade histórica das entradas; registrar essa limitação na apresentação.

## Onde está cada responsabilidade

- `config.py`: quatro nomes de entradas, fuso e caminhos. O nome/ordem das entradas fica em `WEATHER_FEATURES`, para reutilização no futuro treino.
- `scripts/prepare_weather.py`: duas funções, `prepare_table` para transformar/verificar os dados e `run` para ler/gravar e gerar o gráfico opcional. O bloco final interpreta os argumentos do terminal.
- `tests/test_prepare_weather.py`: exemplos pequenos que verificam a regra temporal e os erros mais importantes.

Não movemos auditoria, EDA ou GOES. Eles continuam preservados como apoio. A configuração meteorológica usa `WEATHER_CSV_PATH`; `DATASET_MODE=sample/full` continua sendo escolha dos utilitários GOES, não seleciona linhas meteorológicas.

## Entendendo o código em sete passos

1. **Selecionar:** `source[required].copy()` separa somente as colunas necessárias, sem modificar o DataFrame original.
2. **Interpretar os horários:** `pd.to_datetime` lê a data; `tz_localize` associa horários sem fuso a São Paulo. Horários já com offset são convertidos. Timestamps ausentes, duplicados ou fora de hora cheia interrompem a execução, pois a associação ficaria ambígua.
3. **Ordenar:** `sort_values('time')` organiza os registros. A ordem do arquivo não é usada para decidir qual hora é a seguinte.
4. **Encontrar T+1h:** `pd.Timedelta(hours=1)` calcula o timestamp futuro. `merge` busca exatamente esse horário na própria tabela. Se houver lacuna, não pega uma linha de duas horas depois.
5. **Verificar:** uma linha só entra com quatro entradas finitas, umidade/nuvens em 0–100, pressão positiva e chuva futura finita/não negativa. Não imputamos, normalizamos ou removemos extremos estatísticos. Valores inválidos são excluídos somente do derivado, com motivo registrado; os originais permanecem intactos.
6. **Criar o alvo:** `.gt(0).astype('int8')` transforma chuva futura positiva em 1 e zero em 0, somente nas linhas elegíveis. Ausência não vira zero. `future_rain` e `rain` não são exportadas como entradas; não queremos entregar a resposta ao modelo.
7. **Salvar e conferir:** escrever tabela, resumo, exclusões, dez primeiras linhas e, opcionalmente, gráfico. SHA-256 antes/depois confirma preservação do CSV nesta execução.

Exemplo real conferido: para T = **01/01/2020 14h**, as entradas são 33,3 °C, 42% de umidade, 1005,3 hPa e 93% de nuvens. A resposta consulta chuva às **15h**; como é positiva, `rain_next_hour=1`. Esse exemplo explica o alinhamento, não demonstra desempenho preditivo.

Uma entrada ausente às 15h não invalida necessariamente a resposta para as 14h: para definir essa resposta, basta que a quantidade de chuva às 15h seja válida. As entradas do exemplo vêm das 14h.

## Executar no computador da equipe

Com o ambiente Python do projeto ativo e suas dependências instaladas, configurar em `.env`:

```dotenv
WEATHER_CSV_PATH=D:/dados-goes/dataset_weather.csv
WEATHER_TRAINING_PATH=data/processed/weather_training.csv
```

Usar o caminho real da sua máquina. Depois, na raiz do projeto:

```powershell
python -B scripts/prepare_weather.py --plot
python -B -m unittest discover -s tests -v
```

Alternativa sem editar `.env`:

```powershell
python -B scripts/prepare_weather.py --csv D:/dados-goes/dataset_weather.csv --plot
```

`--plot` usa Matplotlib já previsto nas dependências; sem ele, a preparação usa apenas pandas/NumPy. Nenhuma dependência nova foi instalada nesta etapa. Nesta máquina, o gráfico usou as bibliotecas locais da EDA em `work/eda-deps`; versões efetivas estão no resumo JSON.

O script recusa sobrescrever os derivados existentes. Para outra execução, escolher outro nome, sempre dentro de `data/processed`, por exemplo `--output data/processed/weather_training_v2.csv`. Assim não apagamos a fonte nem resultados por engano.

## Resultado verificado

| Medida | Resultado |
|---|---:|
| Linhas do CSV original | 59.160 |
| Linhas da tabela experimental | 59.159 |
| Sem chuva futura | 49.039 |
| Com chuva futura | 10.120 |
| Linhas excluídas | 1 |

A única exclusão é T = 30/09/2026 23h: não há registro de 01/10/2026 00h para definir seu alvo. Não houve exclusão por entrada inválida ou chuva futura inválida. Não houve lacunas horárias.

Arquivos locais, todos ignorados pelo Git:

- `weather_training.csv`: tabela completa.
- `weather_training.json`: hipótese, parâmetros, versões, hash da fonte e contagens.
- `weather_training_excluded.csv`: horários excluídos e motivos.
- `weather_training_preview.csv`: primeiras dez linhas.
- `weather_training.png`: quantidade por classe, sem métricas de modelo.

Conferimos as dez primeiras linhas e um exemplo positivo. Todas as 59.159 respostas também foram comparadas com uma consulta independente por timestamp ao CSV original; houve concordância completa. Uma repetição em memória produziu os mesmos alvos. **38 testes passaram**, oito novos e 30 preservados. O gráfico foi inspecionado visualmente e os derivados tiveram seu bloqueio no Git confirmado.

## Próxima etapa

Definir os períodos cronológicos de treino, validação e teste e conferir suas fronteiras usando `target_time`. Somente `WEATHER_FEATURES` deve entrar em X; `rain_next_hour` será y. Não usar todas as colunas automaticamente. Não embaralhar toda a série nem ajustar transformações nos dados reservados para teste.

Depois, treinar e avaliar o primeiro modelo e conectá-lo ao contrato `/predict`. A tabela `predictions` do banco é outra coisa: guarda chamadas e resultados da API, não substitui esta tabela de treinamento. Nenhuma API, migração de banco ou nova funcionalidade de GOES foi implementada nesta etapa.
