Relatório do Primeiro Treinamento do Modelo Meteorológico
Projeto: Protótipo de previsão meteorológica para Londrina/PR
Data do experimento: 27/10/2026
Experimento: weather_20261027T173216Z
Código de referência: scripts/train.py
Fonte documental: README_first_training.md
1. Objetivo e escopo
O primeiro treinamento estabelece uma referência inicial para classificar se haverá chuva na próxima hora em Londrina, utilizando quatro variáveis meteorológicas observadas no instante de referência T.

O alvo é rain_next_hour:
- 0: não houve chuva no período-alvo;
- 1: houve chuva no período-alvo.
O código treina dois classificadores: um modelo de referência constante que sempre prevê ausência de chuva e um RandomForestClassifier. O limiar de decisão usado nas métricas de classificação é o padrão do modelo, equivalente a 0,5 para a probabilidade da classe positiva.

Este é um experimento retrospectivo. Ele não implementa uma API, banco de dados, interface ou serviço de previsão em tempo real. Imagens GOES não fazem parte deste fluxo e não são pré-requisito.
2. Dados utilizados
O conjunto de dados foi fornecido pelo SENAI. A documentação do projeto descreve os dados como provenientes de modelos/reanálises meteorológicas do Open-Meteo, não como medições diretas de uma estação meteorológica.
Item	Informação
Local de interesse	Londrina/PR
Frequência	Horária
Linhas do CSV original	59.160
Linhas da tabela preparada	59.159
Classes negativas	49.039
Classes positivas	10.120 (aprox. 17,11%)
Hash SHA-256 da tabela preparada	a3ea57e03c9b66e575cecbcc47a673a9af69c7c6aeeb5d6f07a18b0e69b609d3


A tabela preparada contém time, as quatro entradas meteorológicas, target_time e rain_next_hour. Uma linha final foi excluída na preparação porque não havia observação em T+1h para construir o alvo.
Variáveis de entrada
Variável	Descrição
temperature_2m	Temperatura a 2 metros
relative_humidity_2m	Umidade relativa a 2 metros
pressure_msl	Pressão atmosférica ao nível médio do mar
cloud_cover	Cobertura de nuvens


Definição temporal do alvo
A preparação associa o alvo ao timestamp exato T+1h, com valor positivo quando rain > 0 mm. A interpretação meteorológica depende da hipótese de que rain(u) representa a precipitação acumulada no intervalo (u−1h, u].

O código de treinamento confirma que target_time = time + 1h, mas não consegue comprovar sozinho a semântica da variável rain na exportação original. Essa hipótese continua pendente de confirmação com a documentação ou os dados brutos do produtor.
3. Separação cronológica
O código divide os registros por tempo, sem embaralhamento aleatório. Além de separar pelo timestamp de entrada, exige que o alvo permaneça antes do limite do período correspondente.
Conjunto	Regra temporal	Linhas
Treino	Antes de 01/01/2025 00h (horário de São Paulo)	43.847
Validação	Durante 2025, com alvo antes de 01/01/2026	8.759
Teste	A partir de 01/01/2026	6.551
Excluídas nas fronteiras	Alvo atravessaria a fronteira temporal	2


As duas linhas de fronteira são excluídas para evitar que o alvo de uma observação do período anterior atravesse para o período seguinte. O teste cobre janeiro a setembro de 2026, não o ano completo.
4. Modelos e configuração
modelo de referência
DummyClassifier(strategy='constant', constant=0): prevê ausência de chuva em todas as observações. Serve como referência simples, mas não é útil para detectar chuva, pois sua sensibilidade da classe positiva é zero.
Random Forest
O modelo principal utiliza os seguintes parâmetros:
Parâmetro	Valor
n_estimators	100
max_depth	8
min_samples_leaf	10
random_state	42
n_jobs	1
class_weight	None


O modelo é ajustado apenas no conjunto de treino. A validação é usada para comparação e o teste é avaliado separadamente, mediante solicitação explícita ao script (--evaluate-test).
5. Resultados na validação — 2025
Métrica	modelo de referência sempre seco	Random Forest
Acurácia	84,67%	85,42%
Precisão da chuva	0,00%	53,53%
sensibilidade da chuva	0,00%	37,23%
F1 da chuva	0,00%	43,92%
Chuvas observadas	1.343	1.343
Previsões positivas	0	934


