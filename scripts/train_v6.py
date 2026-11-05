"""Treinamento v6: comparação e combinação de três Random Forests por pesos de classe."""
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import joblib, numpy as np, pandas as pd, sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, log_loss, precision_score, recall_score, f1_score, balanced_accuracy_score, matthews_corrcoef
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, WEATHER_TIMEZONE, settings
from scripts.archive.train_v4 import TARGET, load_table
from scripts.archive.train_v5 import FEATURES, CV_YEARS, SEEDS, temporal_fold

MODELS = {
 'original': {'class_weight': None},
 'balanced': {'class_weight': 'balanced'},
 'balanced_subsample': {'class_weight': 'balanced_subsample'},
}
WEIGHTS = {
 'equal': {'original': 1/3, 'balanced': 1/3, 'balanced_subsample': 1/3},
 'original_favor': {'original': .5, 'balanced': .25, 'balanced_subsample': .25},
 'balanced_favor': {'original': .2, 'balanced': .6, 'balanced_subsample': .2},
 'subsample_favor': {'original': .2, 'balanced': .2, 'balanced_subsample': .6},
}
PARAMS = {'n_estimators':400, 'max_depth':None, 'max_features':'sqrt', 'min_samples_split':2, 'min_samples_leaf':10, 'bootstrap':True, 'n_jobs':-1}
DEV_END = pd.Timestamp('2026-01-01T00:00:00-03:00').tz_convert('UTC')

def metrics(y,p):
 y=np.asarray(y,dtype='int8'); p=np.clip(np.asarray(p,dtype=float),1e-7,1-1e-7); pred=p>=.5
 return {'pr_auc':float(average_precision_score(y,p)), 'roc_auc':float(roc_auc_score(y,p)), 'brier':float(brier_score_loss(y,p)), 'log_loss':float(log_loss(y,p)), 'precision_at_0_5':float(precision_score(y,pred,zero_division=0)), 'recall_at_0_5':float(recall_score(y,pred,zero_division=0)), 'f1_at_0_5':float(f1_score(y,pred,zero_division=0)), 'balanced_accuracy_at_0_5':float(balanced_accuracy_score(y,pred)), 'mcc_at_0_5':float(matthews_corrcoef(y,pred)), 'false_positives_at_0_5':int(((pred)&(y==0)).sum()), 'false_negatives_at_0_5':int(((~pred)&(y==1)).sum())}

