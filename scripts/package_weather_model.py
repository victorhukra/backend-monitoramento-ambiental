"""Empacota o ensemble meteorológico final a partir dos artefatos da v6.

Lê os modelos Random Forest treinados na v6, ajusta os calibradores isotônicos
a partir das previsões out-of-fold (OOF), valida a paridade da engenharia de
features contra um caso histórico e grava o bundle final (weather_ensemble.joblib)
com seu respectivo manifesto.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.isotonic import IsotonicRegression

# Inclusão da raiz do projeto para imports locais
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, settings
from scripts.train_v6 import FEATURES, load_table
from src.models.weather_ensemble import (
    MODEL_NAMES,
    MODEL_VERSION,
    SimpleMeanCalibratedEnsemble,
    WEIGHTS,
)


def compute_sha256(path: Path) -> str:
    """Calcula o hash SHA-256 do arquivo no caminho especificado."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fit_isotonic_calibrators(oof_df: pd.DataFrame) -> Tuple[Dict[str, IsotonicRegression], Dict[str, int]]:
    """Ajusta regressões isotônicas nas probabilidades fora da amostra (OOF).
    
    Args:
        oof_df: DataFrame com as previsões OOF ('strategy', 'rain_next_hour', 'probability').
        
    Returns:
        Dicionário de calibradores ajustados e contagem de amostras por modelo.
    """
    calibrators: Dict[str, IsotonicRegression] = {}
    counts: Dict[str, int] = {}

    for name in MODEL_NAMES:
        subset = oof_df[oof_df['strategy'] == name]
        if subset.empty or subset['rain_next_hour'].nunique() != 2:
            raise ValueError(f'OOF insuficiente para calibrar {name}.')

        calibrator = IsotonicRegression(out_of_bounds='clip')
        calibrator.fit(
            subset['probability'].to_numpy(),
            subset['rain_next_hour'].to_numpy(),
        )
        calibrators[name] = calibrator
        counts[name] = int(len(subset))

    return calibrators, counts


def run_feature_parity_check(
    bundle: SimpleMeanCalibratedEnsemble,
    source_path: Path,
) -> Tuple[pd.Series, Dict[str, Any]]:
    """Verifica se a engenharia de features em tempo de inferência reproduz os dados preparados.
    
    Não avalia acurácia de predição; apenas garante consistência matemática do cálculo
    das 7 features (interação temperatura x umidade, variação barométrica e hora local).
    """
    frame = load_table(source_path)
    eligible = frame[
        frame.target_time < pd.Timestamp('2026-01-01T00:00:00-03:00').tz_convert('UTC')
    ]
    if len(eligible) < 2:
        raise ValueError('Dados insuficientes para teste de paridade.')

    row = eligible.iloc[1]
    previous_row = eligible.iloc[0]

    if row.time - previous_row.time != pd.Timedelta(hours=1):
        raise ValueError('A linha de referência não possui observação imediatamente anterior (1 hora).')

    previous_pressure = float(previous_row.pressure_msl)
    weather_input = {
        'temperature_2m': row.temperature_2m,
        'relative_humidity_2m': row.relative_humidity_2m,
        'pressure_msl': row.pressure_msl,
        'cloud_cover': row.cloud_cover,
        'pressure_msl_previous_hour': previous_pressure,
    }

    engineered = bundle.prepare_features(weather_input, row.time)
    expected_values = row[list(FEATURES)].to_numpy(float)
    actual_values = engineered.iloc[0].to_numpy(float)

    if not np.allclose(actual_values, expected_values, rtol=0, atol=1e-9):
        raise ValueError('A engenharia de features da integração não reproduz a tabela preparada.')

    prediction = bundle.predict_one(weather_input, row.time)
    if not np.isfinite(prediction['rain_probability']):
        raise ValueError('Probabilidade inválida no smoke test de compatibilidade.')

    return row, prediction


