"""Treinamento v6: validação temporal rolling-year e combinação de três Random Forests."""

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
    average_precision_score, balanced_accuracy_score, brier_score_loss,
    f1_score, log_loss, matthews_corrcoef, precision_score, recall_score, roc_auc_score,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, WEATHER_FEATURES, WEATHER_TIMEZONE, settings

TARGET = 'rain_next_hour'
CV_YEARS = (2022, 2023, 2024, 2025)
SEEDS = (17, 42, 2025)
FEATURES = [
    'temperature_2m', 'relative_humidity_2m', 'pressure_msl', 'cloud_cover',
    'temp_humidity', 'pressure_diff', 'hour_of_day',
]

MODELS = {
    'original': {'class_weight': None},
    'balanced': {'class_weight': 'balanced'},
    'balanced_subsample': {'class_weight': 'balanced_subsample'},
}
WEIGHTS = {
    'equal': {'original': 1 / 3, 'balanced': 1 / 3, 'balanced_subsample': 1 / 3},
    'original_favor': {'original': 0.5, 'balanced': 0.25, 'balanced_subsample': 0.25},
    'balanced_favor': {'original': 0.2, 'balanced': 0.6, 'balanced_subsample': 0.2},
    'subsample_favor': {'original': 0.2, 'balanced': 0.2, 'balanced_subsample': 0.6},
}
PARAMS = {
    'n_estimators': 400, 'max_depth': None, 'max_features': 'sqrt',
    'min_samples_split': 2, 'min_samples_leaf': 10, 'bootstrap': True, 'n_jobs': -1,
}
DEV_END = pd.Timestamp('2026-01-01T00:00:00-03:00').tz_convert('UTC')
METRIC_COLS = [
    'pr_auc', 'roc_auc', 'brier', 'log_loss', 'precision_at_0_5', 'recall_at_0_5',
    'f1_at_0_5', 'balanced_accuracy_at_0_5', 'mcc_at_0_5',
    'false_positives_at_0_5', 'false_negatives_at_0_5',
]


def load_table(path):
    """Carrega o CSV preparado, ordena no tempo e calcula as 3 features derivadas."""
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Tabela de treinamento não encontrada: {path}')

    frame = pd.read_csv(path)
    required = ['time', *WEATHER_FEATURES, 'target_time', TARGET]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f'Colunas ausentes na tabela: {sorted(missing)}')
    if frame.empty:
        raise ValueError('A tabela de treinamento está vazia')

    for col in ('time', 'target_time'):
        frame[col] = pd.to_datetime(frame[col], errors='raise', utc=True)
        if frame[col].isna().any():
            raise ValueError(f'Timestamp ausente em {col}')
    if frame['time'].duplicated().any():
        raise ValueError('Existem timestamps duplicados')

    target = pd.to_numeric(frame[TARGET], errors='raise')
    if target.isna().any() or not target.isin([0, 1]).all():
        raise ValueError(f'{TARGET} deve conter apenas 0 e 1')
    frame[TARGET] = target.astype('int8')

    for col in WEATHER_FEATURES:
        frame[col] = pd.to_numeric(frame[col], errors='raise')

    frame = frame.sort_values('time').reset_index(drop=True)
    frame['temp_humidity'] = frame['temperature_2m'] * frame['relative_humidity_2m']
    frame['pressure_diff'] = frame['pressure_msl'].diff().fillna(0.0)
    frame['hour_of_day'] = frame['time'].dt.tz_convert(WEATHER_TIMEZONE).dt.hour
    return frame


def temporal_fold(frame, year):
    """Separa treino (antes do ano) e validação (durante o ano) sem vazamento temporal."""
    start = pd.Timestamp(f'{year}-01-01', tz=WEATHER_TIMEZONE).tz_convert('UTC')
    end = pd.Timestamp(f'{year + 1}-01-01', tz=WEATHER_TIMEZONE).tz_convert('UTC')
    train = frame[frame['target_time'] < start]
    valid = frame[(frame['time'] >= start) & (frame['target_time'] < end)]
    if train.empty or valid.empty or train[TARGET].nunique() < 2 or valid[TARGET].nunique() < 2:
        raise ValueError(f'Dados insuficientes para o fold de {year}')
    return train, valid


