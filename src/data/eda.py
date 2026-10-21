"""EDA descritiva: fontes somente leitura, nenhuma feature/target de treinamento."""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import re
import sys
import zipfile
import numpy as np
import pandas as pd
from audit import audit, fingerprint, scalar, stats

SEED = 42
ROOT = Path(__file__).resolve().parents[2]
UNITS = dict(temperature_2m="°C", relative_humidity_2m="%", dew_point_2m="°C",
             apparent_temperature="°C", cloud_cover="%", pressure_msl="hPa",
             surface_pressure="hPa", wind_speed_10m="m/s", wind_direction_10m="graus",
             wind_gusts_10m="m/s", shortwave_radiation="W/m²", direct_radiation="W/m²",
             diffuse_radiation="W/m²", direct_normal_irradiance="W/m²", is_day="0/1",
             sunshine_duration="s", soil_moisture_0_to_7cm="m³/m³", rain="mm",
             precipitation="mm", weather_code="código")


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def name_time(name, field="s"):
    """Convenção NOAA descrita no README: YYYY + dia juliano + HHMMSS + décimo."""
    match = re.search(r"_" + field + r"(\d{14})(?:_|\.)", name)
    if not match:
        return pd.NaT
    digits = match.group(1)
    return pd.Timestamp(datetime.strptime(digits[:13], "%Y%j%H%M%S").replace(tzinfo=timezone.utc)) + pd.Timedelta(milliseconds=int(digits[13])*100)


def spells(time, active, values=None):
    """Blocos consecutivos verdadeiros; uma lacuna temporal sempre quebra o bloco."""
    frame = pd.DataFrame({"time": time, "active": active}).reset_index(drop=True)
    if values is not None:
        frame["amount"] = np.asarray(values)
    boundary = frame.active.ne(frame.active.shift()) | frame.time.diff().ne(pd.Timedelta(hours=1))
    frame["group"] = boundary.cumsum()
    rows = []
    for _, group in frame[frame.active].groupby("group"):
        row = {"start": str(group.time.iloc[0]), "end": str(group.time.iloc[-1]), "hours": len(group),
               "touches_start": group.index[0] == 0, "touches_end": group.index[-1] == len(frame)-1}
        if values is not None:
            row.update(total_mm=float(group.amount.sum()), max_hour_mm=float(group.amount.max()))
        rows.append(row)
    return pd.DataFrame(rows)


