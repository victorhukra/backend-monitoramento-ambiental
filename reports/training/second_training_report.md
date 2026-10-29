Relatório do Segundo Treinamento do Modelo Meteorológico
Projeto: Protótipo de previsão meteorológica para Londrina/PR
Experimento: weather_20261029T140207Z
Código de referência:
Situação do teste: avaliação retrospectiva concluída em 29/10/2026, com 6.551 registros
Arquivo de métricas: data/experiments/weather_20261029T140207Z/metrics_test.json
Arquivo de previsões: data/experiments/weather_20261029T140207Z/predictions_test.csv
Base documental: relatório anterior, código v3 e resultados de teste fornecidos nesta atualização.
1. Objetivo
O segundo treinamento amplia a comparação inicial para classificar se haverá chuva na próxima hora. Além do baseline constante e do Random Forest original, o código inclui um baseline baseado na frequência das classes, regressão logística e uma variante do Random Forest com pesos de classe balanceados.

A versão v3 também calcula métricas probabilísticas, registra tabelas de limiares, compara a validação nos mesmos meses do teste e executa validação cruzada cronológica por ano. O objetivo é caracterizar o compromisso entre detectar chuva e emitir alarmes falsos, sem declarar um vencedor universal antes de definir os custos operacionais dos erros.

Os resultados de validação, recorte de mesmos meses e validação cruzada abaixo foram transcritos do relatório anterior e não foram recalculados independentemente, pois seus JSON/CSV não foram anexados. Já as métricas de teste da seção 7A foram fornecidas diretamente na atualização desta revisão.
2. Dados utilizados
O conjunto de dados foi fornecido pelo SENAI. A documentação do projeto descreve a fonte meteorológica como modelos/reanálises do Open-Meteo, e não como medições diretas de uma estação física.
Item	Informação
Local de interesse	Londrina/PR
Frequência	Horária
Linhas do CSV original	59.160
Linhas preparadas	59.159
Hash SHA-256 da tabela preparada	a3ea57e03c9b66e575cecbcc47a673a9af69c7c6aeeb5d6f07a18b0e69b609d3
Variáveis de entrada	temperature_2m, relative_humidity_2m, pressure_msl, cloud_cover
Alvo	rain_next_hour


Uma linha final é excluída durante a preparação porque não existe a observação de T+1h necessária para determinar o alvo.

O treinamento verifica as colunas exigidas, converte os timestamps para UTC para comparação consistente, rejeita timestamps duplicados, valida que o alvo contém apenas 0/1, verifica valores numéricos finitos e confirma que target_time = time + 1h. Não realiza imputação automática.
Definição temporal e limitação da fonte
O alvo indica precipitação maior que zero associada ao timestamp exato T+1h. A interpretação como chuva acumulada no intervalo (T, T+1h] depende da hipótese de que a variável original rain representa a precipitação acumulada na hora anterior ao seu timestamp. O código valida o alinhamento dos timestamps, mas não comprova a semântica da variável original.

O experimento é retrospectivo. Os timestamps das entradas não demonstram, por si só, que os valores estavam publicados ou disponíveis no instante em que uma previsão operacional teria sido emitida.
3. Separação temporal
A divisão é cronológica, sem embaralhamento:
Conjunto	Regra temporal	Linhas
Treino	Antes de 01/01/2025 00h, horário de São Paulo	43.847
Validação	Durante 2025, com alvo antes de 01/01/2026	8.759
Teste	A partir de 01/01/2026	6.551
Excluídas nas fronteiras	O alvo atravessaria o limite entre períodos	2


A regra exige que o alvo do registro permaneça dentro do período ao qual ele pertence. Isso evita que uma observação de treino ou validação utilize um alvo situado no período seguinte.

