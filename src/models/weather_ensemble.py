"""Módulo do ensemble meteorológico calibrado.

Contém as definições de features, pesos e a classe adaptadora de inferência
(SimpleMeanCalibratedEnsemble) utilizada para combinar os três Random Forests
(original, balanced e balanced_subsample) com calibração isotônica.
"""

from typing import Any, Dict, Mapping
import numpy as np
import pandas as pd

from config import WEATHER_TIMEZONE

# Versão do artefato do modelo
MODEL_VERSION = 'weather-v6-simple-mean-isotonic-v1'

# Identificadores das três famílias de Random Forest
MODEL_NAMES = ('original', 'balanced', 'balanced_subsample')

# As 7 features finais esperadas pelos modelos (4 originais + 3 derivadas)
FEATURES = (
    'temperature_2m',
    'relative_humidity_2m',
    'pressure_msl',
    'cloud_cover',
    'temp_humidity',
    'pressure_diff',
    'hour_of_day',
)

# Pesos iguais para a média simples das probabilidades calibradas
WEIGHTS = {
    'original': 1.0 / 3.0,
    'balanced': 1.0 / 3.0,
    'balanced_subsample': 1.0 / 3.0,
}

# Campos meteorológicos brutos obrigatórios para a inferência
RAW_FIELDS = (
    'temperature_2m',
    'relative_humidity_2m',
    'pressure_msl',
    'cloud_cover',
    'pressure_msl_previous_hour',
)


class SimpleMeanCalibratedEnsemble:
    """Adaptador de inferência que combina previsões probabilísticas calibradas.
    
    Executa:
    1. Engenharia de atributos (7 features a partir das medições brutas e horário).
    2. Estimativa de probabilidade bruta em cada um dos 3 modelos Random Forest.
    3. Calibração isotônica das probabilidades individuais.
    4. Média ponderada (pesos iguais: 1/3 cada) das probabilidades calibradas.
    5. Decisão binária final baseada em limiar (threshold).
    """

    RAW_FIELDS = RAW_FIELDS

    def __init__(
        self,
        models: Mapping[str, Any],
        calibrators: Mapping[str, Any],
        threshold: float = 0.5,
        model_version: str = MODEL_VERSION,
    ) -> None:
        if set(models) != set(MODEL_NAMES) or set(calibrators) != set(MODEL_NAMES):
            raise ValueError('O bundle deve conter os três modelos e seus calibradores.')

        self.models = models
        self.calibrators = calibrators
        self.threshold = float(threshold)
        self.model_version = str(model_version)

        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError('O limiar deve estar entre 0 e 1.')

    @staticmethod
    def prepare_features(weather: Mapping[str, Any], reference_time: Any) -> pd.DataFrame:
        """Transforma medições brutas e horário de referência nas 7 features do modelo.
        
        Args:
            weather: Dicionário contendo RAW_FIELDS (valores em T e pressão em T-1h).
            reference_time: Timestamp ISO com fuso horário da observação em T.
            
        Returns:
            DataFrame com 1 linha e as 7 colunas esperadas em FEATURES.
        """
        missing = [field for field in RAW_FIELDS if field not in weather]
        extra = [field for field in weather if field not in RAW_FIELDS]
        if missing or extra:
            raise ValueError(f'Entradas inválidas; ausentes={missing}, extras={extra}.')

        values = {field: float(weather[field]) for field in RAW_FIELDS}
        if not np.isfinite(list(values.values())).all():
            raise ValueError('As entradas meteorológicas devem ser finitas.')

        timestamp = pd.Timestamp(reference_time)
        if timestamp.tzinfo is None:
            raise ValueError('reference_time precisa conter fuso horário.')

        local_time = timestamp.tz_convert(WEATHER_TIMEZONE)

        # Cálculo das features derivadas:
        # - temp_humidity: interação entre temperatura e umidade relativa
        # - pressure_diff: tendência barométrica (pressão em T menos pressão em T-1h)
        # - hour_of_day: hora local do dia (0 a 23)
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

    def predict_one(self, weather: Mapping[str, Any], reference_time: Any) -> Dict[str, Any]:
        """Realiza a previsão de chuva para a próxima hora a partir dos dados em T.
        
        Args:
            weather: Medições meteorológicas nos campos RAW_FIELDS.
            reference_time: Horário da medição.
            
        Returns:
            Dicionário com probabilidade de chuva, previsão booleana, limiar e versão.
        """
        features = self.prepare_features(weather, reference_time)
        calibrated_probs: Dict[str, float] = {}

        for name in MODEL_NAMES:
            model = self.models[name]
            classes = list(model.classes_)
            if 1 not in classes:
                raise ValueError(f'O modelo {name} não contém a classe positiva 1.')

            class_1_idx = classes.index(1)
            raw_prob = float(model.predict_proba(features)[0, class_1_idx])

            # Aplica calibrador isotônico ajustado para a família
            calibrated_val = float(self.calibrators[name].predict([raw_prob])[0])
            calibrated_probs[name] = float(np.clip(calibrated_val, 0.0, 1.0))

        # Combinação linear com pesos (1/3 para cada modelo)
        final_probability = float(sum(WEIGHTS[name] * calibrated_probs[name] for name in MODEL_NAMES))

        return {
            'rain_probability': final_probability,
            'rain_predicted': final_probability >= self.threshold,
            'decision_threshold': self.threshold,
            'model_version': self.model_version,
        }
