## Atualização do MVP — 05/11/2026

O MVP meteorológico evoluiu da preparação da tabela para seis execuções documentadas de treinamento e uma avaliação aninhada v7. A v6 compara três estratégias de pesos de classe e combinações ponderadas; a v7 ajusta calibração, pesos e limiar só em anos anteriores à partição avaliada. O escopo continua sendo classificar a ocorrência de chuva na próxima hora em Londrina/PR, com base em dados meteorológicos horários. O projeto permanece experimental e retrospectivo: ainda não há API, banco de dados, interface ou serviço de previsão em tempo real.

### Dados e objetivo

- Base preparada: `data/processed/weather_training.csv`, com **59.159 registros**.
- Classes: **10.120 positivas** (aprox. 17,11%) e **49.039 negativas**.
- Entradas originais: `temperature_2m`, `relative_humidity_2m`, `pressure_msl` e `cloud_cover`.
- Alvo: `rain_next_hour`, associado ao timestamp `T+1h`.
- O conjunto foi fornecido pelo SENAI; a documentação identifica modelos/reanálises do Open-Meteo como fonte meteorológica, sem comprovar que o SENAI tenha realizado a coleta original.

A interpretação de `rain` como precipitação acumulada na hora anterior ao timestamp ainda depende de confirmação documental na origem. Também não está comprovado que as quatro entradas históricas estariam disponíveis no instante de uma previsão operacional.

### Treinamentos documentados

| Etapa | Experimento / data | Escopo e situação |
|---|---|---|
| Primeiro treinamento | `weather_20261027T173216Z` — 27/10/2026 | modelo de referência constante e Random Forest original; validação e teste retrospectivo concluídos. |
| Segundo treinamento | `weather_20261029T140207Z` — 29/10/2026 | Cinco modelos, métricas probabilísticas, tabelas de limiares, recorte de mesmos meses e validação cruzada temporal; avaliação retrospectiva do teste concluída. |
| Terceira execução | `weather_20261031T112237Z` — 31/10/2026 | Cinco modelos, Random Forests com 500 árvores e sem limite de profundidade; validação e validação cruzada temporal documentadas. O teste de 2026 não foi avaliado nesta rodada. |
| Quarta execução — v4 | `weather_20261103T190835Z` — 03/11/2026 | Cinco modelos, sete atributos, seleção de limiar na validação e validação cruzada temporal; manifesto/joblibs conferidos. Teste de 2026 preservado. Relatório: `reports/training/fourth_training_report.md`. |
| Quinta execução — v5 | `weather_v5_20261104T120000Z` — 04/11/2026 | 12 configurações, quatro anos cronológicos, três sementes e bootstrap mensal. Quatro joblibs congelados foram avaliados uma vez no período de 2026; os resultados não foram usados na seleção e são retrospectivos. Métricas, previsões e manifesto registrados. Relatório: `reports/training/fifth_training_report.md`. |
| Sexta execução — v6 | `weather_v6_20261105T120000Z` — 05/11/2026 | Três Random Forests (original, balanced e balanced_subsample) e quatro combinações ponderadas; quatro partições cronológicas, três sementes, previsões fora da amostra, três joblibs e manifesto. O teste de 2026 não foi avaliado nem usado para seleção ou treinamento nesta versão. Relatório: `reports/training/sixth_training_report.md`. |
| Avaliação aninhada — v7 | `weather_v7_reassessment_20261105T` — 05/11/2026 | Reavaliação com 180 resultados em partições externas de 2023–2025; comparação de calibração sem ajuste, sigmoide e isotônica, com seleção interna de pesos e limiares para quatro cenários de custo FN:FP. Sem uso do teste de 2026 e sem modelo final selecionado. Relatório: `reports/training/seventh_training_report.md`. |

### Resultados e interpretação

Na primeira execução, o Random Forest original obteve no teste retrospectivo (6.551 registros) acurácia de 81,18%, precisão de 59,15%, sensibilidade de 33,38% e F1 de 42,68%. Identificou 459 das 1.375 ocorrências de chuva, deixou passar 916 e gerou 317 falsos positivos.

