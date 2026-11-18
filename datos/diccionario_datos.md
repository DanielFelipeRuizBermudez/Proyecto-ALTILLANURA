# Diccionario de datos

## Suelos (cuadernos 40 y 42, Katalina)

### `datos/comunes/suelo_celda.csv` (cuaderno 42, DVC)
Una fila por celda de la grilla común de 2 km (34.763 filas). Llave: `id_celda`. Fuente: SoilGrids 2.0 (ISRIC), 0-30 cm, sin fecha.

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común: esquina inferior izquierda en km, EPSG:9377 | texto | grilla_2km.gpkg (cuaderno 02) |
| `mpio_cdpmp` | Código DIVIPOLA del municipio | texto, 5 dígitos | grilla_2km.gpkg |
| `area_km2` | Área de la celda dentro de la Altillanura (4 si está completa) | km² | grilla_2km.gpkg |
| `n_pixeles` | Píxeles de SoilGrids (≈ 278 m) con centro en la celda | píxeles | SoilGrids |
| `relleno_vecino` | True si la celda no tenía píxeles y tomó el del píxel más cercano (283 celdas) | booleano | cuaderno 42 |
| `ph_medio` | pH en agua, promedio de los píxeles | pH | SoilGrids |
| `cos_medio_gkg` | Carbono orgánico, promedio de los píxeles | g/kg | SoilGrids |
| `log_cos_medio` | Logaritmo natural de cos_medio_gkg | ln(g/kg) | cuaderno 42 |
| `pct_area_ph_menor_5` | % de píxeles con pH < 5 (toxicidad por aluminio) | % del área | SoilGrids |
| `clase_ph` | Clase de pH del promedio de la celda | categoría | cuaderno 42 |
| `pct_ph_menor_4_5` | % de píxeles con pH < 4,5 | % del área | SoilGrids |
| `pct_ph_4_5_a_5_0` | % de píxeles con 4,5 ≤ pH ≤ 5,0 | % del área | SoilGrids |
| `pct_ph_5_1_a_5_5` | % de píxeles con 5,0 < pH ≤ 5,5 | % del área | SoilGrids |
| `pct_ph_mayor_5_5` | % de píxeles con pH > 5,5 | % del área | SoilGrids |
| `ph_kriging` | pH por kriging ordinario con 300 puntos (vacío en 851 celdas de borde) | pH | cuaderno 40 |
| `cos_kriging_gkg` | COS por kriging en log con corrección exp(pred + var/2) (vacío en las mismas celdas) | g/kg | cuaderno 40 |

## Fuego y expansión (cuadernos 23, 24 y 50 a 53, Jonatan)

Módulo `modulos/fuego_expansion/`. Los municipios son los siete de la Altillanura; la llave municipal es el código DIVIPOLA como texto de 5 dígitos y la de celda es `id_celda` de `datos/comunes/grilla_2km.gpkg`.

### Fuentes crudas (`modulos/fuego_expansion/datos/crudos/`, DVC)

| Conjunto | Fuente | Periodo | Resolución | Unidad | Ruta en `crudos/` |
|---|---|---|---|---|---|
| Área quemada anual por clase de cobertura | MapBiomas Fuego Colombia, Colección 1 Beta (estadísticas de la plataforma) | 2000-2025 | Municipio × año | ha | `mapbiomas_fuego/fuego_<municipio>.csv` |
| Supresión de vegetación primaria y secundaria | MapBiomas Colombia (estadísticas de la plataforma) | 1985-2024 | Municipio × año | ha | `perdida_vegetacion/perdida_veg_<municipio>.csv` |
| Mapas anuales de área quemada, Cumaribo | MapBiomas Fuego Colombia, Colección 1 Beta | 2000-2025 | Píxel de 0,00027° (≈ 30 m), EPSG:4326 | valor > 0 = quemado ese año; 0 = sin quema o sin dato | `mapbiomas_fire_cumaribo_tiff/<año>_*.tif` |
| Mapas anuales de área quemada, los otros seis municipios | MapBiomas Fuego Colombia, Colección 1 Beta | 2015-2025 | Píxel de 0,00027° (≈ 30 m), EPSG:4326 | valor > 0 = quemado ese año; 0 = sin quema o sin dato | `mapbiomas_fire_<municipio>_tiff/<año>_fuego_<municipio>.tif` |
| Mapas anuales de cobertura, Cumaribo | MapBiomas Colombia, cobertura y uso | 2000-2024 | Píxel de 0,00027° (≈ 30 m), EPSG:4326 | código de clase (12 = pradera; 9, 21 y 35 = agropecuario); 0 = sin dato | `mapbiomas_coverage_cumaribo_tiff/<año>_*.tif` |

