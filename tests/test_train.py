
import hashlib
import json
import joblib
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.archive.train_v4 import (
    TARGET,
    TRAIN_END,
    VALIDATION_END,
    load_table,
    split_data,
    positive_probability,
    validation_importance,
    choose_threshold,
    run,
)
from sklearn.dummy import DummyClassifier
from config import ROOT, WEATHER_FEATURES
from scripts.train_v5 import (
    FEATURES as V5_FEATURES,
    candidates as v5_candidates,
    evaluate_models_on_test as v5_evaluate_models_on_test,
    evaluate_saved_models_test as v5_evaluate_saved_models_test,
    score_probabilities as v5_score_probabilities,
    temporal_fold as v5_temporal_fold,
)


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

    def test_load_table_sorts_before_pressure_difference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'unsorted.csv'
            times = [
                '2024-01-01T01:00:00-03:00',
                '2024-01-01T00:00:00-03:00',
                '2024-01-01T02:00:00-03:00',
            ]
            frame = pd.DataFrame({
                'time': times,
                'target_time': [
                    '2024-01-01T02:00:00-03:00',
                    '2024-01-01T01:00:00-03:00',
                    '2024-01-01T03:00:00-03:00',
                ],
                'temperature_2m': [20.0, 19.0, 21.0],
                'relative_humidity_2m': [70.0, 71.0, 69.0],
                'pressure_msl': [1002.0, 1000.0, 999.0],
                'cloud_cover': [50.0, 40.0, 60.0],
                TARGET: [0, 1, 0],
            })
            frame.to_csv(path, index=False)

            loaded = load_table(path)

            self.assertEqual(loaded['time'].is_monotonic_increasing, True)
            np.testing.assert_allclose(loaded['pressure_diff'], [0.0, 2.0, -3.0])

    def test_validation_importance_accepts_one_eligible_model(self):
        from sklearn.linear_model import LogisticRegression

        X = pd.DataFrame({
            'temperature_2m': np.linspace(0, 1, 40),
            'humidity': np.tile([0.0, 1.0], 20),
        })
        y = pd.Series(np.tile([0, 1], 20))
        model = LogisticRegression(random_state=42).fit(X, y)

        result = validation_importance(
            {'logistic': model}, X, y, list(X.columns)
        )

        self.assertEqual(set(result), {'logistic'})
        self.assertEqual(set(result['logistic']), set(X.columns))

    def test_threshold_beta_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, 'beta deve ser maior que zero'):
            choose_threshold([0, 1], [0.2, 0.8], beta=0)

    def test_optional_test_evaluation_writes_probabilities_and_predictions(self):
        from unittest.mock import patch

        experiments_root = ROOT / 'data' / 'experiments'
        experiments_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=experiments_root) as temp_dir:
            workspace = Path(temp_dir)
            input_path = workspace / 'synthetic.csv'
            output_path = workspace / 'run'
            times = pd.to_datetime([
                '2024-12-30T03:00:00Z', '2024-12-31T03:00:00Z',
                '2025-01-01T03:00:00Z', '2025-06-01T03:00:00Z',
                '2025-12-30T03:00:00Z', '2026-01-01T03:00:00Z',
                '2026-01-01T04:00:00Z',
            ], utc=True)
            frame = pd.DataFrame({
                'time': times,
                'target_time': times + pd.Timedelta(hours=1),
                'temperature_2m': [18, 20, 19, 22, 21, 20, 23],
                'relative_humidity_2m': [50, 70, 60, 80, 55, 75, 85],
                'pressure_msl': [1012, 1010, 1011, 1008, 1013, 1009, 1007],
                'cloud_cover': [10, 80, 30, 90, 20, 75, 95],
                TARGET: [0, 1, 0, 1, 0, 0, 1],
            })
            frame.to_csv(input_path, index=False)
            model_names = (
                'baseline', 'random_forest', 'baseline_prior', 'logistic',
                'random_forest_balanced',
            )
            with patch('scripts.archive.train_v4.build_models', return_value={
                name: DummyClassifier(strategy='prior') for name in model_names
            }), patch('scripts.archive.train_v4.validation_importance', return_value={}):
                run(input_path, output_path, evaluate_test=True, rolling_cv=False)

            metrics = json.loads((output_path / 'metrics_test.json').read_text())
            predictions = pd.read_csv(output_path / 'predictions_test.csv')
            manifest = json.loads((output_path / 'manifest.json').read_text())
            self.assertEqual(set(metrics), set(model_names))
            self.assertIn('pr_auc', metrics['random_forest'])
            self.assertEqual(len(predictions), 2)
            self.assertIn('random_forest_probability_rain', predictions.columns)
            self.assertEqual(len(manifest['features']), 7)
            self.assertFalse(manifest['rolling_cv_enabled'])
            self.assertTrue(manifest['test_evaluated'])
            model_hash = hashlib.sha256(
                (output_path / 'random_forest.joblib').read_bytes()
            ).hexdigest()
            self.assertEqual(manifest['model_sha256']['random_forest.joblib'], model_hash)