Na segunda execução, a comparação dos cinco modelos mostrou compromissos diferentes. No limiar 0,50, o Random Forest original teve acurácia de 81,18% e precisão de 59,15%, mas sensibilidade de 33,38%. O Random Forest balanceado teve sensibilidade de 81,82% e F1 de 57,37%, à custa de 1.422 falsos positivos. As métricas probabilísticas favoreceram o Random Forest original em Brier e log loss, enquanto o balanceado obteve PR-AUC e ROC-AUC ligeiramente maiores.

Na terceira execução, a validação de 2025 indicou sensibilidade de 0,662 e F1 de 0,512 para o Random Forest balanceado, contra sensibilidade de 0,366 e F1 de 0,416 para o Random Forest original. O relatório recomenda considerar o balanceado quando a prioridade for reduzir falsos negativos, mas ressalta o custo operacional e a necessidade de avaliação adicional.

**Não há vencedor definitivo.** A escolha depende do custo de falsos negativos e falsos positivos, da calibração das probabilidades e do comportamento em um período independente. O teste de janeiro a setembro de 2026 já foi consultado nas duas primeiras execuções; não deve ser reutilizado para escolher modelos, atributos ou limiares.

Na quarta execução (v4), no limiar 0,50 da validação de 2025, o Random Forest original teve acurácia de 88,62%, precisão de 68,44%, sensibilidade de 47,80% e F1 de 56,29%. O Random Forest balanceado teve acurácia de 86,49%, precisão de 54,74%, sensibilidade de 68,80% e F1 de 60,97%. Na validação cruzada por anos, o balanceado teve sensibilidade média de 0,740 e F1 médio de 0,630; o original teve Brier médio menor (0,086 contra 0,101). São resultados de desenvolvimento, não uma avaliação independente futura.

Na v5, pela regra pré-registrada de PR-AUC com desempate por Brier, o candidato técnico foi o Random Forest original com folha mínima 10 e 400 árvores (PR-AUC média 0,67198; Brier 0,08860; sensibilidade @0,50 0,54255). O `balanced_subsample` com folha 10 teve PR-AUC média 0,67268, Brier 0,11695 e sensibilidade 0,81075. Na comparação controlada com folha 5 e 400 árvores, o bootstrap mensal não distinguiu PR-AUC com clareza (delta +0,00117; IC95% -0,00155 a +0,00409), mas confirmou maior sensibilidade e pior Brier para a variante balanceada. A recomendação técnica favorece o original quando se priorizam probabilidade mais confiável e menos alarmes falsos; o balanceado é alternativa quando a prioridade é reduzir chuvas não detectadas.

Após congelar os quatro joblibs finais, a v5 avaliou o teste retrospectivo de 2026 (6.551 linhas, 1.375 positivas; limiar fixo 0,50). O original obteve PR-AUC 0,64577, Brier 0,10904, sensibilidade 0,43345, 273 falsos positivos e 779 falsos negativos. O `balanced_subsample` obteve PR-AUC 0,64234, Brier 0,12542, sensibilidade 0,75855, 853 falsos positivos e 332 falsos negativos. O peso positivo 2:1 ficou entre eles em sensibilidade (0,61891), com PR-AUC 0,64554. A avaliação foi concluída e registrada, mas é retrospectiva: 2026 já havia sido consultado em ciclos anteriores e não participou da seleção v5.

Assim, existe um candidato técnico preferido, mas ainda não uma decisão operacional irreversível: os custos dos erros não foram definidos, as entradas e o alvo precisam de confirmação na fonte, e 2026 já foi consultado em etapas antigas. A v5 avaliou esse período uma vez após congelar os modelos, sem usar os resultados para a seleção; portanto, a avaliação é retrospectiva e não independente.

### Comparação atual `train_v6.py`

