"""Treinamento v6: comparação e combinação de três Random Forests por pesos de classe.

Executa validação cruzada temporal (rolling-year de 2022 a 2025) com múltiplas
sementes aleatórias para comparar três famílias de Random Forest:
1. original (sem pesos de classe)
2. balanced (pesos inversamente proporcionais à frequência das classes)
3. balanced_subsample (pesos recalculados em cada amostra bootstrap)

Avalia também estratégias de combinação em ensemble (média simples e ponderada).
Ao final, ajusta os três modelos no conjunto completo de desenvolvimento
(dados até 31/12/2025), congelando os artefatos .joblib e gerando relatórios.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

# Inclusão da raiz do projeto no PATH para imports locais
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, WEATHER_FEATURES, WEATHER_TIMEZONE, settings

# Nome da coluna alvo (chuva acumulada na próxima hora > 0)
TARGET = 'rain_next_hour'

# Anos das partições cronológicas da validação cruzada
CV_YEARS = (2022, 2023, 2024, 2025)

# Sementes aleatórias para reprodutibilidade das árvores
SEEDS = (17, 42, 2025)

# As 7 features finais esperadas pelos modelos
FEATURES = [
    'temperature_2m',
    'relative_humidity_2m',
    'pressure_msl',
    'cloud_cover',
    'temp_humidity',
    'pressure_diff',
    'hour_of_day'
]


def load_table(path: Path) -> pd.DataFrame:
    """Carrega a tabela de dados processada e realiza a engenharia de atributos.

    Adiciona as features derivadas:
    - temp_humidity: interação temperatura x umidade relativa
    - pressure_diff: variação barométrica em relação à hora anterior
    - hour_of_day: hora local (0 a 23) no fuso America/Sao_Paulo
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Tabela de treinamento não encontrada: {path}')

    frame = pd.read_csv(path)
    required = ['time', *WEATHER_FEATURES, 'target_time', TARGET]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f'Colunas ausentes na tabela: {sorted(missing)}')
    if frame.empty:
        raise ValueError('A tabela de treinamento está vazia')

    for column in ['time', 'target_time']:
        frame[column] = pd.to_datetime(frame[column], errors='raise', utc=True)
        if frame[column].isna().any():
            raise ValueError(f'Timestamp ausente em {column}')

    if frame['time'].duplicated().any():
        raise ValueError('Existem timestamps duplicados')

    target_series = pd.to_numeric(frame[TARGET], errors='raise')
    if target_series.isna().any() or not target_series.isin([0, 1]).all():
        raise ValueError(f'{TARGET} deve conter apenas 0 e 1')
    frame[TARGET] = target_series.astype('int8')

    for column in WEATHER_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors='raise')

    # Ordenação cronológica estrita antes de calcular lags
    frame = frame.sort_values('time').reset_index(drop=True)

    # Engenharia de atributos
    frame['temp_humidity'] = frame['temperature_2m'] * frame['relative_humidity_2m']
    frame['pressure_diff'] = frame['pressure_msl'].diff().fillna(0.0)
    frame['hour_of_day'] = frame['time'].dt.tz_convert(WEATHER_TIMEZONE).dt.hour

    return frame


