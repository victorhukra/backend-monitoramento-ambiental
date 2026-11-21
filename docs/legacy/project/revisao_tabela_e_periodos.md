# Revisão da tabela e escolha dos períodos do MVP

Verificação em **22/10/2026**. Escopo: Londrina, quatro entradas meteorológicas, chuva na próxima hora. Este documento propõe uma conversa e critérios; **não executa a divisão**.

## 1. Podemos começar a revisão?

**Sim. Não encontrei impedimento estrutural para revisar a tabela e escolher períodos para o MVP histórico experimental.** A associação entre horários e valores está correta em relação ao CSV disponível. Ainda não podemos apresentar esse experimento como comprovação de previsão em tempo real: a origem não confirma integralmente o intervalo da chuva nem quando as entradas estavam disponíveis.

A tabela identificada é [weather_training.csv](../../data/processed/weather_training.csv), dentro de `data/processed/`. Ela não é a tabela `predictions` do banco: contém exemplos para um futuro treinamento, não chamadas da API.

| Questão | O que impede? | Como resolver e verificar |
|---|---|---|
| O acumulado `rain(u)` corresponde realmente à hora anterior? A exportação preservou os horários? | Impede certificar o significado definitivo do alvo. Não impede revisar datas ou trabalhar com a hipótese explícita do MVP. | Solicitar requisição/resposta original e código de exportação ao produtor. Rastrear uma sequência seco–chuva–seco e uma virada de dia, verificando fuso, intervalos e deslocamentos. Confirmar se o mesmo processo gerou todo o período. Uma consulta nova não comprova a exportação antiga. |
| As quatro entradas eram acessíveis em T, na versão que usamos hoje? | Impede afirmar avaliação operacional sem informação posterior. Uma divisão cronológica sozinha não resolve isso. | Definir a fonte que alimentará a API e registrar horário de referência, publicação/recebimento e versão. Só declarar disponibilidade quando houver evidência de que cada entrada chegou até a emissão. Se não houver arquivo histórico equivalente, manter o estudo retrospectivo e validar prospectivamente depois. |
| GOES: localização, grades, pixels inválidos e imagens posteriores | Não bloqueia este MVP: nenhuma imagem entra na tabela atual. | Retomar essas verificações antes de incluir GOES. Não excluir agora linhas meteorológicas por falta de imagem. |

Enquanto as duas primeiras questões são investigadas, podemos revisar integridade, cobertura, frequência de chuva e propor datas. Antes de usar a divisão em treinamento, registrar que o protocolo é **experimental e condicionado à hipótese temporal**, ou confirmar essa hipótese com a origem. Se ela mudar, será necessário revisar os alvos e suas fronteiras. Não é necessário refatorar novamente, implementar o banco ou tratar GOES para fazer esta revisão.

## 2. O que foi conferido diretamente

Foram lidos o CSV derivado completo, seu resumo/exclusões, o CSV original, `config.py`, `scripts/prepare_weather.py` e seus testes. Também foram consultados o README do conjunto de dados, auditoria, EDA, protocolo temporal, relatório de proveniência, guia de preparação e estado atual do projeto.

| Verificação da tabela atual | Resultado |
|---|---|
| Tamanho | 59.159 linhas e 7 colunas |
| Primeiro e último `time` | 01/01/2020 00h e 30/09/2026 22h |
| Último `target_time` | 30/09/2026 23h |
| Ordem e frequência | Crescente; intervalos de uma hora; zero lacunas internas |
| Duplicatas | Zero linhas inteiras duplicadas; zero horários duplicados |
| Valores ausentes | Zero nas sete colunas |
| Valores não finitos nas quatro entradas | Zero |
| `target_time − time` | Exatamente uma hora em todas as linhas |
| Entradas comparadas ao original em T | Zero divergências |
| Alvos comparados a `rain(T+1h) > 0` no original | Zero divergências |
| Classes | 49.039 sem chuva; 10.120 com chuva (aproximadamente 17,11%) |

