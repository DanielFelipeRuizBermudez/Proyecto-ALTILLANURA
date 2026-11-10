import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, PercentFormatter

from config import MUNICIPIOS, NOMBRE_REGION, RAIZ
from series import cargar_eva, cargar_mapbiomas

GRAFICAS = RAIZ / "graficas"

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TENUE = "#898781"
GRILLA = "#e1e0d9"
EJE = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
RESTO = "#d9d8d1"

ORDEN = [NOMBRE_REGION, "Puerto López", "Puerto Gaitán", "Mapiripán", "Puerto Carreño", "La Primavera", "Santa Rosalía", "Cumaribo"]

COBERTURAS = [
    ("Zona agrícola y ganadera", ["Zona agrícola y ganadera"], SERIES[0]),
    ("Sabana y humedales", ["Formación natural no forestal"], SERIES[1]),
    ("Bosque", ["Formación forestal"], SERIES[2]),
    ("Agua y sin vegetación", ["Cuerpo de agua", "Zona sin vegetación"], SERIES[3]),
]

CULTIVOS = [
    ("Maíz", ["MAIZ"], SERIES[0]),
    ("Soya", ["SOYA"], SERIES[1]),
    ("Palma de aceite", ["PALMA DE ACEITE"], SERIES[2]),
]


def estilo():
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "font.family": "sans-serif",
        "font.size": 9,
        "text.color": TINTA,
        "axes.labelcolor": TINTA_2,
        "axes.edgecolor": EJE,
        "axes.linewidth": 0.8,
        "xtick.color": TENUE,
        "ytick.color": TENUE,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRILLA,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "legend.frameon": False,
    })


def apilar(ax, x, capas, colores):
    base = np.zeros(len(x))
    for valores, color in zip(capas, colores):
        tope = base + np.asarray(valores, dtype=float)
        ax.fill_between(x, base, tope, color=color, alpha=0.85, linewidth=0.8, edgecolor=SUPERFICIE)
        base = tope


def figura(titulo, subtitulo):
    fig, ejes = plt.subplots(2, 4, figsize=(15, 7.5), sharex=True)
    fig.subplots_adjust(left=0.05, right=0.985, top=0.80, bottom=0.08, wspace=0.28, hspace=0.32)
    fig.text(0.05, 0.955, titulo, fontsize=14, fontweight="bold", color=TINTA)
    fig.text(0.05, 0.915, subtitulo, fontsize=9.5, color=TINTA_2)
    return fig, ejes.ravel()


def leyenda(fig, etiquetas, colores, linea=None):
    manijas = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.85) for c in colores]
    if linea:
        manijas.append(Line2D([0], [0], color=linea[1], linewidth=1.2))
        etiquetas = etiquetas + [linea[0]]
    fig.legend(manijas, etiquetas, loc="upper left", bbox_to_anchor=(0.045, 0.895), ncol=len(etiquetas), fontsize=9, handlelength=1.2, columnspacing=1.6)


def titulo_panel(ax, nombre, departamento=None):
    texto = nombre if departamento is None else f"{nombre}  ·  {departamento}"
    ax.set_title(texto, loc="left", fontsize=10, fontweight="bold" if departamento is None else "normal", color=TINTA, pad=6)


def grafica_cobertura(datos):
    datos = datos.copy()
    region = datos.groupby(["anio", "nivel_1"], as_index=False)["hectareas"].sum()
    region["municipio"] = NOMBRE_REGION
    tabla = pd.concat([datos[["municipio", "anio", "nivel_1", "hectareas"]], region], ignore_index=True)

    fig, ejes = figura(
        "¿Cómo ha cambiado el uso de la tierra en la Altillanura?",
        "Participación de cada cobertura en el área total del municipio, 1985–2024. Fuente: MapBiomas Colombia.",
    )
    departamentos = {n: d for n, d in MUNICIPIOS.values()}
    for ax, municipio in zip(ejes, ORDEN):
        sub = tabla[tabla["municipio"] == municipio].pivot_table(index="anio", columns="nivel_1", values="hectareas", aggfunc="sum")
        total = sub.sum(axis=1)
        x = sub.index.values
        capas = [sub[[c for c in clases if c in sub.columns]].sum(axis=1) / total for _, clases, _ in COBERTURAS]
        apilar(ax, x, capas, [c for _, _, c in COBERTURAS])
        agro_ini, agro_fin = capas[0].iloc[0], capas[0].iloc[-1]
        ax.annotate(f"{agro_fin:.0%}", xy=(x[-1], agro_fin), xytext=(-4, 4), textcoords="offset points", ha="right", va="bottom", fontsize=8.5, fontweight="bold", color=TINTA)
        ax.annotate(f"{agro_ini:.0%}", xy=(x[0], agro_ini), xytext=(4, 4), textcoords="offset points", ha="left", va="bottom", fontsize=8.5, color=TINTA_2)
        ax.set_ylim(0, 1)
        ax.set_xlim(x[0], x[-1])
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.set_xticks([1985, 2000, 2015, 2024])
        titulo_panel(ax, municipio, departamentos.get(municipio))
    leyenda(fig, [n for n, _, _ in COBERTURAS], [c for _, _, c in COBERTURAS])
    ruta = GRAFICAS / "1_cobertura_por_municipio.png"
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    return ruta


