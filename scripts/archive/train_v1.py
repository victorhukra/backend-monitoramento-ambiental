# Script original arquivado - preservado para referência

"""Treinamento experimental para prever chuva na próxima hora.

Usa quatro variáveis meteorológicas em T para prever rain_next_hour.
A divisão dos dados é cronológica; o conjunto de teste é opcional.
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
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

# Permite executar o script diretamente a partir da pasta scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, WEATHER_FEATURES, settings

TARGET = 'rain_next_hour'
TRAIN_END = pd.Timestamp('2025-01-01T00:00:00-03:00')
VALIDATION_END = pd.Timestamp('2026-01-01T00:00:00-03:00')

def load_table(path):
    """Carrega e valida a tabela preparada, sem alterar o arquivo original."""
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
    features = frame[list(WEATHER_FEATURES)].to_numpy(dtype=float)
    if not np.isfinite(features).all():
        raise ValueError('Há valores ausentes ou não finitos nas variáveis')
    expected_target_time = frame['time'] + pd.Timedelta(hours=1)
    if not frame['target_time'].eq(expected_target_time).all():
        raise ValueError('target_time não corresponde exatamente a time + 1h')
    return frame.sort_values('time').reset_index(drop=True)

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
        'features': list(WEATHER_FEATURES),
        'target': TARGET,
        'split_method': 'chronological',
    }
    return train, validation, test, summary

def evaluate(model, X, y):
    predictions = model.predict(X)
    return {
        'accuracy': float(accuracy_score(y, predictions)),
        'precision_rain': float(precision_score(y, predictions, zero_division=0)),
        'recall_rain': float(recall_score(y, predictions, zero_division=0)),
        'f1_rain': float(f1_score(y, predictions, zero_division=0)),
        'actual_rain': int(np.sum(np.asarray(y) == 1)),
        'predicted_rain': int(np.sum(predictions == 1)),
        'confusion_matrix_labels_0_1': confusion_matrix(y, predictions, labels=[0, 1]).tolist(),
    }

def positive_probability(model, X):
    probabilities = model.predict_proba(X)
    positive_index = list(model.classes_).index(1)
    return probabilities[:, positive_index]

def run(training_path, output_dir, evaluate_test=False):
    training_path = Path(training_path).resolve()
    output_dir = Path(output_dir).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()
    if not output_dir.is_relative_to(experiments_root):
        raise ValueError('A saída deve ficar dentro de data/experiments')
    if output_dir.exists():
        raise ValueError('A pasta de saída já existe; escolha outra')
    frame = load_table(training_path)
    train, validation, test, split_summary = split_data(frame)
    X_train = train[list(WEATHER_FEATURES)]
    y_train = train[TARGET]
    X_validation = validation[list(WEATHER_FEATURES)]
    y_validation = validation[TARGET]
    models = {
        'baseline': DummyClassifier(strategy='constant', constant=0),
        'random_forest': RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=1,
            class_weight=None,
        ),
    }
    output_dir.mkdir(parents=True)
    metrics_validation = {}
    predictions_validation = validation[['time', 'target_time', TARGET]].copy()
    for name, model in models.items():
        model.fit(X_train, y_train)
        joblib.dump(model, output_dir / f'{name}.joblib')
        metrics_validation[name] = evaluate(model, X_validation, y_validation)
        predictions_validation[f'{name}_probability_rain'] = positive_probability(model, X_validation)
        predictions_validation[f'{name}_prediction'] = model.predict(X_validation)
    split_summary.update({
        'total_rows': len(frame),
        'training_source': str(training_path),
        'training_source_sha256': hashlib.sha256(training_path.read_bytes()).hexdigest(),
    })
    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'pandas': pd.__version__,
        'numpy': np.__version__,
        'scikit_learn': __import__('sklearn').__version__,
        'joblib': joblib.__version__,
        'features': list(WEATHER_FEATURES),
        'target': TARGET,
        'threshold': 0.5,
        'random_forest_parameters': models['random_forest'].get_params(),
        'test_evaluated': evaluate_test,
    }
    (output_dir / 'split_summary.json').write_text(json.dumps(split_summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    (output_dir / 'metrics_validation.json').write_text(json.dumps(metrics_validation, ensure_ascii=False, indent=2), encoding='utf-8')
    predictions_validation.to_csv(output_dir / 'predictions_validation.csv', index=False)
    if evaluate_test:
        X_test = test[list(WEATHER_FEATURES)]
        y_test = test[TARGET]
        metrics_test = {name: evaluate(model, X_test, y_test) for name, model in models.items()}
        (output_dir / 'metrics_test.json').write_text(json.dumps(metrics_test, ensure_ascii=False, indent=2), encoding='utf-8')
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
    args = parser.parse_args()
    run(args.input, args.output_dir, args.evaluate_test)