Los CSV de MapBiomas Fuego no traen metadato de unidad. Se leen en hectáreas. El cuaderno 24 lo comprueba: el área quemada que suman los mapas de 30 m coincide con la de los CSV en cada municipio y año de 2015-2025 (diferencia máxima del total por municipio: 0,03 %). MapBiomas Fuego complementó Landsat con MODIS MCD64A1 en 2002, 2005 y 2007; esos años se marcan con `fuego_calidad_limitada`.

De otras partes del proyecto se leen `datos/comunes/firms_mensual_municipio.csv`, `chirps_mensual_municipio.csv` y `oni_mensual.csv` (Michelle) y `modulos/expansion/datos/procesados/` (coberturas MapBiomas y EVA, Daniel).

### Periodos y por qué

| Análisis | Periodo | Por qué |
|---|---|---|
| Panel municipio × año | 2001-2024 | La primera temporada seca completa de FIRMS es la de 2001 y la cobertura MapBiomas llega a 2024 |
| Focos Terra + Aqua (serie principal) | 2003-2024 | Aqua opera desde julio de 2002; la primera temporada seca comparable es la de 2003 |
| Focos solo Terra (sensibilidad) | 2001-2024 | Serie más larga, pero Terra pierde detecciones en 2024-2025 por la deriva de su órbita |
| Conversión de pradera en Cumaribo | 2000-2024 | Único municipio con mapas de cobertura y de fuego por píxel para todo el periodo |
| Fracción quemada por celda | 2015-2025 | Único periodo con mapas de fuego en los siete municipios; Cumaribo se recorta a la misma ventana para que todas las celdas midan lo mismo |

Temporada seca del año *t*: de diciembre de *t* − 1 a marzo de *t*.

### `datos/comunes/quema_celda.csv` (cuaderno 24, DVC)
Una fila por celda de la grilla común de 2 km (34.763 filas). Llave: `id_celda`. Fuente: mapas anuales de MapBiomas Fuego, 2015-2025 (11 años).

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común | texto | grilla_2km.gpkg (cuaderno 02) |
| `mpio_cdpmp` | Código DIVIPOLA del municipio | texto, 5 dígitos | grilla_2km.gpkg |
| `n_pixeles` | Píxeles de MapBiomas Fuego (≈ 30 m) con centro en la celda | píxeles | MapBiomas Fuego |
| `quema_media_anual_pct` | Fracción de la celda quemada en un año, promedio de 2015-2025 | % del área por año | MapBiomas Fuego |
| `quema_alguna_vez_pct` | Fracción de la celda quemada al menos una vez en 2015-2025 | % del área | MapBiomas Fuego |
| `anios_con_quema` | Años de 2015-2025 con algún píxel quemado en la celda | años (0 a 11) | MapBiomas Fuego |

### `datos/comunes/quema_celda_anual.csv` (cuaderno 24, DVC)
Una fila por celda y año (34.763 × 11). Llave: `id_celda` + `anio`.

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común | texto | grilla_2km.gpkg (cuaderno 02) |
| `anio` | Año calendario, 2015 a 2025 | año | MapBiomas Fuego |
| `quema_pct` | Fracción de la celda quemada ese año | % del área | MapBiomas Fuego |