def grafica_cultivos(datos, eva):
    agro = datos[datos["nivel_1"] == "Zona agrícola y ganadera"].groupby(["municipio", "anio"])["hectareas"].sum()
    anios = sorted(set(eva["anio"]) & set(datos["anio"]))
    eva = eva[eva["anio"].isin(anios)]
    sembrada = eva.pivot_table(index=["municipio", "anio"], columns="cultivo", values="area_sembrada_ha", aggfunc="sum")

    fig, ejes = figura(
        "¿Cuánto del área agropecuaria son cultivos?",
        "Área sembrada según la EVA dentro del área agropecuaria que detecta MapBiomas, en miles de hectáreas. "
        "El resto es sobre todo pasto para ganado.",
    )
    departamentos = {n: d for n, d in MUNICIPIOS.values()}
    avisos = []
    for ax, municipio in zip(ejes, ORDEN):
        if municipio == NOMBRE_REGION:
            area = agro.groupby("anio").sum().reindex(anios)
            cult = sembrada.groupby("anio").sum(min_count=1).reindex(anios)
        else:
            area = agro.xs(municipio, level="municipio").reindex(anios)
            cult = sembrada.xs(municipio, level="municipio").reindex(anios) if municipio in sembrada.index.get_level_values(0) else pd.DataFrame(index=anios)
        total_eva = cult.sum(axis=1, min_count=1)
        capas = []
        usados = []
        for _, nombres, _ in CULTIVOS:
            cols = [c for c in nombres if c in cult.columns]
            capas.append(cult[cols].sum(axis=1).where(total_eva.notna()) if cols else total_eva * 0)
            usados += cols
        otros = (total_eva - sum(capas)).clip(lower=0)
        resto = (area - total_eva).clip(lower=0)
        if ((area - total_eva) < 0).any():
            avisos.append(municipio)
        capas += [otros, resto]
        colores = [c for _, _, c in CULTIVOS] + [SERIES[3], RESTO]
        x = np.array(anios)
        apilar(ax, x, [c / 1000 for c in capas], colores)
        ax.plot(x, area / 1000, color=TINTA_2, linewidth=1.2)
        fraccion = (total_eva / area).dropna()
        if not fraccion.empty:
            ax.text(0.02, 0.96, f"Cultivos {fraccion.index[-1]}: {fraccion.iloc[-1]:.0%}", transform=ax.transAxes, ha="left", va="top", fontsize=8.5, color=TINTA)
        ax.set_xlim(x[0], x[-1])
        ax.set_ylim(0, None)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", ".")))
        ax.set_xticks([anios[0], 2012, 2018, anios[-1]])
        titulo_panel(ax, municipio, departamentos.get(municipio))
    etiquetas = [n for n, _, _ in CULTIVOS] + ["Otros cultivos", "Resto del área agropecuaria"]
    colores = [c for _, _, c in CULTIVOS] + [SERIES[3], RESTO]
    leyenda(fig, etiquetas, colores, linea=("Área agropecuaria (MapBiomas)", TINTA_2))
    fig.text(0.05, 0.02, "Los huecos en un municipio son años sin reporte en la EVA. La rotación soya-maíz puede contar dos veces el mismo lote en un año.", fontsize=8, color=TENUE)
    ruta = GRAFICAS / "2_cultivos_vs_area_agropecuaria.png"
    fig.savefig(ruta, dpi=200)
    plt.close(fig)
    return ruta, avisos


def main():
    estilo()
    GRAFICAS.mkdir(parents=True, exist_ok=True)
    datos = cargar_mapbiomas()
    print(f"Guardada: {grafica_cobertura(datos)}")
    eva = cargar_eva()
    if eva is None:
        print("No se encontró la EVA. Corra primero 01_descargar_eva.py para la segunda gráfica.")
        return
    ruta, avisos = grafica_cultivos(datos, eva)
    print(f"Guardada: {ruta}")
    if avisos:
        print(f"En algunos años la EVA reporta más área sembrada que el área agropecuaria de MapBiomas: {avisos}")


if __name__ == "__main__":
    main()
