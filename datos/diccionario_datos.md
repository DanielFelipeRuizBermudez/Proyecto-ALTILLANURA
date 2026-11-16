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
