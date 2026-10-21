"""Configuração local: ambiente do processo tem precedência sobre .env."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def settings():
    values = {}
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            if not sep:
                raise ValueError('Linha .env inválida; usar CHAVE=valor')
            values[key.strip()] = value.strip().strip('\"\'')
    values.update(os.environ)
    mode = values.get('DATASET_MODE', 'sample')
    if mode not in ('sample', 'full'):
        raise ValueError('DATASET_MODE deve ser sample ou full')
    def path(key, default):
        value = Path(values.get(key, default)).expanduser()
        return value if value.is_absolute() else ROOT/value
    return dict(mode=mode, sample=path('SAMPLE_PATH','data/sample/sample.npz'),
                full=path('FULL_DATASET_PATH','data/raw/dataset_goes.zip'),
                csv=path('WEATHER_CSV_PATH','data/raw/dataset_weather.csv'),
                readme=path('DATASET_README_PATH','data/raw/README.md'),
                member=values.get('GOES_MEMBER','').strip())
