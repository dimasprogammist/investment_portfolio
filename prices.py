# prices.py - получение цен с MOEX
import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

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
    """Пакетная загрузка цен ISS. При сбое — кэш из БД."""
    from services.moex_client import fetch_quotes, save_price_cache, load_price_cache, LAST_QUOTES

    tickers = list(stocks) + list(bonds)
    quotes = {}
    try:
        quotes = fetch_quotes(list(stocks), list(bonds))
        if quotes:
            try:
                save_price_cache(quotes)
            except Exception:
                pass
    except Exception as e:
        print(f"Ошибка пакетной загрузки цен: {e}")

    missing = [t for t in tickers if t not in quotes]
    if missing:
        cached = load_price_cache(missing)
        quotes.update(cached)
        LAST_QUOTES.update(cached)

    return {ticker: round(float(q["price_rub"]), 2) for ticker, q in quotes.items() if q.get("price_rub")}


def fetch_all_assets_from_moex():
    """Загружает список ВСЕХ акций и облигаций с MOEX с пагинацией"""
    assets = []

    # Акции
    try:
        start = 0
        while True:
            url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities.json?start={start}&limit=100"
            response = requests.get(url, timeout=30)
            data = response.json()

            if 'securities' not in data or 'data' not in data['securities']:
                break

            rows = data['securities']['data']
            if not rows:
                break

            for row in rows:
                ticker = row[0]
                name = row[2]
                if ticker and name:
                    assets.append((ticker, name, 'stock'))

            if len(rows) < 100:
                break
            start += 100

        print(f"Загружено {len([a for a in assets if a[2] == 'stock'])} акций")
    except Exception as e:
        print(f"Ошибка загрузки акций: {e}")

    # Облигации — ТОЧНО ТАК ЖЕ
    try:
        start = 0
        while True:
            url = f"https://iss.moex.com/iss/engines/stock/markets/bonds/securities.json?start={start}&limit=100"
            response = requests.get(url, timeout=30)
            data = response.json()

            if 'securities' not in data or 'data' not in data['securities']:
                break

            rows = data['securities']['data']
            if not rows:
                break

            for row in rows:
                ticker = row[0]
                name = row[2]
                if ticker and name:
                    assets.append((ticker, name, 'bond'))

            if len(rows) < 100:
                break
            start += 100

        print(f"Загружено {len([a for a in assets if a[2] == 'bond'])} облигаций")
    except Exception as e:
        print(f"Ошибка загрузки облигаций: {e}")

    return assets


def update_available_assets():
    """Обновляет таблицу available_assets из MOEX (без пагинации, до 750 записей)"""
    from DB.db_config import create_connection

    print("Загрузка списка активов с MOEX...")

    conn = create_connection()
    if not conn:
        print("ОШИБКА: Нет подключения к БД")
        return

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    saved = 0

    # Акции
    try:
        url = "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"
        r = requests.get(url, timeout=30)
        data = r.json()
        rows = data['securities']['data']
        for row in rows:
            cursor.execute("INSERT IGNORE INTO available_assets (ticker, name, security_type) VALUES (%s, %s, 'stock')",
                           (row[0], (row[2] or row[0])[:200]))
            saved += 1
        print(f"Акций: {len(rows)}")
    except Exception as e:
        print(f"Ошибка загрузки акций: {e}")

    # Облигации
    try:
        url = "https://iss.moex.com/iss/engines/stock/markets/bonds/securities.json"
        r = requests.get(url, timeout=30)
        data = r.json()
        rows = data['securities']['data']
        for row in rows:
            cursor.execute("INSERT IGNORE INTO available_assets (ticker, name, security_type) VALUES (%s, %s, 'bond')",
                           (row[0], (row[2] or row[0])[:200]))
            saved += 1
        print(f"Облигаций: {len(rows)}")
    except Exception as e:
        print(f"Ошибка загрузки облигаций: {e}")

    conn.commit()
    conn.close()
    print(f"Сохранено {saved} активов в БД")