O teste de janeiro a setembro de 2026 já havia sido avaliado no primeiro treinamento, em 27/10/2026. Nesta atualização, a avaliação retrospectiva com a versão v3 foi concluída para comparação e está registrada abaixo. Isso não transforma o período em um teste independente: ele já foi usado anteriormente e não deve orientar novas escolhas de modelo, variáveis ou limiares. O código v3 mantém --evaluate-test como opção explícita e registra o estado no manifesto.
4. Modelos comparados
O código v3 treina cinco modelos:
1. baseline — DummyClassifier constante que sempre prevê a classe 0 (sem chuva).
2. random_forest — Random Forest original, mantido para comparação com o primeiro treinamento.
3. baseline_prior — DummyClassifier(strategy='prior'), que usa a distribuição das classes do treino para estimar probabilidades.
4. logistic — regressão logística precedida por padronização (StandardScaler) em um pipeline.
5. random_forest_balanced — Random Forest com class_weight='balanced_subsample', para dar mais peso à classe minoritária.
Os dois Random Forests usam 100 árvores, profundidade máxima 8, mínimo de 10 amostras por folha e random_state=42. O modelo original usa n_jobs=1 e class_weight=None; o balanceado usa n_jobs=-1 e pesos balanceados por subamostra. A regressão logística usa max_iter=1000 e random_state=42.

As quatro variáveis meteorológicas são as únicas entradas. target_time e rain_next_hour não são fornecidas como atributos de entrada.
5. Resultados principais na validação de 2025
O relatório recebido apresenta as métricas abaixo no limiar de classificação de 0,50.
Modelo	Acurácia	Precisão da chuva	Recall da chuva	F1 da chuva
Baseline constante	84,667%	0,000%	0,000%	0,000%
Random Forest original	85,421%	53,533%	37,230%	43,917%
baseline_prior	84,667%	0,000%	0,000%	0,000%
Regressão logística	83,286%	43,330%	29,263%	34,933%
Random Forest balanceado	75,031%	36,227%	82,651%	50,374%


A acurácia não deve ser usada isoladamente, pois a classe sem chuva é majoritária. O Random Forest original tem a maior acurácia nesta tabela. O Random Forest balanceado apresenta o maior recall e F1, identificando mais eventos de chuva, mas com mais alarmes falsos e menor precisão.
Matrizes de confusão reportadas
A ordem é [[verdadeiros negativos, falsos positivos], [falsos negativos, verdadeiros positivos]].

Random Forest original
[[6982, 434],
 [ 843, 500]]
Random Forest balanceado
[[5462, 1954],
 [ 233, 1110]]
Na validação, o Random Forest balanceado reduz os falsos negativos de 843 para 233, mas aumenta os falsos positivos de 434 para 1.954. A escolha entre esses modelos depende do custo relativo de deixar de detectar chuva e de emitir alertas incorretos.
6. Métricas probabilísticas no recorte de mesmos meses
O código seleciona, dentro da validação de 2025, os meses que correspondem aos meses presentes no teste de 2026. Como o teste cobre janeiro a setembro, esse recorte corresponde a janeiro a setembro de 2025, não de 2026. O relatório anterior dizia “janeiro a setembro de 2026” ao descrever esse subconjunto de validação; essa formulação foi corrigida aqui.

O relatório recebido registra 6.552 linhas nesse recorte e prevalência de chuva de 13,20%.
Modelo	Brier (menor é melhor)	Log loss (menor é melhor)	ROC-AUC (maior é melhor)	PR-AUC (maior é melhor)
Random Forest original	0,08927	0,27630	0,86964	0,43790
Regressão logística	0,09544	0,29604	0,84920	0,37728
Random Forest balanceado	0,14327	0,41139	0,86915	0,43823


Nessas métricas, o Random Forest original tem os menores valores de Brier e log loss, enquanto os dois Random Forests têm ROC-AUC semelhante. A PR-AUC do modelo balanceado é ligeiramente maior no recorte, mas isso não significa que ele seja melhor em todos os critérios. Métricas de probabilidade e métricas de classificação no limiar 0,50 respondem a perguntas diferentes.
7. Validação cruzada cronológica
A versão v3 implementa validação temporal por ano, com períodos de validação em 2023, 2024 e 2025. Cada período é previsto por um modelo treinado apenas com dados anteriores àquele período. O código limita essa análise aos registros cujo alvo ocorre antes de 2026.

