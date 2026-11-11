# Expansión agropecuaria: MapBiomas, EVA, ARIMA y Moran

Responsable: Daniel

**Pregunta:** ¿a qué ritmo crece el uso agropecuario, hacia dónde va en 2030 y está agrupado en el espacio?

Dos análisis del área agropecuaria de los 7 municipios:

- **Series de tiempo (1985–2024):** un modelo ARIMA por municipio y para la Altillanura completa, con pronóstico a 2030.
- **Estadística espacial (2024):** índice de Moran global y local sobre celdas de 2 × 2 km armadas con los mapas de cobertura de MapBiomas.

## Cuadernos de esta parte

| Cuaderno | Carpeta | Qué hace |
|---|---|---|
| `02_rejilla_2km` | `notebooks/00_comun/` | Rejilla de celdas de 2 km con `id_celda` |
| `30_expansion_mapbiomas` | `notebooks/30_expansion/` | Extracción de coberturas MapBiomas por municipio y celda |
| `31_expansion_eva_vs_mapbiomas` | `notebooks/30_expansion/` | Contraste EVA vs MapBiomas (palma) |
| `32_expansion_arima` | `notebooks/30_expansion/` | ARIMA del % agropecuario y pronóstico 2030 |
| `33_expansion_moran_lisa` | `notebooks/30_expansion/` | Moran global y LISA por celda |
| `60_tablas_maestras` | `notebooks/60_integracion/` | Panel municipio × año y tabla de celdas |

## Estructura

```
modulos/expansion/
├── datos/
│   ├── mapbiomas_crudos/       CSV descargados de MapBiomas, uno por municipio (en Git)
│   ├── eva/                    Se llena al correr 01_descargar_eva.py (en Git)
│   ├── procesados/             Tablas listas para analizar (en DVC)
│   └── procesados.dvc
├── mapas_tif/                  Mapas de cobertura 2024 de MapBiomas, uno por municipio (en DVC)
├── mapas_tif.dvc
├── graficas/                   Resultados: series, Moran y ARIMA
├── scripts/
│   ├── config.py               Rutas y lista de municipios
│   ├── 01_descargar_eva.py     Descarga la EVA 2006-2018 y 2019-2025 y la filtra a los 7 municipios
│   ├── 02_unir_mapbiomas.py    Une los 7 CSV de MapBiomas en una sola tabla
│   ├── 03_series_y_cruce_eva.py  Arma las tablas anchas y el cruce MapBiomas + EVA
│   ├── 04_graficas.py          Genera las dos gráficas por municipio en la carpeta graficas/
│   ├── 05_series_altillanura.py  Series de toda la Altillanura con pruebas ADF/KPSS, ACF y PACF
│   ├── 07_moran_espacial.py    Celdas de 2 km, índice de Moran global y local y correlograma
│   ├── 08_arima.py             Modelos ARIMA por municipio, diagnóstico y pronóstico
│   ├── estilo.py               Colores y estilo de las gráficas
│   └── series.py               Funciones para sacar series y cruzar datos
├── tests/                      Pruebas con pytest
└── README.md
```

Las rutas salen de `scripts/config.py` a partir de la ubicación de ese archivo, así que los scripts funcionan desde cualquier carpeta.

## Cómo correrlo

Desde la raíz del repositorio:

```
python modulos/expansion/scripts/01_descargar_eva.py
python modulos/expansion/scripts/02_unir_mapbiomas.py
python modulos/expansion/scripts/03_series_y_cruce_eva.py
python modulos/expansion/scripts/04_graficas.py
python modulos/expansion/scripts/05_series_altillanura.py
python modulos/expansion/scripts/07_moran_espacial.py
python modulos/expansion/scripts/08_arima.py
```

El paso 01 necesita internet (descarga unos cuantos MB de datos.gov.co). Los pasos 02 y 03 funcionan sin internet. Si el 01 no ha corrido, el 03 igual genera las tablas de MapBiomas y avisa que falta la EVA. El paso 07 necesita los mapas de `mapas_tif/` (`dvc pull`) y el 08 necesita `datos/procesados/mapbiomas_largo.csv`, que sale del 02.