def metrics(y_true, probabilities):
    """Calcula métricas probabilísticas e de classificação no limiar 0,50."""
    y = np.asarray(y_true, dtype='int8')
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-7, 1.0 - 1e-7)
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
        'false_positives_at_0_5': int((pred & (y == 0)).sum()),
        'false_negatives_at_0_5': int((~pred & (y == 1)).sum()),
    }


def _oof_frame(valid_df, y_valid, year, seed, strategy, prob):
    return pd.DataFrame({
        'time': valid_df.time.to_numpy(), 'target_time': valid_df.target_time.to_numpy(),
        TARGET: y_valid, 'fold_year': year, 'seed': seed,
        'strategy': strategy, 'probability': prob,
    })


def run_cross_validation(dev):
    """Executa validação cruzada rolling-year (2022–2025) com 3 sementes."""
    feature_cols = list(FEATURES)
    metric_rows, pred_frames = [], []

    for year in CV_YEARS:
        train_df, valid_df = temporal_fold(dev, year)
        y_valid = valid_df[TARGET].to_numpy()
        probs_by_model = {name: [] for name in MODELS}

        for name, cw in MODELS.items():
            for seed in SEEDS:
                model = RandomForestClassifier(**PARAMS, **cw, random_state=seed)
                model.fit(train_df[feature_cols], train_df[TARGET])
                prob = model.predict_proba(valid_df[feature_cols])[:, list(model.classes_).index(1)]
                probs_by_model[name].append(prob)
                metric_rows.append({'strategy': name, 'fold_year': year, 'seed': seed, **metrics(y_valid, prob)})

        for seed_idx, seed in enumerate(SEEDS):
            inputs = {name: probs_by_model[name][seed_idx] for name in MODELS}
            for name, prob in inputs.items():
                pred_frames.append(_oof_frame(valid_df, y_valid, year, seed, name, prob))

            for label, weights in WEIGHTS.items():
                ens_prob = sum(weights[name] * inputs[name] for name in MODELS)
                strategy = f'ensemble_{label}'
                metric_rows.append({'strategy': strategy, 'fold_year': year, 'seed': seed, **metrics(y_valid, ens_prob)})
                pred_frames.append(_oof_frame(valid_df, y_valid, year, seed, strategy, ens_prob))

        print(f'fold={year} concluído para todas as sementes', flush=True)
    return metric_rows, pred_frames