Médias e desvios-padrão reportados entre os períodos:
Modelo	PR-AUC	ROC-AUC	Brier	Precisão a 0,50	Recall a 0,50	F1 a 0,50
Random Forest original	0,51596 ± 0,02805	0,87097 ± 0,00790	0,10271 ± 0,00687	0,54347 ± 0,01369	0,47389 ± 0,07745	0,50283 ± 0,04593
Regressão logística	0,43752 ± 0,02549	0,85042 ± 0,00582	0,10911 ± 0,00621	0,48963 ± 0,04030	0,39992 ± 0,08332	0,43789 ± 0,06487
Random Forest balanceado	0,51837 ± 0,02925	0,87080 ± 0,00778	0,16405 ± 0,01857	0,38300 ± 0,01717	0,87119 ± 0,04315	0,53172 ± 0,02003


Na validação temporal, o Random Forest balanceado tem a maior média de recall e F1 entre os três modelos mostrados. O Random Forest original apresenta maior precisão e melhor Brier. A regressão logística não supera os Random Forests nas métricas apresentadas.

Esses números são os valores transcritos no relatório fornecido e devem ser conferidos contra rolling_cv.json antes de uma publicação formal, pois o arquivo de resultados não foi anexado para auditoria independente.
7A. Avaliação retrospectiva no teste — janeiro a setembro de 2026
A avaliação retrospectiva foi concluída para 6.551 registros, com 1.375 ocorrências de chuva e 5.176 sem chuva (prevalência positiva de 20,99%). Os arquivos informados foram gravados em data/experiments/weather_20261029T140207Z/metrics_test.json e predictions_test.csv.
Métricas probabilísticas
Modelo	Brier ↓	Log loss ↓	ROC-AUC ↑	PR-AUC ↑
Baseline constante	0,20989	7,24940	0,50000	0,20989
Random Forest original	0,12443	0,37631	0,84536	0,53333
baseline_prior	0,16752	0,51948	0,50000	0,20989
Regressão logística	0,13235	0,40187	0,82300	0,47250
Random Forest balanceado	0,16243	0,47069	0,84750	0,53790


O Random Forest original apresenta os menores Brier e log loss entre os modelos, sugerindo probabilidades mais próximas dos rótulos observados segundo essas métricas. O Random Forest balanceado tem os maiores ROC-AUC e PR-AUC, por pequena margem sobre o original, indicando boa capacidade de ordenar os casos, mas isso não garante a melhor calibração nem o melhor resultado em um limiar específico.
Classificação com limiar 0,50
Modelo	Acurácia	Precisão chuva	Recall chuva	F1 chuva	Prevê chuva
Baseline constante	79,01%	0,00%	0,00%	0,00%	0
Random Forest original	81,18%	59,15%	33,38%	42,68%	776
baseline_prior	79,01%	0,00%	0,00%	0,00%	0
Regressão logística	79,24%	51,38%	20,36%	29,17%	545
Random Forest balanceado	74,48%	44,17%	81,82%	57,37%	2.547


O Random Forest original é o mais acurado nesse limiar e tem a maior precisão entre os modelos que emitem previsões positivas de forma útil, mas identifica somente cerca de um terço dos eventos de chuva. O Random Forest balanceado identifica 1.125 das 1.375 ocorrências, mas gera 1.422 falsos positivos. A acurácia mais baixa do modelo balanceado reflete esse aumento de alarmes. Os baselines não detectam chuva no limiar 0,50.
Métricas nos limiares provisórios selecionados na validação
Os limiares abaixo foram escolhidos na validação, não no teste. Aplicá-los ao teste é uma comparação retrospectiva útil, mas não uma validação independente; além disso, como o período de teste já foi usado no primeiro treinamento, estes resultados não devem ser usados para escolher o modelo final.
Modelo	Limiar	Acurácia	Precisão chuva	Recall chuva	F1 chuva	Prevê chuva
Baseline constante	0,05	79,01%	0,00%	0,00%	0,00%	0
Random Forest original	0,30	79,65%	51,27%	61,82%	56,05%	1.658
baseline_prior	0,05	20,99%	20,99%	100,00%	34,70%	6.551
Regressão logística	0,23	77,32%	47,24%	69,16%	56,14%	2.013
Random Forest balanceado	0,68	80,46%	53,19%	57,60%	55,31%	1.489


