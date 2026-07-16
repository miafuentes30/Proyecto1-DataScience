"""Catalogo oficial de departamentos y municipios de Guatemala.

Fuente: Catalogo de Departamentos y Municipios de Guatemala (INE / codigos
administrativos estandar, 22 departamentos - 340 municipios). Se usa como
dominio de referencia para la validacion de las variables DEPARTAMENTO y
MUNICIPIO durante la limpieza (paso 5.f de la guia: "valores fuera de
dominio").

IMPORTANTE: los nombres aqui estan en MAYUSCULAS y SIN el articulo "EL/LA"
inicial (ej. "PETEN" en vez de "EL PETEN", "QUICHE" en vez de "EL QUICHE"),
porque asi es como el sistema del MINEDUC los reporta en el campo
DEPARTAMENTO. Se incluyen alias para reconocer variantes comunes.
"""

from __future__ import annotations

import unicodedata


def _normaliza(texto: str) -> str:
    """Clave de comparacion: mayusculas, sin tildes, espacios colapsados.

    Se usa la MISMA logica que `comparison_key` en limpieza.py para que un
    valor como 'Peten', 'PETÉN' o 'petén ' generen la misma clave y así
    puedan compararse contra el catálogo sin importar tildes/espacios.
    """
    t = unicodedata.normalize("NFKD", texto.strip().upper())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.split())


# Nombre canonico (con tilde correcta) que se escribira en el dato limpio,
# por cada departamento. El orden sigue el codigo INE 01-22.
DEPARTAMENTOS: list[str] = [
    "GUATEMALA",
    "EL PROGRESO",
    "SACATEPEQUEZ".replace("E", "É", 1),  # placeholder no usado, ver abajo
]

# Se define explicitamente (evita errores de reemplazo automatico de tildes)
DEPARTAMENTOS = [
    "GUATEMALA",
    "EL PROGRESO",
    "SACATEPÉQUEZ",
    "CHIMALTENANGO",
    "ESCUINTLA",
    "SANTA ROSA",
    "SOLOLÁ",
    "TOTONICAPÁN",
    "QUETZALTENANGO",
    "SUCHITEPÉQUEZ",
    "RETALHULEU",
    "SAN MARCOS",
    "HUEHUETENANGO",
    "QUICHÉ",
    "BAJA VERAPAZ",
    "ALTA VERAPAZ",
    "PETÉN",
    "IZABAL",
    "ZACAPA",
    "CHIQUIMULA",
    "JALAPA",
    "JUTIAPA",
]

# Alias conocidos -> nombre canonico. No se aplican automaticamente sobre
# CIUDAD CAPITAL (esa unificacion queda para revision manual, tal como se
# documento en el plan de limpieza), pero si sirven para reconocer que el
# valor SI pertenece al dominio, solo que con otra grafia/variante.
_ALIAS_DEPARTAMENTO = {
    "EL PETEN": "PETÉN",
    "PETEN": "PETÉN",
    "EL QUICHE": "QUICHÉ",
    "QUICHE": "QUICHÉ",
    "SOLOLA": "SOLOLÁ",
    "TOTONICAPAN": "TOTONICAPÁN",
    "SACATEPEQUEZ": "SACATEPÉQUEZ",
    "SUCHITEPEQUEZ": "SUCHITEPÉQUEZ",
}

# Casos que SI aparecen en el dominio pero requieren decision manual (no se
# unifican automaticamente; ver plan de limpieza, variable DEPARTAMENTO).
ALIAS_REVISION_MANUAL = {
    "CIUDAD CAPITAL": "GUATEMALA",
}

DEPARTAMENTO_KEY_A_CANONICO: dict[str, str] = {}
for nombre in DEPARTAMENTOS:
    DEPARTAMENTO_KEY_A_CANONICO[_normaliza(nombre)] = nombre
for alias, destino in _ALIAS_DEPARTAMENTO.items():
    DEPARTAMENTO_KEY_A_CANONICO[_normaliza(alias)] = destino


