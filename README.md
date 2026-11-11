# Proyecto Altillanura

**Pregunta del proyecto:** ¿cómo se ha transformado la Altillanura y qué papel juegan el clima, el fuego y el suelo en la expansión agrícola?

Siete municipios: Puerto López (50573), Puerto Gaitán (50568) y Mapiripán (50325) en el Meta; Puerto Carreño (99001), La Primavera (99524), Santa Rosalía (99624) y Cumaribo (99773) en el Vichada.

Resultado esperado el 19 de noviembre:

1. Un repositorio único que corre de principio a fin, con los datos comunes y un diccionario de datos.
2. Dos tablas maestras: panel municipio × año (y mes) y grilla de celdas de 2 km.
3. Los modelos de cada parte terminados y validados, más un análisis integrador.
4. Un informe con 6 capítulos y una presentación de unos 15 minutos.

## Roles

| Integrante | Su parte | Rol de integración | Entrega principal |
|---|---|---|---|
| Michelle | Clima y fuego: FIRMS, ONI, CHIRPS | Datos comunes e informe (edición final) | SARIMAX mensual del fuego y patrón de puntos |
| Daniel | Expansión agrícola: MapBiomas, EVA, ARIMA, Moran | Repositorio (estructura, pruebas, revisión de pull requests) y tablas maestras | Panel municipio × año y grilla de 2 km |
| Jonatan | Fuego y expansión: panel de efectos fijos, Cumaribo | Revisión metodológica | Panel final con FIRMS Terra + Aqua |
| Katalina | Suelos: SoilGrids, kriging | Presentación y mapas finales | pH y carbono por celda y por municipio; mapas de kriging |

## Estructura

```
Proyecto-ALTILLANURA/
├── .github/workflows/ci.yml   Pruebas automáticas en cada push y pull request
├── .dvc/                      Configuración de DVC
├── datos/
│   ├── comunes/               Datos que usa más de una parte
│   └── diccionario_datos.md   Variable, fuente, unidad, periodo y cuaderno que la genera
├── modulos/
│   ├── clima_fuego/
│   ├── expansion/
│   ├── fuego_expansion/
│   └── suelos/
├── notebooks/
│   ├── 00_comun/
│   ├── 10_clima/
│   ├── 20_fuego/
│   ├── 30_expansion/
│   ├── 40_suelos/
│   ├── 50_vinculos/
│   └── 60_integracion/
├── informe/                   Capítulos del informe
├── pytest.ini
├── requirements.txt
└── README.md
```

`modulos/` tiene el proyecto de cada parte y `notebooks/` los cuadernos numerados del proyecto común.

## Numeración de cuadernos

Cada cuaderno lleva un número único de dos dígitos. El primer dígito dice a qué etapa pertenece y el segundo ordena los cuadernos dentro de la etapa.

| Bloque | Carpeta | Etapa | Responsable |
|---|---|---|---|
| 00–09 | `notebooks/00_comun/` | Configuración, límites y rejilla | Michelle y Daniel |
| 10–19 | `notebooks/10_clima/` | Clima | Michelle |
| 20–29 | `notebooks/20_fuego/` | Fuego | Michelle y Jonatan |
| 30–39 | `notebooks/30_expansion/` | Expansión agropecuaria | Daniel |
| 40–49 | `notebooks/40_suelos/` | Suelos | Katalina |
| 50–59 | `notebooks/50_vinculos/` | Vínculos fuego–expansión | Jonatan |
| 60–69 | `notebooks/60_integracion/` | Tablas maestras, modelo integrador, figuras | Todos |

Reglas para nombrar:

- Nombre = `<número>_<etapa>_<tema>.ipynb`, en minúsculas, sin tildes ni espacios.
- El número es único en todo el repositorio: nunca dos cuadernos con el mismo número, aunque estén en carpetas distintas.
- Un cuaderno solo lee archivos que produce un cuaderno de número menor (o datos crudos). Así, ejecutarlos en orden numérico siempre funciona.
- La primera celda de cada cuaderno dice: autor, entradas (archivos que lee), salidas (archivos que escribe) y de qué cuaderno vienen las entradas.
- Los nombres de los CSV y GeoPackage no cambian (por ejemplo `firms_mensual_municipio.csv`), así que renombrar los cuadernos no rompe ninguna ruta.
- Las referencias a números viejos dentro de los cuadernos se corrigen al número nuevo.

## Datos comunes

