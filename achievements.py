from datetime import datetime


class Achievement:
    def __init__(self, name, icon, tiers):
        self.name = name
        self.icon = icon
        self.tiers = tiers

    def get_progress(self, value):
        current_tier_idx = -1
        for i, (threshold, _) in enumerate(self.tiers):
            if value >= threshold:
                current_tier_idx = i

        if current_tier_idx < len(self.tiers) - 1:
            next_tier_idx = current_tier_idx + 1
            next_threshold = self.tiers[next_tier_idx][0]
            next_label = self.tiers[next_tier_idx][1]
            progress = min(100, int(value / next_threshold * 100))
            completed_all = False
        else:
            next_threshold = self.tiers[-1][0]
            next_label = self.tiers[-1][1]
            progress = 100
            completed_all = True

        return {
            'value': value,
            'progress': progress,
            'next_threshold': next_threshold,
            'next_label': next_label,
            'completed_all': completed_all,
            'tiers_count': len(self.tiers),
            'achieved_tiers': current_tier_idx + 1,
        }


# === ДОСТИЖЕНИЯ ЗА ВСЁ ВРЕМЯ ===
PORTFOLIO_VALUE = Achievement("Стоимость портфеля", "💰", [
    (100000, "100 тыс. ₽"), (500000, "500 тыс. ₽"), (1000000, "1 млн ₽"),
    (1500000, "1.5 млн ₽"), (2000000, "2 млн ₽"), (2500000, "2.5 млн ₽"),
    (3000000, "3 млн ₽"), (3500000, "3.5 млн ₽"), (4000000, "4 млн ₽"),
    (5000000, "5 млн ₽"), (6000000, "6 млн ₽"), (7000000, "7 млн ₽"),
    (8000000, "8 млн ₽"), (9000000, "9 млн ₽"), (10000000, "10 млн ₽"),
    (12500000, "12.5 млн ₽"), (15000000, "15 млн ₽"),
])

COUPONS_COUNT = Achievement("Количество купонов", "🎫", [
    (50, "50"), (100, "100"), (200, "200"), (300, "300"),
    (400, "400"), (500, "500"), (750, "750"), (1000, "1000"),
])

COUPONS_SUM = Achievement("Сумма купонов", "💵", [
    (10000, "10 тыс. ₽"), (20000, "20 тыс. ₽"), (30000, "30 тыс. ₽"),
    (40000, "40 тыс. ₽"), (50000, "50 тыс. ₽"), (75000, "75 тыс. ₽"),
    (100000, "100 тыс. ₽"), (150000, "150 тыс. ₽"), (200000, "200 тыс. ₽"),
    (250000, "250 тыс. ₽"),
])

DIVIDENDS_COUNT = Achievement("Количество дивидендов", "📊", [
    (20, "20"), (50, "50"), (75, "75"), (100, "100"),
    (150, "150"), (200, "200"),
])

DIVIDENDS_SUM = Achievement("Сумма дивидендов", "💎", [
    (50000, "50 тыс. ₽"), (100000, "100 тыс. ₽"), (200000, "200 тыс. ₽"),
    (300000, "300 тыс. ₽"), (400000, "400 тыс. ₽"), (500000, "500 тыс. ₽"),
    (750000, "750 тыс. ₽"), (1000000, "1 млн ₽"), (1500000, "1.5 млн ₽"),
])

TOTAL_INCOME = Achievement("Общий доход", "💸", [
    (100000, "100 тыс. ₽"), (250000, "250 тыс. ₽"), (500000, "500 тыс. ₽"),
    (750000, "750 тыс. ₽"), (1000000, "1 млн ₽"), (1500000, "1.5 млн ₽"),
    (2000000, "2 млн ₽"), (3000000, "3 млн ₽"),
])

TOTAL_DEPOSITS = Achievement("Всего пополнено", "🏦", [
    (500000, "500 тыс. ₽"), (1000000, "1 млн ₽"), (1500000, "1.5 млн ₽"),
    (2000000, "2 млн ₽"), (3000000, "3 млн ₽"), (5000000, "5 млн ₽"),
])

PROFIT_ALL_TIME = Achievement("Чистая прибыль", "📈", [
    (50000, "50 тыс. ₽"), (100000, "100 тыс. ₽"), (250000, "250 тыс. ₽"),
    (500000, "500 тыс. ₽"), (750000, "750 тыс. ₽"), (1000000, "1 млн ₽"),
    (2000000, "2 млн ₽"),
])

TRADES_COUNT = Achievement("Количество сделок", "🔄", [
    (50, "50"), (100, "100"), (200, "200"), (300, "300"),
    (500, "500"), (750, "750"), (1000, "1000"),
])

DIVIDEND_MONTHS = Achievement("Месяцы с дивидендами", "📅", [
    (3, "3"), (6, "6"), (9, "9"), (12, "12"), (18, "18"), (24, "24"),
])

# === ЕЖЕГОДНЫЕ ===
YEAR_DIV_GROWTH = Achievement("Рост див.+куп. к прошлому году", "🚀", [
    (0.5, "50%"), (1.0, "100%"), (1.5, "150%"), (2.0, "200%"),
])

YEAR_DEPOSITS = Achievement("Пополнения за год", "📥", [
    (400000, "400 тыс. ₽"), (500000, "500 тыс. ₽"), (600000, "600 тыс. ₽"),
    (750000, "750 тыс. ₽"), (1000000, "1 млн ₽"),
])

