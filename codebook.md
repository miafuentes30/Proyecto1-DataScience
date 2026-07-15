# Libro de Codigos (Codebook)

## Proyecto 1: Obtencion y Limpieza de Datos
## Establecimientos educativos de Guatemala, nivel Diversificado

Universidad del Valle de Guatemala. Facultad de Ingenieria. Departamento de
Ciencias de la Computacion. CC3084 - Data Science. Semestre II - 2026.

---

## 1. Informacion general del conjunto de datos

**Fuente de los datos:** Sistema de busqueda de establecimientos del
Ministerio de Educacion de Guatemala (MINEDUC).
http://www.mineduc.gob.gt/BUSCAESTABLECIMIENTO_GE/

**Criterio de descarga:** Establecimientos con NIVEL ESCOLAR = DIVERSIFICADO,
de todos los departamentos del pais.

**Formato original:** 23 archivos con extension `.xls`, que en realidad son
documentos HTML exportados por la plataforma del MINEDUC (no son archivos
binarios de Excel).

**Fecha de extraccion:** [completar con la fecha en que se descargaron los
23 archivos .xls]

**Unidad de observacion:** un establecimiento educativo con nivel
Diversificado, identificado por su CODIGO.

**Alcance geografico:** los 22 departamentos de Guatemala.

**Version del conjunto limpio:** v1.0

**Herramientas utilizadas:** Python 3, pandas, rapidfuzz (para similitud de
cadenas en la deteccion de duplicados parciales).

**Codigo del proceso:** el pipeline completo (carga, diagnostico, limpieza,
validacion e informe de calidad) esta implementado en 5 modulos:

- `limpieza.py`: carga de los 23 archivos y diagnostico inicial.
- `catalogo_geografico.py`: catalogo oficial de 22 departamentos y 340
  municipios de Guatemala, usado como dominio de referencia.
- `limpieza_transformaciones.py`: limpieza variable por variable y registro
  de transformaciones.
- `validacion.py`: pruebas automaticas de calidad sobre el conjunto limpio.
- `pipeline.py`: orquesta todo el proceso de principio a fin y genera los
  archivos de salida.

---

## 2. Estructura del archivo de datos

**Registros efectivos:** 11,867 (de 11,890 filas crudas extraidas de los 23
archivos; se descartaron 23 filas completamente vacias, una por archivo).
Este numero cambia despues de la limpieza porque se eliminan las filas de
`establecimiento (8).xls` con DEPARTAMENTO='GUATEMALA' (ver seccion 5).

**Variables originales:** 17.

**Variables derivadas agregadas durante la limpieza:** 6 (ver seccion 4).

**Variables tecnicas de trazabilidad:** 2 (`_ARCHIVO_ORIGEN`,
`_FILA_ORIGEN`). No se cuentan como variables analiticas del conjunto,
existen unicamente para poder rastrear de que archivo y fila vino cada
registro.

**Formato de salida:** CSV, codificacion UTF-8 con BOM (utf-8-sig), separado
por comas.

---

## 3. Diccionario de variables originales

### CODIGO

- Descripcion: codigo unico de identificacion del establecimiento asignado
  por el MINEDUC.
- Tipo de dato: texto (string).
- Dominio permitido: cadena alfanumerica con guiones. El formato varia segun
  el archivo de origen (por ejemplo, `01-403`, `10-01-0511`,
  `00-01-0158-46`); no existe un patron unico de longitud fija en la fuente.
- Valores posibles: unico por establecimiento en la practica (0 valores
  faltantes, 11,867 valores unicos sobre 11,867 registros).
- Tratamiento aplicado: se recorta espacios en blanco y caracteres
  invisibles; no se reformatea el codigo en si, porque no hay un formato
  unico documentado que aplique a los 23 archivos.
- Variable derivada asociada: `CODIGO_DUPLICADO` (ver seccion 4).

### DISTRITO

- Descripcion: codigo del distrito educativo al que pertenece el
  establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: codigo alfanumerico; se observaron longitudes de 3, 6 y
  10 caracteres en la fuente original.
- Valores faltantes: 532 (4.48% del total).
- Tratamiento aplicado: se convierten a NA los marcadores de ausencia de
  dato (vacio, "-", "N/A", etc.), se recortan espacios. No se completa ni se
  infiere un distrito faltante.