def get_fundamentals(ticker):
    """Загружает фундаментальные показатели со Smart-lab + расчётные"""
    from bs4 import BeautifulSoup

    try:
        url = f"https://smart-lab.ru/q/shares_fundamental/{ticker}/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        tables = soup.find_all('table')

        result = {
            'ticker': ticker,
            'market_cap': None, 'ev': None, 'revenue': None, 'net_income': None,
            'ebitda': None, 'ebit': None, 'fcf': None, 'capex': None,
            'total_debt': None, 'cash_equivalents': None,
            'pe': None, 'pb': None, 'ps': None, 'pcf': None, 'pfcf': None,
            'ev_s': None, 'evebitda': None, 'evebit': None,
            'de': None, 'debt_ebitda': None, 'net_debt_ebitda': None,
            'capex_revenue': None,
            'roe': None, 'roa': None, 'roic': None, 'roce': None,
            'net_margin': None, 'operating_margin': None, 'ebitda_margin': None,
            'current_ratio': None,
            'report_date': None, 'company_type': 'industrial',
            'net_operating_income': None,
        }

        for table in tables:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue

            header_cells = rows[0].find_all(['td', 'th'])
            is_bank_table = len(header_cells) == 17

            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue

                row_ticker = cells[2].get_text(strip=True) if len(cells) > 2 else ''
                if row_ticker.upper() != ticker.upper():
                    continue

                if is_bank_table:
                    result['company_type'] = 'bank'
                    try:
                        result['market_cap'] = float(cells[5].get_text(strip=True).replace(' ', '')) if cells[
                            5].get_text(strip=True) else None
                        result['net_operating_income'] = float(cells[6].get_text(strip=True).replace(' ', '')) if cells[
                            6].get_text(strip=True) else None
                        result['net_income'] = float(cells[7].get_text(strip=True).replace(' ', '')) if cells[
                            7].get_text(strip=True) else None
                        result['pe'] = float(cells[11].get_text(strip=True).replace(',', '.')) if cells[11].get_text(
                            strip=True) else None
                        result['pb'] = float(cells[12].get_text(strip=True).replace(',', '.')) if cells[12].get_text(
                            strip=True) else None
                        result['roe'] = float(cells[14].get_text(strip=True).replace('%', '').replace(',', '.')) if \
                        cells[14].get_text(strip=True) else None
                        result['roa'] = float(cells[15].get_text(strip=True).replace('%', '').replace(',', '.')) if \
                        cells[15].get_text(strip=True) else None
                        result['report_date'] = cells[16].get_text(strip=True) if len(cells) > 16 else None
                    except Exception as e:
                        print(f"    Ошибка банка: {e}")
                else:
                    result['company_type'] = 'industrial'
                    try:
                        result['market_cap'] = float(cells[5].get_text(strip=True).replace(' ', '')) if cells[
                            5].get_text(strip=True) else None
                        result['ev'] = float(cells[6].get_text(strip=True).replace(' ', '')) if cells[6].get_text(
                            strip=True) else None
                        result['revenue'] = float(cells[7].get_text(strip=True).replace(' ', '')) if cells[7].get_text(
                            strip=True) else None
                        result['net_income'] = float(cells[8].get_text(strip=True).replace(' ', '')) if cells[
                            8].get_text(strip=True) else None
                        result['pe'] = float(cells[12].get_text(strip=True).replace(',', '.')) if cells[12].get_text(
                            strip=True) else None
                        result['ps'] = float(cells[13].get_text(strip=True).replace(',', '.')) if cells[13].get_text(
                            strip=True) else None
                        result['pb'] = float(cells[14].get_text(strip=True).replace(',', '.')) if cells[14].get_text(
                            strip=True) else None
                        result['evebitda'] = float(cells[15].get_text(strip=True).replace(',', '.')) if cells[
                            15].get_text(strip=True) else None

                        # EBITDA расчётная: EV / EV/EBITDA
                        if result['ev'] and result['evebitda'] and result['evebitda'] > 0:
                            result['ebitda'] = result['ev'] / result['evebitda']

                        # EV/S расчётный
                        if result['ev'] and result['revenue'] and result['revenue'] > 0:
                            result['ev_s'] = result['ev'] / result['revenue']

                        if result['debt_ebitda'] and result['ebitda']:
                            result['total_debt'] = result['debt_ebitda'] * result['ebitda']

                        # Долг/EBITDA
                        debt_text = cells[17].get_text(strip=True) if len(cells) > 17 else ''
                        if debt_text and debt_text not in ('', '-', '—'):
                            result['debt_ebitda'] = float(debt_text.replace(',', '.'))
                            # Чистый долг примерно равен долгу (упрощённо)
                            if result['ebitda'] and result['ebitda'] > 0:
                                result['net_debt_ebitda'] = result['debt_ebitda']

                        # Рентабельность EBITDA
                        ebitda_margin_text = cells[16].get_text(strip=True).replace('%', '').replace(',', '.') if len(
                            cells) > 16 else ''
                        if ebitda_margin_text and ebitda_margin_text not in ('', '-', '—'):
                            result['ebitda_margin'] = float(ebitda_margin_text)

                        result['report_date'] = cells[18].get_text(strip=True) if len(cells) > 18 else None

                        # Чистая маржа расчётная
                        if result['net_income'] and result['revenue'] and result['revenue'] > 0:
                            result['net_margin'] = (result['net_income'] / result['revenue']) * 100

                    except Exception as e:
                        print(f"    Ошибка компании: {e}")

                break

        if result['pe'] or result['pb']:
            print(f"  ✅ {ticker} ({result['company_type']}): P/E={result['pe']}, P/B={result['pb']}")
            return result
        return None

    except Exception as e:
        print(f"  ❌ {ticker}: {e}")
        return None