## Datos

| Qué | Dónde se versiona | Por qué |
|---|---|---|
| `datos/mapbiomas_crudos/`, `datos/eva/` | Git | Son las entradas, pesan menos de 1 MB y GitHub Actions las necesita para correr las pruebas y el ARIMA |
| `mapas_tif/` | DVC | Son binarios de unos 21 MB |
| `datos/procesados/` | DVC | Son salidas de los scripts; `celdas_2km.csv` y `celdas_2km_altillanura.csv` pesan casi 7 MB cada una |
| `graficas/` | Git | Son los resultados para revisar en GitHub |

## Pruebas

| Archivo | Qué revisa |
|---|---|
| `tests/test_moran.py` | Que los píxeles de 30 m se agrupen en celdas de 67 × 67, que los porcentajes se calculen sobre los píxeles con dato, que el punto lon −73°, lat 4° quede en x = 5.000.000, y = 2.000.000 en EPSG:9377, que cada celda tenga 8 vecinas, que el I de Moran dé cerca de 1 en un gradiente y −1 en un tablero de ajedrez, que el I global sea el promedio de los locales y que las zonas Alto-Alto y Bajo-Bajo salgan donde deben. |
| `tests/test_arima.py` | La regla para elegir `d` con ADF y KPSS, que una caminata aleatoria se diferencie una vez y el ruido blanco ninguna, que un AR(1) simulado recupere su coeficiente, las raíces de los polinomios AR y MA, y la regla para elegir el modelo con AICc y supuestos. |
| `tests/test_calidad_datos.py` | Que haya un CSV crudo por municipio con los años 1985 a 2024, hectáreas numéricas y no negativas, clases conocidas, sin clases repetidas, área total del municipio constante entre años y cada categoría del nivel 1 igual a la suma de sus clases. Si están los mapas TIF, revisa su sistema de coordenadas, el tamaño del píxel y los códigos de clase. |
| `tests/test_integracion.py` | El camino completo de los CSV crudos al pronóstico ARIMA de Puerto López, y de un mapa simulado a las zonas de Moran. |

Las pruebas de los mapas TIF se saltan cuando `mapas_tif/` no está, como pasa en GitHub Actions.

## Gráficas (`graficas/`)

- `1_cobertura_por_municipio.png`: qué porcentaje de cada municipio es área agropecuaria, sabana y humedales, bosque, y agua o zonas sin vegetación, de 1985 a 2024. Un panel por municipio y uno con el total de la Altillanura.
- `2_cultivos_vs_area_agropecuaria.png`: dentro del área agropecuaria de MapBiomas (línea), cuánto es maíz, soya, palma y otros cultivos según la EVA; la parte gris es el resto, sobre todo pasto. Necesita haber corrido el paso 01.
- `series_altillanura/`: una gráfica por serie del paso 05 (serie original, serie diferenciada, ACF y PACF de la serie diferenciada) y `00_resumen.png` con todas juntas.
- `espacial/`: una figura de Moran por municipio y una de la Altillanura (mapa del % agropecuario, zonas de Moran local, diagrama de dispersión de Moran y correlograma).
- `arima/`: una carpeta por serie con la identificación, la comparación de modelos por AICc, el diagnóstico de residuos y el pronóstico, y `arima_resumen.png`.

## Series de la Altillanura (paso 05)

`datos/procesados/series_altillanura.csv` tiene una fila por año y una columna por serie:

| Serie | Qué mide | Fuente | Años |
|---|---|---|---|
| `mb_area_agropecuaria` | Área agropecuaria, cultivos + pastos (ha) | MapBiomas | 1985–2024 |
| `mb_pct_territorio_agropecuario` | Porcentaje del territorio que es agropecuario | MapBiomas | 1985–2024 |
| `mb_sabana` | Sabana natural, praderas / herbáceas (ha) | MapBiomas | 1985–2024 |
| `mb_perdida_sabana_anual` | Sabana perdida en el año (ha) | MapBiomas | 1986–2024 |
| `mb_humedal` | Humedales (ha) | MapBiomas | 1985–2024 |
| `mb_bosque` | Bosque, incluye bosque inundado (ha) | MapBiomas | 1985–2024 |
| `mb_plantacion_forestal` | Plantación forestal (ha) | MapBiomas | 1985–2024 |
| `mb_palma` | Palma detectada por satélite (ha) | MapBiomas | 1985–2024 |
| `mb_infraestructura` | Infraestructura (ha) | MapBiomas | 1985–2024 |
| `eva_sembrada_total` | Área sembrada, todos los cultivos (ha) | EVA | 2006–2025 |
| `eva_sembrada_maiz`, `eva_sembrada_soya`, `eva_sembrada_palma` | Área sembrada por cultivo (ha) | EVA | 2006–2025 |
| `eva_produccion_maiz`, `eva_produccion_soya` | Producción (t) | EVA | 2006–2025 |
| `eva_rendimiento_maiz`, `eva_rendimiento_soya` | Rendimiento (t/ha) | EVA | 2006–2025 |
| `pct_area_agropecuaria_cultivada` | Porcentaje del área agropecuaria que es cultivo | EVA + MapBiomas | 2006–2024 |

`datos/procesados/series_altillanura_pruebas.csv` trae, para cada serie, los p-valores de ADF y KPSS en nivel (`d0`), primera diferencia (`d1`) y segunda diferencia (`d2`), y el número de diferencias sugerido (`d_sugerido`): el primer `d` en que ADF rechaza (p < 0,05) y KPSS no rechaza (p ≥ 0,05).

- ADF: hipótesis nula = la serie NO es estacionaria (tiene raíz unitaria).
- KPSS: hipótesis nula = la serie SÍ es estacionaria.

Se prueba con `d` = 0, 1 y 2, en ese orden, y se toma el primero en que las dos pruebas indican estacionariedad. Si ninguno lo cumple, `d_sugerido` queda como `revisar` y la gráfica usa la primera diferencia.

En `graficas/series_altillanura/` queda una gráfica por serie (serie original, serie diferenciada, ACF y PACF de la serie diferenciada) y `00_resumen.png` con todas juntas.

Las mismas series salen para un municipio con `construir_series("Puerto Gaitán")` desde `series.py`.

## Índice de Moran (paso 07)

Cada mapa TIF tiene píxeles de unos 30 m con un código de clase. El script los agrupa en bloques de 67 × 67 píxeles (celdas de unos 2 × 2 km), calcula en cada celda el porcentaje agropecuario (clases 21 mosaico de agricultura y pastos, 9 plantación forestal y 35 palma), pasa el centro de cada celda a MAGNA-SIRGAS Origen Nacional (EPSG:9377, en metros) y calcula:

- El I de Moran global con las 8 celdas vecinas, con p-valor por 999 permutaciones.
- El I de Moran local de cada celda y su zona: Alto-Alto, Bajo-Bajo, Alto-Bajo, Bajo-Alto o No significativo.
- El correlograma: el I global para vecinas a distintas distancias, de 0–3 km a 40–60 km.

Salidas en `datos/procesados/espacial/`: `celdas_2km.csv`, `celdas_2km_altillanura.csv`, `moran_global.csv`, `correlograma_moran.csv` y `zonas_lisa.csv`.

## Modelos ARIMA (paso 08)

Para cada municipio y la Altillanura completa, sobre el área agropecuaria anual:

1. Elige `d` con ADF y KPSS, revisando señales de sobrediferenciación.
2. Ajusta los 36 modelos con `p` y `q` de 0 a 5 y los ordena por AICc.
3. Se queda con el de menor AICc que tenga raíces fuera del círculo unitario, coeficientes significativos y residuos sin autocorrelación (Ljung-Box); entre los que están a menos de 2 de AICc prefiere el que además pasa normalidad (Shapiro-Wilk y Jarque-Bera) y homocedasticidad (ARCH-LM).
4. Valida con los últimos 5 años y pronostica de 2025 a 2030.

