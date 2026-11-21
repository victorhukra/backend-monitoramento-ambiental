"""Testes unitários do pipeline de treinamento e do ensemble meteorológico."""

from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.isotonic import IsotonicRegression

from config import ROOT, WEATHER_FEATURES
from scripts.train_v6 import (
    CV_YEARS,
    DEV_END,
    FEATURES,
    SEEDS,
    TARGET,
    load_table,
    metrics,
    temporal_fold,
)
from src.models.weather_ensemble import (
    MODEL_NAMES,
    MODEL_VERSION,
    RAW_FIELDS,
    SimpleMeanCalibratedEnsemble,
    WEIGHTS,
)


def make_synthetic_table() -> pd.DataFrame:
    """Cria uma tabela sintética de registros horários para teste de funções."""
    times = pd.date_range('2024-12-31 20:00-03:00', periods=10, freq='h').tz_convert('UTC')
    data = {
        'time': times,
        'target_time': times + pd.Timedelta(hours=1),
        'temperature_2m': [20.0 + i for i in range(len(times))],
        'relative_humidity_2m': [70.0 - i for i in range(len(times))],
        'pressure_msl': [1010.0 + (i % 3) for i in range(len(times))],
        'cloud_cover': [50.0] * len(times),
        TARGET: [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
    }
    return pd.DataFrame(data)


class TrainV6Tests(unittest.TestCase):

    def test_features_contract(self):
        """Garante que a lista de features contenha as 4 variáveis brutas e as 3 derivadas."""
        expected = [
            'temperature_2m',
            'relative_humidity_2m',
            'pressure_msl',
            'cloud_cover',
            'temp_humidity',
            'pressure_diff',
            'hour_of_day',
        ]
        self.assertEqual(FEATURES, expected)
        self.assertEqual(TARGET, 'rain_next_hour')

    def test_load_table_calculates_derived_features(self):
        """Verifica se load_table calcula temp_humidity, pressure_diff e hour_of_day."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / 'test_data.csv'
            raw = make_synthetic_table()
            raw.to_csv(csv_path, index=False)

            loaded = load_table(csv_path)
            self.assertEqual(len(loaded), len(raw))
            self.assertIn('temp_humidity', loaded.columns)
            self.assertIn('pressure_diff', loaded.columns)
            self.assertIn('hour_of_day', loaded.columns)

            expected_th = loaded['temperature_2m'] * loaded['relative_humidity_2m']
            np.testing.assert_allclose(loaded['temp_humidity'], expected_th)

    def test_temporal_fold_boundaries(self):
        """Verifica se o fold temporal respeita as fronteiras cronológicas sem data leakage."""
        times = pd.date_range('2021-12-31 20:00Z', '2022-01-02 02:00Z', freq='h')
        frame = pd.DataFrame({
            'time': times,
            'target_time': times + pd.Timedelta(hours=1),
            'temperature_2m': [20.0] * len(times),
            'relative_humidity_2m': [70.0] * len(times),
            'pressure_msl': [1010.0] * len(times),
            'cloud_cover': [50.0] * len(times),
            TARGET: np.arange(len(times)) % 2,
        })
        train, valid = temporal_fold(frame, 2022)
        start = pd.Timestamp('2022-01-01', tz='America/Sao_Paulo').tz_convert('UTC')

        self.assertTrue((train['target_time'] < start).all())
        self.assertTrue((valid['time'] >= start).all())

    def test_metrics_calculation(self):
        """Verifica o cálculo das métricas de probabilidade e classificação binária."""
        y_true = np.array([0, 0, 1, 1])
        probs = np.array([0.1, 0.4, 0.6, 0.9])
        res = metrics(y_true, probs)

        self.assertIn('pr_auc', res)
        self.assertIn('roc_auc', res)
        self.assertIn('brier', res)
        self.assertIn('f1_at_0_5', res)
        self.assertEqual(res['false_positives_at_0_5'], 0)
        self.assertEqual(res['false_negatives_at_0_5'], 0)


class EnsembleTests(unittest.TestCase):

    def setUp(self):
        X_dummy = pd.DataFrame(np.ones((10, len(FEATURES))), columns=FEATURES)
        y_dummy = np.array([0, 1] * 5)

        self.models = {}
        self.calibrators = {}
        for name in MODEL_NAMES:
            model = DummyClassifier(strategy='prior')
            model.fit(X_dummy, y_dummy)
            self.models[name] = model

            calibrator = IsotonicRegression(out_of_bounds='clip')
            calibrator.fit([0.2, 0.8], [0, 1])
            self.calibrators[name] = calibrator

        self.ensemble = SimpleMeanCalibratedEnsemble(
            models=self.models,
            calibrators=self.calibrators,
            threshold=0.5,
            model_version=MODEL_VERSION,
        )

    def test_prepare_features_creates_7_columns(self):
        weather_input = {
            'temperature_2m': 22.5,
            'relative_humidity_2m': 80.0,
            'pressure_msl': 1012.0,
            'cloud_cover': 60.0,
            'pressure_msl_previous_hour': 1010.0,
        }
        ref_time = '2025-06-01T15:00:00-03:00'
        features_df = self.ensemble.prepare_features(weather_input, ref_time)

        self.assertEqual(list(features_df.columns), list(FEATURES))
        self.assertEqual(features_df.shape, (1, 7))
        self.assertEqual(features_df['pressure_diff'].iloc[0], 2.0)
        self.assertEqual(features_df['hour_of_day'].iloc[0], 15)

    def test_predict_one_returns_expected_contract(self):
        weather_input = {
            'temperature_2m': 22.5,
            'relative_humidity_2m': 80.0,
            'pressure_msl': 1012.0,
            'cloud_cover': 60.0,
            'pressure_msl_previous_hour': 1010.0,
        }
        ref_time = '2025-06-01T15:00:00-03:00'
        prediction = self.ensemble.predict_one(weather_input, ref_time)

        self.assertIn('rain_probability', prediction)
        self.assertIn('rain_predicted', prediction)
        self.assertIn('decision_threshold', prediction)
        self.assertEqual(prediction['model_version'], MODEL_VERSION)
        self.assertIsInstance(prediction['rain_predicted'], (bool, np.bool_))


if __name__ == '__main__':
    unittest.main()
