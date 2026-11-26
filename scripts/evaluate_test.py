"""Avaliação v7 aninhada de calibração, pesos e limiar para os Random Forests da v6."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import sklearn
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, balanced_accuracy_score, brier_score_loss,
    f1_score, log_loss, matthews_corrcoef, precision_score, recall_score, roc_auc_score,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT

BASE_MODELS = ('original', 'balanced', 'balanced_subsample')
FIXED_POLICIES = {
    'original': (1.0, 0.0, 0.0),
    'balanced_subsample': (0.0, 0.0, 1.0),
    'ensemble_equal': (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
    'ensemble_original_favor': (0.5, 0.25, 0.25),
}
CALIBRATORS = ('none', 'sigmoid', 'isotonic')
COST_RATIOS = (0.5, 1.0, 2.0, 5.0)
THRESHOLDS = np.round(np.arange(0.05, 0.951, 0.01), 2)
EVALUATION_YEARS = (2023, 2024, 2025)


def generate_weight_grid():
    """Gera grade de pesos no simplex (passo 0,1; mínimo 0,1 por modelo)."""
    grid = [
        (i / 10.0, j / 10.0, (10 - i - j) / 10.0)
        for i in range(1, 9)
        for j in range(1, 10 - i)
        if 10 - i - j >= 1
    ]
    return list(dict.fromkeys([FIXED_POLICIES['ensemble_equal'], FIXED_POLICIES['ensemble_original_favor'], *grid]))


def fit_calibration_map(method, probabilities, y_true):
    """Ajusta calibrador (none, sigmoid ou isotonic) nas previsões de treino interno."""
    p = np.clip(np.asarray(probabilities, float), 1e-6, 1.0 - 1e-6)
    y = np.asarray(y_true, dtype='int8')
    if method == 'none':
        return None
    if method == 'sigmoid':
        log_odds = np.log(p / (1.0 - p)).reshape(-1, 1)
        return ('sigmoid', LogisticRegression(max_iter=1000, random_state=42).fit(log_odds, y))
    return ('isotonic', IsotonicRegression(out_of_bounds='clip').fit(p, y))


def apply_calibration_map(fitted_calibrator, probabilities):
    """Aplica o calibrador ajustado às probabilidades."""
    p = np.clip(np.asarray(probabilities, float), 1e-6, 1.0 - 1e-6)
    if fitted_calibrator is None:
        return p
    kind, model = fitted_calibrator
    if kind == 'sigmoid':
        return model.predict_proba(np.log(p / (1.0 - p)).reshape(-1, 1))[:, 1]
    return np.asarray(model.predict(p), float)


def find_min_cost_threshold(y_true, probabilities, cost_ratio):
    """Encontra o limiar em THRESHOLDS que minimiza (FP + cost_ratio * FN) / N."""
    y = np.asarray(y_true, dtype='int8')
    p = np.asarray(probabilities, float)
    order = np.argsort(p)
    ps, ys = p[order], y[order]

    cum_pos = np.cumsum(ys[::-1])[::-1]
    cum_neg = np.cumsum((1 - ys)[::-1])[::-1]
    indices = np.searchsorted(ps, THRESHOLDS, side='left')
    n = len(y)

    tp = np.where(indices < n, cum_pos[np.minimum(indices, n - 1)], 0)
    fp = np.where(indices < n, cum_neg[np.minimum(indices, n - 1)], 0)
    fn = int(y.sum()) - tp

    costs = (fp + cost_ratio * fn) / n
    chosen = np.flatnonzero(np.isclose(costs, costs.min(), rtol=0, atol=1e-12))[-1]
    return float(THRESHOLDS[chosen]), float(costs[chosen])


def compute_metrics(y_true, probabilities, threshold, cost_ratio):
    """Calcula métricas probabilísticas, de classificação e custo ponderado."""
    y = np.asarray(y_true, dtype='int8')
    p = np.clip(np.asarray(probabilities, float), 1e-7, 1.0 - 1e-7)
    pred = p >= threshold
    fp = int((pred & (y == 0)).sum())
    fn = int((~pred & (y == 1)).sum())
    return {
        'pr_auc': float(average_precision_score(y, p)),
        'roc_auc': float(roc_auc_score(y, p)),
        'brier': float(brier_score_loss(y, p)),
        'log_loss': float(log_loss(y, p)),
        'precision': float(precision_score(y, pred, zero_division=0)),
        'recall': float(recall_score(y, pred, zero_division=0)),
        'f1': float(f1_score(y, pred, zero_division=0)),
        'balanced_accuracy': float(balanced_accuracy_score(y, pred)),
        'mcc': float(matthews_corrcoef(y, pred)),
        'false_positives': fp,
        'false_negatives': fn,
        'weighted_error_cost_per_row': float((fp + cost_ratio * fn) / len(y)),
    }


def compute_error_complementarity(wide_df):
    """Mede desacordo e sobreposição de erros entre os três modelos."""
    avg_df = wide_df.groupby(['time', 'target_time', 'rain_next_hour', 'fold_year'], as_index=False)[list(BASE_MODELS)].mean()
    y = avg_df.rain_next_hour.to_numpy(dtype='int8')
    errors = {name: (avg_df[name].to_numpy() >= 0.5) != y for name in BASE_MODELS}

    pairs = []
    for i, a in enumerate(BASE_MODELS):
        for b in BASE_MODELS[i + 1:]:
            ea, eb = errors[a], errors[b]
            pairs.append({
                'model_a': a, 'model_b': b, 'rows': len(y),
                'error_rate_a': float(ea.mean()), 'error_rate_b': float(eb.mean()),
                'both_wrong_rate': float((ea & eb).mean()),
                'disagreement_rate': float((ea != eb).mean()),
                'a_missed_rain_caught_by_b': int(((y == 1) & ea & ~eb).sum()),
                'b_missed_rain_caught_by_a': int(((y == 1) & eb & ~ea).sum()),
            })
    return pd.DataFrame(pairs)


def run(source, out):
    """Executa a avaliação temporal aninhada v7 sobre previsões OOF da v6."""
    source_path, output_dir = Path(source).resolve(), Path(out).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if not source_path.is_relative_to(ROOT):
        raise ValueError('A entrada deve estar dentro da pasta do projeto')
    if not output_dir.is_relative_to(experiments_root) or output_dir.exists():
        raise ValueError('Saída deve ser nova em data/experiments')

    raw = pd.read_csv(source_path)
    required = {'time', 'target_time', 'rain_next_hour', 'fold_year', 'seed', 'strategy', 'probability'}
    if not required.issubset(raw.columns):
        raise ValueError(f'Colunas ausentes: {sorted(required - set(raw.columns))}')

    keys = ['time', 'target_time', 'rain_next_hour', 'fold_year', 'seed']
    wide = raw[raw.strategy.isin(BASE_MODELS)].pivot(index=keys, columns='strategy', values='probability').reset_index()
    if any(name not in wide for name in BASE_MODELS):
        raise ValueError('Previsões das três famílias v6 não encontradas')

    simplex_weights = generate_weight_grid()
    outer_results, selected_configs, pred_frames = [], [], []

    for year in EVALUATION_YEARS:
        inner_df, outer_df = wide[wide.fold_year < year], wide[wide.fold_year == year]
        if inner_df.empty or outer_df.empty or inner_df.rain_next_hour.nunique() < 2:
            raise ValueError(f'Dados insuficientes no fold {year}')

        y_in = inner_df.rain_next_hour.to_numpy(dtype='int8')
        y_out = outer_df.rain_next_hour.to_numpy(dtype='int8')

        prob_in, prob_out = {}, {}
        for method in CALIBRATORS:
            prob_in[method], prob_out[method] = {}, {}
            for name in BASE_MODELS:
                mapper = fit_calibration_map(method, inner_df[name].to_numpy(), y_in)
                prob_in[method][name] = apply_calibration_map(mapper, inner_df[name].to_numpy())
                prob_out[method][name] = apply_calibration_map(mapper, outer_df[name].to_numpy())

        policies = {**FIXED_POLICIES, 'ensemble_tuned': None}
        for ratio in COST_RATIOS:
            for label, fixed_w in policies.items():
                trials = []
                for method in CALIBRATORS:
                    for w in (simplex_weights if label == 'ensemble_tuned' else [fixed_w]):
                        p_in = sum(w[i] * prob_in[method][n] for i, n in enumerate(BASE_MODELS))
                        th, cost = find_min_cost_threshold(y_in, p_in, ratio)
                        trials.append((cost, -th, CALIBRATORS.index(method), tuple(w), method, th))

                best_cost, _, _, w, method, threshold = min(trials, key=lambda z: (z[0], z[1], z[2], z[3]))
                p_out = sum(w[i] * prob_out[method][n] for i, n in enumerate(BASE_MODELS))
                seed_values = outer_df.seed.to_numpy()

                for seed in np.unique(seed_values):
                    mask = seed_values == seed
                    outer_results.append({
                        'outer_year': year, 'seed': int(seed), 'fn_to_fp_cost_ratio': ratio,
                        'pipeline': label, 'calibration': method,
                        'weight_original': w[0], 'weight_balanced': w[1], 'weight_balanced_subsample': w[2],
                        'threshold_selected_on_prior_years': threshold,
                        'inner_cost_per_row': best_cost, 'outer_rows': int(mask.sum()),
                        **compute_metrics(y_out[mask], p_out[mask], threshold, ratio),
                    })

                selected_configs.append({
                    'outer_year': year, 'fn_to_fp_cost_ratio': ratio, 'pipeline': label, 'calibration': method,
                    'weight_original': w[0], 'weight_balanced': w[1], 'weight_balanced_subsample': w[2],
                    'threshold_selected_on_prior_years': threshold, 'inner_cost_per_row': best_cost,
                })
                pred_frames.append(pd.DataFrame({
                    'time': outer_df.time.to_numpy(), 'target_time': outer_df.target_time.to_numpy(),
                    'rain_next_hour': y_out, 'fold_year': year, 'seed': seed_values,
                    'cost_ratio': ratio, 'pipeline': label, 'calibration': method,
                    'threshold': threshold, 'probability': p_out,
                }))

        print(f'fold externo {year} concluído com sucesso', flush=True)

    output_dir.mkdir(parents=True)
    outer_df_res = pd.DataFrame(outer_results)
    outer_df_res.to_csv(output_dir / 'outer_fold_metrics.csv', index=False)
    pd.DataFrame(selected_configs).to_csv(output_dir / 'selected_configuration_by_fold.csv', index=False)
    pd.concat(pred_frames, ignore_index=True).to_csv(output_dir / 'nested_predictions.csv', index=False)
    compute_error_complementarity(wide).to_csv(output_dir / 'error_complementarity.csv', index=False)

    summary_cols = [
        'weighted_error_cost_per_row', 'pr_auc', 'brier', 'precision',
        'recall', 'f1', 'false_positives', 'false_negatives', 'threshold_selected_on_prior_years',
    ]
    summary_df = outer_df_res.groupby(['fn_to_fp_cost_ratio', 'pipeline'])[summary_cols].mean().reset_index()
    summary_df.to_csv(output_dir / 'nested_summary.csv', index=False)

    source_rel = source_path.relative_to(ROOT).as_posix()
    manifest = {
        'experiment': 'v7_nested_temporal_calibration_weight_threshold_evaluation',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'pandas': pd.__version__, 'numpy': np.__version__, 'scikit_learn': sklearn.__version__,
        'input_path': source_rel, 'input_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
        'outer_years': list(EVALUATION_YEARS), 'calibrators': list(CALIBRATORS),
        'cost_ratios_fn_to_fp': list(COST_RATIOS), 'test_2026_used': False, 'final_joblibs_written': False,
        'outputs': ['outer_fold_metrics.csv', 'selected_configuration_by_fold.csv', 'nested_predictions.csv', 'nested_summary.csv', 'error_complementarity.csv'],
    }
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    rows_md = '\n'.join(
        f"| {r.fn_to_fp_cost_ratio:g}:1 | {r.pipeline} | {r.weighted_error_cost_per_row:.5f} | "
        f"{r.pr_auc:.5f} | {r.brier:.5f} | {r.precision:.4f} | {r.recall:.4f} | {r.f1:.4f} | "
        f"{r.threshold_selected_on_prior_years:.3f} |"
        for _, r in summary_df.sort_values(['fn_to_fp_cost_ratio', 'weighted_error_cost_per_row']).iterrows()
    )
    report_file = ROOT / 'reports' / 'training' / 'seventh_training_report.md'
    report_file.write_text(f"""# Avaliação aninhada v7 — calibração, combinação e limiar

**Data:** {datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")}  
**Experimento:** `{output_dir.name}`  
**Entrada:** `{source_rel}`

## Resultados por cenário

| Custo FN:FP | Política | Custo externo/linha | PR-AUC | Brier | Precisão | Sensibilidade | F1 | Limiar médio |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
{rows_md}
""", encoding='utf-8')

    (output_dir / 'experiment_summary.json').write_text(
        json.dumps({
            'outer_years': list(EVALUATION_YEARS), 'cost_ratios': list(COST_RATIOS),
            'pipelines': sorted(outer_df_res.pipeline.unique()), 'outer_metric_rows': len(outer_df_res),
            'report': 'reports/training/seventh_training_report.md', 'test_2026_used': False,
        }, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(json.dumps({'output_dir': str(output_dir), 'report': 'reports/training/seventh_training_report.md', 'outer_metric_rows': len(outer_df_res)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'data' / 'experiments' / 'weather_v6_20261105T120000Z' / 'predictions_oof.csv')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data' / 'experiments' / f"weather_v7_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    args = parser.parse_args()
    run(args.input, args.output_dir)
