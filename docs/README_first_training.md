# Primeiro treinamento do MVP meteorológico de Londrina

Guia de implementação, resultados experimentais e passagem de responsabilidade — **27/10/2026**.

**Escopo:** experimento retrospectivo com dados meteorológicos tabulares. Imagens GOES ficam fora deste fluxo e não são pré-requisito. O treinamento não exige implementar API, banco de dados ou interface.

**Estado verificado:** preparação dos dados, divisão cronológica, treinamento, avaliação da validação e do teste, salvamento e recarga dos modelos foram realizados. Os artefatos da execução estão em `data/experiments/weather_20261027T173216Z/`. Os 42 testes automatizados passaram no ambiente limpo de validação.

**Limitação central:** o experimento técnico foi concluído, mas a semântica temporal exata da variável `rain` no arquivo original e a disponibilidade operacional das entradas no instante da previsão ainda não foram comprovadas. Os resultados não devem ser interpretados como comprovação de desempenho em tempo real.

## 1. Objetivo e escopo

O experimento utiliza quatro medidas meteorológicas do horário de referência T para estimar se haverá chuva na hora seguinte em Londrina.

É uma classificação binária:

- `0`: sem chuva no período-alvo;
- `1`: com chuva no período-alvo.

O modelo também produz uma probabilidade estimada para a classe de chuva. No experimento atual, a decisão é positiva quando essa probabilidade é maior ou igual a 0,5.

As quatro entradas são:

- `temperature_2m`
- `relative_humidity_2m`
- `pressure_msl`
- `cloud_cover`

O alvo é `rain_next_hour`, definido na tabela preparada a partir da chuva registrada no timestamp exato T+1h, com valor positivo quando `rain > 0 mm`.

**Importante:** essa definição depende da hipótese de que a variável `rain` representa a precipitação acumulada na hora anterior ao timestamp. Essa hipótese ainda precisa ser confirmada com evidências da exportação original.

O experimento é retrospectivo: utiliza dados históricos disponíveis atualmente. Isso não demonstra que as mesmas informações estavam publicadas ou recebidas quando a previsão teria sido emitida. A documentação da fonte declara dados meteorológicos históricos de modelos/reanálises da Open-Meteo, e não medições diretas de uma estação física.

O objetivo desta etapa é produzir uma referência simples, um Random Forest, métricas reproduzíveis e modelos que possam ser carregados novamente. Não inclui otimização extensa de parâmetros nem implementação operacional do produto.

## 2. Arquivos, dados e estado do projeto

Todos os caminhos relativos deste guia partem da raiz do repositório.

| Arquivo ou grupo | Estado e finalidade |
|---|---|
| `config.py` | Implementado. Define `WEATHER_FEATURES`, `WEATHER_TIMEZONE` e caminhos por `settings()`. |
| `scripts/prepare_weather.py` | Implementado. Prepara a tabela, gera metadados e protege arquivos de destino existentes. |
| `scripts/check_dataset.py` | Implementado. Verifica a configuração e os dados previstos pelo fluxo de conferência. |
| `scripts/train.py` | Implementado. Treina os modelos e registra os resultados da execução. |
| `scripts/evaluate_test.py` | Implementado. Avalia o conjunto de teste reservado e protege contra uma segunda avaliação registrada. |
| `tests/` | Implementado. Inclui testes de preparação, treinamento, auditoria, onboarding e outras verificações do projeto. |
| `requirements.txt` | Contém as dependências utilizadas pelo experimento, com versões fixadas. |
| `.env.example` | Modelo de configuração de caminhos. |
| `data/processed/weather_training.csv` | Tabela preparada, local e ignorada pelo Git. |
| `data/processed/weather_training.json` | Metadados da preparação, incluindo informações de proveniência e hipótese temporal. |
| `data/experiments/weather_20261027T173216Z/` | Artefatos de treinamento, validação e teste. |
| `docs/integration/` | Contratos propostos para a aplicação; não representam uma API já implementada. |
| `src/data/` e relatórios de EDA/auditoria | Materiais anteriores de investigação. Não precisam ser executados novamente para reproduzir as métricas já registradas. |
| `src/features/goes.py`, `pilot.py` e ferramentas de amostras GOES | Fora do fluxo atual de treinamento tabular. |