### `modulos/fuego_expansion/resultados/tablas/cumaribo/tasas_celdas_2km.csv` (cuaderno 51)
Una fila por celda de la grilla común con pradera elegible en los mapas de Cumaribo. Llave: `id_celda`. Fuente: mapas anuales de cobertura y fuego de MapBiomas, conversiones de 2001-2023. `moran_local_2km.csv` (DVC) tiene las mismas columnas más las de Moran local, solo para las celdas con al menos 100 ha-año de pradera y algún vecino.

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común | texto | grilla_2km.gpkg (cuaderno 02) |
| `mpio_cdpmp` | Código DIVIPOLA del municipio de la celda; las celdas del límite pueden ser de un municipio vecino | texto, 5 dígitos | grilla_2km.gpkg |
| `area_km2` | Área de la celda dentro de la Altillanura | km² | grilla_2km.gpkg |
| `x_m`, `y_m` | Centro del cuadrado de 2 km en EPSG:9377 | m | cuaderno 51 |
| `pradera_ha_anio` | Pradera elegible acumulada: una hectárea disponible diez años aporta diez | ha-año | MapBiomas cobertura |
| `conversion_ha` | Primeras conversiones persistentes de pradera a uso agropecuario | ha | MapBiomas cobertura |
| `conversion_por_1000_ha_anio` | `conversion_ha` por cada 1.000 ha-año de pradera elegible | ha por 1.000 ha-año | cuaderno 51 |
| `moran_local`, `p_perm`, `q_fdr` | Moran local, valor p por 9.999 permutaciones y valor q de Benjamini-Hochberg | adimensional | cuaderno 51 |
| `vecinos` | Celdas vecinas (vecindad reina) incluidas en el cálculo | celdas | cuaderno 51 |
| `cuadrante`, `grupo_moran` | Cuadrante de Moran y grupo que se muestra (cuadrante si q < 0,05) | categoría | cuaderno 51 |

### Panel municipio × año (`01_preparar_panel.construir_panel()`, cuadernos 23, 50, 52 y 53)
Una fila por municipio y año (7 × 24 = 168 filas, 2001-2024). Llave: `cod_mun` + `anio`. Los cuadernos lo construyen en memoria; el cuaderno 52 deja una copia en `modulos/fuego_expansion/datos/derivados/municipal/panel_municipio_anio.csv`, que Git ignora y se regenera. El sufijo `_rez1` indica el valor del año anterior.

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `cod_mun` | Código DIVIPOLA del municipio; entero mientras se calcula y texto de 5 dígitos en el CSV | texto, 5 dígitos | DANE |
| `municipio` | Nombre del municipio | texto | DANE |
| `anio` | Año calendario; para focos y lluvia de temporada seca, año en que termina la temporada | año | — |
| `area_total_ha` | Área del municipio en los mapas de cobertura | ha | MapBiomas cobertura |
| `agro_ha`, `natural_ha`, `bosque_ha` | Área agropecuaria, de formación natural no forestal y de formación forestal | ha | MapBiomas cobertura |
| `agro_pct` | Área agropecuaria sobre el área total | % del área | MapBiomas cobertura |
| `d_agro_ha`, `d_natural_ha`, `d_bosque_ha` | Cambio neto frente al año anterior | ha por año | MapBiomas cobertura |
| `d_agro_pct` | Cambio neto agropecuario sobre el área total del año anterior (resultado principal) | puntos porcentuales del territorio | MapBiomas cobertura |
| `d_agro_sin_forestal_pct` | Igual que `d_agro_pct`, sin plantación forestal | puntos porcentuales del territorio | MapBiomas cobertura |
| `crec_agro_pct` | Cambio neto agropecuario sobre el área agropecuaria del año anterior | % del área agropecuaria previa | MapBiomas cobertura |
| `d_natural_pct`, `d_bosque_pct` | Cambio neto sobre el área total del mismo año | puntos porcentuales del territorio | MapBiomas cobertura |
| `quem_agro_ha`, `quem_natural_ha`, `quem_bosque_ha`, `quem_sin_veg_ha`, `quem_total_ha` | Área quemada por clase de cobertura y total | ha | MapBiomas Fuego |
| `quem_total_pct`, `quem_agro_pct`, `quem_natural_pct` | Área quemada sobre el área total del municipio | % del área | MapBiomas Fuego |
| `tasa_quema_natural` | Área quemada de formación natural no forestal sobre el área de esa cobertura (exposición principal) | % de la cobertura | MapBiomas Fuego y cobertura |
| `tasa_quema_agro` | Área quemada agropecuaria sobre el área agropecuaria | % de la cobertura | MapBiomas Fuego y cobertura |
| `fuego_calidad_limitada` | True en 2002, 2005 y 2007 | booleano | MapBiomas Fuego |
| `perdida_primaria_ha`, `perdida_secundaria_ha`, `perdida_total_ha` | Supresión de vegetación primaria, secundaria y total | ha | MapBiomas |
| `perdida_veg_pct` | Supresión total sobre el área del municipio | % del área | MapBiomas |
| `focos_seca_total` | Detecciones Terra + Aqua en la temporada seca; vacío antes de 2003 | detecciones | FIRMS MODIS |
| `focos_anual_total` | Detecciones Terra + Aqua en el año calendario; vacío antes de 2003 | detecciones | FIRMS MODIS |
| `focos_seca_terra`, `focos_anual_terra` | Detecciones solo de Terra, temporada seca y año calendario (sensibilidad, desde 2001) | detecciones | FIRMS MODIS |
| `focos_seca_dens`, `focos_anual_dens` | Detecciones Terra + Aqua por superficie del municipio | detecciones por 100 km² | FIRMS MODIS |
| `focos_seca_terra_dens`, `focos_anual_terra_dens` | Detecciones solo de Terra por superficie del municipio | detecciones por 100 km² | FIRMS MODIS |
| `lluvia_seca_mm` | Lluvia acumulada de la temporada seca | mm | CHIRPS |
| `normal_seca_mm` | Normal 1991-2020 de la temporada seca | mm | CHIRPS |
| `lluvia_seca_anom_pct` | Anomalía de la lluvia de la temporada seca frente a la normal | % | CHIRPS |
| `lluvia_humeda_prev_mm` | Lluvia de abril a noviembre del año anterior | mm | CHIRPS |
| `oni_nov_feb` | ONI medio de noviembre a febrero | °C | NOAA |
| `eva_sembrada_ha` | Área sembrada total | ha | EVA (módulo de expansión) |

