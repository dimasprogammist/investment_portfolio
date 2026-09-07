"""Клиент ISS MOEX: одна сессия, пакетные котировки, retry, НКД."""
from __future__ import annotations

import time
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.app_log import get_logger

log = get_logger()

ISS_BASE = "https://iss.moex.com/iss"
CHUNK = 20
TIMEOUT = 20

from config import CURRENCY_BONDS_CONFIG as CURRENCY_BONDS

LAST_QUOTES: dict[str, dict] = {}


def _session() -> requests.Session:
    session = requests.Session()
    retry_kwargs = dict(
        total=3,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
    )
    try:
        retry = Retry(allowed_methods=("GET",), **retry_kwargs)
    except TypeError:
        retry = Retry(method_whitelist=("GET",), **retry_kwargs)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "InvestmentPortfolio/1.0"})
    return session


SESSION = _session()


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _iss_table(payload: dict, name: str) -> list[dict]:
    block = payload.get(name) or {}
    columns = [str(c).lower() for c in (block.get("columns") or [])]
    rows = block.get("data") or []
    return [dict(zip(columns, row)) for row in rows]


def _get_json(url: str, params: dict | None = None) -> dict:
    response = SESSION.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_usd_rate() -> float:
    try:
        data = _get_json(
            f"{ISS_BASE}/engines/currency/markets/selt/securities/USDRUB_TOM.json",
            {"iss.meta": "off", "iss.only": "marketdata", "marketdata.columns": "LAST,MARKETPRICE"},
        )
        for row in _iss_table(data, "marketdata"):
            for key in ("LAST", "MARKETPRICE"):
                if row.get(key) is not None:
                    return float(row[key])
    except Exception as exc:
        log.warning("Курс USD/RUB недоступен: %s", exc)
    return 92.5


def _pick_price(row: dict) -> float | None:
    for key in ("MARKETPRICE", "LAST", "LCURRENTPRICE", "OPEN"):
        value = row.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def _bond_dirty_rub(ticker: str, price_pct: float, nkd: float | None, usd_rate: float) -> float:
    cfg = CURRENCY_BONDS.get(ticker)
    if cfg and cfg.get("currency") == "USD":
        clean = price_pct * cfg["nominal"] * usd_rate / 100
        extra = (nkd or 0) * usd_rate
        return clean + extra
    clean = price_pct * 1000 / 100
    return clean + (nkd or 0)


def _fetch_market(tickers: list[str], market: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not tickers:
        return result
    columns = "SECID,MARKETPRICE,LAST,OPEN,ACCRUEDINT"
    url = f"{ISS_BASE}/engines/stock/markets/{market}/securities.json"
    for group in _chunks(tickers, CHUNK):
        params = {
            "securities": ",".join(group),
            "iss.meta": "off",
            "iss.only": "marketdata",
            "marketdata.columns": columns,
        }
        try:
            data = _get_json(url, params)
        except Exception as exc:
            log.warning("Пакет ISS %s (%s): %s", market, group, exc)
            continue
        for row in _iss_table(data, "marketdata"):
            ticker = row.get("SECID")
            if not ticker:
                continue
            price = _pick_price(row)
            nkd = None
            if row.get("ACCRUEDINT") is not None:
                try:
                    nkd = float(row["ACCRUEDINT"])
                except (TypeError, ValueError):
                    nkd = None
            result[str(ticker)] = {"price": price, "nkd": nkd}
        time.sleep(0.05)
    return result


def fetch_quotes(stocks: list[str], bonds: list[str]) -> dict[str, dict]:
    """
    Пакетно загружает котировки. Для облигаций цена в рублях — грязная (с НКД).
    """
    quotes: dict[str, dict] = {}
    usd_rate = get_usd_rate() if bonds else 92.5
    stock_data = _fetch_market(list(stocks), "shares")
    bond_data = _fetch_market(list(bonds), "bonds")

    for ticker in stocks:
        info = stock_data.get(ticker) or {}
        price = info.get("price")
        if price is None:
            continue
        quotes[ticker] = {
            "ticker": ticker,
            "type": "stock",
            "price_rub": round(float(price), 2),
            "price_pct": None,
            "nkd": 0.0,
        }

    for ticker in bonds:
        info = bond_data.get(ticker) or {}
        price_pct = info.get("price")
        if price_pct is None:
            continue
        nkd = info.get("nkd") or 0.0
        dirty = _bond_dirty_rub(ticker, float(price_pct), nkd, usd_rate)
        quotes[ticker] = {
            "ticker": ticker,
            "type": "bond",
            "price_rub": round(dirty, 2),
            "price_pct": round(float(price_pct), 2),
            "nkd": round(float(nkd), 2),
        }

    LAST_QUOTES.clear()
    LAST_QUOTES.update(quotes)
    return quotes


def save_price_cache(quotes: dict[str, dict]) -> None:
    from DB.db_config import create_connection

    if not quotes:
        return
    conn = create_connection()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    for q in quotes.values():
        cursor.execute(
            """
            INSERT INTO price_cache (ticker, security_type, price_rub, price_pct, nkd, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                price_rub = VALUES(price_rub),
                price_pct = VALUES(price_pct),
                nkd = VALUES(nkd),
                updated_at = NOW()
            """,
            (q["ticker"], q["type"], q["price_rub"], q.get("price_pct"), q.get("nkd") or 0),
        )
    conn.commit()
    conn.close()


def load_price_cache(tickers: list[str]) -> dict[str, dict]:
    from DB.db_config import create_connection

    if not tickers:
        return {}
    conn = create_connection()
    if not conn:
        return {}
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    placeholders = ",".join(["%s"] * len(tickers))
    cursor.execute(
        f"SELECT ticker, security_type, price_rub, price_pct, nkd FROM price_cache WHERE ticker IN ({placeholders})",
        tuple(tickers),
    )
    result = {}
    for ticker, sec_type, price_rub, price_pct, nkd in cursor.fetchall():
        result[ticker] = {
            "ticker": ticker,
            "type": sec_type,
            "price_rub": float(price_rub or 0),
            "price_pct": float(price_pct) if price_pct is not None else None,
            "nkd": float(nkd or 0),
        }
    conn.close()
    return result
