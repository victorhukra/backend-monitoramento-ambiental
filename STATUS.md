## Atualização do MVP — 03/11/2026

O MVP meteorológico evoluiu da preparação da tabela para três execuções documentadas de treinamento e avaliação. O escopo continua sendo classificar a ocorrência de chuva na próxima hora em Londrina/PR, com base em dados meteorológicos horários. O projeto permanece experimental e retrospectivo: ainda não há API, banco de dados, interface ou serviço de previsão em tempo real.

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
| Primeiro treinamento | `weather_20261027T173216Z` — 27/10/2026 | Baseline constante e Random Forest original; validação e teste retrospectivo concluídos. |
| Segundo treinamento | `weather_20261029T140207Z` — 29/10/2026 | Cinco modelos, métricas probabilísticas, tabelas de limiares, recorte de mesmos meses e validação cruzada temporal; avaliação retrospectiva do teste concluída. |
| Terceira execução | `weather_20261031T112237Z` — 31/10/2026 | Cinco modelos, Random Forests com 500 árvores e sem limite de profundidade; validação e validação cruzada temporal documentadas. O teste de 2026 não foi avaliado nesta rodada. |
| Código atual — `train_v4.py` | Código fornecido nesta atualização | Adiciona três atributos derivados e eleva os Random Forests para 1.000 árvores. **Ainda não há relatório ou artefatos de uma execução v4 entre os materiais analisados.** O script precisa de correções antes de ser considerado executável/validado. |

### Resultados e interpretação

Na primeira execução, o Random Forest original obteve no teste retrospectivo (6.551 registros) acurácia de 81,18%, precisão de 59,15%, recall de 33,38% e F1 de 42,68%. Identificou 459 das 1.375 ocorrências de chuva, deixou passar 916 e gerou 317 falsos positivos.

Na segunda execução, a comparação dos cinco modelos mostrou compromissos diferentes. No limiar 0,50, o Random Forest original teve acurácia de 81,18% e precisão de 59,15%, mas recall de 33,38%. O Random Forest balanceado teve recall de 81,82% e F1 de 57,37%, à custa de 1.422 falsos positivos. As métricas probabilísticas favoreceram o Random Forest original em Brier e log loss, enquanto o balanceado obteve PR-AUC e ROC-AUC ligeiramente maiores.

Na terceira execução, a validação de 2025 indicou recall de 0,662 e F1 de 0,512 para o Random Forest balanceado, contra recall de 0,366 e F1 de 0,416 para o Random Forest original. O relatório recomenda considerar o balanceado quando a prioridade for reduzir falsos negativos, mas ressalta o custo operacional e a necessidade de avaliação adicional.

**Não há vencedor definitivo.** A escolha depende do custo de falsos negativos e falsos positivos, da calibração das probabilidades e do comportamento em um período independente. O teste de janeiro a setembro de 2026 já foi consultado nas duas primeiras execuções; não deve ser reutilizado para escolher modelos, atributos ou limiares.

### Situação do código atual `train_v4.py`

A versão v4 acrescenta:
- `temp_humidity`: produto entre temperatura e umidade relativa;
- `pressure_diff`: diferença da pressão em relação ao registro anterior;
- `hour_of_day`: hora local extraída do timestamp;
- Random Forest original e balanceado com `n_estimators=1000`, `max_depth=None` e `min_samples_leaf=5`.

A revisão estática identificou pontos que precisam ser corrigidos antes de executar/validar essa versão:

1. `pressure_diff` é calculada antes de ordenar o DataFrame por `time`. Se o CSV não estiver previamente ordenado, a diferença será calculada na ordem incorreta. Ordenar os registros antes de aplicar `.diff()`.
2. `validation_importance()` percorre os três nomes (`random_forest`, `random_forest_balanced` e `logistic`), mas é chamada passando um dicionário que contém apenas o modelo atual. Isso pode gerar `KeyError` ao acessar os outros modelos. A função deve receber o dicionário completo ou processar somente o modelo recebido.
3. O parâmetro `beta` é recebido por `run()`, mas não é utilizado no fluxo; `choose_threshold()` também não é chamado. Portanto, a versão atual não seleciona limiares por F-beta, apesar de expor esse parâmetro na linha de comando.
4. A avaliação opcional do teste grava `metrics_test.json`, mas não gera `predictions_test.csv` nem métricas probabilísticas do teste nesse bloco.
5. O manifesto registra `features` com as quatro entradas originais e `engineered_features` separadamente. Os modelos, porém, são treinados com as sete colunas; a forma de registrar/carregar a lista completa de atributos deve ser mantida consistente para uma futura inferência.

