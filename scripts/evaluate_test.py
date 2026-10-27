
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Adiciona a raiz do projeto ao caminho de busca do Python
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)

from config import WEATHER_FEATURES, settings


# Pasta do experimento já treinado
EXPERIMENT = ROOT / "data" / "experiments" / "weather_20261027T173216Z"
TARGET = "rain_next_hour"


def main():
    # Verifica o manifesto do experimento
    manifest_path = EXPERIMENT / "manifest.json"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifesto não encontrado: {manifest_path}"
        )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if manifest.get("test_evaluated"):
        raise RuntimeError(
            "O teste já está marcado como avaliado. "
            "Avaliação cancelada."
        )

    metrics_path = EXPERIMENT / "metrics_test.json"
    predictions_path = EXPERIMENT / "predictions_test.csv"

    if metrics_path.exists() or predictions_path.exists():
        raise FileExistsError(
            "Já existem arquivos de avaliação do teste. "
            "Verifique-os antes de continuar."
        )

    # Localiza a tabela utilizada no treinamento
    csv_path = Path(settings()["training"])

    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Tabela de treinamento não encontrada: {csv_path}"
        )

    # Confere se a tabela é a mesma utilizada no treinamento
    table_hash = hashlib.sha256(
        csv_path.read_bytes()
    ).hexdigest()

    expected_hash = manifest.get("training_source_sha256")

    if table_hash != expected_hash:
        raise RuntimeError(
            "O hash da tabela não confere com o manifesto. "
            "Avaliação cancelada."
        )

    # Carrega os dados
    df = pd.read_csv(csv_path)

    required_columns = [
        "time",
        "target_time",
        TARGET,
        *WEATHER_FEATURES,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Colunas ausentes na tabela: {missing_columns}"
        )

    df["time"] = pd.to_datetime(
        df["time"], utc=True, errors="raise"
    )
    df["target_time"] = pd.to_datetime(
        df["target_time"], utc=True, errors="raise"
    )

    # Período de teste definido no protocolo
    test_start = pd.Timestamp(
        "2026-01-01T00:00:00-03:00"
    ).tz_convert("UTC")

    test_end = pd.Timestamp(
        "2026-09-30T23:00:00-03:00"
    ).tz_convert("UTC")

    test = df[
        (df["time"] >= test_start)
        & (df["target_time"] <= test_end)
    ].copy()

    if test.empty:
        raise RuntimeError(
            "O conjunto de teste está vazio."
        )

    # Valida os dados usados na avaliação
    if test[required_columns].isnull().any().any():
        raise ValueError(
            "Existem valores ausentes nas colunas utilizadas no teste."
        )

    if not test[TARGET].isin([0, 1]).all():
        raise ValueError(
            f"O alvo {TARGET} deve conter somente 0 e 1."
        )

    X = test[list(WEATHER_FEATURES)]
    y = test[TARGET].astype(int)

    if set(y.unique()) != {0, 1}:
        raise RuntimeError(
            "O teste precisa conter as classes 0 e 1."
        )

    # Prepara o arquivo de previsões
    predictions = test[
        ["time", "target_time", TARGET]
    ].copy()

    predictions.rename(
        columns={TARGET: "actual"},
        inplace=True,
    )

    results = {}

    # Avalia os modelos existentes, sem treiná-los novamente
    for name in ("baseline", "random_forest"):
        model_path = EXPERIMENT / f"{name}.joblib"

        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo não encontrado: {model_path}"
            )

        model = joblib.load(model_path)

        # Confere se o modelo espera as mesmas entradas
        if hasattr(model, "feature_names_in_"):
            if list(model.feature_names_in_) != list(WEATHER_FEATURES):
                raise ValueError(
                    f"As entradas esperadas por {name} "
                    "não correspondem às entradas configuradas."
                )

        predicted = model.predict(X)

        classes = list(model.classes_)

        if 1 not in classes:
            raise ValueError(
                f"O modelo {name} não possui a classe positiva 1."
            )

        positive_index = classes.index(1)

        probabilities = model.predict_proba(X)[
            :, positive_index
        ]

        # Calcula as métricas
        results[name] = {
            "accuracy": float(
                accuracy_score(y, predicted)
            ),
            "precision_rain": float(
                precision_score(
                    y, predicted,
                    pos_label=1,
                    zero_division=0,
                )
            ),
            "recall_rain": float(
                recall_score(
                    y, predicted,
                    pos_label=1,
                    zero_division=0,
                )
            ),
            "f1_rain": float(
                f1_score(
                    y, predicted,
                    pos_label=1,
                    zero_division=0,
                )
            ),
            "actual_rain": int(
                (y == 1).sum()
            ),
            "predicted_rain": int(
                (predicted == 1).sum()
            ),
            "confusion_matrix_labels_0_1": (
                confusion_matrix(
                    y, predicted, labels=[0, 1]
                ).tolist()
            ),
        }

        predictions[f"{name}_prediction"] = predicted
        predictions[
            f"{name}_probability_rain"
        ] = probabilities

    # Organiza as métricas finais
    metrics = {
        "evaluation_period": {
            "start": test_start.isoformat(),
            "target_end": test_end.isoformat(),
        },
        "rows": int(len(test)),
        "features": list(WEATHER_FEATURES),
        "target": TARGET,
        "models": results,
    }

    # Salva os resultados antes de atualizar o manifesto
    metrics_path.write_text(
        json.dumps(
            metrics,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    predictions.to_csv(
        predictions_path,
        index=False,
    )

    # Registra que a avaliação foi realizada
    manifest["test_evaluated"] = True
    manifest["test_evaluation_completed_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Exibe o resumo
    print("Avaliação concluída.")
    print("Registros avaliados:", len(test))
    print("Período inicial:", test["time"].min())
    print("Último horário do alvo:", test["target_time"].max())
    print("Métricas:", metrics_path)
    print("Previsões:", predictions_path)

    for name, values in results.items():
        print(f"\n{name}:")
        print(
            json.dumps(
                values,
                indent=2,
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
