"""Бенчмарки для графика портфеля.

Инфляция берётся с официальной страницы Банка России
(https://www.cbr.ru/hd_base/infl/) — это месячная инфляция в % г/г по Росстату.

График недвижимости убран: в приложении не было достоверного ряда цен,
только захардкоженные значения, которые искажали сравнение.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from DB.db_config import create_connection

CBR_INFLATION_URL = "https://www.cbr.ru/hd_base/infl/"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; InvestmentPortfolio/1.0; +https://www.cbr.ru/hd_base/infl/)",
}


def fetch_cbr_inflation_yoy(from_year: int = 2013) -> dict[str, float]:
    """
    Загружает ряд «Инфляция, % г/г» с сайта ЦБ РФ.

    Возвращает словарь {YYYY-MM-01: yoy_percent}.
    """
    now = datetime.now()
    params = {
        "UniDbQuery.Posted": "True",
        "UniDbQuery.From": f"01.{from_year}",
        "UniDbQuery.To": now.strftime("%m.%Y"),
    }
    response = requests.get(
        CBR_INFLATION_URL,
        params=params,
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", class_="data") or soup.find("table")
    if table is None:
        raise ValueError("На странице ЦБ не найдена таблица инфляции")

    header_cells = table.find("tr")
    if header_cells is None:
        raise ValueError("Таблица инфляции ЦБ без заголовка")
    headers = [cell.get_text(" ", strip=True).lower() for cell in header_cells.find_all(["th", "td"])]
    infl_idx = next((i for i, h in enumerate(headers) if "инфляц" in h), 2)

    result: dict[str, float] = {}
    for row in table.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) <= infl_idx:
            continue
        raw_date = cells[0].strip()
        raw_value = cells[infl_idx].strip().replace(",", ".").replace("\xa0", "")
        try:
            if "." in raw_date:
                month, year = raw_date.split(".")[:2]
                date_key = f"{int(year):04d}-{int(month):02d}-01"
            else:
                continue
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        result[date_key] = value

    if not result:
        raise ValueError("Таблица инфляции ЦБ пуста или не разобрана")
    return dict(sorted(result.items()))


def get_inflation_yoy(from_year: int = 2023) -> dict[str, float]:
    """Официальный ряд инфляции г/г, начиная с указанного года."""
    series = fetch_cbr_inflation_yoy(from_year=2013)
    return {k: v for k, v in series.items() if k >= f"{from_year}-01-01"}


def update_benchmarks_in_db() -> None:
    """Сохраняет ряд инфляции ЦБ в таблицу benchmark_inflation."""
    inflation = get_inflation_yoy(from_year=2023)
    conn = create_connection()
    if not conn:
        raise RuntimeError("Нет подключения к БД для сохранения бенчмарков")

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    for date_str, value in inflation.items():
        cursor.execute(
            """
            INSERT INTO benchmark_inflation (date, value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE value = VALUES(value)
            """,
            (date_str, value),
        )
    conn.commit()
    conn.close()


def inflation_adjusted_deposits(dates: pd.Series, deposits: dict, yoy: dict[str, float]) -> pd.Series:
    """
    Номинальная стоимость пополнений, проиндексированная инфляцией.

    Для каждого месяца берётся официальная инфляция г/г и переводится
    в эквивалентный месячный темп: (1 + yoy/100) ** (1/12) - 1.
    Затем каждое пополнение растёт этим темпом до даты на графике.
    """
    if not yoy or not deposits:
        return pd.Series(0.0, index=dates.index)

    inf = pd.Series(yoy)
    inf.index = pd.to_datetime(inf.index)
    inf = inf.sort_index().astype(float)
    monthly_factor = (1.0 + inf / 100.0) ** (1.0 / 12.0)

    chart_dates = pd.to_datetime(dates)
    result = pd.Series(0.0, index=dates.index)

    for deposit_date, amount in deposits.items():
        dep = pd.Timestamp(deposit_date)
        for i, chart_date in enumerate(chart_dates):
            if chart_date < dep:
                continue
            period = monthly_factor[(monthly_factor.index > dep) & (monthly_factor.index <= chart_date)]
            growth = float(period.prod()) if not period.empty else 1.0
            result.iloc[i] += float(amount) * growth

    return result