Esses pontos são observações da leitura do código, não resultados de execução. Não há evidência fornecida de que a versão v4 tenha sido treinada com sucesso.

### Testes, dependências e publicação

Os registros anteriores documentam 42 testes automatizados aprovados para a etapa inicial. Esse resultado histórico não comprova que os testes atuais cubram ou aprovem `train_v4.py`. A instalação das dependências em ambiente limpo também permanecia pendente no STATUS anterior.

As regras locais de proteção do Git, os hooks e a documentação de onboarding foram desenvolvidos em etapas anteriores. Antes de publicar novas alterações, conferir o estado atual do índice, ativar os hooks no clone e revisar o destino/branch. Não há confirmação nesta atualização de que as mudanças mais recentes tenham sido enviadas ao remoto.

### Próximos passos prioritários

1. Corrigir os problemas identificados em `train_v4.py`, especialmente a ordenação antes de `pressure_diff` e a chamada de `validation_importance()`.
2. Atualizar/adicionar testes para engenharia de atributos, ordenação temporal, treinamento, importância por permutação, manifesto e carregamento dos modelos.
3. Executar a v4 em um novo diretório de experimento e registrar o relatório correspondente; manter `--evaluate-test` desativado nesta etapa.
4. Comparar os resultados da v4 na validação e na validação cruzada temporal com os experimentos anteriores, sem tratar o teste já consultado como avaliação independente.
5. Definir critérios de seleção do modelo e do limiar considerando o custo de falsos positivos e falsos negativos.
6. Confirmar a semântica temporal da precipitação, a procedência primária dos dados e a disponibilidade real das entradas.
7. Reservar um período futuro ainda não utilizado para avaliação independente depois de congelar modelo, atributos e limiar.
8. Validar a instalação em ambiente limpo e revisar o estado do Git antes de publicar.

---

## Resumo geral

O projeto possui uma base de auditoria, análise exploratória, diagnóstico dos dados e investigação preliminar das imagens GOES. No eixo meteorológico, a tabela supervisionada foi preparada e utilizada em três execuções documentadas de treinamento; o código atual evoluiu para `train_v4.py`, mas ainda precisa de correções e de uma execução documentada.

Os resultados continuam experimentais e retrospectivos. Permanecem incertezas sobre a origem primária dos dados, a semântica temporal da precipitação e a disponibilidade real das variáveis no instante em que uma previsão seria emitida. Portanto, ainda não demonstram capacidade de previsão operacional em tempo real.

O trabalho com imagens GOES continua em uma linha exploratória separada. Ainda não há integração validada entre as imagens de satélite e o modelo meteorológico treinado.

A preparação para colaboração no GitHub, as regras locais de proteção de arquivos e os testes automatizados foram desenvolvidos em etapas anteriores. O estado de publicação deve ser interpretado conforme o registro de autorização e as operações efetivamente realizadas no repositório remoto.

## Implementado

### Dados meteorológicos e treinamentos

