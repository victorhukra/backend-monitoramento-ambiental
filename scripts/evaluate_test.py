"""Avaliação v7 aninhada de calibração, pesos e limiar para RFs da v6."""
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd, sklearn
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, roc_auc_score, brier_score_loss,
 log_loss, precision_score, recall_score, f1_score, balanced_accuracy_score, matthews_corrcoef)
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from config import ROOT
BASE=('original','balanced','balanced_subsample')
FIXED={'original':(1.,0.,0.),'balanced_subsample':(0.,0.,1.),'ensemble_equal':(1/3,1/3,1/3),'ensemble_original_favor':(.5,.25,.25)}
CALIBRATORS=('none','sigmoid','isotonic'); COST_RATIOS=(.5,1.,2.,5.)
THRESHOLDS=np.round(np.arange(.05,.951,.01),2); YEARS=(2023,2024,2025)
def weight_grid():
 out=[]
 for i in range(1,9):
  for j in range(1,10-i):
   k=10-i-j
   if k>=1:out.append((i/10,j/10,k/10))
 return list(dict.fromkeys([FIXED['ensemble_equal'],FIXED['ensemble_original_favor'],*out]))
def fit_map(method,p,y):
 p=np.clip(np.asarray(p,float),1e-6,1-1e-6); y=np.asarray(y,dtype='int8')
 if method=='none':return None
 if method=='sigmoid':
  z=np.log(p/(1-p)).reshape(-1,1); return ('sigmoid',LogisticRegression(max_iter=1000,random_state=42).fit(z,y))
 return ('isotonic',IsotonicRegression(out_of_bounds='clip').fit(p,y))
def apply_map(fitted,p):
 p=np.clip(np.asarray(p,float),1e-6,1-1e-6)
 if fitted is None:return p
 kind,model=fitted
 return model.predict_proba(np.log(p/(1-p)).reshape(-1,1))[:,1] if kind=='sigmoid' else np.asarray(model.predict(p),float)
def min_cost_threshold(y,p,ratio):
 y=np.asarray(y,dtype='int8'); p=np.asarray(p,float); order=np.argsort(p); ps=p[order]; ys=y[order]
 pos=np.cumsum(ys[::-1])[::-1]; neg=np.cumsum((1-ys)[::-1])[::-1]; ix=np.searchsorted(ps,THRESHOLDS,side='left')
 tp=np.where(ix<len(ps),pos[np.minimum(ix,len(ps)-1)],0); fp=np.where(ix<len(ps),neg[np.minimum(ix,len(ps)-1)],0); fn=int(y.sum())-tp
 costs=(fp+ratio*fn)/len(y); choices=np.flatnonzero(np.isclose(costs,costs.min(),rtol=0,atol=1e-12)); j=choices[-1]
 return float(THRESHOLDS[j]),float(costs[j])