def train_final_models(dev, output_dir):
    """Treina os 3 modelos finais até 2025 e salva os .joblib com hashes SHA-256."""
    feature_cols = list(FEATURES)
    hashes, params = {}, {}

    for name, cw in MODELS.items():
        model = RandomForestClassifier(**PARAMS, **cw, random_state=42)
        model.fit(dev[feature_cols], dev[TARGET])
        filename = f'{name}_leaf10_trees400.joblib'
        path = output_dir / filename
        joblib.dump(model, path, compress=3)
        hashes[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
        params[filename] = model.get_params()

    return hashes, params


def generate_markdown_report(output_dir, source_path, total_rows, dev_rows, ordered_summary):
    """Gera o relatório sixth_training_report.md com a tabela comparativa."""
    rows_total = f'{total_rows:,}'.replace(',', '.')
    rows_dev = f'{dev_rows:,}'.replace(',', '.')
    table_rows = '\n'.join(
        f"| {r['strategy']} | {r['pr_auc_mean']:.5f} | {r['brier_mean']:.5f} | "
        f"{r['recall_at_0_5_mean']:.5f} | {r['f1_at_0_5_mean']:.5f} |"
        for _, r in ordered_summary.iterrows()
    )
    report_path = ROOT / 'reports' / 'training' / 'sixth_training_report.md'
    report_path.write_text(f"""# Relatório do sexto treinamento — v6

**Data:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}  
**Experimento:** `{output_dir.name}`  
**Script:** `scripts/train_v6.py`

## Objetivo

Comparar três Random Forests com a mesma estrutura e combinar suas probabilidades com quatro proporções previamente definidas.

## Dados e procedimento

Fonte: `{source_path.name}` ({rows_total} linhas). Desenvolvimento: {rows_dev} linhas até 31/12/2025, 7 atributos, 4 folds (2022–2025) e 3 sementes ({', '.join(map(str, SEEDS))}). O período de 2026 não foi usado.

## Configurações

400 árvores, folha mínima 10, `max_features=sqrt`, bootstrap habilitado. Variou apenas `class_weight` (`None`, `balanced`, `balanced_subsample`).

## Resultados

| Estratégia | PR-AUC média | Brier médio | Sensibilidade média | F1 médio |
|---|---:|---:|---:|---:|
{table_rows}
""", encoding='utf-8')
    return report_path


def run(source, out):
    """Orquestra validação cruzada, treino final e gravação dos artefatos v6."""
    source_path, output_dir = Path(source).resolve(), Path(out).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()
    if not output_dir.is_relative_to(experiments_root) or output_dir.exists():
        raise ValueError('Saída deve ser nova e estar dentro de data/experiments')

    frame = load_table(source_path)
    dev_data = frame[frame.target_time < DEV_END].copy()
    metric_rows, pred_frames = run_cross_validation(dev_data)

    output_dir.mkdir(parents=True)
    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(output_dir / 'metrics_by_fold_seed.csv', index=False)
    pd.concat(pred_frames, ignore_index=True).to_csv(output_dir / 'predictions_oof.csv', index=False)

    summary_df = metrics_df.groupby('strategy')[METRIC_COLS].agg(['mean', 'std'])
    summary_df.columns = [f'{col}_{stat}' for col, stat in summary_df.columns]
    summary_flat = summary_df.reset_index()
    summary_flat.to_csv(output_dir / 'strategy_summary.csv', index=False)

    model_hashes, final_params = train_final_models(dev_data, output_dir)
    manifest = {
        'experiment': 'train_v6_weighted_random_forest_ensemble',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'pandas': pd.__version__, 'numpy': np.__version__,
        'scikit_learn': sklearn.__version__, 'joblib': joblib.__version__,
        'source_path': str(source_path),
        'source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
        'source_rows': len(frame), 'development_rows_before_2026': len(dev_data),
        'features': list(FEATURES), 'target': TARGET,
        'cv_years': list(CV_YEARS), 'seeds': list(SEEDS),
        'member_parameters': {n: {**PARAMS, **cw} for n, cw in MODELS.items()},
        'ensemble_weights': WEIGHTS, 'test_2026_used': False,
        'final_models_trained_on_development_only': final_params,
        'model_sha256': model_hashes,
        'outputs': ['metrics_by_fold_seed.csv', 'strategy_summary.csv', 'predictions_oof.csv'],
    }
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    (output_dir / 'experiment_summary.json').write_text(summary_flat.to_json(orient='records', force_ascii=False, indent=2), encoding='utf-8')

    ordered = summary_flat.sort_values(['pr_auc_mean', 'brier_mean'], ascending=[False, True])
    report_path = generate_markdown_report(output_dir, source_path, len(frame), len(dev_data), ordered)
    print(json.dumps({'output': str(output_dir), 'report': str(report_path), 'top': ordered.iloc[0].to_dict()}, ensure_ascii=False, default=str), flush=True)


if __name__ == '__main__':
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=cfg['training'])
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data' / 'experiments' / f"weather_v6_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    args = parser.parse_args()
    run(args.input, args.output_dir)