def physical_checks(df):
    checks, examples = [], []
    def add(name, mask, category, reason, cols):
        mask = mask.fillna(False)
        count = int(mask.sum())
        checks.append(dict(check=name, count=count, category=category if count else "D", reason=reason))
        for idx in df.index[mask][:10]:
            examples.append(dict(check=name, row_index=int(idx), time=df.at[idx,"time"],
                                 values=json.dumps(df.loc[idx, cols].to_dict(), ensure_ascii=False)))
    for col in ["relative_humidity_2m", "cloud_cover"]:
        add(col+"_outside_0_100", ~df[col].between(0,100), "A", "Fora do domínio percentual declarado.", [col])
    for col in ["rain", "precipitation", "wind_speed_10m", "wind_gusts_10m", "shortwave_radiation", "direct_radiation", "diffuse_radiation", "direct_normal_irradiance"]:
        add(col+"_negative", df[col]<0, "A", "Magnitude negativa incompatível com a variável declarada.", [col])
    add("sunshine_outside_hour", ~df.sunshine_duration.between(0,3600), "A", "Segundos de insolação fora de uma hora.", ["sunshine_duration"])
    add("soil_moisture_outside_0_1", ~df.soil_moisture_0_to_7cm.between(0,1), "A", "Fração volumétrica fora de [0,1].", ["soil_moisture_0_to_7cm"])
    add("direction_outside_circle", ~df.wind_direction_10m.between(0,360), "A", "Direção fora do círculo em graus.", ["wind_direction_10m"])
    add("is_day_not_binary", ~df.is_day.isin([0,1]), "A", "Indicador fora de 0/1.", ["is_day"])
    add("dew_above_air", df.dew_point_2m > df.temperature_2m + .2, "B", "Ponto de orvalho acima da temperatura; tolerância exploratória 0,2 °C para arredondamento, sem correção.", ["dew_point_2m","temperature_2m"])
    add("rain_above_total", df.rain > df.precipitation + 1e-8, "B", "Chuva maior que precipitação total; verificar definição/fonte.", ["rain","precipitation"])
    add("radiation_components", abs(df.shortwave_radiation-df.direct_radiation-df.diffuse_radiation)>2, "B", "Diferença global - direta - difusa >2 W/m²; tolerância exploratória para arredondamento.", ["shortwave_radiation","direct_radiation","diffuse_radiation"])
    add("radiation_at_night", (df.is_day==0)&(df.shortwave_radiation>0), "B", "Comparar média da hora anterior com is_day instantâneo pode explicar valores no crepúsculo; não é prova de erro.", ["is_day","shortwave_radiation"])
    add("gust_below_wind", df.wind_gusts_10m<df.wind_speed_10m, "B", "Janelas/modelos de rajada e vento podem diferir; confirmar configuração da fonte.", ["wind_gusts_10m","wind_speed_10m"])
    add("pressure_order", df.surface_pressure>=df.pressure_msl, "B", "Ordem inesperada para local elevado; altitude/configuração não verificadas.", ["surface_pressure","pressure_msl"])
    for col in ["temperature_2m","apparent_temperature","wind_speed_10m","wind_gusts_10m","rain","precipitation"]:
        q1,q3 = df[col].quantile([.25,.75]); iqr=q3-q1
        add(col+"_iqr", (df[col]<q1-1.5*iqr)|(df[col]>q3+1.5*iqr), "C", f"Fora de 1,5 IQR ({q1-1.5*iqr:g}, {q3+1.5*iqr:g}); regra descritiva, não física. Com IQR zero, qualquer chuva positiva é sinalizada.", [col])
    return pd.DataFrame(checks), pd.DataFrame(examples)


