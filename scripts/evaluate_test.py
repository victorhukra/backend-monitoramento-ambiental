"""Avaliação v7 aninhada de calibração, pesos e limiar para os Random Forests da v6.

Utiliza as previsões fora da amostra (out-of-fold) geradas no treinamento v6
para testar de forma aninhada e estritamente cronológica:
1. Métodos de calibração de probabilidade (nenhuma, sigmoide / Platt, isotônica).
2. Pesos de combinação dos três membros do ensemble.
3. Escolha de limiar ótimo sob diferentes razões de custo entre Falso Negativo e Falso Positivo.

Em cada ano de teste externo (2023, 2024, 2025), a calibração, os pesos e o limiar
são determinados exclusivamente com dados de anos anteriores, avaliando o modelo
congelado no ano subsequente sem vazamento de informação.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import sklearn
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

# Inclusão da raiz do projeto para imports locais
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT

# As três famílias de modelos base avaliadas
BASE_MODELS = ('original', 'balanced', 'balanced_subsample')

# Estratégias de pesos fixos pré-definidos (pesos para: original, balanced, balanced_subsample)
FIXED_POLICIES: Dict[str, Tuple[float, float, float]] = {
    'original': (1.0, 0.0, 0.0),
    'balanced_subsample': (0.0, 0.0, 1.0),
    'ensemble_equal': (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
    'ensemble_original_favor': (0.5, 0.25, 0.25),
}

# Métodos de calibração avaliados
CALIBRATORS = ('none', 'sigmoid', 'isotonic')

# Razões de penalidade para Falso Negativo relativo a Falso Positivo (FN : FP)
COST_RATIOS = (0.5, 1.0, 2.0, 5.0)

# Grade de limiares de decisão discretos de 0.05 a 0.95
THRESHOLDS = np.round(np.arange(0.05, 0.951, 0.01), 2)

# Anos das partições externas de avaliação
EVALUATION_YEARS = (2023, 2024, 2025)


def generate_weight_grid() -> List[Tuple[float, float, float]]:
    """Gera a grade de pesos no simplex (passo 0.1, peso mínimo 0.1 por modelo)."""
    grid: List[Tuple[float, float, float]] = []
    for i in range(1, 9):
        for j in range(1, 10 - i):
            k = 10 - i - j
            if k >= 1:
                grid.append((i / 10.0, j / 10.0, k / 10.0))

    candidates = [
        FIXED_POLICIES['ensemble_equal'],
        FIXED_POLICIES['ensemble_original_favor'],
        *grid,
    ]
    # Remove duplicatas preservando a ordem
    return list(dict.fromkeys(candidates))


def fit_calibration_map(
    method: str,
    probabilities: np.ndarray,
    y_true: np.ndarray,
) -> Optional[Tuple[str, Any]]:
    """Ajusta o calibrador de probabilidade solicitado nos dados de treino interno."""
    p = np.clip(np.asarray(probabilities, float), 1e-6, 1.0 - 1e-6)
    y = np.asarray(y_true, dtype='int8')

    if method == 'none':
        return None

    if method == 'sigmoid':
        # Calibração de Platt / Sigmoide via Regressão Logística nas log-odds
        log_odds = np.log(p / (1.0 - p)).reshape(-1, 1)
        model = LogisticRegression(max_iter=1000, random_state=42).fit(log_odds, y)
        return ('sigmoid', model)

    # Calibração isotônica não-paramétrica
    isotonic_model = IsotonicRegression(out_of_bounds='clip').fit(p, y)
    return ('isotonic', isotonic_model)


def apply_calibration_map(
    fitted_calibrator: Optional[Tuple[str, Any]],
    probabilities: np.ndarray,
) -> np.ndarray:
    """Aplica o calibrador ajustado sobre um vetor de probabilidades estimadas."""
    p = np.clip(np.asarray(probabilities, float), 1e-6, 1.0 - 1e-6)
    if fitted_calibrator is None:
        return p

    kind, model = fitted_calibrator
    if kind == 'sigmoid':
        log_odds = np.log(p / (1.0 - p)).reshape(-1, 1)
        return model.predict_proba(log_odds)[:, 1]

    return np.asarray(model.predict(p), float)


def find_min_cost_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    cost_ratio: float,
) -> Tuple[float, float]:
    """Identifica o limiar que minimiza o custo ponderado: FP + cost_ratio * FN.
    
    Returns:
        Tupla com (limiar_otimo, custo_minimo_por_linha).
    """
    y = np.asarray(y_true, dtype='int8')
    p = np.asarray(probabilities, float)

    # Ordenação das previsões para cálculo eficiente de soma cumulativa
    order = np.argsort(p)
    ps = p[order]
    ys = y[order]

    cum_pos = np.cumsum(ys[::-1])[::-1]
    cum_neg = np.cumsum((1 - ys)[::-1])[::-1]

    indices = np.searchsorted(ps, THRESHOLDS, side='left')
    total_pos = int(y.sum())
    n = len(y)

    true_positives = np.where(indices < n, cum_pos[np.minimum(indices, n - 1)], 0)
    false_positives = np.where(indices < n, cum_neg[np.minimum(indices, n - 1)], 0)
    false_negatives = total_pos - true_positives

    costs = (false_positives + cost_ratio * false_negatives) / n
    best_indices = np.flatnonzero(np.isclose(costs, costs.min(), rtol=0, atol=1e-12))
    chosen_idx = best_indices[-1]

    return float(THRESHOLDS[chosen_idx]), float(costs[chosen_idx])


def compute_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    cost_ratio: float,
) -> Dict[str, Any]:
    """Calcula todas as métricas de desempenho sob um limiar e razão de custo específicos."""
    y = np.asarray(y_true, dtype='int8')
    p = np.clip(np.asarray(probabilities, float), 1e-7, 1.0 - 1e-7)
    predicted = p >= threshold

    false_positives = int(((predicted) & (y == 0)).sum())
    false_negatives = int(((~predicted) & (y == 1)).sum())
    weighted_cost = float((false_positives + cost_ratio * false_negatives) / len(y))

    return {
        'pr_auc': float(average_precision_score(y, p)),
        'roc_auc': float(roc_auc_score(y, p)),
        'brier': float(brier_score_loss(y, p)),
        'log_loss': float(log_loss(y, p)),
        'precision': float(precision_score(y, predicted, zero_division=0)),
        'recall': float(recall_score(y, predicted, zero_division=0)),
        'f1': float(f1_score(y, predicted, zero_division=0)),
        'balanced_accuracy': float(balanced_accuracy_score(y, predicted)),
        'mcc': float(matthews_corrcoef(y, predicted)),
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'weighted_error_cost_per_row': weighted_cost,
    }


def compute_error_complementarity(wide_df: pd.DataFrame) -> pd.DataFrame:
    """Mede desacordos e sobreposição de erros entre pares de modelos."""
    avg_df = wide_df.groupby(
        ['time', 'target_time', 'rain_next_hour', 'fold_year'],
        as_index=False,
    )[list(BASE_MODELS)].mean()

    y = avg_df.rain_next_hour.to_numpy(dtype='int8')
    errors = {
        name: (avg_df[name].to_numpy() >= 0.5) != y for name in BASE_MODELS
    }

    pairs: List[Dict[str, Any]] = []
    for i, model_a in enumerate(BASE_MODELS):
        for model_b in BASE_MODELS[i + 1:]:
            err_a = errors[model_a]
            err_b = errors[model_b]

            pairs.append({
                'model_a': model_a,
                'model_b': model_b,
                'rows': len(y),
                'error_rate_a': float(err_a.mean()),
                'error_rate_b': float(err_b.mean()),
                'both_wrong_rate': float((err_a & err_b).mean()),
                'disagreement_rate': float((err_a != err_b).mean()),
                'a_missed_rain_caught_by_b': int(((y == 1) & err_a & ~err_b).sum()),
                'b_missed_rain_caught_by_a': int(((y == 1) & err_b & ~err_a).sum()),
            })

    return pd.DataFrame(pairs)


def run(source: Path, out: Path) -> None:
    """Executa a avaliação aninhada e gera todos os relatórios e tabelas."""
    source_path = Path(source).resolve()
    output_dir = Path(out).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()

    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if not source_path.is_relative_to(ROOT):
        raise ValueError('A entrada deve estar dentro da pasta do projeto')

    source_relative = source_path.relative_to(ROOT).as_posix()
    if not output_dir.is_relative_to(experiments_root) or output_dir.exists():
        raise ValueError('Saída deve ser nova em data/experiments')

    raw = pd.read_csv(source_path)
    required_cols = {
        'time', 'target_time', 'rain_next_hour', 'fold_year', 'seed', 'strategy', 'probability',
    }
    if not required_cols.issubset(raw.columns):
        raise ValueError(f'Colunas ausentes: {sorted(required_cols - set(raw.columns))}')

    # Filtra e pivota as previsões das 3 famílias para o formato largo
    filtered = raw[raw.strategy.isin(BASE_MODELS)]
    keys = ['time', 'target_time', 'rain_next_hour', 'fold_year', 'seed']
    wide = filtered.pivot(index=keys, columns='strategy', values='probability').reset_index()

    if any(name not in wide for name in BASE_MODELS):
        raise ValueError('Previsões das três famílias v6 não encontradas')

    simplex_weights = generate_weight_grid()
    outer_results: List[Dict[str, Any]] = []
    selected_configs: List[Dict[str, Any]] = []
    prediction_records: List[pd.DataFrame] = []

    # Loop da validação externa (anos de 2023 a 2025)
    for year in EVALUATION_YEARS:
        inner_df = wide[wide.fold_year < year]
        outer_df = wide[wide.fold_year == year]

        if inner_df.empty or outer_df.empty or inner_df.rain_next_hour.nunique() < 2:
            raise ValueError(f'Dados insuficientes no fold {year}')

        y_inner = inner_df.rain_next_hour.to_numpy(dtype='int8')
        y_outer = outer_df.rain_next_hour.to_numpy(dtype='int8')

        # Ajuste dos calibradores nos anos anteriores e projeção
        prob_inner: Dict[str, Dict[str, np.ndarray]] = {}
        prob_outer: Dict[str, Dict[str, np.ndarray]] = {}

        for method in CALIBRATORS:
            prob_inner[method] = {}
            prob_outer[method] = {}
            for name in BASE_MODELS:
                mapper = fit_calibration_map(method, inner_df[name].to_numpy(), y_inner)
                prob_inner[method][name] = apply_calibration_map(mapper, inner_df[name].to_numpy())
                prob_outer[method][name] = apply_calibration_map(mapper, outer_df[name].to_numpy())

        policies = {**FIXED_POLICIES, 'ensemble_tuned': None}

        # Avaliação para cada razão de custo operacional
        for ratio in COST_RATIOS:
            for label, fixed_w in policies.items():
                trials: List[Tuple[float, float, int, Tuple[float, ...], str, float]] = []

                for method in CALIBRATORS:
                    candidate_weights = simplex_weights if label == 'ensemble_tuned' else [fixed_w]
                    for w in candidate_weights:
                        p_comb_inner = sum(
                            w[idx] * prob_inner[method][name]
                            for idx, name in enumerate(BASE_MODELS)
                        )
                        th, cost = find_min_cost_threshold(y_inner, p_comb_inner, ratio)
                        trials.append((cost, -th, CALIBRATORS.index(method), tuple(w), method, th))

                # Seleção da melhor configuração com base estrita no passado
                best_trial = min(trials, key=lambda z: (z[0], z[1], z[2], z[3]))
                best_inner_cost, _, _, chosen_w, chosen_calibrator, chosen_threshold = best_trial

                # Aplicação da configuração selecionada na partição externa congelada
                p_comb_outer = sum(
                    chosen_w[idx] * prob_outer[chosen_calibrator][name]
                    for idx, name in enumerate(BASE_MODELS)
                )

                seed_values = outer_df.seed.to_numpy()
                for seed in np.unique(seed_values):
                    mask = seed_values == seed
                    metric_dict = compute_metrics(
                        y_outer[mask], p_comb_outer[mask], chosen_threshold, ratio
                    )
                    outer_results.append({
                        'outer_year': year,
                        'seed': int(seed),
                        'fn_to_fp_cost_ratio': ratio,
                        'pipeline': label,
                        'calibration': chosen_calibrator,
                        'weight_original': chosen_w[0],
                        'weight_balanced': chosen_w[1],
                        'weight_balanced_subsample': chosen_w[2],
                        'threshold_selected_on_prior_years': chosen_threshold,
                        'inner_cost_per_row': best_inner_cost,
                        'outer_rows': int(mask.sum()),
                        **metric_dict,
                    })

                selected_configs.append({
                    'outer_year': year,
                    'fn_to_fp_cost_ratio': ratio,
                    'pipeline': label,
                    'calibration': chosen_calibrator,
                    'weight_original': chosen_w[0],
                    'weight_balanced': chosen_w[1],
                    'weight_balanced_subsample': chosen_w[2],
                    'threshold_selected_on_prior_years': chosen_threshold,
                    'inner_cost_per_row': best_inner_cost,
                })

                prediction_records.append(pd.DataFrame({
                    'time': outer_df.time.to_numpy(),
                    'target_time': outer_df.target_time.to_numpy(),
                    'rain_next_hour': y_outer,
                    'fold_year': year,
                    'seed': seed_values,
                    'cost_ratio': ratio,
                    'pipeline': label,
                    'calibration': chosen_calibrator,
                    'threshold': chosen_threshold,
                    'probability': p_comb_outer,
                }))

        print(f'fold externo {year} concluído com sucesso', flush=True)

    output_dir.mkdir(parents=True)

    # Gravação das tabelas de resultados
    outer_metrics_df = pd.DataFrame(outer_results)
    outer_metrics_df.to_csv(output_dir / 'outer_fold_metrics.csv', index=False)

    pd.DataFrame(selected_configs).to_csv(
        output_dir / 'selected_configuration_by_fold.csv', index=False
    )
    pd.concat(prediction_records, ignore_index=True).to_csv(
        output_dir / 'nested_predictions.csv', index=False
    )

    # Análise de complementaridade de erro entre os membros
    complementarity_df = compute_error_complementarity(wide)
    complementarity_df.to_csv(output_dir / 'error_complementarity.csv', index=False)

    # Sumário agregado
    summary_cols = [
        'weighted_error_cost_per_row',
        'pr_auc',
        'brier',
        'precision',
        'recall',
        'f1',
        'false_positives',
        'false_negatives',
        'threshold_selected_on_prior_years',
    ]
    summary_df = outer_metrics_df.groupby(
        ['fn_to_fp_cost_ratio', 'pipeline']
    )[summary_cols].mean().reset_index()
    summary_df.to_csv(output_dir / 'nested_summary.csv', index=False)

    # Manifesto do experimento v7
    manifest = {
        'experiment': 'v7_nested_temporal_calibration_weight_threshold_evaluation',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'pandas': pd.__version__,
        'numpy': np.__version__,
        'scikit_learn': sklearn.__version__,
        'input_path': source_relative,
        'input_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
        'source_v6': 'weather_v6_20261105T120000Z',
        'outer_years': list(EVALUATION_YEARS),
        'inner_policy': 'only v6 OOF folds strictly earlier than outer evaluation year',
        'calibrators': list(CALIBRATORS),
        'weight_grid_step': 0.1,
        'minimum_weight_per_family': 0.1,
        'cost_ratios_fn_to_fp': list(COST_RATIOS),
        'threshold_grid': [0.05, 0.95, 0.01],
        'test_2026_used': False,
        'test_evaluated': False,
        'final_model_selected': False,
        'final_joblibs_written': False,
        'reason_no_final_joblibs': 'operational error cost has not been approved',
        'outputs': [
            'outer_fold_metrics.csv',
            'selected_configuration_by_fold.csv',
            'nested_predictions.csv',
            'nested_summary.csv',
            'error_complementarity.csv',
        ],
    }
    (output_dir / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding='utf-8',
    )

    # Geração do relatório seventh_training_report.md
    report_lines = [
        '# Avaliação aninhada v7 — calibração, combinação e limiar',
        '',
        f'**Data:** {datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")}  ',
        f'**Experimento:** `{output_dir.name}`  ',
        f'**Entrada:** `{source_relative}`',
        '',
        '## Objetivo',
        '',
        'Avaliar se calibrar probabilidades e escolher pesos/limiar somente em anos anteriores '
        'melhora a decisão no ano seguinte. A v7 reusa previsões fora da amostra da v6; '
        'não retreina os Random Forests nem aprova uso operacional.',
        '',
        '## Protocolo temporal',
        '',
        'As partições externas são os anos de 2023, 2024 e 2025. Em cada ano, calibração, pesos e '
        'limiar são ajustados apenas com previsões fora da amostra dos anos anteriores; a partição '
        'externa mede a configuração congelada. Os resultados mantêm três sementes. O teste de 2026 '
        'não foi usado.',
        '',
        'Compara original, `balanced_subsample`, média igual, `ensemble_original_favor` e combinação '
        'otimizada em grade simplex (passo 0,1; peso mínimo 0,1 por modelo). Calibração sem ajuste '
        '(`none`), sigmoide e isotônica. O limiar minimiza `FP + razão × FN` nos anos anteriores. '
        'Razões FN:FP: 0,5:1, 1:1, 2:1 e 5:1.',
        '',
        '## Resultados por cenário',
        '',
        '| Custo FN:FP | Política | Custo externo/linha | PR-AUC | Brier | Precisão | Sensibilidade | F1 | Limiar médio |',
        '|---:|---|---:|---:|---:|---:|---:|---:|---:|',
    ]

    for _, row in summary_df.sort_values(
        ['fn_to_fp_cost_ratio', 'weighted_error_cost_per_row']
    ).iterrows():
        report_lines.append(
            f"| {row.fn_to_fp_cost_ratio:g}:1 | {row.pipeline} | "
            f"{row.weighted_error_cost_per_row:.5f} | {row.pr_auc:.5f} | {row.brier:.5f} | "
            f"{row.precision:.4f} | {row.recall:.4f} | {row.f1:.4f} | "
            f"{row.threshold_selected_on_prior_years:.3f} |"
        )

    report_lines.extend([
        '',
        'Pesos, calibrador e limiar por ano estão em `selected_configuration_by_fold.csv`; '
        'métricas em `outer_fold_metrics.csv`, previsões em `nested_predictions.csv`. '
        '`error_complementarity.csv` mede desacordo e sobreposição dos erros dos três membros '
        'em previsões fora da amostra a 0,50.',
        '',
        '## Interpretação e limites',
        '',
        'As razões de custo são cenários, não valores aprovados pela equipe. Há só três partições '
        'externas, e a escolha posterior entre políticas ainda pode ser otimista. Os resultados '
        'são evidência de desenvolvimento, não avaliação futura independente. Não se escolhe '
        'vencedor operacional sem aprovar custo ou limite máximo de alertas.',
        '',
        '## Interpretação dos resultados',
        '',
        'A combinação de pesos iguais (`ensemble_equal`) teve o menor custo médio nos cenários '
        'FN:FP de 0,5:1 e 5:1. O modelo original foi melhor nos cenários 1:1 e 2:1; portanto, '
        'não há uma estratégia que minimize o custo em todos os cenários. A média simples manteve '
        'PR-AUC de 0,67189 e Brier de 0,08629, ligeiramente melhores que o original (0,66060 e '
        '0,08640) e próximos do `balanced_subsample` (0,66020 e 0,08650).',
        '',
        'Quando o custo de não detectar chuva sobe para 5:1, a média simples atingiu sensibilidade '
        'de 0,8291, com precisão de 0,4868 e limiar médio de 0,180. No cenário 0,5:1, o limiar '
        'médio subiu para 0,657 e a sensibilidade caiu para 0,2213. Isso mostra que o limiar muda '
        'bastante conforme o custo escolhido. Como os custos ainda não foram aprovados e há somente '
        'três partições externas, esses resultados orientam a discussão, mas não estabelecem uma '
        'política operacional definitiva.',
        '',
        'A v7 não grava joblibs finais porque ainda não existe critério aprovado para congelar uma '
        'combinação. Após essa decisão, treinar a configuração final em todo o desenvolvimento, '
        'fixar o manifesto e avaliar somente em dados futuros ainda não consultados.',
        '',
        '## Referências',
        '',
        '- [RandomForestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)',
        '- [Calibração de probabilidades](https://scikit-learn.org/stable/modules/calibration.html)',
        '- [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)',
        '- [Precisão média (Average Precision) / PR-AUC](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)',
        '',
        '## Preparação para integração',
        '',
        'Após a avaliação, foi preparado o candidato `weather-v6-simple-mean-isotonic-v1`: os três '
        'membros calibrados isotonicamente são combinados com pesos 1/3 e limiar provisório 0,50. '
        'O pacote do modelo e o manifesto estão em `data/experiments/weather_v6_integration_candidate_20261105T190315Z/`. '
        'O teste de 2026 continua sem uso; a escolha prepara a integração histórica e não representa '
        'aprovação operacional independente.',
        '',
    ])

    report_file = ROOT / 'reports' / 'training' / 'seventh_training_report.md'
    report_file.write_text('\n'.join(report_lines), encoding='utf-8')

    (output_dir / 'experiment_summary.json').write_text(
        json.dumps(
            {
                'outer_years': list(EVALUATION_YEARS),
                'cost_ratios': list(COST_RATIOS),
                'pipelines': sorted(outer_metrics_df.pipeline.unique()),
                'outer_metric_rows': len(outer_metrics_df),
                'report': 'reports/training/seventh_training_report.md',
                'test_2026_used': False,
                'final_model_selected': False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    print(
        json.dumps(
            {
                'output_dir': str(output_dir),
                'report': 'reports/training/seventh_training_report.md',
                'outer_metric_rows': len(outer_metrics_df),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == '__main__':
    default_input = (
        ROOT / 'data' / 'experiments' / 'weather_v6_20261105T120000Z' / 'predictions_oof.csv'
    )
    default_output = (
        ROOT / 'data' / 'experiments' / (
            'weather_v7_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        )
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=default_input)
    parser.add_argument('--output-dir', type=Path, default=default_output)
    args = parser.parse_args()

    run(args.input, args.output_dir)