def temporal_fold(frame: pd.DataFrame, year: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Separa o conjunto de desenvolvimento em treino (passado) e validação (ano corrente).
    
    Garante que nenhum registro futuro ou com alvo atravessando a fronteira do ano
    seja utilizado no treino (ausência total de data leakage).
    """
    start = pd.Timestamp(f'{year}-01-01', tz=WEATHER_TIMEZONE).tz_convert('UTC')
    end = pd.Timestamp(f'{year + 1}-01-01', tz=WEATHER_TIMEZONE).tz_convert('UTC')

    train = frame[frame['target_time'] < start]
    valid = frame[(frame['time'] >= start) & (frame['target_time'] < end)]

    if train.empty or valid.empty or train[TARGET].nunique() < 2 or valid[TARGET].nunique() < 2:
        raise ValueError(f'Dados insuficientes para o fold de {year}')

    return train, valid

# Configurações de pesos de classe para as três famílias de modelos
MODELS: Dict[str, Dict[str, Any]] = {
    'original': {'class_weight': None},
    'balanced': {'class_weight': 'balanced'},
    'balanced_subsample': {'class_weight': 'balanced_subsample'},
}

# Pesos para as estratégias de ensemble
WEIGHTS: Dict[str, Dict[str, float]] = {
    'equal': {'original': 1 / 3, 'balanced': 1 / 3, 'balanced_subsample': 1 / 3},
    'original_favor': {'original': 0.5, 'balanced': 0.25, 'balanced_subsample': 0.25},
    'balanced_favor': {'original': 0.2, 'balanced': 0.6, 'balanced_subsample': 0.2},
    'subsample_favor': {'original': 0.2, 'balanced': 0.2, 'balanced_subsample': 0.6},
}

# Hiperparâmetros base idênticos compartilhados entre todos os Random Forests
PARAMS: Dict[str, Any] = {
    'n_estimators': 400,
    'max_depth': None,
    'max_features': 'sqrt',
    'min_samples_split': 2,
    'min_samples_leaf': 10,
    'bootstrap': True,
    'n_jobs': -1,
}

# Limite temporal do conjunto de desenvolvimento: dados estritamente anteriores a 2026
DEV_END = pd.Timestamp('2026-01-01T00:00:00-03:00').tz_convert('UTC')

# Lista de colunas de métricas para resumo estatístico
METRIC_COLS = [
    'pr_auc',
    'roc_auc',
    'brier',
    'log_loss',
    'precision_at_0_5',
    'recall_at_0_5',
    'f1_at_0_5',
    'balanced_accuracy_at_0_5',
    'mcc_at_0_5',
    'false_positives_at_0_5',
    'false_negatives_at_0_5',
]


def metrics(y_true: np.ndarray, probabilities: np.ndarray) -> Dict[str, Any]:
    """Calcula métricas probabilísticas e de classificação binária (limiar 0.50).
    
    Args:
        y_true: Vetor com rótulos reais binários (0 ou 1).
        probabilities: Probabilidades estimadas para a classe positiva (chuva).
        
    Returns:
        Dicionário com métricas calculadas (PR-AUC, ROC-AUC, Brier, F1, etc.).
    """
    y = np.asarray(y_true, dtype='int8')
    p = np.clip(np.asarray(probabilities, dtype=float), 1e-7, 1.0 - 1e-7)
    pred = p >= 0.5

    return {
        'pr_auc': float(average_precision_score(y, p)),
        'roc_auc': float(roc_auc_score(y, p)),
        'brier': float(brier_score_loss(y, p)),
        'log_loss': float(log_loss(y, p)),
        'precision_at_0_5': float(precision_score(y, pred, zero_division=0)),
        'recall_at_0_5': float(recall_score(y, pred, zero_division=0)),
        'f1_at_0_5': float(f1_score(y, pred, zero_division=0)),
        'balanced_accuracy_at_0_5': float(balanced_accuracy_score(y, pred)),
        'mcc_at_0_5': float(matthews_corrcoef(y, pred)),
        'false_positives_at_0_5': int(((pred) & (y == 0)).sum()),
        'false_negatives_at_0_5': int(((~pred) & (y == 1)).sum()),
    }


def run_cross_validation(dev: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[pd.DataFrame]]:
    """Executa a validação cruzada temporal em janela expansiva (rolling-year).
    
    Para cada ano (2022 a 2025):
      - Treina os 3 modelos em dados anteriores ao ano.
      - Avalia no ano corrente para 3 sementes aleatórias.
      - Avalia as 4 estratégias de combinação em ensemble.
      
    Returns:
        Tupla com (linhas_metricas, dataframes_previsoes_oof).
    """
    metric_rows: List[Dict[str, Any]] = []
    prediction_frames: List[pd.DataFrame] = []

    for year in CV_YEARS:
        train_df, valid_df = temporal_fold(dev, year)
        y_valid = valid_df[TARGET].to_numpy()
        model_predictions: Dict[str, List[np.ndarray]] = {name: [] for name in MODELS}

        # Treina e avalia cada família de modelo para cada semente
        for name, class_weight_param in MODELS.items():
            for seed in SEEDS:
                model = RandomForestClassifier(
                    **PARAMS,
                    **class_weight_param,
                    random_state=seed,
                )
                model.fit(train_df[FEATURES], train_df[TARGET])

                class_1_idx = list(model.classes_).index(1)
                prob = model.predict_proba(valid_df[FEATURES])[:, class_1_idx]
                model_predictions[name].append(prob)

                metric_rows.append({
                    'strategy': name,
                    'fold_year': year,
                    'seed': seed,
                    **metrics(y_valid, prob),
                })

        # Avaliação das estratégias de combinação (ensemble)
        for seed_idx, seed in enumerate(SEEDS):
            ensemble_inputs = {name: model_predictions[name][seed_idx] for name in MODELS}

            # Previsões individuais fora da amostra (OOF)
            for name, prob in ensemble_inputs.items():
                prediction_frames.append(pd.DataFrame({
                    'time': valid_df.time.to_numpy(),
                    'target_time': valid_df.target_time.to_numpy(),
                    TARGET: y_valid,
                    'fold_year': year,
                    'seed': seed,
                    'strategy': name,
                    'probability': prob,
                }))

            # Combinações ponderadas
            for weight_label, weight_map in WEIGHTS.items():
                ensemble_prob = sum(
                    weight_map[name] * ensemble_inputs[name] for name in MODELS
                )

                metric_rows.append({
                    'strategy': f'ensemble_{weight_label}',
                    'fold_year': year,
                    'seed': seed,
                    **metrics(y_valid, ensemble_prob),
                })

                prediction_frames.append(pd.DataFrame({
                    'time': valid_df.time.to_numpy(),
                    'target_time': valid_df.target_time.to_numpy(),
                    TARGET: y_valid,
                    'fold_year': year,
                    'seed': seed,
                    'strategy': f'ensemble_{weight_label}',
                    'probability': ensemble_prob,
                }))

        print(f'fold={year} concluído para todas as sementes', flush=True)

    return metric_rows, prediction_frames


def train_final_models(dev: pd.DataFrame, output_dir: Path) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """Treina os modelos finais em todo o conjunto de desenvolvimento (até 2025).
    
    Salva os arquivos .joblib e retorna seus hashes SHA-256 e parâmetros.
    """
    model_hashes: Dict[str, str] = {}
    model_parameters: Dict[str, Any] = {}

    for name, class_weight_param in MODELS.items():
        final_model = RandomForestClassifier(
            **PARAMS,
            **class_weight_param,
            random_state=42,
        )
        final_model.fit(dev[FEATURES], dev[TARGET])

        filename = f'{name}_leaf10_trees400.joblib'
        target_path = output_dir / filename
        joblib.dump(final_model, target_path, compress=3)

        file_bytes = target_path.read_bytes()
        model_hashes[filename] = hashlib.sha256(file_bytes).hexdigest()
        model_parameters[filename] = final_model.get_params()

    return model_hashes, model_parameters


def generate_markdown_report(
    output_dir: Path,
    source_path: Path,
    total_rows: int,
    dev_rows: int,
    ordered_summary: pd.DataFrame,
) -> Path:
    """Gera o relatório descritivo sixth_training_report.md com a tabela de resultados."""
    rows_total_str = f'{total_rows:,}'.replace(',', '.')
    rows_dev_str = f'{dev_rows:,}'.replace(',', '.')

    table_header = (
        '| Estratégia | PR-AUC média | Brier médio | Sensibilidade média | F1 médio |\n'
        '|---|---:|---:|---:|---:|\n'
    )
    table_rows = '\n'.join(
        f"| {row['strategy']} | {row['pr_auc_mean']:.5f} | {row['brier_mean']:.5f} | "
        f"{row['recall_at_0_5_mean']:.5f} | {row['f1_at_0_5_mean']:.5f} |"
        for _, row in ordered_summary.iterrows()
    )
    full_table = table_header + table_rows

    report_path = ROOT / 'reports' / 'training' / 'sixth_training_report.md'
    content = f"""# Relatório do sexto treinamento — v6

**Data:** {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}  
**Experimento:** `{output_dir.name}`  
**Script:** `scripts/train_v6.py`

## Objetivo

Comparar três Random Forests com a mesma estrutura e combinar suas probabilidades com quatro proporções previamente definidas. A intenção é verificar se a combinação equilibra a detecção de chuva e os falsos alarmes.

## Dados e procedimento

Fonte preparada: `{source_path.name}` ({rows_total_str} linhas, SHA-256 no manifesto). Foram usadas {rows_dev_str} linhas até 31/12/2025 para desenvolvimento, sete atributos, quatro partições cronológicas (2022–2025) e três sementes ({', '.join(map(str, SEEDS))}). Cada partição respeita `target_time` na fronteira do ano. O período de 2026 não foi avaliado nem usado na seleção.

## Configurações

Todos os membros têm 400 árvores, folha mínima 10, `max_features=sqrt`, bootstrap habilitado, profundidade não limitada e demais parâmetros iguais. Variou apenas `class_weight`: sem pesos (`original`), `balanced` e `balanced_subsample`. Foram comparadas médias de probabilidades com pesos iguais (1/3 cada) e alternativas pré-definidas favorecendo cada família.

## Resultados

Médias e desvios-padrão sobre anos e sementes; limiar fixo de 0,50 para métricas de classificação.

{full_table}

PR-AUC é a métrica primária descritiva; Brier e métricas de erro ajudam a interpretar a qualidade probabilística e o compromisso operacional. As combinações foram comparadas nas mesmas partições e previsões fora da amostra. A melhor média não é prova de superioridade futura; não houve definição de custos relativos entre falso alarme e chuva não detectada.

## Artefatos e limites

O experimento contém três joblibs finais ajustados somente até 2025, `manifest.json` com parâmetros e hashes, métricas por partição/semente, resumo das estratégias e previsões fora da amostra. Não foram gravados resultados em PDF. O teste retrospectivo de 2026 foi deliberadamente preservado; já foi consultado em ciclos anteriores e não é cego. Para uma decisão operacional, definir custo/limiar usando desenvolvimento e avaliar em dados futuros ainda não consultados.
"""
    report_path.write_text(content, encoding='utf-8')
    return report_path


def run(source: Path, out: Path) -> None:
    """Função principal de orquestração do treinamento v6."""
    source_path = Path(source).resolve()
    output_dir = Path(out).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()

    if not output_dir.is_relative_to(experiments_root) or output_dir.exists():
        raise ValueError('Saída deve ser nova e estar dentro de data/experiments')

    # Carrega a base processada e separa a janela de desenvolvimento (< 2026)
    frame = load_table(source_path)
    dev_data = frame[frame.target_time < DEV_END].copy()

    # 1. Validação cruzada temporal
    metric_rows, prediction_frames = run_cross_validation(dev_data)

    output_dir.mkdir(parents=True)

    # 2. Gravação de previsões OOF e métricas por fold/semente
    metrics_df = pd.DataFrame(metric_rows)
    metrics_df.to_csv(output_dir / 'metrics_by_fold_seed.csv', index=False)

    oof_predictions_df = pd.concat(prediction_frames, ignore_index=True)
    oof_predictions_df.to_csv(output_dir / 'predictions_oof.csv', index=False)

    # 3. Resumo agregado de estratégias (média e desvio padrão)
    summary_df = metrics_df.groupby('strategy')[METRIC_COLS].agg(['mean', 'std'])
    summary_df.columns = [f'{col}_{stat}' for col, stat in summary_df.columns]
    summary_flat = summary_df.reset_index()
    summary_flat.to_csv(output_dir / 'strategy_summary.csv', index=False)

    # 4. Treinamento dos modelos finais para implantação
    model_hashes, final_model_params = train_final_models(dev_data, output_dir)

    # 5. Manifesto do experimento
    manifest = {
        'experiment': 'train_v6_weighted_random_forest_ensemble',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'pandas': pd.__version__,
        'numpy': np.__version__,
        'scikit_learn': sklearn.__version__,
        'joblib': joblib.__version__,
        'source_path': str(source_path),
        'source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
        'source_rows': len(frame),
        'development_rows_before_2026': len(dev_data),
        'features': FEATURES,
        'target': TARGET,
        'cv_years': list(CV_YEARS),
        'seeds': list(SEEDS),
        'split_method': 'expanding chronological folds; target_time constrained within year',
        'member_parameters': {
            name: {**PARAMS, **cw} for name, cw in MODELS.items()
        },
        'ensemble_weights': WEIGHTS,
        'selection_rule': (
            'descriptive comparison by mean PR-AUC; Brier as probability-quality companion; '
            'no operational winner without error-cost definition'
        ),
        'test_2026_used': False,
        'test_evaluated': False,
        'test_used_for_selection': False,
        'independent_blind_test': False,
        'final_models_trained_on_development_only': final_model_params,
        'model_sha256': model_hashes,
        'outputs': [
            'metrics_by_fold_seed.csv',
            'strategy_summary.csv',
            'predictions_oof.csv',
        ],
    }
    (output_dir / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding='utf-8',
    )

    # 6. Sumário estruturado em JSON
    (output_dir / 'experiment_summary.json').write_text(
        summary_flat.to_json(orient='records', force_ascii=False, indent=2),
        encoding='utf-8',
    )

    # 7. Relatório descritivo em Markdown
    ordered_summary = summary_flat.sort_values(
        ['pr_auc_mean', 'brier_mean'], ascending=[False, True]
    )
    report_path = generate_markdown_report(
        output_dir, source_path, len(frame), len(dev_data), ordered_summary
    )

    print(
        json.dumps(
            {
                'output': str(output_dir),
                'report': str(report_path),
                'top': ordered_summary.iloc[0].to_dict(),
            },
            ensure_ascii=False,
            default=str,
        ),
        flush=True,
    )


if __name__ == '__main__':
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=cfg['training'])
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=ROOT / 'data' / 'experiments' / (
            'weather_v6_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        ),
    )
    args = parser.parse_args()
    run(args.input, args.output_dir)