def get_tradingview_fundamentals(tickers):
    """Дозагружает ВСЕ мультипликаторы с TradingView"""
    from DB.db_config import create_connection

    url = "https://scanner.tradingview.com/russia/scan"
    body = {
        "symbols": {"tickers": [f"RUS:{t}" for t in tickers], "query": {"types": []}},
        "columns": [
            "price_earnings_ttm",  # 0 - P/E
            "price_book_ratio",  # 1 - P/B
            "price_revenue_ttm",  # 2 - P/S
            "enterprise_value_ebitda_ttm",  # 3 - EV/EBITDA
            "return_on_equity",  # 4 - ROE
            "return_on_assets",  # 5 - ROA
            "net_margin",  # 6 - Net Margin
            "gross_margin",  # 7 - Gross Margin
            "operating_margin",  # 8 - Operating Margin
            "debt_to_equity",  # 9 - D/E
            "price_to_free_cash_flow",  # 10 - P/FCF
            "price_to_cash_flow",  # 11 - P/CF
            "enterprise_value_ebit_ttm",  # 12 - EV/EBIT
            "return_on_invested_capital",  # 13 - ROIC
            "return_on_capital_employed",  # 14 - ROCE
            "capital_expenditure_to_revenue",  # 15 - CAPEX/Revenue
            "current_ratio",  # 16 - Current Ratio
            "market_cap_basic",  # 17 - Market Cap
            "enterprise_value",  # 18 - EV
            "total_revenue",  # 19 - Revenue
            "net_income",  # 20 - Net Income
            "ebitda",  # 21 - EBITDA
            "ebit",  # 22 - EBIT
            "free_cash_flow",  # 23 - FCF
            "capital_expenditure",  # 24 - CAPEX
            "total_debt",  # 25 - Total Debt
            "cash_and_equivalents",  # 26 - Cash
        ]
    }

    headers = {'Content-Type': 'application/json'}

    try:
        r = requests.post(url, json=body, headers=headers, timeout=15)
        data = r.json()

        if 'data' not in data or not data['data']:
            print("TradingView: нет данных")
            return

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")

        for item in data['data']:
            ticker = item['s'].replace('RUS:', '')
            values = item['d']

            if not values or all(v is None for v in values):
                continue

            # Выводим что загрузилось
            loaded = []
            if values[13]: loaded.append(f"ROIC={values[13]}")
            if values[14]: loaded.append(f"ROCE={values[14]}")
            if values[23]: loaded.append(f"FCF={values[23]}")
            if values[24]: loaded.append(f"CAPEX={values[24]}")
            if values[22]: loaded.append(f"EBIT={values[22]}")
            print(f"  TV {ticker}: {', '.join(loaded) if loaded else 'ничего нового'}")

            # Обновляем ВСЕ поля
            update_fields = {
                'pe': values[0], 'pb': values[1], 'ps': values[2],
                'evebitda': values[3], 'roe': values[4], 'roa': values[5],
                'net_margin': values[6], 'operating_margin': values[8],
                'de': values[9], 'pfcf': values[10], 'pcf': values[11],
                'evebit': values[12], 'roic': values[13], 'roce': values[14],
                'capex_revenue': values[15], 'current_ratio': values[16],
                'market_cap': values[17], 'ev': values[18],
                'revenue': values[19], 'net_income': values[20],
                'ebitda': values[21], 'ebit': values[22],
                'fcf': values[23], 'capex': values[24],
                'total_debt': values[25], 'cash_equivalents': values[26],
            }

            # Оставляем только не-None значения
            update_fields = {k: v for k, v in update_fields.items() if v is not None}

            if update_fields:
                set_clause = ', '.join([f"{k} = COALESCE({k}, %s)" for k in update_fields.keys()])
                vals = list(update_fields.values()) + [ticker]
                cursor.execute(f"UPDATE stock_fundamentals SET {set_clause}, updated_at = CURDATE() WHERE ticker = %s",
                               vals)

        conn.commit()
        conn.close()
        print("TradingView: обновление завершено")

    except Exception as e:
        print(f"TradingView: ошибка — {e}")


