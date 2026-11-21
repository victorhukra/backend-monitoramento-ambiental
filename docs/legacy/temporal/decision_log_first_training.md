# Registro de decisões metodológicas — primeiro treinamento

**Data:** 27/10/2026
**Experimento:** `data/experiments/weather_20261027T173216Z/`

## 1. Escopo

O experimento utiliza exclusivamente dados meteorológicos tabulares. As imagens de satélite e o fluxo GOES ficam fora do escopo deste primeiro treinamento.

## 2. Variáveis

**Entradas:**
- `temperature_2m`
- `relative_humidity_2m`
- `pressure_msl`
- `cloud_cover`

**Alvo:** `rain_next_hour`, construído a partir da variável `rain` para representar a ocorrência de chuva na hora seguinte.

**Ressalva:** a interpretação temporal da variável `rain` ainda não foi confirmada com a procedência exata da exportação. Portanto, o significado do alvo permanece condicionado a essa confirmação.

## 3. Preparação e divisão temporal

A tabela processada contém 59.159 registros. Um registro foi excluído por não possuir o horário futuro necessário.

A divisão cronológica implementada utiliza:
- Treinamento: registros anteriores ao limite de 2025.
- Validação: registros de 2025.
- Teste: registros a partir de 2026.

Dois registros de fronteira foram excluídos para evitar que o horário-alvo ultrapassasse os limites definidos para cada partição.

## 4. Modelos

Foram treinados:
- modelo de referência constante, que sempre prevê ausência de chuva.
- Random Forest com 100 árvores, profundidade máxima 8, mínimo de 10 amostras por folha e `random_state=42`.

O limiar de classificação utilizado é 0,5.

## 5. Avaliação

A validação contém 8.759 registros. O Random Forest obteve:
- Acurácia: aproximadamente 85,42%.
- Precisão da classe de chuva: aproximadamente 53,53%.
- sensibilidade da classe de chuva: aproximadamente 37,23%.
- F1 da classe de chuva: aproximadamente 43,92%.

O modelo de referência obteve acurácia de aproximadamente 84,67%, mas não identificou ocorrências de chuva.

Esses resultados são retrospectivos e não demonstram, por si só, capacidade de previsão operacional.

## 6. Reprodutibilidade

O manifesto do experimento registra versões das bibliotecas, hiperparâmetros, hashes dos arquivos de dados e o status da avaliação do teste.

Os modelos salvos foram recarregados e suas previsões de validação foram reproduzidas. A suíte de testes automatizados passou em 42 testes.

O conjunto de teste permanece reservado e não foi avaliado.

## 7. Pendências

1. Confirmar a origem exata dos dados e os parâmetros da consulta ou exportação.
2. Confirmar o intervalo temporal representado pela variável `rain`.
3. Verificar se todas as entradas estavam disponíveis no instante em que uma previsão seria emitida.
4. Após resolver as questões anteriores e congelar as escolhas metodológicas, avaliar o conjunto de teste uma única vez.

Até que essas pendências sejam resolvidas, o modelo deve ser descrito como um experimento retrospectivo, e não como um sistema de previsão operacional validado.

## 8. Decisão de prosseguimento do experimento retrospectivo

**Data:** 27/10/2026

Foi aceita provisoriamente a continuidade do primeiro experimento retrospectivo sob a hipótese de que `rain(u)` representa a precipitação acumulada no intervalo `(u−1h, u]`. O alvo permanece definido como `rain(T+1h) > 0 mm`.

A origem técnica exata do CSV, os parâmetros da exportação e eventuais transformações anteriores à entrega ainda não foram confirmados. Esta decisão não atribui autoria ou procedência definitiva aos dados e não comprova que as entradas estavam disponíveis no instante de emissão de uma previsão.

Para concluir este ciclo, serão mantidos os dados, as entradas, a divisão cronológica, os parâmetros do Random Forest e o limiar de classificação já registrados. O conjunto de teste será avaliado uma única vez, sem selecionar ou ajustar o modelo com base nos resultados dessa avaliação.

Os resultados serão apresentados como avaliação retrospectiva, sem alegação de desempenho operacional validado. A hipótese temporal e a disponibilidade das entradas continuam sendo limitações a investigar.