# Municipios por departamento (nombre canonico con tilde correcta).
# Codigos INE 01-22, en el mismo orden que DEPARTAMENTOS.
MUNICIPIOS_POR_DEPARTAMENTO: dict[str, list[str]] = {
    "GUATEMALA": [
        "GUATEMALA", "SANTA CATARINA PINULA", "SAN JOSÉ PINULA",
        "SAN JOSÉ DEL GOLFO", "PALENCIA", "CHINAUTLA", "SAN PEDRO AYAMPUC",
        "MIXCO", "SAN PEDRO SACATEPÉQUEZ", "SAN JUAN SACATEPÉQUEZ",
        "SAN RAIMUNDO", "CHUARRANCHO", "FRAIJANES", "AMATITLÁN",
        "VILLA NUEVA", "VILLA CANALES", "PETAPA",
    ],
    "EL PROGRESO": [
        "GUASTATOYA", "MORAZÁN", "SAN AGUSTÍN ACASAGUASTLÁN",
        "SAN CRISTÓBAL ACASAGUASTLÁN", "EL JÍCARO", "SANSARE", "SANARATE",
        "SAN ANTONIO LA PAZ",
    ],
    "SACATEPÉQUEZ": [
        "ANTIGUA GUATEMALA", "JOCOTENANGO", "PASTORES", "SUMPANGO",
        "SANTO DOMINGO XENACOJ", "SANTIAGO SACATEPÉQUEZ",
        "SAN BARTOLOMÉ MILPAS ALTAS", "SAN LUCAS SACATEPÉQUEZ",
        "SANTA LUCÍA MILPAS ALTAS", "MAGDALENA MILPAS ALTAS",
        "SANTA MARÍA DE JESÚS", "CIUDAD VIEJA", "SAN MIGUEL DUEÑAS",
        "ALOTENANGO", "SAN ANTONIO AGUAS CALIENTES", "SANTA CATARINA BARAHONA",
    ],
    "CHIMALTENANGO": [
        "CHIMALTENANGO", "SAN JOSÉ POAQUIL", "SAN MARTÍN JILOTEPEQUE",
        "COMALAPA", "SANTA APOLONIA", "TECPÁN GUATEMALA", "PATZÚN",
        "POCHUTA", "PATZICÍA", "SANTA CRUZ BALANYÁ", "ACATENANGO",
        "YEPOCAPA", "SAN ANDRÉS ITZAPA", "PARRAMOS", "ZARAGOZA", "EL TEJAR",
    ],
    "ESCUINTLA": [
        "ESCUINTLA", "SANTA LUCÍA COTZUMALGUAPA", "LA DEMOCRACIA",
        "SIQUINALÁ", "MASAGUA", "TIQUISATE", "LA GOMERA", "GUANAGAZAPA",
        "SAN JOSÉ", "IZTAPA", "PALÍN", "SAN VICENTE PACAYA",
        "NUEVA CONCEPCIÓN",
    ],
    "SANTA ROSA": [
        "CUILAPA", "BARBERENA", "SANTA ROSA DE LIMA", "CASILLAS",
        "SAN RAFAEL LAS FLORES", "ORATORIO", "SAN JUAN TECUACO",
        "CHIQUIMULILLA", "TAXISCO", "SANTA MARÍA IXHUATÁN", "GUAZACAPÁN",
        "SANTA CRUZ NARANJO", "PUEBLO NUEVO VIÑAS", "NUEVA SANTA ROSA",
    ],
    "SOLOLÁ": [
        "SOLOLÁ", "SAN JOSÉ CHACAYÁ", "SANTA MARÍA VISITACIÓN",
        "SANTA LUCÍA UTATLÁN", "NAHUALÁ", "SANTA CATARINA IXTAHUACÁN",
        "SANTA CLARA LA LAGUNA", "CONCEPCIÓN", "SAN ANDRÉS SEMETABAJ",
        "PANAJACHEL", "SANTA CATARINA PALOPÓ", "SAN ANTONIO PALOPÓ",
        "SAN LUCAS TOLIMÁN", "SANTA CRUZ LA LAGUNA", "SAN PABLO LA LAGUNA",
        "SAN MARCOS LA LAGUNA", "SAN JUAN LA LAGUNA", "SAN PEDRO LA LAGUNA",
        "SANTIAGO ATITLÁN",
    ],
    "TOTONICAPÁN": [
        "TOTONICAPÁN", "SAN CRISTÓBAL TOTONICAPÁN", "SAN FRANCISCO EL ALTO",
        "SAN ANDRÉS XECUL", "MOMOSTENANGO", "SANTA MARÍA CHIQUIMULA",
        "SANTA LUCÍA LA REFORMA", "SAN BARTOLO",
    ],
    "QUETZALTENANGO": [
        "QUETZALTENANGO", "SALCAJÁ", "OLINTEPEQUE", "SAN CARLOS SIJA",
        "SIBILIA", "CABRICÁN", "CAJOLÁ", "SAN MIGUEL SIGÜILÁ", "OSTUNCALCO",
        "SAN MATEO", "CONCEPCIÓN CHIQUIRICHAPA", "SAN MARTÍN SACATEPÉQUEZ",
        "ALMOLONGA", "CANTEL", "HUITÁN", "ZUNIL", "COLOMBA",
        "SAN FRANCISCO LA UNIÓN", "EL PALMAR", "COATEPEQUE", "GÉNOVA",
        "FLORES COSTA CUCA", "LA ESPERANZA", "PALESTINA DE LOS ALTOS",
    ],
    "SUCHITEPÉQUEZ": [
        "MAZATENANGO", "CUYOTENANGO", "SAN FRANCISCO ZAPOTITLÁN",
        "SAN BERNARDINO", "SAN JOSÉ EL ÍDOLO", "SANTO DOMINGO SUCHITEPÉQUEZ",
        "SAN LORENZO", "SAMAYAC", "SAN PABLO JOCOPILAS",
        "SAN ANTONIO SUCHITEPÉQUEZ", "SAN MIGUEL PANÁN", "SAN GABRIEL",
        "CHICACAO", "PATULUL", "SANTA BÁRBARA", "SAN JUAN BAUTISTA",
        "SANTO TOMÁS LA UNIÓN", "ZUNILITO", "PUEBLO NUEVO", "RÍO BRAVO",
    ],
    "RETALHULEU": [
        "RETALHULEU", "SAN SEBASTIÁN", "SANTA CRUZ MULUÁ",
        "SAN MARTÍN ZAPOTITLÁN", "SAN FELIPE", "SAN ANDRÉS VILLA SECA",
        "CHAMPERICO", "NUEVO SAN CARLOS", "EL ASINTAL",
    ],
    "SAN MARCOS": [
        "SAN MARCOS", "SAN PEDRO SACATEPÉQUEZ", "SAN ANTONIO SACATEPÉQUEZ",
        "COMITANCILLO", "SAN MIGUEL IXTAHUACÁN", "CONCEPCIÓN TUTUAPA",
        "TACANÁ", "SIBINAL", "TAJUMULCO", "TEJUTLA",
        "SAN RAFAEL PIE DE LA CUESTA", "NUEVO PROGRESO", "EL TUMBADOR",
        "EL RODEO", "MALACATÁN", "CATARINA", "AYUTLA", "OCÓS", "SAN PABLO",
        "EL QUETZAL", "LA REFORMA", "PAJAPITA", "IXCHIGUÁN",
        "SAN JOSÉ OJETENAM", "SAN CRISTÓBAL CUCHO", "SIPACAPA",
        "ESQUIPULAS PALO GORDO", "RÍO BLANCO", "SAN LORENZO",
        "NUEVO SAN MARCOS",
    ],
    "HUEHUETENANGO": [
        "HUEHUETENANGO", "CHIANTLA", "MALACATANCITO", "CUILCO", "NENTÓN",
        "SAN PEDRO NECTA", "JACALTENANGO", "SOLOMA", "SAN JUAN IXTAHUACÁN",
        "SANTA BÁRBARA", "LA LIBERTAD", "LA DEMOCRACIA", "SAN MIGUEL ACATÁN",
        "SAN RAFAEL LA INDEPENDENCIA", "TODOS SANTOS CUCHUMATANES",
        "SAN JUAN ATITÁN", "SANTA EULALIA", "SAN MATEO IXTATÁN",
        "COLOTENANGO", "SAN SEBASTIÁN HUEHUETENANGO", "TECTITÁN",
        "CONCEPCIÓN HUISTA", "SAN JUAN IXCOY", "SAN ANTONIO HUISTA",
        "SAN SEBASTIÁN COATÁN", "BARILLAS", "AGUACATÁN", "SAN RAFAEL PETZAL",
        "SAN GASPAR IXCHIL", "SANTIAGO CHIMALTENANGO", "SANTA ANA HUISTA",
        "UNIÓN CANTINIL",
    ],
    "QUICHÉ": [
        "SANTA CRUZ DEL QUICHÉ", "CHICHÉ", "CHINIQUE", "ZACUALPA", "CHAJUL",
        "CHICHICASTENANGO", "PATZITÉ", "SAN ANTONIO ILOTENANGO",
        "SAN PEDRO JOCOPILAS", "CUNÉN", "SAN JUAN COTZAL", "JOYABAJ",
        "NEBAJ", "SAN ANDRÉS SAJCABAJÁ", "USPANTÁN", "SACAPULAS",
        "SAN BARTOLOMÉ JOCOTENANGO", "CANILLÁ", "CHICAMÁN", "IXCÁN",
        "PACHALUM",
    ],
    "BAJA VERAPAZ": [
        "SALAMÁ", "SAN MIGUEL CHICAJ", "RABINAL", "CUBULCO", "GRANADOS",
        "EL CHOL", "SAN JERÓNIMO", "PURULHÁ",
    ],
    "ALTA VERAPAZ": [
        "COBÁN", "SANTA CRUZ VERAPAZ", "SAN CRISTÓBAL VERAPAZ", "TACTIC",
        "TAMAHÚ", "TUCURÚ", "PANZÓS", "SENAHÚ", "SAN PEDRO CARCHÁ",
        "SAN JUAN CHAMELCO", "LANQUÍN", "CAHABÓN", "CHISEC", "CHAHAL",
        "FRAY BARTOLOMÉ DE LAS CASAS", "SANTA CATALINA LA TINTA",
        "RAXRUHÁ",
    ],
    "PETÉN": [
        "FLORES", "SAN JOSÉ", "SAN BENITO", "SAN ANDRÉS", "LA LIBERTAD",
        "SAN FRANCISCO", "SANTA ANA", "DOLORES", "SAN LUIS", "SAYAXCHÉ",
        "MELCHOR DE MENCOS", "POPTÚN", "LAS CRUCES", "EL CHAL",
    ],
    "IZABAL": [
        "PUERTO BARRIOS", "LIVINGSTON", "EL ESTOR", "MORALES", "LOS AMATES",
    ],
    "ZACAPA": [
        "ZACAPA", "ESTANZUELA", "RÍO HONDO", "GUALÁN", "TECULUTÁN",
        "USUMATLÁN", "CABAÑAS", "SAN DIEGO", "LA UNIÓN", "HUITÉ",
    ],
    "CHIQUIMULA": [
        "CHIQUIMULA", "SAN JOSÉ LA ARADA", "SAN JUAN ERMITA", "JOCOTÁN",
        "CAMOTÁN", "OLOPA", "ESQUIPULAS", "CONCEPCIÓN LAS MINAS",
        "QUETZALTEPEQUE", "SAN JACINTO", "IPALA",
    ],
    "JALAPA": [
        "JALAPA", "SAN PEDRO PINULA", "SAN LUIS JILOTEPEQUE",
        "SAN MANUEL CHAPARRÓN", "SAN CARLOS ALZATATE", "MONJAS",
        "MATAQUESCUINTLA",
    ],
    "JUTIAPA": [
        "JUTIAPA", "EL PROGRESO", "SANTA CATARINA MITA", "AGUA BLANCA",
        "ASUNCIÓN MITA", "YUPILTEPEQUE", "ATESCATEMPA", "JEREZ",
        "EL ADELANTO", "ZAPOTITLÁN", "COMAPA", "JALPATAGUA", "CONGUACO",
        "MOYUTA", "PASACO", "SAN JOSÉ ACATEMPA", "QUESADA",
    ],
}

