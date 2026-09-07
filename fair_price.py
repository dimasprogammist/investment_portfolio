import requests
from bs4 import BeautifulSoup
import re
import time

# Список банков (особая методика расчета)
BANKS = ['SBER', 'T', 'VTBR']


def get_current_price(ticker):
    """Получает текущую цену акции со страницы МСФО."""
    url = f'https://smart-lab.ru/q/{ticker}/f/y/MSFO/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        row = soup.find('tr', attrs={'field': 'common_share'})
        if row:
            tds = row.find_all('td')
            for i, td in enumerate(tds):
                if 'ltm_spc' in td.get('class', []):
                    if i + 1 < len(tds):
                        price_td = tds[i + 1]
                        price_text = price_td.get_text(strip=True).replace(' ', '').replace(',', '.')
                        try:
                            return float(price_text)
                        except ValueError:
                            pass
        return None
    except:
        return None


def get_current_multipliers(ticker, is_bank=False):
    """Получает текущие (LTM) значения мультипликаторов из таблицы МСФО."""
    url = f'https://smart-lab.ru/q/{ticker}/f/y/MSFO/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        if is_bank:
            # Для банков: P/E, P/BV, ROE
            field_map = {
                'p_e': 'P/E',
                'p_bv': 'P/B',
                'roe': 'ROE'
            }
        else:
            # Для остальных: P/E, P/BV, P/S, EV/EBITDA, P/FCF
            field_map = {
                'p_e': 'P/E',
                'p_bv': 'P/B',
                'p_s': 'P/S',
                'ev_ebitda': 'EV/EBITDA',
                'p_fcf': 'P/CF'
            }

        result = {}

        for field_name, mult_name in field_map.items():
            row = soup.find('tr', attrs={'field': field_name})
            if row:
                tds = row.find_all('td')
                ltm_value = None
                for i, td in enumerate(tds):
                    if 'ltm_spc' in td.get('class', []):
                        if i + 1 < len(tds):
                            ltm_td = tds[i + 1]
                            ltm_value = ltm_td.get_text(strip=True).replace(' ', '').replace(',', '.')
                        break

                if ltm_value:
                    try:
                        ltm_value = ltm_value.replace('%', '')
                        val = float(ltm_value)
                        if val > 0:
                            result[mult_name] = val
                        else:
                            result[mult_name] = None
                    except ValueError:
                        result[mult_name] = None
                else:
                    result[mult_name] = None
            else:
                result[mult_name] = None

        return result
    except:
        return None


def get_average_from_graph(ticker, multiplier_type):
    """Получает среднее значение мультипликатора из годового графика, включая LTM."""
    url = f'https://smart-lab.ru/q/{ticker}/MSFO/{multiplier_type}/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 504:
            return None
        response.raise_for_status()
        html = response.text

        year_data_match = re.search(r"var aYearData\s*=\s*\{", html)
        if not year_data_match:
            return None

        diagram_section = re.search(
            r"'diagram'\s*:\s*\{.*?\"data\":\s*\[(.*?)\]\s*,\s*\"field\"",
            html[year_data_match.start():],
            re.DOTALL
        )

        if not diagram_section:
            return None

        data_text = diagram_section.group(1)
        y_values = re.findall(r'"y"\s*:\s*([\d.]+)', data_text)

        if not y_values:
            return None

        values = [float(y) for y in y_values]
        if not values:
            return None

        avg = sum(values) / len(values)
        return avg
    except:
        return None


