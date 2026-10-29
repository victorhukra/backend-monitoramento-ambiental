
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from config import WEATHER_FEATURES, settings

EXPERIMENT = (
    ROOT / "data" / "experiments" / "weather_20261029T140207Z"
)
TARGET = "rain_next_hour"

MODELS = (
    "baseline",
    "random_forest",
    "baseline_prior",
    "logistic",
    "random_forest_balanced",
)


def probability_metrics(y, probabilities):
    result = {
        "brier": float(brier_score_loss(y, probabilities)),
        "log_loss": float(
            log_loss(
                y,
                np.clip(probabilities, 1e-15, 1 - 1e-15),
                labels=[0, 1],
            )
        ),
        "roc_auc": None,
        "pr_auc": None,
    }

    if len(np.unique(y)) == 2:
        result["roc_auc"] = float(
            roc_auc_score(y, probabilities)
        )
        result["pr_auc"] = float(
            average_precision_score(y, probabilities)
        )

    return result


def classification_metrics(y, probabilities, threshold):
    predicted = (probabilities >= threshold).astype(int)

    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y, predicted)),
        "precision_rain": float(
            precision_score(y, predicted, zero_division=0)
        ),
        "recall_rain": float(
            recall_score(y, predicted, zero_division=0)
        ),
        "f1_rain": float(
            f1_score(y, predicted, zero_division=0)
        ),
        "actual_rain": int((y == 1).sum()),
        "predicted_rain": int((predicted == 1).sum()),
        "confusion_matrix_labels_0_1": confusion_matrix(
            y, predicted, labels=[0, 1]
        ).tolist(),
    }


def main():
    manifest_path = EXPERIMENT / "manifest.json"
    split_path = EXPERIMENT / "split_summary.json"

    if not manifest_path.is_file() or not split_path.is_file():
        raise FileNotFoundError(
            "Manifesto ou resumo da divisão não encontrado."
        )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    split = json.loads(
        split_path.read_text(encoding="utf-8")
    )

    if manifest.get("test_evaluated"):
        raise RuntimeError(
            "O manifesto já indica que o teste foi avaliado. "
            "Confira os arquivos antes de executar novamente."
        )

    metrics_path = EXPERIMENT / "metrics_test.json"
    predictions_path = EXPERIMENT / "predictions_test.csv"

    if metrics_path.exists() or predictions_path.exists():
        raise FileExistsError(
            "Já existem arquivos de avaliação. "
            "Não serão sobrescritos."
        )

    expected_models = manifest.get("models_trained", [])
    if not set(MODELS).issubset(expected_models):
        raise ValueError(
            "O manifesto não registra todos os cinco modelos esperados."
        )

    csv_path = Path(settings()["training"])
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path
    csv_path = csv_path.resolve()

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Tabela não encontrada: {csv_path}"
        )

    actual_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    expected_hash = split.get("training_source_sha256")

    if not expected_hash or actual_hash != expected_hash:
        raise RuntimeError(
            "O hash da tabela não corresponde ao split_summary.json."
        )

    df = pd.read_csv(csv_path)

    required = [
        "time", "target_time", TARGET, *WEATHER_FEATURES
    ]
    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")

    for col in ("time", "target_time"):
        df[col] = pd.to_datetime(
            df[col], utc=True, errors="raise"
        )

    # Mesmo período de teste definido no protocolo do projeto.
    test_start = pd.Timestamp(
        "2026-01-01T00:00:00-03:00"
    ).tz_convert("UTC")
    test_end = pd.Timestamp(
        "2026-09-30T23:00:00-03:00"
    ).tz_convert("UTC")

    test = df.loc[
        (df["time"] >= test_start)
        & (df["target_time"] <= test_end)
    ].copy().sort_values("time")

    if len(test) != split["test_rows"]:
        raise ValueError(
            f"Quantidade de teste inesperada: {len(test)}; "
            f"esperado: {split['test_rows']}."
        )

    if test[required].isnull().any().any():
        raise ValueError("Há valores ausentes no conjunto de teste.")

    X = test[list(WEATHER_FEATURES)]
    if not np.isfinite(X.to_numpy(dtype=float)).all():
        raise ValueError("Há entradas não finitas no conjunto de teste.")

    if not test[TARGET].isin([0, 1]).all():
        raise ValueError("O alvo deve conter somente 0 e 1.")

    y = test[TARGET].astype(int).to_numpy()

    if set(np.unique(y)) != {0, 1}:
        raise ValueError("O teste precisa conter as duas classes.")

    thresholds = manifest.get(
        "provisional_thresholds_validation", {}
    )

    predictions = test[
        ["time", "target_time", TARGET]
    ].rename(columns={TARGET: "actual"}).copy()

    results = {}

    for name in MODELS:
        model_path = EXPERIMENT / f"{name}.joblib"

        if not model_path.is_file():
            raise FileNotFoundError(
                f"Modelo não encontrado: {model_path}"
            )

        model = joblib.load(model_path)

        if hasattr(model, "feature_names_in_"):
            if list(model.feature_names_in_) != list(WEATHER_FEATURES):
                raise ValueError(
                    f"Entradas incompatíveis no modelo {name}."
                )

        if not hasattr(model, "predict_proba"):
            raise ValueError(
                f"O modelo {name} não oferece predict_proba."
            )

        classes = list(model.classes_)
        if 1 not in classes:
            raise ValueError(
                f"O modelo {name} não possui a classe positiva 1."
            )

        probabilities = model.predict_proba(X)[
            :, classes.index(1)
        ]

        if not np.isfinite(probabilities).all():
            raise ValueError(
                f"Probabilidades inválidas no modelo {name}."
            )

        if name not in thresholds:
            raise ValueError(
                f"Limiar de validação ausente para {name}."
            )

        threshold = float(thresholds[name])

        results[name] = {
            "probability_metrics": probability_metrics(
                y, probabilities
            ),
            "at_threshold_0_5": classification_metrics(
                y, probabilities, 0.5
            ),
            "at_provisional_validation_threshold": (
                classification_metrics(y, probabilities, threshold)
            ),
        }

        predictions[f"{name}_probability_rain"] = probabilities
        predictions[f"{name}_prediction_0_5"] = (
            probabilities >= 0.5
        ).astype(int)
        predictions[f"{name}_prediction_validation_threshold"] = (
            probabilities >= threshold
        ).astype(int)

    metrics = {
        "evaluation_type": "retrospective_comparison",
        "independent_test": False,
        "reason": (
            "O período de janeiro a setembro de 2026 já foi "
            "avaliado no primeiro experimento em 27/10/2026."
        ),
        "evaluation_period": {
            "start": test_start.isoformat(),
            "target_end": test_end.isoformat(),
        },
        "rows": int(len(test)),
        "features": list(WEATHER_FEATURES),
        "target": TARGET,
        "training_source_sha256": actual_hash,
        "models": results,
    }

    # Salva os resultados antes de atualizar o manifesto.
    metrics_path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    predictions.to_csv(predictions_path, index=False)

    manifest["test_evaluated"] = True
    manifest["test_evaluation_completed_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )
    manifest["test_evaluation_type"] = "retrospective_comparison"
    manifest["test_evaluation_independent"] = False

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("Avaliação retrospectiva concluída.")
    print("Registros:", len(test))
    print("Métricas:", metrics_path)
    print("Previsões:", predictions_path)

    for name, result in results.items():
        print(f"\n{name}")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