Las tablas de resultados por municipio (`modulos/fuego_expansion/resultados/tablas/municipal/`: `descriptivo_por_municipio.csv`, `composicion_quema_por_municipio.csv` y `tendencias_fuego.csv`) llevan el nombre del municipio y su código en `mpio_cdpmp`, como texto de 5 dígitos.

Terra + Aqua cuenta cerca del doble de detecciones que Terra sola, así que los coeficientes por foco de las dos series no se comparan en magnitud; solo se compara si el intervalo cruza cero.

## Clima y fuego (cuadernos 12 y 22, Michelle)

### `datos/comunes/lluvia_celda.csv` (cuaderno 12, DVC)
Una fila por celda de la grilla común de 2 km (34.763 filas). Llave: `id_celda`. Fuente: CHIRPS Daily v2.0 (UCSB-CHG) en Google Earth Engine, píxeles de 0,05° (~5,5 km), interpolados de forma bilineal a los centroides de la grilla.

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común: esquina inferior izquierda en km, EPSG:9377 | texto | grilla_2km.gpkg (cuaderno 02) |
| `lluvia_anual_1991_2020` | Lluvia media anual, normal climatológica 1991–2020 | mm/año | CHIRPS |
| `lluvia_seca_1991_2020` | Lluvia media de diciembre a marzo, normal 1991–2020 | mm por temporada | CHIRPS |
| `lluvia_anual_2003_2025` | Lluvia media anual en el periodo de los focos | mm/año | CHIRPS |
| `lluvia_seca_2003_2025` | Lluvia media de diciembre a marzo, 2003–2025 | mm por temporada | CHIRPS |
| `frac_seca_1991_2020` | Fracción de la lluvia anual que cae de diciembre a marzo | proporción (0–1) | cuaderno 12 |

