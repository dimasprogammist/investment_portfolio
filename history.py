import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from services.moex_client import SESSION
except Exception:
    import requests
    SESSION = requests.Session()


def get_historical_prices(ticker, start_date, end_date, security_type='stock', interval=24):
    """
    Получение исторических цен закрытия для одного тикера с ПАГИНАЦИЕЙ.
    Запрашиваем ВСЕ данные от start_date до end_date, разбивая на чанки.
    """
    if security_type == 'stock':
        base_url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}/candles.json"
    else:
        base_url = f"https://iss.moex.com/iss/engines/stock/markets/bonds/securities/{ticker}/candles.json"

    all_candles = []
    current_start = start_date
    columns = None

    while current_start < end_date:
        from_str = current_start.strftime('%Y-%m-%d') if hasattr(current_start, 'strftime') else str(current_start)
        till_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else str(end_date)
        params = {
            'interval': interval,
            'from': from_str,
            'till': till_str
        }

        try:
            response = SESSION.get(base_url, params=params, timeout=30)
            data = response.json()

            if 'candles' not in data or 'data' not in data['candles']:
                break

            candles = data['candles']['data']
            if columns is None:
                columns = data['candles']['columns']

            if not candles:
                break

            all_candles.extend(candles)

            # Если получили меньше 500 — это всё, выходим
            if len(candles) < 500:
                break

            # Берём дату последней свечи + 1 день как новый старт
            begin_idx = columns.index('begin') if 'begin' in columns else 0
            last_date_str = candles[-1][begin_idx]
            if ' ' in str(last_date_str):
                last_date = datetime.strptime(str(last_date_str)[:10], '%Y-%m-%d').date()
            else:
                last_date = datetime.strptime(str(last_date_str), '%Y-%m-%d').date()

            current_start = last_date + timedelta(days=1)
            print(f"  {ticker}: загружено {len(candles)} свечей, следующая дата: {current_start}")

        except Exception as e:
            print(f"Ошибка получения истории для {ticker}: {e}")
            break

    if not all_candles:
        print(f"Нет данных для {ticker}")
        return None

    if columns is None:
        columns = ['open', 'close', 'high', 'low', 'value', 'volume', 'begin', 'end']

    df = pd.DataFrame(all_candles, columns=columns)

    close_idx = columns.index('close') if 'close' in columns else 1
    begin_idx = columns.index('begin') if 'begin' in columns else 0

    df['date'] = pd.to_datetime(df['begin']).dt.date
    df['close'] = pd.to_numeric(df[columns[close_idx]], errors='coerce')

    df = df[['date', 'close']].dropna().drop_duplicates(subset='date').sort_values('date')

    return df


def get_all_historical_prices(tickers, start_date, end_date, security_type='stock'):
    """
    Получение исторических цен для нескольких тикеров
    Возвращает словарь: {ticker: DataFrame}
    """
    prices = {}

    for ticker in tickers:
        print(f"Загрузка истории для {ticker}...")
        df = get_historical_prices(ticker, start_date, end_date, security_type)
        if df is not None:
            prices[ticker] = df

    return prices


def get_price_on_date(ticker, date, security_type='stock'):
    """
    Возвращает цену закрытия на указанную дату или ближайшую предыдущую доступную.

    Источник данных: свечи MOEX. Запрашиваем окно 30 дней назад, чтобы корректно
    обрабатывать нерабочие/праздничные дни и пропуски торгов.
    """
    try:
        df = get_historical_prices(ticker, date - timedelta(days=30), date + timedelta(days=1), security_type)
        if df is not None and not df.empty:
            prices_on_date = df[df['date'] <= date]
            if not prices_on_date.empty:
                return prices_on_date.iloc[-1]['close']
    except Exception as e:
        print(f"Ошибка получения цены {ticker} на {date}: {e}")

    return None


# Кеширование данных, чтобы не грузить MOEX при каждом построении графика
_cache = {}


def get_cached_historical_prices(ticker, start_date, end_date, security_type='stock'):
    """Получение исторических цен с кэшированием в памяти"""
    cache_key = f"{ticker}_{start_date}_{end_date}"

    if cache_key not in _cache:
        _cache[cache_key] = get_historical_prices(ticker, start_date, end_date, security_type)

    return _cache[cache_key]


def clear_cache():
    """Очистка кэша"""
    global _cache
    _cache = {}