YEAR_INFLOW = Achievement("Общий приток за год", "🌊", [
    (500000, "500 тыс. ₽"), (750000, "750 тыс. ₽"), (1000000, "1 млн ₽"),
    (1500000, "1.5 млн ₽"),
])

YEAR_DIVIDENDS = Achievement("Дивиденды за год", "💎", [
    (50000, "50 тыс. ₽"), (100000, "100 тыс. ₽"), (200000, "200 тыс. ₽"),
    (300000, "300 тыс. ₽"),
])

YEAR_COUPONS = Achievement("Купоны за год", "🎫", [
    (20000, "20 тыс. ₽"), (50000, "50 тыс. ₽"), (100000, "100 тыс. ₽"),
])


def get_all_achievements_with_progress(user_id):
    """Возвращает ВСЕ достижения с текущим прогрессом"""
    from DB.db_config import create_connection
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    current_year = datetime.now().year

    # Базовая стоимость портфеля
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) FROM (
            SELECT total_amount FROM stock_trades WHERE user_id=%s AND operation='buy'
            UNION ALL
            SELECT total_amount FROM bond_trades WHERE user_id=%s AND operation='buy'
        ) t
    """, (user_id, user_id))
    portfolio_value = float(cursor.fetchone()[0])

    # Купоны
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM coupons WHERE user_id=%s", (user_id,))
    r = cursor.fetchone()
    coupons_count, coupons_sum = int(r[0]), float(r[1])

    # Дивиденды
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM dividends WHERE user_id=%s", (user_id,))
    r = cursor.fetchone()
    div_count, div_sum = int(r[0]), float(r[1])

    # Общий доход
    total_income = coupons_sum + div_sum

    # Всего пополнено
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM deposits WHERE user_id=%s", (user_id,))
    total_deposits = float(cursor.fetchone()[0])

    # Чистая прибыль (стоимость - затраты + доход)
    cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM stock_trades WHERE user_id=%s AND operation='buy'", (user_id,))
    stock_cost = float(cursor.fetchone()[0])
    cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM bond_trades WHERE user_id=%s AND operation='buy'", (user_id,))
    bond_cost = float(cursor.fetchone()[0])
    total_cost = stock_cost + bond_cost
    profit = portfolio_value - total_cost + total_income

    # Количество сделок
    cursor.execute("SELECT (SELECT COUNT(*) FROM stock_trades WHERE user_id=%s) + (SELECT COUNT(*) FROM bond_trades WHERE user_id=%s)", (user_id, user_id))
    trades_count = int(cursor.fetchone()[0])

    # Месяцы с дивидендами
    cursor.execute("SELECT COUNT(DISTINCT CONCAT(YEAR(date), '-', MONTH(date))) FROM dividends WHERE user_id=%s", (user_id,))
    div_months = int(cursor.fetchone()[0])

    # Ежегодные данные
    yearly_data = {}
    for year in range(2024, current_year + 1):
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM dividends WHERE user_id=%s AND YEAR(date)=%s", (user_id, year))
        d_cur = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM coupons WHERE user_id=%s AND YEAR(date)=%s", (user_id, year))
        c_cur = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM dividends WHERE user_id=%s AND YEAR(date)=%s", (user_id, year - 1))
        d_prev = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM coupons WHERE user_id=%s AND YEAR(date)=%s", (user_id, year - 1))
        c_prev = float(cursor.fetchone()[0])

        div_growth = ((d_cur + c_cur) / (d_prev + c_prev)) if (d_prev + c_prev) > 0 else 0
        # Преобразуем в проценты (1.5 = 150%)
        div_growth_pct = div_growth

        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM deposits WHERE user_id=%s AND YEAR(date)=%s", (user_id, year))
        dep = float(cursor.fetchone()[0])

        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM tax_deductions WHERE user_id=%s AND YEAR(date)=%s", (user_id, year))
        t1 = float(cursor.fetchone()[0])
        cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM tax_refunds WHERE user_id=%s AND YEAR(date)=%s", (user_id, year))
        t2 = float(cursor.fetchone()[0])
        inflow = dep + t1 + t2 + d_cur + c_cur

        yearly_data[year] = {
            "div_growth": div_growth_pct,
            "deposits": dep,
            "inflow": inflow,
            "dividends": d_cur,
            "coupons": c_cur,
        }

    conn.close()

    # Общие достижения
    all_time = [
        ("За всё время", PORTFOLIO_VALUE, portfolio_value),
        ("За всё время", TOTAL_DEPOSITS, total_deposits),
        ("За всё время", PROFIT_ALL_TIME, profit),
        ("За всё время", TOTAL_INCOME, total_income),
        ("За всё время", DIVIDENDS_SUM, div_sum),
        ("За всё время", COUPONS_SUM, coupons_sum),
        ("За всё время", DIVIDENDS_COUNT, div_count),
        ("За всё время", COUPONS_COUNT, coupons_count),
        ("За всё время", TRADES_COUNT, trades_count),
        ("За всё время", DIVIDEND_MONTHS, div_months),
    ]

    # Ежегодные
    yearly = []
    for year in sorted(yearly_data.keys()):
        yd = yearly_data[year]
        yearly.append((f"{year} год", YEAR_DIV_GROWTH, yd["div_growth"]))
        yearly.append((f"{year} год", YEAR_DEPOSITS, yd["deposits"]))
        yearly.append((f"{year} год", YEAR_INFLOW, yd["inflow"]))
        yearly.append((f"{year} год", YEAR_DIVIDENDS, yd["dividends"]))
        yearly.append((f"{year} год", YEAR_COUPONS, yd["coupons"]))

    return all_time + yearly