O original tem 59.160 linhas. A única exclusão registrada é **30/09/2026 23h**, porque não existe 01/10/2026 00h para consultar a resposta. Isso não é uma falha de entrada nem uma lacuna interna. O resumo da preparação registra zero exclusões por entradas inválidas.

Os SHA-256 do original e da tabela foram conferidos antes/depois desta leitura e permaneceram iguais:

- Original: `4e83a5248ee7008b0ea4dffb4bba28a80023b1892c4d38ff54cba41b6ee01f4c`.
- Tabela: `a3ea57e03c9b66e575cecbcc47a673a9af69c7c6aeeb5d6f07a18b0e69b609d3`.

Os relatórios antigos descrevem estágios anteriores: quando dizem que ainda não existia alvo ou que `data/processed/` estava vazio, isso não retrata a preparação de 22/10. Foram preservados como histórico. A preparação anterior registra 38 testes aprovados; nesta revisão documental não houve alteração de código nem nova execução da suíte. Houve nova conferência independente de todas as associações da tabela.

## 3. Primeiro: combinar o significado de uma linha

O CSV original traz horários sem offset. O código os interpreta como **America/Sao_Paulo**, conforme o README; a tabela exportada traz `−03:00` neste período. Por exemplo, 14h local corresponde a 17h UTC. Associar o fuso a uma hora local é diferente de converter uma hora que já está em UTC. Não subtrair três horas manualmente.

Para o MVP, a convenção adotada é:

- `time = T`: referência das quatro entradas, tomada como instante de emissão no experimento.
- Entradas: temperatura (°C), umidade (%), pressão ao nível do mar (hPa) e nebulosidade (%), todas da linha T.
- `target_time = T+1h`: fim do intervalo que queremos prever.
- `rain_next_hour = 1` se `rain(T+1h) > 0 mm`; caso contrário, 0. Isso prevê **ocorrência**, não quantidade ou início de uma tempestade.

**Hipótese:** `rain(u)` representa `(u−1h, u]`. Assim, a resposta em 15h descreve chuva entre 14h e 15h. No exemplo real de **01/01/2020 14h**, entram 33,3 °C, 42%, 1005,3 hPa e 93%; a chuva registrada em 15h produz alvo 1. O casamento por horário foi comprovado; o significado físico da janela ainda depende da origem.

O alvo naturalmente consulta o futuro: é a resposta que será conhecida depois. O vazamento ocorreria se essa resposta, ou outra informação futura, fosse usada como entrada. Usar explicitamente apenas as quatro colunas de `WEATHER_FEATURES` em X e `rain_next_hour` em y. `time` e `target_time` servem para auditoria/divisão. Não colocar automaticamente todas as colunas em X.

## 4. Roteiro para revisar juntos

1. **Abrir a tabela e seu resumo.** Confirmar nome, hash, sete colunas, primeira/última hora e fuso. Se alguém tiver outra versão, resolver a diferença antes de escolher datas.
2. **Conferir a sequência.** Procurar horários repetidos, datas inválidas, ordem crescente e intervalos diferentes de uma hora. Comparar também com uma sequência horária esperada; uma contagem total correta pode esconder uma duplicata e uma ausência. A tabela atual passou nessas verificações.
3. **Conferir ausência e validade.** Contar vazios/não finitos por coluna, verificar umidade e nuvens em 0–100 e pressão positiva. Observar extremos sem removê-los automaticamente. Repetições dos mesmos valores meteorológicos em horas diferentes não são, por si só, duplicatas erradas. Chuva ausente nunca deve virar classe zero.
4. **Conferir algumas respostas.** Repetir o exemplo de 14h/15h no original, procurar um caso seco e uma virada de dia. Conferir `target_time = time + 1h`. O código busca o horário exato, não simplesmente a linha seguinte.
5. **Olhar cobertura e chuva por ano e por mês/ano.** Comparar horas existentes com horas esperadas do calendário; fevereiro e anos bissextos variam. Para chuva, usar quantidade de positivos dividida pelas linhas válidas, não apenas contagem bruta. Não mover datas para obter classes iguais ou uma avaliação mais fácil.