### DEPARTAMENTO

- Descripcion: departamento de Guatemala donde se ubica el establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: los 22 departamentos oficiales de Guatemala (catalogo
  INE), definidos en `catalogo_geografico.py`.
- Valores posibles: GUATEMALA, EL PROGRESO, SACATEPEQUEZ, CHIMALTENANGO,
  ESCUINTLA, SANTA ROSA, SOLOLA, TOTONICAPAN, QUETZALTENANGO,
  SUCHITEPEQUEZ, RETALHULEU, SAN MARCOS, HUEHUETENANGO, QUICHE, BAJA
  VERAPAZ, ALTA VERAPAZ, PETEN, IZABAL, ZACAPA, CHIQUIMULA, JALAPA, JUTIAPA
  (nombres canonicos con tilde donde corresponde).
- Tratamiento aplicado: se convierte a mayusculas, se recortan espacios y se
  corrigen variantes sin tilde contra el catalogo (por ejemplo,
  TOTONICAPAN, PETEN, QUICHE, SOLOLA pasan a su forma con tilde).
- Caso especial: el valor CIUDAD CAPITAL se reconoce como un alias
  administrativo de GUATEMALA, pero NO se unifica automaticamente; el valor
  original se conserva y se marca en `DEPARTAMENTO_REVISAR` para decision
  manual. Se confirmo que el MINEDUC usa un pseudo-codigo distinto ("00")
  para estos registros, lo que sugiere una clasificacion administrativa
  propia y no un simple error de escritura.
- Variable derivada asociada: `DEPARTAMENTO_REVISAR`.

### MUNICIPIO

- Descripcion: municipio donde se ubica el establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: los 340 municipios oficiales de Guatemala, agrupados
  por departamento, definidos en `catalogo_geografico.py`.
- Tratamiento aplicado: se convierte a mayusculas, se recortan espacios y se
  valida contra el catalogo de municipios correspondiente al DEPARTAMENTO ya
  limpio de la misma fila (esto evita confundir, por ejemplo, un municipio
  llamado igual en dos departamentos distintos).
- Caso especial: en los registros donde DEPARTAMENTO quedo marcado como
  CIUDAD CAPITAL, la variable MUNICIPIO no contiene nombres de municipio
  sino identificadores de zona de la ciudad capital (por ejemplo, "ZONA 1",
  "ZONA 10"). Esto es una estructura de datos distinta a la del resto del
  conjunto y queda documentada y marcada, no forzada contra el catalogo de
  municipios.
- Variable derivada asociada: `MUNICIPIO_REVISAR`.

### ESTABLECIMIENTO

- Descripcion: nombre oficial del establecimiento educativo.
- Tipo de dato: texto (string).
- Dominio permitido: texto libre, sin catalogo cerrado.
- Valores faltantes: 5 (0.04% del total).
- Tratamiento aplicado: se convierte a mayusculas (decision explicita para
  mantener consistencia con el resto del conjunto), se recortan espacios
  multiples, dobles y caracteres invisibles. No se corrige ortografia ni se
  eliminan tildes de forma automatica, para no alterar un nombre propio.
- Variable derivada asociada: `GRUPO_DUPLICADO_PARCIAL` (ver seccion 4).

### DIRECCION

- Descripcion: direccion fisica del establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: texto libre, sin catalogo cerrado.
- Valores faltantes: 85 (0.72% del total).
- Tratamiento aplicado: se convierte a mayusculas, se recortan espacios y
  caracteres invisibles. No se normaliza abreviaturas (por ejemplo "ZONA"
  vs "Z.") de forma automatica, por el riesgo de alterar la ubicacion
  original.
- Variable derivada asociada: `GRUPO_DUPLICADO_PARCIAL` (ver seccion 4).

### TELEFONO

- Descripcion: numero o numeros telefonicos registrados para el
  establecimiento.
- Tipo de dato: texto (string). Se mantiene como texto y no como numero
  porque puede contener varios numeros y separadores.
- Dominio permitido: uno o mas grupos de 8 digitos, separados por " / ".
- Valores faltantes: 946 (7.97% del total).
- Tratamiento aplicado: se eliminan palabras como FAX, EXT., TEL,
  TELEFONO, AL, Y, CEL, CELULAR; se separan multiples numeros detectados en
  una misma celda y se reformatean como grupos de 8 digitos unidos por
  " / ". Los valores que no se pueden interpretar con confianza (menos de 8
  digitos, mas de 8 digitos sin poder separarlos, numeros antiguos de 7
  digitos) se dejan con su valor original y se marcan para revision.
