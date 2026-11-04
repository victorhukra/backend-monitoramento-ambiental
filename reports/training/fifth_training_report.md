# Relatório do quinto treinamento - comparação v5

**Projeto:** MVP meteorológico de Londrina/PR  
**Data da execução:** 04/11/2026 12:23 UTC  
**Experimento:** `weather_v5_20261104T120000Z`  
**Script:** `scripts/train_v5.py`  
**Pergunta:** qual configuração de Random Forest apresenta o melhor compromisso entre discriminação, calibração e estabilidade temporal?  
**Avaliação do teste:** executada em 04/11/2026 nos quatro modelos finais, em 6.551 registros de 2026. Retrospectiva; não usada para seleção ou ajuste.

## 1. Objetivo e escopo

A v5 comparou 12 configurações de Random Forest em quatro avaliações cronológicas anuais (2022 a 2025), repetidas com três sementes. Foram realizados 144 ajustes de validação, além de ajustes finais dos quatro melhores candidatos por família. Depois que a seleção foi concluída e os joblibs foram congelados, os quatro candidatos finais foram avaliados uma vez no período de 2026.

Pela regra definida antes da comparação - maior PR-AUC média; entre candidatos a até 0,002 do maior valor, menor Brier e depois menor variação de PR-AUC - a escolha técnica foi **Random Forest original, sem pesos de classe, com `min_samples_leaf=10` e 400 árvores**. Sua PR-AUC média foi 0,67198, Brier 0,08860 e recall médio no limiar 0,50 de 0,54255.

O melhor candidato balanceado por amostra foi `balanced_subsample_leaf10_trees400`: PR-AUC 0,67268, Brier 0,11695 e recall 0,81075. Portanto, sua discriminação média foi ligeiramente maior e sua detecção de chuva foi substancialmente maior, mas as probabilidades foram menos bem calibradas segundo Brier e a política de limiar 0,50 produziu mais falsos alarmes. Os dados não sustentam um vencedor operacional universal sem definir o custo de cada tipo de erro.

## 2. Dados e divisão temporal

A fonte usada foi a tabela preparada completa `data/processed/weather_training.csv`, com 59.159 linhas e sete entradas (quatro originais e três derivadas). O CSV meteorológico bruto não está presente na pasta `data/raw` deste ambiente, portanto esta execução usou a base preparada que já integra o projeto. O SHA-256 da fonte foi registrado no manifesto:

```text
a3ea57e03c9b66e575cecbcc47a673a9af69c7c6aeeb5d6f07a18b0e69b609d3
```

Cada fold usa treino expansivo anterior ao ano avaliado. A linha só entra no treino se `target_time` ficar antes do início do ano de validação; a validação só inclui linhas cujo `time` e `target_time` permanecem dentro daquele ano. Essa regra evita que o alvo atravesse a fronteira temporal.

| Ano avaliado | Treino permitido | Sementes | Ajustes candidatos |
|---|---|---:|---:|
| 2022 | dados anteriores a 2022 | 17, 42, 2025 | 36 |
| 2023 | dados anteriores a 2023 | 17, 42, 2025 | 36 |
| 2024 | dados anteriores a 2024 | 17, 42, 2025 | 36 |
| 2025 | dados anteriores a 2025 | 17, 42, 2025 | 36 |

O conjunto de 2026 não foi usado para ajustar configurações, selecionar o candidato, escolher limiar ou treinar os joblibs finais. Após congelar os candidatos e os joblibs, a v5 avaliou esse período uma vez e gravou métricas e previsões. O histórico do projeto registra consultas anteriores ao período de teste de 2026; portanto, os resultados são retrospectivos e não constituem um teste independente intocado.

## 3. Código e configurações

As 12 configurações cobrem:

- pesos de classe ausentes (Random Forest original), `balanced`, `balanced_subsample` e peso positivo manual 2:1;
- `min_samples_leaf` igual a 5 ou 10;
- 400 árvores para toda a grade de pesos/folhas; comparação adicional com 250 e 800 árvores para original e `balanced_subsample`, com folha mínima 5.

