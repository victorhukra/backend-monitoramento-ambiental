# Proposta enxuta — dos dados meteorológicos e GOES ao primeiro modelo

**Data: 21/10/2026. Status: proposta de execução, não processamento concluído.**

## 1. Resposta direta: já poderemos treinar?

**Resolver o recorte espacial e a associação das imagens ao instante T remove dois bloqueios importantes, mas ainda não conclui o processamento.** Depois precisamos extrair as características, montar a tabela combinada, definir corretamente a resposta futura e separar os períodos de avaliação.

Essas tarefas devem formar um fluxo curto, sem abrir novas frentes de investigação indefinidamente. Com a tabela verificada e as hipóteses registradas, poderemos iniciar o treinamento experimental. Não será necessário provar a viabilidade de um sistema operacional completo antes do primeiro experimento retrospectivo.

## 2. Escopo mínimo proposto

Entregar um **protótipo histórico integrado**, capaz de receber um instante T do período preparado e retornar uma probabilidade de chuva para a hora seguinte, usando meteorologia e características GOES.

- Uma localização: região fixa em torno de Londrina.
- Um horizonte inicial proposto: próxima hora. Os horizontes de 3, 6 e 7 horas ficam para uma expansão posterior.
- Uma representação simples da imagem: cinco estatísticas dos pixels válidos da região, sem rede neural de imagens.
- Um procedimento de treinamento tabular, executado com e sem GOES para medir seu acréscimo de informação.
- Uma integração simples entre backend, banco e front-end.

O prazo mencionado é o dia 3; o mês e a exigência de previsão no horário atual ainda precisam ser confirmados. A entrega aqui proposta é histórica. Se a apresentação exigir operação no presente, aquisição e atualização das entradas passam a ser trabalho adicional, com impacto no prazo.

## 3. Como simplificar os dois problemas

### Localização das imagens

O caminho já aceito na conversa é utilizar provisoriamente os parâmetros de projeção, limites e orientação do README original. Vamos visualizar um exemplo de cada grade, marcar Londrina e conferir o recorte antes de ampliar o processamento.

A região deverá ser a mesma em coordenadas geográficas, com índices próprios em cada grade. Não vamos assumir que a imagem inteira representa apenas Londrina, nem que índices iguais correspondem ao mesmo lugar. Centro e extensão da região precisam ser fixados e documentados antes de avaliar modelos.

**Limitação assumida:** seguimos os metadados do autor sem validação geográfica independente completa. A conferência visual pode detectar problemas evidentes, mas não transforma essa hipótese em localização comprovada. Se aparecer uma contradição, investigaremos esse caso antes de continuar.

### Imagem disponível no instante T

T será a hora cheia de emissão da previsão. Preservaremos o `image_link` original, mas faremos uma associação separada com uma imagem anterior elegível.

```text
disponibilidade simulada = máximo(fim da aquisição, criação) + atraso assumido

Uma imagem só pode ser candidata quando:
- os horários de aquisição/criação são coerentes;
- disponibilidade simulada ≤ T;
- idade desde o fim da aquisição ≤ limite definido;
- o recorte tem pixels válidos e cobertura suficiente.
```

Entre as candidatas, selecionar a de aquisição concluída mais recentemente, com desempate determinístico. Se não houver candidata, registrar ausência; não utilizar uma futura nem preencher suas características com zeros. Atraso, idade máxima e cobertura mínima serão parâmetros explícitos, ainda a definir, sem escolhê-los pelo desempenho no teste.

Essa regra representa uma simulação retrospectiva. Não prova disponibilidade histórica real, e não resolve por si só as limitações das variáveis meteorológicas derivadas de reanálise.

## 4. O trabalho mínimo que ainda falta

| Passo | O que fazer | Entrega verificável |
|---|---|---|
| 1. Fixar o pequeno protocolo | Região, horizonte, definição de chuva, atraso/idade/qualidade e período inicial | Uma configuração e uma descrição curta das hipóteses |
| 2. Validar exemplos | Conferir recortes, pixels inválidos e associação temporal em poucos casos | Exemplos compreensíveis pela equipe, incluindo falhas |
| 3. Extrair e combinar | Calcular média, desvio padrão populacional, mínimo, máximo e mediana em Kelvin; unir à meteorologia por T | Uma tabela local com entradas e rastreabilidade |
| 4. Construir a resposta futura | Associar a quantidade de chuva ao intervalo correto por timestamp exato | Coluna de ocorrência futura, sem usá-la como entrada |
| 5. Verificar e separar | Conferir ausências/duplicatas, contar eventos e separar períodos cronológicos | Treino, validação e teste sem compartilhamento dos intervalos-alvo |
| 6. Treinar o primeiro experimento | Comparar meteorologia com meteorologia + GOES nos mesmos exemplos | Modelo salvo, avaliação e formato de entrada definido |

