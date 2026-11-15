# Altillanura: quema y cambio neto del área agropecuaria

Evaluar si, entre 2001 y 2024, los años con mayor proporción quemada de vegetación natural no forestal se asocian con un mayor aumento neto del área agropecuaria ese año o al siguiente dentro de cada uno de los siete municipios de la Altillanura.

El análisis municipal cubre Mapiripán, Puerto Gaitán, Puerto López, Puerto Carreño, La Primavera, Santa Rosalía y Cumaribo. Los datos agregados permiten estimar asociaciones por municipio y año. El notebook espacial de Cumaribo usa los mapas históricos para relacionar quema previa y conversión en el mismo píxel.

## Cómo ejecutar

El proyecto usa Python 3.12 y `uv`. Desde la raíz, ejecuta `uv run --with jupyterlab jupyter lab` y abre los notebooks en orden con el kernel Python 3. También puedes usar `uv sync` y seleccionar el intérprete de `.venv` en un editor con soporte para Jupyter.

1. [Datos y exploración](notebooks/01_datos_y_exploracion.ipynb) arma el panel de 168 filas, la serie regional y los descriptivos.
2. [Quema por cobertura](notebooks/02_quema_por_cobertura.ipynb) compara composición, tasas de quema y tendencias.
3. [Asociación municipal](notebooks/03_asociacion_municipal.ipynb) compara dos escalas de cambio agropecuario en el panel y en la exploración regional.

4. [Predicción regional](notebooks/04_prediccion_regional.ipynb) compara un ARIMA de referencia con modelos que incorporan lluvia y quema rezagadas. Ejecuta primero el notebook 01 y abre Jupyter con `uv run --extra prediccion --with jupyterlab jupyter lab`. La disponibilidad histórica de los insumos queda pendiente de verificar.

Los notebooks 01–03 guardan las salidas vigentes del panel en `datos/derivados/municipal/`, `resultados/tablas/municipal/` y `resultados/figuras/municipal/`. Las salidas del panel que se encuentran directamente en las carpetas superiores corresponden al planteamiento anterior. [Comentarios históricos](comentarios.md)

### Análisis espacial de Cumaribo

Abre el [notebook 05](notebooks/05_conversion_espacial_cumaribo.ipynb) con `uv run --extra espacial --with jupyterlab jupyter lab` o instala el extra espacial con `uv sync --extra espacial`. Este notebook puede ejecutarse por separado. Lee los TIFF en `datos/crudos/mapbiomas_coverage_cumaribo_tiff/` y `datos/crudos/mapbiomas_fire_cumaribo_tiff/`. El nombre de cada archivo empieza por el año.

El notebook genera un mapa de primera conversión de praderas, tasas según quema previa y Moran local de tasas de conversión en celdas de 2 km. Sus salidas se guardan en las subcarpetas `cumaribo/` de datos derivados, tablas y figuras.

## Datos y especificación

- **Resultados.** El cambio neto anual en hectáreas se divide por el área total del territorio en el año anterior para el indicador principal y por el área agropecuaria del año anterior para el crecimiento relativo. Los resultados se expresan en puntos porcentuales del territorio y en porcentaje de la base agropecuaria, respectivamente. MapBiomas incluye mosaico de agricultura y pastos, palma aceitera y plantación forestal. Una sensibilidad del resultado principal excluye plantaciones forestales.
- **Exposición principal.** Área quemada de formación natural no forestal según MapBiomas Fuego, dividida por el área de esa cobertura en el mismo año calendario. La clase incluye praderas y otras coberturas, como humedales. Los CSV adjuntos carecen de metadatos de unidad y el cálculo usa hectáreas como supuesto de trabajo. Se usa el área quemada de 2000 para calcular el primer rezago.
- **Lluvia y contraste.** CHIRPS aporta lluvia de diciembre del año anterior a marzo del año analizado. FIRMS Terra aporta detecciones de la misma temporada, expresadas por 100 km². Las comparaciones de regresión entre fuentes usan una muestra común y sus coeficientes conservan unidades distintas. ONI, EVA y pérdida de vegetación se conservan como contexto en el panel.
- **Calidad del fuego.** MapBiomas Fuego Colección 1 Beta complementó Landsat con MODIS MCD64A1 en 2002, 2005 y 2007. Se conservan esos años en el modelo principal. Una sensibilidad excluye las filas que usan uno de ellos en el predictor contemporáneo o rezagado. [Nota de calidad de MapBiomas Fuego](https://colombia.mapbiomas.org/iniciativas-y-productos/fuego/calidad-mosaico/)
- **Modelo.** Efectos fijos de municipio, tasa de quema del año y del anterior, y lluvia seca del año. Los intervalos aproximados del 95 % se obtienen con 2.000 réplicas de bloques móviles de tres años calendario. Se comprueba la sensibilidad a efectos fijos de año, al salto de Puerto Carreño de 2014, a la definición de área agropecuaria y a los años de fuego con calidad limitada.

## Funciones

- `scripts/01_preparar_panel.py` lee, valida y combina las fuentes y agrega la serie regional.
- `scripts/02_exploracion.py` calcula el resumen municipal.
- `scripts/03_panel_efectos_fijos.py` ajusta el panel y calcula los intervalos.
- `scripts/04_fuego_por_clase.py` calcula composición, tasas comparadas y tendencias.
- `scripts/05_correlacion_regional.py` calcula la correlación cruzada preblanqueada.
- `scripts/06_conversion_cumaribo.py` cruza los GeoTIFF, calcula superficies y estima Moran local.
- `scripts/config.py` y `scripts/utils.py` reúnen parámetros y funciones comunes.