def run(source,out):
 source=Path(source).resolve(); out=Path(out).resolve(); exp=(ROOT/'data'/'experiments').resolve()
 if not out.is_relative_to(exp) or out.exists(): raise ValueError('Saída deve ser nova e estar dentro de data/experiments')
 frame=load_table(source); dev=frame[frame.target_time<DEV_END].copy(); rows=[]; preds=[]
 for year in CV_YEARS:
  tr,va=temporal_fold(dev,year); y=va[TARGET].to_numpy(); ps={}
  for name,cw in MODELS.items():
   ps[name]=[]
   for seed in SEEDS:
    model=RandomForestClassifier(**PARAMS,**cw,random_state=seed); model.fit(tr[FEATURES],tr[TARGET]); p=model.predict_proba(va[FEATURES])[:,list(model.classes_).index(1)]; ps[name].append(p)
    rows.append({'strategy':name,'fold_year':year,'seed':seed,**metrics(y,p)})
  for seed_i,seed in enumerate(SEEDS):
   ensemble_inputs={n:ps[n][seed_i] for n in MODELS}
   for name,p in ensemble_inputs.items(): preds.append(pd.DataFrame({'time':va.time.to_numpy(),'target_time':va.target_time.to_numpy(),TARGET:y,'fold_year':year,'seed':seed,'strategy':name,'probability':p}))
   for label,w in WEIGHTS.items():
    p=sum(w[n]*ensemble_inputs[n] for n in MODELS); rows.append({'strategy':'ensemble_'+label,'fold_year':year,'seed':seed,**metrics(y,p)})
    preds.append(pd.DataFrame({'time':va.time.to_numpy(),'target_time':va.target_time.to_numpy(),TARGET:y,'fold_year':year,'seed':seed,'strategy':'ensemble_'+label,'probability':p}))
   print(f'fold={year} seed={seed} concluído',flush=True)
 out.mkdir(parents=True); pd.DataFrame(rows).to_csv(out/'metrics_by_fold_seed.csv',index=False); pd.concat(preds,ignore_index=True).to_csv(out/'predictions_oof.csv',index=False)
 score=pd.DataFrame(rows); cols=['pr_auc','roc_auc','brier','log_loss','precision_at_0_5','recall_at_0_5','f1_at_0_5','balanced_accuracy_at_0_5','mcc_at_0_5','false_positives_at_0_5','false_negatives_at_0_5']; summary=score.groupby('strategy')[cols].agg(['mean','std']); summary.columns=[f'{a}_{b}' for a,b in summary.columns]; summary.reset_index().to_csv(out/'strategy_summary.csv',index=False)
 hashes={}; final={}
 for name,cw in MODELS.items():
  m=RandomForestClassifier(**PARAMS,**cw,random_state=42); m.fit(dev[FEATURES],dev[TARGET]); f=f'{name}_leaf10_trees400.joblib'; joblib.dump(m,out/f,compress=3); hashes[f]=hashlib.sha256((out/f).read_bytes()).hexdigest(); final[f]=m.get_params()
 manifest={'experiment':'train_v6_weighted_random_forest_ensemble','created_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__,'scikit_learn':sklearn.__version__,'joblib':joblib.__version__,'source_path':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_rows':len(frame),'development_rows_before_2026':len(dev),'features':FEATURES,'target':TARGET,'cv_years':CV_YEARS,'seeds':SEEDS,'split_method':'expanding chronological folds; target_time constrained within year','member_parameters':{n:{**PARAMS,**cw} for n,cw in MODELS.items()},'ensemble_weights':WEIGHTS,'selection_rule':'descriptive comparison by mean PR-AUC; Brier as probability-quality companion; no operational winner without error-cost definition','test_2026_used':False,'test_evaluated':False,'test_used_for_selection':False,'independent_blind_test':False,'final_models_trained_on_development_only':final,'model_sha256':hashes,'outputs':['metrics_by_fold_seed.csv','strategy_summary.csv','predictions_oof.csv']}
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
 rows=summary.reset_index(); (out/'experiment_summary.json').write_text(rows.to_json(orient='records',force_ascii=False,indent=2),encoding='utf-8')
 rows_total_pt=f'{len(frame):,}'.replace(',', '.'); rows_dev_pt=f'{len(dev):,}'.replace(',', '.')
 report=ROOT/'reports'/'training'/'sixth_training_report.md'; ordered=summary.reset_index().sort_values(['pr_auc_mean','brier_mean'],ascending=[False,True]); table='| Estratégia | PR-AUC média | Brier médio | Sensibilidade média | F1 médio |\n|---|---:|---:|---:|---:|\n'+'\n'.join(f"| {r['strategy']} | {r['pr_auc_mean']:.5f} | {r['brier_mean']:.5f} | {r['recall_at_0_5_mean']:.5f} | {r['f1_at_0_5_mean']:.5f} |" for _,r in ordered.iterrows()); report.write_text(f"""# Relatório do sexto treinamento — v6\n\n**Data:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}  \n**Experimento:** `{out.name}`  \n**Script:** `scripts/train_v6.py`\n\n## Objetivo\n\nComparar três Random Forests com a mesma estrutura e combinar suas probabilidades com quatro proporções previamente definidas. A intenção é verificar se a combinação equilibra a detecção de chuva e os falsos alarmes.\n\n## Dados e procedimento\n\nFonte preparada: `{source.name}` ({rows_total_pt} linhas, SHA-256 no manifesto). Foram usadas {rows_dev_pt} linhas até 31/12/2025 para desenvolvimento, sete atributos, quatro partições cronológicas (2022–2025) e três sementes ({', '.join(map(str,SEEDS))}). Cada partição respeita `target_time` na fronteira do ano. O período de 2026 não foi avaliado nem usado na seleção.\n\n## Configurações\n\nTodos os membros têm 400 árvores, folha mínima 10, `max_features=sqrt`, bootstrap habilitado, profundidade não limitada e demais parâmetros iguais. Variou apenas `class_weight`: sem pesos (`original`), `balanced` e `balanced_subsample`. Foram comparadas médias de probabilidades com pesos iguais (1/3 cada) e alternativas pré-definidas favorecendo cada família.\n\n## Resultados\n\nMédias e desvios-padrão sobre anos e sementes; limiar fixo de 0,50 para métricas de classificação.\n\n{table}\n\nPR-AUC é a métrica primária descritiva; Brier e métricas de erro ajudam a interpretar a qualidade probabilística e o compromisso operacional. As combinações foram comparadas nas mesmas partições e previsões fora da amostra. A melhor média não é prova de superioridade futura; não houve definição de custos relativos entre falso alarme e chuva não detectada.\n\n## Artefatos e limites\n\nO experimento contém três joblibs finais ajustados somente até 2025, `manifest.json` com parâmetros e hashes, métricas por partição/semente, resumo das estratégias e previsões fora da amostra. Não foram gravados resultados em PDF. O teste retrospectivo de 2026 foi deliberadamente preservado; já foi consultado em ciclos anteriores e não é cego. Para uma decisão operacional, definir custo/limiar usando desenvolvimento e avaliar em dados futuros ainda não consultados.\n""",encoding='utf-8')
 print(json.dumps({'output':str(out),'report':str(report),'top':ordered.iloc[0].to_dict()},ensure_ascii=False,default=str),flush=True)

if __name__=='__main__':
 cfg=settings(); ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,default=cfg['training']); ap.add_argument('--output-dir',type=Path,default=ROOT/'data'/'experiments'/('weather_v6_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))); a=ap.parse_args(); run(a.input,a.output_dir)
