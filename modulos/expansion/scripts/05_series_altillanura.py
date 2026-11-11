import warnings

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf, adfuller, kpss, pacf

import estilo
from config import NOMBRE_REGION, PROCESADOS, RAIZ
from series import CATALOGO, construir_series

ALFA = 0.05
SALIDA_GRAFICAS = RAIZ / "graficas" / "series_altillanura"


def ejes_anuales(ax, unidad):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    if unidad in ("ha", "t"):
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
    else:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))


def prueba_adf(x):
    try:
        return adfuller(x, autolag="AIC")[1]
    except Exception:
        return np.nan


def prueba_kpss(x):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return kpss(x, regression="c", nlags="auto")[1]
    except Exception:
        return np.nan


def es_estacionaria(p_adf, p_kpss):
    if np.isnan(p_adf) or np.isnan(p_kpss):
        return None
    return p_adf < ALFA and p_kpss >= ALFA


def diagnostico(nombre, serie):
    x = serie.dropna()
    fila = {
        "serie": nombre,
        "descripcion": CATALOGO[nombre][0],
        "fuente": CATALOGO[nombre][1],
        "unidad": CATALOGO[nombre][2],
        "desde": int(x.index.min()),
        "hasta": int(x.index.max()),
        "n": len(x),
    }
    actual = x.values.astype(float)
    d_sugerido = None
    for d in range(3):
        if len(actual) < 10 or np.allclose(actual, actual[0]):
            break
        p_adf, p_kpss = prueba_adf(actual), prueba_kpss(actual)
        fila[f"adf_p_d{d}"] = round(p_adf, 4)
        fila[f"kpss_p_d{d}"] = round(p_kpss, 4)
        if d_sugerido is None and es_estacionaria(p_adf, p_kpss):
            d_sugerido = d
        actual = np.diff(actual)
    fila["d_sugerido"] = d_sugerido if d_sugerido is not None else "revisar"
    return fila