No limiar provisório, o Random Forest original obtém recall maior e F1 de 56,05%, enquanto a regressão logística chega a F1 de 56,14% com recall de 69,16%, porém emitindo 2.013 previsões positivas. O Random Forest balanceado fica com acurácia de 80,46% e F1 de 55,31%. As diferenças são pequenas e refletem compromissos distintos, não uma superioridade universal.

O baseline_prior prevê todos os registros como chuva quando aplicado o limiar 0,05, pois sua probabilidade constante estimada é maior que esse limiar. Isso produz recall de 100%, mas precisão igual à prevalência (20,99%) e acurácia de apenas 20,99%; não representa um detector útil. Já o baseline constante atribui probabilidade zero à chuva e continua prevendo todos os casos como secos.

Matriz de confusão do Random Forest original no limiar 0,50 ([[VN, FP], [FN, VP]]):
[[4859, 317],
 [ 916, 459]]
Matriz de confusão do Random Forest original no limiar 0,30:
[[4368, 808],
 [ 525, 850]]
Reduzir o limiar do Random Forest original de 0,50 para 0,30 aumenta os verdadeiros positivos de 459 para 850 e reduz os falsos negativos de 916 para 525, mas aumenta os falsos positivos de 317 para 808. Isso ilustra diretamente o compromisso entre detectar mais chuva e emitir mais alertas incorretos.

Interpretação e ressalva: os resultados do teste devem ser apresentados como avaliação retrospectiva de um período previamente utilizado, não como estimativa final imparcial de generalização. Para uma avaliação final, congele modelo e limiar com base no treino/validação e use um período novo, ainda não consultado.
8. Limiares de decisão
A versão v3 avalia limiares de 0,05 a 0,95 em passos de 0,01 e registra uma tabela de precisão, recall, F1 e quantidade de previsões positivas. O limiar provisório é escolhido na validação maximizando F-beta; por padrão, beta=1, equivalente a maximizar F1.
Modelo	Limiar provisório reportado
Baseline constante	0,05
Random Forest original	0,30
baseline_prior	0,05
Regressão logística	0,23
Random Forest balanceado	0,68


Esses limiares não são decisões operacionais finais. O limiar e suas métricas são escolhidos e avaliados no mesmo conjunto de validação, o que tende a produzir uma estimativa otimista. A própria versão v3 registra essa ressalva no manifesto.

Os limiares de 0,05 atribuídos aos modelos constantes não devem ser interpretados como calibração útil: como esses modelos não oferecem discriminação comparável à dos modelos treinados, a escolha pode resultar de empate entre limiares com F1 zero. O código deve ser entendido como gerador de análises para apoiar uma decisão, não como definidor automático de uma política de alertas.

Antes de escolher um limiar definitivo, é necessário decidir o custo relativo de falsos alarmes e de chuva não detectada. Para privilegiar a detecção de chuva, pode-se considerar um beta maior que 1, mas essa escolha deve ser justificada pelo uso pretendido.
9. Importância das variáveis
O código calcula importância por permutação na validação para random_forest, random_forest_balanced e logistic, usando a queda de PR-AUC como critério e cinco repetições. Os resultados são salvos em feature_importance_validation.json.

O relatório recebido não contém os valores individuais por variável. Portanto, não é possível afirmar, com base nos materiais fornecidos, qual variável foi a mais importante. Importância por permutação mede a influência da variável no desempenho observado; não comprova causalidade meteorológica.
10. Artefatos do experimento
Diretório reportado:

data/experiments/weather_20261029T140207Z/

O código v3 prevê os seguintes arquivos:
Arquivo	Finalidade
baseline.joblib	Baseline sempre sem chuva
random_forest.joblib	Random Forest original
baseline_prior.joblib	Baseline por prior
logistic.joblib	Pipeline de regressão logística
random_forest_balanced.joblib	Random Forest balanceado
manifest.json	Ambiente, parâmetros, modelos, limiares e estado do teste
split_summary.json	Contagens, períodos, prevalência e hash da tabela de entrada
metrics_validation.json	Métricas de classificação no limiar padrão
metrics_validation_extended.json	Métricas probabilísticas, limiares e recorte de mesmos meses
rolling_cv.json	Resultados da validação cruzada cronológica
feature_importance_validation.json	Importância por permutação
predictions_validation.csv	Rótulos, probabilidades e previsões da validação