As demais opções foram mantidas iguais: profundidade sem limite explícito, `max_features='sqrt'`, bootstrap ativado e sementes fixas. Essa grade permite isolar os efeitos de pesos, folha mínima e quantidade de árvores em um orçamento manejável. Não é uma busca exaustiva de hiperparâmetros.

As sete entradas são as mesmas documentadas na v4: temperatura, umidade relativa, pressão, nebulosidade, produto temperatura x umidade, diferença cronológica da pressão e hora local. A diferença de pressão continua sujeita à ressalva de lacunas na série.

## 4. Critério e resultados da validação temporal

A métrica primária foi PR-AUC, mais informativa que acurácia isolada em uma base com classes desiguais. Para empate prático, definido como diferença de até 0,002 na PR-AUC média, a regra prefere menor Brier e, depois, menor desvio-padrão de PR-AUC. Recall, precisão e F1 são apresentados no limiar fixo 0,50; nenhum limiar foi otimizado sobre os folds.

Os valores abaixo são médias das quatro validações anuais e três sementes. O desvio-padrão de PR-AUC agrega variação de ano e semente; não deve ser lido como erro padrão de observações independentes.

| Candidato | PR-AUC média (DP) | Brier médio | Precisão @0,50 | Recall @0,50 | F1 @0,50 | FP médios/ano | FN médios/ano |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Original, folha 10, 400 árvores** | **0,67198 (0,01359)** | **0,08860** | 0,67249 | 0,54255 | 0,59570 | 425 | 686 |
| `balanced_subsample`, folha 10, 400 | 0,67268 (0,01358) | 0,11695 | 0,50856 | 0,81075 | 0,62309 | 1.219 | 281 |
| `balanced`, folha 10, 400 | 0,67119 (0,01432) | 0,12808 | 0,47769 | 0,84769 | 0,60951 | 1.436 | 225 |
| Peso positivo 2:1, folha 10, 400 | 0,67170 (0,01392) | 0,09701 | 0,58194 | 0,70304 | 0,63377 | 794 | 443 |
| Original, folha 5, 400 | 0,66712 (0,01592) | 0,08902 | 0,66549 | 0,54514 | 0,59485 | 439 | 683 |
| `balanced_subsample`, folha 5, 250 | 0,66782 (0,01521) | 0,10557 | 0,54657 | 0,75507 | 0,63156 | 981 | 365 |

FP = falsos positivos; FN = falsos negativos. Contagens são médias entre os quatro anos e três sementes, arredondadas. A configuração balanceada recupera mais positivos, mas aumenta bastante os falsos alarmes. O peso positivo manual 2:1 oferece um ponto intermediário nessa comparação.

### Quantidade de árvores

Com folha mínima 5, passar de 250 para 400 ou 800 árvores pouco alterou os resultados médios:

| Família | Árvores | PR-AUC média | Brier médio | Recall @0,50 |
|---|---:|---:|---:|---:|
| Original | 250 | 0,66684 | 0,08903 | 0,54623 |
| Original | 400 | 0,66712 | 0,08902 | 0,54514 |
| Original | 800 | 0,66739 | 0,08898 | 0,54611 |
| `balanced_subsample` | 250 | 0,66782 | 0,10557 | 0,75507 |
| `balanced_subsample` | 400 | 0,66832 | 0,10550 | 0,75413 |
| `balanced_subsample` | 800 | 0,66859 | 0,10544 | 0,75372 |

Neste teste, mais árvores trouxeram ganhos pequenos. Aumentar o número de estimadores, sozinho, não resolveu a diferença de calibração nem eliminou o compromisso entre falsos positivos e falsos negativos.

### Avaliação retrospectiva no teste de 2026

Depois de concluída a seleção e congelados os quatro joblibs finais, os modelos foram avaliados uma vez nos 6.551 registros a partir de 01/01/2026. O período contém 1.375 positivos (taxa de chuva de 20,99%). O limiar permaneceu fixo em 0,50; o teste não alterou candidato, hiperparâmetros nem limiar.

