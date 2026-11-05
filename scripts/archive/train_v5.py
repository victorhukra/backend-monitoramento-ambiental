# Script original arquivado - preservado para referência

"""Comparação rigorosa de Random Forests sob validação temporal repetida.

O período de 2026 fica fora da seleção e do ajuste final. A saída registra
previsões out-of-fold, métricas por ano/semente, modelos finais e hashes.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import ROOT, WEATHER_FEATURES, WEATHER_TIMEZONE, settings
from scripts.archive.train_v4 import TARGET, VALIDATION_END, load_table, split_data

CV_YEARS = (2022, 2023, 2024, 2025)
SEEDS = (17, 42, 2025)
FEATURES = list(WEATHER_FEATURES) + [
    'temp_humidity', 'pressure_diff', 'hour_of_day'
]
DEV_END = pd.Timestamp('2026-01-01T00:00:00-03:00').tz_convert('UTC')


def candidates():
    """Grade enxuta de pesos, folhas e quantidade de árvores."""
    configurations = {}
    weights = {
        'original': None,
        'balanced': 'balanced',
        'balanced_subsample': 'balanced_subsample',
        'positive_x2': {0: 1.0, 1: 2.0},
    }
    for weight_name, class_weight in weights.items():
        for leaf in (5, 10):
            name = f'{weight_name}_leaf{leaf}_trees400'
            configurations[name] = {
                'class_weight': class_weight,
                'min_samples_leaf': leaf,
                'n_estimators': 400,
            }
    for weight_name, class_weight in (
        ('original', None), ('balanced_subsample', 'balanced_subsample')
    ):
        for trees in (250, 800):
            name = f'{weight_name}_leaf5_trees{trees}'
            configurations[name] = {
                'class_weight': class_weight,
                'min_samples_leaf': 5,
                'n_estimators': trees,
            }
    return configurations


def temporal_fold(frame, year):
    start = pd.Timestamp(f'{year}-01-01', tz=WEATHER_TIMEZONE).tz_convert('UTC')
    end = pd.Timestamp(f'{year + 1}-01-01', tz=WEATHER_TIMEZONE).tz_convert('UTC')
    # Usa o horário-alvo nos limites para não atravessar uma fronteira temporal.
    train = frame[frame['target_time'] < start]
    valid = frame[(frame['time'] >= start) & (frame['target_time'] < end)]
    if train.empty or valid.empty or train[TARGET].nunique() < 2 or valid[TARGET].nunique() < 2:
        raise ValueError(f'Dados insuficientes para o fold de {year}')
    return train, valid


def score_probabilities(y, probability):
    y = np.asarray(y, dtype='int8')
    p = np.clip(np.asarray(probability, dtype=float), 1e-7, 1 - 1e-7)
    pred = p >= 0.5
    return {
        'pr_auc': float(average_precision_score(y, p)),
        'roc_auc': float(roc_auc_score(y, p)),
        'brier': float(brier_score_loss(y, p)),
        'log_loss': float(log_loss(y, p)),
        'precision_at_0_5': float(precision_score(y, pred, zero_division=0)),
        'recall_at_0_5': float(recall_score(y, pred, zero_division=0)),
        'f1_at_0_5': float(f1_score(y, pred, zero_division=0)),
        'balanced_accuracy_at_0_5': float(balanced_accuracy_score(y, pred)),
        'mcc_at_0_5': float(matthews_corrcoef(y, pred)),
        'rain_rate': float(np.mean(y)),
        'predicted_rain_rate_at_0_5': float(np.mean(pred)),
        'false_positives_at_0_5': int(np.sum(pred & (y == 0))),
        'false_negatives_at_0_5': int(np.sum(~pred & (y == 1))),
    }


def evaluate_models_on_test(models, test_frame):
    """Avalia modelos congelados no teste sem escolher candidato ou limiar."""
    X_test = test_frame[FEATURES]
    y_test = test_frame[TARGET].to_numpy()
    predictions = test_frame[['time', 'target_time', TARGET]].copy()
    results = {}
    for candidate, model in models.items():
        probability = model.predict_proba(X_test)[:, list(model.classes_).index(1)]
        classification = score_probabilities(y_test, probability)
        predicted = probability >= 0.5
        results[candidate] = {
            **classification,
            'accuracy_at_0_5': float(accuracy_score(y_test, predicted)),
            'test_rows': int(len(test_frame)),
            'selected_threshold': 0.5,
        }
        predictions[f'{candidate}_probability_rain'] = probability
        predictions[f'{candidate}_prediction_at_0_5'] = predicted.astype('int8')
    return results, predictions


def evaluate_saved_models_test(input_path, output_dir):
    """Avalia uma vez os joblibs congelados no período de teste de 2026."""
    input_path, output_dir = Path(input_path).resolve(), Path(output_dir).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()
    if not output_dir.is_relative_to(experiments_root):
        raise ValueError('A pasta do experimento deve ficar dentro de data/experiments')
    manifest_path = output_dir / 'manifest.json'
    if not manifest_path.is_file():
        raise FileNotFoundError(f'Manifesto v5 não encontrado: {manifest_path}')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('test_evaluated_at_utc') or (output_dir / 'metrics_test.json').exists():
        raise ValueError('O teste deste experimento já foi avaliado; não reutilize o período')
    input_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    if input_hash != manifest['source_sha256']:
        raise ValueError('A fonte não corresponde ao hash usado no experimento v5')
    frame = load_table(input_path)
    _, _, test, _ = split_data(frame)
    if test.empty:
        raise ValueError('O conjunto de teste ficou vazio')
    models = {}
    for filename, expected_hash in manifest['model_sha256'].items():
        model_path = output_dir / filename
        if hashlib.sha256(model_path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f'Hash do modelo não confere: {filename}')
        model = joblib.load(model_path)
        if model.n_features_in_ != len(manifest['features']):
            raise ValueError(f'Dimensão de entrada incorreta: {filename}')
        models[Path(filename).stem] = model
    metrics, predictions = evaluate_models_on_test(models, test)
    metrics_path = output_dir / 'metrics_test.json'
    predictions_path = output_dir / 'predictions_test.csv'
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    predictions.to_csv(predictions_path, index=False)
    now = datetime.now(timezone.utc).isoformat()
    manifest.update({
        'test_2026_used': True,
        'test_evaluated': True,
        'test_evaluated_at_utc': now,
        'test_rows': int(len(test)),
        'test_start': VALIDATION_END.isoformat(),
        'test_source_sha256': input_hash,
        'test_metrics_file': metrics_path.name,
        'test_predictions_file': predictions_path.name,
        'test_used_for_selection': False,
        'independent_blind_test': False,
        'test_interpretation': 'Retrospective: the 2026 period was accessed in earlier experiments; results are descriptive and were not used to select candidates or thresholds.',
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    summary_path = output_dir / 'experiment_summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    summary['test_2026_evaluated'] = True
    summary['test_metrics_file'] = metrics_path.name
    summary['test_used_for_selection'] = False
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'output_dir': str(output_dir), 'test_rows': int(len(test)),
        'metrics_file': str(metrics_path), 'predictions_file': str(predictions_path),
        'metrics': metrics,
    }, ensure_ascii=False, indent=2), flush=True)


def bootstrap_monthly_delta(predictions, left, right, replicates=2000, seed=91):
    """IC pareado descritivo; probabilidade média de três sementes por linha."""
    frame = predictions.groupby(
        ['time', 'fold_year', TARGET, 'candidate'], as_index=False
    )['probability'].mean()
    wide = frame.pivot(index=['time', 'fold_year', TARGET], columns='candidate', values='probability')
    wide = wide.reset_index()
    wide['month_block'] = pd.to_datetime(wide['time'], utc=True).dt.strftime('%Y-%m')
    blocks = [part for _, part in wide.groupby('month_block', sort=True)]
    rng = np.random.default_rng(seed)
    deltas = {'pr_auc': [], 'brier': [], 'recall_at_0_5': []}
    for _ in range(replicates):
        sampled = [blocks[i] for i in rng.integers(0, len(blocks), size=len(blocks))]
        sample = pd.concat(sampled, ignore_index=True)
        y = sample[TARGET].to_numpy()
        p_left = sample[left].to_numpy()
        p_right = sample[right].to_numpy()
        deltas['pr_auc'].append(average_precision_score(y, p_right) - average_precision_score(y, p_left))
        deltas['brier'].append(brier_score_loss(y, p_right) - brier_score_loss(y, p_left))
        deltas['recall_at_0_5'].append(
            recall_score(y, p_right >= 0.5, zero_division=0)
            - recall_score(y, p_left >= 0.5, zero_division=0)
        )
    return {
        metric: {
            'delta_right_minus_left_mean': float(np.mean(values)),
            'ci95_percentile': [float(np.quantile(values, .025)), float(np.quantile(values, .975))],
            'replicates': replicates,
            'unit': 'bloco de mês calendário, probabilidades médias de três sementes',
        }
        for metric, values in deltas.items()
    }


def finalize_existing_experiment(input_path, output_dir):
    """Reconstroi joblibs e manifesto a partir dos CSVs da CV concluída."""
    input_path, output_dir = Path(input_path).resolve(), Path(output_dir).resolve()
    summary = pd.read_csv(output_dir / 'candidate_summary.csv')
    ranked = summary.sort_values(
        ['pr_auc_mean', 'brier_mean', 'pr_auc_std'], ascending=[False, True, True]
    )
    near_ties = ranked[ranked['pr_auc_mean'] >= float(ranked.iloc[0]['pr_auc_mean']) - 0.002]
    near_ties = near_ties.sort_values(['brier_mean', 'pr_auc_std'], ascending=[True, True])
    selected = str(near_ties.iloc[0]['candidate'])
    grid = candidates()
    family_best = {}
    for family in ('original', 'balanced_subsample', 'balanced', 'positive_x2'):
        prefix = 'balanced_leaf' if family == 'balanced' else family + '_'
        family_best[family] = str(
            ranked[ranked['candidate'].str.startswith(prefix)].iloc[0]['candidate']
        )
    save_names = list(dict.fromkeys([*family_best.values(), selected]))
    development = load_table(input_path)
    development = development[development['target_time'] < DEV_END]
    hashes, final_params = {}, {}
    for candidate in save_names:
        model = RandomForestClassifier(
            **grid[candidate], max_depth=None, max_features='sqrt',
            min_samples_split=2, bootstrap=True, n_jobs=-1, random_state=42,
        )
        model.fit(development[FEATURES], development[TARGET])
        filename = f'{candidate}.joblib'
        joblib.dump(model, output_dir / filename, compress=3)
        hashes[filename] = hashlib.sha256((output_dir / filename).read_bytes()).hexdigest()
        final_params[filename] = model.get_params()
    manifest_path = output_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update({
        'selected_candidate': selected,
        'best_candidate_by_weight_family': family_best,
        'final_models_trained_on_development_only': final_params,
        'model_sha256': hashes,
        'artifact_finalization': 'models reloaded from candidate summary and family prefixes audited',
    })
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8'
    )
    summary_path = output_dir / 'experiment_summary.json'
    experiment_summary = json.loads(summary_path.read_text(encoding='utf-8'))
    experiment_summary['selected_candidate'] = selected
    experiment_summary['best_candidate_by_weight_family'] = family_best
    summary_path.write_text(
        json.dumps(experiment_summary, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps({
        'output_dir': str(output_dir), 'selected_candidate': selected,
        'best_by_family': family_best, 'model_files': list(hashes),
    }, ensure_ascii=False, indent=2), flush=True)


def run(input_path, output_dir):
    input_path, output_dir = Path(input_path).resolve(), Path(output_dir).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()
    if not output_dir.is_relative_to(experiments_root):
        raise ValueError('A saída deve ficar dentro de data/experiments')
    if output_dir.exists():
        raise ValueError('A pasta de saída já existe; escolha outra')
    frame = load_table(input_path)
    development = frame[frame['target_time'] < DEV_END].copy()
    grid = candidates()
    metric_rows, prediction_parts = [], []

    for year in CV_YEARS:
        train, valid = temporal_fold(development, year)
        X_train, y_train = train[FEATURES], train[TARGET]
        X_valid, y_valid = valid[FEATURES], valid[TARGET]
        for candidate, params in grid.items():
            for seed in SEEDS:
                model = RandomForestClassifier(
                    **params, max_depth=None, max_features='sqrt',
                    min_samples_split=2, bootstrap=True, n_jobs=-1,
                    random_state=seed,
                )
                model.fit(X_train, y_train)
                probability = model.predict_proba(X_valid)[:, list(model.classes_).index(1)]
                metric_rows.append({
                    'candidate': candidate, 'fold_year': year, 'seed': seed,
                    'train_rows': len(train), 'validation_rows': len(valid),
                    **score_probabilities(y_valid, probability),
                })
                prediction_parts.append(pd.DataFrame({
                    'time': valid['time'].to_numpy(),
                    'target_time': valid['target_time'].to_numpy(),
                    TARGET: y_valid.to_numpy(),
                    'fold_year': year, 'candidate': candidate, 'seed': seed,
                    'probability': probability,
                }))
                print(f'fold={year} candidate={candidate} seed={seed} concluído', flush=True)

    metrics = pd.DataFrame(metric_rows)
    predictions = pd.concat(prediction_parts, ignore_index=True)
    metric_columns = [
        'pr_auc', 'roc_auc', 'brier', 'log_loss', 'precision_at_0_5',
        'recall_at_0_5', 'f1_at_0_5', 'balanced_accuracy_at_0_5', 'mcc_at_0_5',
        'predicted_rain_rate_at_0_5', 'false_positives_at_0_5', 'false_negatives_at_0_5',
    ]
    summary = metrics.groupby('candidate')[metric_columns].agg(['mean', 'std']).round(8)
    summary.columns = [f'{metric}_{stat}' for metric, stat in summary.columns]
    summary = summary.reset_index()
    # Regra pré-declarada: maior PR-AUC média; entre candidatos a até 0,002,
    # menor Brier, depois menor variabilidade de PR-AUC.
    ranked = summary.sort_values(['pr_auc_mean', 'brier_mean', 'pr_auc_std'], ascending=[False, True, True])
    top_pr = float(ranked.iloc[0]['pr_auc_mean'])
    near_ties = ranked[ranked['pr_auc_mean'] >= top_pr - 0.002].sort_values(
        ['brier_mean', 'pr_auc_std'], ascending=[True, True]
    )
    selected_candidate = str(near_ties.iloc[0]['candidate'])

    # Comparação pareada pré-especificada da configuração convencional:
    # mesmas folhas/árvores/sementes, variando somente o peso de classe.
    canonical_original = 'original_leaf5_trees400'
    canonical_balanced = 'balanced_subsample_leaf5_trees400'
    canonical_ci = bootstrap_monthly_delta(
        predictions, canonical_original, canonical_balanced
    )

    output_dir.mkdir(parents=True)
    metrics.to_csv(output_dir / 'metrics_by_fold_seed.csv', index=False)
    summary.to_csv(output_dir / 'candidate_summary.csv', index=False)
    predictions.to_csv(output_dir / 'predictions_oof.csv', index=False)
    (output_dir / 'paired_monthly_bootstrap.json').write_text(
        json.dumps(canonical_ci, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # Salva os melhores hiperparâmetros dentro de cada família de peso, mais
    # o campeão geral; todos são ajustados somente até 31/12/2025.
    family_best = {}
    for family in ('original', 'balanced_subsample', 'balanced', 'positive_x2'):
        if family == 'balanced':
            family_mask = ranked['candidate'].str.startswith('balanced_leaf')
        else:
            family_mask = ranked['candidate'].str.startswith(family + '_')
        family_candidates = ranked[family_mask]
        family_best[family] = str(family_candidates.iloc[0]['candidate'])
    save_names = list(dict.fromkeys([*family_best.values(), selected_candidate]))
    model_hashes, final_params = {}, {}
    for candidate in save_names:
        params = grid[candidate]
        model = RandomForestClassifier(
            **params, max_depth=None, max_features='sqrt',
            min_samples_split=2, bootstrap=True, n_jobs=-1, random_state=42,
        )
        model.fit(development[FEATURES], development[TARGET])
        filename = f'{candidate}.joblib'
        joblib.dump(model, output_dir / filename, compress=3)
        model_hashes[filename] = hashlib.sha256((output_dir / filename).read_bytes()).hexdigest()
        final_params[filename] = model.get_params()

    manifest = {
        'experiment': 'train_v5_temporal_repeated_random_forest_comparison',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'pandas': pd.__version__, 'numpy': np.__version__,
        'scikit_learn': sklearn.__version__, 'joblib': joblib.__version__,
        'source_path': str(input_path),
        'source_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'source_rows': int(len(frame)),
        'development_rows_before_2026': int(len(development)),
        'features': FEATURES, 'target': TARGET,
        'cv_years': CV_YEARS, 'seeds': SEEDS,
        'split_method': 'expanding chronological folds; target_time cannot cross year boundary',
        'test_2026_used': False,
        'test_evaluated': False,
        'test_used_for_selection': False,
        'candidate_parameters': grid,
        'selection_rule': {
            'primary': 'highest mean PR-AUC across 4 years x 3 seeds',
            'near_tie_tolerance': 0.002,
            'near_tie_tiebreaks': ['lower mean Brier', 'lower PR-AUC standard deviation'],
            'decision_use': 'technical development winner only; operational error costs not specified',
        },
        'selected_candidate': selected_candidate,
        'best_candidate_by_weight_family': family_best,
        'paired_bootstrap': {
            'comparison': [canonical_original, canonical_balanced],
            'results_file': 'paired_monthly_bootstrap.json',
            'interpretation': 'exploratory paired uncertainty interval; not a prospective test',
        },
        'final_models_trained_on_development_only': final_params,
        'model_sha256': model_hashes,
        'prediction_file': 'predictions_oof.csv',
        'metrics_file': 'metrics_by_fold_seed.csv',
        'summary_file': 'candidate_summary.csv',
    }
    (output_dir / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8'
    )
    (output_dir / 'experiment_summary.json').write_text(
        json.dumps({
            'selected_candidate': selected_candidate,
            'best_candidate_by_weight_family': family_best,
            'canonical_original_vs_balanced_monthly_bootstrap': canonical_ci,
            'test_2026_used': False,
            'test_evaluated': False,
        }, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps({
        'output_dir': str(output_dir), 'selected_candidate': selected_candidate,
        'best_by_family': family_best, 'candidate_summary': str(output_dir / 'candidate_summary.csv'),
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=cfg['training'])
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data' / 'experiments' /
                        ('weather_v5_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--finalize-existing', action='store_true',
                         help='Refazer modelos e manifesto de uma execução cuja CV já terminou.')
    actions.add_argument('--evaluate-test', action='store_true',
                         help='Avaliar uma única vez os joblibs congelados no teste de 2026; não usar para seleção.')
    args = parser.parse_args()
    if args.finalize_existing:
        finalize_existing_experiment(args.input, args.output_dir)
    elif args.evaluate_test:
        evaluate_saved_models_test(args.input, args.output_dir)
    else:
        run(args.input, args.output_dir)