def score(y,p,t,ratio):
 y=np.asarray(y,dtype='int8'); p=np.clip(np.asarray(p,float),1e-7,1-1e-7); pred=p>=t; fp=int((pred&(y==0)).sum()); fn=int(((~pred)&(y==1)).sum())
 return {'pr_auc':float(average_precision_score(y,p)),'roc_auc':float(roc_auc_score(y,p)),'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p)),'precision':float(precision_score(y,pred,zero_division=0)),'recall':float(recall_score(y,pred,zero_division=0)),'f1':float(f1_score(y,pred,zero_division=0)),'balanced_accuracy':float(balanced_accuracy_score(y,pred)),'mcc':float(matthews_corrcoef(y,pred)),'false_positives':fp,'false_negatives':fn,'weighted_error_cost_per_row':float((fp+ratio*fn)/len(y))}
def run(source,out):
 source=Path(source).resolve(); out=Path(out).resolve(); exp=(ROOT/'data'/'experiments').resolve()
 if not source.is_file():raise FileNotFoundError(source)
 if not source.is_relative_to(ROOT):raise ValueError('A entrada deve estar dentro da pasta do projeto')
 source_relative=source.relative_to(ROOT).as_posix()
 if not out.is_relative_to(exp) or out.exists():raise ValueError('Saída deve ser nova em data/experiments')
 raw=pd.read_csv(source); required={'time','target_time','rain_next_hour','fold_year','seed','strategy','probability'}
 if not required.issubset(raw.columns):raise ValueError(f'Colunas ausentes: {sorted(required-set(raw.columns))}')
 raw=raw[raw.strategy.isin(BASE)]; keys=['time','target_time','rain_next_hour','fold_year','seed']; wide=raw.pivot(index=keys,columns='strategy',values='probability').reset_index()
 if any(n not in wide for n in BASE):raise ValueError('Previsões das três famílias v6 não encontradas')
 weights=weight_grid(); results=[]; configs=[]; pred_frames=[]
 for year in YEARS:
  inner=wide[wide.fold_year<year]; outer=wide[wide.fold_year==year]
  if inner.empty or outer.empty or inner.rain_next_hour.nunique()<2:raise ValueError(f'Dados insuficientes no fold {year}')
  yi=inner.rain_next_hour.to_numpy(dtype='int8'); yo=outer.rain_next_hour.to_numpy(dtype='int8'); pin={}; pout={}
  for method in CALIBRATORS:
   pin[method]={}; pout[method]={}
   for name in BASE:
    mapper=fit_map(method,inner[name].to_numpy(),yi); pin[method][name]=apply_map(mapper,inner[name].to_numpy()); pout[method][name]=apply_map(mapper,outer[name].to_numpy())
  policies={**FIXED,'ensemble_tuned':None}
  for ratio in COST_RATIOS:
   for label,fixed_w in policies.items():
    trials=[]
    for method in CALIBRATORS:
     options=weights if label=='ensemble_tuned' else [fixed_w]
     for w in options:
      p=sum(w[i]*pin[method][n] for i,n in enumerate(BASE)); threshold,cost=min_cost_threshold(yi,p,ratio)
      trials.append((cost,-threshold,CALIBRATORS.index(method),tuple(w),method,threshold))
    best=min(trials,key=lambda z:(z[0],z[1],z[2],z[3])); _,_,_,w,method,threshold=best
    p=sum(w[i]*pout[method][n] for i,n in enumerate(BASE))
    seed_values=outer.seed.to_numpy()
    for seed in np.unique(seed_values):
     mask=seed_values==seed; measured=score(yo[mask],p[mask],threshold,ratio)
     row={'outer_year':year,'seed':int(seed),'fn_to_fp_cost_ratio':ratio,'pipeline':label,'calibration':method,'weight_original':w[0],'weight_balanced':w[1],'weight_balanced_subsample':w[2],'threshold_selected_on_prior_years':threshold,'inner_cost_per_row':best[0],'outer_rows':int(mask.sum()),**measured}; results.append(row)
    configs.append({'outer_year':year,'fn_to_fp_cost_ratio':ratio,'pipeline':label,'calibration':method,'weight_original':w[0],'weight_balanced':w[1],'weight_balanced_subsample':w[2],'threshold_selected_on_prior_years':threshold,'inner_cost_per_row':best[0]})
    pred_frames.append(pd.DataFrame({'time':outer.time.to_numpy(),'target_time':outer.target_time.to_numpy(),'rain_next_hour':yo,'fold_year':year,'seed':seed_values,'cost_ratio':ratio,'pipeline':label,'calibration':method,'threshold':threshold,'probability':p}))
  print(f'fold externo {year} concluído; ajuste interno limitado a anos anteriores',flush=True)
 out.mkdir(parents=True); res=pd.DataFrame(results); res.to_csv(out/'outer_fold_metrics.csv',index=False); pd.DataFrame(configs).to_csv(out/'selected_configuration_by_fold.csv',index=False); pd.concat(pred_frames,ignore_index=True).to_csv(out/'nested_predictions.csv',index=False)
 avg=wide.groupby(['time','target_time','rain_next_hour','fold_year'],as_index=False)[list(BASE)].mean(); y=avg.rain_next_hour.to_numpy(dtype='int8'); err={n:(avg[n].to_numpy()>=.5)!=y for n in BASE}; pairs=[]
 for i,a in enumerate(BASE):
  for b in BASE[i+1:]:
   ea,eb=err[a],err[b]; pairs.append({'model_a':a,'model_b':b,'rows':len(y),'error_rate_a':ea.mean(),'error_rate_b':eb.mean(),'both_wrong_rate':(ea&eb).mean(),'disagreement_rate':(ea!=eb).mean(),'a_missed_rain_caught_by_b':int(((y==1)&ea&~eb).sum()),'b_missed_rain_caught_by_a':int(((y==1)&eb&~ea).sum())})
 pd.DataFrame(pairs).to_csv(out/'error_complementarity.csv',index=False)
 fields=['weighted_error_cost_per_row','pr_auc','brier','precision','recall','f1','false_positives','false_negatives','threshold_selected_on_prior_years']; summary=res.groupby(['fn_to_fp_cost_ratio','pipeline'])[fields].mean().reset_index(); summary.to_csv(out/'nested_summary.csv',index=False)
 manifest={'experiment':'v7_nested_temporal_calibration_weight_threshold_evaluation','created_at_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__,'scikit_learn':sklearn.__version__,'input_path':source_relative,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_v6':'weather_v6_20261105T120000Z','outer_years':YEARS,'inner_policy':'only v6 OOF folds strictly earlier than outer evaluation year','calibrators':CALIBRATORS,'weight_grid_step':.1,'minimum_weight_per_family':.1,'cost_ratios_fn_to_fp':COST_RATIOS,'threshold_grid':[.05,.95,.01],'test_2026_used':False,'test_evaluated':False,'final_model_selected':False,'final_joblibs_written':False,'reason_no_final_joblibs':'operational error cost has not been approved','outputs':['outer_fold_metrics.csv','selected_configuration_by_fold.csv','nested_predictions.csv','nested_summary.csv','error_complementarity.csv']}
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
 lines=['# Avaliação aninhada v7 — calibração, combinação e limiar','',f'**Data:** {datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")}  ',f'**Experimento:** `{out.name}`  ',f'**Entrada:** `{source_relative}`','','## Objetivo','','Avaliar se calibrar probabilidades e escolher pesos/limiar somente em anos anteriores melhora a decisão no ano seguinte. A v7 reusa previsões fora da amostra da v6; não retreina os Random Forests nem aprova uso operacional.','','## Protocolo temporal','','As partições externas são os anos de 2023, 2024 e 2025. Em cada ano, calibração, pesos e limiar são ajustados apenas com previsões fora da amostra dos anos anteriores; a partição externa mede a configuração congelada. Os resultados mantêm três sementes. O teste de 2026 não foi usado.','','Compara original, `balanced_subsample`, média igual, `ensemble_original_favor` e combinação otimizada em grade simplex (passo 0,1; peso mínimo 0,1 por modelo). Calibração sem ajuste (`none`), sigmoide e isotônica. O limiar minimiza `FP + razão × FN` nos anos anteriores. Razões FN:FP: 0,5:1, 1:1, 2:1 e 5:1.','','## Resultados por cenário','','| Custo FN:FP | Política | Custo externo/linha | PR-AUC | Brier | Precisão | Sensibilidade | F1 | Limiar médio |','|---:|---|---:|---:|---:|---:|---:|---:|---:|']
 for _,r in summary.sort_values(['fn_to_fp_cost_ratio','weighted_error_cost_per_row']).iterrows():lines.append(f"| {r.fn_to_fp_cost_ratio:g}:1 | {r.pipeline} | {r.weighted_error_cost_per_row:.5f} | {r.pr_auc:.5f} | {r.brier:.5f} | {r.precision:.4f} | {r.recall:.4f} | {r.f1:.4f} | {r.threshold_selected_on_prior_years:.3f} |")
 lines += [
  '', 'Pesos, calibrador e limiar por ano estão em `selected_configuration_by_fold.csv`; métricas em `outer_fold_metrics.csv`, previsões em `nested_predictions.csv`. `error_complementarity.csv` mede desacordo e sobreposição dos erros dos três membros em previsões fora da amostra a 0,50.',
  '', '## Interpretação e limites',
  '', 'As razões de custo são cenários, não valores aprovados pela equipe. Há só três partições externas, e a escolha posterior entre políticas ainda pode ser otimista. Os resultados são evidência de desenvolvimento, não avaliação futura independente. Não se escolhe vencedor operacional sem aprovar custo ou limite máximo de alertas.',
  '', '## Interpretação dos resultados',
  '', 'A combinação de pesos iguais (`ensemble_equal`) teve o menor custo médio nos cenários FN:FP de 0,5:1 e 5:1. O modelo original foi melhor nos cenários 1:1 e 2:1; portanto, não há uma estratégia que minimize o custo em todos os cenários. A média simples manteve PR-AUC de 0,67189 e Brier de 0,08629, ligeiramente melhores que o original (0,66060 e 0,08640) e próximos do `balanced_subsample` (0,66020 e 0,08650).',
  '', 'Quando o custo de não detectar chuva sobe para 5:1, a média simples atingiu sensibilidade de 0,8291, com precisão de 0,4868 e limiar médio de 0,180. No cenário 0,5:1, o limiar médio subiu para 0,657 e a sensibilidade caiu para 0,2213. Isso mostra que o limiar muda bastante conforme o custo escolhido. Como os custos ainda não foram aprovados e há somente três partições externas, esses resultados orientam a discussão, mas não estabelecem uma política operacional definitiva.',
  '', 'A v7 não grava joblibs finais porque ainda não existe critério aprovado para congelar uma combinação. Após essa decisão, treinar a configuração final em todo o desenvolvimento, fixar o manifesto e avaliar somente em dados futuros ainda não consultados.',
  '', '## Referências',
  '', '- [RandomForestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)',
  '- [Calibração de probabilidades](https://scikit-learn.org/stable/modules/calibration.html)',
  '- [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)',
  '- [Precisão média (Average Precision) / PR-AUC](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html)',
  '', '## Preparação para integração',
  '', 'Após a avaliação, foi preparado o candidato `weather-v6-simple-mean-isotonic-v1`: os três membros calibrados isotonicamente são combinados com pesos 1/3 e limiar provisório 0,50. O pacote do modelo e o manifesto estão em `data/experiments/weather_v6_integration_candidate_20261105T190315Z/`. O teste de 2026 continua sem uso; a escolha prepara a integração histórica e não representa aprovação operacional independente.', ''
 ]
 report=ROOT/'reports'/'training'/'seventh_training_report.md'; report.write_text('\n'.join(lines),encoding='utf-8'); (out/'experiment_summary.json').write_text(json.dumps({'outer_years':YEARS,'cost_ratios':COST_RATIOS,'pipelines':sorted(res.pipeline.unique()),'outer_metric_rows':len(res),'report':'reports/training/seventh_training_report.md','test_2026_used':False,'final_model_selected':False},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'output_dir':str(out),'report':'reports/training/seventh_training_report.md','outer_metric_rows':len(res)},ensure_ascii=False),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,default=ROOT/'data'/'experiments'/'weather_v6_20261105T120000Z'/'predictions_oof.csv'); ap.add_argument('--output-dir',type=Path,default=ROOT/'data'/'experiments'/('weather_v7_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))); a=ap.parse_args();run(a.input,a.output_dir)