def package(v6_dir: Path, out_dir: Path) -> None:
    """Orquestra o empacotamento do modelo ensemble e calibração isotônica."""
    v6_path = Path(v6_dir).resolve()
    output_path = Path(out_dir).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()

    if not output_path.is_relative_to(experiments_root) or output_path.exists():
        raise ValueError('A saída deve ser uma pasta nova dentro de data/experiments.')

    # Validação do manifesto da v6 e da fonte processada
    v6_manifest_path = v6_path / 'manifest.json'
    v6_manifest = json.loads(v6_manifest_path.read_text(encoding='utf-8'))
    oof_path = v6_path / 'predictions_oof.csv'
    source_path = Path(settings()['training']).resolve()

    if compute_sha256(source_path) != v6_manifest['source_sha256']:
        raise ValueError('Hash da tabela processada diverge do manifesto v6.')

    # Carregamento e validação de integridade dos 3 modelos Random Forest da v6
    models: Dict[str, Any] = {}
    expected_hashes = v6_manifest['model_sha256']
    for name in MODEL_NAMES:
        model_filename = f'{name}_leaf10_trees400.joblib'
        model_file_path = v6_path / model_filename

        if compute_sha256(model_file_path) != expected_hashes[model_filename]:
            raise ValueError(f'Hash divergente para {model_filename}.')

        loaded_model = joblib.load(model_file_path)
        if tuple(loaded_model.feature_names_in_) != tuple(FEATURES):
            raise ValueError(f'Features inesperadas em {model_filename}.')

        models[name] = loaded_model

    # Ajuste dos calibradores isotônicos com as previsões OOF
    oof_df = pd.read_csv(oof_path, usecols=['strategy', 'rain_next_hour', 'probability'])
    oof_df = oof_df[oof_df['strategy'].isin(MODEL_NAMES)]
    calibrators, calibration_counts = fit_isotonic_calibrators(oof_df)

    # Criação do diretório e serialização dos artefatos
    output_path.mkdir(parents=True)
    calibrator_path = output_path / 'isotonic_calibrators.joblib'
    joblib.dump(calibrators, calibrator_path, compress=3)

    bundle = SimpleMeanCalibratedEnsemble(
        models=models,
        calibrators=calibrators,
        threshold=0.5,
        model_version=MODEL_VERSION,
    )
    bundle_path = output_path / 'weather_ensemble.joblib'
    joblib.dump(bundle, bundle_path, compress=3)

    # Verificação de paridade de features com um registro histórico
    ref_row, smoke_prediction = run_feature_parity_check(bundle, source_path)

    # Geração do manifesto de entrega para integração
    manifest = {
        'model_version': MODEL_VERSION,
        'artifact_status': 'integration_candidate_not_operationally_approved',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'numpy': np.__version__,
        'pandas': pd.__version__,
        'scikit_learn': sklearn.__version__,
        'joblib': joblib.__version__,
        'source_experiment': 'weather_v6_20261105T120000Z',
        'evaluation_reference': 'weather_v7_20261105T183313Z',
        'source_dataset_sha256': compute_sha256(source_path),
        'oof_predictions_sha256': compute_sha256(oof_path),
        'features': list(FEATURES),
        'required_weather_inputs': list(bundle.RAW_FIELDS),
        'feature_engineering': {
            'temp_humidity': 'temperature_2m * relative_humidity_2m',
            'pressure_diff': 'pressure_msl - pressure_msl_previous_hour (T-1h)',
            'hour_of_day': 'reference_time converted to America/Sao_Paulo, hour',
        },
        'members': {
            name: {
                'class_weight': models[name].class_weight,
                'n_estimators': models[name].n_estimators,
                'min_samples_leaf': models[name].min_samples_leaf,
                'random_state': models[name].random_state,
                'v6_model_sha256': expected_hashes[f'{name}_leaf10_trees400.joblib'],
                'calibration': 'isotonic',
                'calibration_oof_rows': calibration_counts[name],
            }
            for name in MODEL_NAMES
        },
        'weights': WEIGHTS,
        'threshold': 0.5,
        'threshold_status': 'provisional; use response field decision_threshold',
        'test_2026_used': False,
        'independent_blind_test': False,
        'bundle_file': bundle_path.name,
        'bundle_sha256': compute_sha256(bundle_path),
        'calibrators_file': calibrator_path.name,
        'calibrators_sha256': compute_sha256(calibrator_path),
        'adapter_sha256': compute_sha256(ROOT / 'src' / 'models' / 'weather_ensemble.py'),
        'packager_sha256': compute_sha256(Path(__file__)),
        'feature_compatibility_smoke': {
            'passed': True,
            'reference_time': str(ref_row.time),
            'model_output': smoke_prediction,
            'note': 'feature-parity check only; not a performance test',
        },
    }

    manifest_output_path = output_path / 'manifest.json'
    manifest_output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding='utf-8',
    )

    print(
        json.dumps(
            {
                'output_dir': str(output_path),
                'bundle': str(bundle_path),
                'manifest': str(manifest_output_path),
                'model_version': MODEL_VERSION,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == '__main__':
    default_v6 = ROOT / 'data' / 'experiments' / 'weather_v6_20261105T120000Z'
    default_candidate = (
        ROOT / 'data' / 'experiments' / (
            'weather_v6_integration_candidate_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        )
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v6-dir', type=Path, default=default_v6)
    parser.add_argument('--output-dir', type=Path, default=default_candidate)
    args = parser.parse_args()

    package(args.v6_dir, args.output_dir)
