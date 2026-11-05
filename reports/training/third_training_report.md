# Relatório de Treinamento – Terceira Execução

**Data:** 31/10/2026 11:22 (UTC)  
**Diretório do experimento:** `data/experiments/weather_20261031T112237Z`

## 1. Fonte de Dados
- **Arquivo:** `data/processed/weather_training.csv`
- Conjunto já foi limpo e preparado pelo fluxo de pré‑processamento do projeto.
- **Divisão temporal:**
  - Treino até `2025‑01‑01 00:00:00‑03:00`
  - Validação de `2025‑01‑01` a `2026‑01‑01`
  - Teste a partir de `2026‑01‑01` (não avaliado nesta rodada).
- **Estatísticas de prevalência:**
  - Treino: 16,9 % de horas com chuva
  - Validação: 15,3 % de horas com chuva
  - Teste: 20,9 % de horas com chuva

## 2. Modelos Treinados
| Modelo | Tipo | Principais hiper‑parâmetros alterados |
|--------|------|----------------------------------------|
| `baseline` | Dummy (constante 0) | — |
| `baseline_prior` | Dummy (probabilidade da taxa base) | — |
| `logistic` | Regressão Logística (cadeia com `StandardScaler`) | `max_iter=2000`, `random_state=42` |
| `random_forest` | Random Forest original – **versão pesada** | `n_estimators=500`, `max_depth=None` (cresce até pureza), `min_samples_leaf=5`, `n_jobs=-1`, `class_weight=None` |
| `random_forest_balanced` | Random Forest balanceado – **versão pesada** | `n_estimators=500`, `max_depth=None`, `min_samples_leaf=5`, `class_weight='balanced_subsample'`, `n_jobs=-1` |

## 3. Métricas de Validação (conjunto de validação)
### 3.1 Métricas clássicas
| Modelo | Acurácia | Precisão (chuva) | sensibilidade (chuva) | F1 (chuva) | Acurácia balanceada | Especificidade | MCC |
|--------|----------|------------------|----------------|------------|-------------------|----------------|-----|
| modelo de referência | 0.8467 | 0.0 | 0.0 | 0.0 | 0.50 | 1.0 | 0.0 |
| baseline_prior | 0.8467 | 0.0 | 0.0 | 0.0 | 0.50 | 1.0 | 0.0 |
| logistic | 0.8329 | 0.433 | 0.293 | 0.349 | 0.612 | 0.931 | 0.264 |
| random_forest | 0.8426 | 0.482 | 0.366 | 0.416 | 0.648 | 0.929 | 0.332 |
| random_forest_balanced | **0.8063** | **0.417** | **0.662** | **0.512** | **0.747** | **0.832** | **0.415** |

### 3.2 Métricas baseadas em probabilidade (validação)
| Modelo | PR‑AUC | ROC‑AUC | Brier |
|--------|--------|----------|-------|
| logistic | 0.378 | 0.850 | 0.109 |
| random_forest | 0.491 | 0.863 | 0.107 |
| random_forest_balanced | **0.494** | **0.863** | **0.135** |

### 3.3 Validação Cruzada Cronológica (anos 2023‑2025)
| Modelo | PR‑AUC (média ± dp) | ROC‑AUC (média ± dp) | Brier (média ± dp) | Precisão @0.5 (média) | sensibilidade @0.5 (média) |
|--------|----------------------|----------------------|--------------------|----------------------|---------------------|
| random_forest | 0.491 ± 0.031 | 0.863 ± 0.009 | 0.107 ± 0.007 | 0.516 ± 0.033 | 0.454 ± 0.074 |
| random_forest_balanced | 0.494 ± 0.031 | **0.863** ± 0.009 | 0.135 ± 0.014 | 0.433 ± 0.014 | **0.743** ± 0.075 |
| logistic | 0.438 ± 0.025 | 0.850 ± 0.006 | 0.109 ± 0.006 | 0.490 ± 0.040 | 0.400 ± 0.083 |
| modelo de referência | 0.168 ± 0.014 | 0.500 ± 0.000 | 0.168 ± 0.014 | 0.0 | 0.0 |
| baseline_prior | 0.168 ± 0.014 | 0.500 ± 0.000 | 0.140 ± 0.010 | 0.0 | 0.0 |

## 4. Análise e Decisão
- O **Random Forest balanceado** apresentou a **maior sensibilidade (0.662)** e um **F1** superior (0.512) apesar de menor acurácia geral; isso indica que ele captura a maioria dos eventos de chuva, o que costuma ser desejável em sistemas de alerta meteorológico.
- O **Random Forest original** tem acurácia ligeiramente maior e um melhor balanço entre precisão e sensibilidade (precisão ≈ 0.48, sensibilidade ≈ 0.37).
- A **Regressão Logística** oferece um ponto intermediário, com boa especificidade e ROC‑AUC acima de 0.85, mas a sensibilidade ainda é baixa.
- Os modelos *modelo de referência* e *baseline_prior* servem apenas como referência mínima.

### Recomendações
1. **Selecionar o `random_forest_balanced`** se a prioridade for minimizar falsos negativos (não perder chuvas).  
2. Caso seja necessário um compromisso maior entre precisão e sensibilidade, o `random_forest` pode ser considerado.
3. Avaliar o custo operacional de usar 500 árvores sem limite de profundidade; se o tempo de inferência for crítico, pode‑se reduzir `max_depth` ou `n_estimators` e re‑treinar.
4. Gerar um modelo final treinado em **todos os dados disponíveis** (treino + validação) usando os mesmos hiper‑parâmetros do modelo escolhido antes de colocar em produção.

## 5. Arquivos Gerados
- `split_summary.json`
- `manifest.json`
- `metrics_validation.json`
- `metrics_validation_extended.json`
- `rolling_cv_summary.json`
- `predictions_validation.csv`

> **Observação:** todos os arquivos acima estão dentro da pasta do experimento citada no início deste relatório.