# Indice de busqueda: (clave_departamento, clave_municipio) -> nombre canonico
# Se indexa por clave normalizada (sin tildes) del departamento porque asi
# es como llega DEPARTAMENTO en los datos crudos (ej. "TOTONICAPAN").
MUNICIPIO_KEY_A_CANONICO: dict[tuple[str, str], str] = {}
for depto, municipios in MUNICIPIOS_POR_DEPARTAMENTO.items():
    clave_depto = _normaliza(depto)
    for municipio in municipios:
        MUNICIPIO_KEY_A_CANONICO[(clave_depto, _normaliza(municipio))] = municipio


def validar_departamento(valor: str) -> tuple[str | None, bool]:
    """Devuelve (nombre_canonico_o_None, requiere_revision_manual).

    Si el valor pertenece al dominio (incluyendo alias conocidos como
    'TOTONICAPAN' sin tilde), regresa el nombre canonico y False.
    Si el valor es un alias marcado para revision manual (ej. 'CIUDAD
    CAPITAL'), regresa el nombre canonico sugerido pero con True, para que
    NO se sobrescriba automaticamente.
    Si no pertenece al dominio, regresa (None, False).
    """
    clave = _normaliza(valor)
    if clave in DEPARTAMENTO_KEY_A_CANONICO:
        return DEPARTAMENTO_KEY_A_CANONICO[clave], False

    for alias, destino in ALIAS_REVISION_MANUAL.items():
        if _normaliza(alias) == clave:
            return destino, True

    return None, False


def validar_municipio(departamento_canonico: str, valor: str) -> str | None:
    """Devuelve el nombre canonico del municipio si pertenece al
    departamento dado, o None si no se reconoce (fuera de dominio o
    departamento incorrecto)."""
    clave = (_normaliza(departamento_canonico), _normaliza(valor))
    return MUNICIPIO_KEY_A_CANONICO.get(clave)