Contagens abaixo são por **ano de T**, antes de qualquer exclusão nas futuras fronteiras:

| Ano | Linhas | Alvo positivo | Percentual positivo |
|---|---:|---:|---:|
| 2020 | 8.784 | 1.293 | 14,72% |
| 2021 | 8.760 | 1.376 | 15,71% |
| 2022 | 8.760 | 1.648 | 18,81% |
| 2023 | 8.760 | 1.646 | 18,79% |
| 2024 | 8.784 | 1.439 | 16,38% |
| 2025 | 8.760 | 1.343 | 15,33% |
| 2026, janeiro–setembro | 6.551 | 1.375 | 20,99% |

Há **81 meses consecutivos**. 2020–2025 têm os 12 meses; 2026 não tem outubro–dezembro. Setembro/2026 tem 719 linhas elegíveis, pela exclusão da última hora. Agrupando todos os anos por mês de T, janeiro tem 30,41% de positivos e julho 5,24%. Essa diferença justifica cobrir épocas distintas do ano. Não prova causalidade nem representa uma climatologia de longo prazo. Os meses de outubro–dezembro agregam seis anos; janeiro–setembro, sete.

Há variação importante entre meses individuais: agosto/2025 tem 11 positivos em 744 horas (1,48%); fevereiro/2023, 321 em 672 (47,77%). Não selecionar o teste pelo mês com melhor equilíbrio. A taxa anual de 2026 também não deve ser comparada como se representasse um ano completo. Consultar os gráficos já existentes em `reports/figures/` e os resumos da EDA como apoio; eles descrevem a chuva do horário original, enquanto esta tabela descreve o alvo uma hora à frente.

## 5. Escolher os períodos pelo calendário

**Treino** ensina o modelo. **Validação** permite comparar escolhas de modelo, parâmetros e limiar de decisão. **Teste** responde, ao final, como o procedimento escolhido se comporta em um período posterior que não orientou essas escolhas.

Uma proposta simples, coerente com o protocolo anterior, é:

| Uso proposto | Período de referência T, horário local | Critério |
|---|---|---|
| Treino | 01/01/2020 00h até antes de 01/01/2025 00h | Cinco anos, várias repetições das estações |
| Validação | 01/01/2025 00h até antes de 01/01/2026 00h | Um ano completo para orientar escolhas |
| Teste | 01/01/2026 00h a 30/09/2026 22h | Período mais recente disponível, com limite de nove meses |

**São datas para discussão, não uma divisão aprovada ou executada.** Aplicar também a regra de fronteira da próxima seção. A justificativa é calendário, cobertura e ordem temporal; não porcentagens automáticas nem desempenho.

Se a prioridade for testar um ciclo anual completo, a alternativa é **treino 2020–2023, validação 2024, teste 2025**, deixando 2026 reservado para uma avaliação posterior adicional. Essa alternativa usa menos histórico no treino e não testa inicialmente o período mais recente. Escolher uma das propostas antes de experimentar modelos; não rodar ambas e divulgar apenas a mais favorável.

Não embaralhar toda a série nem distribuir horas da mesma época aleatoriamente entre os conjuntos. Não balancear o teste artificialmente: a proporção natural de chuva faz parte da avaliação.

## 6. Conferir as fronteiras pelos alvos

Para uma fronteira B, recomendo a regra conservadora: no conjunto anterior, manter apenas linhas com **`time < B` e `target_time < B`**. O seguinte começa em `time >= B`. Usar comparações com fuso explícito.

Exemplo na proposta principal: a linha **31/12/2024 23h** tem resposta em **01/01/2025 00h**. Pela regra, ela não entra no treino; a última linha de treino seria 31/12/2024 22h, com resposta às 23h. A validação começa em 01/01/2025 00h. Repetir isso entre validação e teste: retirar da seleção a linha de 31/12/2025 23h. Não apagar essas linhas da tabela original; futuramente registrar a exclusão na construção dos conjuntos.