Nota: en el nororiente (entre La Primavera y Puerto Carreño) CHIRPS tiene un artefacto rectangular, probablemente por la mezcla con estaciones; conviene un análisis de sensibilidad sin esas celdas.

### `datos/comunes/focos_celda.csv` (cuaderno 22, DVC)
Una fila por celda de la grilla común de 2 km (34.763 filas). Llave: `id_celda`. Fuente: NASA FIRMS, MODIS C6.1 Terra + Aqua, enero de 2003 a diciembre de 2025, solo vegetación (`type = 0`) y confianza ≥ 30 % (cuaderno 03).

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común | texto | grilla_2km.gpkg (cuaderno 02) |
| `focos_total_2003_2025` | Focos de calor en la celda, 2003–2025 | focos | FIRMS |
| `focos_media_anual` | Promedio de focos por año (23 años) | focos/año | cuaderno 22 |
| `focos_temporada_seca_media` | Promedio de focos de diciembre a marzo por temporada (2004–2025) | focos/temporada | cuaderno 22 |
| `anios_con_focos` | Años con al menos un foco | años (0–23) | cuaderno 22 |
| `focos_km2_anio` | `focos_media_anual` / `area_km2` de la celda | focos/km²/año | cuaderno 22 |

Nota: en celdas de borde muy pequeñas (`area_km2` < 1) un solo foco da densidades extremas; usar `frac_celda` ≥ 0,5 o ponderar por área.

### `datos/comunes/focos_celda_anual.csv` (cuaderno 22, DVC)
Formato largo celda × año (34.763 × 23 = 799.549 filas): `id_celda`, `anio` (2003–2025) y `focos` (número de focos de la celda en ese año, 0 si no hubo).


## Grilla común y expansión agropecuaria (cuadernos 02 y 30, Daniel)

### `datos/comunes/grilla_2km.gpkg` (cuaderno 02, DVC)
Capa `grilla`: 34.763 celdas de 2 × 2 km en EPSG:9377, recortadas al área de la Altillanura (135.649 km²). Cada celda pertenece al municipio que ocupa la mayor parte de su área. Fuente: límites del DANE, MGN 2025 (cuaderno 01).

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común: coordenadas en km de la esquina inferior izquierda, EPSG:9377 (por ejemplo `x5120_y1986`) | texto | cuaderno 02 |
| `mpio_cdpmp` | Código DIVIPOLA del municipio con la mayor parte de la celda | texto, 5 dígitos | MGN 2025 |
| `mpio_cnmbr` | Nombre del municipio | texto | MGN 2025 |
| `area_km2` | Área de la celda dentro de la Altillanura (4 si está completa) | km² | cuaderno 02 |
| `frac_celda` | Fracción de la celda dentro de la Altillanura | proporción (0–1) | cuaderno 02 |
| `x_9377`, `y_9377` | Centroide de la celda | m, EPSG:9377 | cuaderno 02 |
| `geometry` | Polígono de la celda | EPSG:9377 | cuaderno 02 |

### `datos/comunes/agro_celda.csv` (cuaderno 30, DVC)
Una fila por celda de la grilla común (34.763 filas). Llave: `id_celda`. Fuente: MapBiomas Colombia, Colección 3, mapas de 2000 y 2024 con píxeles de 30 m. Uso agropecuario = clases 9 (plantación forestal), 21 (mosaico de agricultura y pastos) y 35 (palma de aceite).

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `id_celda` | Llave de la grilla común | texto | grilla_2km.gpkg (cuaderno 02) |
| `agro_pct_2000`, `agro_pct_2024` | Área agropecuaria sobre el área con dato de la celda | % | MapBiomas |
| `cambio_agro_pp` | `agro_pct_2024 − agro_pct_2000` | puntos porcentuales | cuaderno 30 |
| `agro_ha_2000`, `agro_ha_2024` | Área agropecuaria de la celda | ha | MapBiomas |
| `frac_valida_2000`, `frac_valida_2024` | Fracción del área de la celda con dato en el mapa | proporción (0–1) | cuaderno 30 |
| `celda_valida` | True si los dos años tienen dato en al menos la mitad de la celda | booleano | cuaderno 30 |

