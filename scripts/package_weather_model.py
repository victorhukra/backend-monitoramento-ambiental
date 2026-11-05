# Empacota o ensemble provisório, calibrado e com pesos iguais, a partir dos artefatos congelados da v6.
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import joblib, numpy as np, pandas as pd, sklearn
from sklearn.isotonic import IsotonicRegression
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import ROOT, settings
from scripts.archive.train_v4 import load_table, TARGET
from scripts.archive.train_v5 import FEATURES
from src.models.weather_ensemble import SimpleMeanCalibratedEnsemble, MODEL_NAMES, MODEL_VERSION, WEIGHTS

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def package(v6_dir,out_dir):
    v6_dir=Path(v6_dir).resolve(); out_dir=Path(out_dir).resolve(); exp=(ROOT/'data'/'experiments').resolve()
    if not out_dir.is_relative_to(exp) or out_dir.exists(): raise ValueError('A saída deve ser uma pasta nova dentro de data/experiments.')
    v6_manifest=json.loads((v6_dir/'manifest.json').read_text(encoding='utf-8'))
    oof_path=v6_dir/'predictions_oof.csv'; source=Path(settings()['training']).resolve()
    if sha(source)!=v6_manifest['source_sha256']: raise ValueError('Hash da tabela processada diverge do manifesto v6.')
    models={}; expected=v6_manifest['model_sha256']
    for name in MODEL_NAMES:
        model_file=f'{name}_leaf10_trees400.joblib'; model_path=v6_dir/model_file
        if sha(model_path)!=expected[model_file]: raise ValueError(f'Hash divergente para {model_file}.')
        models[name]=joblib.load(model_path)
        if tuple(models[name].feature_names_in_)!=tuple(FEATURES): raise ValueError(f'Features inesperadas em {model_file}.')
    oof=pd.read_csv(oof_path,usecols=['strategy','rain_next_hour','probability'])
    oof=oof[oof.strategy.isin(MODEL_NAMES)]
    calibrators={}
    calibration_counts={}
    for name in MODEL_NAMES:
        part=oof[oof.strategy==name]
        if part.empty or part.rain_next_hour.nunique()!=2: raise ValueError(f'OOF insuficiente para calibrar {name}.')
        calibrators[name]=IsotonicRegression(out_of_bounds='clip').fit(part.probability.to_numpy(),part.rain_next_hour.to_numpy())
        calibration_counts[name]=int(len(part))
    out_dir.mkdir(parents=True)
    calibrator_path=out_dir/'isotonic_calibrators.joblib'; joblib.dump(calibrators,calibrator_path,compress=3)
    bundle=SimpleMeanCalibratedEnsemble(models,calibrators,threshold=.5,model_version=MODEL_VERSION)
    bundle_path=out_dir/'weather_ensemble.joblib'; joblib.dump(bundle,bundle_path,compress=3)
    # Sanidade de engenharia de features contra uma linha processada anterior a 2026; não avalia desempenho.
    frame=load_table(source); eligible=frame[frame.target_time<pd.Timestamp('2026-01-01T00:00:00-03:00').tz_convert('UTC')]
    row=eligible.iloc[1]; previous_row=eligible.iloc[0]
    if row.time-previous_row.time!=pd.Timedelta(hours=1): raise ValueError('A linha de referência não possui observação horária imediatamente anterior.')
    previous=float(previous_row.pressure_msl)
    weather={
      'temperature_2m':row.temperature_2m,'relative_humidity_2m':row.relative_humidity_2m,
      'pressure_msl':row.pressure_msl,'cloud_cover':row.cloud_cover,'pressure_msl_previous_hour':previous,
    }
    engineered=bundle.prepare_features(weather,row.time)
    if not np.allclose(engineered.iloc[0].to_numpy(float),row[list(FEATURES)].to_numpy(float),rtol=0,atol=1e-9):
        raise ValueError('A engenharia de features da integração não reproduz a tabela preparada.')
    prediction=bundle.predict_one(weather,row.time)
    if not np.isfinite(prediction['rain_probability']): raise ValueError('Probabilidade inválida no smoke de compatibilidade.')
    manifest={
      'model_version':MODEL_VERSION,'artifact_status':'integration_candidate_not_operationally_approved',
      'created_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'numpy':np.__version__,
      'pandas':pd.__version__,'scikit_learn':sklearn.__version__,'joblib':joblib.__version__,
      'source_experiment':'weather_v6_20261105T120000Z','evaluation_reference':'weather_v7_20261105T183313Z',
      'source_dataset_sha256':sha(source),'oof_predictions_sha256':sha(oof_path),
      'features':list(FEATURES),'required_weather_inputs':list(bundle.RAW_FIELDS) if hasattr(bundle,'RAW_FIELDS') else ['temperature_2m','relative_humidity_2m','pressure_msl','cloud_cover','pressure_msl_previous_hour'],
      'feature_engineering':{'temp_humidity':'temperature_2m * relative_humidity_2m','pressure_diff':'pressure_msl - pressure_msl_previous_hour (T-1h)','hour_of_day':'reference_time converted to America/Sao_Paulo, hour'},
      'members':{name:{'class_weight':models[name].class_weight,'n_estimators':models[name].n_estimators,'min_samples_leaf':models[name].min_samples_leaf,'random_state':models[name].random_state,'v6_model_sha256':expected[f'{name}_leaf10_trees400.joblib'],'calibration':'isotonic','calibration_oof_rows':calibration_counts[name]} for name in MODEL_NAMES},
      'weights':WEIGHTS,'threshold':.5,'threshold_status':'provisional; use response field decision_threshold','test_2026_used':False,
      'independent_blind_test':False,'bundle_file':bundle_path.name,'bundle_sha256':sha(bundle_path),
      'calibrators_file':calibrator_path.name,'calibrators_sha256':sha(calibrator_path),'adapter_sha256':sha(ROOT/'src'/'models'/'weather_ensemble.py'),'packager_sha256':sha(Path(__file__)),
      'feature_compatibility_smoke':{'passed':True,'reference_time':str(row.time),'model_output':prediction,'note':'feature-parity check only; not a performance test'},
    }
    (out_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'output_dir':str(out_dir),'bundle':str(bundle_path),'manifest':str(out_dir/'manifest.json'),'model_version':MODEL_VERSION},ensure_ascii=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--v6-dir',type=Path,default=ROOT/'data'/'experiments'/'weather_v6_20261105T120000Z'); ap.add_argument('--output-dir',type=Path,default=ROOT/'data'/'experiments'/('weather_v6_integration_candidate_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))); args=ap.parse_args(); package(args.v6_dir,args.output_dir)