- Variable derivada asociada: `TELEFONO_REVISAR`.

### SUPERVISOR

- Descripcion: nombre de la persona encargada de la supervision educativa
  del establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: texto libre (nombre propio), sin catalogo cerrado.
- Valores faltantes: 535 (4.51% del total).
- Tratamiento aplicado: se convierte a mayusculas, se recortan espacios y
  caracteres invisibles, se convierten marcadores de ausencia de dato a NA.
  No se corrige ortografia de nombres propios automaticamente.

### DIRECTOR

- Descripcion: nombre del director o directora del establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: texto libre (nombre propio), sin catalogo cerrado.
- Valores faltantes: 2,000 (16.85% del total, la variable con mayor
  proporcion de faltantes del conjunto).
- Tratamiento aplicado: igual que SUPERVISOR.

### NIVEL

- Descripcion: nivel educativo ofrecido por el establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: un unico valor esperado, DIVERSIFICADO, ya que ese fue
  el criterio de descarga de los datos.
- Tratamiento aplicado: se convierte a mayusculas y se recortan espacios.
  Un valor distinto a DIVERSIFICADO se documentaria como posible error de
  extraccion.

### SECTOR

- Descripcion: sector administrativo del establecimiento (publico, privado,
  etc.).
- Tipo de dato: texto (string).
- Dominio permitido: categorico. No existe un catalogo oficial cerrado
  incorporado al codigo; la limpieza normaliza formato (mayusculas,
  espacios) pero no valida contra una lista externa de valores permitidos.
- Valores unicos observados en el diagnostico inicial: 4.
- Tratamiento aplicado: se convierte a mayusculas y se recortan espacios.

### AREA

- Descripcion: clasificacion territorial del establecimiento (urbana o
  rural).
- Tipo de dato: texto (string).
- Dominio permitido: URBANA, RURAL, SIN ESPECIFICAR. Esta ultima categoria
  se conserva como valor documentado en vez de convertirse a NA, porque
  representa una respuesta explicita de la fuente, no una ausencia de
  captura.
- Tratamiento aplicado: se convierte a mayusculas y se recortan espacios.

### STATUS

- Descripcion: estado administrativo del establecimiento (por ejemplo,
  abierta, cerrada temporal o definitivamente).
- Tipo de dato: texto (string).
- Dominio permitido: categorico, 5 categorias observadas en el diagnostico
  inicial. No se unifican categorias parecidas entre si (por ejemplo,
  distintos tipos de cierre) porque pueden representar situaciones
  administrativas distintas.
- Tratamiento aplicado: se convierte a mayusculas y se recortan espacios.
  Errores ortograficos puntuales detectados en el diagnostico (por ejemplo,
  "TEMPORAL TITULOS") se documentan pero no se reinterpretan
  automaticamente, para no asumir un significado que no esta confirmado.
- Variable derivada asociada: `CODIGO_DUPLICADO` (un mismo CODIGO con
  distinto STATUS es el ejemplo tipico de esta bandera).

### MODALIDAD

- Descripcion: modalidad linguistica del establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: MONOLINGUE, BILINGUE (con dieresis en la forma
  correcta: MONOLINGÜE, BILINGÜE).
- Tratamiento aplicado: se convierte a mayusculas, se recortan espacios y se
  corrige la falta de dieresis (MONOLINGUE / BILINGUE pasan a MONOLINGÜE /
  BILINGÜE), por tratarse de un error ortografico sistematico y no de una
  categoria distinta.

### JORNADA

- Descripcion: jornada en la que funciona el establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: categorico, 6 categorias observadas en el diagnostico
  inicial (por ejemplo, MATUTINA, VESPERTINA, DOBLE, entre otras). No existe
  un catalogo oficial cerrado incorporado al codigo.
- Tratamiento aplicado: se convierte a mayusculas y se recortan espacios.

### PLAN