Nas partições de desenvolvimento, `ensemble_original_favor` obteve a maior PR-AUC média (0,67319), praticamente empatada com a média simples (0,67315). A média simples alcançou sensibilidade de 0,75967, entre o original (0,54255) e o `balanced_subsample` (0,81075), com Brier 0,10470, pior que o original (0,08860). Como as proporções foram comparadas nas mesmas partições e os custos dos erros não foram definidos, isto é evidência exploratória, não escolha operacional.

A v6 mantém sete atributos e os parâmetros estruturais `n_estimators=400`, `min_samples_leaf=10`, `max_features=sqrt` e bootstrap. Compara os pesos de classe `None`, `balanced` e `balanced_subsample`, além das combinações de probabilidades com pesos iguais e três proporções alternativas. A avaliação usa as partições cronológicas 2022–2025 e três sementes; o teste de 2026 não foi consultado nesta versão. Métricas por partição/semente, previsões fora da amostra, três joblibs, resumo e hashes estão no experimento local `data/experiments/weather_v6_20261105T120000Z/`; consulte `reports/training/sixth_training_report.md`. As combinações são evidência de desenvolvimento, não decisão operacional; custos dos erros e avaliação futura independente continuam pendentes.

### Avaliação aninhada `evaluate_test.py`

A v7 reutiliza previsões fora da amostra da v6. Para cada partição externa de 2023, 2024 e 2025, ajusta calibradores, pesos (grade simplex com passo 0,1) e limiar somente com anos anteriores. Compara calibração sigmoide, isotônica e sem ajuste, quatro políticas fixas e uma combinação de três modelos ajustada internamente, sob quatro cenários de custo FN:FP. Mede também complementaridade de erros. Reavaliação registrada em `data/experiments/weather_v7_reassessment_20261105T/`; não seleciona modelo operacional nem grava joblibs finais porque a equipe ainda não definiu custo/limite de alertas. 2026 não foi usado. Consulte `reports/training/seventh_training_report.md`.



### Candidato preparado para futura integração

A equipe optou provisoriamente pela média simples dos três membros v6: original, `balanced` e `balanced_subsample`, com calibradores isotônicos individuais e pesos 1/3. Limiar inicial 0,50; versão `weather-v6-simple-mean-isotonic-v1`. Pacote do modelo e manifesto locais: `data/experiments/weather_v6_integration_candidate_20261105T190315Z/`; empacotador `scripts/package_weather_model.py`; adaptador `src/models/weather_ensemble.py`. Os contratos de [serviço de retaguarda](docs/integration/backend.md), [interface](docs/integration/frontend.md) e [Banco](docs/integration/database.md) foram alinhados.

A v6 requer quatro medidas atuais e pressão em T-1h; o serviço de retaguarda deriva `temp_humidity`, `pressure_diff` e `hour_of_day`. A pressão anterior foi adicionada à requisição e ao esquema proposto para tornar a engenharia reproduzível. Este é um candidato para integração histórica, não validação operacional independente. API, migração e tela continuam por implementar.

### Versão v4 arquivada

A versão v4 acrescenta:
- `temp_humidity`: produto entre temperatura e umidade relativa;
- `pressure_diff`: diferença da pressão em relação ao registro anterior;
- `hour_of_day`: hora local extraída do timestamp;
- Random Forest original e balanceado com `n_estimators=1000`, `max_depth=None` e `min_samples_leaf=5`.

Foram corrigidos e validados os seguintes pontos na v4:

1. Ordenação cronológica antes de calcular `pressure_diff`.
2. Cálculo de importância por permutação para um modelo por chamada.
3. Uso de `beta` na seleção de limiar por F-beta e registro do limiar/métricas selecionados.
4. Registro das sete entradas usadas, parâmetros e hashes SHA-256 no manifesto.
5. Avaliação opcional de teste com métricas probabilísticas e previsões, embora desativada nesta execução.

A execução `weather_20261103T190835Z` concluiu treino, validação e validação cruzada; os cinco joblibs foram carregados e conferidos com sete entradas. Os hashes da tabela e dos modelos correspondem ao manifesto. O conjunto de teste de 2026 permaneceu sem avaliação nesta rodada. Ver `reports/training/fourth_training_report.md` para métricas, artefatos e ressalvas.