Não é necessário refatorar a estrutura do projeto nem adicionar infraestrutura de acompanhamento de experimentos. A preparação meteorológica existente deve ser reutilizada, sem recriar o alvo no treinamento.

### 2.1. Dados conferidos

- CSV original: **59.160 linhas**, abrangendo de 01/01/2020 00h a 30/09/2026 23h.
- Tabela preparada: **59.159 linhas e sete colunas**, com T até 30/09/2026 22h.
- Alvos negativos: **49.039**.
- Alvos positivos: **10.120**, aproximadamente 17,11%.
- Ausência de valores faltantes, timestamps duplicados e lacunas internas na tabela preparada conferida.
- Uma linha excluída por não haver registro em T+1h para definir seu alvo: T = 30/09/2026 23h.

A tabela contém, nesta ordem:

`time`, `temperature_2m`, `relative_humidity_2m`, `pressure_msl`, `cloud_cover`, `target_time`, `rain_next_hour`.

O hash SHA-256 do CSV original é:

`4e83a5248ee7008b0ea4dffb4bba28a80023b1892c4d38ff54cba41b6ee01f4c`

O hash SHA-256 da tabela preparada é:

`a3ea57e03c9b66e575cecbcc47a673a9af69c7c6aeeb5d6f07a18b0e69b609d3`

Esses hashes identificam as versões utilizadas. Se os arquivos recebidos tiverem hashes diferentes, não se deve presumir que sejam equivalentes sem verificar as diferenças.

## 3. Limitações científicas ainda pendentes

### 3.1. Semântica temporal da chuva

O arquivo original contém timestamps sem offset. A preparação associa o fuso `America/Sao_Paulo` e grava timestamps com offset. Durante o período considerado, 14h em Londrina corresponde a 17h UTC.

O alvo atual é `rain(T+1h) > 0 mm`, condicionado à hipótese de que `rain(u)` representa o intervalo `(u−1h,u]`. Sob essa hipótese, o valor às 15h representa a chuva acumulada entre 14h e 15h.

O código realiza a associação pelo timestamp exato T+1h, e não pela posição da próxima linha. Essa associação matemática foi conferida. Entretanto, a requisição original, a resposta bruta ou o código de exportação que confirmaria a semântica da variável não foram recuperados.

O fato de `rain` e `precipitation` terem os mesmos valores no arquivo não comprova, por si só, que sejam conceitualmente intercambiáveis ou que tenham a mesma janela temporal.

**Próxima ação:** solicitar ao produtor o material original da consulta ou exportação. Se possível, conferir uma virada de dia e uma sequência seco–chuva–seco desde a resposta original até o CSV. Uma consulta nova não comprova como a exportação antiga foi produzida.

Até que essa investigação seja concluída, os resultados devem ser apresentados como condicionados à hipótese temporal documentada.

### 3.2. Disponibilidade das entradas em T

O timestamp de uma observação indica sua referência temporal, não necessariamente quando ela foi publicada ou recebida. Mesmo os valores registrados em T podem ter sido produzidos posteriormente por modelos ou reanálises.

Não foram encontrados registros históricos suficientes para provar que as quatro entradas estavam disponíveis no momento em que a previsão teria sido emitida.

O experimento atual é, portanto, retrospectivo. Uma futura versão operacional precisará definir a fonte de dados e registrar os horários de referência, publicação e recebimento, além da versão das entradas.

Não se deve acrescentar um atraso arbitrário e tratá-lo como prova de disponibilidade operacional.

### 3.3. Integração com a aplicação

Não foi encontrada uma implementação de API em `src`, `scripts` ou nos arquivos de entrada usuais do projeto. Os documentos em `docs/integration/` descrevem contratos propostos.

A existência dos modelos treinados não significa que exista um endpoint de previsão. A integração, a fonte de dados em tempo real, o banco e a interface continuam fora do escopo desta entrega.

## 4. Protocolo experimental executado

O experimento utilizou a divisão cronológica proposta originalmente:

| Conjunto | Período | Linhas |
|---|---|---:|
| Treino | 2020–2024 | 43.847 |
| Validação | 2025 | 8.759 |
| Teste | Janeiro–setembro de 2026 | 6.551 |
| Excluídas nas fronteiras | Transições entre períodos | 2 |

