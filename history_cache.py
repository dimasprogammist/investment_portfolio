# history_cache.py - работа с кэшем исторических цен
from db_config import create_connection
from history import get_historical_prices
from datetime import datetime, timedelta
import pandas as pd
import requests
from config import STOCKS, BONDS

# Попробуем импортировать CURRENCY_BONDS_CONFIG
try:
    from config import CURRENCY_BONDS_CONFIG
except ImportError:
    CURRENCY_BONDS_CONFIG = {}

# Тикер для бенчмарка (Индекс МосБиржи полной доходности)
INDEX_TICKER = 'MCFTR'


def save_prices_to_cache(ticker, security_type, prices_df):
    """Сохраняет исторические цены в кэш БД"""
    if prices_df is None or prices_df.empty:
        return 0

    conn = create_connection()
    if not conn:
        return 0

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    saved = 0
    for _, row in prices_df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO historical_prices (date, ticker, price, security_type)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE price = VALUES(price)
            """, (row['date'], ticker, float(row['close']), security_type))
            saved += 1
        except Exception as e:
            print(f"Ошибка сохранения {ticker} на {row['date']}: {e}")

    conn.commit()
    conn.close()
    print(f"Сохранено {saved} записей для {ticker}")
    return saved


def get_prices_from_cache(ticker, start_date, end_date):
    """Получает цены из кэша БД для любого тикера (включая ETF)"""
    conn = create_connection()
    if not conn:
        return None

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    cursor.execute("""
        SELECT date, price 
        FROM historical_prices 
        WHERE ticker = %s AND date BETWEEN %s AND %s
        ORDER BY date
    """, (ticker, start_date, end_date))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=['date', 'close'])
    df['date'] = pd.to_datetime(df['date'])
    return df


def ensure_prices_cached(ticker, security_type, start_date, end_date, force_refresh=False):
    """Проверяет наличие АКТУАЛЬНЫХ данных в кэше, загружает недостающие"""
    conn = create_connection()
    if not conn:
        return

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    # Проверяем максимальную дату в кэше для этого тикера
    cursor.execute("""
        SELECT MAX(date), COUNT(*) FROM historical_prices 
        WHERE ticker = %s AND date BETWEEN %s AND %s
    """, (ticker, start_date, end_date))

    last_date, count = cursor.fetchone()
    conn.close()

    # Если force_refresh, данных нет вообще, или последняя дата старше чем нужно
    need_refresh = force_refresh or count == 0

    if last_date:
        # Если последняя дата в кэше отстаёт больше чем на 3 дня от end_date
        days_behind = (end_date - last_date).days if end_date else 365
        if days_behind > 3:
            need_refresh = True
            print(f"{ticker}: данные отстают на {days_behind} дней, обновляем")
    else:
        need_refresh = True

    if need_refresh:
        print(f"Загрузка {ticker} с {start_date} по {end_date}...")
        prices = get_historical_prices(ticker, start_date, end_date, security_type)
        if prices is not None and not prices.empty:
            save_prices_to_cache(ticker, security_type, prices)
    else:
        print(f"{ticker}: данные актуальны (последняя дата: {last_date})")


def fetch_index_history(ticker, start_date, end_date):
    """Загружает историю индекса с MOEX через history-эндпоинт с пагинацией"""
    if isinstance(start_date, datetime):
        start_date = start_date.strftime('%Y-%m-%d')
    if isinstance(end_date, datetime):
        end_date = end_date.strftime('%Y-%m-%d')

    all_data = []
    start = 0
    page_size = 100

    while True:
        url = f"https://iss.moex.com/iss/history/engines/stock/markets/index/securities/{ticker}.json"
        params = {
            'from': start_date,
            'till': end_date,
            'start': start,
            'limit': page_size,
            'iss.meta': 'off',
            'iss.only': 'history',
            'history.columns': 'TRADEDATE,CLOSE'
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if 'history' not in data or not data['history']['data']:
                break

            candles = data['history']['data']
            columns = data['history']['columns']

            df_page = pd.DataFrame(candles, columns=columns)
            all_data.append(df_page)

            if len(candles) < page_size:
                break

            start += page_size
        except Exception as e:
            print(f"Ошибка получения истории {ticker} (страница {start}): {e}")
            break

    if not all_data:
        print(f"Нет исторических данных {ticker} за период {start_date} - {end_date}")
        return None

    df = pd.concat(all_data, ignore_index=True)
    df['date'] = pd.to_datetime(df['TRADEDATE']).dt.date
    df['close'] = pd.to_numeric(df['CLOSE'], errors='coerce')
    df = df[['date', 'close']].dropna().sort_values('date')

    print(f"Загружено {len(df)} записей для {ticker}")
    return df


def ensure_index_cached(ticker, start_date, end_date, force_refresh=False):
    """Гарантирует наличие кэша для индекса (использует специальную функцию загрузки)"""
    conn = create_connection()
    if not conn:
        return

    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    cursor.execute("""
        SELECT COUNT(*) FROM historical_prices 
        WHERE ticker = %s AND date BETWEEN %s AND %s
    """, (ticker, start_date, end_date))
    count = cursor.fetchone()[0]
    conn.close()

    if force_refresh or count == 0:
        print(f"Загрузка индекса {ticker} с {start_date} по {end_date}...")
        prices = fetch_index_history(ticker, start_date, end_date)
        if prices is not None and not prices.empty:
            save_prices_to_cache(ticker, 'index', prices)


def init_historical_cache(start_date=None):
    """Инициализация кэша исторических данных для всех активов и индекса"""
    if start_date is None:
        start_date = datetime(2023, 6, 30).date()
    else:
        if isinstance(start_date, datetime):
            start_date = start_date.date()

    end_date = datetime.now().date()

    all_tickers = STOCKS + BONDS + [INDEX_TICKER]
    total = len(all_tickers)

    print(f"Инициализация кэша исторических цен для {total} активов...")
    print(f"Период: {start_date} - {end_date}")

    for i, ticker in enumerate(all_tickers, 1):
        if ticker == INDEX_TICKER:
            print(f"[{i}/{total}] Обработка индекса {ticker}...")
            ensure_index_cached(ticker, start_date, end_date, force_refresh=True)
        else:
            security_type = 'stock' if ticker in STOCKS else 'bond'
            print(f"[{i}/{total}] Обработка {ticker} ({security_type})...")
            ensure_prices_cached(ticker, security_type, start_date, end_date, force_refresh=True)

    print("Инициализация кэша завершена!")


def get_portfolio_history_cached(start_date, end_date, user_id: int = 1):
    """Рассчитывает историю портфеля пользователя, используя кэшированные цены."""
    from db_config import create_connection
    import pandas as pd
    from datetime import datetime
    from prices import get_usd_rate

    print(f"Расчёт истории портфеля через кэш с {start_date} по {end_date}")

    if isinstance(start_date, datetime):
        start_date = start_date.date()
    if isinstance(end_date, datetime):
        end_date = end_date.date()

    conn = create_connection()
    if not conn:
        print("Ошибка подключения к БД")
        return None

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    operations = []

    cursor.execute("SELECT date, amount FROM deposits WHERE user_id = %s", (user_id,))
    for row in cursor.fetchall():
        operations.append({'date': row[0], 'ticker': None, 'type': 'deposit',
                           'quantity': 0, 'amount': float(row[1])})

    cursor.execute("SELECT date, amount FROM tax_deductions WHERE user_id = %s", (user_id,))
    for row in cursor.fetchall():
        operations.append({'date': row[0], 'ticker': None, 'type': 'tax_refund',
                           'quantity': 0, 'amount': float(row[1])})

    cursor.execute("SELECT date, amount FROM tax_refunds WHERE user_id = %s", (user_id,))
    for row in cursor.fetchall():
        operations.append({'date': row[0], 'ticker': None, 'type': 'tax_refund',
                           'quantity': 0, 'amount': float(row[1])})

    cursor.execute("SELECT date, amount FROM taxes WHERE user_id = %s", (user_id,))
    for row in cursor.fetchall():
        operations.append({'date': row[0], 'ticker': None, 'type': 'tax',
                           'quantity': 0, 'amount': -float(row[1])})

    cursor.execute(
        "SELECT date, ticker, quantity, total_amount, operation FROM stock_trades WHERE user_id = %s",
        (user_id,),
    )
    for row in cursor.fetchall():
        qty = float(row[2]) if row[4] == 'buy' else -float(row[2])
        amount = float(row[3]) if row[4] == 'buy' else -float(row[3])
        operations.append({'date': row[0], 'ticker': row[1], 'type': row[4],
                           'quantity': qty, 'amount': amount})

    cursor.execute(
        "SELECT date, ticker, quantity, total_amount, operation FROM bond_trades WHERE user_id = %s",
        (user_id,),
    )
    for row in cursor.fetchall():
        qty = float(row[2]) if row[4] == 'buy' else -float(row[2])
        amount = float(row[3]) if row[4] == 'buy' else -float(row[3])
        operations.append({'date': row[0], 'ticker': row[1], 'type': row[4],
                           'quantity': qty, 'amount': amount})

    cursor.execute(
        "SELECT date, ticker, quantity, total_amount FROM bond_redemptions WHERE user_id = %s",
        (user_id,),
    )
    for row in cursor.fetchall():
        operations.append({'date': row[0], 'ticker': row[1], 'type': 'redemption',
                           'quantity': -float(row[2]), 'amount': float(row[3])})

    cursor.execute("SELECT date, ticker, amount FROM dividends WHERE user_id = %s", (user_id,))
    for row in cursor.fetchall():
        operations.append({'date': row[0], 'ticker': row[1], 'type': 'dividend',
                           'quantity': 0, 'amount': float(row[2])})

    cursor.execute("SELECT date, ticker, amount FROM coupons WHERE user_id = %s", (user_id,))
    for row in cursor.fetchall():
        operations.append({'date': row[0], 'ticker': row[1], 'type': 'coupon',
                           'quantity': 0, 'amount': float(row[2])})

    if not operations:
        print("Нет операций для расчёта!")
        conn.close()
        return None

    operations.sort(key=lambda x: x['date'])
    first_op_date = operations[0]['date']

    if start_date < first_op_date:
        start_date = first_op_date

    tickers_in_ops = set(op['ticker'] for op in operations if op['ticker'])

    usd_rate = get_usd_rate()

    prices_cache = {}
    for ticker in tickers_in_ops:
        cursor.execute("""
            SELECT date, price 
            FROM historical_prices 
            WHERE ticker = %s AND date <= %s
            ORDER BY date
        """, (ticker, end_date))

        rows = cursor.fetchall()
        if rows:
            data = []
            for row in rows:
                price = float(row[1])

                if ticker in BONDS:
                    if ticker in CURRENCY_BONDS_CONFIG:
                        config = CURRENCY_BONDS_CONFIG[ticker]
                        nominal_in_rub = config['nominal'] * usd_rate
                        price = price * nominal_in_rub / 100
                    else:
                        price = price * 1000 / 100

                data.append({'date': row[0], 'price': price})

            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            prices_cache[ticker] = df.set_index('date')['price']

    conn.close()

    date_range = pd.date_range(start=start_date, end=end_date, freq='D')

    portfolio_values = []
    current_positions = {}
    cash = 0
    last_op_idx = 0

    print(f"Расчёт значений для {len(date_range)} дней...")

    for i, date in enumerate(date_range):
        date_obj = date.date()

        while last_op_idx < len(operations) and operations[last_op_idx]['date'] <= date_obj:
            op = operations[last_op_idx]

            if op['type'] == 'buy':
                current_positions[op['ticker']] = current_positions.get(op['ticker'], 0) + op['quantity']
                cash -= op['amount']
            elif op['type'] == 'sell':
                current_positions[op['ticker']] = current_positions.get(op['ticker'], 0) + op['quantity']
                cash -= op['amount']
            elif op['type'] == 'redemption':
                current_positions[op['ticker']] = current_positions.get(op['ticker'], 0) + op['quantity']
                cash += op['amount']
            elif op['type'] == 'deposit':
                cash += op['amount']
            elif op['type'] == 'tax_refund':
                cash += op['amount']
            elif op['type'] == 'tax':
                cash += op['amount']
            elif op['type'] in ['dividend', 'coupon']:
                cash += op['amount']

            last_op_idx += 1

        total_value = cash

        for ticker, qty in current_positions.items():
            if qty > 0 and ticker in prices_cache:
                try:
                    price_series = prices_cache[ticker]
                    price_on_date = price_series[price_series.index <= date]
                    if not price_on_date.empty:
                        price = price_on_date.iloc[-1]
                        total_value += qty * price
                except:
                    pass

        portfolio_values.append({'date': date, 'value': total_value, 'cash': cash})

        if len(date_range) > 10 and i % (len(date_range) // 10) == 0:
            progress = int(i / len(date_range) * 100)
            print(f"  Прогресс: {progress}%")

    print(f"Расчёт завершён. Получено {len(portfolio_values)} записей")
    return pd.DataFrame(portfolio_values)