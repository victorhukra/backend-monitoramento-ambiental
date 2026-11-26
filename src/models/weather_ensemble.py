"""Adaptador de inferência do ensemble meteorológico calibrado."""

import numpy as np
import pandas as pd

from config import WEATHER_TIMEZONE

MODEL_VERSION = 'weather-v6-simple-mean-isotonic-v1'
MODEL_NAMES = ('original', 'balanced', 'balanced_subsample')
FEATURES = (
    'temperature_2m', 'relative_humidity_2m', 'pressure_msl', 'cloud_cover',
    'temp_humidity', 'pressure_diff', 'hour_of_day',
)
WEIGHTS = {'original': 1 / 3, 'balanced': 1 / 3, 'balanced_subsample': 1 / 3}
RAW_FIELDS = (
    'temperature_2m', 'relative_humidity_2m', 'pressure_msl',
    'cloud_cover', 'pressure_msl_previous_hour',
)


class SimpleMeanCalibratedEnsemble:
    """Combina três Random Forests calibrados isotonicamente por média simples."""

    RAW_FIELDS = RAW_FIELDS

    def __init__(self, models, calibrators, threshold=0.5, model_version=MODEL_VERSION):
        if set(models) != set(MODEL_NAMES) or set(calibrators) != set(MODEL_NAMES):
            raise ValueError('O bundle deve conter os três modelos e seus calibradores.')
        self.models = models
        self.calibrators = calibrators
        self.threshold = float(threshold)
        self.model_version = str(model_version)
        if not 0 <= self.threshold <= 1:
            raise ValueError('O limiar deve estar entre 0 e 1.')

    @staticmethod
    def prepare_features(weather, reference_time):
        """Calcula as 7 features a partir das medições em T, pressão em T-1h e horário."""
        missing = [f for f in RAW_FIELDS if f not in weather]
        extra = [f for f in weather if f not in RAW_FIELDS]
        if missing or extra:
            raise ValueError(f'Entradas inválidas; ausentes={missing}, extras={extra}.')

        values = {f: float(weather[f]) for f in RAW_FIELDS}
        if not np.isfinite(list(values.values())).all():
            raise ValueError('As entradas meteorológicas devem ser finitas.')

        timestamp = pd.Timestamp(reference_time)
        if timestamp.tzinfo is None:
            raise ValueError('reference_time precisa conter fuso horário.')

        local_time = timestamp.tz_convert(WEATHER_TIMEZONE)
        row = {
            'temperature_2m': values['temperature_2m'],
            'relative_humidity_2m': values['relative_humidity_2m'],
            'pressure_msl': values['pressure_msl'],
            'cloud_cover': values['cloud_cover'],
            'temp_humidity': values['temperature_2m'] * values['relative_humidity_2m'],
            'pressure_diff': values['pressure_msl'] - values['pressure_msl_previous_hour'],
            'hour_of_day': local_time.hour,
        }
        return pd.DataFrame([[row[name] for name in FEATURES]], columns=FEATURES)

    def predict_one(self, weather, reference_time):
        """Executa os 3 modelos, aplica calibração isotônica e combina pela média simples."""
        features = self.prepare_features(weather, reference_time)
        calibrated = {}

        for name in MODEL_NAMES:
            model = self.models[name]
            classes = list(model.classes_)
            if 1 not in classes:
                raise ValueError(f'O modelo {name} não contém a classe positiva 1.')

            raw_prob = float(model.predict_proba(features)[0, classes.index(1)])
            cal_prob = float(self.calibrators[name].predict([raw_prob])[0])
            calibrated[name] = float(np.clip(cal_prob, 0.0, 1.0))

        probability = float(sum(WEIGHTS[name] * calibrated[name] for name in MODEL_NAMES))
        return {
            'rain_probability': probability,
            'rain_predicted': probability >= self.threshold,
            'decision_threshold': self.threshold,
            'model_version': self.model_version,
        }
