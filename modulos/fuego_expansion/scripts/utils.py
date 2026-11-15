"""Funciones comunes de lectura, estadística y estilo de gráficas."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import config as cfg


# ---------------------------------------------------------------- lectura
def leer_csv(ruta, **kw) -> pd.DataFrame:
    return pd.read_csv(ruta, encoding="utf-8-sig", **kw)


# ------------------------------------------------------------ estadística
def fdr_bh(p) -> np.ndarray:
    """Valores q de Benjamini-Hochberg (control de la tasa de falsos descubrimientos).

    Reemplaza a scipy.stats.false_discovery_control(p, method="bh"), que exige
    scipy >= 1.11 (requirements.txt pide >= 1.10). Admite solo un vector 1-D sin NaN.
    """
    p = np.asarray(p, dtype=float)
    if p.ndim != 1 or np.isnan(p).any() or ((p < 0) | (p > 1)).any():
        raise ValueError("p debe ser un vector 1-D de valores entre 0 y 1, sin NaN.")
    n = p.size
    orden = np.argsort(p)
    q = p[orden] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    salida = np.empty(n)
    salida[orden] = np.minimum(q, 1.0)
    return salida


# ---------------------------------------------------------- transformación
def zscore_por_grupo(df: pd.DataFrame, cols, grupo="cod_mun") -> pd.DataFrame:
    """Estandariza cada columna dentro de cada municipio (media 0, desv. 1)."""
    g = df.groupby(grupo)[list(cols)]
    z = (df[list(cols)] - g.transform("mean")) / g.transform("std", ddof=1)
    z.columns = [f"z_{c}" for c in cols]
    return z


def rezagar(df: pd.DataFrame, col: str, k: int, grupo="cod_mun") -> pd.Series:
    """Valor de `col` k años antes (k>0) o k años después (k<0) en el mismo municipio."""
    return df.groupby(grupo)[col].shift(k)


# -------------------------------------------------------- efectos fijos
def _within(y, X, g):
    """Transformación intra-grupo (resta la media de cada municipio)."""
    g = np.asarray(g)
    _, inv = np.unique(g, return_inverse=True)
    n_g = inv.max() + 1
    cnt = np.bincount(inv, minlength=n_g).astype(float)

    def dem(a):
        a = np.asarray(a, float)
        if a.ndim == 1:
            return a - (np.bincount(inv, weights=a, minlength=n_g) / cnt)[inv]
        out = np.empty_like(a)
        for j in range(a.shape[1]):
            out[:, j] = dem(a[:, j])
        return out

    return dem(y), dem(X), inv, n_g


def fe_ols(y, X, g, nombres):
    """MCO con efectos fijos por grupo.

    Devuelve un DataFrame con el coeficiente, el error estándar clásico, el error
    estándar agrupado por municipio (CR1) y sus valores p.
    """
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    yw, Xw, inv, n_g = _within(y, X, g)
    n, k = Xw.shape
    xtx_inv = np.linalg.inv(Xw.T @ Xw)
    beta = xtx_inv @ Xw.T @ yw
    e = yw - Xw @ beta

    gl = n - k - n_g
    s2 = (e @ e) / gl
    se_iid = np.sqrt(np.diag(xtx_inv) * s2)

    meat = np.zeros((k, k))
    for j in range(n_g):
        idx = inv == j
        s = Xw[idx].T @ e[idx]
        meat += np.outer(s, s)
    corr = (n_g / (n_g - 1)) * ((n - 1) / (n - k))
    v_cl = corr * xtx_inv @ meat @ xtx_inv
    se_cl = np.sqrt(np.diag(v_cl))

    p_iid = 2 * stats.t.sf(np.abs(beta / se_iid), gl)
    p_cl = 2 * stats.t.sf(np.abs(beta / se_cl), n_g - 1)
    ss_tot = yw @ yw
    r2_w = 1 - (e @ e) / ss_tot if ss_tot > 0 else np.nan
    return pd.DataFrame(
        {
            "variable": nombres,
            "coef": beta,
            "ee_clasico": se_iid,
            "p_clasico": p_iid,
            "ee_mpio": se_cl,
            "p_mpio": p_cl,
            "n": n,
            "municipios": n_g,
            "r2_intra": r2_w,
        }
    )


def bootstrap_anios(y, X, g, anios, B=2000, semilla=cfg.SEMILLA):
    """Bootstrap por años: se remuestrean años completos (con sus 7 municipios).

    Conserva la dependencia entre municipios dentro de un mismo año (choques
    comunes como una sequía) y devuelve el intervalo del 95 % y un valor p.
    """
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    g = np.asarray(g)
    anios = np.asarray(anios)
    rng = np.random.default_rng(semilla)
    ua = np.unique(anios)
    filas_por_anio = {a: np.where(anios == a)[0] for a in ua}
    k = X.shape[1]
    out = np.full((B, k), np.nan)
    for b in range(B):
        sel = rng.choice(ua, size=len(ua), replace=True)
        idx = np.concatenate([filas_por_anio[a] for a in sel])
        yw, Xw, _, _ = _within(y[idx], X[idx], g[idx])
        try:
            out[b] = np.linalg.lstsq(Xw, yw, rcond=None)[0]
        except np.linalg.LinAlgError:
            continue
    lo, hi = np.nanpercentile(out, [2.5, 97.5], axis=0)
    p = 2 * np.minimum((out <= 0).mean(axis=0), (out >= 0).mean(axis=0))
    return lo, hi, np.minimum(p, 1.0)


# ------------------------------------------------------------ tendencia
def mann_kendall(x, t=None):
    """Prueba de Mann-Kendall (tau de Kendall contra el tiempo) y pendiente de Sen."""
    x = np.asarray(x, float)
    ok = ~np.isnan(x)
    x = x[ok]
    t = np.arange(len(x)) if t is None else np.asarray(t, float)[ok]
    tau, p = stats.kendalltau(t, x)
    sen = stats.theilslopes(x, t)[0] if len(x) >= 3 else np.nan
    return tau, p, sen


# ------------------------------------------------------------ estadística
def aicc(llf: float, k: int, n: int) -> float:
    """AIC corregido para muestras pequeñas."""
    aic = -2 * llf + 2 * k
    return aic + (2 * k * (k + 1)) / max(n - k - 1, 1)


def ccf_manual(x, y, kmax=4):
    """Correlación cruzada corr(x_t, y_{t+k}) para k de -kmax a kmax.

    k > 0: x va primero (x anticipa a y). k < 0: y va primero.
    Devuelve (lags, r, n_pares).
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    lags, r, npar = [], [], []
    for k in range(-kmax, kmax + 1):
        if k >= 0:
            a, b = x[: n - k], y[k:]
        else:
            a, b = x[-k:], y[: n + k]
        m = ~(np.isnan(a) | np.isnan(b))
        lags.append(k)
        npar.append(int(m.sum()))
        r.append(np.corrcoef(a[m], b[m])[0, 1] if m.sum() > 3 else np.nan)
    return np.array(lags), np.array(r), np.array(npar)


# ------------------------------------------------------------- gráficas
def estilo_matplotlib():
    import matplotlib as mpl

    mpl.rcParams.update(
        {
            "figure.facecolor": cfg.COLOR_SUPERFICIE,
            "axes.facecolor": cfg.COLOR_SUPERFICIE,
            "savefig.facecolor": cfg.COLOR_SUPERFICIE,
            "axes.edgecolor": cfg.COLOR_GRILLA,
            "axes.labelcolor": cfg.COLOR_TEXTO_2,
            "axes.titlecolor": cfg.COLOR_TEXTO,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": cfg.COLOR_GRILLA,
            "grid.linewidth": 0.6,
            "xtick.color": cfg.COLOR_TEXTO_2,
            "ytick.color": cfg.COLOR_TEXTO_2,
            "text.color": cfg.COLOR_TEXTO,
            "font.size": 9,
            "legend.frameon": False,
            "lines.linewidth": 2,
            "figure.dpi": 110,
            "savefig.dpi": 150,
        }
    )


def pie_fuente(fig, texto):
    fig.text(0.01, 0.005, texto, fontsize=7, color=cfg.COLOR_TEXTO_2, ha="left", va="bottom")
