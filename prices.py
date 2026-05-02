# prices.py - получение цен с MOEX
import requests
import pandas as pd
from datetime import datetime

_usd_rate_cache = None
_usd_rate_time = None

# Словарь валютных облигаций с указанием номинала в валюте
CURRENCY_BONDS_CONFIG = {
    'RU000A10AXW4': {'currency': 'USD', 'nominal': 100},  # Сибур 0001P-03
    # Добавь другие валютные облигации по мере необходимости
}

import requests
import pandas as pd
from datetime import datetime
import os

# Резервные данные по инфляции
DEFAULT_INFLATION = {
    '2023-01-01': 0.8, '2023-02-01': 0.5, '2023-03-01': 0.4, '2023-04-01': 0.4,
    '2023-05-01': 0.3, '2023-06-01': 0.4, '2023-07-01': 0.6, '2023-08-01': 0.3,
    '2023-09-01': 0.9, '2023-10-01': 0.8, '2023-11-01': 1.1, '2023-12-01': 0.7,
    '2024-01-01': 0.9, '2024-02-01': 0.7, '2024-03-01': 0.4, '2024-04-01': 0.5,
    '2024-05-01': 0.7, '2024-06-01': 0.6, '2024-07-01': 1.1, '2024-08-01': 0.2,
    '2024-09-01': 0.5, '2024-10-01': 0.8, '2024-11-01': 1.4, '2024-12-01': 0.8,
    '2025-01-01': 1.2, '2025-02-01': 0.8, '2025-03-01': 0.5, '2025-04-01': 0.5,
    '2025-05-01': 0.4, '2025-06-01': 0.3, '2025-07-01': 0.5, '2025-08-01': 0.1,
    '2025-09-01': 0.3, '2025-10-01': 0.6, '2025-11-01': 0.7, '2025-12-01': 0.8,
}

# Резервные данные по недвижимости (руб/кв.м)
DEFAULT_REAL_ESTATE = {
    '2023-06-30': 250000,
    '2023-12-31': 265000,
    '2024-06-30': 285000,
    '2024-12-31': 310000,
    '2025-06-30': 340000,
    '2025-12-31': 375000,
    '2026-03-31': 395000,
}


def fetch_inflation_from_cbr():
    """Загружает данные инфляции из ЦБ РФ"""
    try:
        # Прямая ссылка на Excel с данными инфляции
        url = "https://www.cbr.ru/vfs/statistics/table/inflation.xlsx"
        response = requests.get(url, timeout=30)
        df = pd.read_excel(response.content, skiprows=3)
        df.columns = ['date', 'inflation']
        df = df.dropna()
        df['date'] = pd.to_datetime(df['date'])
        df['inflation'] = pd.to_numeric(df['inflation'], errors='coerce')
        df = df[df['inflation'] > 0]

        result = {}
        for _, row in df.iterrows():
            result[row['date'].strftime('%Y-%m-%d')] = float(row['inflation'])
        return result if result else DEFAULT_INFLATION
    except Exception as e:
        print(f"Ошибка загрузки инфляции из ЦБ: {e}")
        return DEFAULT_INFLATION


def get_inflation_data():
    """Возвращает данные инфляции"""
    return {k: v for k, v in sorted(fetch_inflation_from_cbr().items()) if k >= '2023-01-01'}


def fetch_real_estate_from_rosstat():
    """Загружает индекс цен на недвижимость из открытых данных"""
    try:
        # Можно попробовать загрузить из IRN.RU
        url = "https://www.irn.ru/index/"
        response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})

        # Парсим HTML (упрощенно — берем последнее значение)
        import re
        match = re.search(r'Индекс стоимости жилья.*?(\d+)\s*₽/м²', response.text)
        if match:
            current_price = int(match.group(1))
            # Обновляем последнее значение
            data = DEFAULT_REAL_ESTATE.copy()
            data[datetime.now().strftime('%Y-%m-%d')] = current_price
            return data
    except Exception as e:
        print(f"Ошибка загрузки данных недвижимости: {e}")
    return DEFAULT_REAL_ESTATE


def get_real_estate_data():
    """Возвращает данные по недвижимости"""
    return fetch_real_estate_from_rosstat()