O Random Forest supera o modelo de referência em acurácia e detecta parte das ocorrências positivas, mas deixa passar a maior parte dos eventos de chuva. Como a classe sem chuva é majoritária, a acurácia sozinha não é suficiente para avaliar o valor do modelo.
6. Resultados no teste — janeiro a setembro de 2026
O README_first_training.md registra que o conjunto de teste foi avaliado na execução original.
Métrica	modelo de referência sempre seco	Random Forest
Acurácia	79,01%	81,18%
Precisão da chuva	0,00%	59,15%
sensibilidade da chuva	0,00%	33,38%
F1 da chuva	0,00%	42,68%
Chuvas observadas	1.375	1.375
Previsões positivas	0	776


Matriz de confusão do Random Forest, com linhas para a classe real [0, 1] e colunas para a classe prevista [0, 1]:
	Prevê sem chuva	Prevê chuva
Sem chuva real	4.859	317
Chuva real	916	459


O modelo detectou 459 ocorrências de chuva, deixou passar 916 e gerou 317 alarmes falsos. A sensibilidade de 33,38% indica que aproximadamente dois terços dos casos positivos não foram identificados.

Cuidado com o teste: esse período já foi usado para avaliação. Não deve orientar novas escolhas de modelo ou limiar; se os resultados do teste forem usados para desenvolver uma nova versão, será necessário obter uma avaliação independente.
7. Artefatos registrados
A execução documentada está em data/experiments/weather_20261027T173216Z/.
Arquivo	Finalidade
modelo de referência.joblib	Classificador que sempre prevê ausência de chuva
random_forest.joblib	Random Forest treinado
manifest.json	Versões, parâmetros e informações do experimento
split_summary.json	Contagens e regras da separação temporal
metrics_validation.json	Métricas da validação
predictions_validation.csv	Probabilidades e previsões da validação
metrics_test.json	Métricas do teste, quando avaliado
predictions_test.csv	Previsões do teste, se geradas pelo fluxo de avaliação


O código calcula SHA-256 da tabela de entrada e grava versões de Python, pandas, NumPy, scikit-learn e joblib no manifesto. O README informa que os modelos foram recarregados e os artefatos conferidos, e que 42 testes automatizados passaram no ambiente limpo descrito.
8. Avaliação técnica do train.py
Pontos positivos observados no código:
- valida a presença das colunas obrigatórias, timestamps, duplicatas, alvo binário e valores finitos;
- confirma que target_time corresponde exatamente a time + 1h;
- realiza divisão cronológica e verifica que os conjuntos não compartilham registros;
- limita as entradas às quatro variáveis meteorológicas;
- salva modelos, métricas, probabilidades, previsões, manifesto e resumo da divisão;
- mantém a avaliação do teste opcional, em vez de executá-la automaticamente;
- impede que a pasta de saída sobrescreva um experimento existente e exige que fique dentro de data/experiments.
Limitações e pontos de atenção:
- as métricas principais dependem do limiar padrão de 0,5 e não exploram outros compromissos entre precisão e sensibilidade;
- o relatório original não inclui métricas probabilísticas como PR-AUC, ROC-AUC, Brier score ou log loss;
- o modelo de referência constante é útil como referência, mas não como detector de chuva;
- a qualidade retrospectiva não comprova que as entradas estavam disponíveis no instante real da previsão;
- a definição temporal de rain continua sendo uma hipótese que precisa de confirmação externa;
- a avaliação do teste já realizada significa que esse período não deve ser tratado como completamente intocado para decisões futuras.
9. Conclusão
O primeiro treinamento concluiu o fluxo técnico inicial: validação dos dados, divisão cronológica, treinamento de um modelo de referência e de um Random Forest, registro de métricas e salvamento dos artefatos. Na validação e no teste documentados, o Random Forest superou o modelo de referência em acurácia e identificou parte dos eventos de chuva.

O desempenho ainda não sustenta afirmar que o modelo está pronto para uso operacional. A sensibilidade no teste foi de 33,38%, e permanecem pendentes a confirmação da semântica temporal da precipitação, a comprovação da disponibilidade das entradas em tempo real e a definição de critérios mínimos de desempenho.

O segundo treinamento amplia a análise com modelos adicionais, métricas probabilísticas, validação cruzada temporal e estudo de limiares; seus resultados são documentados separadamente em second_training_report.md.