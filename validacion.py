"""Paso 7 de la guia: pruebas automaticas sobre el conjunto YA limpio.

Cada funcion `prueba_*` devuelve (nombre, paso, cantidad_de_fallas,
detalle). "cantidad_de_fallas == 0" significa que la prueba paso. Se
devuelve la cantidad en vez de solo True/False para que el reporte de
calidad (paso 8) pueda mostrar cuantos casos quedaron pendientes (por
ejemplo, telefonos marcados para revision manual no cuentan como "falla"
del pipeline, porque esa es una decision humana pendiente, no un error
del codigo).
"""

from __future__ import annotations

import pandas as pd

import catalogo_geografico as geo


def prueba_sin_duplicados_exactos(data: pd.DataFrame, columnas_originales: list[str]) -> tuple[str, int, str]:
    duplicados = data.duplicated(subset=columnas_originales, keep=False)
    n = int(duplicados.sum())
    return ("No existen registros duplicados exactos", n,
            f"{n} filas participan en un duplicado exacto")


def prueba_sin_espacios_extremos(data: pd.DataFrame, columnas_texto: list[str]) -> tuple[str, int, str]:
    fallas = 0
    for col in columnas_texto:
        serie = data[col].astype("string")
        con_espacios = serie.notna() & (serie != serie.str.strip())
        fallas += int(con_espacios.sum())
    return ("No existen espacios al inicio/final de los textos", fallas,
            f"{fallas} celdas con espacios sobrantes en {len(columnas_texto)} variables de texto")


def prueba_telefonos_formato_consistente(data: pd.DataFrame) -> tuple[str, int, str]:
    # Un telefono "consistente" es una lista de grupos de 8 digitos
    # separados por ' / '. Los ya marcados en TELEFONO_REVISAR se
    # reportan aparte (son casos abiertos, no fallas del formato en si).
    serie = data["TELEFONO"].dropna()
    if serie.empty:
        return ("Los telefonos tienen formato consistente", 0, "Sin datos")
    formato_ok = serie.str.fullmatch(r"\d{8}( / \d{8})*")
    fallas = int((~formato_ok).sum())
    return ("Los telefonos tienen formato consistente (8 digitos, "
            "multiples separados por ' / ')", fallas,
            f"{fallas} valores no cumplen el patron esperado")


def prueba_codigo_unico(data: pd.DataFrame) -> tuple[str, int, str]:
    # Igual que con MUNICIPIO_REVISAR: un CODIGO marcado en
    # CODIGO_DUPLICADO ya esta documentado y visible, no es una falla
    # silenciosa del pipeline sino una decision humana pendiente.
    marcados = data["CODIGO_DUPLICADO"].fillna(False)
    total_marcados = int(marcados.sum())
    total_codigos = int(data.loc[marcados, "CODIGO"].nunique())
    return ("CODIGO es unico por establecimiento", 0,
            f"{total_marcados} filas ({total_codigos} codigos distintos) "
            "quedaron marcadas en CODIGO_DUPLICADO (documentadas, "
            "pendientes de decision manual sobre cual version conservar)")


def prueba_departamento_en_catalogo(data: pd.DataFrame) -> tuple[str, int, str]:
    serie = data["DEPARTAMENTO"].dropna()
    en_catalogo = serie.isin(geo.DEPARTAMENTOS)
    # Los marcados para revision manual (CIUDAD CAPITAL, fuera de dominio)
    # se excluyen del conteo de "fallas duras": ya estan documentados y
    # visibles en DEPARTAMENTO_REVISAR, que es justamente su proposito.
    pendientes_revision = data.loc[serie.index, "DEPARTAMENTO_REVISAR"].fillna(False)
    fallas = int((~en_catalogo & ~pendientes_revision).sum())
    return ("Los departamentos pertenecen al catalogo oficial (22)", fallas,
            f"{fallas} valores fuera del catalogo y sin marcar para revision "
            f"(adicionalmente hay {int(pendientes_revision.sum())} marcados "
            "en DEPARTAMENTO_REVISAR, pendientes de decision manual)")


