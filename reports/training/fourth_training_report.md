# Relatório do quarto treinamento - v4

**Data da execução:** 03/11/2026 19:10 UTC  
**Experimento:** `weather_20261103T190835Z`  
**Script:** `scripts/archive/train_v4.py`  
**Avaliação do teste:** não executada nesta rodada.

## 1. Objetivo e escopo

Esta execução valida o fluxo corrigido da v4 e compara cinco classificadores para estimar `rain_next_hour` em Londrina. O conjunto de teste foi mantido fora da avaliação. Treino, seleção do limiar, métricas de validação e validação cruzada temporal usam somente dados anteriores a 2026.

Esta é uma avaliação retrospectiva e experimental. Não demonstra disponibilidade operacional das entradas nem qualidade de previsão em tempo real. A semântica temporal do campo de precipitação na fonte continua dependendo de confirmação documental.

## 2. Dados e separação temporal

Fonte: `data/processed/weather_training.csv`, 59.159 registros. SHA-256:

```text
a3ea57e03c9b66e575cecbcc47a673a9af69c7c6aeeb5d6f07a18b0e69b609d3
```

| Partição | Regra | Registros |
|---|---|---:|
| Treino | Antes de 01/01/2025 00:00, fuso de São Paulo | 43.847 |
| Validação | Ano de 2025; alvo antes de 01/01/2026 | 8.759 |
| Teste reservado | A partir de 01/01/2026 | 6.551 |
| Excluídos na fronteira | Alvo cruza limite temporal | 2 |

O alvo tem 1.343 positivos na validação (15,33%). A prevalência é menor que na base completa, portanto PR-AUC deve ser interpretada junto com a prevalência do período.

## 3. Código validado e configurações

Antes da execução foram corrigidos:

1. Ordenação cronológica antes do cálculo de `pressure_diff`.
2. Cálculo de importância por permutação quando a função recebe apenas um modelo.
3. Aplicação do parâmetro `beta` na seleção do limiar pela métrica F-beta (padrão: beta=1, equivalente a F1), registrando os resultados selecionados na validação.
4. Consistência do manifesto: lista completa das sete entradas, parâmetros dos modelos, hash da base, hashes dos joblibs e limiares selecionados.
5. O fluxo opcional de teste passou a gravar métricas probabilísticas e previsões; não foi acionado nesta execução.

As sete entradas usadas são as quatro originais: temperatura, umidade relativa, pressão e nebulosidade; e três derivadas:

- `temp_humidity`: temperatura × umidade;
- `pressure_diff`: pressão atual menos pressão no registro cronologicamente anterior;
- `hour_of_day`: hora local em São Paulo, de 0 a 23.

Se houver lacunas na série, `pressure_diff` é diferença em relação ao registro disponível anterior, que pode estar separado por mais de uma hora. O efeito dessa característica deve ser interpretado considerando essa possibilidade.

Compararam-se dois baselines, regressão logística com `StandardScaler` e dois Random Forests. Cada floresta usa 1.000 árvores, folha mínima 5 e semente 42; a balanceada usa `class_weight='balanced_subsample'`.

## 4. Resultados da validação em 2025

### Classificação no limiar 0,50

| Modelo | Acurácia | Precisão | sensibilidade | F1 | Falsos positivos | Falsos negativos |
|---|---:|---:|---:|---:|---:|---:|
| modelo de referência sempre seco | 84,67% | 0,00% | 0,00% | 0,00% | 0 | 1.343 |
| Random Forest original | 88,62% | 68,44% | 47,80% | 56,29% | 296 | 701 |
| modelo de referência por prior | 84,67% | 0,00% | 0,00% | 0,00% | 0 | 1.343 |
| Regressão logística | 84,24% | 47,89% | 31,20% | 37,78% | 456 | 924 |
| Random Forest balanceado | 86,49% | 54,74% | 68,80% | 60,97% | 764 | 419 |

No limiar 0,50, o balanceado identifica mais chuvas e deixa passar menos eventos, com aumento de falsos positivos. O original tem maior precisão e acurácia nessa validação. Não há vencedor universal sem definir o custo dos dois tipos de erro.

### Qualidade probabilística

| Modelo | PR-AUC ↑ | ROC-AUC ↑ | Brier ↓ | Log loss ↓ |
|---|---:|---:|---:|---:|
| Random Forest original | 0,6579 | 0,9044 | 0,0815 | 0,2598 |
| Random Forest balanceado | 0,6595 | 0,9053 | 0,0940 | 0,2919 |
| Regressão logística | 0,4371 | 0,8494 | 0,1027 | 0,3178 |
| modelo de referência sempre seco | 0,1533 | 0,5000 | 0,1533 | 5,5265 |
| modelo de referência por prior | 0,1533 | 0,5000 | 0,1301 | 0,4293 |