A desigualdade estrita também retira o alvo que termina exatamente na fronteira. É uma escolha conservadora para não depender de uma resposta nesse instante. Em cada corte verificar: máximo `target_time` anterior menor que o início seguinte; nenhum T compartilhado; quantidades e horários excluídos registrados.

**Precisamos de um intervalo maior?** Não há exigência estrutural de vários dias no desenho atual: são quatro entradas em T, horizonte de uma hora, sem janelas móveis ou imagens compartilhadas. A regra já retira a linha de fronteira. Horas próximas continuam correlacionadas e uma mesma chuva pode persistir entre períodos; isso deve ser reconhecido, sem chamar toda correlação de vazamento.

Reavaliar um intervalo adicional se surgirem atrasos comprovados de publicação dos alvos, janelas temporais, novos horizontes ou o objetivo de avaliar eventos de chuva totalmente separados. Definir sua duração pela janela/latência e pelo objetivo, antes de olhar resultados do teste. Um intervalo arbitrário não torna reanálises historicamente disponíveis em T.

## 7. Depois da escolha: proteger a avaliação

Por enquanto não houve imputação nem normalização. Se necessárias, médias para preencher vazios, escalas, limites aprendidos dos dados e seleção de variáveis devem ser **ajustados somente no treino**. Aplicar as mesmas regras já aprendidas à validação e ao teste, sem recalculá-las nesses conjuntos. Caso contrário, o procedimento aprende algo sobre os dados que deveria prever.

Usar validação para escolher modelo e limiar; congelar essas escolhas antes de abrir as métricas do teste. Definir previamente métricas que mostrem acertos e erros de chuva, como precisão, revocação e matriz de confusão, além de comparar com sempre prever ausência de chuva. Acurácia isolada pode enganar quando predominam horas secas.

**Transparência:** a EDA já examinou descritivamente todo o período, inclusive os candidatos a teste. Portanto, não alegar que ninguém viu esses dados. A partir da escolha, reservá-los de decisões baseadas em desempenho: não ajustar modelo, atributos, limiar ou datas conforme o resultado final. Se esse resultado motivar mudanças, será necessária outra avaliação independente para avaliar essas mudanças sem reutilizar o mesmo teste.

## 8. Decisões a registrar ao final da conversa

- Escopo histórico experimental, fuso, emissão em T e hipótese de chuva em `(T,T+1h]`; responsável por investigar a origem.
- Alvo `rain(T+1h) > 0 mm` e quatro entradas; qualquer mudança exige nova versão documentada.
- Datas escolhidas, motivo, meses cobertos e limitação do teste parcial, se adotado.
- Regra estrita nas fronteiras e justificativa de haver ou não intervalo adicional.
- Versão/hash da tabela, futuras contagens por conjunto e exclusões de fronteira.
- Métricas, uso da validação e compromisso de reservar o teste para a avaliação final.

Após registrar essas decisões, a próxima implementação pode ser uma divisão cronológica pequena, legível e testada nas fronteiras. **Nesta revisão só foi criado este documento: nenhum dado, alvo, código, relatório anterior ou conjunto foi alterado.**

## Referências locais

- [Preparação do MVP](../../docs/prepare_weather.md) e [script responsável](../../scripts/prepare_weather.py).
- [Resumo da tabela](../../data/processed/weather_training.json) e [exclusões](../../data/processed/weather_training_excluded.csv).
- [README do conjunto de dados preservado](../../docs/dataset/README.md).
- [Auditoria](../dataset_audit.md), [EDA](../eda/eda_report.md) e [protocolo anterior](../protocol/protocol_proposal.md).
- [Proveniência e significado temporal ainda pendentes](../temporal/source_provenance_report.md).

Os dados são locais e ignorados pelo Git; seus links só funcionarão onde os arquivos estiverem disponíveis. Não foi necessário reler pixels GOES, instalar dependências ou consultar novas fontes externas para conferir o estado existente.