As duas linhas excluídas são:

- T = 31/12/2024 23h, cujo alvo está em 01/01/2025 00h;
- T = 31/12/2025 23h, cujo alvo está em 01/01/2026 00h.

A regra aplicada exige que o `target_time` do conjunto anterior seja estritamente anterior ao início do conjunto seguinte. Assim, o alvo de uma linha não atravessa a fronteira temporal.

Os horários foram mantidos para divisão e auditoria, mas não fazem parte das quatro entradas do modelo.

### 4.1. Modelos e parâmetros

Foram treinadas duas referências:

1. **Baseline sempre seco:** prevê a classe `0` para todas as observações.
2. **Random Forest:** configuração fixa, sem busca extensa de parâmetros.

Parâmetros registrados do Random Forest:

- `n_estimators=100`
- `max_depth=8`
- `min_samples_leaf=10`
- `random_state=42`
- `n_jobs=1`
- `class_weight=None`

O limiar de decisão foi 0,5. Esse limiar de probabilidade não deve ser confundido com a definição do alvo observado, que utiliza `rain > 0 mm`.

O ajuste dos modelos utiliza somente o conjunto de treino. A validação serve para comparação; o teste é reservado para avaliação final.

### 4.2. Ambiente

Versões registradas no manifesto do experimento:

- Python 3.13.3
- NumPy 2.5.4
- pandas 3.0.1
- scikit-learn 1.9.1
- joblib 1.6.0

O arquivo `requirements.txt` contém as dependências fixadas. A instalação foi verificada em um ambiente virtual limpo criado com Python 3.13.3, e `python -m pip check` terminou sem conflitos.

Os 42 testes automatizados passaram nesse ambiente.

## 5. Resultados

As métricas foram calculadas separadamente na validação e no teste. Precisão, recall e F1 referem-se à classe positiva, isto é, à ocorrência de chuva.

### 5.1. Validação — 2025

| Métrica | Baseline sempre seco | Random Forest |
|---|---:|---:|
| Acurácia | 84,67% | 85,42% |
| Precisão da chuva | 0% | 53,53% |
| Recall da chuva | 0% | 37,23% |
| F1 da chuva | 0% | 43,92% |
| Chuvas observadas | 1.343 | 1.343 |
| Previsões positivas | 0 | 934 |

O Random Forest melhorou a acurácia e identificou parte das ocorrências de chuva. Ainda assim, deixou de detectar a maior parte dos casos positivos.

### 5.2. Teste — janeiro a setembro de 2026

| Métrica | Baseline sempre seco | Random Forest |
|---|---:|---:|
| Acurácia | 79,01% | 81,18% |
| Precisão da chuva | 0% | 59,15% |
| Recall da chuva | 0% | 33,38% |
| F1 da chuva | 0% | 42,68% |
| Chuvas observadas | 1.375 | 1.375 |
| Previsões positivas | 0 | 776 |

Matriz de confusão do Random Forest no teste, com linhas representando a classe real `[0, 1]` e colunas representando a classe prevista `[0, 1]`:

| | Prevê sem chuva | Prevê chuva |
|---|---:|---:|
| Sem chuva real | 4.859 | 317 |
| Chuva real | 916 | 459 |

Portanto, o modelo identificou 459 ocorrências positivas, deixou passar 916 e gerou 317 alarmes falsos.

O baseline sempre seco tem acurácia relativamente alta porque a maioria das observações é negativa. Entretanto, seu recall de chuva é zero, o que o torna inadequado se o objetivo for detectar ocorrências de chuva.

**Interpretação:** o fluxo técnico foi concluído e o Random Forest superou o baseline nas métricas principais apresentadas. O recall de 33,38% no teste mostra, porém, que o modelo deixou passar aproximadamente dois terços das ocorrências positivas. Não há uma meta mínima de desempenho aprovada, portanto não é possível declarar que o modelo esteja pronto para uso.

O teste cobre somente janeiro a setembro de 2026. Não representa o ano completo e não deve ser descrito como tal.

### 5.3. Integridade dos resultados

Os seguintes pontos foram verificados:

- Os arquivos de métricas e previsões de validação e teste existem.
- A validação contém 8.759 previsões e o teste contém 6.551.
- As colunas de previsão verificadas não apresentam valores ausentes.
- As divisões e contagens correspondem ao resumo registrado.
- O hash da tabela preparada corresponde ao hash registrado no manifesto.
- Os modelos salvos foram carregados novamente em um ambiente limpo e produziram previsões válidas em amostras de verificação.
- O manifesto registra `test_evaluated: true`.

A recarga e a verificação em amostras demonstram que os artefatos podem ser utilizados no ambiente testado. Não equivalem a uma garantia de previsões idênticas em todos os ambientes ou versões de bibliotecas.

**Não executar novamente o treinamento nem a avaliação do teste apenas para reproduzir os números deste guia.** Se alterações futuras forem selecionadas com base nos resultados desse teste, será necessária uma avaliação independente para confirmar as mudanças.

## 6. Caminhos e reprodução em outra máquina

O `config.py` define a raiz do projeto com base na localização do próprio arquivo. Os caminhos relativos são resolvidos a partir dessa raiz; variáveis de ambiente podem substituir os valores padrão.

Os caminhos relevantes são:

- `WEATHER_CSV_PATH`: CSV original, padrão `data/raw/dataset_weather.csv`.
- `WEATHER_TRAINING_PATH`: tabela preparada, padrão `data/processed/weather_training.csv`.

Na máquina em que o experimento foi executado, o CSV original estava em Downloads, enquanto a tabela preparada estava em `data/processed/`. Por isso, não se deve presumir que o caminho padrão do CSV original funcione em outra máquina.

O repositório não inclui automaticamente todos os arquivos de dados e artefatos experimentais. Para uma entrega reproduzível, compartilhar por canal apropriado:

- CSV original e documentação da fonte;
- tabela preparada e seu JSON de metadados, se a equipe optar por reutilizá-los;
- relatórios necessários para compreender as hipóteses;
- hashes e identificação do experimento;
- versão do código utilizada.

Não colocar caminhos pessoais no código e não incluir credenciais no `.env`.

Para conferir os caminhos configurados, sem treinar nem avaliar modelos:

```powershell
python -B -c "from config import settings; c=settings(); print('CSV:', c['csv'], c['csv'].is_file()); print('Tabela:', c['training'], c['training'].is_file())"
```

Para preparar a tabela do zero, primeiro confirmar que a fonte existe no caminho configurado. A preparação deve gerar uma nova tabela sem sobrescrever arquivos existentes. Se for necessário produzir uma nova versão, utilizar um destino diferente e atualizar `WEATHER_TRAINING_PATH` de forma correspondente.

A instalação e a execução dos testes podem ser conferidas em um ambiente virtual:

```powershell
py -3.13 -m venv .venv-validacao
.\.venv-validacao\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
python -B -m unittest discover -s tests -v
```

Esses comandos são para verificar o ambiente e os testes. Não executam o treinamento nem a avaliação final.

## 7. Artefatos do experimento

Os arquivos da execução estão em:

`data/experiments/weather_20261027T173216Z/`

| Arquivo | Finalidade |
|---|---|
| `baseline.joblib` | Modelo de referência sempre seco |
| `random_forest.joblib` | Random Forest treinado |
| `manifest.json` | Configuração, versões, hashes e estado da avaliação |
| `metrics_validation.json` | Métricas da validação |
| `predictions_validation.csv` | Previsões da validação para auditoria |
| `split_summary.json` | Contagens e períodos dos conjuntos |
| `metrics_test.json` | Métricas finais do teste |
| `predictions_test.csv` | Previsões do teste para auditoria |

Esses arquivos não devem ser tratados como dados públicos ou incluídos no Git à força. Para carregar modelos serializados, utilizar somente artefatos confiáveis e um ambiente compatível.

A preparação da tabela também mantém `weather_training.json`, que documenta informações como hash, versões e hipótese temporal.

## 8. Cuidados contra vazamento temporal

