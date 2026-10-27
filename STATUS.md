# STATUS — Preparação para colaboração no GitHub

## Atualização do MVP — 27/10/2026

O MVP meteorológico avançou da preparação da tabela para o primeiro experimento de treinamento e avaliação. O escopo continua sendo estimar a ocorrência de chuva na próxima hora em Londrina, utilizando quatro entradas: temperatura, umidade relativa, pressão ao nível do mar e nebulosidade.

A tabela experimental contém **59.159 registros**, com 10.120 alvos positivos e 49.039 negativos. O arquivo original permaneceu preservado. A interpretação temporal do alvo ainda depende de confirmação na origem dos dados; portanto, os resultados devem ser tratados como experimentais e retrospectivos, sem alegação de previsão operacional em tempo real.

### Treinamento e avaliação

Foi implementada a divisão cronológica proposta:

- **Treino:** período anterior a 01/01/2025.
- **Validação:** ano de 2025.
- **Teste:** de janeiro a setembro de 2026, respeitando os limites temporais dos alvos.

Foram treinados dois modelos:

- **Baseline:** classificador que sempre prevê ausência de chuva.
- **Random Forest:** modelo de classificação utilizado no primeiro experimento.

A avaliação final utilizou 6.551 registros do conjunto de teste.

| Métrica | Baseline | Random Forest |
|---|---:|---:|
| Acurácia | 79,01% | 81,18% |
| Precisão para chuva | 0,00% | 59,15% |
| Revocação para chuva | 0,00% | 33,38% |
| F1 para chuva | 0,00% | 42,68% |

No teste, havia 1.375 casos positivos. O Random Forest identificou 459 deles, deixou de identificar 916 e gerou 317 falsos positivos.

A acurácia isolada não é suficiente para avaliar a utilidade do modelo, especialmente diante do desequilíbrio entre as classes. Embora o Random Forest tenha superado o baseline em acurácia e identificado parte dos casos de chuva, ainda deixou de detectar a maior parte dos positivos.

Os artefatos do experimento foram salvos localmente em `data/experiments/weather_20261027T173216Z/`, incluindo modelos serializados, manifesto, métricas, previsões de validação e teste e resumo da divisão. Os dados e resultados gerados continuam sujeitos à política de exclusão do Git.

A avaliação do conjunto de teste foi realizada separadamente, sem retreinar os modelos. Esse conjunto deve permanecer reservado para a avaliação deste experimento e não deve orientar ajustes de parâmetros, variáveis ou limiares.

### Testes e dependências

A suíte automatizada foi executada com sucesso: **42 testes aprovados**.

As versões de `scikit-learn` e `joblib` utilizadas correspondem às declaradas em `requirements.txt`. Ainda falta validar a instalação em um ambiente limpo para verificar a reprodutibilidade fora do ambiente atual.

### Limitações e próximos passos

1. Atualizar a documentação de acompanhamento para refletir o treinamento e a avaliação realizados.
2. Validar a instalação das dependências em um ambiente limpo.
3. Confirmar, junto à origem, o significado temporal da precipitação e a procedência primária dos registros. O SENAI foi identificado como fornecedor da base, sem confirmação de que tenha realizado a coleta original.
4. Preservar o conjunto de teste já avaliado, sem utilizá-lo para escolher novos parâmetros, variáveis ou limiares.
5. Manter o projeto como experimento histórico. API, banco de dados, interface e integração GOES não fazem parte desta etapa concluída.

A conclusão deste primeiro treinamento não certifica o modelo para uso operacional. Caso sejam feitas alterações motivadas pelos resultados do teste, será necessária uma nova avaliação independente para medir o desempenho do procedimento alterado.

---

## Resumo geral

O projeto possui uma base de auditoria, análise exploratória, diagnóstico dos dados e investigação preliminar das imagens GOES. No eixo meteorológico, a tabela supervisionada experimental foi preparada e utilizada no primeiro treinamento e na avaliação cronológica de um baseline e de um Random Forest.

O experimento representa um avanço metodológico, mas ainda existem incertezas sobre a origem primária dos dados, a semântica temporal da precipitação e a disponibilidade real das variáveis no instante em que uma previsão seria emitida. Portanto, os resultados não demonstram, por si só, capacidade de previsão operacional em tempo real.

O trabalho com imagens GOES continua em uma linha exploratória separada. Ainda não há integração validada entre as imagens de satélite e o modelo meteorológico treinado.

A preparação para colaboração no GitHub, as regras locais de proteção de arquivos e os testes automatizados foram desenvolvidos em etapas anteriores. O estado de publicação deve ser interpretado conforme o registro de autorização e as operações efetivamente realizadas no repositório remoto.

## Implementado

### Dados meteorológicos e primeiro modelo

- Preparação de uma tabela meteorológica com 59.159 registros, quatro variáveis de entrada, horário de referência, horário-alvo e alvo `rain_next_hour`.
- Preservação do arquivo original utilizado na preparação.
- Separação cronológica em treino, validação e teste, com limites temporais aplicados também ao horário-alvo.
- Implementação de `scripts/train.py` para treinar o baseline e o Random Forest, registrar métricas de validação e salvar os artefatos do experimento.
- Implementação de `scripts/evaluate_test.py` para avaliar o experimento já treinado no conjunto de teste sem realizar novo treinamento.
- Registro de métricas, previsões, manifesto e resumo da divisão temporal no diretório local do experimento.
- Testes automatizados para validação de colunas, entradas finitas, alvo binário, probabilidade da classe positiva e limites temporais.
- Execução da suíte automatizada com 42 testes aprovados.

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

Resultados do Random Forest no teste:

| Métrica | Resultado |
|---|---:|
| Acurácia | 81,18% |
| Precisão para chuva | 59,15% |
| Revocação para chuva | 33,38% |
| F1 para chuva | 42,68% |
| Casos de chuva identificados | 459 |
| Casos de chuva não identificados | 916 |
| Falsos positivos | 317 |

O baseline que sempre prevê ausência de chuva obteve acurácia de 79,01%, mas não identificou nenhum caso positivo. Esse resultado demonstra por que a acurácia, isoladamente, é insuficiente para avaliar este problema.

O teste já foi avaliado e não deve ser reutilizado para escolher parâmetros, variáveis ou limiares do modelo atual.

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
