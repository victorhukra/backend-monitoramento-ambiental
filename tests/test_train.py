
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.train import (
    TARGET,
    TRAIN_END,
    VALIDATION_END,
    load_table,
    split_data,
    positive_probability,
)
from sklearn.dummy import DummyClassifier
from config import WEATHER_FEATURES


def make_table():
    """Cria registros horários sintéticos ao redor dos limites temporais."""
    times = pd.to_datetime([
        '2024-12-31T21:00:00-03:00',
        '2024-12-31T22:00:00-03:00',
        '2024-12-31T23:00:00-03:00',
        '2025-01-01T00:00:00-03:00',
        '2025-06-01T12:00:00-03:00',
        '2025-12-31T22:00:00-03:00',
        '2025-12-31T23:00:00-03:00',
        '2026-01-01T00:00:00-03:00',
        '2026-01-01T01:00:00-03:00',
    ], utc=True)

    data = {
        'time': times,
        'target_time': times + pd.Timedelta(hours=1),
        'temperature_2m': [20.0] * len(times),
        'relative_humidity_2m': [70.0] * len(times),
        'pressure_msl': [1010.0] * len(times),
        'cloud_cover': [50.0] * len(times),
        TARGET: [0, 1, 0, 1, 0, 1, 0, 1, 0],
    }
    return pd.DataFrame(data)


class TrainTests(unittest.TestCase):

    def test_split_respects_time_boundaries(self):
        frame = make_table()
        train, validation, test, summary = split_data(frame)

        # Converte os limites locais de São Paulo para UTC.
        train_end = TRAIN_END.tz_convert('UTC')
        validation_end = VALIDATION_END.tz_convert('UTC')

        self.assertTrue(
            (train['time'] < train_end).all()
        )
        self.assertTrue(
            (train['target_time'] < train_end).all()
        )

        self.assertTrue(
            (validation['time'] >= train_end).all()
        )
        self.assertTrue(
            (validation['time'] < validation_end).all()
        )
        self.assertTrue(
            (validation['target_time'] < validation_end).all()
        )

        self.assertTrue(
            (test['time'] >= validation_end).all()
        )

        self.assertEqual(
            summary['train_rows']
            + summary['validation_rows']
            + summary['test_rows']
            + summary['excluded_boundary_rows'],
            len(frame),
        )


    def test_features_are_finite_and_target_is_binary(self):
        frame = make_table()
        self.assertEqual(list(WEATHER_FEATURES), [
            'temperature_2m',
            'relative_humidity_2m',
            'pressure_msl',
            'cloud_cover',
        ])
        self.assertTrue(frame[TARGET].isin([0, 1]).all())

    def test_positive_probability_uses_class_one(self):
        X = pd.DataFrame({'feature': [0, 1, 2, 3]})
        y = np.array([0, 0, 1, 1])
        model = DummyClassifier(strategy='prior')
        model.fit(X, y)

        probabilities = positive_probability(model, X)
        self.assertEqual(len(probabilities), len(X))
        self.assertTrue(np.isfinite(probabilities).all())
        self.assertTrue(((probabilities >= 0) & (probabilities <= 1)).all())

    def test_load_table_rejects_missing_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'invalid.csv'
            pd.DataFrame({'time': ['2025-01-01T00:00:00Z']}).to_csv(
                path, index=False
            )

            with self.assertRaisesRegex(ValueError, 'Colunas ausentes'):
                load_table(path)


if __name__ == '__main__':
    unittest.main()
