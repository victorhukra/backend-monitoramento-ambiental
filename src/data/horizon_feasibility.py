"""Contagens estruturais condicionais; não constrói rótulos nem associa novas imagens."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit import fingerprint
from eda import name_time

ROOT = Path(__file__).resolve().parents[2]


def complete_windows(index, usable, horizon):
    """Hipótese de hora anterior: exige cada timestamp exato t+1,...,t+H.

    Somente disponibilidade estrutural, sem calcular evento/target.
    """
    if index.has_duplicates or index.hasnans or index.tz is None:
        raise ValueError('Índice deve ser único, sem NaT e com fuso explícito')
    if horizon < 1 or int(horizon) != horizon:
        raise ValueError('Horizonte deve ser inteiro positivo')
    present = pd.Series(np.asarray(usable, dtype=bool), index=index)
    result = np.ones(len(index), dtype=bool)
    for step in range(1, horizon + 1):
        result &= present.reindex(index + pd.Timedelta(hours=step), fill_value=False).to_numpy()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--zip', type=Path, required=True)
    args = parser.parse_args()
    eda = ROOT/'reports/eda/goes_sample_details.json'
    pilot = ROOT/'reports/pilot/image_diagnostics.json'
    sources = [args.csv,args.zip,eda,pilot]
    before = [fingerprint(p) for p in sources]
    df = pd.read_csv(args.csv)
    local = pd.DatetimeIndex(pd.to_datetime(df.time, format='ISO8601')).tz_localize('America/Sao_Paulo', ambiguous='raise', nonexistent='raise')
    utc = local.tz_convert('UTC')
    numeric = df.select_dtypes(include='number')
    weather_complete = np.isfinite(numeric.to_numpy()).all(axis=1)
    rain_usable = np.isfinite(df[['rain','precipitation']]).all(axis=1).to_numpy() & (df[['rain','precipitation']]>=0).all(axis=1).to_numpy()
    with zipfile.ZipFile(args.zip) as archive:
        names = [x.filename for x in archive.infolist() if not x.is_dir()]
    if len(names) != len(set(names)):
        raise ValueError('Nomes duplicados no ZIP exigem investigação')
    members = set(names)
    links = df.image_link
    linked = links.notna().to_numpy()
    exists = links.isin(members).to_numpy()
    cache = {}
    for link in links.dropna().unique():
        cache[link] = [name_time(link,k) for k in ('s','e','c')]
    times = [pd.DatetimeIndex([cache[x][j] if pd.notna(x) else pd.NaT for x in links]) for j in range(3)]
    start,end,creation = times
    parseable = ~start.isna() & ~end.isna() & ~creation.isna()
    coherent = parseable & (start<=end) & (end<=creation)
    nominal = exists & coherent & (end<=utc) & (creation<=utc)
    known = {x['image_link']:x['valid_pixels'] for x in json.loads(eda.read_text(encoding='utf-8')) if 'valid_pixels' in x}
    known.update({x['image_link']:x['diagnostics']['valid_pixels'] for x in json.loads(pilot.read_text(encoding='utf-8')) if 'valid_pixels' in x.get('diagnostics',{})})
    invalid = links.map(known).eq(0).to_numpy()
    inspected = links.isin(known).to_numpy()
    rows=[]
    for h in (1,3,6,7):
        complete = complete_windows(utc,np.ones(len(df),dtype=bool),h)
        amounts = complete_windows(utc,rain_usable,h)
        potential = amounts & weather_complete
        rows.append(dict(horizon_hours=h,complete_timestamp_windows=int(complete.sum()),
            complete_amount_windows_conditional=int(amounts.sum()),
            with_finite_meteorology_at_t_conditional=int(potential.sum()),
            without_original_link=int((potential & ~linked).sum()),
            with_existing_original_link=int((potential & exists).sum()),
            original_link_nominal_end_creation_le_t=int((potential & nominal).sum()),
            nominal_and_known_all_invalid=int((potential & nominal & invalid).sum()),
            nominal_pixel_quality_unexamined=int((potential & nominal & ~inspected).sum()),
            known_all_invalid_original_links=int((potential & invalid).sum()),
            targets_temporally_confirmed=None,operational_meteorology_confirmed=None,
            operational_goes_confirmed=None,final_comparable_examples=None))
    after = [fingerprint(p) for p in sources]
    if before != after: raise RuntimeError('Fontes alteradas durante a leitura')
    output=ROOT/'reports/horizons'; output.mkdir(parents=True,exist_ok=True)
    result=dict(date='2026-10-15',timezone='America/Sao_Paulo',hypothesis='Registro u representa (u-1h,u]; não confirmado na exportação',
        sources_before=before,sources_after=after,sources_unchanged=True,
        python=sys.version,numpy=np.__version__,pandas=pd.__version__,
        rows=len(df),first_local=str(local.min()),last_local=str(local.max()),
        sorted=bool(local.is_monotonic_increasing),missing_hours=len(pd.date_range(utc.min(),utc.max(),freq='h').difference(utc)),
        meteorology_finite_rows=int(weather_complete.sum()),meteorology_columns=list(numeric.columns),
        invalid_rain_or_precipitation_rows=int((~rain_usable).sum()),
        equal_rain_precipitation=bool(df.rain.equals(df.precipitation)),
        smallest_positive_rain=float(df.loc[df.rain>0,'rain'].min()),
        smallest_positive_precipitation=float(df.loc[df.precipitation>0,'precipitation'].min()),
        zip_index_members=len(names),missing_link_members=int((linked & ~exists).sum()),
        unparsable_link_rows=int((linked & ~parseable).sum()),incoherent_link_rows=int((parseable & ~coherent).sum()),
        nominal_start_after_t=int((parseable & (start>utc)).sum()),
        nominal_end_after_t=int((parseable & (end>utc)).sum()),
        nominal_creation_after_t=int((parseable & (creation>utc)).sum()),
        horizons=rows)
    (output/'feasibility_counts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    pd.DataFrame(rows).to_csv(output/'horizon_comparison.csv',index=False,na_rep='NA')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
