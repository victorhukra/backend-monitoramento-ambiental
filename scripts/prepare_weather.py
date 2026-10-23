"""MVP histórico: quatro entradas em T e ocorrência de chuva em (T,T+1h].

Hipótese de trabalho: rain(u) acumula a hora anterior. Não é prova da origem.
Não treina, não divide períodos e não usa GOES nesta primeira versão.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, WEATHER_FEATURES, WEATHER_TIMEZONE, settings


def prepare_table(source):
    """Retorna tabela elegível, exclusões e contagens; não altera o DataFrame original."""
    required = ['time', *WEATHER_FEATURES, 'rain']
    missing = set(required) - set(source.columns)
    if missing:
        raise ValueError(f'Colunas ausentes: {sorted(missing)}')
    if source.empty:
        raise ValueError('CSV vazio')
    frame = source[required].copy()

    # O CSV original não tem offset. Localizamos em São Paulo, sem subtrair horas à mão.
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

    # Texto inválido vira NaN apenas na cópia para ser explicitamente rejeitado abaixo.
    # Não há imputação, normalização ou remoção de extremos estatísticos.
    for column in [*WEATHER_FEATURES, 'rain']:
        frame[column] = pd.to_numeric(frame[column], errors='coerce')

    frame['target_time'] = frame['time'] + pd.Timedelta(hours=1)
    future = frame[['time', 'rain']].rename(columns={'time': 'target_time', 'rain': 'future_rain'})
    # Merge por horário exato: uma lacuna não pode virar "a próxima linha".
    joined = frame.merge(future, on='target_time', how='left', validate='one_to_one', indicator=True)
    features_ok = np.isfinite(joined[list(WEATHER_FEATURES)]).all(axis=1)
    domain_ok = (joined.relative_humidity_2m.between(0, 100)
                 & joined.cloud_cover.between(0, 100) & joined.pressure_msl.gt(0))
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
        lambda row: '|'.join(row.index[row]), axis=1)

    # Somente as quatro variáveis em T são entradas. Nem rain(T+1), nem rain(T),
    # nem weather_code entram na tabela de características deste MVP.
    table = joined.loc[eligible, ['time', *WEATHER_FEATURES, 'target_time']].copy()
    table['rain_next_hour'] = joined.loc[eligible, 'future_rain'].gt(0).astype('int8')
    table = table.reset_index(drop=True)
    counts = table.rain_next_hour.value_counts()
    summary = {
        'source_rows': len(source), 'training_rows': len(table), 'excluded_rows': len(rejected),
        'exclusion_counts_may_overlap': {k: int(v) for k,v in reasons.sum().items()},
        'no_rain': int(counts.get(0, 0)), 'rain': int(counts.get(1, 0)),
        'missing_hours': len(pd.date_range(frame.time.min(), frame.time.max(), freq='h').difference(pd.DatetimeIndex(frame.time))),
        'features': list(WEATHER_FEATURES), 'timezone': WEATHER_TIMEZONE,
        'horizon_hours': 1, 'target_rule': 'rain at exact T+1h > 0 mm',
        'temporal_assumption': 'rain(u) represents (u-1h,u]; not confirmed for original export',
        'mode': 'historical_experimental', 'split_created': False,
    }
    return table, rejected.reset_index(drop=True), summary


def run(csv_path, output, plot=False):
    """Grava apenas derivados novos em data/processed; não sobrescreve arquivos."""
    csv_path, output = Path(csv_path).resolve(), Path(output).resolve()
    if output.suffix != '.csv' or not output.is_relative_to((ROOT/'data/processed').resolve()):
        raise ValueError('Saída deve ser .csv dentro de data/processed (ignorada pelo Git)')
    outputs = [output, output.with_suffix('.json'), output.with_name(output.stem+'_excluded.csv'),
               output.with_name(output.stem+'_preview.csv')]
    if plot:
        outputs.append(output.with_suffix('.png'))
    if csv_path in outputs or any(p.exists() for p in outputs):
        raise ValueError('Destino existente ou igual à fonte; escolha outro WEATHER_TRAINING_PATH/--output')
    # Carregar o gráfico antes de escrever: dependência ausente não deixa saída parcial.
    if plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    before = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    source = pd.read_csv(csv_path)
    table, rejected, summary = prepare_table(source)
    if table.empty:
        raise ValueError('Nenhuma linha elegível; conferir fonte e critérios')
    after = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if before != after:
        raise ValueError('Fonte mudou durante a leitura')
    summary.update(source=str(csv_path), source_sha256=before, source_unchanged=True,
                   created_at_utc=datetime.now(timezone.utc).isoformat(),
                   python=sys.version, pandas=pd.__version__, numpy=np.__version__)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(outputs[0], index=False)
    outputs[1].write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    rejected.to_csv(outputs[2], index=False)
    table.head(10).to_csv(outputs[3], index=False)
    if plot:
        fig, ax = plt.subplots(figsize=(6, 4))
        bars = ax.bar(['Sem chuva (0)', 'Com chuva (1)'], [summary['no_rain'], summary['rain']], color=['#456990','#20816a'])
        ax.bar_label(bars, padding=3)
        ax.set(title='Alvo experimental: chuva na próxima hora', ylabel='Quantidade de registros', xlabel='Classe do alvo')
        ax.set_ylim(0, max(summary['no_rain'], summary['rain'])*1.15)
        fig.tight_layout(); fig.savefig(output.with_suffix('.png'), dpi=150); plt.close(fig)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=cfg['csv'])
    parser.add_argument('--output', type=Path, default=cfg['training'])
    parser.add_argument('--plot', action='store_true', help='Gerar gráfico de classes com matplotlib')
    args = parser.parse_args()
    run(args.csv, args.output, args.plot)
