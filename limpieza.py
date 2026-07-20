from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUTS_DIR = BASE_DIR / "outputs"

MISSING_TOKENS = {
    "",
    "N/A",
    "NA",
    "N.D.",
    "ND",
    "NULL",
    "NONE",
    "-",
    "--",
    "---",
    ".",
    "SIN DATO",
    "SIN INFORMACION",
    "SIN INFORMACIÓN",
    "NO APARECE REGISTRO",
}


def natural_key(path: Path) -> list[object]:
    """Ordena establecimiento (2).xls antes de establecimiento (10).xls."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def clean_header(value: object) -> str:
    """Limpia únicamente el nombre técnico de una columna."""
    text = str(value).replace("\xa0", " ").strip().upper()
    text = re.sub(r"\s+", "_", text)
    return text


def select_data_table(tables: list[pd.DataFrame], file_path: Path) -> pd.DataFrame:
    """Selecciona la tabla que contiene las columnas de establecimientos."""
    for table in tables:
        if table.empty:
            continue

        first_row = {clean_header(value) for value in table.iloc[0].tolist()}
        columns = {clean_header(value) for value in table.columns.tolist()}

        if {"CODIGO", "ESTABLECIMIENTO"}.issubset(first_row):
            result = table.iloc[1:].copy()
            result.columns = [clean_header(value) for value in table.iloc[0].tolist()]
            return result

        if {"CODIGO", "ESTABLECIMIENTO"}.issubset(columns):
            result = table.copy()
            result.columns = [clean_header(value) for value in table.columns.tolist()]
            return result

    if not tables:
        raise ValueError(f"No se encontró ninguna tabla HTML en {file_path.name}")

    # Respaldo: elegir la tabla más grande y comprobar el encabezado.
    largest = max(tables, key=lambda frame: frame.shape[0] * frame.shape[1])
    if largest.empty:
        raise ValueError(f"La tabla más grande de {file_path.name} está vacía")

    first_row = [clean_header(value) for value in largest.iloc[0].tolist()]
    if "CODIGO" in first_row and "ESTABLECIMIENTO" in first_row:
        result = largest.iloc[1:].copy()
        result.columns = first_row
        return result

    raise ValueError(
        f"No fue posible identificar la tabla de establecimientos en {file_path.name}. "
        f"Dimensión de la tabla más grande: {largest.shape}"
    )


def read_exported_xls(file_path: Path) -> pd.DataFrame:
    """Lee los .xls del MINEDUC, que internamente son documentos HTML."""
    try:
        tables = pd.read_html(
            file_path,
            encoding="ISO-8859-1",
            keep_default_na=False,
        )
    except Exception as exc:
        raise RuntimeError(f"No se pudo leer {file_path.name}: {exc}") from exc

    data = select_data_table(tables, file_path)
    data = data.astype("string")
    data = data.reset_index(drop=True)
    return data


def is_fully_empty_row(data: pd.DataFrame) -> pd.Series:
    """Detecta filas donde todas las celdas están vacías o contienen solo espacios."""
    text = data.astype("string")
    return text.apply(lambda col: col.isna() | col.str.strip().eq("")).all(axis=1)


def missing_mask(series: pd.Series) -> pd.Series:
    """Reconoce NA reales, cadenas vacías y textos equivalentes a ausencia de datos."""
    text = series.astype("string")
    stripped = text.str.replace("\xa0", " ", regex=False).str.strip()
    upper = stripped.str.upper()
    return text.isna() | stripped.eq("") | upper.isin(MISSING_TOKENS)


def comparison_key(value: object) -> str | None:
    """Clave auxiliar para detectar variantes, sin modificar el valor original."""
    if pd.isna(value):
        return None

    text = str(value).replace("\xa0", " ").strip().upper()
    if text in MISSING_TOKENS:
        return None

    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^A-Z0-9Ñ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def build_variable_diagnosis(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_rows = len(data)

    for column in data.columns:
        series = data[column].astype("string")
        stripped = series.str.replace("\xa0", " ", regex=False).str.strip()
        missing = missing_mask(series)

        leading_trailing = (~missing) & series.ne(stripped)
        multiple_spaces = (~missing) & stripped.str.contains(r"\s{2,}", regex=True, na=False)
        invisible_nbsp = series.str.contains("\xa0", regex=False, na=False)

        rows.append(
            {
                "variable": column,
                "tipo_pandas": str(series.dtype),
                "registros": total_rows,
                "faltantes": int(missing.sum()),
                "porcentaje_faltantes": round(float(missing.mean() * 100), 2) if total_rows else 0.0,
                "valores_unicos_sin_faltantes": int(stripped.mask(missing).nunique(dropna=True)),
                "espacios_inicio_o_final": int(leading_trailing.sum()),
                "espacios_multiples": int(multiple_spaces.sum()),
                "caracteres_nbsp": int(invisible_nbsp.sum()),
            }
        )

    return pd.DataFrame(rows)


def build_text_variants(data: pd.DataFrame) -> pd.DataFrame:
    """Lista grupos con varias escrituras equivalentes según una clave auxiliar."""
    records: list[dict[str, object]] = []

    for column in data.columns:
        series = data[column].astype("string")
        temp = pd.DataFrame({"original": series})
        temp["clave"] = temp["original"].map(comparison_key)
        temp = temp.dropna(subset=["clave"])

        for key, group in temp.groupby("clave", sort=False):
            variants = sorted({str(value).strip() for value in group["original"].dropna()})
            if len(variants) <= 1:
                continue

            records.append(
                {
                    "variable": column,
                    "clave_comparacion": key,
                    "cantidad_variantes": len(variants),
                    "cantidad_registros": len(group),
                    "variantes": " | ".join(variants),
                }
            )

    return pd.DataFrame(records)


def load_all_files(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    files = sorted(raw_dir.glob("*.xls"), key=natural_key)
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos .xls en: {raw_dir}")

    frames: list[pd.DataFrame] = []
    metadata: list[dict[str, object]] = []
    expected_columns: list[str] | None = None

    for file_path in files:
        frame = read_exported_xls(file_path)

        if expected_columns is None:
            expected_columns = frame.columns.tolist()
        elif frame.columns.tolist() != expected_columns:
            raise ValueError(
                f"Las columnas de {file_path.name} no coinciden con las del primer archivo.\n"
                f"Esperadas: {expected_columns}\n"
                f"Encontradas: {frame.columns.tolist()}"
            )

        empty_rows = is_fully_empty_row(frame)
        frame_with_origin = frame.copy()
        frame_with_origin.insert(0, "_ARCHIVO_ORIGEN", file_path.name)
        frame_with_origin.insert(1, "_FILA_ORIGEN", range(1, len(frame_with_origin) + 1))
        frames.append(frame_with_origin)

        metadata.append(
            {
                "archivo": file_path.name,
                "filas_crudas": len(frame),
                "filas_completamente_vacias": int(empty_rows.sum()),
                "filas_efectivas": int((~empty_rows).sum()),
                "variables_originales": len(frame.columns),
            }
        )

        print(f"[OK] {file_path.name}: {len(frame):,} filas, {len(frame.columns)} variables")

    combined = pd.concat(frames, ignore_index=True)
    return combined, pd.DataFrame(metadata)


def save_summary(
    effective_data: pd.DataFrame,
    metadata: pd.DataFrame,
    diagnosis: pd.DataFrame,
    exact_duplicates: pd.DataFrame,
    variants: pd.DataFrame,
    output_path: Path,
) -> None:
    original_columns = [column for column in effective_data.columns if not column.startswith("_")]
    total_cells = len(effective_data) * len(original_columns)
    total_missing = sum(int(missing_mask(effective_data[column]).sum()) for column in original_columns)
    missing_pct = (total_missing / total_cells * 100) if total_cells else 0.0

    lines = [
        "DIAGNÓSTICO INICIAL DEL CONJUNTO DE DATOS",
        "=" * 44,
        f"Archivos cargados: {len(metadata):,}",
        f"Filas crudas extraídas: {int(metadata['filas_crudas'].sum()):,}",
        f"Filas completamente vacías: {int(metadata['filas_completamente_vacias'].sum()):,}",
        f"Registros efectivos: {len(effective_data):,}",
        f"Variables originales: {len(original_columns):,}",
        f"Valores faltantes o equivalentes: {total_missing:,} ({missing_pct:.2f}%)",
        f"Variables con al menos un faltante: {int((diagnosis['faltantes'] > 0).sum()):,}",
        f"Registros involucrados en duplicados exactos: {len(exact_duplicates):,}",
        f"Grupos de posibles variantes de escritura: {len(variants):,}",
        "",
        "Nota: _ARCHIVO_ORIGEN y _FILA_ORIGEN son variables técnicas de trazabilidad",
        "y no se cuentan dentro de las variables originales del conjunto.",
        "",
        "5.1 VALORES FALTANTES POR VARIABLE",
        "-" * 44,
    ]

    tabla = diagnosis[["variable", "faltantes", "porcentaje_faltantes"]].sort_values("variable")
    ancho_variable = max(len("Variable"), tabla["variable"].str.len().max())
    lines.append(f"{'Variable':<{ancho_variable}}  {'Faltantes':>10}  {'Porcentaje':>10}")
    for _, fila in tabla.iterrows():
        lines.append(
            f"{fila['variable']:<{ancho_variable}}  {fila['faltantes']:>10,}  "
            f"{fila['porcentaje_faltantes']:>9.2f} %"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    combined, metadata = load_all_files(RAW_DIR)
    original_columns = [column for column in combined.columns if not column.startswith("_")]

    empty_rows = is_fully_empty_row(combined[original_columns])
    effective = combined.loc[~empty_rows].copy().reset_index(drop=True)

    diagnosis = build_variable_diagnosis(effective[original_columns])
    variants = build_text_variants(effective[original_columns])

    duplicate_mask = effective.duplicated(subset=original_columns, keep=False)
    exact_duplicates = effective.loc[duplicate_mask].sort_values(original_columns).copy()

    combined.to_csv(
        OUTPUTS_DIR / "datos_crudos_unificados_con_origen.csv",
        index=False,
        encoding="utf-8-sig",
    )
    effective.to_csv(
        OUTPUTS_DIR / "datos_crudos_efectivos_con_origen.csv",
        index=False,
        encoding="utf-8-sig",
    )
    metadata.to_csv(
        OUTPUTS_DIR / "archivos_cargados.csv",
        index=False,
        encoding="utf-8-sig",
    )
    diagnosis.to_csv(
        OUTPUTS_DIR / "diagnostico_variables.csv",
        index=False,
        encoding="utf-8-sig",
    )
    exact_duplicates.to_csv(
        OUTPUTS_DIR / "duplicados_exactos.csv",
        index=False,
        encoding="utf-8-sig",
    )
    variants.to_csv(
        OUTPUTS_DIR / "posibles_variantes_texto.csv",
        index=False,
        encoding="utf-8-sig",
    )

    save_summary(
        effective_data=effective,
        metadata=metadata,
        diagnosis=diagnosis,
        exact_duplicates=exact_duplicates,
        variants=variants,
        output_path=OUTPUTS_DIR / "resumen_diagnostico.txt",
    )

    print("\nDiagnóstico completado.")
    print(f"Revisa los resultados en: {OUTPUTS_DIR}")


if __name__ == "__main__":
    main()