1. **O alvo futuro não entra em X.** `rain_next_hour` e `target_time` não são entradas do modelo.
2. **As entradas permanecem limitadas às quatro colunas definidas.** Não incluir variáveis adicionais sem revisar o protocolo.
3. **A divisão respeita o alvo.** Não basta separar somente pela data de T; o alvo precisa terminar antes da fronteira do conjunto seguinte.
4. **Não utilizar dados posteriores para preencher ausências.** A interpolação que utiliza observações futuras pode introduzir informação indisponível em T.
5. **Transformações futuras devem ser ajustadas somente no treino.** Caso sejam introduzidas imputação, seleção de variáveis ou escala, devem ser ajustadas no conjunto de treino e aplicadas sem reaprendizado à validação e ao teste.
6. **A disponibilidade operacional continua sendo uma limitação.** Um timestamp anterior a T não comprova que o dado estava publicado ou recebido até o instante da previsão.
7. **A EDA anterior examinou os dados históricos.** Portanto, o teste não deve ser descrito como totalmente desconhecido para todas as pessoas envolvidas. A reserva significa que ele não deve orientar novas escolhas de modelo a partir de agora.

## 9. Checklist de passagem de responsabilidade

### Entrega do projeto

- [ ] Compartilhar o repositório, este guia e os relatórios citados.
- [ ] Entregar o CSV original e a documentação da fonte por canal separado do Git.
- [ ] Informar os hashes do CSV original e da tabela preparada.
- [ ] Compartilhar os artefatos experimentais necessários à análise.
- [ ] Conferir e corrigir os caminhos na máquina de destino.
- [x] Registrar os parâmetros, versões, métricas e estado da avaliação final.
- [x] Registrar a limitação de cobertura do teste e as hipóteses temporais.

### Decisões e investigação ainda pendentes

- [ ] Confirmar com o produtor a janela temporal exata da variável `rain` no CSV original.
- [ ] Confirmar ou aceitar formalmente a hipótese temporal utilizada para o experimento.
- [ ] Definir uma fonte operacional e comprovar a disponibilidade das quatro entradas no momento da previsão.
- [ ] Definir os custos relativos de alarmes falsos e chuvas perdidas antes de ajustar o limiar.
- [ ] Definir critérios mínimos de desempenho antes de qualquer nova comparação de modelos.

### Execução técnica

- [x] Preparar e conferir a tabela meteorológica.
- [x] Implementar o treinamento e os testes correspondentes.
- [x] Validar o ambiente e as dependências em ambiente limpo.
- [x] Conferir as fronteiras e contagens da divisão cronológica.
- [x] Treinar o baseline e o Random Forest.
- [x] Registrar os resultados da validação.
- [x] Congelar a configuração e avaliar o teste uma vez.
- [x] Salvar e recarregar os modelos.
- [x] Verificar os artefatos e executar os 42 testes automatizados.
- [ ] Fazer uma avaliação independente caso alterações futuras sejam selecionadas com base no teste atual.

### Integração e uso operacional

- [ ] Definir a origem e o procedimento de obtenção das entradas para previsões operacionais.
- [ ] Implementar a API, caso seja aprovada como próxima etapa.
- [ ] Implementar persistência e interface, caso sejam necessárias ao MVP.
- [ ] Definir monitoramento e critérios de reavaliação antes de uso real.

Esses itens de integração não impedem reconhecer a conclusão do experimento retrospectivo. Eles delimitam o trabalho necessário para transformar o experimento em um serviço operacional.

## 10. Referências e alcance da revisão

- [Preparação didática](prepare_weather.md) e [código de preparação](../scripts/prepare_weather.py).
- [Auditoria](../reports/dataset_audit.md) e [relatório de EDA](../reports/eda/eda_report.md).
- [README original do dataset](dataset/README.md).
- [Relatório de proveniência e semântica temporal](../reports/temporal/source_provenance_report.md).
- [Revisão da tabela e dos períodos](../reports/project/revisao_tabela_e_periodos.md).
- [Proposta anterior de protocolo](../reports/protocol/protocol_proposal.md).
- [Contrato proposto para o backend](integration/backend.md).

Este guia registra o estado verificado em 27/10/2026. Os resultados são de um experimento retrospectivo com dados históricos e não comprovam disponibilidade operacional das entradas, nem desempenho em produção.

**Conclusão:** o primeiro ciclo técnico de treinamento foi concluído, com divisão cronológica, comparação entre baseline e Random Forest, avaliação final registrada, artefatos salvos e testes automatizados aprovados. O desempenho observado ainda apresenta limitações relevantes para a detecção de chuva. A confirmação da semântica temporal e a definição de uma fonte operacional permanecem como próximos passos científicos e de engenharia.