**Decisão temporal ainda pendente:** a hipótese é que `rain`/`precipitation` em u resume a hora anterior. Sob essa hipótese, para emissão às 14h e previsão entre 14h e 15h, a quantidade usada para definir a resposta vem do registro das 15h. Não basta deslocar uma linha sem verificar o horário.

Tentaremos confirmar essa convenção na origem. Se a comprovação não chegar a tempo, seguir com ela exige alinhamento explícito com o professor e identificação do resultado como experimento condicionado. A concordância sobre o recorte GOES não equivale à aprovação dessa outra hipótese.

Para simplificar, a primeira tabela poderá usar somente exemplos completos que cumpram os critérios, sem imputação automática. Os originais permanecem intactos; devemos registrar quantos exemplos ficaram de fora, por quê e em quais períodos. Essa seleção pode alterar a representatividade da avaliação.

## 5. Quando considerar a preparação concluída

Podemos liberar o treinamento quando:

- A equipe consegue explicar uma linha da tabela: o que era entrada em T e qual intervalo constitui a resposta futura.
- As cinco características GOES foram calculadas no recorte definido e não incluem pixels inválidos.
- Nenhuma imagem selecionada viola a regra temporal adotada.
- As hipóteses, parâmetros e critérios de ausência estão registrados; a definição de chuva foi aprovada.
- Há exemplos com e sem chuva em quantidade avaliada como suficiente nos períodos de desenvolvimento e teste. Isso ainda será contado, não presumido.
- A separação respeita a cronologia, as fronteiras dos alvos e o reuso de imagens; transformações aprendidas, se necessárias, são ajustadas apenas no treino.

Cumprir esses itens conclui a preparação **para o primeiro experimento**, não a validação científica final nem a construção de um serviço em tempo real. Não precisamos processar os 73 GB antes de verificar esse fluxo em um período menor; também não devemos chamar um teste com poucas imagens de avaliação preditiva suficiente.

## 6. Backend, banco e front-end trabalhando em paralelo

O processamento pesado e o treinamento acontecem previamente. A aplicação não deve abrir o acervo inteiro nem retreinar a cada requisição.

```text
Preparação: CSV + NPZ → tabela combinada → treinamento → modelo salvo
Aplicação: front-end → backend → dados preparados/modelo → resposta e registro no banco
```

**Backend:** preparar entradas, carregar o modelo e calcular a probabilidade. **Banco:** armazenar as entradas/resultados necessários e seus identificadores temporais. **Front-end:** solicitar e apresentar a previsão, mostrando localização, emissão, intervalo futuro e indicação de simulação histórica.

Alinhar primeiro um contrato pequeno: localização, T, horizonte, probabilidade, versão do modelo e estado do resultado. Quando faltarem dados, retornar indisponibilidade, não probabilidade zero. Antes de existir um modelo, uma resposta de exemplo pode apoiar a integração, desde que seja claramente identificada como fictícia.

## 7. Controle da complexidade

Vamos reutilizar leitura, reconstrução GOES, verificações e testes existentes. Auditoria e EDA permanecem como apoio; não entram em toda chamada da aplicação. A refatoração deve se limitar às dependências necessárias ao fluxo principal, sem reescrever todo o projeto.

Para cada alteração, explicar **entrada → operação → saída** com um exemplo pequeno. A equipe deve conseguir executar e compreender cada etapa antes de aumentar a escala. Não acrescentar múltiplos modelos, vários horizontes, redes neurais, serviços separados ou infraestrutura sem necessidade demonstrada para essa entrega.

**Próxima ação proposta:** fechar os poucos parâmetros pendentes e executar um piloto de ponta a ponta que produza uma pequena tabela meteorologia + GOES. Só então ampliar o período e iniciar o treinamento. Este documento não autoriza silenciosamente hipóteses pendentes nem registra como executadas essas novas etapas.

### Referências do projeto

- [Piloto GOES](../pilot/goes_pilot_report.md).
- [Viabilidade dos horizontes](../horizons/horizon_feasibility_report.md).
- [Investigação da geolocalização](../temporal/goes_geolocation_report.md).
- [Proveniência temporal](../temporal/source_provenance_report.md).

Esta proposta registra a simplificação discutida posteriormente: uso condicionado dos metadados do README para o protótipo, sem apagar as limitações documentadas nas etapas anteriores.