def calculate_fair_price_for_ticker(ticker):
    """Рассчитывает справедливую цену для одного тикера."""
    is_bank = ticker in BANKS

    if is_bank:
        mult_names = ['P/E', 'P/B', 'ROE']
        url_map = {
            'P/E': 'p_e',
            'P/B': 'p_bv',
            'ROE': 'roe'
        }
        print(f"    Методика: банковская (P/E, P/BV, ROE)")
    else:
        mult_names = ['P/E', 'P/B', 'P/S', 'EV/EBITDA', 'P/CF']
        url_map = {
            'P/E': 'p_e',
            'P/B': 'p_bv',
            'P/S': 'p_s',
            'EV/EBITDA': 'ev_ebitda',
            'P/CF': 'p_fcf'
        }

    # Получаем текущую цену
    current_price = get_current_price(ticker)
    if not current_price:
        return None, None, None, "Ошибка получения текущей цены"

    # Получаем текущие значения мультипликаторов
    current_mult = get_current_multipliers(ticker, is_bank)
    if not current_mult:
        return None, None, None, "Ошибка получения мультипликаторов"

    # Получаем средние значения
    avg_mult = {}
    for mult_name in mult_names:
        avg_mult[mult_name] = get_average_from_graph(ticker, url_map[mult_name])
        time.sleep(0.3)

    # Расчет коэффициентов с фильтрацией выбросов
    coefficients = {}
    raw_k = {}
    details = {}

    for mult_name in mult_names:
        current_val = current_mult.get(mult_name)
        avg_val = avg_mult.get(mult_name)

        details[mult_name] = {
            'current': current_val,
            'average': avg_val,
            'k': None
        }

        if current_val and current_val != 0 and avg_val and avg_val != 0:
            # Для ROE особая формула: K = Текущий_ROE / Средний_ROE
            # Чем выше ROE, тем дороже должен стоить банк
            if mult_name == 'ROE':
                k = current_val / avg_val
            else:
                k = avg_val / current_val
            raw_k[mult_name] = k

    # Фильтруем выбросы: K должен быть в пределах [0.1, 20]
    MIN_K = 0.1
    MAX_K = 20.0

    for mult_name, k in raw_k.items():
        if MIN_K <= k <= MAX_K:
            coefficients[mult_name] = k
            details[mult_name]['k'] = k

    # Минимум 2 мультипликатора для расчета
    MIN_MULTIPLIERS = 2

    if len(coefficients) < MIN_MULTIPLIERS:
        return current_price, details, None, f"Недостаточно мультипликаторов ({len(coefficients)} из {len(mult_names)})"

    # Используем СРЕДНЕЕ АРИФМЕТИЧЕСКОЕ
    k_values = list(coefficients.values())
    average_k = sum(k_values) / len(k_values)

    fair_price = current_price * average_k

    details['_avg_k'] = average_k
    details['_count'] = len(coefficients)

    return current_price, details, fair_price, None


def calculate_all_fair_prices(tickers):
    """Рассчитывает справедливые цены для списка тикеров и возвращает словарь"""
    results = {}

    for ticker in tickers:
        current_price, details, fair_price, error = calculate_fair_price_for_ticker(ticker)

        if fair_price and current_price:
            upside = ((fair_price / current_price) - 1) * 100
            results[ticker] = {
                'current_price': current_price,
                'fair_price': fair_price,
                'upside': upside,
                'details': details,
            }
        else:
            results[ticker] = None

        time.sleep(0.5)

    return results


def get_msfo_table(ticker):
    """Получает ВСЕ мультипликаторы из таблицы МСФО за все годы + LTM"""
    url = f'https://smart-lab.ru/q/{ticker}/f/y/MSFO/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем строки с атрибутом field (это показатели)
        indicator_rows = soup.find_all('tr', attrs={'field': True})

        if not indicator_rows:
            return None

        # Ищем заголовки годов в первой строке с годами
        years = []
        for row in soup.find_all('tr'):
            tds = row.find_all('td')
            year_texts = []
            for td in tds:
                text = td.get_text(strip=True)
                if text and (text.startswith('20') or 'LTM' in text.upper()):
                    year_texts.append(text)
            if len(year_texts) >= 3:  # Минимум 3 года
                years = year_texts
                break

        # Собираем все показатели
        indicators = {}

        for row in indicator_rows:
            field_name = row.get('field', '')

            # Получаем название из th
            th = row.find('th')
            if th:
                name = th.get_text(strip=True)
            else:
                name = field_name

            if not name:
                continue

            # Собираем значения из td (пропускаем первые служебные)
            tds = row.find_all('td')
            values = []

            for td in tds:
                # Пропускаем служебные ячейки
                classes = td.get('class', [])
                if any(c in ['chartrow', 'ltm_spc'] for c in classes):
                    continue

                text = td.get_text(strip=True).replace(' ', '').replace(',', '.').replace('%', '')
                if text and text not in ('&nbsp;', ''):
                    try:
                        val = float(text)
                        values.append(val)
                    except:
                        pass

            if values and len(values) >= len(years):
                # Если значений больше чем годов — берём последние
                values = values[-len(years):]

            if values:
                indicators[name] = dict(zip(years[:len(values)], values))

        return {
            'years': years,
            'indicators': indicators,
            'ticker': ticker
        }

    except Exception as e:
        print(f"Ошибка парсинга МСФО для {ticker}: {e}")
        return None


def get_all_msfo_data(tickers):
    """Получает МСФО данные для всех тикеров"""
    results = {}
    for ticker in tickers:
        print(f"  Загрузка МСФО {ticker}...")
        data = get_msfo_table(ticker)
        if data:
            # Сохраняем в БД
            save_msfo_to_db(ticker, data)
            results[ticker] = data
        time.sleep(0.3)
    return results