| Candidato final | PR-AUC | ROC-AUC | Brier | Acurácia @0,50 | Precisão | Recall | F1 | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Original, folha 10, 400 árvores (selecionado na validação)** | **0,64577** | 0,88177 | **0,10904** | 0,83941 | **0,68585** | 0,43345 | 0,53119 | **273** | 779 |
| `balanced_subsample`, folha 10, 400 | 0,64234 | 0,88206 | 0,12542 | 0,81911 | 0,55011 | 0,75855 | **0,63773** | 853 | 332 |
| `balanced`, folha 10, 400 | 0,64261 | 0,88226 | 0,13535 | 0,80186 | 0,51795 | **0,80800** | 0,63125 | 1.034 | **264** |
| Peso positivo 2:1, folha 10, 400 | 0,64554 | **0,88228** | 0,11083 | **0,84033** | 0,61981 | 0,61891 | 0,61936 | 522 | 524 |

No período retrospectivo, o modelo original conservou a melhor PR-AUC entre os candidatos avaliados e teve o menor Brier, maior precisão e menos falsos positivos, mas deixou passar 779 positivos. `balanced_subsample` elevou o recall em 0,325 (0,759 contra 0,433) e reduziu os falsos negativos em 447, ao custo de 580 falsos positivos adicionais. O peso positivo 2:1 também apresentou compromisso intermediário. As diferenças pequenas de PR-AUC não devem ser tratadas como prova de superioridade em dados futuros, especialmente porque este período já havia sido consultado em ciclos anteriores.

## 5. Comparação pareada e incerteza

Para isolar o peso de classe, foi comparada a configuração convencional com a variante `balanced_subsample` mantendo folha 5, 400 árvores e as mesmas sementes. As probabilidades das três sementes foram calculadas em média por instante. Um bootstrap pareado de 2.000 réplicas reamostrou blocos de mês calendário, mantendo as observações horárias de cada bloco juntas.

As diferenças abaixo são **balanceado menos original**:

| Métrica | Diferença média | IC bootstrap percentil de 95% | Leitura |
|---|---:|---:|---|
| PR-AUC | +0,00117 | [-0,00155; +0,00409] | intervalo inclui zero; diferença de discriminação inconclusiva |
| Brier | +0,01648 | [+0,01293; +0,02036] | maior é pior; favorece o original |
| Recall @0,50 | +0,20838 | [+0,19365; +0,22257] | favorece fortemente o balanceado |

O bootstrap é uma estimativa descritiva condicionada a estes períodos, modelo e configuração. Ele não transforma os folds em amostra aleatória de anos futuros, não corrige a seleção de hiperparâmetros e não substitui validação prospectiva. É evidência de que o peso de classe muda principalmente o ponto de operação e a calibração, sem ganho claro de PR-AUC na configuração controlada.

## 6. Decisão recomendada

**Escolha técnica pelo critério registrado:** Random Forest original sem pesos de classe, `min_samples_leaf=10`, 400 árvores. O candidato balanceado tem PR-AUC apenas 0,00069 maior, dentro da margem de empate, enquanto o original tem Brier 0,02835 menor e comportamento com menos falsos positivos no limiar 0,50. Isso faz do original uma opção mais prudente quando a qualidade da probabilidade e o custo de alarme falso importam.

**Se a prioridade for não deixar passar chuva:** considerar `balanced_subsample`, folha 10 e 400 árvores. No limiar de 0,50, o recall médio foi 0,811 contra 0,543 do original, ao custo de aproximadamente 794 falsos positivos adicionais por ano de validação.