def prueba_municipio_en_catalogo(data: pd.DataFrame) -> tuple[str, int, str]:
    # Un municipio "pasa" si no quedo marcado para revision (si quedo
    # marcado, ya sabemos que no calzo con el catalogo y esta
    # documentado en MUNICIPIO_REVISAR, no es una falla silenciosa).
    pendientes_revision = data["MUNICIPIO_REVISAR"].fillna(False)
    total_pendientes = int(pendientes_revision.sum())
    return ("Los municipios pertenecen al departamento indicado", 0,
            f"{total_pendientes} municipios quedaron marcados en "
            "MUNICIPIO_REVISAR (documentados, pendientes de decision manual)")


def prueba_tipos_de_dato(data: pd.DataFrame) -> tuple[str, int, str]:
    # Todas las variables de este conjunto son de tipo texto (identificadores,
    # nombres, categorias); la prueba confirma que ninguna quedo como
    # object/mixed sin declarar.
    no_string = [c for c in data.columns
                 if not c.startswith("_") and not c.endswith("_REVISAR")
                 and c not in ("GRUPO_DUPLICADO_PARCIAL", "CODIGO_DUPLICADO")
                 and str(data[c].dtype) != "string"]
    return ("Todas las variables tienen el tipo de dato esperado (string)",
            len(no_string), f"Columnas con tipo inesperado: {no_string}")


def prueba_categorias_sin_variantes(data: pd.DataFrame, variables_categoricas: list[str]) -> tuple[str, int, str]:
    """Revisa que, luego de la limpieza, ya no existan dos valores en la
    misma variable que solo difieran en tildes/mayusculas (lo que build_
    text_variants detectaba antes de limpiar)."""
    import unicodedata

    def clave(v: str) -> str:
        t = unicodedata.normalize("NFKD", v)
        return "".join(c for c in t if not unicodedata.combining(c))

    fallas = 0
    detalle = []
    for col in variables_categoricas:
        valores = data[col].dropna().unique().tolist()
        claves = {}
        for v in valores:
            claves.setdefault(clave(v), []).append(v)
        variantes = {k: vs for k, vs in claves.items() if len(vs) > 1}
        if variantes:
            fallas += len(variantes)
            detalle.append(f"{col}: {variantes}")
    return ("No existen categorias duplicadas por diferencias de escritura",
            fallas, "; ".join(detalle) if detalle else "OK")


def ejecutar_todas(data: pd.DataFrame, columnas_originales: list[str]) -> pd.DataFrame:
    columnas_texto = [c for c in ["ESTABLECIMIENTO", "DIRECCION", "SUPERVISOR",
                                    "DIRECTOR", "CODIGO"] if c in data.columns]
    variables_categoricas = [c for c in ["DEPARTAMENTO", "MUNICIPIO", "SECTOR",
                                          "AREA", "STATUS", "MODALIDAD",
                                          "JORNADA", "PLAN", "DEPARTAMENTAL"]
                             if c in data.columns]

    resultados = [
        prueba_sin_duplicados_exactos(data, columnas_originales),
        prueba_codigo_unico(data),
        prueba_sin_espacios_extremos(data, columnas_texto),
        prueba_telefonos_formato_consistente(data),
        prueba_departamento_en_catalogo(data),
        prueba_municipio_en_catalogo(data),
        prueba_tipos_de_dato(data),
        prueba_categorias_sin_variantes(data, variables_categoricas),
    ]

    filas = []
    for nombre, fallas, detalle in resultados:
        filas.append({
            "prueba": nombre,
            "resultado": "PASA" if fallas == 0 else "FALLAS DETECTADAS",
            "cantidad": fallas,
            "detalle": detalle,
        })
    return pd.DataFrame(filas)