def calculate_missing_fundamentals():
    """Рассчитывает недостающие мультипликаторы"""
    from DB.db_config import create_connection

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    cursor.execute("""
        SELECT ticker, market_cap, ev, revenue, net_income, ebitda, ebit, fcf, capex,
               total_debt, cash_equivalents, pe, pb, ps, evebitda, evebit, de, debt_ebitda
        FROM stock_fundamentals
    """)
    rows = cursor.fetchall()

    for row in rows:
        ticker = row[0]
        d = dict(zip(['market_cap', 'ev', 'revenue', 'net_income', 'ebitda', 'ebit', 'fcf', 'capex',
                      'total_debt', 'cash', 'pe', 'pb', 'ps', 'evebitda', 'evebit', 'de', 'debt_ebitda'], row[1:]))

        updates = {}

        # EBIT из EBITDA (если нет) — примерно 80% от EBITDA
        if not d['ebit'] and d['ebitda']:
            updates['ebit'] = float(d['ebitda']) * 0.8

        # Общий долг из Долг/EBITDA × EBITDA
        if not d['total_debt'] and d['debt_ebitda'] and d['ebitda']:
            updates['total_debt'] = float(d['debt_ebitda']) * float(d['ebitda'])

        # Чистый долг
        if d['total_debt']:
            net_debt = float(d['total_debt']) - (float(d['cash']) if d['cash'] else 0)
            if d['ebitda'] and float(d['ebitda']) > 0:
                updates['net_debt_ebitda'] = net_debt / float(d['ebitda'])

        # EV/S
        if d['ev'] and d['revenue'] and float(d['revenue']) > 0:
            updates['ev_s'] = float(d['ev']) / float(d['revenue'])

        # D/E
        if d['total_debt'] and d['market_cap'] and d['pb'] and float(d['pb']) > 0:
            equity = float(d['market_cap']) / float(d['pb'])
            if equity > 0:
                updates['de'] = float(d['total_debt']) / equity

        # ROE из P/B и P/E
        if not d.get('roe') and d['pb'] and d['pe'] and float(d['pe']) > 0:
            updates['roe'] = (float(d['pb']) / float(d['pe'])) * 100

        # Чистая маржа
        if d['net_income'] and d['revenue'] and float(d['revenue']) > 0:
            updates['net_margin'] = (float(d['net_income']) / float(d['revenue'])) * 100

        if updates:
            set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
            values = list(updates.values()) + [ticker]
            cursor.execute(f"UPDATE stock_fundamentals SET {set_clause}, updated_at = CURDATE() WHERE ticker = %s",
                           values)

    conn.commit()
    conn.close()
    print("Расчёт недостающих мультипликаторов завершён")