Nota: el paso 5 del cuaderno 30 compara el % agropecuario de cada municipio calculado con los mapas contra las tablas municipales de MapBiomas.

## Tablas maestras (cuaderno 60, Daniel)

### `datos/comunes/grilla_2km_variables.csv` (cuaderno 60, DVC)
Una fila por celda de la grilla común (34.763 filas). Llave: `id_celda`. Une las columnas de `grilla_2km.gpkg` (sin la geometría) con todas las capas `datos/comunes/*_celda.csv` que tienen una fila por celda (`focos_celda`, `lluvia_celda`, `quema_celda`, `agro_celda` y `suelo_celda`); las variables de cada capa están descritas en su sección. Las columnas que una capa repite de la grilla (municipio, área) se toman de la grilla. Se vuelve a generar cuando llega una capa nueva.

### `datos/comunes/panel_municipio_anio.csv` (cuaderno 60)
Una fila por municipio y año: 7 × 41 = 287 filas (1985–2025). Llave: `mpio_cdpmp` + `anio`. La temporada seca del año t va de diciembre de t − 1 a marzo de t. Un año o una temporada solo se calcula si tiene todos sus meses. Las variables que también están en el panel del módulo de fuego y expansión usan los mismos nombres y definiciones.

| Variable | Descripción | Unidad | Fuente |
|---|---|---|---|
| `mpio_cdpmp`, `mpio_cnmbr` | Código DIVIPOLA y nombre del municipio | texto | MGN 2025 |
| `anio` | Año calendario; para la temporada seca, año en que termina | año | cuaderno 60 |
| `area_mpio_ha` | Área oficial del municipio | ha | MGN 2025 (cuaderno 01) |
| `area_total_ha` | Área del municipio en las tablas de MapBiomas | ha | MapBiomas Colección 3, tablas municipales |
| `agro_ha`, `agro_pct` | Zona agrícola y ganadera (nivel 1) | ha; % del área total | MapBiomas |
| `d_agro_pct` | Cambio neto agropecuario sobre el área total del año anterior | puntos porcentuales del territorio | cuaderno 60 |
| `sabana_ha`, `sabana_pct` | Praderas y herbáceas | ha; % del área total | MapBiomas |
| `palma_mapbiomas_ha` | Palma de aceite | ha | MapBiomas |
| `eva_sembrada_ha` | Área sembrada de todos los cultivos (2006–2025) | ha | EVA |
| `eva_palma_ha`, `eva_soya_ha`, `eva_maiz_ha`, `eva_arroz_ha` | Área sembrada por cultivo | ha | EVA |
| `focos_anual_total` | Detecciones Terra + Aqua en el año calendario (2003–2025) | detecciones | FIRMS (cuaderno 03) |
| `focos_seca_total` | Detecciones Terra + Aqua en la temporada seca (2004–2025) | detecciones | FIRMS (cuaderno 03) |
| `lluvia_anual_mm`, `lluvia_seca_mm` | Lluvia del año y de la temporada seca | mm | CHIRPS (cuaderno 11) |
| `lluvia_anual_anom_pct`, `lluvia_seca_anom_pct` | Lluvia frente a la normal 1991–2020 | % | CHIRPS (cuaderno 11) |
| `oni_anual`, `oni_seca` | Promedio del ONI del año y de la temporada seca, igual para los siete municipios | °C | NOAA (cuaderno 10) |

### `datos/comunes/panel_municipio_mes.csv` (cuaderno 60)
Una fila por municipio y mes: 7 × 540 = 3.780 filas (1981-01 a 2025-12). Llave: `mpio_cdpmp` + `mes`. Columnas: `lluvia_mm`, `normal_mm`, `anom_mm` y `anom_pct` (CHIRPS, cuaderno 11); `focos_total` (Terra + Aqua desde 2003-01, vacío antes) y `focos_terra` (desde 2000-11) (FIRMS, cuaderno 03); `oni` y `fase` (NOAA, cuaderno 10).