### Comparação histórica v5 (arquivada)

A v5 compara os pesos `None`, `balanced`, `balanced_subsample` e positivo manual 2:1; folhas mínimas 5 e 10; e 250, 400 ou 800 árvores nas combinações selecionadas. Usa os sete atributos da v4, partições expansivos 2022-2025 e três sementes. O limiar é fixo em 0,50 nas métricas de classificação e o período de 2026 não participa da seleção nem do ajuste final.

O experimento contém 144 resultados de partição/semente, 1.262.160 linhas de previsão fora da amostra, quatro joblibs finais e métricas/previsões de teste para 6.551 registros de 2026. Os modelos estão ajustados somente com dados anteriores a 2026. O manifesto registra parâmetros, versões, hashes, avaliação retrospectiva concluída e a confirmação de que o teste não participou da seleção. Consulte `reports/training/fifth_training_report.md` para resultados, limitações e próximos passos.

### Testes, dependências e publicação

Na atualização v5, a suíte completa passou com **51 testes aprovados**, incluindo os testes da grade de candidatos, limites temporais, métricas e avaliação congelada de teste. `pip check` não encontrou dependências quebradas em `.venv` nem em `.venv-validacao`; uma instalação limpa em outra máquina ainda deve ser confirmada.

As regras locais de proteção do Git, os hooks e a documentação de onboarding foram desenvolvidos em etapas anteriores. Antes de publicar novas alterações, conferir o estado atual do índice, ativar os hooks no clone e revisar o destino/branch. Não há confirmação nesta atualização de que as mudanças mais recentes tenham sido enviadas ao remoto.

### Próximos passos prioritários

1. Aprovar com a equipe a prioridade entre alarmes falsos e chuvas não detectadas, incluindo o limiar ou taxa máxima de alertas.
2. Confirmar a semântica temporal da precipitação, a procedência primária dos dados e a disponibilidade real das entradas.
3. Reservar dados futuros ainda não consultados para avaliação independente depois de congelar modelo, atributos e limiar.
4. Garantir que a engenharia das sete entradas seja reproduzida sem diferenças no futuro serviço de retaguarda.
5. Validar a instalação em ambiente limpo e revisar o estado do Git antes de publicar.

---

## Resumo geral

O projeto possui uma base de auditoria, análise exploratória, diagnóstico dos dados e investigação preliminar das imagens GOES. No eixo meteorológico, a tabela supervisionada foi preparada e utilizada em seis execuções documentadas de treinamento; a v5 adiciona comparação repetida; a v6 compara três estratégias de peso; a v7 avalia calibração, combinação e limiar com validação temporal aninhada, sem consultar o teste de 2026.

Os resultados continuam experimentais e retrospectivos. Permanecem incertezas sobre a origem primária dos dados, a semântica temporal da precipitação e a disponibilidade real das variáveis no instante em que uma previsão seria emitida. Portanto, ainda não demonstram capacidade de previsão operacional em tempo real.

O trabalho com imagens GOES continua em uma linha exploratória separada. Ainda não há integração validada entre as imagens de satélite e o modelo meteorológico treinado.

A preparação para colaboração no GitHub, as regras locais de proteção de arquivos e os testes automatizados foram desenvolvidos em etapas anteriores. O estado de publicação deve ser interpretado conforme o registro de autorização e as operações efetivamente realizadas no repositório remoto.

## Implementado

### Dados meteorológicos e treinamentos

