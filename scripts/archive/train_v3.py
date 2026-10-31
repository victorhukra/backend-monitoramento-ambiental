# Script original arquivado - preservado para referência

"""Treinamento experimental para prever chuva na próxima hora (v3).

Usa quatro variáveis meteorológicas em T para prever rain_next_hour.
A divisão dos dados é cronológica.

Mudanças em relação ao train.py original (todas aditivas):
- mantém `evaluate(model, X, y)`, os nomes `baseline` e `random_forest`,
  o formato de metrics_validation.json e as chaves antigas do manifest;
- adiciona os modelos baseline_prior, logistic e random_forest_balanced;
- adiciona métricas por probabilidade (PR-AUC, ROC-AUC, Brier, log loss);
- grava uma tabela de limiares (precisão/recall por limiar) em vez de
  decidir sozinho, porque o custo de alarme falso x chuva perdida ainda
  não foi definido;
- compara a validação nos mesmos meses do teste (o teste cobre jan-set);
- validação cruzada cronológica por ano (expansão da janela de treino);
- importância das variáveis por permutação na validação.

ATENÇÃO: o teste de janeiro a setembro de 2026 já foi avaliado uma vez
(27/10/2026). Ele não deve orientar nenhuma escolha nova. Escolhas de
modelo e de limiar devem usar apenas a validação e a validação cruzada.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    fbeta_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Permite executar o script diretamente a partir da pasta scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ROOT, WEATHER_FEATURES, settings

try:
    from config import WEATHER_TIMEZONE
except ImportError:
    WEATHER_TIMEZONE = 'America/Sao_Paulo'


TARGET = 'rain_next_hour'
TRAIN_END = pd.Timestamp('2025-01-01T00:00:00-03:00')
VALIDATION_END = pd.Timestamp('2026-01-01T00:00:00-03:00')

# Grade para o limiar provisório e limiares mostrados na tabela.
THRESHOLD_GRID = np.round(np.arange(0.05, 0.951, 0.01), 2)
TABLE_THRESHOLDS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]

# Anos usados como validação na validação cruzada cronológica. Cada ano é
# previsto por um modelo treinado apenas com os anos anteriores.
CV_VALIDATION_YEARS = [2023, 2024, 2025]

TEST_ALREADY_USED_NOTE = (
    'O teste de janeiro a setembro de 2026 ja foi avaliado em 27/10/2026. '
    'Nao e mais um conjunto independente para escolher modelo ou limiar.'
)


def load_table(path):
    """Carrega e valida a tabela preparada, sem alterar o arquivo original."""
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

    # UTC permite comparar horários mesmo que tenham offsets diferentes.
    for column in ['time', 'target_time']:
        frame[column] = pd.to_datetime(
            frame[column], errors='raise', utc=True
        )
        if frame[column].isna().any():
            raise ValueError(f'Timestamp ausente em {column}')

    if frame['time'].duplicated().any():
        raise ValueError('Existem timestamps duplicados')

    # O alvo deve conter apenas 0 e 1.
    target = pd.to_numeric(frame[TARGET], errors='raise')
    if target.isna().any() or not target.isin([0, 1]).all():
        raise ValueError(f'{TARGET} deve conter apenas 0 e 1')
    frame[TARGET] = target.astype('int8')

    # Não fazemos imputação nem inventamos valores para dados inválidos.
    for column in WEATHER_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors='raise')

    features = frame[list(WEATHER_FEATURES)].to_numpy(dtype=float)
    if not np.isfinite(features).all():
        raise ValueError('Há valores ausentes ou não finitos nas variáveis')

    # Confirma que cada alvo corresponde exatamente a T + 1 hora.
    expected_target_time = frame['time'] + pd.Timedelta(hours=1)
    if not frame['target_time'].eq(expected_target_time).all():
        raise ValueError('target_time não corresponde exatamente a time + 1h')

    return frame.sort_values('time').reset_index(drop=True)


def local_month(series):
    """Mês no fuso local, para comparar períodos sazonalmente."""
    return series.dt.tz_convert(WEATHER_TIMEZONE).dt.month


def prevalence(part):
    """Resume linhas, linhas com chuva, taxa de chuva e meses cobertos."""
    rain = int((part[TARGET] == 1).sum())
    has_rows = len(part) > 0
    return {
        'rows': int(len(part)),
        'rain_rows': rain,
        'rain_rate': float(rain / len(part)) if has_rows else None,
        'first_time': part['time'].min().isoformat() if has_rows else None,
        'last_time': part['time'].max().isoformat() if has_rows else None,
        'months_covered_local': (
            sorted(int(m) for m in local_month(part['time']).unique())
            if has_rows else []
        ),
    }


def split_data(frame):
    """Separa treino, validação e teste respeitando a ordem temporal."""
    train_end = TRAIN_END.tz_convert('UTC')
    validation_end = VALIDATION_END.tz_convert('UTC')

    time = frame['time']
    target_time = frame['target_time']

    # Treino: tanto a entrada quanto o alvo devem estar antes de 2025.
    train_mask = (
        (time < train_end)
        & (target_time < train_end)
    )

    # Validação: entrada e alvo devem permanecer dentro de 2025.
    validation_mask = (
        (time >= train_end)
        & (time < validation_end)
        & (target_time < validation_end)
    )

    # Teste: começa em 2026.
    test_mask = time >= validation_end

    train = frame.loc[train_mask].copy()
    validation = frame.loc[validation_mask].copy()
    test = frame.loc[test_mask].copy()

    if train.empty or validation.empty or test.empty:
        raise ValueError(
            'Uma das divisões ficou vazia; confira as datas da tabela'
        )

    # As divisões não podem compartilhar registros.
    if train.index.intersection(validation.index).size:
        raise ValueError('Há registros compartilhados entre treino e validação')
    if train.index.intersection(test.index).size:
        raise ValueError('Há registros compartilhados entre treino e teste')
    if validation.index.intersection(test.index).size:
        raise ValueError('Há registros compartilhados entre validação e teste')

    summary = {
        'train_rows': len(train),
        'validation_rows': len(validation),
        'test_rows': len(test),
        'excluded_boundary_rows': (
            len(frame) - len(train) - len(validation) - len(test)
        ),
        'train_before': TRAIN_END.isoformat(),
        'validation_before': VALIDATION_END.isoformat(),
        'test_from': VALIDATION_END.isoformat(),
        'features': list(WEATHER_FEATURES),
        'target': TARGET,
        'split_method': 'chronological',
        'prevalence': {
            'train': prevalence(train),
            'validation': prevalence(validation),
            'test': prevalence(test),
        },
    }

    return train, validation, test, summary


def evaluate(model, X, y):
    """Calcula métricas binárias, tratando chuva como classe positiva.

    Mantida com a mesma assinatura e compatível com train.py original.
    """
    predictions = model.predict(X)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

    return {
        'accuracy': float(accuracy_score(y, predictions)),
        'precision_rain': float(
            precision_score(y, predictions, zero_division=0)
        ),
        'recall_rain': float(
            recall_score(y, predictions, zero_division=0)
        ),
        'f1_rain': float(
            f1_score(y, predictions, zero_division=0)
        ),
        'balanced_accuracy': float(balanced_accuracy_score(y, predictions)),
        'specificity': specificity,
        'matthews_corrcoef': float(matthews_corrcoef(y, predictions)),
        'actual_rain': int(np.sum(np.asarray(y) == 1)),
        'predicted_rain': int(np.sum(predictions == 1)),
        'confusion_matrix_labels_0_1': [
            [int(tn), int(fp)],
            [int(fn), int(tp)],
        ],
    }


def positive_probability(model, X):
    """Retorna a probabilidade da classe 1, sem presumir sua posição."""
    probabilities = model.predict_proba(X)
    positive_index = list(model.classes_).index(1)
    return probabilities[:, positive_index]


def probability_metrics(y, proba):
    """Métricas que não dependem de limiar."""
    y = np.asarray(y)
    proba = np.asarray(proba, dtype=float)
    result = {
        'brier': float(brier_score_loss(y, proba)),
        'log_loss': float(
            log_loss(y, np.clip(proba, 1e-15, 1 - 1e-15), labels=[0, 1])
        ),
        'roc_auc': None,
        'pr_auc': None,
    }
    # As AUCs só existem se o conjunto tiver as duas classes.
    if len(np.unique(y)) == 2:
        result['roc_auc'] = float(roc_auc_score(y, proba))
        result['pr_auc'] = float(average_precision_score(y, proba))
    return result


def threshold_metrics(y, proba, threshold):
    """Métricas binárias com decisão positiva se proba >= limiar.

    Pode diferir de model.predict() apenas em empates exatos de 0,5.
    """
    y = np.asarray(y)
    predictions = (np.asarray(proba) >= threshold).astype(int)

    return {
        'threshold': float(threshold),
        'accuracy': float(accuracy_score(y, predictions)),
        'precision_rain': float(
            precision_score(y, predictions, zero_division=0)
        ),
        'recall_rain': float(
            recall_score(y, predictions, zero_division=0)
        ),
        'f1_rain': float(f1_score(y, predictions, zero_division=0)),
        'actual_rain': int(np.sum(y == 1)),
        'predicted_rain': int(np.sum(predictions == 1)),
        'confusion_matrix_labels_0_1': confusion_matrix(
            y, predictions, labels=[0, 1]
        ).tolist(),
    }


def threshold_table(y, proba, extra=()):
    """Precisão e recall por limiar, para decidir conforme o custo."""
    values = sorted({*TABLE_THRESHOLDS, *[round(float(t), 2) for t in extra]})
    rows = []
    for threshold in values:
        metrics = threshold_metrics(y, proba, threshold)
        rows.append({
            key: metrics[key]
            for key in (
                'threshold', 'precision_rain', 'recall_rain',
                'f1_rain', 'predicted_rain',
            )
        })
    return rows


def choose_threshold(y, proba, beta=1.0):
    """Limiar PROVISÓRIO que maximiza F-beta da chuva na validação.

    beta=1 pesa precisão e recall igualmente; beta>1 favorece recall.
    A escolha definitiva depende do custo de alarme falso x chuva perdida.
    """
    y = np.asarray(y)
    best_threshold, best_score = 0.5, -1.0
    for threshold in THRESHOLD_GRID:
        predictions = (np.asarray(proba) >= threshold).astype(int)
        score = fbeta_score(y, predictions, beta=beta, zero_division=0)
        if score > best_score:
            best_threshold, best_score = float(threshold), float(score)
    return best_threshold


def build_models():
    """Baselines e modelos candidatos.
    Inclui versões mais robustas dos Random Forests para teste mais pesado.
    """
    return {
        'baseline': DummyClassifier(strategy='constant', constant=0),
        # Random Forest original – parâmetros aumentados para maior carga computacional.
        'random_forest': RandomForestClassifier(
            n_estimators=500,
            max_depth=None,  # deixar árvore crescer até pureza
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            class_weight=None,
        ),
        # Prevê sempre a taxa-base de chuva do treino (dá probabilidade).
        'baseline_prior': DummyClassifier(strategy='prior'),
        'logistic': make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, random_state=42),
        ),
        # Random Forest balanceado – também com parâmetros mais exigentes.
        'random_forest_balanced': RandomForestClassifier(
            n_estimators=500,
            max_depth=None,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            class_weight='balanced_subsample',
        ),
    }


def rolling_year_cv(frame, models, features):
    """Validação cruzada cronológica: cada ano é previsto só com o passado.

    Usa apenas dados de treino e validação (alvo antes de 2026).
    """
    cutoff = VALIDATION_END.tz_convert('UTC')
    dev = frame[frame['target_time'] < cutoff]

    folds = {}
    collected = {name: [] for name in models}

    for year in CV_VALIDATION_YEARS:
        start = pd.Timestamp(
            f'{year}-01-01', tz=WEATHER_TIMEZONE
        ).tz_convert('UTC')
        end = pd.Timestamp(
            f'{year + 1}-01-01', tz=WEATHER_TIMEZONE
        ).tz_convert('UTC')

        fold_train = dev[dev['target_time'] < start]
        fold_val = dev[(dev['time'] >= start) & (dev['target_time'] < end)]

        if (
            fold_train.empty or fold_val.empty
            or fold_train[TARGET].nunique() < 2
            or fold_val[TARGET].nunique() < 2
        ):
            folds[str(year)] = {
                'skipped': 'dados insuficientes ou classe única'
            }
            continue

        entry = {
            'train_rows': int(len(fold_train)),
            'validation_rows': int(len(fold_val)),
            'validation_rain_rate': float(fold_val[TARGET].mean()),
        }
        for name, model in models.items():
            fitted = clone(model).fit(
                fold_train[features], fold_train[TARGET]
            )
            proba = positive_probability(fitted, fold_val[features])
            prob = probability_metrics(fold_val[TARGET], proba)
            thr = threshold_metrics(fold_val[TARGET], proba, 0.5)
            row = {
                'pr_auc': prob['pr_auc'],
                'roc_auc': prob['roc_auc'],
                'brier': prob['brier'],
                'precision_rain_at_0.5': thr['precision_rain'],
                'recall_rain_at_0.5': thr['recall_rain'],
                'f1_rain_at_0.5': thr['f1_rain'],
            }
            entry[name] = row
            collected[name].append(row)
        folds[str(year)] = entry

    summary = {}
    for name, rows in collected.items():
        if not rows:
            continue
        summary[name] = {
            metric: {
                'mean': float(np.mean([row[metric] for row in rows])),
                'std': float(np.std([row[metric] for row in rows])),
            }
            for metric in rows[0]
        }

    return {
        'validation_years': CV_VALIDATION_YEARS,
        'folds': folds,
        'summary_mean_std': summary,
    }


def validation_importance(models, X, y, features):
    """Importância por permutação (queda de PR-AUC) na validação."""
    if y.nunique() < 2:
        return {}
    importance = {}
    for name in ('random_forest', 'random_forest_balanced', 'logistic'):
        result = permutation_importance(
            models[name], X, y,
            scoring='average_precision',
            n_repeats=5,
            random_state=42,
            n_jobs=1,
        )
        importance[name] = {
            feature: {
                'mean': float(result.importances_mean[i]),
                'std': float(result.importances_std[i]),
            }
            for i, feature in enumerate(features)
        }
    return importance


def run(training_path, output_dir, evaluate_test=False,
        beta=1.0, rolling_cv=True):
    """Treina os modelos e salva resultados em uma nova pasta de experimento."""
    training_path = Path(training_path).resolve()
    output_dir = Path(output_dir).resolve()
    experiments_root = (ROOT / 'data' / 'experiments').resolve()

    if not output_dir.is_relative_to(experiments_root):
        raise ValueError('A saída deve ficar dentro de data/experiments')

    if output_dir.exists():
        raise ValueError('A pasta de saída já existe; escolha outra')

    frame = load_table(training_path)
    train, validation, test, split_summary = split_data(frame)

    # Somente as quatro variáveis meteorológicas entram no modelo.
    features = list(WEATHER_FEATURES)
    X_train = train[features]
    y_train = train[TARGET]
    X_validation = validation[features]
    y_validation = validation[TARGET]

    if y_train.nunique() < 2:
        raise ValueError('O treino precisa ter as duas classes')

    models = build_models()
    output_dir.mkdir(parents=True)

    # Mesmo formato do original: limiar 0,5, métricas planas por modelo.
    metrics_validation = {}
    extended = {}
    thresholds = {}
    probabilities = {}
    predictions_validation = validation[
        ['time', 'target_time', TARGET]
    ].copy()

    for name, model in models.items():
        model.fit(X_train, y_train)

        # Salva o modelo treinado para uso posterior.
        joblib.dump(model, output_dir / f'{name}.joblib')

        metrics_validation[name] = evaluate(
            model, X_validation, y_validation
        )

        proba = positive_probability(model, X_validation)
        probabilities[name] = proba
        thresholds[name] = choose_threshold(y_validation, proba, beta)

        extended[name] = {
            **probability_metrics(y_validation, proba),
            'provisional_threshold': thresholds[name],
            'at_provisional_threshold': threshold_metrics(
                y_validation, proba, thresholds[name]
            ),
            'threshold_table': threshold_table(
                y_validation, proba, extra=[thresholds[name]]
            ),
        }

        # Guarda probabilidades para permitir análises posteriores.
        predictions_validation[f'{name}_probability_rain'] = proba
        predictions_validation[f'{name}_prediction'] = model.predict(
            X_validation
        )

    # Validação nos mesmos meses do teste (o teste não cobre o ano todo).
    test_months = sorted(int(m) for m in local_month(test['time']).unique())
    month_mask = local_month(validation['time']).isin(test_months).to_numpy()
    same_months = {
        'months_local': test_months,
        'rows': int(month_mask.sum()),
        'rain_rate': (
            float(y_validation.to_numpy()[month_mask].mean())
            if month_mask.any() else None
        ),
        'models': {},
    }
    if month_mask.any():
        y_sub = y_validation.to_numpy()[month_mask]
        for name, proba in probabilities.items():
            same_months['models'][name] = {
                **probability_metrics(y_sub, proba[month_mask]),
                'at_0.5': threshold_metrics(y_sub, proba[month_mask], 0.5),
            }

    cv_results = (
        rolling_year_cv(frame, models, features) if rolling_cv
        else {'skipped': 'desativada pelo usuário'}
    )

    importance = validation_importance(
        models, X_validation, y_validation, features
    )

    split_summary.update({
        'total_rows': len(frame),
        'training_source': str(training_path),
        'training_source_sha256': hashlib.sha256(
            training_path.read_bytes()
        ).hexdigest(),
    })

    manifest = {
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'pandas': pd.__version__,
        'numpy': np.__version__,
        'scikit_learn': __import__('sklearn').__version__,
        'joblib': joblib.__version__,
        'features': features,
        'target': TARGET,
        'threshold': 0.5,
        'random_forest_parameters': models['random_forest'].get_params(),
        'models_trained': list(models),
        'provisional_thresholds_validation': thresholds,
        'provisional_threshold_beta': beta,
        'provisional_threshold_note': (
            'Limiar escolhido e avaliado na mesma validacao, entao e '
            'otimista. A decisao definitiva depende do custo de alarme '
            'falso x chuva perdida, ainda nao definido.'
        ),
        'rolling_cv': rolling_cv,
        'test_evaluated': evaluate_test,
        'test_already_used_note': TEST_ALREADY_USED_NOTE,
        'note': (
            'Experimento retrospectivo. A semântica temporal da chuva '
            'e a disponibilidade operacional das entradas não foram confirmadas.'
        ),
    }

    def dump(name, payload):
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding='utf-8',
        )

    dump('split_summary.json', split_summary)
    dump('manifest.json', manifest)
    dump('metrics_validation.json', metrics_validation)
    dump('metrics_validation_extended.json', {
        'beta': beta,
        'models': extended,
        'validation_same_months_as_test': same_months,
    })
    dump('rolling_cv.json', cv_results)
    dump('feature_importance_validation.json', importance)
    predictions_validation.to_csv(
        output_dir / 'predictions_validation.csv', index=False
    )

    # O teste de jan-set/2026 já foi usado; este caminho só existe por
    # compatibilidade e não deve orientar novas escolhas.
    if evaluate_test:
        print(f'AVISO: {TEST_ALREADY_USED_NOTE}', file=sys.stderr)
        X_test = test[features]
        y_test = test[TARGET]
        metrics_test = {
            name: evaluate(model, X_test, y_test)
            for name, model in models.items()
        }
        dump('metrics_test.json', metrics_test)

    print(json.dumps({
        'output_dir': str(output_dir),
        'split': split_summary,
        'validation_metrics': metrics_validation,
        'provisional_thresholds': thresholds,
        'validation_same_months_as_test': same_months,
        'rolling_cv_summary': cv_results.get('summary_mean_std', cv_results),
        'test_evaluated': evaluate_test,
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=cfg['training'])
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=ROOT / 'data' / 'experiments' / (
            'weather_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        ),
    )
    parser.add_argument(
        '--evaluate-test',
        action='store_true',
        help=(
            'Avalia o teste. ATENÇÃO: jan-set/2026 já foi usado em '
            '27/10/2026; não use para escolher modelo ou limiar.'
        ),
    )
    parser.add_argument(
        '--beta',
        type=float,
        default=1.0,
        help='Peso do recall no limiar provisório (F-beta). 1 = F1.',
    )
    parser.add_argument(
        '--skip-cv',
        action='store_true',
        help='Pula a validação cruzada cronológica por ano (mais rápido).',
    )
    args = parser.parse_args()
    run(
        args.input,
        args.output_dir,
        args.evaluate_test,
        beta=args.beta,
        rolling_cv=not args.skip_cv,
    )