O balanceado tem PR-AUC e ROC-AUC ligeiramente maiores; o original tem Brier e log loss menores, indicando probabilidades mais bem avaliadas por essas métricas nesta validação. A diferença não autoriza declarar um modelo final.

### Limiares exploratórios selecionados na validação

Com beta=1, a busca selecionou limiar 0,32 para o Random Forest original (F1=0,6109) e 0,53 para o balanceado (F1=0,6128). Os valores foram otimizados e medidos no mesmo conjunto de validação, logo são exploratórios e tendem a ser otimistas. Não são limiares operacionais aprovados. Os limiares escolhidos para os modelos constantes não devem ser interpretados como política útil de previsão.

## 5. Validação cruzada temporal

Foram usadas partições cronológicas de 2023, 2024 e 2025; cada ano é avaliado por um modelo ajustado apenas nos dados anteriores. Média ± desvio-padrão entre as partições:

| Modelo | PR-AUC | ROC-AUC | Brier | sensibilidade @0,50 | F1 @0,50 |
|---|---:|---:|---:|---:|---:|
| Random Forest original | 0,6708 ± 0,0161 | 0,9072 ± 0,0065 | 0,0862 ± 0,0075 | 0,5265 ± 0,0613 | 0,5886 ± 0,0238 |
| Random Forest balanceado | 0,6712 ± 0,0163 | 0,9078 ± 0,0071 | 0,1014 ± 0,0148 | 0,7396 ± 0,0585 | 0,6304 ± 0,0164 |
| Regressão logística | 0,4662 ± 0,0205 | 0,8570 ± 0,0085 | 0,1068 ± 0,0068 | 0,4006 ± 0,0713 | 0,4487 ± 0,0525 |

O balanceado conserva sensibilidade e F1 mais altos na média dos anos, enquanto o original apresenta Brier médio menor. A validação cruzada informa estabilidade relativa entre as partições, mas não substitui uma avaliação futura intocada.

## 6. Importância por permutação

O código calculou queda média de PR-AUC na validação com cinco permutações por entrada. Nos dois Random Forests, `hour_of_day` e `cloud_cover` tiveram as maiores quedas observadas; por exemplo, no modelo original as médias foram 0,2266 e 0,2063. Isso descreve associação preditiva nessa validação, não causalidade meteorológica nem importância garantida em outro período.

## 7. Artefatos e reprodutibilidade

Todos os arquivos foram gravados em `data/experiments/weather_20261103T190835Z/`:

- cinco modelos: `baseline.joblib`, `baseline_prior.joblib`, `logistic.joblib`, `random_forest.joblib`, `random_forest_balanced.joblib`;
- `manifest.json`: versão do ambiente, fonte e hash, partições, sete entradas, configurações, hashes dos joblibs, limiares e indicação de execução da validação cruzada/teste;
- `split_summary.json`: contagens e limites temporais;
- `metrics_validation.json` e cinco `metrics_*_prob.json`;
- `thresholds.json`;
- `rolling_cv_summary.json`;
- `predictions_validation.csv`;
- `importance_*.json` para regressão logística e os dois Random Forests.

Os cinco joblibs foram recarregados e cada um reportou sete entradas. Os hashes foram conferidos contra o manifesto e o SHA-256 da tabela foi recalculado. O manifesto registra `test_evaluated: false`; não existem `metrics_test.json` nem `predictions_test.csv` neste experimento.

## 8. Validações executadas

- Suíte completa: **46 testes aprovados** nos ambientes `.venv` e `.venv-validacao`; `pip check` sem conflitos nos dois.
- `git diff --check`: aprovado.
- Integridade do manifesto, hash da fonte e hashes de todos os joblibs: aprovados.
- Carregamento de todos os cinco joblibs e verificação das sete entradas: aprovado.
- Execução do treino e dos três partições temporais: concluída.
- Teste de 2026: preservado, sem avaliação.

## 9. Conclusão e próximos passos

A execução corrigida da v4 está completa para treino, validação e validação cruzada, com artefatos verificáveis. O Random Forest balanceado apresenta melhor sensibilidade/F1; o original apresenta melhor calibração segundo Brier/log loss nesta validação. A decisão final depende do custo de falsos alarmes e de eventos não detectados.

Antes de integração: confirmar a semântica de `rain` na fonte; definir qual modelo e limiar atendem ao uso; reservar dados futuros ainda não consultados para avaliação independente; e garantir que a transformação das sete entradas seja aplicada exatamente igual no serviço de retaguarda. A API, a persistência e a interface continuam fora desta execução.