O resultado do teste retrospectivo é compatível com o compromisso visto na validação: original para menor taxa de alarmes falsos e melhor Brier; balanceado para maior detecção de chuva. Não foi definido um critério operacional mínimo de aprovação. Ainda faltam uma regra de custo/benefício dos erros, confirmação de que as entradas existem no momento T e confirmação da semântica temporal da precipitação. Como 2026 já havia sido consultado em etapas anteriores, a v5 não pode chamar este resultado de avaliação independente final. A aprovação operacional exige congelar modelo e limiar e avaliá-los em dados futuros ainda não vistos.

## 7. Artefatos e reprodutibilidade

Pasta experimental: `data/experiments/weather_v5_20261104T120000Z/`.

- Quatro joblibs finais, ajustados em todos os dados de desenvolvimento anteriores a 2026: melhor candidato original, melhor `balanced`, melhor `balanced_subsample`, melhor peso manual 2:1. O original é o campeão técnico pela regra de seleção.
- `manifest.json`: versões, SHA-256 da fonte e de cada joblib, sete entradas, grade de candidatos, anos, sementes, partição, critério de seleção e registro de que o teste de 2026 só foi usado após congelar os modelos, sem participar da seleção.
- `metrics_by_fold_seed.csv`: 144 linhas, uma por candidato, fold e semente.
- `candidate_summary.csv`: médias e desvios por candidato.
- `predictions_oof.csv`: 1.262.160 previsões out-of-fold, com instante, alvo, candidato, ano e semente.
- `paired_monthly_bootstrap.json` e `experiment_summary.json`: intervalos pareados e decisão técnica registrada.
- `metrics_test.json` e `predictions_test.csv`: avaliação retrospectiva dos quatro joblibs no período de 2026, com limiar fixo 0,50.

Os joblibs são arquivos locais ignorados pelo Git, por seu tamanho. Seus hashes no manifesto e a recarga com verificação de sete entradas permitem verificar integridade nesta máquina. O manifesto registra `test_evaluated: true`, `test_used_for_selection: false` e que o conjunto não é um teste cego independente. O CSV completo preparado também não é versionado.

## 8. Verificações executadas e referências

A configuração `balanced` usa pesos inversos às frequências de classe; `balanced_subsample` recalcula os pesos em cada amostra bootstrap da floresta. Esse comportamento está descrito na documentação oficial de `RandomForestClassifier`. A separação temporal foi adotada porque o objetivo é prever observações futuras; divisões aleatórias não representariam essa ordem. A PR-AUC segue a definição de Average Precision do scikit-learn. Referências:

- [RandomForestClassifier e pesos de classe](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- [TimeSeriesSplit e validação ordenada no tempo](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)
- [Average Precision / PR-AUC](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)

Foram executados **51 testes automatizados**, todos aprovados, incluindo cobertura da grade, dos limites temporais, das métricas, da gravação dos artefatos de teste e da proteção contra reutilizar o mesmo teste. `pip check` não encontrou dependências quebradas nos ambientes `.venv` e `.venv-validacao`; `git diff --check` também passou após as alterações. O SHA-256 da fonte e dos quatro joblibs confere com o manifesto. Os quatro modelos foram reabertos e cada um declara sete entradas. A execução registrou 144 linhas de métricas out-of-fold, 1.262.160 previsões out-of-fold e métricas/previsões para os 6.551 registros de teste. Os detalhes e hashes efetivos estão no manifesto do experimento.

## 9. Limitações e próximos passos

1. Registrar com a equipe se um falso alarme ou uma chuva não detectada tem maior custo; formalizar também uma taxa máxima de alertas aceitável.
2. Confirmar na documentação da fonte o intervalo temporal representado por `rain`/precipitação e quando cada entrada fica disponível.
3. Congelar a configuração e definir limiar usando somente desenvolvimento, sem ajustar sobre o período final.
4. Aguardar dados futuros não consultados para um teste prospectivo independente.
5. Confirmar com instalação limpa se o pipeline e os joblibs são reproduzíveis em outra máquina.

Até essas pendências serem resolvidas, a v5 melhora a evidência comparativa e fecha uma escolha técnica sob critério explícito, mas não comprova previsão operacional em tempo real.
