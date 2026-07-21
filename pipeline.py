"""Orquesta todo el proyecto: carga, diagnostico (limpieza.py, ya existente),
limpieza real (limpieza_transformaciones.py), validacion (validacion.py) e
informe de calidad antes/despues.

Este es el archivo que se entrega como "codigo de las acciones tomadas
desde que se carga el conjunto de datos hasta que se termina de limpiar"
(material a entregar, guia paso 11).
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pandas as pd

from limpieza import (
    BASE_DIR, RAW_DIR, OUTPUTS_DIR,
    load_all_files, is_fully_empty_row, missing_mask,
    build_variable_diagnosis, build_text_variants,
)
from limpieza_transformaciones import limpiar_dataset
import validacion


def _metrica_faltantes(data: pd.DataFrame, columnas: list[str]) -> tuple[int, float]:
    total_celdas = len(data) * len(columnas)
    total_faltantes = sum(int(missing_mask(data[c]).sum()) for c in columnas)
    porcentaje = (total_faltantes / total_celdas * 100) if total_celdas else 0.0
    return total_faltantes, porcentaje


def construir_informe_calidad(
    antes: pd.DataFrame, columnas_antes: list[str],
    despues: pd.DataFrame, columnas_despues: list[str],
    duplicados_exactos_antes: int, duplicados_exactos_despues: int,
    posibles_duplicados_parciales: int,
    diagnostico_antes: pd.DataFrame,
    resultados_validacion: pd.DataFrame,
    log_transformaciones: pd.DataFrame,
) -> pd.DataFrame:
    """Paso 8: tabla Metrica / Antes / Despues."""
    faltantes_antes, pct_antes = _metrica_faltantes(antes, columnas_antes)
    faltantes_despues, pct_despues = _metrica_faltantes(despues, columnas_despues)

    variables_con_na_antes = int((diagnostico_antes["faltantes"] > 0).sum())
    variables_con_na_despues = int(
        sum(missing_mask(despues[c]).any() for c in columnas_despues)
    )

    # "Variables con formato inconsistente" antes: telefono (longitudes
    # variadas), distrito (3/6/10 caracteres), plan (parentesis). Despues:
    # las que siguen marcadas para revision (telefono) porque esas SI
    # siguen siendo, honestamente, inconsistentes en la fuente original.
    variables_formato_inconsistente_antes = 3  # TELEFONO, DISTRITO, PLAN
    variables_formato_inconsistente_despues = int(
        (despues.get("TELEFONO_REVISAR", pd.Series(dtype=bool)).fillna(False)).any()
    )

    categorias_inconsistentes_antes = len(build_text_variants(antes[columnas_antes]))
    variables_categoricas_despues = [c for c in ["DEPARTAMENTO", "MUNICIPIO", "SECTOR",
                                                   "AREA", "STATUS", "MODALIDAD",
                                                   "JORNADA", "PLAN", "DEPARTAMENTAL"]
                                     if c in despues.columns]
    categorias_inconsistentes_despues = int(
        validacion.prueba_categorias_sin_variantes(despues, variables_categoricas_despues)[1]
    )

    filas = [
        ("Registros", len(antes), len(despues)),
        ("Variables", len(columnas_antes),
         len([c for c in despues.columns if not c.startswith("_")])),
        ("Valores faltantes", f"{faltantes_antes:,} ({pct_antes:.2f}%)",
         f"{faltantes_despues:,} ({pct_despues:.2f}%)"),
        ("Variables con NA", variables_con_na_antes, variables_con_na_despues),
        ("Duplicados exactos", duplicados_exactos_antes, duplicados_exactos_despues),
        ("Registros con CODIGO duplicado (pendiente revision)",
         "No evaluado antes de limpiar",
         int(despues["CODIGO_DUPLICADO"].fillna(False).sum())
         if "CODIGO_DUPLICADO" in despues.columns else "N/A"),
        ("Posibles duplicados (parciales)", "No evaluado antes de limpiar",
         posibles_duplicados_parciales),
        ("Variables con formato inconsistente",
         variables_formato_inconsistente_antes, variables_formato_inconsistente_despues),
        ("Variables con tipo incorrecto", "17 (todo string sin declarar)", 0),
        ("Categorias inconsistentes (grupos de variantes)",
         categorias_inconsistentes_antes, categorias_inconsistentes_despues),
        ("Errores corregidos (transformaciones aplicadas)",
         "N/A", int(log_transformaciones["registros_afectados"].sum())),
    ]
    return pd.DataFrame(filas, columns=["metrica", "antes", "despues"])


def _tabla_faltantes_por_variable(diagnostico: pd.DataFrame) -> list[str]:
    """Da formato de tabla de texto a variable/faltantes/porcentaje,
    ordenado alfabeticamente (mismo formato que la tabla 5.1 del
    diagnostico original)."""
    tabla = diagnostico[["variable", "faltantes", "porcentaje_faltantes"]].sort_values("variable")
    ancho_variable = max(len("Variable"), tabla["variable"].str.len().max())
    lineas = [f"{'Variable':<{ancho_variable}}  {'Faltantes':>10}  {'Porcentaje':>10}"]
    for _, fila in tabla.iterrows():
        lineas.append(
            f"{fila['variable']:<{ancho_variable}}  {fila['faltantes']:>10,}  "
            f"{fila['porcentaje_faltantes']:>9.2f} %"
        )
    return lineas


def guardar_resumen_ejecucion(
    metadata: pd.DataFrame,
    efectivo: pd.DataFrame,
    limpio: pd.DataFrame,
    log_transformaciones: pd.DataFrame,
    resultados_validacion: pd.DataFrame,
    informe_calidad: pd.DataFrame,
    diagnostico_antes: pd.DataFrame,
    diagnostico_despues: pd.DataFrame,
    output_path: Path,
) -> None:
    """Genera un .txt legible con lo que se analizo y los resultados de
    correr el pipeline completo (carga, limpieza, validacion, informe),
    para tener un resumen humano ademas de los CSV."""
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lineas: list[str] = [
        "RESUMEN DE EJECUCION DEL PIPELINE DE LIMPIEZA",
        "Establecimientos educativos nivel Diversificado - MINEDUC Guatemala",
        "=" * 70,
        f"Fecha y hora de ejecucion: {ahora}",
        "",
        "1. CARGA DE ARCHIVOS",
        "-" * 70,
        f"Archivos .xls cargados: {len(metadata):,}",
        f"Filas crudas extraidas (todas las fuentes): {int(metadata['filas_crudas'].sum()):,}",
        f"Filas completamente vacias descartadas: {int(metadata['filas_completamente_vacias'].sum()):,}",
        f"Registros efectivos antes de limpiar: {len(efectivo):,}",
        "",
        "1.1 VALORES FALTANTES POR VARIABLE (antes de limpiar)",
        "-" * 70,
    ]
    lineas += _tabla_faltantes_por_variable(diagnostico_antes)
    lineas += [
        "",
        "2. LIMPIEZA",
        "-" * 70,
        f"Registros despues de limpiar: {len(limpio):,}",
        f"Diferencia de registros: {len(limpio) - len(efectivo):+,} "
        "(ver detalle en 'registro_transformaciones.csv'; incluye la "
        "eliminacion de filas de establecimiento (8).xls con "
        "DEPARTAMENTO='GUATEMALA', ya cubiertas por establecimiento (5).xls)",
        f"Transformaciones distintas documentadas: {len(log_transformaciones):,}",
        f"Total de registros afectados por alguna transformacion: "
        f"{int(log_transformaciones['registros_afectados'].sum()):,}",
        "",
        "Detalle de transformaciones (variable: problema -> transformacion "
        "[registros afectados]):",
    ]

    for _, fila in log_transformaciones.iterrows():
        lineas.append(
            f"  - {fila['variable']}: {fila['problema_detectado']} "
            f"-> {fila['transformacion']} [{fila['registros_afectados']:,} registros]"
        )

    lineas += [
        "",
        "2.1 VALORES FALTANTES POR VARIABLE (despues de limpiar)",
        "-" * 70,
    ]
    lineas += _tabla_faltantes_por_variable(diagnostico_despues)

    lineas += [
        "",
        "3. RESULTADOS DE VALIDACION (paso 7)",
        "-" * 70,
    ]
    for _, fila in resultados_validacion.iterrows():
        lineas.append(f"  [{fila['resultado']}] {fila['prueba']}")
        lineas.append(f"      cantidad: {fila['cantidad']:,} | {fila['detalle']}")

    lineas += [
        "",
        "4. INFORME DE CALIDAD ANTES / DESPUES (paso 8)",
        "-" * 70,
    ]
    for _, fila in informe_calidad.iterrows():
        lineas.append(f"  {fila['metrica']}: antes = {fila['antes']} | despues = {fila['despues']}")

    lineas += [
        "",
        "=" * 70,
        "Archivos generados en esta corrida (carpeta outputs/):",
        "  - datos_limpios.csv",
        "  - registro_transformaciones.csv",
        "  - resultados_validacion.csv",
        "  - informe_calidad_antes_despues.csv",
        "  - resumen_ejecucion.txt (este archivo)",
    ]

    output_path.write_text("\n".join(lineas), encoding="utf-8")


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Paso 1-3: carga + diagnostico (reutiliza limpieza.py tal cual) ---
    combined, metadata = load_all_files(RAW_DIR)
    columnas_originales = [c for c in combined.columns if not c.startswith("_")]
    filas_vacias = is_fully_empty_row(combined[columnas_originales])
    efectivo = combined.loc[~filas_vacias].copy().reset_index(drop=True)

    diagnostico_antes = build_variable_diagnosis(efectivo[columnas_originales])
    duplicados_antes = int(efectivo.duplicated(subset=columnas_originales, keep=False).sum())

    # --- Paso 5-6: limpieza real + log de transformaciones ---
    limpio, log_transformaciones = limpiar_dataset(efectivo)

    # --- Paso 7: validacion automatica ---
    columnas_originales_en_limpio = [c for c in columnas_originales if c in limpio.columns]
    resultados_validacion = validacion.ejecutar_todas(limpio, columnas_originales_en_limpio)

    duplicados_despues = int(
        limpio.duplicated(subset=columnas_originales_en_limpio, keep=False).sum()
    )
    posibles_duplicados_parciales = int(limpio["GRUPO_DUPLICADO_PARCIAL"].notna().sum())
    diagnostico_despues = build_variable_diagnosis(limpio[columnas_originales_en_limpio])

    # --- Paso 8: informe antes / despues ---
    informe_calidad = construir_informe_calidad(
        antes=efectivo, columnas_antes=columnas_originales,
        despues=limpio, columnas_despues=columnas_originales_en_limpio,
        duplicados_exactos_antes=duplicados_antes,
        duplicados_exactos_despues=duplicados_despues,
        posibles_duplicados_parciales=posibles_duplicados_parciales,
        diagnostico_antes=diagnostico_antes,
        resultados_validacion=resultados_validacion,
        log_transformaciones=log_transformaciones,
    )

    # --- Paso 9: guardar dataset limpio final + artefactos de las pruebas ---
    limpio.to_csv(OUTPUTS_DIR / "datos_limpios.csv", index=False, encoding="utf-8-sig")
    log_transformaciones.to_csv(
        OUTPUTS_DIR / "registro_transformaciones.csv", index=False, encoding="utf-8-sig"
    )
    resultados_validacion.to_csv(
        OUTPUTS_DIR / "resultados_validacion.csv", index=False, encoding="utf-8-sig"
    )
    informe_calidad.to_csv(
        OUTPUTS_DIR / "informe_calidad_antes_despues.csv", index=False, encoding="utf-8-sig"
    )

    guardar_resumen_ejecucion(
        metadata=metadata,
        efectivo=efectivo,
        limpio=limpio,
        log_transformaciones=log_transformaciones,
        resultados_validacion=resultados_validacion,
        informe_calidad=informe_calidad,
        diagnostico_antes=diagnostico_antes,
        diagnostico_despues=diagnostico_despues,
        output_path=OUTPUTS_DIR / "resumen_ejecucion.txt",
    )

    print("Limpieza completa.")
    print(f"Registros: {len(efectivo):,} -> {len(limpio):,}")
    print(f"Transformaciones documentadas: {len(log_transformaciones):,}")
    print("\nResultados de validacion:")
    print(resultados_validacion.to_string(index=False))
    print(f"\nArchivos generados en: {OUTPUTS_DIR}")


if __name__ == "__main__":
    main()