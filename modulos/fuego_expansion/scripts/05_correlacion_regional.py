"""Correlación cruzada preblanqueada para la exploración regional."""
import numpy as np
import pandas as pd

from utils import ccf_manual


def ajustar_ar(x, p):
    """MCO de x_t = c + sum(phi_i x_{t-i}) + e_t. Devuelve phi y residuos."""
    n = len(x)
    if p == 0:
        return np.array([]), x - x.mean()
    Z = np.column_stack([np.ones(n - p)] + [x[p - i - 1: n - i - 1] for i in range(p)])
    yv = x[p:]
    beta, *_ = np.linalg.lstsq(Z, yv, rcond=None)
    return beta[1:], yv - Z @ beta


def elegir_ar(x, pmax=2):
    """Menor p cuyo AICc está a menos de 2 del mejor, comparado sobre la misma muestra."""
    recorte = x[pmax:]
    n = len(recorte)
    cand = []
    for p in range(pmax + 1):
        if p == 0:
            e = recorte - recorte.mean()
        else:
            Z = np.column_stack([np.ones(n)] + [x[pmax - i - 1: len(x) - i - 1] for i in range(p)])
            b, *_ = np.linalg.lstsq(Z, recorte, rcond=None)
            e = recorte - Z @ b
        k = p + 2
        cand.append((p, n * np.log((e @ e) / n) + 2 * k + 2 * k * (k + 1) / max(n - k - 1, 1)))
    mejor = min(c[1] for c in cand)
    return min(p for p, a in cand if a <= mejor + 2)


def preblanquear(x, y, p):
    phi, e_x = ajustar_ar(x, p)
    if p == 0:
        return x - x.mean(), y - y.mean()
    n = len(y)
    y_f = y[p:] - sum(phi[i] * y[p - i - 1: n - i - 1] for i in range(p))
    return e_x, y_f


def quitar_tendencia(v):
    t = np.arange(len(v), dtype=float)
    b = np.polyfit(t, v, 1)
    return v - np.polyval(b, t)


def correlacion_cruzada(reg, variable, kmax=1, resultado="d_agro_pct"):
    """Compara la quema y el cambio agropecuario regional en años contiguos."""
    reg = reg.sort_values("anio")
    if not reg["anio"].diff().iloc[1:].eq(1).all():
        raise ValueError("La correlación regional requiere años consecutivos.")
    y0 = reg[resultado].to_numpy(float)
    x0 = reg[variable].to_numpy(float)
    if not (np.isfinite(y0).all() and np.isfinite(x0).all()):
        raise ValueError("La correlación regional requiere series sin datos faltantes.")
    filas = []
    for trat in ("sin quitar tendencia", "tendencia lineal removida"):
        y = quitar_tendencia(y0) if trat.startswith("tendencia") else y0
        x = quitar_tendencia(x0) if trat.startswith("tendencia") else x0
        p = elegir_ar(x)
        ex, ey = preblanquear(x, y, p)
        lags, r, npar = ccf_manual(ex, ey, kmax)
        for k, rr, n in zip(lags, r, npar):
            filas.append((trat, variable, p, k, rr, n, 1.96 / np.sqrt(n)))
    t = pd.DataFrame(filas, columns=["tratamiento", "variable", "p_ar", "rezago", "r", "n_pares", "banda95"])
    t["significativo"] = t["r"].abs() > t["banda95"]
    return t
