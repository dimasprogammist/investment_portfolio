# prices.py - получение цен с MOEX
import requests

_usd_rate_cache = None
_usd_rate_time = None

# Словарь валютных облигаций с указанием номинала в валюте
CURRENCY_BONDS_CONFIG = {
    'RU000A10AXW4': {'currency': 'USD', 'nominal': 100},  # Сибур 0001P-03
    # Добавь другие валютные облигации по мере необходимости
}


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

'''
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
            # ВРЕМЕННАЯ ОТЛАДКА ДЛЯ ПЕРВОГО ТИКЕРА
            if ticker == 'SBER':
                print(f"\nОтладка {ticker}:")
                print(f"Колонки marketdata: {data['marketdata']['columns']}")
                for row in data['marketdata']['data']:
                    print(f"  Данные: {row}")

            for row in data['marketdata']['data']:
                # Пробуем разные индексы
                if len(row) > 4 and row[4] is not None:  # CURRENTVALUE
                    return float(row[4])
                elif len(row) > 2 and row[2] is not None:  # LASTVALUE
                    return float(row[2])
                elif len(row) > 3 and row[3] is not None:  # OPENVALUE
                    return float(row[3])
    except Exception as e:
        print(f"Ошибка получения цены для {ticker}: {e}")
    return None'''