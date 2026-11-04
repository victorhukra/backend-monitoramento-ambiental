"""Treinamento experimental versão 4 – inclui engenharia de atributos e modelos mais robustos.

Este script estende `train_v3.py` adicionando recursos derivados (ex.: temperatura × umidade, diferença de pressão, hora do dia) e aumenta o número de árvores nos Random Forests para 1000.
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
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Permite executar o script diretamente a partir da pasta scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, WEATHER_FEATURES, settings, WEATHER_TIMEZONE

# ---------------------------------------------------------------------------
# Configurações gerais
# ---------------------------------------------------------------------------
TARGET = 'rain_next_hour'
TRAIN_END = pd.Timestamp('2025-01-01T00:00:00-03:00')
VALIDATION_END = pd.Timestamp('2026-01-01T00:00:00-03:00')
CV_VALIDATION_YEARS = [2023, 2024, 2025]

# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def load_table(path):
    """Carrega a tabela CSV e adiciona variáveis derivadas.

    Variáveis adicionadas:
    - `temp_humidity` = temperature_2m * relative_humidity_2m
    - `pressure_diff` = diferença da pressão em relação ao horário anterior
    - `hour_of_day` = hora (0‑23) extraída do timestamp (fuso local)
    """
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
    for column in ['time', 'target_time']:
        frame[column] = pd.to_datetime(frame[column], errors='raise', utc=True)
        if frame[column].isna().any():
            raise ValueError(f'Timestamp ausente em {column}')
    if frame['time'].duplicated().any():
        raise ValueError('Existem timestamps duplicados')
    target = pd.to_numeric(frame[TARGET], errors='raise')
    if target.isna().any() or not target.isin([0, 1]).all():
        raise ValueError(f'{TARGET} deve conter apenas 0 e 1')
    frame[TARGET] = target.astype('int8')
    for column in WEATHER_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors='raise')
    # Derivações temporais dependem da ordem cronológica, não da ordem do CSV.
    frame = frame.sort_values('time').reset_index(drop=True)
    # --- Engenharia de atributos ---
    # Produto temperatura × umidade (proxy para índice de desconforto)
    frame['temp_humidity'] = frame['temperature_2m'] * frame['relative_humidity_2m']
    # Diferença de pressão em relação ao ponto anterior (hpa)
    frame['pressure_diff'] = frame['pressure_msl'].diff().fillna(0)
    # Hora do dia (local)
    frame['hour_of_day'] = frame['time'].dt.tz_convert(WEATHER_TIMEZONE).dt.hour
    # Garantir que não haja NaNs nas novas colunas
    if not np.isfinite(frame[['temp_humidity', 'pressure_diff', 'hour_of_day']].to_numpy()).all():
        raise ValueError('Valores não finitos nas variáveis derivadas')
    return frame

def split_data(frame):
    """Separa treino, validação e teste respeitando a ordem temporal."""
    train_end = TRAIN_END.tz_convert('UTC')
    validation_end = VALIDATION_END.tz_convert('UTC')
    time = frame['time']
    target_time = frame['target_time']
    train_mask = (time < train_end) & (target_time < train_end)
    validation_mask = (time >= train_end) & (time < validation_end) & (target_time < validation_end)
    test_mask = time >= validation_end
    train = frame.loc[train_mask].copy()
    validation = frame.loc[validation_mask].copy()
    test = frame.loc[test_mask].copy()
    if train.empty or validation.empty or test.empty:
        raise ValueError('Uma das divisões ficou vazia; confira as datas da tabela')
    summary = {
        'train_rows': len(train),
        'validation_rows': len(validation),
        'test_rows': len(test),
        'excluded_boundary_rows': (len(frame) - len(train) - len(validation) - len(test)),
        'train_before': TRAIN_END.isoformat(),
        'validation_before': VALIDATION_END.isoformat(),
        'test_from': VALIDATION_END.isoformat(),
        'features': list(WEATHER_FEATURES) + ['temp_humidity', 'pressure_diff', 'hour_of_day'],
        'target': TARGET,
        'split_method': 'chronological',
    }
    return train, validation, test, summary

def evaluate(model, X, y):
    """Métricas de classificação binária (mantidas para compatibilidade)."""
    predictions = model.predict(X)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    return {
        'accuracy': float(accuracy_score(y, predictions)),
        'precision_rain': float(precision_score(y, predictions, zero_division=0)),
        'recall_rain': float(recall_score(y, predictions, zero_division=0)),
        'f1_rain': float(f1_score(y, predictions, zero_division=0)),
        'balanced_accuracy': float(balanced_accuracy_score(y, predictions)),
        'specificity': specificity,
        'matthews_corrcoef': float(matthews_corrcoef(y, predictions)),
        'actual_rain': int(np.sum(np.asarray(y) == 1)),
        'predicted_rain': int(np.sum(predictions == 1)),
        'confusion_matrix_labels_0_1': [
            [int(tn), int(fp)],
            [int(fn), int(tp)],
        ],
    }

def positive_probability(model, X):
    """Retorna a probabilidade da classe 1."""
    probabilities = model.predict_proba(X)
    positive_index = list(model.classes_).index(1)
    return probabilities[:, positive_index]

def probability_metrics(y, proba):
    """Métricas que não dependem de limiar."""
    y = np.asarray(y)
    proba = np.asarray(proba, dtype=float)
    return {
        'pr_auc': float(average_precision_score(y, proba)),
        'roc_auc': float(roc_auc_score(y, proba)),
        'brier': float(brier_score_loss(y, proba)),
        'log_loss': float(log_loss(y, proba)),
    }

def threshold_metrics(y, proba, threshold=0.5):
    """Métricas num ponto de corte específico."""
    y = np.asarray(y)
    proba = np.asarray(proba, dtype=float)
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    precision = float(precision_score(y, pred, zero_division=0))
    recall = float(recall_score(y, pred, zero_division=0))
    f1 = float(f1_score(y, pred, zero_division=0))
    return {
        'threshold': float(threshold),
        'precision_rain': precision,
        'recall_rain': recall,
        'f1_rain': f1,
        'predicted_rain': int(np.sum(pred == 1)),
        'confusion_matrix_labels_0_1': [
            [int(tn), int(fp)],
            [int(fn), int(tp)],
        ],
    }

def threshold_table(y, proba, extra=()):
    """Precisão e recall por limiar."""
    values = sorted({*TABLE_THRESHOLDS, *[round(float(t), 2) for t in extra]})
    rows = []
    for threshold in values:
        metrics = threshold_metrics(y, proba, threshold)
        rows.append({
            key: metrics[key]
            for key in ('threshold', 'precision_rain', 'recall_rain', 'f1_rain', 'predicted_rain')
        })
    return rows

def choose_threshold(y, proba, beta=1.0):
    """Limiar que maximiza F‑beta (beta=1 para F1)."""
    if beta <= 0:
        raise ValueError('beta deve ser maior que zero')
    y = np.asarray(y)
    best_threshold, best_score = 0.5, -1.0
    for threshold in THRESHOLD_GRID:
        predictions = (np.asarray(proba) >= threshold).astype(int)
        score = fbeta_score(y, predictions, beta=beta, zero_division=0)
        if score > best_score:
            best_threshold, best_score = float(threshold), float(score)
    return best_threshold

# ---------------------------------------------------------------------------
# Construção de modelos
# ---------------------------------------------------------------------------

def build_models():
    """Modelos candidatos – Random Forests agora com 1000 árvores.
    Também incluímos o modelo balanceado com os mesmos hiper‑parâmetros.
    """
    return {
        'baseline': DummyClassifier(strategy='constant', constant=0),
        'random_forest': RandomForestClassifier(
            n_estimators=1000,
            max_depth=None,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            class_weight=None,
        ),
        'baseline_prior': DummyClassifier(strategy='prior'),
        'logistic': make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, random_state=42),
        ),
        'random_forest_balanced': RandomForestClassifier(
            n_estimators=1000,
            max_depth=None,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced_subsample',
        ),
    }

# ---------------------------------------------------------------------------
# Validação cruzada por ano
# ---------------------------------------------------------------------------

def rolling_year_cv(frame, models, features):
    """Validação cruzada cronológica por ano (2023‑2025)."""
    cutoff = VALIDATION_END.tz_convert('UTC')
    dev = frame[frame['target_time'] < cutoff]
    folds = {}
    collected = {name: [] for name in models}
    for year in CV_VALIDATION_YEARS:
        start = pd.Timestamp(f'{year}-01-01', tz=WEATHER_TIMEZONE).tz_convert('UTC')
        end = pd.Timestamp(f'{year + 1}-01-01', tz=WEATHER_TIMEZONE).tz_convert('UTC')
        fold_train = dev[dev['target_time'] < start]
        fold_val = dev[(dev['time'] >= start) & (dev['target_time'] < end)]
        if (
            fold_train.empty or fold_val.empty or
            fold_train[TARGET].nunique() < 2 or fold_val[TARGET].nunique() < 2
        ):
            folds[str(year)] = {'skipped': 'dados insuficientes ou classe única'}
            continue
        entry = {
            'train_rows': int(len(fold_train)),
            'validation_rows': int(len(fold_val)),
            'validation_rain_rate': float(fold_val[TARGET].mean()),
        }
        for name, model in models.items():
            fitted = clone(model).fit(fold_train[features], fold_train[TARGET])
            proba = positive_probability(fitted, fold_val[features])
            prob = probability_metrics(fold_val[TARGET], proba)
            thr = threshold_metrics(fold_val[TARGET], proba, 0.5)
            row = {
                'pr_auc': prob['pr_auc'],
                'roc_auc': prob['roc_auc'],
                'brier': prob['brier'],
                'precision_rain_at_0.5': thr['precision_rain'],
                'recall_rain_at_0.5': thr['recall_rain'],
                'f1_rain_at_0.5': thr['f1_rain'],
            }
            entry[name] = row
            collected[name].append(row)
        folds[str(year)] = entry
    summary = {}
    for name, rows in collected.items():
        if not rows:
            continue
        summary[name] = {
            metric: {'mean': float(np.mean([r[metric] for r in rows])),
                     'std': float(np.std([r[metric] for r in rows]))}
            for metric in rows[0]
        }
    return {'validation_years': CV_VALIDATION_YEARS, 'folds': folds, 'summary_mean_std': summary}

# ---------------------------------------------------------------------------
# Importância por permutação (validacao)
# ---------------------------------------------------------------------------

def validation_importance(models, X, y, features):
    """Importância por permutação (queda de PR‑AUC) na validação."""
    if y.nunique() < 2:
        return {}
    importance = {}
    eligible = ('random_forest', 'random_forest_balanced', 'logistic')
    for name in eligible:
        if name not in models:
            continue
        result = permutation_importance(
            models[name], X, y,
            scoring='average_precision',
            n_repeats=5,
            random_state=42,
            n_jobs=1,
        )
        importance[name] = {
            feature: {'mean': float(result.importances_mean[i]),
                      'std': float(result.importances_std[i])}
            for i, feature in enumerate(features)
        }
    return importance

# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------

THRESHOLD_GRID = np.round(np.arange(0.05, 0.951, 0.01), 2)
TABLE_THRESHOLDS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]

def run(training_path, output_dir, evaluate_test=False, beta=1.0, rolling_cv=True):
    """Treina os modelos e grava resultados.
    Parámetros `beta` e `rolling_cv` podem ser ajustados para novos experimentos.
    """
    training_path = Path(training_path).resolve()
    output_dir = Path(output_dir).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()
    if not output_dir.is_relative_to(experiments_root):
        raise ValueError('A saída deve ficar dentro de data/experiments')
    if output_dir.exists():
        raise ValueError('A pasta de saída já existe; escolha outra')
    if beta <= 0:
        raise ValueError('beta deve ser maior que zero')
    frame = load_table(training_path)
    train, validation, test, split_summary = split_data(frame)
    # Conjunto de atributos inclui os originais e os derivados
    all_features = list(WEATHER_FEATURES) + ['temp_humidity', 'pressure_diff', 'hour_of_day']
    X_train = train[all_features]
    y_train = train[TARGET]
    X_validation = validation[all_features]
    y_validation = validation[TARGET]
    if y_train.nunique() < 2:
        raise ValueError('O treino precisa ter as duas classes')
    models = build_models()
    output_dir.mkdir(parents=True)
    metrics_validation = {}
    thresholds = {}
    selected_thresholds = {}
    model_hashes = {}
    predictions_validation = validation[['time', 'target_time', TARGET]].copy()
    for name, model in models.items():
        model.fit(X_train, y_train)
        model_path = output_dir / f'{name}.joblib'
        joblib.dump(model, model_path)
        model_hashes[model_path.name] = hashlib.sha256(model_path.read_bytes()).hexdigest()
        metrics_validation[name] = evaluate(model, X_validation, y_validation)
        proba = positive_probability(model, X_validation)
        prob_metrics = probability_metrics(y_validation, proba)
        thr = threshold_metrics(y_validation, proba, 0.5)
        chosen_threshold = choose_threshold(y_validation, proba, beta=beta)
        selected_thresholds[name] = chosen_threshold
        thresholds[name] = {
            'beta': beta,
            'selected_threshold': chosen_threshold,
            'selected_metrics': threshold_metrics(y_validation, proba, chosen_threshold),
            'at_0.5': thr,
            'table': threshold_table(y_validation, proba, extra=THRESHOLD_GRID),
        }
        predictions_validation[f'{name}_probability_rain'] = proba
        predictions_validation[f'{name}_prediction'] = model.predict(X_validation)
        # grava métricas de probabilidade separadamente
        (output_dir / f'metrics_{name}_prob.json').write_text(
            json.dumps(prob_metrics, ensure_ascii=False, indent=2), encoding='utf-8')
        # importância por permutação (salva para os modelos RF e logistic)
        if name in ('random_forest', 'random_forest_balanced', 'logistic'):
            imp = validation_importance({name: model}, X_validation, y_validation, all_features)
            (output_dir / f'importance_{name}.json').write_text(
                json.dumps(imp.get(name, {}), ensure_ascii=False, indent=2), encoding='utf-8')

    split_summary.update({
        'total_rows': len(frame),
        'training_source': str(training_path),
        'training_source_sha256': hashlib.sha256(training_path.read_bytes()).hexdigest(),
        'engineered_features': ['temp_humidity', 'pressure_diff', 'hour_of_day'],
    })
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'pandas': pd.__version__,
        'numpy': np.__version__,
        'scikit_learn': __import__('sklearn').__version__,
        'joblib': joblib.__version__,
        'features': all_features,
        'original_features': list(WEATHER_FEATURES),
        'engineered_features': ['temp_humidity', 'pressure_diff', 'hour_of_day'],
        'target': TARGET,
        'threshold_default': 0.5,
        'threshold_selection': {'method': 'max_fbeta_on_validation', 'beta': beta,
                                'selected_by_model': selected_thresholds},
        'models': {name: model.get_params() for name, model in models.items()},
        'model_sha256': model_hashes,
        'training_source_sha256': split_summary['training_source_sha256'],
        'training_source': str(training_path),
        'split_method': 'chronological',
        'timezone': WEATHER_TIMEZONE,
        'validation_end': VALIDATION_END.isoformat(),
        'train_end': TRAIN_END.isoformat(),
        'rolling_cv_enabled': rolling_cv,
        'test_evaluated': evaluate_test,
    }
    (output_dir / 'split_summary.json').write_text(json.dumps(split_summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    (output_dir / 'metrics_validation.json').write_text(json.dumps(metrics_validation, ensure_ascii=False, indent=2), encoding='utf-8')
    (output_dir / 'thresholds.json').write_text(json.dumps(thresholds, ensure_ascii=False, indent=2), encoding='utf-8')
    predictions_validation.to_csv(output_dir / 'predictions_validation.csv', index=False)
    if rolling_cv:
        cv_summary = rolling_year_cv(frame, models, all_features)
        (output_dir / 'rolling_cv_summary.json').write_text(json.dumps(cv_summary, ensure_ascii=False, indent=2), encoding='utf-8')
    if evaluate_test:
        X_test = test[all_features]
        y_test = test[TARGET]
        metrics_test = {}
        predictions_test = test[['time', 'target_time', TARGET]].copy()
        for name, model in models.items():
            proba = positive_probability(model, X_test)
            metrics_test[name] = {
                **evaluate(model, X_test, y_test),
                **probability_metrics(y_test, proba),
                'threshold_metrics_selected_on_validation': threshold_metrics(
                    y_test, proba, selected_thresholds[name]),
                'selected_threshold': selected_thresholds[name],
            }
            predictions_test[f'{name}_probability_rain'] = proba
            predictions_test[f'{name}_prediction'] = model.predict(X_test)
        (output_dir / 'metrics_test.json').write_text(json.dumps(metrics_test, ensure_ascii=False, indent=2), encoding='utf-8')
        predictions_test.to_csv(output_dir / 'predictions_test.csv', index=False)
    print(json.dumps({
        'output_dir': str(output_dir),
        'split': split_summary,
        'validation_metrics': metrics_validation,
        'test_evaluated': evaluate_test,
    }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=cfg['training'])
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data' / 'experiments' / ('weather_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')))
    parser.add_argument('--evaluate-test', action='store_true', help='Avaliar no conjunto de teste; use apenas após decidir o modelo.')
    parser.add_argument('--beta', type=float, default=1.0, help='Beta para F‑beta ao escolher limiar.')
    parser.add_argument('--no-rolling-cv', dest='rolling_cv', action='store_false', help='Desabilitar validação cruzada cronológica.')
    args = parser.parse_args()
    run(args.input, args.output_dir, args.evaluate_test, beta=args.beta, rolling_cv=args.rolling_cv)