- Descripcion: plan o frecuencia bajo la que se imparten las clases.
- Tipo de dato: texto (string).
- Dominio permitido: categorico, 13 categorias observadas en el diagnostico
  inicial (por ejemplo, DIARIO(REGULAR), FIN DE SEMANA, entre otras).
- Tratamiento aplicado: se convierte a mayusculas y se recortan espacios. No
  se reescriben los parentesis de valores como DIARIO(REGULAR), para no
  asumir un formato de reemplazo sin confirmacion.

### DEPARTAMENTAL

- Descripcion: direccion departamental de educacion responsable del
  establecimiento.
- Tipo de dato: texto (string).
- Dominio permitido: categorico, 26 categorias observadas en el diagnostico
  inicial (mas que los 22 departamentos, porque algunas direcciones
  departamentales se subdividen por region, por ejemplo GUATEMALA NORTE y
  GUATEMALA SUR). No existe un catalogo oficial cerrado incorporado al
  codigo.
- Tratamiento aplicado: se convierte a mayusculas y se recortan espacios.

---

## 4. Variables derivadas

Estas variables no vienen en la fuente original del MINEDUC; se agregaron
durante la limpieza para documentar decisiones y facilitar la revision
manual posterior. Todas son de tipo booleano (verdadero o falso), excepto
`GRUPO_DUPLICADO_PARCIAL`, que es un identificador de grupo.

### DEPARTAMENTO_REVISAR

- Por que se creo: para separar los valores de DEPARTAMENTO que SI se
  pudieron normalizar contra el catalogo oficial (corregidos
  automaticamente) de los que requieren una decision humana (CIUDAD
  CAPITAL, o cualquier valor fuera del catalogo de 22 departamentos).
- Como se calcula: verdadero cuando el valor original de DEPARTAMENTO es
  CIUDAD CAPITAL, o cuando no coincide con ningun departamento ni alias
  conocido del catalogo.
- Utilidad: permite filtrar y priorizar los registros que necesitan
  revision manual sin perder ni alterar el dato original.

### MUNICIPIO_REVISAR

- Por que se creo: mismo motivo que DEPARTAMENTO_REVISAR, aplicado a
  MUNICIPIO.
- Como se calcula: verdadero cuando el valor de MUNICIPIO no coincide con
  ningun municipio del catalogo dentro del DEPARTAMENTO ya limpio de la
  misma fila.
- Utilidad: identifica municipios mal escritos, inexistentes, o casos
  estructuralmente distintos (como las zonas de la ciudad capital).

### TELEFONO_REVISAR

- Por que se creo: para diferenciar los telefonos que se pudieron
  reformatear con confianza (grupos de 8 digitos) de los que quedaron en un
  formato ambiguo.
- Como se calcula: verdadero cuando, despues de limpiar separadores y
  palabras como FAX o EXT., el valor resultante no se puede interpretar
  como uno o mas numeros de 8 digitos.
- Utilidad: evita inventar o recortar digitos de un numero telefonico
  incierto.

### CODIGO_DUPLICADO

- Por que se creo: CODIGO deberia ser un identificador unico por
  establecimiento; esta bandera documenta los casos donde no lo es.
- Como se calcula: verdadero en todas las filas donde el mismo valor de
  CODIGO aparece mas de una vez en el conjunto, sin importar si el resto de
  las columnas coincide o no.
- Utilidad: expone casos donde un mismo establecimiento aparece con datos
  contradictorios entre si (por ejemplo, un mismo CODIGO con un STATUS
  distinto en cada aparicion), para que se decida manualmente cual version
  es la vigente. No se elimina ni se fusiona ninguna fila automaticamente.

### GRUPO_DUPLICADO_PARCIAL

- Por que se creo: para detectar establecimientos que probablemente son el
  mismo pero estan escritos de forma distinta (por ejemplo, con o sin la
  palabra INSTITUTO o COLEGIO antes del nombre).
- Como se calcula: se compara, dentro de un mismo municipio, una clave
  formada por el nombre del establecimiento (sin palabras genericas como
  INSTITUTO, COLEGIO, ESCUELA, LICEO, ACADEMIA, entre otras), la direccion
  y el municipio, usando similitud de cadenas (rapidfuzz, umbral de 90 sobre
  100). Los establecimientos cuya clave resulta suficientemente parecida
  reciben el mismo numero de grupo.