def csv_analysis(df, output):
    time = pd.to_datetime(df.time, format="ISO8601").dt.tz_localize("America/Sao_Paulo", ambiguous="raise", nonexistent="raise")
    numeric = df.select_dtypes(include="number")
    desc = numeric.describe(percentiles=[.01,.05,.25,.5,.75,.95,.99]).T
    desc["median"] = numeric.median(); desc["unique"] = numeric.nunique(); desc["missing"] = numeric.isna().sum()
    desc["infinite"] = np.isinf(numeric).sum(); desc["unit_readme"] = pd.Series(UNITS)
    desc.to_csv(output/"numeric_summary.csv", index_label="variable")
    base = pd.DataFrame({"time":time,"month":time.dt.strftime("%Y-%m"),"year":time.dt.year,
                         "temperature":df.temperature_2m,"precipitation":df.precipitation,"rain":df.rain,
                         "positive":df.precipitation.gt(0),"has_image":df.image_link.notna(),
                         "satellite_filename":df.image_link.str.extract(r"_(G\d+)_",expand=False).fillna("sem_imagem")})
    monthly = base.groupby("month").agg(rows=("time","size"),temperature_mean=("temperature","mean"),
        precipitation_mm=("precipitation",lambda x:x.sum(min_count=1)),rain_mm=("rain",lambda x:x.sum(min_count=1)),
        positive_hours=("positive","sum"),positive_fraction=("positive","mean"),images=("has_image","sum"),coverage=("has_image","mean"))
    monthly.to_csv(output/"monthly.csv")
    annual = base.groupby("year").agg(rows=("time","size"),temperature_mean=("temperature","mean"),
        precipitation_mm=("precipitation","sum"),positive_fraction=("positive","mean"),images=("has_image","sum"),coverage=("has_image","mean"))
    annual.to_csv(output/"annual.csv")
    # Comparação anual com os mesmos meses, para não comparar 2026 parcial com anos completos.
    base[time.dt.month<=9].groupby("year").agg(rows=("time","size"),temperature_mean=("temperature","mean"),precipitation_mm=("precipitation","sum")).to_csv(output/"annual_jan_sep.csv")
    numeric.assign(year=time.dt.year).groupby("year").describe().to_csv(output/"numeric_by_year.csv")
    seasonal = monthly.assign(calendar_month=pd.to_datetime(monthly.index).month).groupby("calendar_month").agg(
        months_observed=("rows","size"),temperature_mean=("temperature_mean","mean"),precipitation_month_mean_mm=("precipitation_mm","mean"),positive_fraction=("positive_fraction","mean"))
    seasonal.to_csv(output/"seasonality.csv")
    base.assign(hour=time.dt.hour).groupby("hour").agg(temperature_mean=("temperature","mean"),positive_fraction=("positive","mean")).to_csv(output/"hourly_cycle.csv")
    pd.crosstab(base.year,base.satellite_filename).to_csv(output/"coverage_year_satellite_filename.csv")
    categorical = df.groupby("weather_code").agg(rows=("time","size"),rain_min=("rain","min"),rain_max=("rain","max"),rain_mean=("rain","mean"),
        precipitation_mean=("precipitation","mean"),positive_fraction=("precipitation",lambda x:x.gt(0).mean()))
    categorical["fraction"]=categorical.rows/len(df); categorical.to_csv(output/"weather_code.csv")
    df.is_day.value_counts().sort_index().rename_axis("is_day").rename("rows").to_csv(output/"is_day.csv")
    angle=np.deg2rad(df.loc[df.wind_speed_10m>0,"wind_direction_10m"] % 360)
    circular={"noncalm_rows":len(angle),"calm_rows":int(df.wind_speed_10m.eq(0).sum()),
              "mean_direction_degrees":float(np.rad2deg(np.arctan2(np.sin(angle).mean(),np.cos(angle).mean()))%360),
              "mean_resultant_length":float(np.hypot(np.sin(angle).mean(),np.cos(angle).mean()))}
    save_json(output/"wind_circular.json",circular)
    rain_rows=[]
    for col in ["rain","precipitation"]:
        x=df[col]; positive=x[x>0]
        rain_rows.append({"variable":col,"zero":int(x.eq(0).sum()),"positive":len(positive),"negative":int(x.lt(0).sum()),
             "zero_fraction":float(x.eq(0).mean()),"positive_fraction":float(x.gt(0).mean()),"min":float(x.min()),"max":float(x.max()),"unique":int(x.nunique()),
             "positive_mean":float(positive.mean()), **{f"q{q:g}":float(x.quantile(q)) for q in [.5,.9,.95,.99,.999]},
             **{f"positive_q{q:g}":float(positive.quantile(q)) for q in [.25,.5,.75,.95,.99]}})
    rain_summary=pd.DataFrame(rain_rows); rain_summary.to_csv(output/"rain_summary.csv",index=False)
    for col in ["rain","precipitation"]:
        df[col].value_counts().sort_index().rename_axis("mm").rename("rows").to_csv(output/f"{col}_values.csv")
        spells(time,df[col].gt(0),df[col]).to_csv(output/f"{col}_positive_spells.csv",index=False)
    spells(time,df.image_link.isna()).to_csv(output/"missing_image_spells.csv",index=False)
    df.loc[df.image_link.isna(),["time","rain","precipitation","weather_code"]].to_csv(output/"missing_image_records.csv",index_label="row_index")
    checks, examples=physical_checks(df)
    checks.to_csv(output/"consistency_checks.csv",index=False); examples.to_csv(output/"suspect_examples.csv",index=False)
    selected=numeric.drop(columns=["weather_code","wind_direction_10m","is_day"])
    corr=selected.corr(method="pearson"); corr.to_csv(output/"pearson_exploratory.csv")
    reuse=[]
    for link,group in df.dropna(subset=["image_link"]).groupby("image_link",sort=True):
        if len(group)<2: continue
        times=time.loc[group.index].sort_values()
        reuse.append({"image_link":link,"rows":len(group),"first":str(times.iloc[0]),"last":str(times.iloc[-1]),
                      "span_hours":(times.iloc[-1]-times.iloc[0]).total_seconds()/3600,
                      "gaps_hours":json.dumps((times.diff().dropna().dt.total_seconds()/3600).tolist())})
    reuse=pd.DataFrame(reuse); reuse.to_csv(output/"image_reuse.csv",index=False)
    comparison={"different_rows":int(df.rain.ne(df.precipitation).sum()),"max_abs_difference":float(abs(df.rain-df.precipitation).max())}
    save_json(output/"rain_comparison.json",comparison)
    return time,monthly,annual,seasonal,desc,categorical,corr,reuse


