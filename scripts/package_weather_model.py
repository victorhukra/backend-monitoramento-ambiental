"""Empacota o ensemble meteorológico calibrado a partir dos artefatos da v6."""

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
from sklearn.isotonic import IsotonicRegression

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, settings
from scripts.train_v6 import FEATURES, load_table
from src.models.weather_ensemble import (
    MODEL_NAMES, MODEL_VERSION, WEIGHTS, SimpleMeanCalibratedEnsemble,
)


def compute_sha256(path):
    """Calcula o hash SHA-256 do arquivo informado."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fit_isotonic_calibrators(oof_df):
    """Ajusta um calibrador isotônico para cada modelo usando as previsões OOF."""
    calibrators, counts = {}, {}
    for name in MODEL_NAMES:
        subset = oof_df[oof_df['strategy'] == name]
        if subset.empty or subset['rain_next_hour'].nunique() != 2:
            raise ValueError(f'OOF insuficiente para calibrar {name}.')
        cal = IsotonicRegression(out_of_bounds='clip')
        cal.fit(subset['probability'].to_numpy(), subset['rain_next_hour'].to_numpy())
        calibrators[name] = cal
        counts[name] = int(len(subset))
    return calibrators, counts


def run_feature_parity_check(bundle, source_path):
    """Confere se prepare_features reproduz exatamente as 7 colunas da base de treino."""
    frame = load_table(source_path)
    eligible = frame[frame.target_time < pd.Timestamp('2026-01-01T00:00:00-03:00').tz_convert('UTC')]
    if len(eligible) < 2:
        raise ValueError('Dados insuficientes para teste de paridade.')

    row, previous_row = eligible.iloc[1], eligible.iloc[0]
    if row.time - previous_row.time != pd.Timedelta(hours=1):
        raise ValueError('A linha de referência não possui observação imediatamente anterior (1 hora).')

    weather_input = {
        'temperature_2m': row.temperature_2m,
        'relative_humidity_2m': row.relative_humidity_2m,
        'pressure_msl': row.pressure_msl,
        'cloud_cover': row.cloud_cover,
        'pressure_msl_previous_hour': float(previous_row.pressure_msl),
    }
    engineered = bundle.prepare_features(weather_input, row.time)
    if not np.allclose(engineered.iloc[0].to_numpy(float), row[list(FEATURES)].to_numpy(float), rtol=0, atol=1e-9):
        raise ValueError('A engenharia de features da integração não reproduz a tabela preparada.')

    prediction = bundle.predict_one(weather_input, row.time)
    if not np.isfinite(prediction['rain_probability']):
        raise ValueError('Probabilidade inválida no smoke test de compatibilidade.')
    return row, prediction


def package(v6_dir, out_dir):
    """Valida os modelos da v6, ajusta calibradores e grava weather_ensemble.joblib + manifest.json."""
    v6_path, output_path = Path(v6_dir).resolve(), Path(out_dir).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()
    if not output_path.is_relative_to(experiments_root) or output_path.exists():
        raise ValueError('A saída deve ser uma pasta nova dentro de data/experiments.')

    v6_manifest = json.loads((v6_path / 'manifest.json').read_text(encoding='utf-8'))
    oof_path = v6_path / 'predictions_oof.csv'
    source_path = Path(settings()['training']).resolve()
    if compute_sha256(source_path) != v6_manifest['source_sha256']:
        raise ValueError('Hash da tabela processada diverge do manifesto v6.')

    models = {}
    expected_hashes = v6_manifest['model_sha256']
    for name in MODEL_NAMES:
        filename = f'{name}_leaf10_trees400.joblib'
        model_path = v6_path / filename
        if compute_sha256(model_path) != expected_hashes[filename]:
            raise ValueError(f'Hash divergente para {filename}.')
        model = joblib.load(model_path)
        if tuple(model.feature_names_in_) != tuple(FEATURES):
            raise ValueError(f'Features inesperadas em {filename}.')
        models[name] = model

    oof_df = pd.read_csv(oof_path, usecols=['strategy', 'rain_next_hour', 'probability'])
    calibrators, cal_counts = fit_isotonic_calibrators(oof_df[oof_df['strategy'].isin(MODEL_NAMES)])

    output_path.mkdir(parents=True)
    calibrator_path = output_path / 'isotonic_calibrators.joblib'
    joblib.dump(calibrators, calibrator_path, compress=3)

    bundle = SimpleMeanCalibratedEnsemble(models, calibrators, threshold=0.5, model_version=MODEL_VERSION)
    bundle_path = output_path / 'weather_ensemble.joblib'
    joblib.dump(bundle, bundle_path, compress=3)

    ref_row, smoke_prediction = run_feature_parity_check(bundle, source_path)

    manifest = {
        'model_version': MODEL_VERSION,
        'artifact_status': 'integration_candidate_not_operationally_approved',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version, 'numpy': np.__version__, 'pandas': pd.__version__,
        'scikit_learn': sklearn.__version__, 'joblib': joblib.__version__,
        'source_experiment': v6_path.name,
        'source_dataset_sha256': compute_sha256(source_path),
        'oof_predictions_sha256': compute_sha256(oof_path),
        'features': list(FEATURES),
        'required_weather_inputs': list(bundle.RAW_FIELDS),
        'members': {
            name: {
                'class_weight': models[name].class_weight, 'n_estimators': models[name].n_estimators,
                'min_samples_leaf': models[name].min_samples_leaf, 'random_state': models[name].random_state,
                'v6_model_sha256': expected_hashes[f'{name}_leaf10_trees400.joblib'],
                'calibration': 'isotonic', 'calibration_oof_rows': cal_counts[name],
            }
            for name in MODEL_NAMES
        },
        'weights': WEIGHTS, 'threshold': 0.5, 'test_2026_used': False,
        'bundle_file': bundle_path.name, 'bundle_sha256': compute_sha256(bundle_path),
        'calibrators_file': calibrator_path.name, 'calibrators_sha256': compute_sha256(calibrator_path),
        'adapter_sha256': compute_sha256(ROOT / 'src' / 'models' / 'weather_ensemble.py'),
        'packager_sha256': compute_sha256(Path(__file__)),
        'feature_compatibility_smoke': {'passed': True, 'reference_time': str(ref_row.time), 'model_output': smoke_prediction},
    }
    manifest_path = output_path / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'output_dir': str(output_path), 'bundle': str(bundle_path), 'manifest': str(manifest_path), 'model_version': MODEL_VERSION}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v6-dir', type=Path, default=ROOT / 'data' / 'experiments' / 'weather_v6_20261105T120000Z')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data' / 'experiments' / f"weather_v6_integration_candidate_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    args = parser.parse_args()
    package(args.v6_dir, args.output_dir)