class TrainV5Tests(unittest.TestCase):
    def test_candidate_grid_covers_class_weights_leaf_size_and_tree_count(self):
        grid = v5_candidates()
        self.assertEqual(len(grid), 12)
        weights = {str(params['class_weight']) for params in grid.values()}
        self.assertIn('None', weights)
        self.assertIn('balanced_subsample', weights)
        self.assertIn('balanced', weights)
        self.assertEqual({p['min_samples_leaf'] for p in grid.values()}, {5, 10})
        self.assertEqual({p['n_estimators'] for p in grid.values()}, {250, 400, 800})

    def test_temporal_fold_does_not_train_on_rows_whose_target_crosses_boundary(self):
        times = pd.date_range('2021-12-31 20:00Z', '2022-01-02 02:00Z', freq='h')
        frame = pd.DataFrame({
            'time': times,
            'target_time': times + pd.Timedelta(hours=1),
            TARGET: np.arange(len(times)) % 2,
        })
        train, valid = v5_temporal_fold(frame, 2022)
        start = pd.Timestamp('2022-01-01', tz='America/Sao_Paulo').tz_convert('UTC')
        self.assertTrue((train['target_time'] < start).all())
        self.assertTrue((valid['time'] >= start).all())

    def test_score_probabilities_returns_probabilistic_and_threshold_metrics(self):
        scores = v5_score_probabilities([0, 0, 1, 1], [0.1, 0.6, 0.4, 0.9])
        self.assertAlmostEqual(scores['pr_auc'], 0.8333333333)
        self.assertAlmostEqual(scores['brier'], 0.185)
        self.assertEqual(scores['false_positives_at_0_5'], 1)
        self.assertEqual(scores['false_negatives_at_0_5'], 1)

    def test_frozen_model_test_evaluation_keeps_threshold_at_half(self):
        X_train = pd.DataFrame(np.arange(28).reshape(4, 7), columns=V5_FEATURES)
        model = DummyClassifier(strategy='prior').fit(X_train, [0, 0, 1, 1])
        times = pd.date_range('2026-01-01T00:00:00Z', periods=4, freq='h')
        test_frame = X_train.copy()
        test_frame['time'] = times
        test_frame['target_time'] = times + pd.Timedelta(hours=1)
        test_frame[TARGET] = [0, 1, 0, 1]
        metrics, predictions = v5_evaluate_models_on_test({'candidate': model}, test_frame)
        self.assertEqual(metrics['candidate']['test_rows'], 4)
        self.assertEqual(metrics['candidate']['selected_threshold'], 0.5)
        self.assertIn('candidate_probability_rain', predictions.columns)
        self.assertIn('candidate_prediction_at_0_5', predictions.columns)

    def test_saved_v5_test_evaluation_records_artifacts_and_blocks_reuse(self):
        experiments_root = ROOT / 'data' / 'experiments'
        experiments_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=experiments_root) as temp_dir:
            workspace = Path(temp_dir)
            source = workspace / 'weather.csv'
            output = workspace / 'run'
            times = pd.to_datetime([
                '2024-12-30T12:00:00Z', '2024-12-31T12:00:00Z',
                '2025-01-01T12:00:00Z', '2025-12-31T21:00:00Z',
                '2026-01-01T03:00:00Z', '2026-01-01T04:00:00Z',
            ], utc=True)
            frame = pd.DataFrame({
                'time': times,
                'target_time': times + pd.Timedelta(hours=1),
                'temperature_2m': [18, 20, 19, 22, 21, 23],
                'relative_humidity_2m': [50, 70, 60, 80, 55, 85],
                'pressure_msl': [1012, 1010, 1011, 1008, 1013, 1007],
                'cloud_cover': [10, 80, 30, 90, 20, 95],
                TARGET: [0, 1, 0, 1, 0, 1],
            })
            frame.to_csv(source, index=False)
            loaded = load_table(source)
            train, _, test, _ = split_data(loaded)
            model = DummyClassifier(strategy='prior').fit(train[V5_FEATURES], train[TARGET])
            output.mkdir()
            model_path = output / 'frozen_candidate.joblib'
            joblib.dump(model, model_path)
            manifest = {
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'features': list(V5_FEATURES),
                'model_sha256': {
                    model_path.name: hashlib.sha256(model_path.read_bytes()).hexdigest(),
                },
            }
            (output / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            (output / 'experiment_summary.json').write_text('{}', encoding='utf-8')

            v5_evaluate_saved_models_test(source, output)

            recorded = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
            metrics = json.loads((output / 'metrics_test.json').read_text(encoding='utf-8'))
            predictions = pd.read_csv(output / 'predictions_test.csv')
            self.assertEqual(recorded['test_rows'], len(test))
            self.assertTrue(recorded['test_evaluated'])
            self.assertFalse(recorded['test_used_for_selection'])
            self.assertFalse(recorded['independent_blind_test'])
            self.assertEqual(metrics['frozen_candidate']['test_rows'], len(test))
            self.assertEqual(len(predictions), len(test))
            with self.assertRaisesRegex(ValueError, 'já foi avaliado'):
                v5_evaluate_saved_models_test(source, output)


if __name__ == '__main__':
    unittest.main()
