from DB.db_config import create_connection
from typing import Any


def get_portfolio_stats(user_id: int = 1) -> dict[str, Any]:
    """Получение статистики портфеля для конкретного пользователя."""
    conn = create_connection()
    if not conn:
        return {}

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    # Покупки акций - получаем уже готовый total_amount из БД
    cursor.execute(
        'SELECT ticker, quantity, total_amount FROM stock_trades WHERE user_id = %s AND operation = "buy"',
        (user_id,),
    )
    stock_buys = cursor.fetchall()

    cursor.execute(
        'SELECT ticker, quantity FROM stock_trades WHERE user_id = %s AND operation = "sell"',
        (user_id,),
    )
    stock_sells = cursor.fetchall()

    stock_positions = {}
    for ticker, qty, total_amount in stock_buys:
        if ticker not in stock_positions:
            stock_positions[ticker] = {'qty': 0, 'total_cost': 0}
        stock_positions[ticker]['qty'] += float(qty)
        stock_positions[ticker]['total_cost'] += float(total_amount)  # Используем total_amount из БД

    for ticker, qty in stock_sells:
        if ticker in stock_positions:
            stock_positions[ticker]['qty'] -= float(qty)

    # Покупки облигаций - тоже используем total_amount
    cursor.execute(
        'SELECT ticker, quantity, total_amount FROM bond_trades WHERE user_id = %s AND operation = "buy"',
        (user_id,),
    )
    bond_buys = cursor.fetchall()

    cursor.execute(
        'SELECT ticker, quantity FROM bond_trades WHERE user_id = %s AND operation = "sell"',
        (user_id,),
    )
    bond_sells = cursor.fetchall()

    cursor.execute(
        "SELECT ticker, quantity, price FROM bond_redemptions WHERE user_id = %s",
        (user_id,),
    )
    bond_redemptions = cursor.fetchall()

    bond_positions = {}
    for ticker, qty, total_amount in bond_buys:
        if ticker not in bond_positions:
            bond_positions[ticker] = {'qty': 0, 'total_cost': 0}
        bond_positions[ticker]['qty'] += float(qty)
        bond_positions[ticker]['total_cost'] += float(total_amount)  # Используем total_amount из БД

    for ticker, qty in bond_sells:
        if ticker in bond_positions:
            bond_positions[ticker]['qty'] -= float(qty)

    for ticker, qty, price in bond_redemptions:
        if ticker in bond_positions:
            bond_positions[ticker]['qty'] -= float(qty)

    # Общая статистика
    cursor.execute("SELECT SUM(amount) FROM deposits WHERE user_id = %s", (user_id,))
    total_deposits = float(cursor.fetchone()[0] or 0)

    cursor.execute("SELECT SUM(amount) FROM dividends WHERE user_id = %s", (user_id,))
    total_dividends = float(cursor.fetchone()[0] or 0)

    cursor.execute("SELECT SUM(amount) FROM coupons WHERE user_id = %s", (user_id,))
    total_coupons = float(cursor.fetchone()[0] or 0)

    cursor.execute("SELECT SUM(amount) FROM taxes WHERE user_id = %s", (user_id,))
    total_taxes = float(cursor.fetchone()[0] or 0)

    cursor.execute(
        "SELECT SUM(quantity * price) FROM bond_redemptions WHERE user_id = %s",
        (user_id,),
    )
    total_redemptions = float(cursor.fetchone()[0] or 0)

    conn.close()

    return {
        'stock_positions': stock_positions,
        'bond_positions': bond_positions,
        'total_deposits': total_deposits,
        'total_dividends': total_dividends,
        'total_coupons': total_coupons,
        'total_taxes': total_taxes,
        'total_redemptions': total_redemptions,
    }


def save_deposit(date, amount, user_id: int = 1):
    """Сохранение пополнения пользователя."""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute(
            "INSERT INTO deposits (user_id, date, amount) VALUES (%s, %s, %s)",
            (user_id, date, amount),
        )
        conn.commit()
        conn.close()
        return True
    return False

def save_tax_refund(date, amount, description="", user_id: int = 1):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute(
            "INSERT INTO tax_refunds (user_id, date, amount, description) VALUES (%s, %s, %s, %s)",
            (user_id, date, amount, description),
        )
        conn.commit()
        conn.close()
        return True
    return False

def get_tax_refunds(user_id: int = 1):
    conn = create_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    cursor.execute(
        "SELECT date, amount, description FROM tax_refunds WHERE user_id = %s ORDER BY date DESC",
        (user_id,),
    )
    result = cursor.fetchall()
    conn.close()
    return result

def save_trade(sec_type, operation, ticker, date, quantity, price, total, user_id: int = 1):
    """Сохранение сделки (price должен быть в рублях для облигаций)"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        tables = {"stock": "stock_trades", "bond": "bond_trades"}
        table = tables.get(sec_type)
        if table is None:
            conn.close()
            raise ValueError(f"Неизвестный тип инструмента: {sec_type!r}")
        cursor.execute(
            f"""
            INSERT INTO {table} (user_id, date, ticker, operation, quantity, price, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, date, ticker, operation, quantity, price, total),
        )
        conn.commit()
        conn.close()
        return True
    return False


