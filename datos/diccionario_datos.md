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

De otras partes del proyecto se leen `datos/comunes/firms_mensual_municipio.csv`, `chirps_mensual_municipio.csv` y `oni_mensual.csv`