| Qué | Archivo en `datos/comunes/` | De | Fecha límite |
|---|---|---|---|
| Límites municipales (MGN 2025) | `altillanura_municipios.gpkg` | Michelle | Mié 11 |
| CHIRPS mensual | `chirps_mensual_municipio.csv` | Michelle | Mié 11 |
| FIRMS mensual | `firms_mensual_municipio.csv` | Michelle | Mié 11 |
| ONI mensual | `oni_mensual.csv` | Michelle | Mié 11 |
| Panel municipio × año | | Daniel | Vie 13 |
| Grilla de 2 km | `grilla_2km.gpkg` | Daniel | Sáb 14 |
| Focos por celda | `focos_celda.csv` | Michelle | Dom 15 |
| Conversión y quema por celda | | Jonatan | Dom 15 |
| pH y carbono por celda y municipio | `suelo_celda.csv`, `suelo_municipio.csv` | Katalina | Dom 15 |
| Variables de todos por celda | `grilla_2km_variables.csv` | Daniel y Katalina | Dom 15 |

Cada archivo nuevo se describe en `datos/diccionario_datos.md`.

## Acuerdos técnicos

| Tema | Acuerdo |
|---|---|
| Límites municipales | `datos/comunes/altillanura_municipios.gpkg` (DANE, MGN 2025); área total 135.649 km² |
| Sistema de coordenadas | EPSG:9377 (MAGNA-SIRGAS Origen Nacional) para áreas, distancias y la grilla |
| Llave de unión | Código DIVIPOLA de 5 dígitos como texto (`50568`, no `50568.0`); `id_celda` en la grilla |
| Formato de tablas | Largo: una fila por municipio (o celda) y periodo; CSV en UTF-8 |
| Nombres de archivo | Minúsculas, sin tildes ni espacios: `firms_mensual_municipio.csv` |
| FIRMS | Terra + Aqua desde enero de 2003; detecciones con `type = 0` y confianza ≥ 30 |
| Lluvia | CHIRPS v2.0 mensual por municipio; normal 1991–2020 |
| Unidades | Hectáreas, milímetros, grados Celsius, detecciones; siempre en el nombre de la columna (`area_ha`, `lluvia_mm`) |
| Periodos | Cada análisis declara el suyo en el diccionario de datos y explica por qué |
| Git | Ramas `feature/<tema>`, pull request a `main` revisado por otra persona, commits con tipo (`feat`, `fix`, `data`, `docs`) |
| Datos pesados | No van a Git: DVC o Drive, con el código que los descarga |
| Entorno | Un solo `requirements.txt`; los notebooks deben correr en Colab y en local |
| Figuras | Título con el hallazgo, ejes con unidades y fuente al pie |

## Instalación

### En el computador

```
git clone https://github.com/DanielFelipeRuizBermudez/Proyecto-ALTILLANURA.git
cd Proyecto-ALTILLANURA
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Los datos pesados están en el bucket de Google Cloud Storage del proyecto y se bajan con DVC. Se necesita [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) y una cuenta de Google con acceso al bucket:

```
gcloud auth application-default login
dvc pull
```

### En Colab

```python
from google.colab import auth
auth.authenticate_user()
```

```
!git clone https://github.com/DanielFelipeRuizBermudez/Proyecto-ALTILLANURA.git
%cd Proyecto-ALTILLANURA
!pip install -q -r requirements.txt
!dvc pull
```

## Flujo de trabajo

1. Actualizar código y datos:
   ```
   git switch main
   git pull
   dvc pull
   ```
2. Crear una rama para el tema: `git switch -c feature/<tema>`.
3. Hacer commits pequeños, cada uno con su tipo: `feat`, `fix`, `data` o `docs`.
4. Subir los datos y la rama:
   ```
   dvc push
   git push -u origin feature/<tema>
   ```
5. Abrir en GitHub el pull request hacia `main`. Otra persona del equipo lo revisa y se une cuando las pruebas están en verde.

Las librerías nuevas se agregan a `requirements.txt` en el mismo pull request.

## Subir datos con DVC

Cada archivo pesado se agrega por separado, para que varias personas puedan subir datos al mismo tiempo sin conflictos:

```
dvc add datos/comunes/firms_mensual_municipio.csv
git add datos/comunes/firms_mensual_municipio.csv.dvc datos/comunes/.gitignore
git commit -m "data: FIRMS mensual por municipio"
dvc push
```

Para actualizar un archivo se repiten los mismos comandos.

## Pruebas

```
pytest
```

GitHub Actions corre las pruebas en cada push a `main` o a una rama `feature/...` y en cada pull request a `main`. Las pruebas de una parte van en `modulos/<parte>/tests/`; esa carpeta se agrega a `testpaths` en `pytest.ini` y su carpeta de código a `pythonpath`.

## Entrega

```
git tag -a v1.0-entrega -m "Entrega del 19 de noviembre"
git push origin v1.0-entrega
```