def update_benchmarks_in_db():
    """Обновляет бенчмарки в БД (инфляция + недвижимость)"""
    from DB.db_config import create_connection

    inflation = get_inflation_data()
    real_estate = get_real_estate_data()

    conn = create_connection()
    if not conn:
        return

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    # Инфляция
    for date_str, value in inflation.items():
        cursor.execute("""
            INSERT INTO benchmark_inflation (date, value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        """, (date_str, value))

    # Недвижимость
    for date_str, value in real_estate.items():
        cursor.execute("""
            INSERT INTO benchmark_real_estate (date, value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        """, (date_str, value))

    conn.commit()
    conn.close()
    print("Бенчмарки обновлены в БД")


def get_usd_rate():
    """Получение текущего курса USD/RUB с MOEX"""
    global _usd_rate_cache, _usd_rate_time
    from datetime import datetime, timedelta

    # Если кэш свежий (менее 1 часа), используем его
    if _usd_rate_cache is not None and _usd_rate_time is not None:
        if datetime.now() - _usd_rate_time < timedelta(hours=1):
            return _usd_rate_cache

    try:
        # Курс USD/RUB с MOEX
        url = "https://iss.moex.com/iss/engines/currency/markets/selt/securities/USDRUB_TOM.json"
        response = requests.get(url, timeout=10)
        data = response.json()

        if 'marketdata' in data and 'data' in data['marketdata']:
            for row in data['marketdata']['data']:
                if len(row) > 2 and row[2] is not None:
                    _usd_rate_cache = float(row[2])
                    _usd_rate_time = datetime.now()
                    return _usd_rate_cache
    except Exception as e:
        print(f"Ошибка получения курса доллара: {e}")

    return 92.5  # значение по умолчанию


def get_current_price(ticker, security_type='stock'):
    """Получение текущей цены с MOEX"""
    if security_type == 'stock':
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}.json"
    else:
        url = f"https://iss.moex.com/iss/engines/stock/markets/bonds/securities/{ticker}.json"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if 'marketdata' in data and 'data' in data['marketdata']:
            for row in data['marketdata']['data']:
                # Ищем колонки по названиям
                columns = data['marketdata']['columns']

                # Приоритет: MARKETPRICE > LAST > CURRENTVALUE > OPEN
                for col_name in ['MARKETPRICE', 'LAST', 'CURRENTVALUE', 'OPEN']:
                    if col_name in columns:
                        idx = columns.index(col_name)
                        if len(row) > idx and row[idx] is not None:
                            return float(row[idx])

                # Если не нашли по названиям — пробуем по индексам
                for idx in [24, 12, 4, 2]:
                    if len(row) > idx and row[idx] is not None:
                        return float(row[idx])
                    elif len(row) > 3 and row[3] is not None:
                        return float(row[3])

        if security_type == 'stock':
            url_candles = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}/candles.json"
        else:
            url_candles = f"https://iss.moex.com/iss/engines/stock/markets/bonds/securities/{ticker}/candles.json"

        params = {"interval": 24, "limit": 1}
        response = requests.get(url_candles, params=params, timeout=10)
        data = response.json()
        candles = data.get('candles', {}).get('data', [])
        if candles and len(candles[0]) > 1:
            return float(candles[0][1])

    except Exception as e:
        print(f"Ошибка получения цены для {ticker}: {e}")
    return None


def convert_bond_price_to_rub(price_percent, ticker):
    """Конвертирует цену облигации из процентов в рубли с учетом валюты"""
    # Проверяем, валютная ли облигация
    if ticker in CURRENCY_BONDS_CONFIG:
        config = CURRENCY_BONDS_CONFIG[ticker]
        if config['currency'] == 'USD':
            usd_rate = get_usd_rate()
            nominal_in_rub = config['nominal'] * usd_rate
            return price_percent * nominal_in_rub / 100
    else:
        # Обычная рублевая облигация с номиналом 1000₽
        return price_percent * 1000 / 100


def get_current_price_rub(ticker, security_type='stock'):
    """Получает текущую цену в рублях"""
    price = get_current_price(ticker, security_type)
    if price is None:
        return None

    if security_type == 'bond':
        return convert_bond_price_to_rub(price, ticker)
    return price


def get_all_prices(stocks, bonds):
    """Получение всех текущих цен (в рублях)"""
    prices = {}
    for ticker in stocks:
        price = get_current_price_rub(ticker, 'stock')
        if price:
            prices[ticker] = round(price, 2)
    for ticker in bonds:
        price = get_current_price_rub(ticker, 'bond')
        if price:
            prices[ticker] = round(price, 2)
    return prices