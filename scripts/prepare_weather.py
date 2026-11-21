"""Preparação do conjunto de dados meteorológicos para treinamento.

Lê as medições meteorológicas brutas horárias, valida consistência temporal
e física das variáveis, associa o alvo binário (chuva acumulada na hora seguinte > 0)
e gera o dataset tabular final elegível (`weather_training.csv`), registrando
as exclusões e metadados de proveniência.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

# Inclusão da raiz do projeto para imports locais
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, WEATHER_FEATURES, WEATHER_TIMEZONE, settings


def prepare_table(source: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Valida, alinha temporalmente e filtra medições elegíveis para treinamento.
    
    Args:
        source: DataFrame bruto contendo 'time', as 4 features meteorológicas e 'rain'.
        
    Returns:
        Tupla contendo:
        1. table: DataFrame com registros válidos e alvo `rain_next_hour`.
        2. rejected: DataFrame com os registros excluídos e seus motivos.
        3. summary: Dicionário com estatísticas descritivas do processamento.
    """
    required = ['time', *WEATHER_FEATURES, 'rain']
    missing = set(required) - set(source.columns)
    if missing:
        raise ValueError(f'Colunas ausentes: {sorted(missing)}')
    if source.empty:
        raise ValueError('CSV vazio')

    frame = source[required].copy()

    # Validação e localização temporal em São Paulo
    times = pd.to_datetime(frame['time'], format='ISO8601', errors='raise')
    if times.isna().any():
        raise ValueError('Timestamp ausente')

    if times.dt.tz is None:
        times = times.dt.tz_localize(WEATHER_TIMEZONE, ambiguous='raise', nonexistent='raise')
    else:
        times = times.dt.tz_convert(WEATHER_TIMEZONE)

    if (times != times.dt.floor('h')).any():
        raise ValueError('Esperados registros em hora cheia')
    if times.duplicated().any():
        raise ValueError('Timestamps duplicados: resolver a ambiguidade na origem')

    frame['time'] = times
    frame = frame.sort_values('time').reset_index(drop=True)

    # Conversão explícita para numérico (valores textuais inválidos viram NaN)
    for column in [*WEATHER_FEATURES, 'rain']:
        frame[column] = pd.to_numeric(frame[column], errors='coerce')

    # Definição do alvo: observação exatamente em T+1h
    frame['target_time'] = frame['time'] + pd.Timedelta(hours=1)
    future = frame[['time', 'rain']].rename(
        columns={'time': 'target_time', 'rain': 'future_rain'}
    )

    # Junção exata por horário (evita pular lacunas)
    joined = frame.merge(
        future, on='target_time', how='left', validate='one_to_one', indicator=True
    )

    # Verificação de validade de domínio físico
    features_ok = np.isfinite(joined[list(WEATHER_FEATURES)]).all(axis=1)
    domain_ok = (
        joined.relative_humidity_2m.between(0, 100)
        & joined.cloud_cover.between(0, 100)
        & joined.pressure_msl.gt(0)
    )
    future_exists = joined['_merge'].eq('both')
    future_ok = np.isfinite(joined.future_rain) & joined.future_rain.ge(0)

    reasons = pd.DataFrame({
        'invalid_or_missing_features': ~features_ok,
        'features_outside_domain': features_ok & ~domain_ok,
        'missing_future_timestamp': ~future_exists,
        'invalid_or_missing_future_rain': future_exists & ~future_ok,
    })

    eligible = ~reasons.any(axis=1)
    rejected = joined.loc[~eligible, ['time', 'target_time']].copy()
    rejected['reason'] = reasons.loc[~eligible].apply(
        lambda row: '|'.join(row.index[row]), axis=1
    )

    # Tabela final elegível
    table = joined.loc[eligible, ['time', *WEATHER_FEATURES, 'target_time']].copy()
    table['rain_next_hour'] = joined.loc[eligible, 'future_rain'].gt(0).astype('int8')
    table = table.reset_index(drop=True)

    counts = table.rain_next_hour.value_counts()
    all_expected_hours = pd.date_range(frame.time.min(), frame.time.max(), freq='h')
    missing_hours_count = len(all_expected_hours.difference(pd.DatetimeIndex(frame.time)))

    summary = {
        'source_rows': len(source),
        'training_rows': len(table),
        'excluded_rows': len(rejected),
        'exclusion_counts_may_overlap': {k: int(v) for k, v in reasons.sum().items()},
        'no_rain': int(counts.get(0, 0)),
        'rain': int(counts.get(1, 0)),
        'missing_hours': missing_hours_count,
        'features': list(WEATHER_FEATURES),
        'timezone': WEATHER_TIMEZONE,
        'horizon_hours': 1,
        'target_rule': 'rain at exact T+1h > 0 mm',
        'temporal_assumption': 'rain(u) represents (u-1h,u]; not confirmed for original export',
        'mode': 'historical_experimental',
        'split_created': False,
    }

    return table, rejected.reset_index(drop=True), summary


def run(csv_path: Path, output: Path, plot: bool = False) -> None:
    """Processa o CSV meteorológico e grava a tabela de treinamento em data/processed."""
    csv_file = Path(csv_path).resolve()
    output_file = Path(output).resolve()
    processed_dir = (ROOT / 'data' / 'processed').resolve()

    if output_file.suffix != '.csv' or not output_file.is_relative_to(processed_dir):
        raise ValueError('Saída deve ser .csv dentro de data/processed (ignorada pelo Git)')

    outputs = [
        output_file,
        output_file.with_suffix('.json'),
        output_file.with_name(output_file.stem + '_excluded.csv'),
        output_file.with_name(output_file.stem + '_preview.csv'),
    ]
    if plot:
        outputs.append(output_file.with_suffix('.png'))

    if csv_file in outputs or any(p.exists() for p in outputs):
        raise ValueError('Destino existente ou igual à fonte; escolha outro caminho de saída.')

    if plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

    before_hash = hashlib.sha256(csv_file.read_bytes()).hexdigest()
    source_df = pd.read_csv(csv_file)
    table, rejected, summary = prepare_table(source_df)

    if table.empty:
        raise ValueError('Nenhuma linha elegível; conferir fonte e critérios.')

    after_hash = hashlib.sha256(csv_file.read_bytes()).hexdigest()
    if before_hash != after_hash:
        raise ValueError('Fonte mudou durante a leitura.')

    summary.update({
        'source': str(csv_file),
        'source_sha256': before_hash,
        'source_unchanged': True,
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'pandas': pd.__version__,
        'numpy': np.__version__,
    })

    output_file.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(outputs[0], index=False)
    outputs[1].write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    rejected.to_csv(outputs[2], index=False)
    table.head(10).to_csv(outputs[3], index=False)

    if plot:
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(
            ['Sem chuva (0)', 'Com chuva (1)'],
            [summary['no_rain'], summary['rain']],
            color=['#456990', '#20816a'],
        )
        ax.bar_label(bars, padding=3)
        ax.set(
            title='Alvo experimental: chuva na próxima hora',
            ylabel='Quantidade de registros',
            xlabel='Classe do alvo',
        )
        ax.set_ylim(0, max(summary['no_rain'], summary['rain']) * 1.15)
        fig.tight_layout()
        fig.savefig(output_file.with_suffix('.png'), dpi=150)
        plt.close(fig)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=cfg['csv'])
    parser.add_argument('--output', type=Path, default=cfg['training'])
    parser.add_argument('--plot', action='store_true', help='Gerar gráfico de classes com matplotlib')
    args = parser.parse_args()
    run(args.csv, args.output, args.plot)