- Preparação de uma tabela meteorológica com 59.159 registros, quatro variáveis originais, horário de referência, horário-alvo e alvo `rain_next_hour`.
- Preservação do arquivo original utilizado na preparação.
- Separação cronológica em treino, validação e teste, com limites temporais aplicados também ao horário-alvo.
- Implementação e execução documentada de quatro ciclos: treinamento inicial, comparação ampliada v3, execução de 31/10 e v4 corrigida em `weather_20261103T190835Z`.
- Comparação de modelo de referência constante, modelo de referência por prior, regressão logística, Random Forest original e Random Forest balanceado.
- Avaliação retrospectiva do teste nas duas primeiras execuções; a terceira e a quarta execuções mantiveram o teste sem avaliação.
- Registro de métricas, previsões, manifesto e resumo da divisão temporal nos diretórios locais dos experimentos, conforme os relatórios.
- `scripts/archive/train_v4.py` corrigido e executado historicamente; inclui três atributos derivados, seleção de limiar na validação e validação cruzada temporal. Manifesto e cinco joblibs foram conferidos; teste de 2026 não avaliado nessa execução.
- `scripts/archive/train_v5.py` preserva o experimento histórico; a v6 é o treinamento mais recente e os testes permanecem centralizados em `tests/test_train.py`.
- Suíte atual com 46 testes aprovados; a etapa inicial havia registrado 42 testes.

### Auditoria e exploração de dados

- Auditoria de 59.160 registros meteorológicos e de um índice com 59.033 arquivos NPZ, com verificações de continuidade, ausências, duplicatas e preservação.
- Análise exploratória temporal e distributiva, verificações físicas, investigação de chuva/precipitação, cobertura e possibilidade de reutilização.
- Análise de 192 imagens amostradas e geração local de 12 gráficos.
- Investigação da proveniência e da geolocalização dos dados meteorológicos e de satélite.
- Avaliação estrutural da viabilidade dos horizontes de 1, 3, 6 e 7 horas, sem confundir essa análise com a validação de um modelo operacional.

### Exploração de imagens GOES

- Piloto com 19 imagens.
- Reconstrução física dos valores em Kelvin, inspeção de metadados e tratamento de pixels de preenchimento e valores não finitos.
- 15 reconstruções e quatro imagens totalmente inválidas no piloto registrado.
- Identificação de uma reconstrução com apenas 1,61% de pixels válidos.
- Identificação de três produtos originais relevantes para a investigação.
- Investigação da projeção, da navegação e da compatibilidade entre as grades GOES-16 e GOES-19, sem transformação geográfica validada.

Essas atividades são exploratórias. Não constituem um conjunto de imagens geograficamente validado nem uma integração GOES aprovada para treinamento.

### Configuração, amostragem e proteção do repositório

- Configuração em `config.py` e `.env.example`, incluindo modo `sample`/`full`, caminhos de NPZ/ZIP, CSV e README e membro opcional.
- `scripts/make_sample.py`: seleção determinística de um NPZ inteiro, sem extração em massa ou sobrescrita, com saída estritamente menor que 50 MB.
- `scripts/check_dataset.py`: teste rápido de uma imagem na fonte configurada. O modo `full` troca a origem configurada, mas não executa processamento integral.
- `.gitignore` com negação por padrão: somente código e documentação explicitamente permitidos podem ser adicionados conforme as regras definidas.
- Exclusão de dados NPZ/ZIP/CSV, resultados JSON/PNG, ambientes locais e credenciais.
- `.githooks/pre-commit` e `scripts/check_staged.py` para inspecionar todo o índice, rejeitar tipos e caminhos proibidos e arquivos acima de 1 MB, inclusive NPZ adicionado à força.
- README de onboarding, comandos Git, branches e instruções de compartilhamento externo da amostra.

As regras de proteção reduzem o risco de publicação acidental, mas não substituem a revisão do índice Git nem garantem proteção contra todas as formas de contorno.

## Arquitetura atual

```text
config.py / .env.example
    Configuração dos utilitários

scripts/
    Preparação meteorológica
    Treinamento e avaliação do modelo
    Amostragem e teste rápido do acervo
    Verificação do índice Git

src/data/
    Auditoria, EDA, figuras, relatório,
    viabilidade dos horizontes e proveniência

src/features/
    Leitura física GOES e execução do piloto

tests/
    Testes unitários dos componentes existentes

reports/
    Relatórios Markdown e registros científicos

docs/
    Documentação de preparação e integração

docs/history/
    README e STATUS anteriores preservados

.githooks/
    Hook local de pré-commit

data/
    Tabela meteorológica e artefatos experimentais
    mantidos localmente e excluídos do Git
```