metrics_test.json e predictions_test.csv foram gerados nesta avaliação retrospectiva mediante a opção --evaluate-test. O manifesto do experimento original pode ter registrado test_evaluated: false antes dessa execução; o estado atual deve ser confirmado no manifesto atualizado. A geração desses arquivos não torna o teste de 2026 independente, pois o período já havia sido usado no primeiro treinamento.

O código também registra o hash SHA-256 da tabela de entrada e as versões de Python, pandas, NumPy, scikit-learn e joblib. Como os artefatos do experimento não foram anexados nesta revisão, confirme os arquivos reais no diretório antes de afirmar que todos foram gerados com sucesso.
11. Avaliação técnica do train_v3.py
Melhorias em relação ao train.py
- mantém as funções evaluate, baseline e random_forest, preservando a estrutura das métricas principais;
- adiciona baseline_prior, regressão logística e Random Forest balanceado;
- inclui PR-AUC, ROC-AUC, Brier score e log loss;
- gera tabelas de limiares, em vez de fixar uma política operacional;
- compara os meses de validação com os meses abrangidos pelo teste;
- implementa validação cruzada cronológica por ano;
- calcula importância por permutação;
- registra no manifesto que o teste de janeiro a setembro de 2026 já foi usado.
Cuidados e limitações
- o teste não é avaliado por padrão, o que é apropriado dado o uso anterior desse período;
- as métricas e limiares selecionados na validação são resultados de desenvolvimento, não uma avaliação independente;
- o limiar provisório é otimizado e avaliado no mesmo conjunto, portanto pode ser otimista;
- a seleção de limiar para modelos sem discriminação, como os baselines, pode produzir valores pouco informativos;
- o script permite --evaluate-test por compatibilidade, mas o aviso não impede tecnicamente a execução; a proteção depende também do procedimento da equipe;
- a validação cruzada por ano exige dados suficientes e duas classes em cada divisão; anos que não atendem aos requisitos são registrados como ignorados;
- não há comprovação de que os dados históricos de entrada estivessem disponíveis em tempo real;
- a semântica temporal de rain ainda precisa de confirmação documental.
12. Conclusão e próximos passos
O segundo treinamento amplia de forma relevante a análise em relação ao primeiro. Os números reportados indicam um compromisso claro: o Random Forest original apresenta maior acurácia e melhores métricas de Brier/log loss, enquanto o Random Forest balanceado aumenta o recall e o F1 à custa de mais falsos positivos.

Não existe um vencedor universal sem definir o objetivo do produto. Se deixar de detectar chuva for muito custoso, o modelo balanceado merece investigação; se alarmes falsos forem especialmente custosos e a qualidade das probabilidades for prioritária, o Random Forest original pode ser mais adequado. Essa conclusão é provisória e restrita aos resultados de validação apresentados.

Antes de uma decisão final:
1. conferir os valores deste relatório com os JSON/CSV do diretório weather_20261029T140207Z;
2. definir critérios de desempenho e o custo relativo de falsos positivos e falsos negativos;
3. confirmar a semântica temporal de rain com a fonte original;
4. definir uma fonte operacional e comprovar quando as quatro entradas ficam disponíveis;
5. evitar reutilizar o teste de 2026 para escolher modelos ou limiares;
6. obter um período de teste novo e independente quando houver uma versão congelada para avaliação final.
Estado final: treinamento v3 e avaliação retrospectiva de teste concluídos; o Random Forest original apresenta melhores Brier/log loss, enquanto o Random Forest balanceado tem maior recall e F1 no limiar 0,50. Nos limiares provisórios, RF original, regressão logística e RF balanceado apresentam F1 próximos (aprox. 55–56%). O período de teste já foi usado anteriormente, portanto a comparação não substitui uma avaliação final independente. Prontidão operacional não demonstrada.