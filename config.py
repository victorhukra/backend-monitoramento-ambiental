"""Configuração central do projeto (o ambiente do sistema tem precedência sobre o .env)."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEATHER_FEATURES = ('temperature_2m', 'relative_humidity_2m', 'pressure_msl', 'cloud_cover')
WEATHER_TIMEZONE = 'America/Sao_Paulo'


def settings():
    """Carrega caminhos de entrada e saída a partir do .env e das variáveis de ambiente."""
    values = {}
    env_file = ROOT / '.env'

    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            if not sep:
                raise ValueError('Linha .env inválida; usar CHAVE=valor')
            values[key.strip()] = value.strip().strip('"\'')

    values.update(os.environ)

    def resolve_path(key, default):
        value = Path(values.get(key, default)).expanduser()
        return value if value.is_absolute() else ROOT / value

    return {
        'csv': resolve_path('WEATHER_CSV_PATH', 'data/raw/dataset_weather.csv'),
        'training': resolve_path('WEATHER_TRAINING_PATH', 'data/processed/weather_training.csv'),
    }