def save_income(income_type, ticker, date, quantity, amount, avg_price=None, user_id: int = 1):
    """Сохранение дивидендов или купонов с количеством бумаг и средней ценой"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        tables = {"dividend": "dividends", "coupon": "coupons"}
        table = tables.get(income_type)
        if table is None:
            conn.close()
            raise ValueError(f"Неизвестный тип дохода: {income_type!r}")

        if income_type == 'dividend' and avg_price is not None:
            cursor.execute(f"""
                INSERT INTO {table} (user_id, date, ticker, quantity, amount, avg_price) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, date, ticker, quantity, amount, avg_price))
        else:
            cursor.execute(f"""
                INSERT INTO {table} (user_id, date, ticker, quantity, amount) 
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, date, ticker, quantity, amount))

        conn.commit()
        conn.close()
        return True
    return False


def save_redemption(ticker, date, quantity, price, total, user_id: int = 1):
    """Сохранение погашения облигации"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute("""
            INSERT INTO bond_redemptions (user_id, date, ticker, quantity, price, total_amount) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, date, ticker, quantity, price, total))
        conn.commit()
        conn.close()
        return True
    return False


def get_deposits(user_id: int = 1):
    """Получение всех пополнений"""
    conn = create_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    cursor.execute('SELECT date, amount FROM deposits WHERE user_id = %s ORDER BY date DESC', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result


def get_dividends(user_id: int = 1):
    """Получение всех дивидендов"""
    conn = create_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    cursor.execute('SELECT date, ticker, amount FROM dividends WHERE user_id = %s ORDER BY date DESC', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result


def get_coupons(user_id: int = 1):
    """Получение всех купонов"""
    conn = create_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    cursor.execute('SELECT date, ticker, amount FROM coupons WHERE user_id = %s ORDER BY date DESC', (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result


def get_portfolio_history(start_date, end_date, user_id: int = 1):
    """Рассчитывает стоимость портфеля на каждый день используя кэш"""
    from history_cache import get_portfolio_history_cached
    return get_portfolio_history_cached(start_date, end_date, user_id=user_id)

def save_deposit_account(name, account_type, current_amount, interest_rate=None, maturity_date=None, notes=None, user_id: int = 1):
    """Сохранение нового вклада/счета"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute("""
            INSERT INTO deposits_accounts (user_id, name, type, current_amount, interest_rate, maturity_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, name, account_type, current_amount, interest_rate, maturity_date, notes))
        conn.commit()
        conn.close()
        return True
    return False


def update_deposit_account(account_id, current_amount, user_id: int = 1):
    """Обновление суммы на счете"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute(
            "UPDATE deposits_accounts SET current_amount = %s WHERE id = %s AND user_id = %s",
            (current_amount, account_id, user_id),
        )
        conn.commit()
        conn.close()
        return True
    return False


def get_deposit_accounts(user_id: int = 1):
    """Получение всех вкладов"""
    conn = create_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    cursor.execute("""
        SELECT id, name, type, current_amount, interest_rate, maturity_date, notes 
        FROM deposits_accounts
        WHERE user_id = %s
        ORDER BY id
    """, (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result


def save_deposit_payment(account_id, date, amount, user_id: int = 1):
    """Сохранение выплаты по вкладу"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute("""
            INSERT INTO deposit_payments (user_id, account_id, date, amount)
            VALUES (%s, %s, %s, %s)
        """, (user_id, account_id, date, amount))
        conn.commit()
        conn.close()
        return True
    return False


def get_deposit_payments(user_id: int = 1):
    """Получение всех выплат по вкладам с названиями счетов"""
    conn = create_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    cursor.execute("""
        SELECT a.name, p.date, p.amount 
        FROM deposit_payments p
        JOIN deposits_accounts a ON p.account_id = a.id
        WHERE p.user_id = %s AND a.user_id = %s
        ORDER BY p.date DESC
    """, (user_id, user_id))
    result = cursor.fetchall()
    conn.close()
    return result


def delete_deposit_account(account_id, user_id: int = 1):
    """Удаление вклада"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute("DELETE FROM deposits_accounts WHERE id = %s AND user_id = %s", (account_id, user_id))
        conn.commit()
        conn.close()
        return True
    return False


def save_tax_deduction(date, amount, deduction_type, description='', year=None, user_id: int = 1):
    """Сохранение налогового вычета"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute("""
            INSERT INTO tax_deductions (user_id, date, amount, type, description, year)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, date, amount, deduction_type, description, year))
        conn.commit()
        conn.close()
        return True
    return False


def get_tax_deductions(user_id: int = 1):
    """Получение всех налоговых вычетов"""
    conn = create_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")
    cursor.execute("""
        SELECT id, date, amount, type, description, year 
        FROM tax_deductions 
        WHERE user_id = %s
        ORDER BY date DESC
    """, (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result


def delete_tax_deduction(deduction_id, user_id: int = 1):
    """Удаление налогового вычета"""
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute("DELETE FROM tax_deductions WHERE id = %s AND user_id = %s", (deduction_id, user_id))
        conn.commit()
        conn.close()
        return True
    return False


def get_tax_deductions_stats(user_id: int = 1):
    """Статистика по налоговым вычетам"""
    conn = create_connection()
    if not conn:
        return {}

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    # Общая сумма
    cursor.execute("SELECT SUM(amount) FROM tax_deductions WHERE user_id = %s", (user_id,))
    total = float(cursor.fetchone()[0] or 0)

    # По типам
    cursor.execute("""
        SELECT type, SUM(amount) 
        FROM tax_deductions 
        WHERE user_id = %s
        GROUP BY type
    """, (user_id,))
    by_type = {row[0]: float(row[1]) for row in cursor.fetchall()}

    # По годам
    cursor.execute("""
        SELECT year, SUM(amount) 
        FROM tax_deductions 
        WHERE user_id = %s AND year IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
    """, (user_id,))
    by_year = {row[0]: float(row[1]) for row in cursor.fetchall()}

    conn.close()

    return {
        'total': total,
        'by_type': by_type,
        'by_year': by_year
    }