def update_all_fundamentals(tickers):
    """Обновляет фундаментальные показатели для списка тикеров"""
    from DB.db_config import create_connection

    conn = create_connection()
    if not conn:
        return

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    for ticker in tickers:
        print(f"Загрузка {ticker}...")
        data = get_fundamentals(ticker)
        # В конце update_all_fundamentals добавить:
        print("\nДозагрузка с TradingView...")
        get_tradingview_fundamentals(tickers)
        print("\nРасчёт недостающих мультипликаторов...")
        calculate_missing_fundamentals()
        if data:
            try:
                cursor.execute("""
                    INSERT INTO stock_fundamentals 
                    (ticker, market_cap, ev, revenue, net_income, ebitda, ebit, fcf, capex,
                     total_debt, cash_equivalents, pe, pb, ps, pcf, pfcf, ev_s, evebitda, evebit,
                     de, debt_ebitda, net_debt_ebitda, capex_revenue,
                     roe, roa, roic, roce, net_margin, operating_margin, ebitda_margin,
                     current_ratio, report_date, company_type, net_operating_income, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURDATE())
                    ON DUPLICATE KEY UPDATE
                        market_cap=VALUES(market_cap), ev=VALUES(ev), revenue=VALUES(revenue),
                        net_income=VALUES(net_income), ebitda=VALUES(ebitda),
                        pe=VALUES(pe), pb=VALUES(pb), ps=VALUES(ps),
                        evebitda=VALUES(evebitda), ev_s=VALUES(ev_s),
                        debt_ebitda=VALUES(debt_ebitda), net_debt_ebitda=VALUES(net_debt_ebitda),
                        roe=VALUES(roe), roa=VALUES(roa), net_margin=VALUES(net_margin),
                        ebitda_margin=VALUES(ebitda_margin),
                        report_date=VALUES(report_date), company_type=VALUES(company_type),
                        net_operating_income=VALUES(net_operating_income), updated_at=CURDATE()
                """, (
                    data['ticker'], data['market_cap'], data['ev'], data['revenue'],
                    data['net_income'], data['ebitda'], data['ebit'], data['fcf'], data['capex'],
                    data['total_debt'], data['cash_equivalents'],
                    data['pe'], data['pb'], data['ps'], data['pcf'], data['pfcf'],
                    data['ev_s'], data['evebitda'], data['evebit'],
                    data['de'], data['debt_ebitda'], data['net_debt_ebitda'], data['capex_revenue'],
                    data['roe'], data['roa'], data['roic'], data['roce'],
                    data['net_margin'], data['operating_margin'], data['ebitda_margin'],
                    data['current_ratio'], data['report_date'], data['company_type'],
                    data['net_operating_income']
                ))
            except Exception as e:
                print(f"  Ошибка сохранения {ticker}: {e}")

    conn.commit()
    conn.close()
    print("Обновление завершено!")