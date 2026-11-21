"""Configuração central do projeto de monitoramento ambiental.

Define diretórios, constantes meteorológicas e leitura de variáveis de ambiente.
O ambiente do processo (os.environ) possui precedência sobre o arquivo .env local.
"""

from pathlib import Path
import os
from typing import Any, Dict

# Diretório raiz do projeto
ROOT = Path(__file__).resolve().parent

# Quatro variáveis meteorológicas brutas de entrada
WEATHER_FEATURES = (
    'temperature_2m',
    'relative_humidity_2m',
    'pressure_msl',
    'cloud_cover',
)

# Fuso horário padrão das observações locais
WEATHER_TIMEZONE = 'America/Sao_Paulo'


def settings() -> Dict[str, Any]:
    """Carrega as configurações a partir do arquivo .env e do ambiente do sistema.
    
    Returns:
        Dicionário com caminhos canônicos e parâmetros de execução.
    """
    values: Dict[str, str] = {}
    env_file = ROOT / '.env'

    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            if not sep:
                raise ValueError('Linha .env inválida; usar CHAVE=valor')
            values[key.strip()] = value.strip().strip('\"\'')

    # Variáveis do sistema têm precedência sobre o .env
    values.update(os.environ)

    mode = values.get('DATASET_MODE', 'sample')
    if mode not in ('sample', 'full'):
        raise ValueError('DATASET_MODE deve ser sample ou full')

    def resolve_path(key: str, default: str) -> Path:
        value = Path(values.get(key, default)).expanduser()
        return value if value.is_absolute() else ROOT / value

    return {
        'mode': mode,
        'sample': resolve_path('SAMPLE_PATH', 'data/sample/sample.npz'),
        'full': resolve_path('FULL_DATASET_PATH', 'data/raw/dataset_goes.zip'),
        'csv': resolve_path('WEATHER_CSV_PATH', 'data/raw/dataset_weather.csv'),
        'training': resolve_path('WEATHER_TRAINING_PATH', 'data/processed/weather_training.csv'),
        'readme': resolve_path('DATASET_README_PATH', 'data/raw/README.md'),
        'member': values.get('GOES_MEMBER', '').strip(),
    }
