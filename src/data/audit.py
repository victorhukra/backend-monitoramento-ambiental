"""Auditoria somente de leitura e prova de conceito de uma imagem GOES."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys
import zipfile

import numpy as np
import pandas as pd


def fingerprint(path):
    stat = path.stat()
    result = {"path": str(path.resolve()), "bytes": stat.st_size,
              "mtime_ns": stat.st_mtime_ns}
    # Não ler 79 GB só para calcular um hash nesta etapa.
    if stat.st_size <= 32 * 1024**2:
        result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def stats(values):
    values = np.asarray(values)
    if not values.size:
        raise ValueError("Nenhum pixel válido para calcular estatísticas.")
    return {"mean": float(values.mean()), "std_ddof0": float(values.std()),
            "min": float(values.min()), "max": float(values.max()),
            "median": float(np.median(values))}


def scalar(data, key):
    value = np.asarray(data[key])
    if value.size != 1:
        raise ValueError(f"Metadado {key} deveria conter um único valor: {value.shape}")
    value = value.item()
    return value.decode("utf-8") if isinstance(value, bytes) else value


def inspect_npz(payload, csv_time):
    result = {"warnings": []}
    with np.load(io.BytesIO(payload), allow_pickle=False) as data:
        result["keys"] = data.files
        keys = ["scale_factor", "add_offset", "fill_value", "units", "timestamp_utc",
                "satellite", "source_filename", "source_key", "grid_signature"]
        metadata = {key: scalar(data, key) for key in keys if key in data}
        result["metadata"] = metadata
        result["missing_metadata"] = [key for key in keys if key not in data]
        if "cmi_c13_raw" not in data:
            raise ValueError("NPZ sem a matriz cmi_c13_raw.")
        raw = data["cmi_c13_raw"]
        if raw.ndim != 2 or raw.dtype.kind not in "iuf":
            raise ValueError(f"Matriz não numérica ou não bidimensional: {raw.shape}, {raw.dtype}")
        finite = np.isfinite(raw)
        fill = metadata.get("fill_value")
        fill_mask = raw == fill if fill is not None else np.zeros(raw.shape, dtype=bool)
        valid = finite & ~fill_mask
        result.update(shape=list(raw.shape), dtype=str(raw.dtype), pixels=int(raw.size),
                      nonfinite=int((~finite).sum()), fill_pixels=int(fill_mask.sum()),
                      valid_pixels=int(valid.sum()), invalid_pixels=int((~valid).sum()),
                      raw_range_including_fill=stats(raw[finite]), raw_valid=stats(raw[valid]))
        # Sem informação sobre fill, não afirmar que os pixels finitos são válidos.
        if all(key in metadata for key in ("scale_factor", "add_offset", "fill_value", "units")):
            scale, offset = float(metadata["scale_factor"]), float(metadata["add_offset"])
            if not np.isfinite([scale, offset]).all():
                raise ValueError("Escala ou offset não finito.")
            physical = raw[valid].astype(np.float64) * scale + offset
            if not np.isfinite(physical).all():
                raise ValueError("A reconstrução gerou valores não finitos.")
            result["transformation"] = "raw * scale_factor + add_offset; máscara aplicada antes"
            result["physical"] = stats(physical)
            if str(metadata["units"]).strip().lower() in {"k", "kelvin"}:
                result["celsius"] = stats(physical - 273.15)
        else:
            result["warnings"].append("Reconstrução não executada: metadados insuficientes para escala/unidade/máscara.")
        local = pd.Timestamp(csv_time)
        if local.tzinfo is None:
            local = local.tz_localize("America/Sao_Paulo", ambiguous="raise", nonexistent="raise")
        utc = local.tz_convert("UTC")
        result["csv_local"] = str(local)
        result["csv_utc"] = str(utc)
        if "timestamp_utc" in metadata:
            capture = pd.Timestamp(metadata["timestamp_utc"])
            if capture.tzinfo is not None and capture.utcoffset().total_seconds() != 0:
                result["warnings"].append("Apesar do nome timestamp_utc, o valor usa offset não UTC. Offset explícito respeitado na conversão; divergência com a descrição do README.")
            if capture.tzinfo is None:
                result["warnings"].append("timestamp_utc sem offset explícito: interpretado como UTC conforme chave e README.")
                capture = capture.tz_localize("UTC")
            capture = capture.tz_convert("UTC")
            result["capture_utc"] = str(capture)
            result["capture_minus_csv_seconds"] = (capture - utc).total_seconds()
        else:
            result["warnings"].append("Sem timestamp_utc: comparação temporal indisponível.")
    return result


def audit(csv_path, zip_path, readme_path, extra_sources=()):
    paths = [csv_path, zip_path, readme_path, *extra_sources]
    before = [fingerprint(path) for path in paths]
    if csv_path.stat().st_size > 128 * 1024**2:
        raise ValueError("CSV acima do limite de 128 MiB desta auditoria; adaptar para leitura em blocos.")
    df = pd.read_csv(csv_path)
    if not {"time", "image_link"}.issubset(df.columns):
        raise ValueError("CSV precisa conter time e image_link.")
    time = pd.to_datetime(df["time"], errors="coerce", format="ISO8601")
    unique_time = pd.DatetimeIndex(time.dropna().unique()).sort_values()
    if unique_time.empty:
        raise ValueError("CSV sem timestamps interpretáveis.")
    expected = pd.date_range(unique_time.min(), unique_time.max(), freq="h")
    missing = expected.difference(unique_time)
    links = df["image_link"].dropna().astype(str)
    links = links[links.str.strip().ne("")]
    summary = {
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "pandas": pd.__version__, "numpy": np.__version__},
        "sources_before": before,
        "csv": {"rows": len(df), "columns": len(df.columns),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "missing": df.isna().sum().astype(int).to_dict(),
                "numeric": df.select_dtypes(include="number").columns.tolist(),
                "non_numeric": df.select_dtypes(exclude="number").columns.tolist(),
                "infinite_numeric": {col: int(np.isinf(df[col]).sum()) for col in df.select_dtypes(include="number")},
                "duplicate_rows_extra": int(df.duplicated().sum()),
                "duplicate_timestamps_extra": int(time.dropna().duplicated().sum()),
                "unparseable_times": int(time.isna().sum()),
                "time_min": str(unique_time.min()), "time_max": str(unique_time.max()),
                "time_monotonic": bool(time.is_monotonic_increasing),
                "time_format_iso_seconds": int(df["time"].astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}").sum()),
                "off_hour": int((unique_time != unique_time.floor("h")).sum()),
                "consecutive_deltas": {str(k): int(v) for k, v in time.diff().value_counts().items()},
                "missing_hours": len(missing), "missing_hours_examples": missing[:20].astype(str).tolist(),
                "links_filled": len(links), "links_missing": len(df)-len(links),
                "links_unique": int(links.nunique()),
                "reused_link_rows_extra": len(links) - int(links.nunique()),
                "reused_link_distinct": int((links.value_counts() > 1).sum()),
                "memory_bytes_deep": int(df.memory_usage(deep=True).sum()),
                "head": json.loads(df.head().to_json(orient="records")),
                "tail": json.loads(df.tail().to_json(orient="records"))}}
    with zipfile.ZipFile(zip_path, "r") as archive:
        entries = archive.infolist()
        files = [entry for entry in entries if not entry.is_dir()]
        by_name = {entry.filename: entry for entry in files}
        duplicates = [name for name, count in Counter(e.filename for e in files).items() if count > 1]
        npz = [entry for entry in files if entry.filename.lower().endswith(".npz")]
        matched = links.isin(by_name)
        referenced = set(links)
        dates = [re.search(r"samples/(\d{4}/\d{2}/\d{2})/", entry.filename) for entry in npz]
        dates = [match.group(1) for match in dates if match]
        summary["zip"] = {
            "entries": len(entries), "directories": len(entries)-len(files), "files": len(files),
            "npz_files": len(npz), "extensions": dict(Counter(Path(e.filename).suffix for e in files)),
            "compressed_bytes": sum(e.compress_size for e in files),
            "uncompressed_bytes": sum(e.file_size for e in files),
            "npz_bytes_min": min((e.file_size for e in npz), default=None),
            "npz_bytes_max": max((e.file_size for e in npz), default=None),
            "path_date_min": min(dates, default=None), "path_date_max": max(dates, default=None),
            "npz_per_year": dict(sorted(Counter(d[:4] for d in dates).items())),
            "npz_per_month": dict(sorted(Counter(d[:7] for d in dates).items())),
            "duplicate_member_names": duplicates, "matched_rows": int(matched.sum()),
            "missing_link_rows": int((~matched).sum()),
            "missing_link_examples": links[~matched].head(20).tolist(),
            "unreferenced_npz": sum(e.filename not in referenced for e in npz),
            "example_paths": [e.filename for e in files[:5]],
            "all_npz_follow_readme_structure": all(re.fullmatch(r"dataset_goes/samples/\d{4}/\d{2}/\d{2}/[^/]+\.npz", e.filename) for e in npz)}
        try:
            if not matched.any():
                raise ValueError("Nenhum image_link corresponde exatamente a uma entrada do ZIP; caminhos não corrigidos automaticamente.")
            row = df.loc[matched[matched].index[0]]
            name = row["image_link"]
            if name in duplicates:
                raise ValueError("Nome de amostra duplicado no ZIP: associação ambígua.")
            entry = by_name[name]
            if entry.file_size > 32 * 1024**2:
                raise ValueError("NPZ excede limite de leitura de 32 MiB.")
            payload = archive.read(entry)
            # O NPZ também é um ZIP; limitar sua expansão antes de carregar arrays.
            with zipfile.ZipFile(io.BytesIO(payload)) as inner:
                if sum(e.file_size for e in inner.infolist()) > 128 * 1024**2:
                    raise ValueError("Conteúdo interno NPZ excede limite de 128 MiB.")
            summary["sample"] = {"row_index_zero_based": int(row.name),
                                 "record": json.loads(row.to_json()),
                                 "member_bytes": entry.file_size,
                                 "member_compressed_bytes": entry.compress_size,
                                 "sha256": hashlib.sha256(payload).hexdigest(),
                                 **inspect_npz(payload, row["time"])}
        except (ValueError, KeyError, OSError, zipfile.BadZipFile, NotImplementedError) as error:
            summary["sample_error"] = f"{type(error).__name__}: {error}"
    summary["sources_after"] = [fingerprint(path) for path in paths]
    summary["sources_unchanged"] = before == summary["sources_after"]
    return summary, df


def write_report(summary, df, output):
    output.mkdir(parents=True, exist_ok=True)
    (output / "audit_results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    c, z = summary["csv"], summary["zip"]
    lines = ["# Auditoria inicial do dataset GOES", "",
             "## Objetivo e método", "Validar a estrutura, os vínculos e uma leitura numérica. Sem target, tratamento, EDA aprofundada ou treinamento.",
             "CSV lido com pandas; ZIP aberto somente para leitura do índice e de um NPZ em memória. Nenhum arquivo extraído. Estatísticas populacionais (ddof=0).",
             "## Fontes e preservação", "| Arquivo original | Bytes |", "|---|---:|"]
    lines += [f"| `{s['path']}` | {s['bytes']} |" for s in summary["sources_before"]]
    lines += [f"Verificação antes/depois sem alterações: **{summary['sources_unchanged']}**. SHA-256 para arquivos pequenos; tamanho e mtime para o ZIP. Não foi calculado hash integral do ZIP nem testado o CRC de todas as imagens.",
              "A pasta original Backend_UTFPR contém README.md e dataset_weather.csv. O ZIP permanece na pasta Downloads. O projeto foi criado separadamente em outputs/projeto-goes. firstprompt.md é material fornecido, não uma autorização adicional; o escopo vem do pedido colado.",
              "## Estrutura e qualidade do CSV",
              f"{c['rows']} linhas × {c['columns']} colunas. Memória pandas estimada: {c['memory_bytes_deep']} bytes.",
              f"Período local America/Sao_Paulo: **{c['time_min']} a {c['time_max']}**.",
              f"Formato ISO sem offset com segundos: {c['time_format_iso_seconds']} registros. Datas inválidas: {c['unparseable_times']}. Ordem crescente: {c['time_monotonic']}.",
              f"Duplicatas completas adicionais: {c['duplicate_rows_extra']}; timestamps duplicados adicionais: {c['duplicate_timestamps_extra']}; horas ausentes: {c['missing_hours']}; horários fora da hora cheia: {c['off_hour']}.",
              f"Diferenças consecutivas: `{c['consecutive_deltas']}`. Lacunas verificadas na sequência local ingênua; o período observado começa após o último horário de verão brasileiro.",
              "| Coluna | dtype pandas | Ausentes |", "|---|---|---:|"]
    lines += [f"| {name} | {dtype} | {c['missing'][name]} |" for name, dtype in c["dtypes"].items()]
    lines += [f"Valores infinitos numéricos: `{c['infinite_numeric']}`.",
              "Numéricas: " + ", ".join(c["numeric"]) + ".",
              "Texto: " + ", ".join(c["non_numeric"]) + ". weather_code é código categórico apesar do dtype numérico; is_day é binário; wind_direction_10m é circular. time e image_link são referências e exigem tratamento específico. rain e precipitation exigem definição do horizonte/target e da disponibilidade operacional antes de decidir seu uso.",
              "### Primeiras cinco linhas", "```text", df.head().to_string(index=False), "```",
              "### Últimas cinco linhas", "```text", df.tail().to_string(index=False), "```",
              "## ZIP e correspondência dos links",
              f"Entradas: {z['entries']}; diretórios: {z['directories']}; arquivos: {z['files']}; NPZ: {z['npz_files']}. Extensões: `{z['extensions']}`.",
              f"Soma dos tamanhos compactados: {z['compressed_bytes']} bytes; descompactados: {z['uncompressed_bytes']} bytes. NPZ individual: {z['npz_bytes_min']} a {z['npz_bytes_max']} bytes.",
              f"Estrutura dataset_goes/samples/ANO/MES/DIA/*.npz em todos os NPZ: {z['all_npz_follow_readme_structure']}. Datas dos caminhos: {z['path_date_min']} a {z['path_date_max']}. São datas de diretórios, não uma validação dos timestamps de todas as capturas.",
              f"Contagem por ano: `{z['npz_per_year']}`. Contagens mensais no JSON anexo.",
              f"Links preenchidos: {c['links_filled']}; ausentes: {c['links_missing']}; distintos: {c['links_unique']}. Correspondências exatas: {z['matched_rows']}; links preenchidos sem arquivo: {z['missing_link_rows']}; NPZ não referenciados: {z['unreferenced_npz']}.",
              f"Reuso de imagens: {c['reused_link_distinct']} links aparecem em mais de uma linha, com {c['reused_link_rows_extra']} referências adicionais. Isso não é duplicação de registros meteorológicos; exige atenção futura ao pareamento e às fronteiras de divisão temporal.",
              f"Nomes duplicados no ZIP: {len(z['duplicate_member_names'])}. Exemplos de links sem arquivo: `{z['missing_link_examples']}`.",
              "image_link usa caminhos relativos à pasta que conteria dataset_goes. No ZIP, o caminho é o nome completo da entrada, sem depender do diretório atual do Python. O pacote está compactado, enquanto o README ilustra a árvore extraída; o acesso direto exemplificado no README precisa ser adaptado para ZipFile.",
              "## Prova de conceito"]
    if "sample" in summary:
        s = summary["sample"]
        lines += [f"Registro (índice base zero): {s['row_index_zero_based']}. Conteúdo completo e resultados:",
                  "```json", json.dumps(s, ensure_ascii=False, indent=2), "```",
                  "Os valores físicos são temperatura de brilho, não temperatura do ar a 2 m. A reconstrução usa os metadados reais e a fórmula documentada no README original."]
        if "capture_minus_csv_seconds" in s:
            lines += [f"Diferença captura − referência: **{s['capture_minus_csv_seconds']} segundos**. O desvio deve ser interpretado em conjunto com a tolerância de pareamento, não como prova automática de erro. Se positivo, a imagem começa depois da referência e pode ainda não estar disponível numa previsão emitida exatamente naquela hora."]
    else:
        lines += ["**Falha explícita:** " + summary["sample_error"]]
    lines += ["## Problemas, limitações e decisões pendentes",
              "- Apenas uma imagem teve conteúdo e CRC de leitura verificados. Correspondência de todos os links no índice não prova integridade ou coerência temporal de todo o acervo.",
              "- Ausência de image_link não equivale a ausência de chuva. Não houve imputação ou exclusão.",
              "- A máscara considera fill_value e não finitos. Sem flags de qualidade adicionais, não se garante validade radiométrica de todos os pixels restantes.",
              "- O README descreve grades e satélites distintos. A amostra não estabelece homogeneidade espacial ou temporal do conjunto. Estatísticas da área inteira podem diluir sinais locais de Londrina.",
              "- Definir horizonte, limiar de chuva, instante de emissão, tolerância e latência de disponibilidade das imagens. O pareamento pelo vizinho temporal mais próximo pode escolher uma captura futura.",
              "- Dados meteorológicos são históricos de modelos/reanálises conforme o README. Verificar quais variáveis estariam disponíveis no instante real de previsão e quais representam acumulações do intervalo.",
              "- As unidades meteorológicas seguem o README; o CSV sozinho não permite verificar a configuração original da API (inclusive unidade do vento).",
              "## Protocolo contra vazamento de informação",
              "Não usar informação futura nem o target como feature. Não criar target neste estágio. Não embaralhar nem dividir aleatoriamente a avaliação temporal final. Ajustar imputadores, normalizadores e demais transformações apenas no treino. Não usar estatísticas globais de outros períodos para transformar o treino, nem resultados do teste para selecionar variáveis. Não equiparar chuva zero e dado ausente. A EDA descritiva futura pode observar todo o período, mas decisões de modelagem devem respeitar o protocolo temporal.",
              "## Próximos passos, sujeitos a autorização",
              "Revisar estes achados; definir disponibilidade operacional, horizonte e limiar; depois autorizar a EDA aprofundada, a análise de cobertura temporal e das grades. Só em etapas posteriores: recorte/amostragem, tratamento, features, target, divisão temporal e comparação com baseline meteorológico. Nenhuma dessas etapas foi executada.",
              "## Ambiente", "```json", json.dumps(summary["environment"], indent=2), "```",
              "A execução foi feita no Windows com o Python já disponível no ambiente do aplicativo, sem instalações globais. Código parametrizado para Ubuntu; execução no Ubuntu ainda não testada."]
    (output / "dataset_audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--readme", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / "reports")
    args = parser.parse_args()
    # Impedir que nomes de saída sobrescrevam qualquer fonte por acidente.
    sources = {p.resolve() for p in (args.csv, args.zip, args.readme, *args.source)}
    if any((args.output / name).resolve() in sources for name in ("dataset_audit.md", "audit_results.json")):
        parser.error("Diretório de saída causaria sobrescrita de uma fonte original.")
    try:
        summary, df = audit(args.csv, args.zip, args.readme, args.source)
        write_report(summary, df, args.output)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Falha na auditoria: {type(error).__name__}: {error}\n")
    print(f"Relatório: {args.output / 'dataset_audit.md'}")
    print(json.dumps({"csv": summary["csv"]["rows"], "npz": summary["zip"]["npz_files"],
                      "sample_error": summary.get("sample_error"),
                      "sources_unchanged": summary["sources_unchanged"]}, indent=2))
    if "sample_error" in summary or not summary["sources_unchanged"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