Os scripts científicos antigos continuam recebendo caminhos explícitos; os utilitários mais novos leem `.env`. Um `sample.npz` não substitui o CSV e o ZIP em uma EDA completa. Certas etapas dependem de JSON e CSV gerados localmente por etapas anteriores. Por isso, um clone que contenha apenas código e documentação pode não conter as saídas necessárias para repetir todo o histórico científico.

A etapa meteorológica agora possui scripts de treinamento e avaliação, mas ainda não está integrada a uma API, banco de dados ou interface.

## Dados e validações

### Base meteorológica

A tabela experimental em `data/processed/weather_training.csv` contém 59.159 registros, com 10.120 casos positivos e 49.039 negativos.

A tabela cobre o período de 01/01/2020 até 30/09/2026, com horários de referência e alvo. O último registro de entrada do período original foi excluído durante a preparação porque não havia timestamp futuro disponível para formar o alvo.

O SHA-256 registrado para a tabela preparada é:

```text
a3ea57e03c9b66e575cecbcc47a673a9af69c7c6aeeb5d6f07a18b0e69b609d3
```

O SHA-256 registrado para o arquivo original é:

```text
4e83a5248ee7008b0ea4dffb4bba28a80023b1892c4d38ff54cba41b6ee01f4c
```

A semântica exata do alvo de precipitação ainda precisa ser confirmada na origem dos dados. Até essa confirmação, a definição de chuva na próxima hora é uma hipótese metodológica adotada para o experimento, não uma propriedade definitivamente comprovada da coleta original.

### Divisão temporal e avaliação

O experimento utiliza a seguinte divisão:

- Treino: antes de 01/01/2025.
- Validação: ano de 2025.
- Teste: a partir de 01/01/2026, até o final do período disponível em setembro de 2026.

Os limites foram aplicados ao horário da entrada e ao horário-alvo, evitando incluir em um conjunto um registro cujo alvo ultrapasse a fronteira temporal correspondente.

O conjunto de teste contém 6.551 registros, dos quais 1.375 são positivos. Ele representa um período parcial de 2026, não um ano completo.

Resultado histórico do Random Forest original no primeiro experimento, no teste retrospectivo:

| Métrica | Resultado |
|---|---:|
| Acurácia | 81,18% |
| Precisão para chuva | 59,15% |
| Revocação para chuva | 33,38% |
| F1 para chuva | 42,68% |
| Casos de chuva identificados | 459 |
| Casos de chuva não identificados | 916 |
| Falsos positivos | 317 |

Nas avaliações posteriores, a versão v3 comparou cinco modelos no mesmo período já consultado. No limiar 0,50, o Random Forest balanceado alcançou sensibilidade de 81,82% e F1 de 57,37%, mas gerou 1.422 falsos positivos. Esses resultados são retrospectivos e não independentes.

O modelo de referência que sempre prevê ausência de chuva obteve acurácia de 79,01%, mas não identificou nenhum caso positivo. Isso demonstra por que a acurácia, isoladamente, é insuficiente para avaliar este problema.

O teste de janeiro a setembro de 2026 já foi utilizado nas avaliações anteriores e não deve ser reutilizado para escolher parâmetros, atributos ou limiares da v4.

### Amostra GOES e validações anteriores

O acervo GOES investigado é um ZIP de 79.201.181.103 bytes, aproximadamente 73,8 GiB. A amostra criada em `data/sample/sample.npz` tem 1.455.519 bytes, preserva uma imagem inteira e seus metadados e não deve ser publicada no Git.

A amostra não é um recorte geográfico validado nem uma amostra estatística destinada à modelagem. Os smoke tests `sample` e `full` foram aprovados na validação registrada, com uma matriz de 885 × 1217 e 1.077.045 pixels válidos, sem inconsistências de identidade detectadas naquela verificação. A geolocalização continua sem validação.