def correlogramas(ax, valores, funcion, titulo):
    n = len(valores)
    rezagos = max(1, min(10, n // 2 - 1))
    if funcion == "acf":
        r = acf(valores, nlags=rezagos, fft=False)[1:]
    else:
        r = pacf(valores, nlags=rezagos, method="ywm")[1:]
    banda = 1.96 / np.sqrt(n)
    k = np.arange(1, rezagos + 1)
    ax.axhspan(-banda, banda, color=estilo.GRILLA, alpha=0.8, linewidth=0)
    ax.axhline(0, color=estilo.EJE, linewidth=0.8)
    ax.vlines(k, 0, r, color=estilo.SERIE_1, linewidth=2)
    ax.plot(k, r, "o", color=estilo.SERIE_1, markersize=4)
    ax.set_xticks(k)
    ax.set_ylim(-1.05, 1.05)
    ax.set_title(titulo, loc="left", fontsize=9.5, color=estilo.TINTA)
    ax.set_xlabel("Rezago (años)")


def grafica_serie(nombre, serie, fila):
    x = serie.dropna()
    d = fila["d_sugerido"] if isinstance(fila["d_sugerido"], int) else 1
    trabajada = x.copy()
    for _ in range(d):
        trabajada = trabajada.diff().dropna()
    descripcion, fuente, unidad = CATALOGO[nombre]

    fig, ejes = plt.subplots(2, 2, figsize=(11, 6.5))
    fig.subplots_adjust(left=0.09, right=0.98, top=0.82, bottom=0.09, wspace=0.24, hspace=0.45)
    fig.text(0.09, 0.95, f"{descripcion} · {NOMBRE_REGION}", fontsize=13, fontweight="bold", color=estilo.TINTA)
    fig.text(0.09, 0.905, f"Fuente: {fuente}. {fila['desde']}–{fila['hasta']}, {fila['n']} datos anuales. Diferencias sugeridas por ADF y KPSS: d = {fila['d_sugerido']}.", fontsize=9, color=estilo.TINTA_2)

    ax = ejes[0, 0]
    ax.plot(x.index, x.values, color=estilo.SERIE_1, linewidth=2)
    ax.set_title(f"Serie original ({unidad})", loc="left", fontsize=9.5, color=estilo.TINTA)
    ax.set_xlim(x.index.min(), x.index.max())
    ejes_anuales(ax, unidad)

    ax = ejes[0, 1]
    if d == 0:
        ax.plot(x.index, x.values, color=estilo.SERIE_2, linewidth=2)
        ax.set_title("Sin diferenciar (ya es estacionaria)", loc="left", fontsize=9.5, color=estilo.TINTA)
    else:
        ax.plot(trabajada.index, trabajada.values, color=estilo.SERIE_2, linewidth=2)
        ax.axhline(0, color=estilo.EJE, linewidth=0.8)
        etiqueta = "Primera diferencia" if d == 1 else f"Diferencia de orden {d}"
        ax.set_title(f"{etiqueta} ({unidad} por año)", loc="left", fontsize=9.5, color=estilo.TINTA)
    ax.set_xlim(x.index.min(), x.index.max())
    ejes_anuales(ax, unidad)

    valores = trabajada.values.astype(float)
    if len(valores) >= 6 and not np.allclose(valores, valores[0]):
        correlogramas(ejes[1, 0], valores, "acf", "ACF de la serie trabajada")
        correlogramas(ejes[1, 1], valores, "pacf", "PACF de la serie trabajada")
    else:
        for ax in ejes[1]:
            ax.set_axis_off()

    ruta = SALIDA_GRAFICAS / f"{nombre}.png"
    fig.savefig(ruta, dpi=160)
    plt.close(fig)


def resumen_visual(series, nombres):
    columnas = 4
    filas = int(np.ceil(len(nombres) / columnas))
    fig, ejes = plt.subplots(filas, columnas, figsize=(15, 2.6 * filas + 1))
    fig.subplots_adjust(left=0.05, right=0.985, top=1 - 0.9 / (2.6 * filas + 1), bottom=0.04, wspace=0.28, hspace=0.6)
    fig.text(0.05, 1 - 0.35 / (2.6 * filas + 1), f"Series anuales de la {NOMBRE_REGION}", fontsize=14, fontweight="bold", color=estilo.TINTA)
    for ax, nombre in zip(ejes.ravel(), nombres):
        x = series[nombre].dropna()
        ax.plot(x.index, x.values, color=estilo.SERIE_1, linewidth=1.8)
        ax.set_title(f"{CATALOGO[nombre][0]} ({CATALOGO[nombre][2]})", loc="left", fontsize=8.5, color=estilo.TINTA)
        ax.set_xlim(x.index.min(), x.index.max())
        ejes_anuales(ax, CATALOGO[nombre][2])
    for ax in ejes.ravel()[len(nombres):]:
        ax.set_axis_off()
    fig.savefig(SALIDA_GRAFICAS / "00_resumen.png", dpi=160)
    plt.close(fig)


def main():
    estilo.aplicar()
    SALIDA_GRAFICAS.mkdir(parents=True, exist_ok=True)
    series = construir_series()
    series.to_csv(PROCESADOS / "series_altillanura.csv", encoding="utf-8-sig")

    nombres = [c for c in series.columns if series[c].notna().sum() > 0]
    filas = []
    for nombre in nombres:
        fila = diagnostico(nombre, series[nombre])
        filas.append(fila)
        grafica_serie(nombre, series[nombre], fila)
    resumen_visual(series, nombres)

    pruebas = pd.DataFrame(filas)
    pruebas.to_csv(PROCESADOS / "series_altillanura_pruebas.csv", index=False, encoding="utf-8-sig")

    print(f"Series guardadas en datos/procesados/series_altillanura.csv ({len(nombres)} series)")
    print(f"Pruebas guardadas en datos/procesados/series_altillanura_pruebas.csv")
    print(f"Gráficas guardadas en graficas/series_altillanura/\n")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(pruebas[["serie", "fuente", "desde", "hasta", "n", "d_sugerido"]].to_string(index=False))
    if "eva_sembrada_total" not in series.columns:
        print("\nNo se encontró la EVA: solo se armaron las series de MapBiomas. Corra 01_descargar_eva.py para incluirlas.")


if __name__ == "__main__":
    main()