Salidas en `datos/procesados/arima/`: `modelos.csv`, `candidatos.csv`, `estacionariedad.csv`, `coeficientes.csv`, `raices.csv`, `pronosticos.csv` y `series_modeladas.csv`.

## Archivos en `datos/procesados/`

| Archivo | Una fila es | Para qué |
|---|---|---|
| `mapbiomas_largo.csv` | municipio + año + clase | Programar: filtrar, agrupar, sacar series |
| `mapbiomas_nivel_1_ancho.csv` | municipio + año, con las 5 categorías grandes en columnas | Series por categoría (bosque, sabana, agro, agua…) |
| `mapbiomas_nivel_2_ancho.csv` | municipio + año, con las 17 clases en columnas | Series por clase específica (palma, humedal, mosaico…) |
| `cruce_mapbiomas_eva.csv` | municipio + año, solo años con EVA | Comparar cobertura de MapBiomas con lo sembrado según la EVA |

Las tablas anchas traen además 40 filas con `cod_mun = 0` y `municipio = Altillanura`, que son la suma de los 7 municipios.

En el nivel 2, cada clase pertenece a una sola categoría del nivel 1, y el nivel 1 es la suma de sus clases. Por ejemplo: Formación forestal = Bosque + Bosque inundado.

## Columnas del cruce con la EVA

- `mb_agricola_ganadera`: hectáreas de "Zona agrícola y ganadera" según MapBiomas.
- `mb_mosaico_agricultura_pastos`, `mb_palma`, `mb_plantacion_forestal`, `mb_praderas_herbaceas`: clases de MapBiomas.
- `eva_total_area_sembrada_ha`: suma del área sembrada de todos los cultivos según la EVA.
- `eva_<cultivo>`: área sembrada de cada cultivo con más de 1.000 ha en algún año (por ejemplo `eva_maiz`, `eva_soya`, `eva_palma_de_aceite`). Vacío significa que la EVA no reporta ese cultivo ese año.
- `eva_sobre_mb_agricola`: qué fracción del área agropecuaria de MapBiomas corresponde a cultivos de la EVA. El resto es sobre todo pasto para ganado.

La llave del cruce es `cod_mun` + `anio`. Los años en común son 2007-2024.

## Sacar una serie en Python

Desde un notebook o script dentro de `modulos/expansion/scripts/`:

```python
from series import serie, tabla_ancha, cruce_mapbiomas_eva

agro_gaitan = serie("Zona agrícola y ganadera", "Puerto Gaitán")
sabana_region = serie("Praderas / herbáceas", nivel="nivel_2")
palma_mapiripan = serie("Aceite de palma", "Mapiripán", nivel="nivel_2")
```

`serie` devuelve un `pd.Series` anual con índice de periodos (1985-2024), listo para `statsmodels` (ARIMA, ETS). Si no se pasa municipio, suma los 7.

## Alertas antes de modelar

- Saltos de un año que pueden ser cambios de clasificación y no cambios reales: Puerto Gaitán 1985→1986 (+44.600 ha de área agropecuaria), Puerto Carreño 2013→2014 (+26.200 ha), palma en Mapiripán de 0 a 10.166 ha en 2009 y luego casi constante.
- Las clases de un municipio suman siempre su área total. Si se pronostica cada clase por separado, los pronósticos pueden no cuadrar con el total.
- MapBiomas no separa cultivos dentro de "Mosaico de agricultura y pastos". Para saber qué se sembró se usa la EVA.
- La suma de los 7 municipios en los CSV de MapBiomas da 134.874 km²; el área acordada con los límites del MGN 2025 es 135.649 km².

## Fuentes

- MapBiomas Colombia, serie temporal "Cobertura por clase" 1985-2024, por municipio, y mapas de cobertura 2024 (Colección 3): https://colombia.mapbiomas.org/
- EVA 2006-2018: https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Evaluaciones-Agropecuarias-Municipales-EVA/2pnw-mmge
- EVA 2019-2025: https://www.datos.gov.co/Agricultura-y-Desarrollo-Rural/Evaluaciones-Agropecuarias-Municipales-EVA-2019-20/uejq-wxrr
