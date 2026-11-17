# Altillanura: quema y cambio neto del área agropecuaria

Evaluar si, entre 2001 y 2024, los años con mayor proporción quemada de vegetación natural no forestal se asocian con un mayor aumento neto del área agropecuaria ese año o al siguiente dentro de cada uno de los siete municipios de la Altillanura.

El análisis municipal cubre Mapiripán, Puerto Gaitán, Puerto López, Puerto Carreño, La Primavera, Santa Rosalía y Cumaribo. Los datos agregados permiten estimar asociaciones por municipio y año. El notebook espacial de Cumaribo usa los mapas históricos para relacionar quema previa y conversión en el mismo píxel.

## Cómo ejecutar

Este módulo usa el entorno y los datos del repositorio completo (ver el README de la raíz). Se probó en local con Python 3.12.

1. Desde la raíz del repositorio, instala las dependencias con `pip install -r requirements.txt`.
2. Baja los datos pesados con `dvc pull`. Este módulo lee de tres lugares:
   - `modulos/fuego_expansion/datos/crudos/` (estadísticas de MapBiomas Fuego, pérdida de vegetación, TIFF de cobertura de Cumaribo y TIFF de fuego de los siete municipios; puntero `datos/crudos.dvc`).
   - `datos/comunes/` (FIRMS, CHIRPS y ONI mensuales por municipio, límites municipales y grilla común de 2 km).
   - `modulos/expansion/datos/procesados/` (coberturas MapBiomas y EVA, del módulo de expansión).
3. Abre los cuadernos desde su carpeta (`notebooks/20_fuego/` y `notebooks/50_vinculos/`). Cada uno construye lo que necesita y no depende de que otro se haya ejecutado antes. Los datos derivados se escriben en `datos/derivados/`, que Git ignora y se regenera al ejecutar.

1. [52 · Panel y descriptivos](../../notebooks/50_vinculos/52_panel_exploracion.ipynb) arma el panel de 168 filas, la serie regional y los descriptivos.
2. [23 · Tendencias del fuego](../../notebooks/20_fuego/23_fuego_tendencias.ipynb) compara composición, tasas de quema y tendencias.
3. [50 · Panel de efectos fijos](../../notebooks/50_vinculos/50_panel_fuego_expansion.ipynb) compara dos escalas de cambio agropecuario en el panel y en la exploración regional.

4. [53 · Predicción regional](../../notebooks/50_vinculos/53_prediccion_regional.ipynb) compara un pronóstico ingenuo y un ARIMA de referencia con modelos que incorporan lluvia y quema rezagadas, con MAE y MASE fuera de muestra. No se verificó la disponibilidad histórica de los insumos al momento del pronóstico; queda como observación al inicio del cuaderno.

Los cuadernos 23, 50 y 52 guardan las salidas vigentes del panel en `datos/derivados/municipal/`, `resultados/tablas/municipal/` y `resultados/figuras/municipal/`. Las salidas del planteamiento anterior que estaban directamente en `resultados/tablas/` y `resultados/figuras/` se eliminaron.

### Análisis espacial de Cumaribo

El [cuaderno 51](../../notebooks/50_vinculos/51_cumaribo.ipynb) necesita `rasterio`, que ya está en el `requirements.txt` de la raíz. Puede ejecutarse por separado. Lee los TIFF en `datos/crudos/mapbiomas_coverage_cumaribo_tiff/` y `datos/crudos/mapbiomas_fire_cumaribo_tiff/`. El nombre de cada archivo empieza por el año.

El notebook genera un mapa de primera conversión de praderas, tasas según quema previa y Moran local de tasas de conversión en las celdas de 2 km de la grilla común (`id_celda`, EPSG:9377). Sus salidas se guardan en las subcarpetas `cumaribo/` de datos derivados, tablas y figuras.

### Fracción quemada por celda

El [cuaderno 24](../../notebooks/20_fuego/24_fuego_quema_celda.ipynb) lleva los mapas anuales de MapBiomas Fuego de los siete municipios (2015–2025) a la grilla común de 2 km. Lee los TIFF en `datos/crudos/mapbiomas_fire_<municipio>_tiff/` y escribe `quema_celda.csv` y `quema_celda_anual.csv` en `datos/comunes/` (DVC). Compara además el área quemada de los mapas con las estadísticas municipales de la plataforma.

## Datos y especificación

- **Resultados.** El cambio neto anual en hectáreas se divide por el área total del territorio en el año anterior para el indicador principal y por el área agropecuaria del año anterior para el crecimiento relativo. Los resultados se expresan en puntos porcentuales del territorio y en porcentaje de la base agropecuaria, respectivamente. MapBiomas incluye mosaico de agricultura y pastos, palma aceitera y plantación forestal. Una sensibilidad del resultado principal excluye plantaciones forestales.
- **Exposición principal.** Área quemada de formación natural no forestal según MapBiomas Fuego, dividida por el área de esa cobertura en el mismo año calendario. La clase incluye praderas y otras coberturas, como humedales. Los CSV no traen metadatos de unidad; se leen en hectáreas, y el cuaderno 24 comprueba que coinciden con el área quemada de los mapas de 30 m. Se usa el área quemada de 2000 para calcular el primer rezago.
- **Lluvia y contraste.** CHIRPS aporta lluvia de diciembre del año anterior a marzo del año analizado. FIRMS aporta detecciones de la misma temporada, expresadas por 100 km²: Terra + Aqua desde 2003 como serie principal y Terra sola desde 2001 como sensibilidad. Las comparaciones de regresión entre fuentes usan una muestra común y sus coeficientes conservan unidades distintas. ONI, EVA y pérdida de vegetación se conservan como contexto en el panel.
- **Calidad del fuego.** MapBiomas Fuego Colección 1 Beta complementó Landsat con MODIS MCD64A1 en 2002, 2005 y 2007. Se conservan esos años en el modelo principal. Una sensibilidad excluye las filas que usan uno de ellos en el predictor contemporáneo o rezagado. [Nota de calidad de MapBiomas Fuego](https://colombia.mapbiomas.org/iniciativas-y-productos/fuego/calidad-mosaico/)
- **Modelo.** Efectos fijos de municipio, tasa de quema del año y del anterior, y lluvia seca del año. Los intervalos aproximados del 95 % se obtienen con 2.000 réplicas de bloques móviles de tres años calendario. Se comprueba la sensibilidad a efectos fijos de año, al salto de Puerto Carreño de 2014, a la definición de área agropecuaria y a los años de fuego con calidad limitada.

## Funciones

- `scripts/01_preparar_panel.py` lee, valida y combina las fuentes y agrega la serie regional.
- `scripts/02_exploracion.py` calcula el resumen municipal.
- `scripts/03_panel_efectos_fijos.py` ajusta el panel y calcula los intervalos.
- `scripts/04_fuego_por_clase.py` calcula composición, tasas comparadas y tendencias.
- `scripts/05_correlacion_regional.py` calcula la correlación cruzada preblanqueada.
- `scripts/06_conversion_cumaribo.py` cruza los GeoTIFF, calcula superficies por celda de la grilla común y estima Moran local.
- `scripts/07_quema_celda.py` calcula la fracción quemada por celda de la grilla común en los siete municipios.
- `scripts/config.py` y `scripts/utils.py` reúnen parámetros y funciones comunes.