def save_msfo_to_db(ticker, data):
    """Сохраняет МСФО данные в БД"""
    from DB.db_config import create_connection

    conn = create_connection()
    if not conn:
        return

    cursor = conn.cursor()
    cursor.execute("USE investment_portfolio")

    indicators = data['indicators']

    # Маппинг: название на Smart-lab → (поле в БД, это проценты?)
    field_map = {
        'P/E': ('pe', False),
        'P/B': ('pb', False),
        'P/S': ('ps', False),
        'EV/EBITDA': ('evebitda', False),
        'EV/EBIT': ('evebit', False),
        'EV/S': ('ev_s', False),
        'ROE,%': ('roe', True),
        'ROA,%': ('roa', True),
        'ROIC,%': ('roic', True),
        'ROCE,%': ('roce', True),
        'Чистая прибыль,млрд руб': ('net_income', False),
        'Выручка,млрд руб': ('revenue', False),
        'EBITDA,млрд руб': ('ebitda', False),
        'EBIT,млрд руб': ('ebit', False),
        'FCF,млрд руб': ('fcf', False),
        'Капитализация,млрд руб': ('market_cap', False),
        'EV,млрд руб': ('ev', False),
        'Долг/EBITDA': ('debt_ebitda', False),
        'Чистый долг/EBITDA': ('net_debt_ebitda', False),
        'D/E': ('de', False),
        'Чистая маржа,%': ('net_margin', True),
        'Операционная маржа,%': ('operating_margin', True),
        'EBITDA маржа,%': ('ebitda_margin', True),
        'CAPEX/Выручка,%': ('capex_revenue', True),
        'Тек. ликвидность': ('current_ratio', False),
        'P/FCF': ('pfcf', False),
        'P/CF': ('pcf', False),
        'Див доход, ао,%': ('dividend_yield', True),
    }

    # Берём LTM (последний столбец)
    ltm_key = None
    for year in data['years']:
        if 'LTM' in year.upper():
            ltm_key = year
            break

    if not ltm_key and data['years']:
        ltm_key = data['years'][-1]

    if not ltm_key:
        conn.close()
        return

    updates = {}
    for smartlab_name, (db_field, is_percent) in field_map.items():
        if smartlab_name in indicators:
            vals = indicators[smartlab_name]
            if ltm_key in vals and vals[ltm_key] is not None:
                val = float(vals[ltm_key])
                # Если на смартлабе в процентах (например ROE = 22.7 означает 22.7%)
                # то так и сохраняем
                updates[db_field] = val

    if updates:
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [ticker]
        cursor.execute(f"UPDATE stock_fundamentals SET {set_clause}, updated_at = CURDATE() WHERE ticker = %s", values)
        print(f"  {ticker}: обновлено {len(updates)} полей")

    # Сохраняем полную историю
    import json
    history_json = json.dumps(data, ensure_ascii=False)
    cursor.execute("UPDATE stock_fundamentals SET msfo_history = %s WHERE ticker = %s", (history_json, ticker))

    conn.commit()
    conn.close()

# Список тикеров
TICKERS = [
    'SBER', 'ROSN', 'YDEX', 'T', 'TATN', 'NVTK', 'GMKN',
    'X5', 'MDMG', 'OZON', 'ASTR', 'ELMT', 'MAGN', 'NLMK',
    'AQUA', 'FLOT', 'POSI', 'PHOR', 'PLZL', 'NMTP', 'PRMD'
]

NAMES = {
    'SBER': 'Сбербанк',
    'ROSN': 'Роснефть',
    'YDEX': 'Яндекс',
    'T': 'Т-Технологии',
    'TATN': 'Татнефть',
    'NVTK': 'Новатэк',
    'GMKN': 'Норильский никель',
    'X5': 'X5 Group',
    'MDMG': 'Мать и дитя',
    'OZON': 'Ozon',
    'ASTR': 'Астра',
    'ELMT': 'Элемент',
    'MAGN': 'ММК',
    'NLMK': 'НЛМК',
    'AQUA': 'Инарктика',
    'FLOT': 'Совкомфлот',
    'POSI': 'Positive Technologies',
    'PHOR': 'ФосАгро',
    'PLZL': 'Полюс',
    'NMTP': 'НМТП',
    'PRMD': 'Промед',
}