def sample_goes(df,time,zip_path,output,reuse):
    rng=np.random.default_rng(SEED)
    with zipfile.ZipFile(zip_path,"r") as archive:
        infos={entry.filename:entry for entry in archive.infolist() if entry.filename.endswith(".npz")}
        inventory=pd.DataFrame([{"image_link":name,"bytes":entry.file_size,"capture_filename":name_time(name),
                                 "satellite_filename":re.search(r"_(G\d+)_",name).group(1)} for name,entry in infos.items()])
        inventory=inventory.sort_values(["capture_filename","image_link"]).reset_index(drop=True)
        inventory["referenced"]=inventory.image_link.isin(df.image_link.dropna())
        inventory["month_utc"]=inventory.capture_filename.dt.strftime("%Y-%m")
        inventory.groupby(["month_utc","satellite_filename"]).agg(npz=("image_link","size"),referenced=("referenced","sum")).to_csv(output/"zip_coverage_month_satellite.csv")
        unreferenced=inventory[~inventory.referenced]
        unreferenced.to_csv(output/"unreferenced_npz.csv",index=False)
        referenced=inventory[inventory.referenced]
        chosen=defaultdict(set)
        def choose(names,reason):
            for name in names: chosen[name].add(reason)
        for _,group in referenced.groupby(["month_utc","satellite_filename"],sort=True):
            choose(group.iloc[np.sort(rng.choice(len(group),min(2,len(group)),replace=False))].image_link,"2_por_mes_utc_satelite_seed42")
        transitions=inventory.index[inventory.satellite_filename.ne(inventory.satellite_filename.shift())].tolist()[1:]
        for idx in transitions:
            choose(inventory.iloc[max(0,idx-3):idx+3].image_link,"vizinhanca_transicao_satelite")
        choose(inventory.nsmallest(3,"bytes").image_link,"3_menores_npz")
        choose(inventory.nlargest(3,"bytes").image_link,"3_maiores_npz")
        choose(reuse.sort_values(["span_hours","image_link"],ascending=[False,True]).head(8).image_link,"8_reusos_maior_intervalo")
        choose(unreferenced.head(1).image_link,"primeiro_nao_referenciado")
        choose(unreferenced.tail(1).image_link,"ultimo_nao_referenciado")
        choose(df.image_link.dropna().head(1),"amostra_estagio1")
        nominal=pd.DataFrame({"row_index":df.index,"csv_time":time,"image_link":df.image_link}).dropna(subset=["image_link"])
        nominal["capture_filename"]=nominal.image_link.map(dict(zip(inventory.image_link,inventory.capture_filename)))
        nominal["delta_seconds"]=(nominal.capture_filename-nominal.csv_time).dt.total_seconds()
        choose(nominal.nsmallest(3,"delta_seconds").image_link,"3_menores_desvios_nome")
        choose(nominal.nlargest(3,"delta_seconds").image_link,"3_maiores_desvios_nome")
        nominal.delta_seconds.describe(percentiles=[.01,.5,.99]).to_csv(output/"filename_delta_summary.csv")
        manifest=inventory[inventory.image_link.isin(chosen)].copy()
        manifest["reason"]=manifest.image_link.map(lambda name:";".join(sorted(chosen[name])))
        manifest.to_csv(output/"goes_sample_manifest.csv",index=False)
        inventory.loc[transitions].to_csv(output/"satellite_filename_transitions.csv",index=False)
        details=[]; pairings=[]
        metadata_keys=["timestamp_utc","satellite","source_filename","source_key","grid_signature","scale_factor","add_offset","fill_value","units"]
        for number,row in enumerate(manifest.itertuples(index=False),1):
            detail={"image_link":row.image_link,"reason":row.reason,"bytes":row.bytes,"errors":[]}
            try:
                if row.bytes>32*1024**2: raise ValueError("NPZ acima do limite de 32 MiB")
                payload=archive.read(row.image_link)
                with zipfile.ZipFile(io.BytesIO(payload)) as inner:
                    if sum(i.file_size for i in inner.infolist())>128*1024**2: raise ValueError("Expansão NPZ acima de 128 MiB")
                with np.load(io.BytesIO(payload),allow_pickle=False) as data:
                    detail["keys"]=data.files
                    meta={key:scalar(data,key) for key in metadata_keys if key in data}
                    detail["metadata"]=meta
                    detail["missing_metadata"]=[key for key in metadata_keys if key not in data]
                    raw=data["cmi_c13_raw"]
                    if raw.ndim!=2 or raw.dtype.kind not in "iuf": raise ValueError("Matriz não numérica/bidimensional")
                    mask=np.isfinite(raw)
                    if "fill_value" in meta: mask &= raw!=meta["fill_value"]
                    else: detail["errors"].append("Sem fill_value: contagem finita não certifica validade")
                    detail.update(shape=list(raw.shape),dtype=str(raw.dtype),pixels=int(raw.size),valid_pixels=int(mask.sum()),invalid_pixels=int((~mask).sum()))
                    detail["raw_valid"]=stats(raw[mask]) if mask.any() else None
                    if all(k in meta for k in ["scale_factor","add_offset","fill_value","units"]) and mask.any():
                        physical=raw[mask].astype(np.float64)*float(meta["scale_factor"])+float(meta["add_offset"])
                        if not np.isfinite(physical).all(): raise ValueError("Reconstrução não finita")
                        detail["physical"]=stats(physical)
                        if str(meta["units"]).strip().lower() in ["k","kelvin"]: detail["celsius"]=stats(physical-273.15)
                        del physical
                    if not mask.any(): detail["errors"].append("Matriz sem pixels válidos; estatísticas indisponíveis")
                    del raw,mask
                del payload
                if "timestamp_utc" in meta:
                    capture=pd.Timestamp(meta["timestamp_utc"])
                    detail["timestamp_offset_seconds"]=None if capture.tzinfo is None else capture.utcoffset().total_seconds()
                    if capture.tzinfo is None:
                        detail["errors"].append("timestamp sem offset: UTC adotado conforme README")
                        capture=capture.tz_localize("UTC")
                    capture=capture.tz_convert("UTC")
                    detail["capture_utc"]=str(capture)
                    detail["metadata_minus_filename_seconds"]=(capture-row.capture_filename).total_seconds()
                    detail["filename_satellite_matches"]=str(meta.get("satellite","")).replace("GOES-","G")==row.satellite_filename
                    detail["source_filename_matches"]=Path(str(meta.get("source_filename",""))).stem==Path(row.image_link).stem
                    detail["source_key_basename_matches"]=Path(str(meta.get("source_key",""))).name==meta.get("source_filename")
                    for idx in df.index[df.image_link.eq(row.image_link).fillna(False)]:
                        delta=(capture-time.iloc[idx].tz_convert("UTC")).total_seconds()
                        end=name_time(str(meta.get("source_filename","")),"e")
                        creation=name_time(str(meta.get("source_filename","")),"c")
                        pairings.append({"row_index":int(idx),"csv_local":str(time.iloc[idx]),"csv_utc":str(time.iloc[idx].tz_convert("UTC")),"image_link":row.image_link,
                            "timestamp_original":meta["timestamp_utc"],"capture_utc":str(capture),"delta_seconds":delta,
                            "direction":"depois" if delta>0 else "antes" if delta<0 else "igual",
                            "end_minus_csv_seconds":None if pd.isna(end) else (end-time.iloc[idx]).total_seconds(),
                            "creation_minus_csv_seconds":None if pd.isna(creation) else (creation-time.iloc[idx]).total_seconds(),
                            "satellite":meta.get("satellite"),"reason":row.reason})
            except (ValueError,KeyError,OSError,zipfile.BadZipFile,TypeError) as error:
                detail["errors"].append(f"{type(error).__name__}: {error}")
            details.append(detail)
            if number%25==0: print(f"GOES: {number}/{len(manifest)} imagens examinadas",flush=True)
        save_json(output/"goes_sample_details.json",details)
        flat=[]
        for detail in details:
            flat.append({"image_link":detail["image_link"],"reason":detail["reason"],
                **detail.get("metadata",{}),"shape":str(detail.get("shape")),"dtype":detail.get("dtype"),
                "pixels":detail.get("pixels"),"invalid_pixels":detail.get("invalid_pixels"),
                **{f"physical_{k}":v for k,v in detail.get("physical",{}).items()},
                "metadata_minus_filename_seconds":detail.get("metadata_minus_filename_seconds"),
                "errors":";".join(detail["errors"])})
        flat=pd.DataFrame(flat); flat.to_csv(output/"goes_sample_summary.csv",index=False)
        pairs=pd.DataFrame(pairings); pairs.to_csv(output/"goes_temporal_pairings.csv",index=False)
        flat.groupby(["satellite","grid_signature","shape","dtype","units","scale_factor","add_offset","fill_value"],dropna=False).agg(images=("image_link","size"),invalid_min=("invalid_pixels","min"),invalid_max=("invalid_pixels","max")).to_csv(output/"goes_grids.csv")
        return details,pairs,inventory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv",type=Path,required=True); parser.add_argument("--zip",type=Path,required=True)
    parser.add_argument("--readme",type=Path,required=True)
    args=parser.parse_args()
    output=ROOT/"reports"/"eda"; output.mkdir(parents=True,exist_ok=True)
    figures=ROOT/"reports"/"figures"; figures.mkdir(parents=True,exist_ok=True)
    protected=[args.csv,args.zip,args.readme,ROOT/"reports"/"dataset_audit.md",ROOT/"reports"/"audit_results.json",ROOT/"src"/"data"/"audit.py",ROOT/"tests"/"test_audit.py"]
    before=[fingerprint(p) for p in protected]
    previous=json.loads((ROOT/"reports"/"audit_results.json").read_text(encoding="utf-8"))
    current,df=audit(args.csv,args.zip,args.readme)
    save_json(output/"audit_recheck.json",current)
    divergences={key:{"previous":previous["csv"].get(key),"current":value} for key,value in current["csv"].items()
                 if key not in ["head","tail","memory_bytes_deep"] and previous["csv"].get(key)!=value}
    values=csv_analysis(df,output)
    time,monthly,annual,seasonal,desc,categories,corr,reuse=values
    details,pairs,inventory=sample_goes(df,time,args.zip,output,reuse)
    after=[fingerprint(p) for p in protected]
    run={"seed":SEED,"sample_images":len(details),"sample_pairings":len(pairs),"csv_divergences":divergences,
         "environment":current["environment"],"sources_before":before,"sources_after":after,"protected_unchanged":before==after,
         "original_readme":str(args.readme),"previous_sample_timestamp":previous.get("sample",{}).get("metadata",{}).get("timestamp_utc"),
         "current_first_timestamp":current.get("sample",{}).get("metadata",{}).get("timestamp_utc"),
         "parameters":{"timezone":"America/Sao_Paulo","monthly_per_satellite":2,"iqr_factor":1.5,"dew_tolerance_C":.2,"radiation_tolerance_W_m2":2,
                       "sample_max_bytes":32*1024**2,"inner_npz_max_bytes":128*1024**2,"std_csv_ddof":1,"std_pixels_ddof":0}}
    import matplotlib
    run["environment"]["matplotlib"]=matplotlib.__version__
    save_json(output/"run_manifest.json",run)
    from eda_figures import render
    render(df,time,monthly,seasonal,categories,corr,pairs,figures)
    from eda_report import build
    build(df,output)
    print(json.dumps({"sample_images":len(details),"pairings":len(pairs),"protected_unchanged":before==after,"csv_divergences":divergences},ensure_ascii=False),flush=True)
    if before!=after: raise RuntimeError("Uma fonte protegida mudou durante a execução")


if __name__=="__main__":
    main()