As validações anteriores de proteção do repositório incluíram testes de regras de ignore para NPZ, ZIP, `.env`, dados, `node_modules` e resultados; staging permitido de código/documentação; e bloqueio de NPZ forçado no índice. Esses registros históricos não substituem a validação do estado atual do repositório.

### Dependências

As dependências diretas incluem NumPy, pandas, Matplotlib, scikit-learn e joblib. As versões declaradas em `requirements.txt` são:

```text
numpy==2.5.4
pandas==3.0.1
matplotlib==3.11.2
scikit-learn==1.9.1
joblib==1.6.0
```

As versões de scikit-learn e joblib utilizadas no experimento correspondem às declaradas no arquivo. A instalação em um ambiente limpo ainda precisa ser validada para confirmar a reprodutibilidade fora do ambiente atual. O arquivo de requisitos fixa as dependências diretas, mas não representa um lock completo de todas as dependências transitivas.

## Pendências

### Antes de publicar ou compartilhar novas alterações

1. Revisar a documentação histórica para decidir se caminhos locais e detalhes do conjunto de dados devem ser públicos.
2. Validar a instalação limpa das dependências em um ambiente da equipe.
3. Definir armazenamento externo autorizado para amostras e acervo, se necessário. Não há licença de redistribuição dos dados aprovada nem URL de download configurada.
4. Ativar o hook em cada clone e exigir revisão por solicitação de integração no ramo principal, conforme o fluxo acordado.
5. Conferir o índice Git antes de cada commit. `.gitignore` e hooks podem ser contornados; não utilizar `git add -f` para incluir dados nem `--no-verify` para ignorar as verificações.

### Pendências científicas do MVP meteorológico

1. Recuperar a requisição, a resposta e o código de exportação meteorológica para confirmar o intervalo temporal representado por `rain`/`precipitation`.
2. Confirmar a procedência primária dos registros e os procedimentos usados para coleta, transformação e exportação.
3. Documentar a disponibilidade real das quatro variáveis no instante em que uma previsão seria emitida. A existência de um valor na tabela histórica não comprova que ele estaria disponível em operação.
4. Tratar os resultados atuais como retrospectivos e experimentais até que essas questões sejam resolvidas.
5. Não ajustar o modelo atual usando o conjunto de teste já avaliado. Caso o procedimento seja alterado com base nesses resultados, reservar uma nova avaliação independente.

### Pendências da linha exploratória GOES

1. Recuperar projeção, vetores de navegação e vínculo do recorte GOES para validar a mesma região nas duas grades.
2. Aprovar semântica dos alvos, região, qualidade mínima e regra de disponibilidade e idade das imagens.
3. Investigar a hipótese de que os 50 links com fim/criação até o horário de referência representem imagens disponíveis operacionalmente; isso ainda não está confirmado.
4. Somente depois dessas validações, avaliar a construção de um conjunto de dados supervisionado multimodal e a comparação entre modelos meteorológicos com e sem GOES.

A linha GOES é uma evolução futura do projeto e não constitui requisito para concluir a documentação ou a avaliação do primeiro modelo meteorológico.

### Organização futura

Parametrizar caminhos fixos e saídas dos scripts legados quando necessário, evitando reescrever documentação histórica sem revisão. Considerar configuração central e integração contínua quando o fluxo estiver definido.

Não há API, interface, banco de dados ou serviço operacional implementado nesta etapa. O projeto segue como pesquisa baseada em scripts.

Para detalhes científicos, consultar os relatórios em `reports/temporal/`, `reports/horizons/` e `reports/pilot/`, além de `reports/project/revisao_tabela_e_periodos.md`. Os documentos históricos anteriores continuam disponíveis em `docs/history/`.

## Registro de publicação autorizado

Destino registrado: repositório privado `victorhukra/backend-monitoramento-ambiental`, com permissão de escrita. A integração deve partir do commit remoto existente, sem force-push. O README original remoto foi preservado em `docs/dataset/README.md`.

Esse registro descreve a autorização de publicação documentada no histórico do projeto. A situação efetiva do remoto e as alterações enviadas devem ser confirmadas pelo estado atual do Git antes de realizar novas operações.
