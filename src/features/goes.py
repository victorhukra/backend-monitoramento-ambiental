"""Leitura e reconstrução C13; nenhuma geolocalização ou feature regional implícita."""
from dataclasses import dataclass
from datetime import datetime
import io
from pathlib import PurePosixPath
import re
import zipfile

import numpy as np

from src.data.audit import scalar, stats  # Reuso da interpretação escalar e estatística testada.

METADATA = ("satellite", "grid_signature", "timestamp_utc", "source_filename",
            "source_key", "units", "scale_factor", "add_offset", "fill_value")
MAX_MEMBER_BYTES = 32 * 1024**2
MAX_INNER_BYTES = 128 * 1024**2


@dataclass
class PhysicalImage:
    """values é sempre Kelvin; None significa reconstrução não autorizada/possível."""
    status: str
    values: np.ndarray | None
    valid: np.ndarray | None
    diagnostics: dict


def _real_scalar(value, key):
    if isinstance(value, (bool, str, bytes)) or np.asarray(value).ndim != 0 or not np.isrealobj(value):
        raise ValueError(f"{key}: esperado escalar numérico real")
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{key}: escalar numérico inválido") from error


def reconstruct(raw, metadata):
    """Valida packing e máscara antes de reconstruir. Não calcula features de imagem real."""
    raw = np.asarray(raw)
    info = {"shape": list(raw.shape), "dtype": str(raw.dtype), "pixels": int(raw.size),
            "issues": [], "unit_calculation": None}
    if raw.ndim != 2 or raw.dtype.kind not in "iuf" or not raw.size:
        info["issues"].append("Matriz deve ser bidimensional, numérica real e não vazia")
        return PhysicalImage("invalid_matrix", None, None, info)
    finite = np.isfinite(raw)
    info["nonfinite_pixels"] = int((~finite).sum())
    info["raw_finite_min"] = float(raw[finite].min()) if finite.any() else None
    info["raw_finite_max"] = float(raw[finite].max()) if finite.any() else None
    # Não certificar validade quando o sentinela é desconhecido ou incompatível com dtype.
    try:
        if "fill_value" not in metadata:
            raise ValueError("fill_value ausente: máscara não pode ser certificada")
        fill = _real_scalar(metadata["fill_value"], "fill_value")
        if raw.dtype.kind in "iu":
            limits = np.iinfo(raw.dtype)
            if not np.isfinite(fill) or not fill.is_integer() or not limits.min <= fill <= limits.max:
                raise ValueError("fill_value não representável no dtype inteiro; não reinterpretar signedness")
        elif np.isfinite(fill) and float(np.asarray(fill, dtype=raw.dtype)) != fill:
            raise ValueError("fill_value não representável exatamente no dtype; confirmar packing")
        fill_mask = np.isnan(raw) if np.isnan(fill) else raw == fill
        valid = finite & ~fill_mask
        info.update(fill_pixels=int(fill_mask.sum()), valid_pixels=int(valid.sum()),
                    invalid_pixels=int((~valid).sum()), valid_fraction=float(valid.mean()),
                    fill_nonfinite_overlap=int((fill_mask & ~finite).sum()))
    except ValueError as error:
        info["issues"].append(str(error))
        return PhysicalImage("invalid_mask_metadata", None, None, info)
    try:
        missing = [key for key in ("scale_factor", "add_offset", "units") if key not in metadata]
        if missing:
            raise ValueError("Metadados físicos ausentes: " + ", ".join(missing))
        scale = _real_scalar(metadata["scale_factor"], "scale_factor")
        offset = _real_scalar(metadata["add_offset"], "add_offset")
        if not np.isfinite([scale, offset]).all() or scale <= 0:
            raise ValueError("C13 neste piloto exige escala positiva finita e offset finito")
        unit = metadata["units"]
        if isinstance(unit, bytes):
            unit = unit.decode("utf-8")
        if not isinstance(unit, str) or unit.strip().lower() not in {"k", "kelvin"}:
            raise ValueError("Unidade não suportada/confirmada para C13: esperado K ou Kelvin; sem conversão implícita")
    except (ValueError, UnicodeError) as error:
        info["issues"].append(str(error))
        return PhysicalImage("invalid_physical_metadata", None, valid, info)
    if not valid.any():
        info["issues"].append("Nenhum pixel válido; reconstrução e estatísticas indisponíveis")
        return PhysicalImage("all_invalid", None, valid, info)
    values = np.full(raw.shape, np.nan, dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore"):
        values[valid] = raw[valid].astype(np.float64) * scale + offset
    if not np.isfinite(values[valid]).all():
        info["issues"].append("Transformação gerou valores não finitos; não descartar silenciosamente")
        return PhysicalImage("invalid_reconstruction", None, valid, info)
    if (values[valid] <= 0).any():
        info["issues"].append("Temperatura de brilho não positiva em Kelvin: verificar packing/unidade")
        return PhysicalImage("invalid_reconstruction", None, valid, info)
    info.update(unit_calculation="K", physical_min_K=float(values[valid].min()),
                physical_max_K=float(values[valid].max()),
                array_bytes_lower_bound=int(raw.nbytes + finite.nbytes + fill_mask.nbytes + valid.nbytes + values.nbytes))
    return PhysicalImage("reconstructed", values, valid, info)


def validate_identity(metadata, member_name):
    """Diagnóstico de identidade; não determina elegibilidade temporal."""
    issues = []
    for key in METADATA[:5]:
        if key not in metadata:
            issues.append(f"{key}: ausente")
        elif not isinstance(metadata[key], str) or not metadata[key].strip():
            issues.append(f"{key}: esperado texto não vazio")
    timestamp = metadata.get("timestamp_utc")
    if isinstance(timestamp, str):
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                issues.append("timestamp_utc sem offset: não assumir fuso")
        except ValueError:
            issues.append("timestamp_utc não interpretável")
    sat_match = re.search(r"_G(\d+)_", member_name)
    if sat_match and "satellite" in metadata and metadata["satellite"] != "GOES-" + sat_match.group(1):
        issues.append("satellite diverge do nome do membro")
    source = metadata.get("source_filename")
    if isinstance(source, str) and PurePosixPath(source).stem != PurePosixPath(member_name).stem:
        issues.append("source_filename diverge do nome do membro")
    key = metadata.get("source_key")
    if isinstance(source, str) and isinstance(key, str) and PurePosixPath(key).name != source:
        issues.append("source_key diverge de source_filename")
    return issues


def read_member(archive, member):
    """Lê um ZipInfo, com limites de expansão e sem extração em disco."""
    if member.file_size > MAX_MEMBER_BYTES:
        raise ValueError("Membro NPZ excede limite de 32 MiB")
    payload = archive.read(member)
    return payload, inspect_payload(payload, member.filename)


def inspect_payload(payload, member_name):
    with zipfile.ZipFile(io.BytesIO(payload), "r") as inner:
        entries = inner.infolist()
        if sum(entry.file_size for entry in entries) > MAX_INNER_BYTES:
            raise ValueError("Expansão interna NPZ excede limite de 128 MiB")
        if len({entry.filename for entry in entries}) != len(entries):
            raise ValueError("NPZ possui membros internos duplicados")
    metadata, issues = {}, []
    with np.load(io.BytesIO(payload), allow_pickle=False) as data:
        keys = list(data.files)
        for key in METADATA:
            if key in data:
                try:
                    metadata[key] = scalar(data, key)
                except (ValueError, TypeError, UnicodeError) as error:
                    issues.append(f"{key}: {error}")
        if "cmi_c13_raw" not in data:
            raise ValueError("cmi_c13_raw ausente")
        result = reconstruct(data["cmi_c13_raw"], metadata)
    issues.extend(validate_identity(metadata, member_name))
    result.diagnostics.update(keys=keys, metadata=metadata, metadata_issues=issues,
        missing_metadata=[key for key in METADATA if key not in metadata],
        spatial_status="not_validated", region_statistics=None)
    return result
