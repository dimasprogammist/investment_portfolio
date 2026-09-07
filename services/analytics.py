"""Аналитика портфеля: TWR, просадка, альфа, бета, концентрация."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from services.app_log import get_logger

log = get_logger()

INDEX_TICKER = "MCFTR"
MIN_BETA_POINTS = 20


def max_drawdown_pct(values: list[float]) -> float | None:
    peak = None
    worst = 0.0
    for value in values:
        if value is None or value <= 0:
            continue
        if peak is None or value > peak:
            peak = value
        dd = (value - peak) / peak
        if dd < worst:
            worst = dd
    if peak is None:
        return None
    return worst * 100


def twr_pct(history_df: pd.DataFrame, cashflows: dict) -> float | None:
    """Time-weighted return: доходность «как у фонда», без эффекта дат пополнений."""
    if history_df is None or history_df.empty or "value" not in history_df.columns:
        return None
    df = history_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    product = 1.0
    prev = None
    periods = 0
    for _, row in df.iterrows():
        value = float(row["value"] or 0)
        if value <= 0:
            continue
        dt = row["date"]
        cf = float(cashflows.get(dt, 0) or cashflows.get(dt.normalize(), 0) or 0)
        if prev is None or prev <= 0:
            prev = value
            continue
        ret = (value - cf - prev) / prev
        if ret < -0.99:
            ret = -0.99
        product *= 1 + ret
        periods += 1
        prev = value
    if periods == 0:
        return None
    return (product - 1) * 100


def annualize_twr(twr_total_pct: float, first_date, last_date) -> float | None:
    if twr_total_pct is None or first_date is None or last_date is None:
        return None
    days = (pd.to_datetime(last_date) - pd.to_datetime(first_date)).days
    if days < 30:
        return twr_total_pct
    years = days / 365.25
    total = 1 + twr_total_pct / 100
    if total <= 0:
        return twr_total_pct
    return (total ** (1 / years) - 1) * 100


def top3_share_pct(weights_pct: list[float]) -> float:
    weights = [max(0.0, float(w)) for w in weights_pct if w is not None]
    return sum(sorted(weights, reverse=True)[:3])


def _cashflow_on(dt, cashflows: dict) -> float:
    return float(cashflows.get(dt, 0) or cashflows.get(dt.normalize(), 0) or 0)


def daily_portfolio_returns(history_df: pd.DataFrame, cashflows: dict) -> pd.Series:
    df = history_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date")
    df = df.set_index("date")
    values = df["value"].astype(float)
    rets = []
    dates = []
    prev = None
    for dt, value in values.items():
        if value is None or value <= 0:
            continue
        cf = _cashflow_on(pd.Timestamp(dt), cashflows)
        if prev is None or prev <= 0:
            prev = value
            continue
        rets.append((value - cf - prev) / prev)
        dates.append(pd.Timestamp(dt))
        prev = value
    return pd.Series(rets, index=pd.DatetimeIndex(dates), name="port")


def beta_and_corr(port_rets: pd.Series, index_df: pd.DataFrame) -> tuple[float | None, float | None, int]:
    """
    Бета = cov(r_портфеля, r_индекса) / var(r_индекса).
    Корреляция — насколько движения совпадают по направлению (от −1 до 1).
    """
    if index_df is None or index_df.empty or port_rets is None or port_rets.empty:
        return None, None, 0
    idx = index_df.copy()
    idx["date"] = pd.to_datetime(idx["date"])
    idx = idx.sort_values("date").drop_duplicates("date")
    idx = idx.set_index("date")["close"].astype(float)
    idx_rets = idx.pct_change().dropna()
    aligned = pd.concat([port_rets.rename("p"), idx_rets.rename("m")], axis=1, join="inner").dropna()
    aligned = aligned.replace([np.inf, -np.inf], np.nan).dropna()
    n = len(aligned)
    if n < MIN_BETA_POINTS:
        return None, None, n
    p = aligned["p"].to_numpy(dtype=float)
    m = aligned["m"].to_numpy(dtype=float)
    var_m = float(np.var(m, ddof=1))
    if var_m <= 0:
        return None, None, n
    beta = float(np.cov(p, m, ddof=1)[0, 1] / var_m)
    corr = float(np.corrcoef(p, m)[0, 1])
    if not np.isfinite(beta):
        beta = None
    if not np.isfinite(corr):
        corr = None
    return beta, corr, n


def compute_from_history(user_id: int, start: date | None = None, end: date | None = None) -> dict:
    """TWR, просадка, альфа, бета и корреляция к MCFTR."""
    from DB.database import get_portfolio_history
    from history_cache import ensure_index_cached, get_prices_from_cache

    end = end or date.today()
    start = start or (end - timedelta(days=365))
    result = {
        "twr": None,
        "twr_ann": None,
        "drawdown": None,
        "alpha": None,
        "index_return": None,
        "beta": None,
        "corr": None,
        "beta_points": 0,
    }

    try:
        history_df = get_portfolio_history(start, end, user_id=user_id)
    except Exception as exc:
        log.warning("История для аналитики: %s", exc)
        return result

    if history_df is None or getattr(history_df, "empty", True):
        return result

    from DB.db_config import create_connection

    cashflows = {}
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute(
            "SELECT date, amount FROM deposits WHERE user_id=%s AND date BETWEEN %s AND %s",
            (user_id, start, end),
        )
        for d, amount in cursor.fetchall():
            cashflows[pd.to_datetime(d)] = float(amount or 0)
        conn.close()

    twr = twr_pct(history_df, cashflows)
    result["twr"] = twr
    result["drawdown"] = max_drawdown_pct(list(history_df["value"].astype(float)))
    first = history_df["date"].iloc[0]
    last = history_df["date"].iloc[-1]
    result["twr_ann"] = annualize_twr(twr, first, last)

    try:
        ensure_index_cached(INDEX_TICKER, start, end)
        bench = get_prices_from_cache(INDEX_TICKER, start, end)
        if bench is not None and not bench.empty:
            p0 = float(bench["close"].iloc[0])
            p1 = float(bench["close"].iloc[-1])
            if p0 > 0:
                result["index_return"] = (p1 / p0 - 1) * 100
                if twr is not None:
                    result["alpha"] = twr - result["index_return"]
            port_rets = daily_portfolio_returns(history_df, cashflows)
            beta, corr, n = beta_and_corr(port_rets, bench)
            result["beta"] = beta
            result["corr"] = corr
            result["beta_points"] = n
    except Exception as exc:
        log.info("Индекс MCFTR: %s", exc)
    return result