- Preparação de uma tabela meteorológica com 59.159 registros, quatro variáveis originais, horário de referência, horário-alvo e alvo `rain_next_hour`.
- Preservação do arquivo original utilizado na preparação.
- Separação cronológica em treino, validação e teste, com limites temporais aplicados também ao horário-alvo.
- Implementação e execução documentada de três etapas de treinamento: `train.py`, versão v3 e terceira execução registrada em `weather_20261031T112237Z`.
- Comparação de baseline constante, baseline por prior, regressão logística, Random Forest original e Random Forest balanceado.
- Avaliação retrospectiva do teste nas duas primeiras execuções; a terceira execução não avaliou o teste.
- Registro de métricas, previsões, manifesto e resumo da divisão temporal nos diretórios locais dos experimentos, conforme os relatórios.
- Desenvolvimento de `train_v4.py`, com três atributos derivados e Random Forests de 1.000 árvores; execução ainda não comprovada e correções pendentes.
- Testes automatizados históricos para validação de colunas, entradas finitas, alvo binário, probabilidade da classe positiva e limites temporais; 42 testes foram aprovados na etapa inicial.

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
- `scripts/check_dataset.py`: smoke test de uma imagem na fonte configurada. O modo `full` troca a origem configurada, mas não executa processamento integral.
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
    Amostragem e smoke test do acervo
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

Nas avaliações posteriores, a versão v3 comparou cinco modelos no mesmo período já consultado. No limiar 0,50, o Random Forest balanceado alcançou recall de 81,82% e F1 de 57,37%, mas gerou 1.422 falsos positivos. Esses resultados são retrospectivos e não independentes.

O baseline que sempre prevê ausência de chuva obteve acurácia de 79,01%, mas não identificou nenhum caso positivo. Isso demonstra por que a acurácia, isoladamente, é insuficiente para avaliar este problema.

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

1. Revisar a documentação histórica para decidir se caminhos locais e detalhes do dataset devem ser públicos.
2. Validar a instalação limpa das dependências em um ambiente da equipe.
3. Definir armazenamento externo autorizado para amostras e acervo, se necessário. Não há licença de redistribuição dos dados aprovada nem URL de download configurada.
4. Ativar o hook em cada clone e exigir revisão por Pull Request na branch principal, conforme o fluxo acordado.
5. Conferir o índice Git antes de cada commit. `.gitignore` e hooks podem ser contornados; não utilizar `git add -f` para incluir dados nem `--no-verify` para ignorar as verificações.

### Pendências do código atual `train_v4.py`

1. Ordenar os registros por `time` antes de calcular `pressure_diff`.
2. Corrigir a chamada de `validation_importance()`, que atualmente recebe apenas um modelo, embora a função tente acessar três nomes.
3. Definir e implementar o uso de `beta`/`choose_threshold()` ou remover o parâmetro se a seleção de limiar não fizer parte do fluxo.
4. Completar a avaliação opcional do teste, caso seja necessária em uma futura avaliação independente, incluindo previsões e métricas probabilísticas.
5. Registrar de forma consistente as sete entradas utilizadas pelos modelos e garantir que o mesmo processamento seja aplicado na inferência.
6. Criar testes específicos para as novas variáveis e executar a versão corrigida antes de atualizar o relatório de treinamento.

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
4. Somente depois dessas validações, avaliar a construção de um dataset supervisionado multimodal e a comparação entre modelos meteorológicos com e sem GOES.

A linha GOES é uma evolução futura do projeto e não constitui requisito para concluir a documentação ou a avaliação do primeiro modelo meteorológico.

### Organização futura

Parametrizar caminhos fixos e saídas dos scripts legados quando necessário, evitando reescrever documentação histórica sem revisão. Considerar configuração central e integração contínua quando o fluxo estiver definido.

Não há API, frontend, banco de dados ou serviço operacional implementado nesta etapa. O projeto segue como pesquisa baseada em scripts.

Para detalhes científicos, consultar os relatórios em `reports/temporal/`, `reports/horizons/` e `reports/pilot/`, além de `reports/project/revisao_tabela_e_periodos.md`. Os documentos históricos anteriores continuam disponíveis em `docs/history/`.

## Registro de publicação autorizado

Destino registrado: repositório privado `victorhukra/backend-monitoramento-ambiental`, com permissão de escrita. A integração deve partir do commit remoto existente, sem force-push. O README original remoto foi preservado em `docs/dataset/README.md`.

Esse registro descreve a autorização de publicação documentada no histórico do projeto. A situação efetiva do remoto e as alterações enviadas devem ser confirmadas pelo estado atual do Git antes de realizar novas operações.