- Utilidad: agrupa candidatos a duplicado parcial para revision manual, sin
  fusionar ni eliminar ningun registro. Dos establecimientos legitimos
  distintos pueden compartir grupo por error (por ejemplo, dos sedes
  distintas de una misma cadena), por lo que la decision final siempre
  queda en manos de un analista.

### _ARCHIVO_ORIGEN y _FILA_ORIGEN (variables tecnicas)

- Por que se crearon: para poder rastrear, en cualquier momento, de que uno
  de los 23 archivos .xls y de que fila dentro de ese archivo vino cada
  registro del conjunto unificado.
- Como se calculan: se asignan durante la carga de cada archivo, antes de
  cualquier limpieza.
- Utilidad: trazabilidad y auditoria del proceso; permitieron, por ejemplo,
  identificar que las filas con DEPARTAMENTO='GUATEMALA' que se eliminaron
  (ver seccion 5) venian especificamente de `establecimiento (8).xls`. No se
  cuentan como variables analiticas del conjunto de datos.

---

## 5. Decisiones especiales de limpieza documentadas

### Filas eliminadas de establecimiento (8).xls

Se identifico, por inspeccion manual, que `establecimiento (8).xls`
contenia registros incompletos y duplicados para DEPARTAMENTO='GUATEMALA',
ya cubiertos de forma completa en `establecimiento (5).xls` (donde ese
mismo conjunto de establecimientos aparece bajo el valor CIUDAD CAPITAL).
Se eliminaron esas filas completas (todas sus columnas) del conjunto antes
de continuar con el resto de la limpieza. Esta es la unica transformacion
del pipeline que elimina filas completas; el resto de los duplicados
detectados solo se marcan, nunca se eliminan.

### CIUDAD CAPITAL como valor pendiente de decision

CIUDAD CAPITAL representa una proporcion considerable del conjunto de
datos (los registros de ese unico archivo equivalen a aproximadamente 18%
del total de filas). Se confirmo que el MINEDUC le asigna un pseudo-codigo
propio ("00-") distinto al codigo oficial de Guatemala ("01-"), y que sus
registros usan zonas de la ciudad capital en lugar de municipios. Por esa
razon, el codigo actual NO unifica automaticamente CIUDAD CAPITAL con
GUATEMALA; ambas variables (DEPARTAMENTO y MUNICIPIO) quedan con su valor
original y marcadas para revision, en espera de una decision final sobre
si deben tratarse como el mismo departamento o como una clasificacion
administrativa aparte.

### Duplicados: tres niveles de deteccion, ninguno elimina automaticamente

1. Exactos: comparacion de las 17 variables originales a la vez.
2. Por CODIGO repetido con datos contradictorios: bandera
   `CODIGO_DUPLICADO`.
3. Parciales por similitud de nombre, direccion y municipio, ignorando
   palabras genericas de tipo de institucion: variable
   `GRUPO_DUPLICADO_PARCIAL`.

En los tres casos, la decision de que fila conservar, corregir o descartar
queda para revision manual; el pipeline documenta y marca, no decide por
si mismo.

---

## 6. Archivos generados por el pipeline

Todos se generan en la carpeta `outputs/` al correr `pipeline.py`:

- `datos_limpios.csv`: conjunto de datos final, limpio.
- `registro_transformaciones.csv`: tabla con cada transformacion aplicada
  (variable, problema detectado, transformacion, registros afectados,
  justificacion).
- `resultados_validacion.csv`: resultado de las 8 pruebas automaticas de
  calidad.
- `informe_calidad_antes_despues.csv`: comparacion de metricas antes y
  despues de la limpieza.
- `resumen_ejecucion.txt`: resumen legible de toda la corrida (carga,
  limpieza, validacion e informe de calidad), incluyendo el detalle de
  valores faltantes por variable antes y despues de limpiar.

Adicionalmente, `limpieza.py` genera por separado los artefactos del
diagnostico inicial (`diagnostico_variables.csv`,
`posibles_variantes_texto.csv`, `duplicados_exactos.csv`,
`resumen_diagnostico.txt`, entre otros).

---

## 7. Control de versiones de este libro de codigos

| Version | Fecha | Cambios |
|---|---|---|
| v1.0 | [completar] | Version inicial del libro de codigos, con las 17 variables originales, las 6 variables derivadas y las decisiones especiales de limpieza documentadas. |