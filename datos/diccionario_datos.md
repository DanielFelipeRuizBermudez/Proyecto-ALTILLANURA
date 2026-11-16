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
| `cod_mun` | Código DIVIPOLA del municipio | texto, 5 dígitos | DANE |
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

Terra + Aqua cuenta cerca del doble de detecciones que Terra sola, así que los coeficientes por foco de las dos series no se comparan en magnitud; solo se compara si el intervalo cruza cero.
