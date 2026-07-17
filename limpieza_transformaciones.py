"""Paso 5 y 6 de la guia: limpieza real del conjunto de datos + registro de
transformaciones.

Este modulo NO vuelve a implementar la carga/diagnostico (eso ya lo hace
`limpieza.py`); se importa desde ahi para reutilizar `missing_mask`,
`comparison_key`, etc. y no duplicar logica.

Diseno general:
- Cada funcion `limpiar_<variable>` recibe la Serie cruda y un `RegistroLog`
  donde anota (variable, problema, transformacion, registros_afectados,
  justificacion). Asi el log de transformaciones (paso 6) se arma solo,
  sin tener que llevarlo a mano por separado.
- Ninguna funcion elimina registros. Los "duplicados parciales" solo se
  MARCAN para revision humana (columna nueva), tal como pide la guia:
  "No elimine automaticamente los registros. Analice cada caso y
  documente la decision tomada."
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

from limpieza import missing_mask, comparison_key
import catalogo_geografico as geo

try:
    from rapidfuzz import fuzz
    _RAPIDFUZZ_DISPONIBLE = True
except ImportError:  # pragma: no cover - fallback si no esta instalado
    _RAPIDFUZZ_DISPONIBLE = False


# ---------------------------------------------------------------------------
# Registro de transformaciones (paso 6 de la guia)
# ---------------------------------------------------------------------------

@dataclass
class RegistroLog:
    """Acumula una fila por cada transformacion aplicada, para poder
    construir la tabla Variable/Problema/Transformacion/Registros
    afectados/Justificacion que pide el paso 6."""

    filas: list[dict] = field(default_factory=list)

    def anota(self, variable: str, problema: str, transformacion: str,
              registros_afectados: int, justificacion: str) -> None:
        # Se ignoran entradas con 0 registros afectados: si una regla no
        # tuvo que corregir nada, no aporta valor documentar que se aplico.
        if registros_afectados <= 0:
            return
        self.filas.append({
            "variable": variable,
            "problema_detectado": problema,
            "transformacion": transformacion,
            "registros_afectados": registros_afectados,
            "justificacion": justificacion,
        })

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.filas, columns=[
            "variable", "problema_detectado", "transformacion",
            "registros_afectados", "justificacion",
        ])


# ---------------------------------------------------------------------------
# Utilidades de texto compartidas
# ---------------------------------------------------------------------------

def _a_na(serie: pd.Series) -> pd.Series:
    """Convierte cadenas vacias y marcadores de faltante (N/A, ---, ., etc.)
    en pd.NA real, usando el mismo detector que el diagnostico
    (`missing_mask`) para que el criterio sea identico en ambas fases."""
    resultado = serie.astype("string").copy()
    resultado[missing_mask(serie)] = pd.NA
    return resultado


def _normaliza_espacios(serie: pd.Series) -> pd.Series:
    """Quita espacios al inicio/final y colapsa espacios multiples internos.
    No toca mayusculas/tildes: eso lo decide cada variable por separado
    porque no todas deben forzarse a mayusculas (ej. nombres propios se
    dejan como fueron capturados, solo se limpia el espaciado)."""
    sin_nbsp = serie.str.replace("\xa0", " ", regex=False)
    return sin_nbsp.str.strip().str.replace(r"\s{2,}", " ", regex=True)


def _a_mayusculas_normalizadas(serie: pd.Series) -> pd.Series:
    """Mayusculas + espacios limpios. Se usa en variables categoricas
    (DEPARTAMENTO, MUNICIPIO, SECTOR, AREA, STATUS, MODALIDAD, JORNADA,
    PLAN, DEPARTAMENTAL) donde la capitalizacion no aporta informacion y
    unificarla reduce categorias espurias como 'Guatemala' vs 'GUATEMALA'."""
    return _normaliza_espacios(serie).str.upper()


def _cuenta_diferencias(original: pd.Series, limpio: pd.Series) -> int:
    """Cuenta cuantos valores cambiaron (NA se trata como un valor mas,
    usando un marcador comun, para no fallar al comparar NA != NA)."""
    a = original.astype("string").fillna("<NA>")
    b = limpio.astype("string").fillna("<NA>")
    return int((a != b).sum())


# ---------------------------------------------------------------------------
# Eliminacion puntual de fuente: filas DEPARTAMENTO=GUATEMALA en
# establecimiento(8) (decision explicita de Mia, ver hilo de conversacion)
# ---------------------------------------------------------------------------

# Se identifico por inspeccion manual que este archivo especifico trae
# registros incompletos/duplicados para DEPARTAMENTO="GUATEMALA": el mismo
# conjunto de establecimientos ya esta completo en
# `_ARCHIVO_GUATEMALA_REFERENCIA` (ahi identificados como "CIUDAD CAPITAL",
# el pseudo-departamento que usa el MINEDUC para la capital). A diferencia
# del resto del pipeline, aqui SI se eliminan filas completas porque Mia
# confirmo explicitamente el criterio y que el reemplazo (archivo 5) ya
# cubre esos mismos establecimientos.
_ARCHIVO_GUATEMALA_INCOMPLETO = "establecimiento (8).xls"
_ARCHIVO_GUATEMALA_REFERENCIA = "establecimiento (5).xls"  # solo para el log/justificacion


def eliminar_filas_departamento_guatemala_archivo8(
    data: pd.DataFrame, log: RegistroLog,
) -> pd.DataFrame:
    """Elimina POR COMPLETO (todas sus columnas) las filas de
    `_ARCHIVO_GUATEMALA_INCOMPLETO` donde DEPARTAMENTO='GUATEMALA'.

    Debe ejecutarse ANTES del resto de la limpieza, sobre el DataFrame
    crudo/efectivo (con `_ARCHIVO_ORIGEN` todavia presente). Cambia la
    cantidad de registros del conjunto, por lo que queda documentado en
    el log de transformaciones (paso 6) y se reflejara en el conteo de
    'Registros: antes/despues' del informe de calidad (paso 8).
    """
    if "_ARCHIVO_ORIGEN" not in data.columns:
        return data

    depto_normalizado = _a_mayusculas_normalizadas(_a_na(data["DEPARTAMENTO"]))
    filas_a_eliminar = (
        (data["_ARCHIVO_ORIGEN"] == _ARCHIVO_GUATEMALA_INCOMPLETO)
        & (depto_normalizado == "GUATEMALA")
    )
    n = int(filas_a_eliminar.sum())
    if n == 0:
        return data

    log.anota(
        "(fila completa)",
        f"'{_ARCHIVO_GUATEMALA_INCOMPLETO}' trae registros incompletos/"
        f"duplicados para DEPARTAMENTO='GUATEMALA' (el mismo conjunto de "
        f"establecimientos ya esta completo en "
        f"'{_ARCHIVO_GUATEMALA_REFERENCIA}', ahi identificados como "
        "'CIUDAD CAPITAL')",
        "Se elimina la fila completa (todas sus columnas), no solo el "
        "valor de DEPARTAMENTO",
        n,
        "Decision explicita confirmada por la responsable del proyecto "
        "tras inspeccion manual de la fuente: conservarlas duplicaria "
        "informacion incompleta que ya existe completa en otro archivo. "
        "A diferencia del resto de duplicados del pipeline (que solo se "
        "marcan, nunca se eliminan), aqui si se justifica eliminar la "
        "fila completa porque ya se identifico con certeza el archivo "
        "de reemplazo.",
    )
    return data.loc[~filas_a_eliminar].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Limpieza por variable
# ---------------------------------------------------------------------------

def limpiar_codigo(serie: pd.Series, log: RegistroLog) -> pd.Series:
    """CODIGO: identificador de texto, no numerico. Solo se recorta
    espacios; NO se toca el formato de guiones porque codifica
    depto-distrito-establecimiento-nivel y alterarlo perderia esa
    informacion (ver plan de limpieza: 'convertirlo a numero podria
    eliminar ceros iniciales')."""
    original = serie.astype("string")
    limpio = original.str.strip()
    afectados = _cuenta_diferencias(original, limpio)
    log.anota(
        "CODIGO", "Posibles espacios al inicio/final",
        "strip() manteniendo el codigo como texto (con guiones y ceros "
        "a la izquierda intactos)",
        afectados,
        "El codigo es un identificador compuesto, no un numero; "
        "convertirlo perderia estructura y ceros iniciales.",
    )
    return limpio


def limpiar_distrito(serie: pd.Series, log: RegistroLog) -> pd.Series:
    """DISTRITO: mismo tratamiento que CODIGO (texto identificador) +
    conversion de marcadores de faltante a NA real."""
    original = serie.astype("string")
    sin_na = _a_na(original)
    limpio = sin_na.str.strip()
    faltantes = int(limpio.isna().sum())
    log.anota(
        "DISTRITO", "Valores faltantes representados como '', '-', 'N/A', etc.",
        "Unificados a NA real usando el mismo criterio del diagnostico "
        "(missing_mask)",
        faltantes,
        "Se documento en el diagnostico que DISTRITO tiene 532 "
        "faltantes/equivalentes; se preserva la cantidad pero como NA "
        "real para que pandas/analisis posteriores los reconozcan.",
    )
    return limpio


def limpiar_categorica(
    serie: pd.Series, nombre_variable: str, log: RegistroLog,
    correcciones_ortograficas: dict[str, str] | None = None,
) -> pd.Series:
    """Limpieza generica para variables categoricas simples (SECTOR, AREA,
    STATUS, NIVEL, JORNADA): mayusculas + espacios + correccion puntual de
    ortografia conocida (ej. MONOLINGUE -> MONOLINGÜE)."""
    original = serie.astype("string")
    sin_na = _a_na(original)
    mayus = _a_mayusculas_normalizadas(sin_na)

    corregido = mayus.copy()
    if correcciones_ortograficas:
        for incorrecto, correcto in correcciones_ortograficas.items():
            mask = mayus == incorrecto
            n = int(mask.sum())
            if n:
                corregido[mask] = correcto
                log.anota(
                    nombre_variable,
                    f"Grafia sin tilde/dieresis: '{incorrecto}'",
                    f"Reemplazado por la forma ortografica correcta "
                    f"'{correcto}'",
                    n,
                    "Es un error ortografico sistematico (falta la "
                    "dieresis/tilde), no una categoria distinta; "
                    "unificarlo no combina conceptos diferentes.",
                )

    espacios_afectados = _cuenta_diferencias(original.fillna(""), mayus.fillna(""))
    if espacios_afectados:
        log.anota(
            nombre_variable, "Mayusculas inconsistentes / espacios extra",
            "Se normaliza a mayusculas y se recortan espacios",
            espacios_afectados,
            "La variable es categorica; la capitalizacion no aporta "
            "informacion y genera categorias duplicadas si no se unifica.",
        )
    return corregido


def limpiar_departamento(serie: pd.Series, log: RegistroLog) -> tuple[pd.Series, pd.Series]:
    """DEPARTAMENTO: valida contra el catalogo oficial de 22 departamentos.

    Devuelve (serie_limpia, serie_flag_revision_manual). CIUDAD CAPITAL se
    reconoce como alias de GUATEMALA pero NO se sobrescribe automaticamente
    (queda con su valor original) y se marca en la columna de revision,
    respetando lo indicado en el plan de limpieza."""
    original = serie.astype("string")
    mayus = _a_mayusculas_normalizadas(_a_na(original))

    limpio = mayus.copy()
    revision_manual = pd.Series(False, index=serie.index)
    fuera_de_dominio = pd.Series(False, index=serie.index)

    tildes_corregidas = 0
    for idx, valor in mayus.items():
        if pd.isna(valor):
            continue
        canonico, requiere_revision = geo.validar_departamento(valor)
        if canonico is None:
            fuera_de_dominio.at[idx] = True
            continue
        if requiere_revision:
            revision_manual.at[idx] = True
            continue  # se deja el valor original, solo se marca
        if canonico != valor:
            tildes_corregidas += 1
        limpio.at[idx] = canonico

    if tildes_corregidas:
        log.anota(
            "DEPARTAMENTO", "Nombres sin tilde (ej. TOTONICAPAN, PETEN, QUICHE, SOLOLA)",
            "Se normaliza a la grafia oficial con tilde usando el catalogo "
            "de 22 departamentos",
            tildes_corregidas,
            "Son la misma entidad geografica; la tilde faltante es un "
            "problema de captura, no una categoria distinta.",
        )
    n_revision = int(revision_manual.sum())
    if n_revision:
        log.anota(
            "DEPARTAMENTO", "'CIUDAD CAPITAL' usado en lugar de 'GUATEMALA'",
            "NO se unifica automaticamente; se marca en "
            "DEPARTAMENTO_REVISAR para decision manual",
            n_revision,
            "Segun el plan de limpieza, unificar automaticamente podria "
            "borrar una clasificacion administrativa valida (zona "
            "metropolitana vs. resto del departamento); se deja a "
            "criterio humano.",
        )
    n_fuera = int(fuera_de_dominio.sum())
    if n_fuera:
        log.anota(
            "DEPARTAMENTO", "Valor no reconocido en el catalogo de 22 departamentos",
            "Se deja el valor original y se marca DEPARTAMENTO_REVISAR",
            n_fuera,
            "No se puede corregir con seguridad sin saber la intencion "
            "original; se documenta para revision manual en vez de "
            "adivinar.",
        )

    return limpio, (revision_manual | fuera_de_dominio)


def limpiar_municipio(
    departamento_limpio: pd.Series, municipio: pd.Series, log: RegistroLog,
) -> tuple[pd.Series, pd.Series]:
    """MUNICIPIO: valida que exista dentro del departamento ya limpio.
    Devuelve (serie_limpia, flag_revision_manual)."""
    original = municipio.astype("string")
    mayus = _a_mayusculas_normalizadas(_a_na(original))

    limpio = mayus.copy()
    revision_manual = pd.Series(False, index=municipio.index)
    corregidos = 0

    for idx in mayus.index:
        valor = mayus.at[idx]
        depto = departamento_limpio.at[idx]
        if pd.isna(valor) or pd.isna(depto):
            continue
        canonico = geo.validar_municipio(depto, valor)
        if canonico is None:
            revision_manual.at[idx] = True
            continue
        if canonico != valor:
            corregidos += 1
        limpio.at[idx] = canonico

    if corregidos:
        log.anota(
            "MUNICIPIO", "Grafia distinta a la oficial (tildes/mayusculas)",
            "Se normaliza a la grafia oficial validando contra el "
            "municipio correspondiente dentro del mismo departamento",
            corregidos,
            "El catalogo geografico permite distinguir, por ejemplo, "
            "'San Jose' de Escuintla vs. 'San Jose' de Peten sin "
            "confundirlos, porque se valida junto con DEPARTAMENTO.",
        )
    n_revision = int(revision_manual.sum())
    if n_revision:
        log.anota(
            "MUNICIPIO",
            "No coincide con ningun municipio del departamento indicado",
            "Se deja el valor original y se marca MUNICIPIO_REVISAR",
            n_revision,
            "Puede ser un error de captura o una variante del catalogo "
            "que no cubrimos (municipios de creacion reciente); se deja "
            "para revision manual en vez de forzar una correccion.",
        )
    return limpio, revision_manual


_PALABRAS_TELEFONO_A_DESCARTAR = re.compile(
    r"\b(FAX|EXT\.?|EXTENSION|TEL|TELEFONO|AL|Y|CEL|CELULAR)\b", re.IGNORECASE
)


def limpiar_telefono(serie: pd.Series, log: RegistroLog) -> tuple[pd.Series, pd.Series]:
    """TELEFONO: puede traer varios numeros en una celda, separadores
    mixtos (coma, guion, '/', 'Y') y palabras como FAX/EXT. Se separan los
    numeros, se valida que cada uno tenga 8 digitos (formato guatemalteco
    actual) y se reconstruye la celda con los numeros separados por ' / '.

    Devuelve (serie_limpia, flag_formato_no_valido). No se inventan
    digitos faltantes ni se recortan numeros de 7 digitos (podrian ser
    numeros antiguos reales); solo se marca la fila para revision."""
    original = serie.astype("string")
    sin_na = _a_na(original)

    limpio = pd.Series(pd.NA, index=serie.index, dtype="string")
    formato_no_valido = pd.Series(False, index=serie.index)
    reformateados = 0

    for idx, valor in sin_na.items():
        if pd.isna(valor):
            continue
        texto = _PALABRAS_TELEFONO_A_DESCARTAR.sub(" ", valor)
        numeros = re.findall(r"\d{4,}", texto)

        if not numeros:
            # No se reconocio ningun numero: se deja el texto original y
            # se marca para revision en vez de descartarlo.
            formato_no_valido.at[idx] = True
            limpio.at[idx] = valor.strip()
            continue

        valor_reescrito = " / ".join(numeros)
        limpio.at[idx] = valor_reescrito
        if valor_reescrito != valor.strip():
            reformateados += 1
        if any(len(n) != 8 for n in numeros):
            formato_no_valido.at[idx] = True

    if reformateados:
        log.anota(
            "TELEFONO", "Multiples numeros por celda y separadores inconsistentes "
            "(comas, guiones, 'Y', 'FAX', 'EXT')",
            "Se extraen solo los digitos de cada numero y se reescriben "
            "separados por ' / ', descartando palabras de relleno",
            reformateados,
            "Preserva todos los numeros originales (no se eliminan "
            "extensiones ni numeros adicionales) pero en un formato "
            "consistente y parseable.",
        )
    n_invalidos = int(formato_no_valido.sum())
    if n_invalidos:
        log.anota(
            "TELEFONO", "Numero con longitud distinta a 8 digitos, o sin digitos reconocibles",
            "Se deja el valor y se marca TELEFONO_REVISAR",
            n_invalidos,
            "Podria ser un numero antiguo de 7 digitos, un error de "
            "captura o texto sin numero; no se descarta el dato, solo "
            "se marca para que un humano decida.",
        )
    return limpio, formato_no_valido


def limpiar_texto_libre(serie: pd.Series, nombre_variable: str, log: RegistroLog) -> pd.Series:
    """ESTABLECIMIENTO, DIRECCION, SUPERVISOR, DIRECTOR: nombres propios y
    direcciones. Por decision explicita de Mia, TODO el texto del
    conjunto se sube a mayusculas (incluidos estos campos). Las TILDES SI
    se conservan (mayusculas no las elimina), solo cambia la
    capitalizacion; se normalizan tambien espacios y caracteres
    invisibles.

    Riesgo documentado: subir a mayusculas es reversible y de bajo riesgo
    (no borra informacion, solo capitalizacion), a diferencia de intentar
    corregir ortografia o tildes automaticamente en nombres propios, que
    si se evita en esta funcion."""
    original = serie.astype("string")
    sin_na = _a_na(original)
    limpio = _a_mayusculas_normalizadas(sin_na)
    afectados = _cuenta_diferencias(original.fillna(""), limpio.fillna(""))
    if afectados:
        log.anota(
            nombre_variable, "Mayusculas inconsistentes, espacios extra, "
            "NBSP invisible o marcadores de faltante",
            "Se convierte a mayusculas, se recortan espacios y se "
            "convierten marcadores de faltante a NA; las tildes SI se "
            "conservan (no se tocan, solo la capitalizacion)",
            afectados,
            "Es un nombre propio o direccion, por lo que no se corrige "
            "ortografia ni se quitan tildes automaticamente (ver riesgo "
            "en el plan de limpieza); subir a mayusculas es una "
            "normalizacion de bajo riesgo pedida explicitamente para "
            "mantener consistencia con el resto del conjunto.",
        )
    return limpio


# ---------------------------------------------------------------------------
# Duplicados por CODIGO repetido (paso 5.h: consistencia entre variables)
# ---------------------------------------------------------------------------

def detectar_duplicados_por_codigo(data: pd.DataFrame, log: RegistroLog) -> pd.Series:
    """CODIGO deberia ser unico por establecimiento. Se encontraron casos
    (ver imagen de ejemplo: CODIGO '01-627' repetido con STATUS
    'CERRADA TEMPORALMENTE' en una fila y 'CERRADA DEFINITIVAMENTE' en
    otra) donde el mismo CODIGO aparece en mas de una fila con datos que
    se contradicen. Se marca CODIGO_DUPLICADO=True en TODAS las filas
    involucradas para revision manual; no se elimina ni se decide
    automaticamente cual version es la vigente."""
    codigo = data["CODIGO"].astype("string").str.strip()
    duplicado = codigo.notna() & codigo.duplicated(keep=False)
    n = int(duplicado.sum())
    if n:
        n_codigos = int(codigo[duplicado].nunique())
        log.anota(
            "CODIGO",
            "El mismo CODIGO aparece en mas de una fila, con valores "
            "distintos en otras variables (ej. STATUS, JORNADA, PLAN)",
            "Se marca CODIGO_DUPLICADO=True en todas las filas "
            "involucradas para revision manual; ninguna fila se elimina "
            "ni se fusiona automaticamente",
            n,
            f"CODIGO es el identificador unico del establecimiento "
            f"({n_codigos} codigos distintos estan repetidos); que "
            "aparezca mas de una vez con datos distintos sugiere "
            "exportaciones del sistema del MINEDUC en momentos distintos "
            "(ej. un establecimiento que cambio de estado), y decidir "
            "cual version es la vigente requiere criterio humano.",
        )
    return duplicado


# ---------------------------------------------------------------------------
# Duplicados parciales (paso 5.g.2): similitud de cadenas
# ---------------------------------------------------------------------------

# Palabras genericas de "tipo de institucion" que NO ayudan a distinguir un
# establecimiento de otro (ej. "INSTITUTO SAN CARLOS" / "COLEGIO SAN
# CARLOS" / "SAN CARLOS" son, muy probablemente, el mismo establecimiento
# escrito de tres formas distintas). Se quitan SOLO para calcular la clave
# de similitud (deteccion); el nombre original en ESTABLECIMIENTO nunca se
# modifica con esta lista.
_PALABRAS_TIPO_INSTITUCION = {
    "INSTITUTO", "COLEGIO", "ESCUELA", "LICEO", "ACADEMIA", "CENTRO",
    "EDUCATIVO", "EDUCATIVA", "NACIONAL", "MIXTO", "MIXTA", "PRIVADO",
    "PRIVADA", "COOPERATIVA", "OFICIAL", "PARTICULAR", "COLEGIO.",
}

