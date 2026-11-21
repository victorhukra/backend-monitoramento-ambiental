# Próximas etapas e plano de elegibilidade

Etapa 6 — 15/10/2026. Proposta para discussão; não aplicada ao conjunto de dados.

## Menor tarefa que desbloqueia os alvos

**Obter do produtor um pacote mínimo de proveniência meteorológica:** uma requisição original, a resposta correspondente e o trecho/versionamento do código que exportou time, rain e precipitation. Priorizar um trecho com chuva e virada de dia. Essa tarefa resolve uma incerteza que mais estatísticas do CSV não resolvem. Não foi enviado pedido a terceiros.

Critério de aceite: demonstrar para linhas específicas o intervalo de origem de cada quantidade, o timezone/offset, as conversões e eventuais deslocamentos, e justificar que esse caminho é válido para todo o período ou segmentá-lo por versão. Só depois aprovar definição de chuva/limiar e mapear intervalos completos para 1, 3, 6 e 7 horas. Se esse pacote não puder ser recuperado, um estudo sob hipótese explícita exige decisão metodológica; não chamar a hipótese de confirmação.

## Trabalhos seguintes, com critérios de saída

| Ordem | Tarefa | Evidência exigida para avançar |
|---|---|---|
| 1 | Rastrear exportação meteorológica | Requisição/resposta/código e comparação de linhas; sem ambiguidade do intervalo |
| 2 | Recuperar navegação de três produtos indicados no relatório geográfico e código/índices do recorte | x/y e projeção completos; correspondência comprovada netCDF↔NPZ por sensor/grade |
| 3 | Fixar região de Londrina e QA | Coordenada/área justificada, máscaras validadas por grade, cobertura mínima q e idade máxima A aprovadas |
| 4 | Escolher modalidade retrospectiva ou operacional | Logs e versões disponíveis, ou hipóteses de latência explicitamente identificadas |
| 5 | Aprovar protocolo de construção futura | Alvos A separados de B, timestamps exatos, tratamento de ausência, fronteiras por H e comparações em mesma coorte |

As etapas 1 e 2 podem ser investigadas independentemente. A etapa 1 desbloqueia a definição dos alvos meteorológicos; as etapas 2–4 são necessárias para o conjunto de dados combinado e suas alegações de uso. Nenhuma dessas aprovações foi presumida nesta entrega.

## Regra de elegibilidade proposta

Para imagem i, definir s_i (início), e_i (fim), c_i (criação), a_i (instante documentado em que a versão completa estava recebida e utilizável), r_i (fração válida na região comprovada). Todos os instantes devem ser comparados em UTC e ter precisão preservada. Rejeitar/sinalizar metadados ausentes ou cronologia incoerente; não inventar horários. A>0 é idade máxima desde o fim da aquisição; q é cobertura regional mínima. Seus valores estão pendentes, não escolhidos arbitrariamente.

**Modalidade operacional, somente com evidências:** exigir s_i≤e_i≤c_i≤a_i≤t, 0≤t−e_i≤A, r_i≥q e ao menos um pixel válido, além de navegação, unidade e qualidade necessárias verificadas. a_i deve incluir ingestão e qualquer processamento necessário para uso. Selecionar a imagem de maior e_i entre as elegíveis; desempatar deterministicamente por c_i e nome, usando apenas versões comprovadamente disponíveis em t. Não usar revisão posterior do mesmo produto. Conservar IDs e motivo de elegibilidade.

Hoje, essa regra é uma especificação defensável, mas **não uma seleção operacional comprovável**: faltam a_i e qualidade regional. End/criação≤t é condição necessária, não suficiente. O timestamp do NPZ informa início, não o momento de observação individual de cada pixel nem o recebimento da imagem completa.

**Modalidade retrospectiva com hipótese:** definir a_i*=max(e_i,c_i)+L, L≥0, como atraso residual simulado incluindo publicação/ingestão/processamento. Exigir cronologia coerente, a_i*≤t, idade e QA regional. Registrar L, A, q, fonte das escolhas e eventual análise de sensibilidade pré-especificada; L=0 também é hipótese, não fato. Não estimar esses parâmetros pelo desempenho no teste. Essa simulação não resolve por si só a disponibilidade/revisão da meteorologia histórica.

**Ausência:** se nenhuma imagem passar, manter motivo explícito de ausência. Não escolher imagem futura, preencher por zero, alterar image_link ou reutilizar imagem antiga fora da idade máxima silenciosamente. Uma eventual nova associação deve ter coluna própria e registro de s/e/c/a, versão, idade, grade, máscara e qualidade. A regra ainda não foi aplicada nem mesmo como associação experimental em massa.

Meteorologia precisa de controle paralelo: suporte temporal terminado até t e versão recebida até t. Campos futuros, inclusive código meteorológico derivado da precipitação futura, não podem compor entradas. Para alvos A, exigir as horas futuras exatas conforme a semântica confirmada; não fazer shift posicional para transpor lacunas. Fronteiras de avaliação devem impedir compartilhamento de intervalos-alvo entre períodos, considerando H, lags e reuso de imagens. Não foram criadas partições.

## Respostas às sete perguntas da etapa

1. **Confirmamos a semântica de rain/precipitation?** Não; hora anterior é compatível com a documentação, mas não comprovada para a exportação local.
2. **Identificamos origem e transformação do CSV?** Origem declarada no README: Open-Meteo histórico. Requisição, modelo/configuração exata e transformação não recuperados.
3. **Geolocalizamos os pixels GOES?** Não. Confirmamos metadados de três representantes e nomes dos originais; a navegação e o recorte ainda não estão validados.
4. **O que falta para região fixa?** x/y e projeção completos, vínculo do recorte ao original, validação por sensor/grade e definição explícita da região/ponto de referência.
5. **Qual regra é sustentada?** Não admitir fim/criação depois de t; exigir também disponibilidade documentada, idade máxima e qualidade regional para uma alegação operacional. Latência simulada só sustenta um cenário retrospectivo declarado.
6. **O que impede os alvos supervisionados?** Falta confirmar qual intervalo cada acumulado representa e aprovar variável/limiar. Disponibilidade e geolocalização são bloqueios adicionais do conjunto de dados combinado, não justificativas para confundir alvo com entrada.
7. **Menor próxima tarefa?** Recuperar e rastrear o pacote meteorológico original mínimo da seção inicial; solicitar em paralelo o código de recorte GOES se estiver com o mesmo produtor.

## Verificação desta entrega

Inventário executado com sucesso após corrigir a chamada ao helper existente `scalar`. Suíte preservada: **27 testes aprovados**, saída em `tests.txt`. Não foram introduzidas novas funções de cálculo que exigissem novos testes unitários; o script diagnóstico reutiliza os helpers existentes e contém verificações de limite e preservação. A tentativa de HEAD dos três produtos falhou por DNS e está registrada; não se concluiu ausência no servidor.

Arquivos novos ficam em `reports/temporal/` e `src/data/provenance_inventory.py`. Não houve instalação, extração de ZIP, processamento de pixels em massa, alvo, atributos regionais ou modelo. Os relatórios interpretativos devem ser revisados se novas evidências forem adicionadas; executar novamente o inventário não atualiza automaticamente suas conclusões.