if __name__ == "__main__":
    print("=" * 110)
    print("РАСЧЕТ СПРАВЕДЛИВОЙ ЦЕНЫ ПО МУЛЬТИПЛИКАТОРАМ (Smart-lab)")
    print("=" * 110)
    print(f"Дата расчета: {time.strftime('%d.%m.%Y %H:%M')}")
    print(f"Компаний: {len(TICKERS)}")
    print(f"Фильтр K: [0.1, 20.0] | Мин. мультипликаторов: 2 | Усреднение: СРЕДНЕЕ")
    print(f"Банки (особая методика): {', '.join(BANKS)}")
    print("-" * 110)

    results = []

    for ticker in TICKERS:
        company = NAMES.get(ticker, ticker)

        print(f"\n  [{company} ({ticker})]")

        current_price, details, fair_price, error = calculate_fair_price_for_ticker(ticker)

        if error:
            print(f"    ❌ {error}")
            if details:
                print(f"    Доступные мультипликаторы:")
                for mult_name in details:
                    if mult_name.startswith('_'):
                        continue
                    d = details[mult_name]
                    cur = f"{d['current']:.2f}" if d['current'] else "—"
                    avg = f"{d['average']:.2f}" if d['average'] else "—"
                    print(f"      {mult_name:<12} тек={cur:<8} сред={avg:<8}")

            results.append({
                'ticker': ticker,
                'company': company,
                'price': current_price,
                'fair_price': None,
                'upside': None,
                'error': error
            })
        else:
            upside = ((fair_price / current_price) - 1) * 100

            print(f"    Цена: {current_price:.2f} руб.")
            print(f"    Мультипликаторы (✓ — используется, ✗ — отброшен):")
            for mult_name in details:
                if mult_name.startswith('_'):
                    continue
                d = details[mult_name]
                cur = f"{d['current']:.2f}" if d['current'] else "—"
                avg = f"{d['average']:.2f}" if d['average'] else "—"

                if d['k'] is not None:
                    print(f"      ✓ {mult_name:<12} тек={cur:<8} сред={avg:<8} K={d['k']:.4f}")
                else:
                    if d['current'] and d['average']:
                        raw = d['average'] / d['current']
                        print(f"      ✗ {mult_name:<12} тек={cur:<8} сред={avg:<8} K={raw:.4f} (выброс)")
                    else:
                        print(f"      ✗ {mult_name:<12} тек={cur:<8} сред={avg:<8} (нет данных)")

            print(f"    Среднее K: {details['_avg_k']:.4f}")
            print(f"    Использовано мультипликаторов: {details['_count']}")
            print(f"    Справедливая цена: {fair_price:.2f} руб.", end="")
            if upside > 0:
                print(f" | 📈 +{upside:.1f}%")
            else:
                print(f" | 📉 {upside:.1f}%")

            results.append({
                'ticker': ticker,
                'company': company,
                'price': current_price,
                'fair_price': fair_price,
                'upside': upside,
                'error': None
            })

        time.sleep(1)

    # Итоговая таблица
    print("\n\n" + "=" * 110)
    print("ИТОГОВАЯ ТАБЛИЦА (сортировка по потенциалу)")
    print("=" * 110)
    print(f"{'Тикер':<8} {'Компания':<25} {'Цена':>10} {'Справедливо':>12} {'Потенциал':>10} {'K ср.':>8}")
    print("-" * 110)

    sorted_results = sorted([r for r in results if r['fair_price'] is not None],
                            key=lambda x: x['upside'] if x['upside'] is not None else -999, reverse=True)

    for r in sorted_results:
        upside_str = f"+{r['upside']:.1f}%" if r['upside'] > 0 else f"{r['upside']:.1f}%"
        k_avg = r['fair_price'] / r['price'] if r['price'] > 0 else 0
        print(
            f"{r['ticker']:<8} {r['company']:<25} {r['price']:>10.2f} {r['fair_price']:>12.2f} {upside_str:>10} {k_avg:>8.2f}")

    errors = [r for r in results if r['error']]
    if errors:
        print("\n" + "-" * 110)
        print("Компании с ошибками:")
        for r in errors:
            print(f"  {r['ticker']} ({r['company']}): {r['error']}")

    successful = [r for r in results if r['fair_price'] is not None]
    if successful:
        undervalued = [r for r in successful if r['upside'] > 0]
        overvalued = [r for r in successful if r['upside'] <= 0]

        print("\n" + "=" * 110)
        print("СТАТИСТИКА")
        print(f"  Всего компаний: {len(results)}")
        print(f"  Успешно рассчитано: {len(successful)}")
        print(f"  Ошибки/пропуски: {len(errors)}")
        print(f"  Недооценены (потенциал > 0): {len(undervalued)}")
        print(f"  Переоценены (потенциал ≤ 0): {len(overvalued)}")
        if successful:
            avg_upside = sum(r['upside'] for r in successful) / len(successful)
            print(f"  Средний потенциал: {avg_upside:+.1f}%")

    print("\n" + "=" * 110)
    print("Методика:")
    print("  • Для банков (SBER, T): P/E, P/BV, ROE")
    print("  • Для остальных: P/E, P/BV, P/S, EV/EBITDA, P/FCF")
    print("  • Отбрасываем выбросы K ∉ [0.1, 20.0]")
    print("  • Минимум 2 мультипликатора для расчета")
    print("  • Используем СРЕДНЕЕ АРИФМЕТИЧЕСКОЕ")
    print("=" * 110)