import sys
import traceback

try:
    import tkinter as tk
    import numpy as np
    from tkinter import ttk, messagebox
    from datetime import datetime
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import threading
    import time
    from scipy.optimize import newton
    from DB.db_config import init_db
    from config import COLORS, TICKER_COLORS, TARGET_SHARES, TARGET_SHARES_STOCKS, TARGET_SHARES_BONDS, STOCKS, BONDS, \
        TICKER_NAMES, CURRENCY_BONDS
    from DB.database import (get_portfolio_stats, save_deposit, save_trade,
                             save_income, save_redemption, get_deposits,
                             get_dividends, get_coupons)
    from prices import get_all_prices
    from authorization.auth_dialogs import LoginDialog, SettingsDialog
    from benchmarks import update_benchmarks_in_db, get_inflation_yoy, inflation_adjusted_deposits

    import pandas as pd
    from datetime import timedelta
    from history import get_historical_prices, get_price_on_date
    from DB.database import get_portfolio_history

    from dialogs import (
        StyledButton,
        StyledDialog,
        AddDepositDialog,
        AddTradeDialog,
        AddIncomeDialog,
        AddRedemptionDialog,
        AddTaxRefundDialog,
        AddDepositAccountDialog,
        AddDepositPaymentDialog,
        AddTaxDeductionDialog,
        UpdateAccountDialog
    )

except Exception:
    traceback.print_exception() 
    input()
    sys.exit(1)

def calculate_xirr(cashflows, dates):
    """
    Расчет среднегодовой доходности (XIRR).
    cashflows — список сумм (пополнения с минусом, выводы с плюсом)
    dates — список дат
    """
    if len(cashflows) < 2 or len(dates) < 2:
        return 0

    # Переводим даты в дни от первой даты
    d0 = dates[0]
    days = [(d - d0).days for d in dates]

    def npv(rate):
        total = 0
        for cf, day in zip(cashflows, days):
            total += cf * (1 + rate) ** (-day / 365.0)
        return total

    try:
        result = newton(npv, 0.1, maxiter=100)
        return result * 100
    except:
        return 0


# Всплывающая подсказка для заголовков таблиц
_tooltip_window = None


def show_tooltip_window(widget, text, x, y):
    """Показывает всплывающую подсказку"""
    global _tooltip_window
    hide_tooltip()
    _tooltip_window = tk.Toplevel(widget)
    _tooltip_window.wm_overrideredirect(True)
    _tooltip_window.wm_geometry(f"+{x+10}+{y+10}")
    label = tk.Label(_tooltip_window, text=text, background="#ffffcc",
                     relief="solid", borderwidth=1, font=("Calibri", 9),
                     wraplength=300, padx=5, pady=3)
    label.pack()

def hide_tooltip(event=None):
    """Скрывает подсказку"""
    global _tooltip_window
    if _tooltip_window:
        _tooltip_window.destroy()
        _tooltip_window = None


class InvestmentApp:
    def __init__(self, root, user_id: int):
        self.root = root
        self.user_id = user_id
        self.root.title("Инвестиционный учёт")
        self.root.geometry("1500x800")
        self.root.configure(bg=COLORS['bg_header'])

        self.stocks = STOCKS
        self.bonds = BONDS

        self.current_prices = {}
        self.update_thread_running = True
        self.auto_update_enabled = True

        self.load_user_assets()
        self.create_widgets()
        import os
        benchmark_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'last_benchmark_update.txt')
        need_update = True
        if os.path.exists(benchmark_file):
            try:
                with open(benchmark_file) as f:
                    last_update = datetime.fromisoformat(f.read().strip())
                    need_update = (datetime.now() - last_update).days > 30
            except:
                pass

        if need_update:
            try:
                update_benchmarks_in_db()
                with open(benchmark_file, 'w') as f:
                    f.write(datetime.now().isoformat())
            except Exception as e:
                print(f"Не удалось обновить бенчмарки: {e}")

        self.refresh_prices()
        self.start_auto_update()
        self.fair_prices = {}
        self.load_fair_prices()

    def load_user_assets(self):
        """Загружает выбранные активы из БД"""
        from DB.db_config import create_connection
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute("SELECT ticker, security_type FROM user_assets WHERE user_id = %s AND is_active = TRUE",
                           (self.user_id,))
            user_assets = cursor.fetchall()
            conn.close()

            stocks_from_db = [t for t, s in user_assets if s == 'stock']
            bonds_from_db = [t for t, s in user_assets if s == 'bond']

            if stocks_from_db:
                self.stocks = stocks_from_db
            # Если нет в БД — оставляем из конфига (STOCKS)

            if bonds_from_db:
                self.bonds = bonds_from_db
            # Если нет в БД — оставляем из конфига (BONDS)

    def show_multiplier_chart(self, ticker, company_name, indicator_name, full_years, ltm_years, year_values,
                              higher_better):
        """Показывает столбчатую диаграмму мультипликатора по годам"""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        # Закрываем все предыдущие фигуры чтобы не было наложений
        plt.close('all')

        # Собираем данные
        years_labels = full_years + ltm_years
        values = []
        for year in years_labels:
            val = year_values.get(year)
            values.append(val if val is not None else 0)

        # Считаем среднее по полным годам
        full_vals = [v for v in values[:len(full_years)] if v is not None and v != 0]
        avg_val = sum(full_vals) / len(full_vals) if full_vals else 0

        # Определяем цвета столбцов
        colors = []
        for i, val in enumerate(values):
            if val == 0:
                colors.append('#bdbdbd')
            elif i < len(full_years):
                if indicator_name in higher_better:
                    colors.append('#4caf50' if val > avg_val else '#f44336')
                else:
                    colors.append('#4caf50' if val < avg_val else '#f44336')
            else:
                colors.append('#2196f3')

        # Создаём окно
        chart_win = tk.Toplevel(self.root)
        chart_win.title(f"{company_name} ({ticker}) — {indicator_name}")
        chart_win.geometry("700x500")
        chart_win.transient(self.root)
        chart_win.grab_set()
        chart_win.configure(bg=COLORS['bg_main'])

        tk.Label(chart_win, text=f"{indicator_name} по годам", font=("Calibri", 14, "bold"),
                 bg=COLORS['bg_main'], fg=COLORS['accent']).pack(pady=(15, 5))

        # Создаём НОВУЮ фигуру
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor(COLORS['bg_main'])
        ax.set_facecolor(COLORS['bg_main'])

        x = range(len(years_labels))
        bars = ax.bar(x, values, color=colors, width=0.6, edgecolor='white', linewidth=0.5)

        # Горизонтальная линия среднего
        ax.axhline(y=avg_val, color='#ff9800', linestyle='--', linewidth=2,
                   label=f'Среднее: {avg_val:.2f}')

        # Подписи значений над столбцами
        for i, (bar, val) in enumerate(zip(bars, values)):
            if val != 0:
                ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + (max(values) * 0.02),
                        f'{val:.2f}', ha='center', va='bottom', fontsize=9, color=COLORS['text'])

        ax.set_xticks(x)
        ax.set_xticklabels(years_labels, fontsize=10, color=COLORS['text'])
        ax.tick_params(axis='y', colors=COLORS['text'])
        ax.set_ylabel(indicator_name, color=COLORS['text'], fontsize=11)
        ax.legend(loc='upper right', fontsize=9)

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(COLORS['text_secondary'])
        ax.spines['bottom'].set_color(COLORS['text_secondary'])
        ax.grid(axis='y', alpha=0.3, color=COLORS['text_secondary'])

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, chart_win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Button(chart_win, text="Закрыть", command=chart_win.destroy,
                  bg=COLORS['bg_header'], fg=COLORS['text'], font=("Calibri", 10),
                  relief="flat", padx=25, pady=8, cursor="hand2").pack(pady=(0, 15))

    def load_fair_prices(self):
        """Загружает справедливые цены из файла или рассчитывает"""
        import os
        import json

        fair_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fair_prices.json')
        need_calc = True

        if os.path.exists(fair_file):
            try:
                with open(fair_file, 'r') as f:
                    data = json.load(f)
                    # Проверяем свежесть (не старше 24 часов)
                    from datetime import datetime
                    if datetime.now().timestamp() - data.get('_updated', 0) < 86400:
                        self.fair_prices = data
                        need_calc = False
            except:
                pass

        if need_calc:
            self.calculate_fair_prices()

    def calculate_fair_prices(self):
        """Рассчитывает справедливые цены в фоновом потоке"""
        self.status_label.config(text="Расчёт справедливых цен...")
        self.root.update()

        def run():
            from fair_price import calculate_all_fair_prices
            results = calculate_all_fair_prices(self.stocks)
            results['_updated'] = datetime.now().timestamp()

            import json
            import os
            fair_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fair_prices.json')
            with open(fair_file, 'w') as f:
                json.dump(results, f)

            self.fair_prices = results
            self.root.after(0, lambda: self.status_label.config(text="Справедливые цены обновлены!"))
            self.root.after(0, self.update_all_tables)

        threading.Thread(target=run, daemon=True).start()

    def switch_user(self):
        """Смена пользователя: вход под другим логином и перезагрузка данных."""
        dlg = LoginDialog(self.root)
        uid = dlg.show()
        if uid is None:
            return
        self.user_id = uid
        self.update_all_tables()
        self.load_data()

    def open_settings(self):
        """Открывает окно настроек."""
        SettingsDialog(
            self.root,
            current_theme_callback=self.apply_theme,
            switch_user_callback=self.switch_user,
            user_id=self.user_id
        )

    def apply_theme(self, theme):
        """Применяет выбранную тему."""
        import json
        import os

        # Сохраняем тему в файл
        theme_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.theme')
        with open(theme_file, 'w') as f:
            json.dump({'theme': theme}, f)

        # Показываем сообщение и ЗАКРЫВАЕМ приложение
        messagebox.showinfo("Тема",
                            f"Приложение будет перезапущено с {'тёмной' if theme == 'dark' else 'светлой'} темой.")

        # Закрываем главное окно
        self.root.destroy()

        import subprocess
        import sys
        python = sys.executable
        script = os.path.abspath(__file__)
        subprocess.Popen([python, script])

    def update_bottom_stats(self, stats, total_value, total_cost, all_positions):
        """Обновление нижней статистики на всех вкладках"""

        # Разделяем позиции на акции и облигации
        stock_positions = [p for p in all_positions if p[0] == 'stock']
        bond_positions = [p for p in all_positions if p[0] == 'bond']

        # Статистика по акциям
        stocks_cost = sum(p[2]['total_cost'] for p in stock_positions)
        stocks_value = sum(p[4] for p in stock_positions)
        stocks_profit = stocks_value - stocks_cost
        stocks_profit_pct = (stocks_profit / stocks_cost * 100) if stocks_cost > 0 else 0

        # Статистика по облигациям
        bonds_cost = sum(p[2]['total_cost'] for p in bond_positions)
        bonds_value = sum(p[4] for p in bond_positions)
        bonds_profit = bonds_value - bonds_cost
        bonds_profit_pct = (bonds_profit / bonds_cost * 100) if bonds_cost > 0 else 0

        # Общая статистика
        total_dividends = stats['total_dividends']
        total_coupons = stats['total_coupons']
        total_income = total_dividends + total_coupons + stats['total_redemptions']

        # Обновляем сводную вкладку
        left_text = f"Акции: {stocks_cost:,.0f}₽ → {stocks_value:,.0f}₽ | Облигации: {bonds_cost:,.0f}₽ → {bonds_value:,.0f}₽"
        right_text = f"Дивиденды: {total_dividends:,.0f}₽ | Купоны: {total_coupons:,.0f}₽ | Всего дохода: {total_income:,.0f}₽"

        if hasattr(self, 'summary_stats_left'):
            self.summary_stats_left.config(text=left_text)
            self.summary_stats_right.config(text=right_text)

        # Обновляем вкладку акций
        stocks_left = f"Всего акций: {len(stock_positions)} | Затраты: {stocks_cost:,.0f}₽ | Тек. стоимость: {stocks_value:,.0f}₽"
        stocks_right = f"Прибыль: {stocks_profit:+,.0f}₽ ({stocks_profit_pct:+.2f}%) | Дивиденды: {total_dividends:,.0f}₽"

        if hasattr(self, 'stocks_stats_left'):
            self.stocks_stats_left.config(text=stocks_left)
            self.stocks_stats_right.config(text=stocks_right)

        # Обновляем вкладку облигаций
        bonds_left = f"Всего облигаций: {len(bond_positions)} | Затраты: {bonds_cost:,.0f}₽ | Тек. стоимость: {bonds_value:,.0f}₽"
        bonds_right = f"Прибыль: {bonds_profit:+,.0f}₽ ({bonds_profit_pct:+.2f}%) | Купоны: {total_coupons:,.0f}₽"

        if hasattr(self, 'bonds_stats_left'):
            self.bonds_stats_left.config(text=bonds_left)
            self.bonds_stats_right.config(text=bonds_right)

    def create_cashflow_tab(self):
        """Вкладка с денежным потоком по годам"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📊 Денежный поток")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        # Верхняя панель с выбором года
        control_frame = tk.Frame(bg_frame, bg=COLORS['bg_header'])
        control_frame.pack(fill=tk.X, padx=0, pady=5)

        tk.Label(control_frame, text="Год:", font=("Calibri", 10),
                 bg=COLORS['bg_header'], fg=COLORS['text']).pack(side=tk.LEFT, padx=5)

        current_year = datetime.now().year
        years = [str(y) for y in range(2023, current_year + 1)]
        self.cashflow_year = ttk.Combobox(control_frame, values=years, width=10, state='readonly')
        self.cashflow_year.set(str(current_year))
        self.cashflow_year.pack(side=tk.LEFT, padx=5)

        self.cashflow_btn = StyledButton(control_frame, "Построить", self.plot_cashflow, width=15)
        self.cashflow_btn.pack(side=tk.LEFT, padx=10)

        # Фрейм для графика
        graph_frame = tk.Frame(bg_frame, bg=COLORS['bg_main'])
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        self.cashflow_figure = Figure(figsize=(16, 9), dpi=100, facecolor=COLORS['bg_main'])
        self.cashflow_ax = self.cashflow_figure.add_subplot(111)
        self.cashflow_ax.set_facecolor(COLORS['table_odd'])
        self.cashflow_ax.tick_params(colors=COLORS['text'])

        self.cashflow_figure.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.12)

        self.cashflow_canvas = FigureCanvasTkAgg(self.cashflow_figure, graph_frame)
        self.cashflow_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Сразу строим график для текущего года
        self.plot_cashflow()

    def create_achievements_tab(self):
        """Вкладка с достижениями"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🏆 Достижения")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(bg_frame, bg=COLORS['bg_main'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(bg_frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS['bg_main'])

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        style = ttk.Style()
        style.configure("green.Horizontal.TProgressbar",
                        troughcolor=COLORS['bg_header'],
                        background=COLORS['accent'],
                        bordercolor=COLORS['bg_header'],
                        lightcolor=COLORS['accent'],
                        darkcolor=COLORS['accent'])

        from achievements import get_all_achievements_with_progress
        achievements_data = get_all_achievements_with_progress(self.user_id)

        groups = {}
        for category, ach, value in achievements_data:
            if category not in groups:
                groups[category] = []
            groups[category].append((ach, value))

        row = 0
        for group_name, items in groups.items():
            tk.Label(scroll_frame, text=group_name, font=("Calibri", 14, "bold"),
                     bg=COLORS['bg_main'], fg=COLORS['accent']).grid(
                row=row, column=0, columnspan=5, padx=15, pady=(15, 5), sticky="w")
            row += 1

            col = 0
            for ach, value in items:
                progress_data = ach.get_progress(value)
                bg_color = '#e8f5e9' if progress_data['completed_all'] else COLORS['bg_card']
                fg_color = COLORS['text_secondary'] if progress_data['completed_all'] else COLORS['text']

                card = tk.Frame(scroll_frame, bg=bg_color, relief=tk.FLAT, bd=1, padx=10, pady=8)
                card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

                tk.Label(card, text=f"{ach.icon} {ach.name}", font=("Calibri", 10, "bold"),
                         bg=bg_color, fg=fg_color).pack(anchor="w")

                bar = ttk.Progressbar(card, mode='determinate', length=258, maximum=100,
                                      value=progress_data['progress'],
                                      style="green.Horizontal.TProgressbar")
                bar.pack(fill=tk.X, pady=(5, 3))

                if progress_data['completed_all']:
                    value_text = f"✅ {progress_data['next_label']}"
                else:
                    value_text = f"{progress_data['value']:,.0f} из {progress_data['next_label']}".replace(',', ' ')
                tk.Label(card, text=value_text, font=("Calibri", 8), bg=bg_color, fg=fg_color).pack(anchor="w")
                tk.Label(card,
                         text=f"{progress_data['progress']}% | {progress_data['achieved_tiers']}/{progress_data['tiers_count']} ур.",
                         font=("Calibri", 7), bg=bg_color, fg=COLORS['text_light']).pack(anchor="w")

                col += 1
                if col == 5:
                    col = 0
                    row += 1

            if col > 0:
                row += 1

            for c in range(5):
                scroll_frame.grid_columnconfigure(c, weight=1, uniform="col")

    def plot_cashflow(self):
        """Построение графика денежного потока за выбранный год"""
        from DB.db_config import create_connection

        year = int(self.cashflow_year.get())

        conn = create_connection()
        if not conn:
            return

        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")

        # Месяцы для локализации
        months_ru = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
                     'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']

        # Инициализируем данные по месяцам
        monthly_data = {i: {'deposits': 0, 'tax_refunds': 0, 'purchases': 0,
                            'dividends': 0, 'coupons': 0} for i in range(1, 13)}

        # Пополнения (из deposits)
        cursor.execute(f"""
            SELECT MONTH(date), SUM(amount) FROM deposits 
            WHERE YEAR(date) = {year}
            GROUP BY MONTH(date)
        """)
        for row in cursor.fetchall():
            monthly_data[row[0]]['deposits'] = float(row[1] or 0)

        # Налоговые вычеты (из tax_deductions и tax_refunds)
        cursor.execute(f"""
            SELECT MONTH(date), SUM(amount) FROM tax_deductions 
            WHERE YEAR(date) = {year}
            GROUP BY MONTH(date)
        """)
        for row in cursor.fetchall():
            monthly_data[row[0]]['tax_refunds'] += float(row[1] or 0)

        cursor.execute(f"""
            SELECT MONTH(date), SUM(amount) FROM tax_refunds 
            WHERE YEAR(date) = {year}
            GROUP BY MONTH(date)
        """)
        for row in cursor.fetchall():
            monthly_data[row[0]]['tax_refunds'] += float(row[1] or 0)

        # Покупки (акции + облигации)
        cursor.execute(f"""
            SELECT MONTH(date), SUM(total_amount) FROM stock_trades 
            WHERE YEAR(date) = {year} AND operation = 'buy'
            GROUP BY MONTH(date)
        """)
        for row in cursor.fetchall():
            monthly_data[row[0]]['purchases'] += float(row[1] or 0)

        cursor.execute(f"""
            SELECT MONTH(date), SUM(total_amount) FROM bond_trades 
            WHERE YEAR(date) = {year} AND operation = 'buy'
            GROUP BY MONTH(date)
        """)
        for row in cursor.fetchall():
            monthly_data[row[0]]['purchases'] += float(row[1] or 0)

        # Дивиденды
        cursor.execute(f"""
            SELECT MONTH(date), SUM(amount) FROM dividends 
            WHERE YEAR(date) = {year}
            GROUP BY MONTH(date)
        """)
        for row in cursor.fetchall():
            monthly_data[row[0]]['dividends'] = float(row[1] or 0)

        # Купоны
        cursor.execute(f"""
            SELECT MONTH(date), SUM(amount) FROM coupons 
            WHERE YEAR(date) = {year}
            GROUP BY MONTH(date)
        """)
        for row in cursor.fetchall():
            monthly_data[row[0]]['coupons'] = float(row[1] or 0)

        conn.close()

        # Формируем данные для графика
        months = []
        deposits_tax = []  # Пополнения + вычеты
        dividends = []  # Дивиденды
        coupons = []  # Купоны
        purchases = []  # Покупки
        div_coupon_sum = []
        total_inflow = []  # Сумма всего

        for m in range(1, 13):
            data = monthly_data[m]
            months.append(months_ru[m - 1])

            dep_tax = data['deposits'] + data['tax_refunds']
            div = data['dividends']
            coup = data['coupons']

            deposits_tax.append(dep_tax)
            dividends.append(div)
            coupons.append(coup)
            purchases.append(data['purchases'])
            div_coupon_sum.append(div + coup)
            total_inflow.append(dep_tax + div + coup)

        # Очищаем и рисуем график
        self.cashflow_ax.clear()
        self.cashflow_ax.set_facecolor(COLORS['table_odd'])

        x = range(len(months))
        width = 0.16

        # Настройка цветов столбцов
        COLOR_DEPOSITS = '#719ef9'  # Синий для пополнений
        COLOR_DIVIDENDS = '#f73b4e'  # Зеленый для дивидендов
        COLOR_COUPONS = '#e0c200'  # Оранжевый для купонов
        COLOR_TOTAL = '#d67200'  # Голубой для общего притока
        COLOR_PURCHASES = '#45daf7'  # Красный для покупок

        # Группированные столбцы
        bars1 = self.cashflow_ax.bar([i - width * 2.0 for i in x], deposits_tax, width,
                                     label='Пополнения + вычеты', color=COLOR_DEPOSITS, alpha=0.8)
        bars2 = self.cashflow_ax.bar([i - width * 1.0 for i in x], dividends, width,
                                     label='Дивиденды', color=COLOR_DIVIDENDS, alpha=0.7)
        bars3 = self.cashflow_ax.bar([i + width * 0.0 for i in x], coupons, width,
                                     label='Купоны', color=COLOR_COUPONS, alpha=0.7)
        bars5 = self.cashflow_ax.bar([i + width * 1.0 for i in x], div_coupon_sum, width,
                                     label='Дивиденды + Купоны', color='#ab47bc', alpha=0.7)
        bars4 = self.cashflow_ax.bar([i + width * 2.0 for i in x], total_inflow, width,
                                     label='Общий приток', color=COLOR_TOTAL, alpha=0.6)

        # Линия покупок
        self.cashflow_ax.plot(x, purchases, 'o-', color=COLOR_PURCHASES, linewidth=2,
                              markersize=6, label='Покупки')

        # Подписи суммы на столбцах + Расчет отступов для подписей
        all_values = deposits_tax + dividends + coupons + div_coupon_sum + total_inflow + purchases
        max_val = max(all_values) if all_values else 100000
        offset = max_val * 0.03

        for i in x:
            if deposits_tax[i] > 0:
                self.cashflow_ax.text(i - width * 2, deposits_tax[i] + offset,
                                      f'{deposits_tax[i]:,.0f}'.replace(',', ' '),
                                      ha='center', va='bottom', fontsize=7,
                                      color=COLOR_DEPOSITS, rotation=90)
            if dividends[i] > 0:
                self.cashflow_ax.text(i - width * 1, dividends[i] + offset,
                                      f'{dividends[i]:,.0f}'.replace(',', ' '),
                                      ha='center', va='bottom', fontsize=7,
                                      color=COLOR_DIVIDENDS, rotation=90)
            if coupons[i] > 0:
                self.cashflow_ax.text(i + width * 0.0, coupons[i] + offset,
                                      f'{coupons[i]:,.0f}'.replace(',', ' '),
                                      ha='center', va='bottom', fontsize=7,
                                      color=COLOR_COUPONS, rotation=90)
            if div_coupon_sum[i] > 0:
                self.cashflow_ax.text(i + width * 1, div_coupon_sum[i] + offset,
                                      f'{div_coupon_sum[i]:,.0f}'.replace(',', ' '),
                                      ha='center', va='bottom', fontsize=7,
                                      color='#ab47bc', rotation=90)
            if total_inflow[i] > 0:
                self.cashflow_ax.text(i + width * 2, total_inflow[i] + offset,
                                      f'{total_inflow[i]:,.0f}'.replace(',', ' '),
                                      ha='center', va='bottom', fontsize=7,
                                      color=COLOR_TOTAL, rotation=90)
            if purchases[i] > 0:
                self.cashflow_ax.text(i, purchases[i] + offset,
                                      f'{purchases[i]:,.0f}'.replace(',', ' '),
                                      ha='center', va='bottom', fontsize=8,
                                      color=COLOR_PURCHASES, rotation=90, fontweight='bold')

            for i in range(len(months) + 1):
                # Пунктирные линии между месяцами
                self.cashflow_ax.axvline(x=i - 0.5, color='#bdbdbd', linestyle='--', linewidth=0.5, alpha=0.5)

        # Настройка осей
        self.cashflow_ax.set_xticks(x)
        self.cashflow_ax.set_xticklabels(months, rotation=0, ha='center', fontsize=8)
        self.cashflow_ax.set_ylabel('Сумма (₽)', color=COLORS['text'], fontsize=8)
        self.cashflow_ax.set_title(f'Денежный поток за {year} год', color=COLORS['text'],
                                   fontsize=12, pad=10)
        self.cashflow_ax.tick_params(axis='y', labelsize=8)
        self.cashflow_ax.tick_params(axis='x', labelsize=8)

        self.cashflow_ax.set_xlim(-0.5, 11.5)

        # Увеличиваем верхнюю границу оси Y
        all_values = deposits_tax + dividends + coupons + total_inflow + purchases
        max_value = max(all_values) if all_values else 100000
        y_max = max(max_value * 1.2, 100000)
        self.cashflow_ax.set_ylim(0, y_max)

        # Статистика
        total_dep = sum(data['deposits'] for data in monthly_data.values())
        total_tax = sum(data['tax_refunds'] for data in monthly_data.values())
        total_purchases = sum(purchases)
        total_div = sum(dividends)
        total_coupon = sum(coupons)

        # Панель статистики и суммами за год
        stats_text = (f'Пополнения: {total_dep:,.0f} ₽\n'
                      f'Налоговые вычеты: {total_tax:,.0f} ₽\n'
                      f'Пополнения + вычеты: {total_dep + total_tax:,.0f} ₽\n'
                      f'Покупки: {total_purchases:,.0f} ₽\n'
                      f'Дивиденды: {total_div:,.0f} ₽\n'
                      f'Купоны: {total_coupon:,.0f} ₽\n'
                      f'Див + Куп: {total_div + total_coupon:,.0f} ₽\n'
                      f'Общий приток: {total_dep + total_tax + total_div + total_coupon:,.0f} ₽')

        self.cashflow_ax.text(0.02, 0.95, stats_text, transform=self.cashflow_ax.transAxes,
                              fontsize=8, verticalalignment='top',
                              bbox=dict(boxstyle='round', facecolor=COLORS['accent_light'], alpha=0.8),
                              color=COLORS['text'])

        # Сравнение размера дивидендов с прошлым годом в %
        if year > 2023:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute(f"SELECT SUM(amount) FROM dividends WHERE YEAR(date) = {year - 1}")
            prev_div = float(cursor.fetchone()[0] or 0)

            if prev_div >= 0:
                # ... новый код вместо старого ...
                cursor.execute(f"SELECT SUM(amount) FROM coupons WHERE YEAR(date) = {year - 1}")
                prev_coupons = float(cursor.fetchone()[0] or 0)
                prev_total = prev_div + prev_coupons

                current_total = total_div + total_coupon
                share_of_last = (current_total / prev_total * 100) if prev_total > 0 else 0

                growth_text = f'Отношение дивидендов {year}/{year - 1} = {share_of_last:.2f}%'

                self.cashflow_ax.text(0.98, 0.95, growth_text, transform=self.cashflow_ax.transAxes,
                                      fontsize=8, verticalalignment='top', horizontalalignment='right',
                                      bbox=dict(boxstyle='round', facecolor=COLORS['warning'], alpha=0.3),
                                      color=COLORS['text'])
            conn.close()

        self.cashflow_ax.legend(loc='upper left', bbox_to_anchor=(1.0, 1.0105), fontsize=8)
        self.cashflow_ax.grid(True, alpha=0.3, axis='y')

        # Убираем верхнюю и правую границы
        self.cashflow_ax.spines['top'].set_visible(False)
        self.cashflow_ax.spines['right'].set_visible(False)
        self.cashflow_ax.spines['left'].set_color(COLORS['text_secondary'])
        self.cashflow_ax.spines['bottom'].set_color(COLORS['text_secondary'])

        self.cashflow_figure.tight_layout()
        self.cashflow_canvas.draw()

    def create_deposits_accounts_tab(self):
        """Вкладка с банковскими вкладами и счетами"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💰 Вклады")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        # Верхняя панель с кнопками
        btn_frame = tk.Frame(bg_frame, bg=COLORS['bg_header'])
        btn_frame.pack(fill=tk.X, padx=0, pady=5)

        # Кнопки функций вкладки вкладов
        StyledButton(btn_frame, "➕ Добавить вклад", self.add_deposit_account, width=18).pack(side=tk.LEFT, padx=0)
        StyledButton(btn_frame, "💵 Добавить выплату", self.add_deposit_payment, width=18).pack(side=tk.LEFT, padx=0)
        StyledButton(btn_frame, "✏️ Обновить сумму", self.update_account_amount, width=18).pack(side=tk.LEFT, padx=0)
        StyledButton(btn_frame, "🗑️ Удалить вклад", self.delete_account, width=18).pack(side=tk.LEFT, padx=0)

        # Таблица вкладов
        accounts_frame = tk.LabelFrame(bg_frame, text="Счета и вклады", font=("Calibri", 11, "bold"),
                                       bg=COLORS['bg_header'], fg=COLORS['text'], padx=5, pady=0, relief='flat', bd=0)
        accounts_frame.pack(fill=tk.X, padx=15, pady=(0, 0))

        columns = ('name', 'type', 'amount', 'rate', 'maturity', 'notes')
        self.accounts_tree = ttk.Treeview(accounts_frame, columns=columns, show='headings', height=3)

        self.accounts_tree.heading('name', text='Название')
        self.accounts_tree.heading('type', text='Тип')
        self.accounts_tree.heading('amount', text='Текущая сумма (₽)')
        self.accounts_tree.heading('rate', text='Ставка (%)')
        self.accounts_tree.heading('maturity', text='Дата погашения')
        self.accounts_tree.heading('notes', text='Примечания')

        self.accounts_tree.column('name', width=150, anchor='center')
        self.accounts_tree.column('type', width=120, anchor='center')
        self.accounts_tree.column('amount', width=150, anchor='center')
        self.accounts_tree.column('rate', width=100, anchor='center')
        self.accounts_tree.column('maturity', width=120, anchor='center')
        self.accounts_tree.column('notes', width=200, anchor='center')

        self.accounts_tree.pack(fill=tk.BOTH, expand=True)
        self.configure_tree_style(self.accounts_tree)

        # Таблица выплат по вкладам
        payments_frame = tk.LabelFrame(bg_frame, text="Выплаты процентов", font=("Calibri", 11, "bold"),
                                       bg=COLORS['bg_header'], fg=COLORS['text'], padx=5, pady=0, relief='flat', bd=0)
        payments_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 0))

        columns_payments = ('account', 'date', 'amount')
        self.payments_tree = ttk.Treeview(payments_frame, columns=columns_payments, show='headings', height=8)

        self.payments_tree.heading('account', text='Счет')
        self.payments_tree.heading('date', text='Дата')
        self.payments_tree.heading('amount', text='Сумма (₽)')

        self.payments_tree.column('account', width=200, anchor='center')
        self.payments_tree.column('date', width=150, anchor='center')
        self.payments_tree.column('amount', width=150, anchor='center')

        self.payments_tree.pack(fill=tk.BOTH, expand=True)
        self.configure_tree_style(self.payments_tree)

        # Загружаем данные
        self.load_deposits_data()

    def create_widgets(self):
        # Верхняя с кнопками функций (заголовок)
        self.header_frame = tk.Frame(self.root, bg=COLORS['bg_header'], height=65)
        self.header_frame.pack(fill=tk.X)
        self.header_frame.pack_propagate(False)

        separator = tk.Frame(self.root, bg=COLORS['text'], height=1)
        separator.pack(fill=tk.X)

        title_label = tk.Label(
            self.header_frame, text="Инвестиционный портфель",
            font=("Calibri", 16, "bold"), bg=COLORS['bg_header'],
            fg=COLORS['text']
        )
        title_label.place(x=20, y=17)

        btn_frame = tk.Frame(self.header_frame, bg=COLORS['bg_header'])
        btn_frame.place(relx=1.0, x=0, y=0, anchor='ne')

        btn_row1 = tk.Frame(btn_frame, bg=COLORS['bg_header'])
        btn_row1.pack(anchor='e')

        btn_row2 = tk.Frame(btn_frame, bg=COLORS['bg_header'])
        btn_row2.pack(anchor='e')

        # Верхний ряд кнопок
        buttons_row1 = [
            ("Пополнение", self.add_deposit),
            ("Покупка акций", lambda: self.add_trade('stock', 'buy')),
            ("Покупка облигаций", lambda: self.add_trade('bond', 'buy')),
            ("Дивиденды", lambda: self.add_income('dividend')),
            ("Купоны", lambda: self.add_income('coupon')),
            ("Графики", self.show_charts),
        ]

        # Нижний ряд кнопок
        buttons_row2 = [
            ("Продажа акций", lambda: self.add_trade('stock', 'sell')),
            ("Погашение облигаций", self.add_redemption),
            ("Продажа облигаций", lambda: self.add_trade('bond', 'sell')),
            ("Обновить цены", self.refresh_prices),
            ("Автообновление", self.toggle_auto_update),
            ("Налоговый вычет", self.add_tax_refund),
            ("Настройки", self.open_settings),
        ]

        for text, cmd in buttons_row1:
            btn = StyledButton(btn_row1, text, cmd, width=16)
            btn.pack(side=tk.LEFT, padx=2)

        for text, cmd in buttons_row2:
            btn = StyledButton(btn_row2, text, cmd, width=16)
            btn.pack(side=tk.LEFT, padx=2)

        # Вкладки
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background=COLORS['bg_header'], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS['bg_header'],
                        foreground=COLORS['text'], padding=[25, 6],
                        font=("Calibri", 9))
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS['accent'])],
                  foreground=[("selected", "white")],
                  padding=[("selected", [25, 6])])
        style.configure(
            "green.Horizontal.TProgressbar",
            troughcolor=COLORS['bg_header'],
            background=COLORS['accent'],
            bordercolor=COLORS['bg_header'],
            lightcolor=COLORS['accent'],
            darkcolor=COLORS['accent'],
        )

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.create_summary_tab()   # ← Вкладка "Сводная"
        self.create_stocks_tab()    # ← Вкладка "Акции"
        self.create_bonds_tab()     # ← Вкладка "Облигации"
        self.create_dividends_tab() # ← Вкладка "Дивиденды"
        self.create_coupons_tab()   # ← Вкладка "Купоны"
        self.create_deposits_tab()  # ← Вкладка "Пополнения"
        self.create_deposits_accounts_tab()  # ← Вкладка "Вклады"
        self.create_history_tab()   # ← Вкладка "История портфеля"
        self.create_cashflow_tab()  # ← Вкладка "Денежный поток"
        self.create_achievements_tab()  # ← Вкладка "Достижения"
        self.create_fundamentals_tab()  # ← Вкладка "Мультипликаторы"

        # Статусная строка
        self.status_bar = tk.Frame(self.root, bg=COLORS['bg_header'], height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = tk.Label(
            self.status_bar, text="Готово", font=("Calibri", 9),
            bg=COLORS['bg_header'], fg=COLORS['text_secondary'], anchor='w'
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=3)

    def configure_tree_style(self, tree):
        style = ttk.Style()
        style.configure("Treeview",
                        background=COLORS['table_odd'],
                        foreground=COLORS['text'],
                        fieldbackground=COLORS['table_odd'],
                        rowheight=28,
                        font=("Calibri", 9),
                        borderwidth=0,
                        relief='flat',
                        show='tree headings')
        style.configure("Treeview.Heading",
                        background=COLORS['table_header'],
                        foreground=COLORS['text'],
                        font=("Calibri", 9, "bold"),
                        borderwidth=0,
                        relief='flat')
        style.map("Treeview.Heading",
                  background=[('active', COLORS['accent_light'])])

        tree.tag_configure('evenrow', background=COLORS['table_even'])
        tree.tag_configure('oddrow', background=COLORS['table_odd'])
        tree.tag_configure('positive', foreground=COLORS['success'], font=('Calibri', 9, 'bold'))
        tree.tag_configure('negative', foreground=COLORS['danger'], font=('Calibri', 9, 'bold'))
        tree.tag_configure('deviation_positive', foreground=COLORS['success'])
        tree.tag_configure('deviation_negative', foreground=COLORS['danger'])

    def create_summary_tab(self):
        '''Создание вкладки "Сводная"'''
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Сводная")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        # Карточки
        cards_frame = tk.Frame(bg_frame, bg=COLORS['table_header'])
        cards_frame.pack(fill=tk.X, padx=15, pady=(15, 5))

        self.total_deposits_var = tk.StringVar(value="0 ₽")
        self.total_portfolio_value_var = tk.StringVar(value="0 ₽")  # ← ПЕРЕИМЕНОВАЛ
        self.total_value_with_deposits_var = tk.StringVar(value="0 ₽")  # ← НОВАЯ
        self.total_profit_var = tk.StringVar(value="0 ₽")
        self.total_profit_pct_var = tk.StringVar(value="0%")
        self.fair_value_var = tk.StringVar(value="0 ₽")
        self.xirr_var = tk.StringVar(value="0%")

        cards = [
            ("Всего пополнено", self.total_deposits_var, COLORS['info']),
            ("Текущая стоимость БС", self.total_portfolio_value_var, COLORS['success']),  # ← ПЕРЕИМЕНОВАЛ
            ("Текущая стоимость", self.total_value_with_deposits_var, COLORS['accent']),  # ← НОВАЯ
            ("Общая прибыль", self.total_profit_var, COLORS['warning']),
            ("Доходность", self.total_profit_pct_var, COLORS['info']),
            ("Справедливая оценка", self.fair_value_var, '#ce93d8'),
            ("Среднегодовая (XIRR)", self.xirr_var, '#b39ddb'),
        ]

        for title, var, color in cards:
            card = tk.Frame(cards_frame, bg=color, relief=tk.FLAT, padx=5, pady=3, width=160, height=55)
            card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
            card.pack_propagate(False)

            tk.Label(card, text=title, font=("Calibri", 9),
                     bg=color, fg="white").pack()
            tk.Label(card, textvariable=var, font=("Calibri", 16, "bold"),
                     bg=color, fg="white").pack()

        # Таблица
        columns = ('name', 'ticker', 'type', 'quantity', 'avg_price', 'current_price',
                   'total_cost', 'current_value', 'profit', 'profit_pct', 'share', 'target_share', 'deviation',
                   'to_buy', 'fair_price', 'upside', 'fair_value')
        self.summary_tree = ttk.Treeview(bg_frame, columns=columns, show='headings', height=8)

        headings = {
            'name': 'Название', 'ticker': 'Тикер', 'type': 'Тип', 'quantity': 'Кол-во',
            'avg_price': 'Ср.цена', 'current_price': 'Текущая',
            'total_cost': 'Затраты', 'current_value': 'Стоимость',
            'profit': 'Прибыль', 'profit_pct': 'Доходность',
            'share': 'Доля', 'target_share': 'Цель', 'deviation': 'Отклонение', 'to_buy': 'Докупить',
            'fair_price': 'Справед. цена', 'upside': 'Потенциал', 'fair_value': 'Справед. стоимость'
        }

        for col, title in headings.items():
            self.summary_tree.heading(col, text=title)
            self.summary_tree.column(col, width=80, anchor='center')

        self.summary_tree.column('name', width=100)
        self.summary_tree.column('ticker', width=60)
        self.summary_tree.column('type', width=60)
        self.summary_tree.column('quantity', width=60)
        self.summary_tree.column('deviation', width=70)
        self.summary_tree.column('to_buy', width=70)

        self.summary_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 5))

        self.configure_tree_style(self.summary_tree)

        # Нижняя статистика
        stats_bottom_frame = tk.Frame(bg_frame, bg=COLORS['bg_main'])
        stats_bottom_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        self.summary_stats_left = tk.Label(
            stats_bottom_frame, text="",
            font=("Calibri", 9),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary'],
            justify=tk.LEFT
        )
        self.summary_stats_left.pack(side=tk.LEFT)

        self.summary_stats_right = tk.Label(
            stats_bottom_frame, text="",
            font=("Calibri", 9),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary'],
            justify=tk.RIGHT
        )
        self.summary_stats_right.pack(side=tk.RIGHT)

    def create_stocks_tab(self):
        '''Создание вкладки "Акции"'''
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Акции")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('name', 'ticker', 'quantity', 'avg_price', 'current_price', 'total_cost',
                   'current_value', 'profit', 'profit_pct', 'profit_with_div', 'profit_pct_with_div',
                   'share', 'target_share', 'deviation', 'to_buy', 'fair_price', 'upside', 'fair_value')
        self.stocks_tree = ttk.Treeview(bg_frame, columns=columns, show='headings', height=15)

        headings = {
            'name': 'Название', 'ticker': 'Тикер', 'quantity': 'Кол-во', 'avg_price': 'Ср.цена',
            'current_price': 'Текущая', 'total_cost': 'Затраты',
            'current_value': 'Стоимость', 'profit': 'Прибыль',
            'profit_pct': 'Доходность', 'profit_with_div': 'Прибыль с див.',
            'profit_pct_with_div': 'Доходность с див.', 'share': 'Доля',
            'target_share': 'Цель', 'deviation': 'Отклонение', 'to_buy': 'Докупить',
            'fair_price': 'Справед. цена', 'upside': 'Потенциал', 'fair_value': 'Справед. стоимость'
        }

        for col, title in headings.items():
            self.stocks_tree.heading(col, text=title)
            self.stocks_tree.column(col, width=90, anchor='center')

        self.stocks_tree.column('name', width=110)
        self.stocks_tree.column('ticker', width=70)
        self.stocks_tree.column('profit_with_div', width=100)
        self.stocks_tree.column('profit_pct_with_div', width=100)
        self.stocks_tree.column('to_buy', width=70)

        self.stocks_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 5))
        self.configure_tree_style(self.stocks_tree)

        # Нижняя статистика
        stats_bottom_frame = tk.Frame(bg_frame, bg=COLORS['bg_main'])
        stats_bottom_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        self.stocks_stats_left = tk.Label(
            stats_bottom_frame, text="",
            font=("Calibri", 9),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary'],
            justify=tk.LEFT
        )
        self.stocks_stats_left.pack(side=tk.LEFT)

        self.stocks_stats_right = tk.Label(
            stats_bottom_frame, text="",
            font=("Calibri", 9),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary'],
            justify=tk.RIGHT
        )
        self.stocks_stats_right.pack(side=tk.RIGHT)

    def create_bonds_tab(self):
        '''Создание вкладки "Облигации"'''
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Облигации")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('name', 'ticker', 'quantity', 'avg_price_rub', 'avg_price_percent',
                   'current_price_rub', 'current_price_percent',
                   'total_cost', 'current_value', 'profit', 'profit_pct',
                   'profit_with_coupon', 'profit_pct_with_coupon',
                   'share', 'target_share', 'deviation', 'to_buy')
        self.bonds_tree = ttk.Treeview(bg_frame, columns=columns, show='headings', height=12)

        headings = {
            'name': 'Название',
            'ticker': 'Тикер',
            'quantity': 'Кол-во',
            'avg_price_rub': 'Ср.цена (₽)',
            'avg_price_percent': 'Ср.цена (%)',
            'current_price_rub': 'Текущая (₽)',
            'current_price_percent': 'Текущая (%)',
            'total_cost': 'Затраты (₽)',
            'current_value': 'Стоимость (₽)',
            'profit': 'Прибыль (₽)',
            'profit_pct': 'Доходность',
            'profit_with_coupon': 'Прибыль с куп.',
            'profit_pct_with_coupon': 'Доходность с куп.',
            'share': 'Доля',
            'target_share': 'Цель',
            'deviation': 'Отклонение',
            'to_buy': 'Докупить'
        }

        for col, title in headings.items():
            self.bonds_tree.heading(col, text=title)
            self.bonds_tree.column(col, width=80, anchor='center')

        self.bonds_tree.column('name', width=110)
        self.bonds_tree.column('ticker', width=70)
        self.bonds_tree.column('profit_with_coupon', width=100)
        self.bonds_tree.column('profit_pct_with_coupon', width=100)
        self.bonds_tree.column('to_buy', width=70)

        self.bonds_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=(20, 5))
        self.configure_tree_style(self.bonds_tree)

        # Нижняя статистика
        stats_bottom_frame = tk.Frame(bg_frame, bg=COLORS['bg_main'])
        stats_bottom_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        self.bonds_stats_left = tk.Label(
            stats_bottom_frame, text="",
            font=("Calibri", 9),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary'],
            justify=tk.LEFT
        )
        self.bonds_stats_left.pack(side=tk.LEFT)

        self.bonds_stats_right = tk.Label(
            stats_bottom_frame, text="",
            font=("Calibri", 9),
            bg=COLORS['bg_main'], fg=COLORS['text_secondary'],
            justify=tk.RIGHT
        )
        self.bonds_stats_right.pack(side=tk.RIGHT)

    def create_deposits_tab(self):
        '''Создание вкладки с пополнениями и налоговыми вычетами "Поступления"'''
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Пополнения")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        # Основной контейнер с двумя таблицами
        main_frame = tk.Frame(bg_frame, bg=COLORS['bg_header'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Левая таблица "Пополнения"
        left_frame = tk.LabelFrame(main_frame, text="Пополнения",
                                   font=("Calibri", 11, "bold"),
                                   bg=COLORS['bg_header'], fg=COLORS['text'],
                                   padx=5, pady=5, relief='flat', bd=0)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Создание пустого фрейма над таблицей "Пополнения" (для выравнивания таблиц)
        spacer_frame = tk.Frame(left_frame, bg=COLORS['bg_header'], height=36)
        spacer_frame.pack(fill=tk.X, pady=(0, 0))
        spacer_frame.pack_propagate(False)

        columns = ('date', 'amount')
        self.deposits_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=10)

        self.deposits_tree.heading('date', text='Дата')
        self.deposits_tree.heading('amount', text='Сумма (₽)')

        self.deposits_tree.column('date', width=120, anchor='center')
        self.deposits_tree.column('amount', width=130, anchor='center')

        self.deposits_tree.pack(fill=tk.BOTH, expand=True)

        self.deposits_total_label = tk.Label(
            left_frame, text="", font=("Calibri", 11, "bold"),
            bg=COLORS['bg_header'], fg=COLORS['text']
        )
        self.deposits_total_label.pack(pady=(5, 0))

        self.configure_tree_style(self.deposits_tree)

        separator = tk.Frame(main_frame, bg=COLORS['text_secondary'], width=1)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Правая таблица "Налоговые вычеты"
        right_frame = tk.LabelFrame(main_frame, text="Налоговые вычеты",
                                    font=("Calibri", 11, "bold"),
                                    bg=COLORS['bg_header'], fg=COLORS['text'],
                                    padx=5, pady=5, relief='flat', bd=0)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Кнопки для вычетов
        btn_frame = tk.Frame(right_frame, bg=COLORS['bg_header'])
        btn_frame.pack(fill=tk.X, pady=(0, 5))

        StyledButton(btn_frame, "➕ Добавить", self.add_tax_deduction, width=14).pack(side=tk.LEFT, padx=0)
        StyledButton(btn_frame, "🗑️ Удалить", self.delete_tax_deduction, width=14).pack(side=tk.LEFT, padx=2)

        columns_ded = ('date', 'type', 'year', 'amount', 'description')
        self.deductions_tree = ttk.Treeview(right_frame, columns=columns_ded, show='headings', height=10)

        self.deductions_tree.heading('date', text='Дата')
        self.deductions_tree.heading('type', text='Тип вычета')
        self.deductions_tree.heading('year', text='Год')
        self.deductions_tree.heading('amount', text='Сумма (₽)')
        self.deductions_tree.heading('description', text='Описание')

        self.deductions_tree.column('date', width=90, anchor='center')
        self.deductions_tree.column('type', width=110, anchor='center')
        self.deductions_tree.column('year', width=50, anchor='center')
        self.deductions_tree.column('amount', width=100, anchor='center')
        self.deductions_tree.column('description', width=120, anchor='center')

        self.deductions_tree.pack(fill=tk.BOTH, expand=True)

        self.deductions_total_label = tk.Label(
            right_frame, text="", font=("Calibri", 11, "bold"),
            bg=COLORS['bg_header'], fg=COLORS['text']
        )
        self.deductions_total_label.pack(pady=(5, 0))

        self.configure_tree_style(self.deductions_tree)

        # Загружаем данные
        self.load_data()
        self.load_tax_deductions_data()

    def create_dividends_tab(self):
        '''Создание вкладки "Дивиденды"'''
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Дивиденды")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        table_frame = tk.Frame(bg_frame, bg=COLORS['bg_main'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        columns = ('name', 'ticker', 'date', 'quantity', 'amount', 'yield_per_share', 'yield_percent')
        self.dividends_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=19)

        self.dividends_tree.heading('name', text='Название')
        self.dividends_tree.heading('ticker', text='Тикер')
        self.dividends_tree.heading('date', text='Дата')
        self.dividends_tree.heading('quantity', text='Кол-во')
        self.dividends_tree.heading('amount', text='Сумма (₽)')
        self.dividends_tree.heading('yield_per_share', text='Доход на бумагу (₽)')
        self.dividends_tree.heading('yield_percent', text='Доходность (%)')

        self.dividends_tree.column('name', width=120, anchor='center')
        self.dividends_tree.column('ticker', width=80, anchor='center')
        self.dividends_tree.column('date', width=100, anchor='center')
        self.dividends_tree.column('quantity', width=80, anchor='center')
        self.dividends_tree.column('amount', width=110, anchor='center')
        self.dividends_tree.column('yield_per_share', width=130, anchor='center')
        self.dividends_tree.column('yield_percent', width=110, anchor='center')

        self.dividends_tree.pack(fill=tk.BOTH, expand=True)

        self.dividends_total_label = tk.Label(
            bg_frame, text="", font=("Calibri", 11, "bold"),
            bg=COLORS['bg_header'], fg=COLORS['text']
        )
        self.dividends_total_label.pack(pady=(0, 19))

        self.configure_tree_style(self.dividends_tree)

    def create_coupons_tab(self):
        '''Создание вкладки "Купоны"'''
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Купоны")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        table_frame = tk.Frame(bg_frame, bg=COLORS['bg_main'])
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        columns = ('name', 'ticker', 'date', 'quantity', 'amount', 'yield_per_share', 'yield_percent')
        self.coupons_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=19)

        self.coupons_tree.heading('name', text='Название')
        self.coupons_tree.heading('ticker', text='Тикер')
        self.coupons_tree.heading('date', text='Дата')
        self.coupons_tree.heading('quantity', text='Кол-во')
        self.coupons_tree.heading('amount', text='Сумма (₽)')
        self.coupons_tree.heading('yield_per_share', text='Доход на бумагу (₽)')
        self.coupons_tree.heading('yield_percent', text='Доходность (%)')

        self.coupons_tree.column('name', width=100, anchor='center')
        self.coupons_tree.column('ticker', width=90, anchor='center')
        self.coupons_tree.column('date', width=100, anchor='center')
        self.coupons_tree.column('quantity', width=40, anchor='center')
        self.coupons_tree.column('amount', width=110, anchor='center')
        self.coupons_tree.column('yield_per_share', width=110, anchor='center')
        self.coupons_tree.column('yield_percent', width=110, anchor='center')

        self.coupons_tree.pack(fill=tk.BOTH, expand=True)

        self.coupons_total_label = tk.Label(
            bg_frame, text="", font=("Calibri", 11, "bold"),
            bg=COLORS['bg_header'], fg=COLORS['text']
        )
        self.coupons_total_label.pack(pady=(0, 19))

        self.configure_tree_style(self.coupons_tree)

    def create_history_tab(self):
        '''Создание вкладки с графиком стоимости портфеля "История портфеля"'''
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📈 История портфеля")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        # Панель управления
        control_frame = tk.Frame(bg_frame, bg=COLORS['bg_header'])
        control_frame.pack(fill=tk.X, padx=0, pady=0)

        tk.Label(control_frame, text="Период:", font=("Calibri", 10),
                 bg=COLORS['bg_header'], fg=COLORS['text']).pack(side=tk.LEFT, padx=0)

        self.history_period = ttk.Combobox(control_frame,
                                           values=['1 месяц', '3 месяца', '6 месяцев', '1 год', 'Всё время'],
                                           width=12, state='readonly')
        self.history_period.set('1 год')
        self.history_period.pack(side=tk.LEFT, padx=5)

        self.build_btn = StyledButton(control_frame, "Построить график", self.plot_portfolio_history, width=18)
        self.build_btn.pack(side=tk.LEFT, padx=10)

        self.cache_btn = StyledButton(control_frame, "🔄 Обновить кэш", self.init_cache, width=18)
        self.cache_btn.pack(side=tk.LEFT, padx=10)

        # ← ПРОГРЕСС-БАР СПРАВА
        progress_container = tk.Frame(control_frame, bg=COLORS['bg_header'])
        progress_container.pack(side=tk.LEFT, padx=(20, 0), fill=tk.X, expand=True)

        self.progress_bar = ttk.Progressbar(
            progress_container,
            mode='determinate',
            length=200,
            maximum=100,
            style="green.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 5))

        self.progress_label = tk.Label(
            progress_container,
            text="",
            font=("Calibri", 8),
            bg=COLORS['bg_header'],
            fg=COLORS['text_secondary']
        )
        self.progress_label.pack(side=tk.LEFT)

        # Контейнер для графика
        graph_frame = tk.Frame(bg_frame, bg=COLORS['bg_main'])
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # График
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        self.history_figure = Figure(figsize=(14, 8), dpi=100, facecolor=COLORS['bg_main'])
        self.history_ax = self.history_figure.add_subplot(111)
        self.history_ax.set_facecolor(COLORS['table_odd'])
        self.history_ax.tick_params(colors=COLORS['text'])
        self.history_ax.grid(True, alpha=0.3, color=COLORS['text_secondary'])

        self.history_figure.subplots_adjust(left=0.08, right=0.95, top=0.95, bottom=0.08)

        self.history_canvas = FigureCanvasTkAgg(self.history_figure, graph_frame)
        self.history_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_fundamentals_tab(self):
        """Вкладка с фундаментальными показателями"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📊 Мультипликаторы")

        bg_frame = tk.Frame(frame, bg=COLORS['bg_main'])
        bg_frame.pack(fill=tk.BOTH, expand=True)

        # Панель с кнопкой и прогресс-баром
        control_frame = tk.Frame(bg_frame, bg=COLORS['bg_header'])
        control_frame.pack(fill=tk.X, padx=20, pady=(10, 5))

        StyledButton(control_frame, "🔄 Обновить данные",
                     lambda: self.update_fundamentals(), width=20).pack(side=tk.LEFT)

        tk.Label(control_frame, text="Данные со Smart-lab.ru", font=("Calibri", 8),
                 bg=COLORS['bg_header'], fg=COLORS['text_secondary']).pack(side=tk.RIGHT)

        # Прогресс-бар
        progress_container = tk.Frame(control_frame, bg=COLORS['bg_header'])
        progress_container.pack(side=tk.LEFT, padx=(20, 0), fill=tk.X, expand=True)

        self.fund_progress_bar = ttk.Progressbar(
            progress_container, mode='determinate', length=200, maximum=100,
            style="green.Horizontal.TProgressbar"
        )
        self.fund_progress_bar.pack(side=tk.LEFT, padx=(0, 5))

        self.fund_progress_label = tk.Label(
            progress_container, text="", font=("Calibri", 8),
            bg=COLORS['bg_header'], fg=COLORS['text_secondary']
        )
        self.fund_progress_label.pack(side=tk.LEFT)

        # Таблица 1: Обычные компании
        columns1 = ('ticker', 'name', 'pe', 'pb', 'ps', 'evebitda', 'ev_s',
                    'debt_ebitda', 'net_debt_ebitda', 'roe', 'net_margin',
                    'ebitda_margin', 'market_cap', 'report')
        self.fund_tree1 = ttk.Treeview(bg_frame, columns=columns1, show='headings', height=17)

        headers1 = {
            'ticker': 'Тикер', 'name': 'Название',
            'pe': 'P/E', 'pb': 'P/B', 'ps': 'P/S',
            'evebitda': 'EV/EBITDA', 'ev_s': 'EV/S',
            'debt_ebitda': 'Долг/EBITDA', 'net_debt_ebitda': 'Чист.долг/EBITDA',
            'roe': 'ROE %', 'net_margin': 'Чистая маржа %',
            'ebitda_margin': 'EBITDA маржа %', 'market_cap': 'Капит., млрд',
            'report': 'Отчет'
        }

        for col, title in headers1.items():
            self.fund_tree1.heading(col, text=title)
            self.fund_tree1.column(col, width=85, anchor='center')
        self.fund_tree1.column('name', width=130)
        self.fund_tree1.column('report', width=85)

        self.fund_tree1.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 5))

        # Таблица 2: Банки
        columns2 = ('ticker', 'name', 'pe', 'pb', 'roe', 'roa', 'net_margin', 'market_cap', 'report')
        self.fund_tree2 = ttk.Treeview(bg_frame, columns=columns2, show='headings', height=2)

        headers2 = {
            'ticker': 'Тикер', 'name': 'Название',
            'pe': 'P/E', 'pb': 'P/B', 'roe': 'ROE %', 'roa': 'ROA %',
            'net_margin': 'Чистая маржа %', 'market_cap': 'Капит., млрд',
            'report': 'Отчет'
        }

        for col, title in headers2.items():
            self.fund_tree2.heading(col, text=title)
            self.fund_tree2.column(col, width=85, anchor='center')
        self.fund_tree2.column('name', width=130)
        self.fund_tree2.column('report', width=85)

        self.fund_tree2.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 20))

        # Загружаем данные
        self.load_fundamentals_data()

        def on_double_click(event, tree=self.fund_tree1):
            item = tree.selection()
            if item:
                values = tree.item(item[0], 'values')
                ticker = values[0]
                self.show_fundamental_detail(ticker)

        self.fund_tree1.bind('<Double-1>', on_double_click)
        self.fund_tree2.bind('<Double-1>', lambda e: on_double_click(e, self.fund_tree2))
        self.configure_tree_style(self.fund_tree1)
        self.configure_tree_style(self.fund_tree2)

    def show_fundamental_detail(self, ticker):
        """Показывает модальное окно с историей мультипликаторов по годам"""
        from DB.db_config import create_connection
        from config import TICKER_NAMES
        import json

        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute("SELECT msfo_history FROM stock_fundamentals WHERE ticker = %s", (ticker,))
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            messagebox.showinfo("Нет данных", f"Нет исторических данных МСФО для {ticker}")
            return

        name = TICKER_NAMES.get(ticker, ticker)

        try:
            data = json.loads(row[0])
        except:
            messagebox.showerror("Ошибка", "Не удалось загрузить данные МСФО")
            return

        years = data.get('years', [])
        indicators = data.get('indicators', {})

        if not years or not indicators:
            messagebox.showinfo("Нет данных", "Пустые данные МСФО")
            return

        full_years = [y for y in years if 'LTM' not in y.upper() and '?' not in y]
        ltm_years = [y for y in years if 'LTM' in y.upper() or '?' in y]
        display_years = full_years + ltm_years

        skip_fields = [
            'IR рейтинг', 'Качество фин.отчетности', 'Презентации для инвесторов',
            'Присутствие на смартлабе', 'Годовой отчет', 'Сайт для инвесторов',
            'Календарь инвесторов', 'Обратная связь',
        ]

        tooltips = {
            'P/E': 'Цена/Прибыль — за сколько лет окупится акция (чем ниже, тем дешевле)',
            'P/B': 'Цена/Балансовая стоимость — оценка относительно активов',
            'P/S': 'Цена/Выручка — сколько платишь за 1₽ выручки',
            'EV/EBITDA': 'Стоимость компании / Прибыль до вычетов',
            'ROE': 'Рентабельность капитала — прибыль на 1₽ собственных средств (чем выше, тем лучше)',
            'ROA': 'Рентабельность активов — эффективность использования имущества',
            'ROIC': 'Рентабельность инвестированного капитала',
            'ROCE': 'Рентабельность задействованного капитала',
            'Чистая прибыль,млрд руб': 'Прибыль после всех расходов, налогов и процентов',
            'Выручка,млрд руб': 'Общая сумма денег от продаж за отчётный период',
            'EBITDA,млрд руб': 'Прибыль до вычета процентов, налогов и амортизации',
            'Чистая маржа': 'Сколько копеек чистой прибыли с 1₽ выручки',
            'Операционная маржа': 'Прибыль от основной деятельности в % от выручки',
            'EBITDA маржа': 'Операционная прибыль в % от выручки',
            'D/E': 'Долг/Собственный капитал — уровень закредитованности',
            'Долг/EBITDA': 'За сколько лет компания расплатится с долгами',
            'Чистый долг/EBITDA': 'Долг минус деньги, делённый на EBITDA',
            'P/FCF': 'Цена/Свободный денежный поток',
            'P/CF': 'Цена/Денежный поток',
            'Капитализация,млрд руб': 'Рыночная стоимость компании',
            'EV,млрд руб': 'Стоимость компании с учётом долга',
            'EPS,руб': 'Прибыль на акцию',
            'FCF,млрд руб': 'Свободный денежный поток',
            'EBIT,млрд руб': 'Прибыль до вычета процентов и налогов',
        }

        # Показатели где "чем выше, тем лучше"
        higher_better = ['ROE', 'ROA', 'ROIC', 'ROCE', 'Чистая прибыль,млрд руб',
                         'Выручка,млрд руб', 'EBITDA,млрд руб', 'EBIT,млрд руб',
                         'FCF,млрд руб', 'EPS,руб', 'Чистая маржа', 'Операционная маржа',
                         'EBITDA маржа', 'Капитализация,млрд руб', 'EV,млрд руб',
                         'Див доход, ао,%']

        win = tk.Toplevel(self.root)
        win.title(f"{name} ({ticker}) — МСФО по годам")
        win.geometry("870x650")
        win.transient(self.root)
        win.grab_set()
        win.configure(bg=COLORS['bg_main'])

        tk.Label(win, text=f"{name} ({ticker})", font=("Calibri", 14, "bold"),
                 bg=COLORS['bg_main'], fg=COLORS['accent']).pack(pady=(15, 5))

        tree_frame = tk.Frame(win, bg=COLORS['bg_main'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))

        columns = ('indicator',) + tuple(display_years) + ('avg',)
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=25)

        tree.heading('indicator', text='Показатель')
        tree.column('indicator', width=200, anchor='w')

        for year in display_years:
            tree.heading(year, text=year)
            tree.column(year, width=85, anchor='center')

        tree.heading('avg', text='Среднее')
        tree.column('avg', width=90, anchor='center')

        tree.pack(fill=tk.BOTH, expand=True)

        def on_double_click(event):
            region = tree.identify_region(event.x, event.y)
            if region == 'cell':
                column = tree.identify_column(event.x)
                item = tree.identify_row(event.y)
                if column == '#1' and item:
                    values = tree.item(item, 'values')
                    indicator_name = values[0]
                    # Берём данные КОНКРЕТНОГО показателя из indicators
                    if indicator_name in indicators:
                        self.show_multiplier_chart(ticker, name, indicator_name, full_years, ltm_years,
                                                   indicators[indicator_name], higher_better)

        tree.bind('<Double-1>', on_double_click)

        tree.tag_configure('evenrow', background=COLORS['table_even'])
        tree.tag_configure('oddrow', background=COLORS['table_odd'])

        for indicator_name, year_values in indicators.items():
            if indicator_name in skip_fields:
                continue

            values = [indicator_name]
            numeric_full_years = []

            for year in full_years:
                val = year_values.get(year)
                if val is not None:
                    numeric_full_years.append(val)
                    if abs(val) >= 1000:
                        values.append(f"{val:,.0f}")
                    elif abs(val) >= 100:
                        values.append(f"{val:.1f}")
                    elif abs(val) >= 1:
                        values.append(f"{val:.2f}")
                    else:
                        values.append(f"{val:.4f}")
                else:
                    values.append("-")

            for year in ltm_years:
                val = year_values.get(year)
                if val is not None:
                    if abs(val) >= 1000:
                        values.append(f"{val:,.0f}")
                    elif abs(val) >= 100:
                        values.append(f"{val:.1f}")
                    elif abs(val) >= 1:
                        values.append(f"{val:.2f}")
                    else:
                        values.append(f"{val:.4f}")
                else:
                    values.append("-")

            # Среднее
            if numeric_full_years:
                avg_val = sum(numeric_full_years) / len(numeric_full_years)

                ltm_val = year_values.get(ltm_years[0]) if ltm_years else None

                if ltm_val is not None and avg_val != 0:
                    if indicator_name in higher_better:
                        is_good = ltm_val > avg_val
                    else:
                        is_good = ltm_val < avg_val
                else:
                    is_good = None

                # Форматируем значение
                if abs(avg_val) >= 1000:
                    val_str = f"{avg_val:,.0f}"
                elif abs(avg_val) >= 100:
                    val_str = f"{avg_val:.1f}"
                elif abs(avg_val) >= 1:
                    val_str = f"{avg_val:.2f}"
                else:
                    val_str = f"{avg_val:.4f}"

                # Добавляем индикатор
                if is_good is True:
                    values.append(f"▲ {val_str}")  # зелёный треугольник вверх
                elif is_good is False:
                    values.append(f"▼ {val_str}")  # красный треугольник вниз
                else:
                    values.append(f"● {val_str}")  # серый круг
            else:
                values.append("—")

            tree.insert('', tk.END, values=values)

        # Чередование цветов строк
        for i, item in enumerate(tree.get_children()):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.item(item, tags=(tag,))

        # Обработчик двойного клика по показателю


        # Подсказки при наведении
        def on_motion(event):
            region = tree.identify_region(event.x, event.y)
            if region == 'cell':
                column = tree.identify_column(event.x)
                item = tree.identify_row(event.y)
                if column == '#1':
                    values = tree.item(item, 'values')
                    indicator = values[0]
                    tip = tooltips.get(indicator, '')
                    if tip:
                        show_tooltip_window(tree, tip, event.x_root, event.y_root)
                else:
                    hide_tooltip()
            else:
                hide_tooltip()

        tree.bind('<Motion>', on_motion)
        tree.bind('<Leave>', lambda e: hide_tooltip())

        tk.Button(win, text="Закрыть", command=win.destroy,
                  bg=COLORS['bg_header'], fg=COLORS['text'], font=("Calibri", 10),
                  relief="flat", padx=25, pady=8, cursor="hand2").pack(pady=(0, 15))

    def show_tooltip_text(widget, text):
        """Показывает всплывающую подсказку"""
        global _tooltip_window
        hide_tooltip()
        x = widget.winfo_rootx() + widget.winfo_width() + 10
        y = widget.winfo_rooty()
        _tooltip_window = tk.Toplevel(widget)
        _tooltip_window.wm_overrideredirect(True)
        _tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(_tooltip_window, text=text, background="#ffffcc",
                         relief="solid", borderwidth=1, font=("Calibri", 9),
                         wraplength=250, padx=5, pady=3)
        label.pack()

    def load_fundamentals_data(self):
        """Загружает фундаментальные данные в две таблицы"""
        for tree in [self.fund_tree1, self.fund_tree2]:
            for item in tree.get_children():
                tree.delete(item)

        from DB.db_config import create_connection
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute("SELECT * FROM stock_fundamentals ORDER BY ticker")
            rows = cursor.fetchall()

            from config import STOCKS, TICKER_NAMES
            ticker_order = {t: i for i, t in enumerate(STOCKS)}
            rows.sort(key=lambda r: ticker_order.get(r[0], 999))

            count1 = 0  # Счётчик для обычных компаний
            count2 = 0  # Счётчик для банков

            for row in rows:
                ticker = row[0]
                name = TICKER_NAMES.get(ticker, ticker)
                company_type = row[32] if len(row) > 32 and row[32] else 'industrial'

                if company_type == 'bank':
                    tag = 'evenrow' if count2 % 2 == 0 else 'oddrow'
                    count2 += 1
                    self.fund_tree2.insert('', tk.END, values=(
                        ticker, name,
                        f"{float(row[11]):.1f}" if row[11] else '-',
                        f"{float(row[12]):.2f}" if row[12] else '-',
                        f"{float(row[24]):.1f}%" if row[24] else '-',
                        f"{float(row[25]):.1f}%" if row[25] else '-',
                        f"{float(row[28]):.1f}%" if row[28] else '-',
                        f"{float(row[1]):,.0f}" if row[1] else '-',
                        row[31] if len(row) > 31 and row[31] else '-',
                    ), tags=(tag,))
                else:
                    tag = 'evenrow' if count1 % 2 == 0 else 'oddrow'
                    count1 += 1
                    self.fund_tree1.insert('', tk.END, values=(
                        ticker, name,
                        f"{float(row[11]):.1f}" if row[11] else '-',
                        f"{float(row[12]):.2f}" if row[12] else '-',
                        f"{float(row[13]):.2f}" if row[13] else '-',
                        f"{float(row[17]):.1f}" if row[17] else '-',
                        f"{float(row[16]):.2f}" if row[16] else '-',
                        f"{float(row[20]):.2f}" if row[20] else '-',
                        f"{float(row[21]):.2f}" if row[21] else '-',
                        f"{float(row[24]):.1f}%" if row[24] else '-',
                        f"{float(row[28]):.1f}%" if row[28] else '-',
                        f"{float(row[30]):.1f}%" if row[30] else '-',
                        f"{float(row[1]):,.0f}" if row[1] else '-',
                        row[31] if len(row) > 31 and row[31] else '-',
                    ), tags=(tag,))
            conn.close()

    def update_fundamentals(self):
        """Обновляет фундаментальные показатели со Smart-lab"""

        self.fund_progress_bar['value'] = 0
        self.fund_progress_label.config(text="0%")
        self.status_label.config(text="Загрузка данных со Smart-lab...")
        self.root.update()

        def run():
            from fair_price import get_all_msfo_data

            # Обновляем прогресс
            total = len(self.stocks)
            self.root.after(0, lambda: self.fund_progress_label.config(text=f"0/{total}"))

            # Загружаем МСФО данные
            get_all_msfo_data(self.stocks)

            # Обновляем интерфейс
            self.root.after(0, lambda: self.fund_progress_bar.configure(value=100))
            self.root.after(0, lambda: self.fund_progress_label.config(text=f"{total}/{total}"))
            self.root.after(0, lambda: self.status_label.config(text="Мультипликаторы обновлены!"))
            self.root.after(0, lambda: self.load_fundamentals_data())

        threading.Thread(target=run, daemon=True).start()

    def init_cache(self):
        """Инициализация кэша исторических цен"""
        from history_cache import STOCKS, BONDS, INDEX_TICKER, ensure_prices_cached, ensure_index_cached
        from datetime import datetime

        all_tickers = STOCKS + BONDS + [INDEX_TICKER]
        total = len(all_tickers)

        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = total
        self.progress_label.config(text=f"0/{total}")
        self.status_label.config(text="Инициализация кэша...")
        self.root.update()

        def run_init():
            start = datetime(2023, 6, 30).date()
            end = datetime.now().date()

            for i, ticker in enumerate(all_tickers, 1):
                if ticker == INDEX_TICKER:
                    ensure_index_cached(ticker, start, end, force_refresh=True)
                else:
                    security_type = 'stock' if ticker in STOCKS else 'bond'
                    ensure_prices_cached(ticker, security_type, start, end, force_refresh=True)

                # Обновляем прогресс
                progress = int(i / total * 100)
                self.root.after(0, lambda v=progress, c=i: self._update_progress(v, c, total))

            self.root.after(0, lambda: self.progress_label.config(text="Готово"))
            self.root.after(0, lambda: self.status_label.config(text="Кэш исторических цен обновлен!"))

        threading.Thread(target=run_init, daemon=True).start()

    def _update_progress(self, value, current, total):
        """Обновляет прогресс-бар"""
        self.progress_bar['value'] = current
        self.progress_label.config(text=f"{current}/{total}")
        self.root.update_idletasks()

    def plot_portfolio_history(self):
        '''Построение графика исторической стоимости портфеля и индекса'''
        from DB.database import get_portfolio_history
        from history_cache import ensure_index_cached, get_prices_from_cache
        from DB.db_config import create_connection
        from datetime import timedelta, datetime
        import pandas as pd

        INDEX_TICKER = 'MCFTR'

        period_map = {
            '1 месяц': 30, '3 месяца': 90, '6 месяцев': 180, '1 год': 365
        }
        period = self.history_period.get()

        if period == 'Всё время':
            start_date = datetime(2023, 6, 30)
        else:
            days = period_map.get(period, 365)
            start_date = datetime.now() - timedelta(days=days)

        end_date = datetime.now()

        self.status_label.config(text="Загрузка исторических данных...")
        self.root.update()

        def load_and_plot():
            # 1. История портфеля
            self.root.after(0, lambda: self.progress_bar.start())
            self.root.after(0, lambda: self.progress_label.config(text="Загрузка данных..."))

            history_df = get_portfolio_history(start_date, end_date)
            if history_df is None or history_df.empty:
                self.root.after(0, lambda: self._update_history_plot(None, None))
                return

            # 2. Бенчмарк: индекс MCFTR
            ensure_index_cached(INDEX_TICKER, start_date.date(), end_date.date())
            benchmark_df = get_prices_from_cache(INDEX_TICKER, start_date.date(), end_date.date())

            # 3. Пополнения
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute("SELECT date, amount FROM deposits WHERE date >= %s AND date <= %s ORDER BY date",
                           (start_date, end_date))
            deposits = cursor.fetchall()

            conn.close()

            try:
                inflation_yoy = get_inflation_yoy(from_year=2023)
            except Exception as e:
                print(f"Не удалось загрузить инфляцию ЦБ: {e}")
                inflation_yoy = {}

            deposits_dict = {pd.to_datetime(d[0]): float(d[1]) for d in deposits}
            history_df['date'] = pd.to_datetime(history_df['date'])
            merged = history_df[['date', 'value']].copy()

            # 5. Симуляция индексного портфеля
            if benchmark_df is not None and not benchmark_df.empty:
                benchmark_df['date'] = pd.to_datetime(benchmark_df['date'])
                benchmark_df = benchmark_df.sort_values('date')
                benchmark_df['close'] = benchmark_df['close'].ffill().bfill()

                merged = pd.merge(merged, benchmark_df, on='date', how='left')
                merged['close'] = merged['close'].ffill().bfill()

                first_valid_idx = merged['close'].first_valid_index()
                if first_valid_idx is not None:
                    first_price = float(merged.loc[first_valid_idx, 'close'])
                    initial_value = float(merged.loc[first_valid_idx, 'value'])
                    index_units = initial_value / first_price if first_price > 0 else 0

                    index_values = []
                    for _, row in merged.iterrows():
                        price = float(row['close'])
                        if pd.notna(price) and price > 0:
                            if row['date'] in deposits_dict:
                                index_units += deposits_dict[row['date']] / price
                            index_values.append(index_units * price)
                        else:
                            index_values.append(index_values[-1] if index_values else 0)
                    merged['index_value'] = index_values
                else:
                    merged['index_value'] = merged['value']
            else:
                merged['index_value'] = merged['value']

            # Пополнения, проиндексированные официальной инфляцией ЦБ (г/г → месячный эквивалент)
            if inflation_yoy and deposits_dict:
                merged['inflated_value'] = inflation_adjusted_deposits(
                    merged['date'], deposits_dict, inflation_yoy
                )
            else:
                merged['inflated_value'] = None

            self.root.after(0, lambda: self.progress_bar.stop())
            self.root.after(0, lambda: self.progress_label.config(text="Готово"))
            self.root.after(0, lambda: self._update_history_plot(history_df, merged))
        threading.Thread(target=load_and_plot, daemon=True).start()

    # main.py
    def _update_history_plot(self, history_df, index_df):
        """Обновление графика с реальным и индексным портфелем"""
        self.history_ax.clear()
        self.history_ax.set_facecolor(COLORS['table_odd'])

        if history_df is not None and not history_df.empty:
            # Портфель
            self.history_ax.plot(history_df['date'], history_df['value'],
                                 color=COLORS['accent'], linewidth=2, label='Ваш портфель')
            self.history_ax.plot(history_df['date'], history_df['cash'],
                                 color=COLORS['info'], linewidth=1, alpha=0.7, label='Денежные средства')

            # Индекс MCFTR
            if 'index_value' in index_df.columns:
                self.history_ax.plot(index_df['date'], index_df['index_value'],
                                     color=COLORS['warning'], linewidth=2, label='Индекс MCFTR')

            # Инфляция (взносы, проиндексированные рядом ЦБ РФ)
            if 'inflated_value' in index_df.columns and index_df['inflated_value'].notna().any():
                self.history_ax.plot(index_df['date'], index_df['inflated_value'],
                                     color='#ef5350', linewidth=1.5, linestyle=':',
                                     label='Инфляция (ЦБ РФ, г/г)')

            self.history_ax.set_title('Динамика стоимости портфеля vs Индекс МосБиржи', color=COLORS['text'],
                                      fontsize=14)
            self.history_ax.set_xlabel('Дата', color=COLORS['text'])
            self.history_ax.set_ylabel('Стоимость (₽)', color=COLORS['text'])

            # Легенду перемещаем ВНИЗ (под график или в правый нижний угол)
            self.history_ax.legend(loc='upper left', bbox_to_anchor=(0.02, 0.90), fontsize=9)

            self.history_ax.tick_params(colors=COLORS['text'])
            self.history_ax.grid(True, alpha=0.3)

            # Расчет чистого инвестиционного дохода
            from DB.db_config import create_connection

            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")

            start_date = history_df['date'].iloc[0]
            end_date = history_df['date'].iloc[-1]

            # Сумма пополнений за период
            cursor.execute("SELECT SUM(amount) FROM deposits WHERE date BETWEEN %s AND %s",
                           (start_date, end_date))
            total_deposits_period = float(cursor.fetchone()[0] or 0)

            # Сумма налоговых вычетов за период
            cursor.execute("SELECT SUM(amount) FROM tax_deductions WHERE date BETWEEN %s AND %s",
                           (start_date, end_date))
            total_tax_ded = float(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT SUM(amount) FROM tax_refunds WHERE date BETWEEN %s AND %s",
                           (start_date, end_date))
            total_tax_ref = float(cursor.fetchone()[0] or 0)

            # Сумма дивидендов и купонов за период
            cursor.execute("SELECT SUM(amount) FROM dividends WHERE date BETWEEN %s AND %s",
                           (start_date, end_date))
            total_dividends_period = float(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT SUM(amount) FROM coupons WHERE date BETWEEN %s AND %s",
                           (start_date, end_date))
            total_coupons_period = float(cursor.fetchone()[0] or 0)

            conn.close()

            # Внешние поступления (пополнения + вычеты)
            total_external = total_deposits_period + total_tax_ded + total_tax_ref

            # Финальная и начальная стоимость портфеля
            final_value = history_df['value'].iloc[-1]
            start_value = history_df['value'].iloc[0]

            # Реальная прибыль = изменение стоимости + дивиденды + купоны - внешние поступления
            # НО: дивиденды и купоны уже учтены в value через cash, поэтому:
            # Чистая прибыль = финальная стоимость - начальная стоимость - внешние поступления
            net_profit = final_value - start_value - total_external

            # Начальный капитал (то, что реально вложено)
            initial_investment = start_value + total_external

            # Для первой точки (когда start_value = 0):
            if start_value == 0:
                # Считаем доходность от первого пополнения
                portfolio_growth = (net_profit / total_external * 100) if total_external > 0 else 0
            else:
                portfolio_growth = (net_profit / initial_investment * 100) if initial_investment > 0 else 0

            # Для индекса
            if index_df is not None and 'index_value' in index_df.columns and not index_df[
                'index_value'].isnull().all():
                # Находим первую и последнюю не нулевую стоимость индекса
                index_values = index_df['index_value'].dropna()
                index_values = index_values[index_values > 0]

                if len(index_values) > 0:
                    index_start = index_values.iloc[0]
                    index_final = index_values.iloc[-1]

                    # Рост индекса в процентах
                    if index_start > 0:
                        index_pct = ((index_final - index_start) / index_start * 100)
                    else:
                        index_pct = 0
                else:
                    index_final = 0
                    index_pct = 0
            else:
                index_final = 0
                index_pct = 0

            # Текст статистики
            info_text = (f'Портфель: {final_value:,.0f} ₽ ({portfolio_growth:+.1f}%) | '
                         f'Индекс: {index_final:,.0f} ₽ ({index_pct:+.1f}%)')

            # Размещаем надпись в левом верхнем углу
            self.history_ax.text(0.02, 0.95, info_text, transform=self.history_ax.transAxes,
                                 bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS['accent_light'], alpha=0.8),
                                 fontsize=10, color=COLORS['text'])

        GOAL_AMOUNT = 1500000  # или загрузить из БД
        self.history_ax.axhline(y=GOAL_AMOUNT, color='red', linestyle='--',
                                linewidth=1.5, label='Цель: 1,7 млн ₽')

        self.history_canvas.draw()

    def add_tax_deduction(self):
        '''Добавление налогового вычета'''
        AddTaxDeductionDialog(self.root, self.save_tax_deduction)

    def save_tax_deduction(self, **kwargs):
        '''Сохранение налогового вычета'''
        from DB.database import save_tax_deduction
        if save_tax_deduction(
                kwargs['date'],
                kwargs['amount'],
                kwargs['deduction_type'],
                kwargs.get('description', ''),
                kwargs.get('year')
        ):
            messagebox.showinfo("Успех", "Налоговый вычет добавлен")
            self.load_tax_deductions_data()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить вычет")

    def delete_tax_deduction(self):
        '''Удаление вычета'''
        selected = self.deductions_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите вычет для удаления")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранный вычет?"):
            item = self.deductions_tree.item(selected[0])
            deduction_id = self.deductions_ids[selected[0]]

            from DB.database import delete_tax_deduction
            if delete_tax_deduction(deduction_id):
                messagebox.showinfo("Успех", "Вычет удален")
                self.load_tax_deductions_data()
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить вычет")

    def load_tax_deductions_data(self):
        '''Загрузка данных о налоговых вычетах'''
        from DB.database import get_tax_deductions

        # Очищаем таблицу
        for item in self.deductions_tree.get_children():
            self.deductions_tree.delete(item)

        self.deductions_ids = {}

        # Загружаем вычеты
        deductions = get_tax_deductions(self.user_id)
        total_deductions = 0
        for i, ded in enumerate(deductions):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            ded_id, date, amount, ded_type, description, year = ded

            item_id = self.deductions_tree.insert('', tk.END, values=(
                date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else date,
                ded_type,
                str(year) if year else '-',
                f"{float(amount):,.2f}",
                description if description else ''
            ), tags=(tag,))

            self.deductions_ids[item_id] = ded_id
            total_deductions += float(amount)

        self.deductions_total_label.config(text=f"Всего вычетов: {total_deductions:,.2f} ₽")

    def load_data(self):
        '''Загрузка данных из БД для вкладок сводная, акции, облигации'''
        from DB.db_config import create_connection

        # Пополнения
        for item in self.deposits_tree.get_children():
            self.deposits_tree.delete(item)

        deposits = get_deposits(self.user_id)
        total_deposits = 0
        for i, row in enumerate(deposits):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.deposits_tree.insert('', tk.END, values=(row[0], f"{float(row[1]):,.2f}"), tags=(tag,))
            total_deposits += float(row[1])
        self.deposits_total_label.config(text=f"Всего пополнено: {total_deposits:,.2f} ₽")

        # Дивиденды
        for item in self.dividends_tree.get_children():
            self.dividends_tree.delete(item)

        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute(
                "SELECT date, ticker, quantity, amount, avg_price FROM dividends WHERE user_id = %s ORDER BY date DESC",
                (self.user_id,),
            )
            total_dividends = 0
            for i, row in enumerate(cursor.fetchall()):
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                date = row[0]
                ticker = row[1]
                name = TICKER_NAMES.get(ticker, ticker)
                qty = float(row[2]) if row[2] and row[2] > 0 else 1
                amount = float(row[3])
                avg_price = float(row[4]) if row[4] else None

                yield_per_share = amount / qty if qty > 0 else 0
                yield_percent = (yield_per_share / avg_price * 100) if avg_price and avg_price > 0 else 0

                self.dividends_tree.insert('', tk.END,
                                           values=(name, ticker, date, f"{qty:.0f}", f"{amount:,.2f}",
                                                   f"{yield_per_share:.2f}", f"{yield_percent:.2f}%"),
                                           tags=(tag,))
                total_dividends += amount
            conn.close()
            self.dividends_total_label.config(text=f"Всего дивидендов: {total_dividends:,.2f} ₽")

        # Купоны
        for item in self.coupons_tree.get_children():
            self.coupons_tree.delete(item)

        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute(
                "SELECT date, ticker, quantity, amount FROM coupons WHERE user_id = %s ORDER BY date DESC",
                (self.user_id,),
            )
            total_coupons = 0
            for i, row in enumerate(cursor.fetchall()):
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                date = row[0]
                ticker = row[1]
                name = TICKER_NAMES.get(ticker, ticker)
                qty = float(row[2]) if row[2] and row[2] > 0 else 1
                amount = float(row[3])

                yield_per_share = amount / qty if qty > 0 else 0
                nominal = 1000
                yield_percent = (yield_per_share / nominal * 100) if nominal > 0 else 0

                self.coupons_tree.insert('', tk.END,
                                         values=(name, ticker, date, f"{qty:.0f}", f"{amount:,.2f}",
                                                 f"{yield_per_share:.2f}", f"{yield_percent:.2f}%"),
                                         tags=(tag,))
                total_coupons += amount
            conn.close()
            self.coupons_total_label.config(text=f"Всего купонов: {total_coupons:,.2f} ₽")

    def refresh_prices(self):
        '''Обновление цен'''
        self.status_label.config(text="Обновление цен...")
        self.root.update()

        def update():
            self.current_prices = get_all_prices(self.stocks, self.bonds)
            self.root.after(0, self.update_all_tables)
            self.root.after(0, self.load_data)
            self.root.after(0, lambda: self.status_label.config(
                text=f"Цены обновлены {datetime.now().strftime('%H:%M:%S')}"))

        threading.Thread(target=update, daemon=True).start()

    def update_all_tables(self):
        stats = get_portfolio_stats(self.user_id)
        if not stats:
            return

        total_portfolio_value = 0
        all_positions = []

        # Собираем акции
        for ticker, pos in stats['stock_positions'].items():
            if pos['qty'] > 0:
                current_price = self.current_prices.get(ticker, 0)
                current_value = pos['qty'] * current_price
                total_portfolio_value += current_value
                all_positions.append(('stock', ticker, pos, current_price, current_value))

        # Собираем облигации
        for ticker, pos in stats['bond_positions'].items():
            if pos['qty'] > 0:
                current_price_rub = self.current_prices.get(ticker, 0)
                current_value = pos['qty'] * current_price_rub
                total_portfolio_value += current_value

                from prices import get_current_price
                current_price_percent = get_current_price(ticker, 'bond') or 0

                all_positions.append(('bond', ticker, pos, current_price_rub, current_value, current_price_percent))

        def get_position_order(item):
            sec_type = item[0]
            ticker = item[1]
            if sec_type == 'stock':
                if ticker in STOCKS:
                    return STOCKS.index(ticker)
                return len(STOCKS) + 999
            else:
                if ticker in BONDS:
                    return len(STOCKS) + BONDS.index(ticker)
                return len(STOCKS) + len(BONDS) + 999

        all_positions.sort(key=get_position_order)

        # Очистка таблиц
        for tree in [self.summary_tree, self.stocks_tree, self.bonds_tree]:
            if tree is not None:
                for item in tree.get_children():
                    tree.delete(item)

        # Считаем реальные затраты на покупки
        total_purchases = 0
        for ticker, pos in stats['stock_positions'].items():
            total_purchases += pos['total_cost']
        for ticker, pos in stats['bond_positions'].items():
            total_purchases += pos['total_cost']

        # Обновление карточек
        self.total_deposits_var.set(f"{stats['total_deposits']:,.2f} ₽")
        self.total_portfolio_value_var.set(f"{total_portfolio_value:,.2f} ₽")

        # Получаем сумму вкладов
        from DB.database import get_deposit_accounts
        deposits_accounts = get_deposit_accounts()
        total_in_deposits_accounts = sum(float(acc[3]) for acc in deposits_accounts)
        total_all_value = total_portfolio_value + total_in_deposits_accounts
        self.total_value_with_deposits_var.set(f"{total_all_value:,.2f} ₽")

        profit = total_portfolio_value - total_purchases + stats['total_dividends'] + \
                 stats['total_coupons'] + stats['total_redemptions'] - stats['total_taxes']
        self.total_profit_var.set(f"{profit:,.2f} ₽")

        profit_pct = (profit / total_purchases * 100) if total_purchases > 0 else 0
        self.total_profit_pct_var.set(f"{profit_pct:.2f}%")

        # Заполнение таблиц
        for i, item in enumerate(all_positions):
            if len(item) == 5:  # акция
                sec_type, ticker, pos, current_price, current_value = item
                avg_price = pos['total_cost'] / pos['qty'] if pos['qty'] > 0 else 0
                position_profit = current_value - pos['total_cost']
                profit_pct_pos = (position_profit / pos['total_cost'] * 100) if pos['total_cost'] > 0 else 0
                share = (current_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0

                target_share = TARGET_SHARES.get(ticker, 0)
                deviation = share - target_share

                to_buy = 0
                if deviation < 0 and current_price > 0:
                    target_value = total_portfolio_value * target_share / 100
                    needed_value = target_value - current_value
                    to_buy = int(needed_value / current_price)

                from DB.db_config import create_connection
                conn = create_connection()
                cursor = conn.cursor()
                cursor.execute("USE investment_portfolio")
                cursor.execute("SELECT SUM(amount) FROM dividends WHERE ticker = %s", (ticker,))
                total_div = cursor.fetchone()[0] or 0
                conn.close()

                profit_with_div = position_profit + float(total_div)
                profit_pct_with_div = (profit_with_div / pos['total_cost'] * 100) if pos['total_cost'] > 0 else 0

                type_name = "Акция"

                # Справедливая цена
                fair_data = self.fair_prices.get(ticker) if hasattr(self, 'fair_prices') else None
                if fair_data:
                    fair_price = fair_data.get('fair_price')
                    upside = fair_data.get('upside')
                    fair_value = fair_price * pos['qty'] if fair_price else None
                else:
                    fair_price = None
                    upside = None
                    fair_value = None

                row_data = [
                    TICKER_NAMES.get(ticker, ticker),
                    ticker,
                    f"{pos['qty']:.0f}",
                    f"{avg_price:.2f}",
                    f"{current_price:.2f}",
                    f"{pos['total_cost']:,.2f}",
                    f"{current_value:,.2f}",
                    f"{position_profit:,.2f}",
                    f"{profit_pct_pos:.2f}%",
                    f"{profit_with_div:,.2f}",
                    f"{profit_pct_with_div:.2f}%",
                    f"{share:.2f}%",
                    f"{target_share:.2f}%",
                    f"{deviation:+.2f}%" if deviation != 0 else "0%",
                    str(to_buy) if to_buy > 0 else "-",
                    f"{fair_price:.2f}" if fair_price else "-",
                    f"{upside:+.1f}%" if upside else "-",
                    f"{fair_value:,.0f}" if fair_value else "-",
                ]

                summary_values = [
                    TICKER_NAMES.get(ticker, ticker),
                    ticker,
                    type_name,
                    f"{pos['qty']:.0f}",
                    f"{avg_price:.2f}",
                    f"{current_price:.2f}",
                    f"{pos['total_cost']:,.2f}",
                    f"{current_value:,.2f}",
                    f"{position_profit:,.2f}",
                    f"{profit_pct_pos:.2f}%",
                    f"{share:.2f}%",
                    f"{target_share:.2f}%",
                    f"{deviation:+.2f}%" if deviation != 0 else "0%",
                    str(to_buy) if to_buy > 0 else "-",
                    f"{fair_price:.2f}" if fair_price else "-",
                    f"{upside:+.1f}%" if upside else "-",
                    f"{fair_value:,.0f}" if fair_value else "-",
                ]

                row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.summary_tree.insert('', tk.END, values=summary_values, tags=(row_tag,))
                self.stocks_tree.insert('', tk.END, values=row_data, tags=(row_tag,))

            else:  # облигация
                sec_type, ticker, pos, current_price_rub, current_value, current_price_percent = item
                avg_price_rub = pos['total_cost'] / pos['qty'] if pos['qty'] > 0 else 0
                avg_price_percent = (avg_price_rub / 1000 * 100) if avg_price_rub > 0 else 0
                position_profit = current_value - pos['total_cost']
                profit_pct_pos = (position_profit / pos['total_cost'] * 100) if pos['total_cost'] > 0 else 0
                share = (current_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
                target_share = TARGET_SHARES.get(ticker, 0)
                deviation = share - target_share

                to_buy = 0
                if deviation < 0 and current_price_rub > 0:
                    target_value = total_portfolio_value * target_share / 100
                    needed_value = target_value - current_value
                    to_buy = int(needed_value / current_price_rub)

                from DB.db_config import create_connection
                conn = create_connection()
                cursor = conn.cursor()
                cursor.execute("USE investment_portfolio")
                cursor.execute("SELECT SUM(amount) FROM coupons WHERE ticker = %s", (ticker,))
                total_coupon = cursor.fetchone()[0] or 0
                conn.close()
                profit_with_coupon = position_profit + float(total_coupon)
                profit_pct_with_coupon = (profit_with_coupon / pos['total_cost'] * 100) if pos['total_cost'] > 0 else 0
                type_name = "Облигация"

                row_data = [
                    TICKER_NAMES.get(ticker, ticker),
                    ticker,
                    f"{pos['qty']:.0f}",
                    f"{avg_price_rub:.2f}",
                    f"{avg_price_percent:.2f}",
                    f"{current_price_rub:.2f}",
                    f"{current_price_percent:.2f}",
                    f"{pos['total_cost']:,.2f}",
                    f"{current_value:,.2f}",
                    f"{position_profit:,.2f}",
                    f"{profit_pct_pos:.2f}%",
                    f"{profit_with_coupon:,.2f}",
                    f"{profit_pct_with_coupon:.2f}%",
                    f"{share:.2f}%",
                    f"{target_share:.2f}%",
                    f"{deviation:+.2f}%" if deviation != 0 else "0%",
                    str(to_buy) if to_buy > 0 else "-",
                    "-", "-", "-",  # для облигаций нет справедливой цены
                ]

                summary_values = [
                    TICKER_NAMES.get(ticker, ticker),
                    ticker,
                    type_name,
                    f"{pos['qty']:.0f}",
                    f"{avg_price_rub:.2f}",
                    f"{current_price_rub:.2f}",
                    f"{pos['total_cost']:,.2f}",
                    f"{current_value:,.2f}",
                    f"{position_profit:,.2f}",
                    f"{profit_pct_pos:.2f}%",
                    f"{share:.2f}%",
                    f"{target_share:.2f}%",
                    f"{deviation:+.2f}%" if deviation != 0 else "0%",
                    str(to_buy) if to_buy > 0 else "-",
                    "-", "-", "-",
                ]

                row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                self.summary_tree.insert('', tk.END, values=summary_values, tags=(row_tag,))
                self.bonds_tree.insert('', tk.END, values=row_data, tags=(row_tag,))

        # Справедливая стоимость всего портфеля
        if hasattr(self, 'fair_prices'):
            total_fair_stocks = sum(
                (self.fair_prices.get(ticker, {}).get('fair_price', 0) or 0) * pos['qty']
                for ticker, pos in stats['stock_positions'].items()
                if pos['qty'] > 0
            )
            total_fair_bonds = sum(pos['total_cost'] for pos in stats['bond_positions'].values())
            total_fair_value = total_fair_stocks + total_fair_bonds + total_in_deposits_accounts
            self.fair_value_var.set(f"{total_fair_value:,.2f} ₽")

        self.update_bottom_stats(stats, total_portfolio_value, total_purchases, all_positions)

        # Расчет XIRR
        from DB.db_config import create_connection
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("USE investment_portfolio")
        cursor.execute("SELECT date, amount FROM deposits WHERE user_id = %s ORDER BY date", (self.user_id,))
        deposits = cursor.fetchall()
        conn.close()

        if deposits:
            current_value = total_portfolio_value
            cashflows = [-float(d[1]) for d in deposits]
            dates = [d[0] for d in deposits]
            cashflows.append(current_value)
            dates.append(datetime.now().date())
            xirr = calculate_xirr(cashflows, dates)
            self.xirr_var.set(f"{xirr:.2f}%")
        else:
            self.xirr_var.set("0%")

    def start_auto_update(self):
        '''Автоматическое обновление цен раз в минуту'''
        def auto_update():
            while self.update_thread_running and self.auto_update_enabled:
                time.sleep(60)
                if self.auto_update_enabled:
                    self.refresh_prices()

        threading.Thread(target=auto_update, daemon=True).start()

    def toggle_auto_update(self):
        '''Выключение автоматического обновления'''
        self.auto_update_enabled = not self.auto_update_enabled
        status = "включено" if self.auto_update_enabled else "выключено"
        self.status_label.config(text=f"Автообновление {status}")

    def add_deposit(self):
        AddDepositDialog(self.root, self.save_deposit)

    def save_deposit(self, type_, **kwargs):
        if save_deposit(kwargs['date'], kwargs['amount'], user_id=self.user_id):
            messagebox.showinfo("Успех", "Пополнение добавлено")
            self.refresh_prices()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить пополнение")

    def add_trade(self, sec_type, operation):
        securities = self.stocks if sec_type == 'stock' else self.bonds
        AddTradeDialog(self.root, sec_type, operation, securities, self.save_trade)

    def save_trade(self, sec_type, operation, **kwargs):
        if save_trade(sec_type, operation, kwargs['ticker'], kwargs['date'],
                      kwargs['quantity'], kwargs['price'], kwargs['total'], user_id=self.user_id):
            messagebox.showinfo("Успех", f"{'Покупка' if operation == 'buy' else 'Продажа'} добавлена")
            self.refresh_prices()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить сделку")

    def add_income(self, income_type):
        securities = self.stocks if income_type == 'dividend' else self.bonds
        AddIncomeDialog(self.root, income_type, securities, self.save_income)

    def save_income(self, **kwargs):
        from DB.database import save_income
        income_type = kwargs.get('income_type')

        avg_price = kwargs.get('avg_price')
        if save_income(income_type, kwargs['ticker'], kwargs['date'],
                       kwargs['quantity'], kwargs['amount'], avg_price, user_id=self.user_id):
            messagebox.showinfo("Успех", f"{'Дивиденды' if income_type == 'dividend' else 'Купон'} добавлены")
            self.refresh_prices()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить доход")

    def add_redemption(self):
        AddRedemptionDialog(self.root, self.bonds, self.save_redemption)

    def save_redemption(self, **kwargs):
        if save_redemption(kwargs['ticker'], kwargs['date'], kwargs['quantity'], kwargs['price'], kwargs['total'], user_id=self.user_id):
            messagebox.showinfo("Успех", "Погашение облигации добавлено")
            self.refresh_prices()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить погашение")

    def add_tax_refund(self):
        AddTaxRefundDialog(self.root, self.save_tax_refund)

    def save_tax_refund(self, **kwargs):
        from DB.database import save_tax_refund
        if save_tax_refund(kwargs['date'], kwargs['amount'], kwargs.get('description', ''), user_id=self.user_id):
            messagebox.showinfo("Успех", "Налоговый вычет добавлен")
            self.refresh_prices()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить вычет")

    def show_charts(self):
        '''Всплывающее окно с круговой диаграммой'''
        stats = get_portfolio_stats(self.user_id)

        chart_window = tk.Toplevel(self.root)
        chart_window.title("Графики портфеля")
        chart_window.geometry("800x800")
        chart_window.configure(bg=COLORS['bg_main'])

        chart_window.transient(self.root)
        chart_window.grab_set()

        chart_window.update_idletasks()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()

        window_width = 800
        window_height = 800

        x = parent_x + (parent_width // 2) - (window_width // 2)
        y = parent_y + (parent_height // 2) - (window_height // 2)
        chart_window.geometry(f"+{x}+{y}")

        notebook = ttk.Notebook(chart_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка 1: Структура портфеля
        frame1 = ttk.Frame(notebook)
        notebook.add(frame1, text="Структура портфеля")

        fig1, ax1 = plt.subplots(figsize=(16, 12))
        fig1.patch.set_facecolor(COLORS['bg_main'])
        ax1.set_facecolor(COLORS['bg_main'])
        fig1.subplots_adjust(left=0.15, right=0.85, top=0.85, bottom=0.15)

        positions_data = []

        for ticker, pos in stats['stock_positions'].items():
            if pos['qty'] > 0:
                current_price = self.current_prices.get(ticker, 0)
                current_value = pos['qty'] * current_price
                if current_value > 0:
                    name = TICKER_NAMES.get(ticker, ticker)
                    color = TICKER_COLORS.get(ticker, COLORS['accent'])
                    positions_data.append((name, current_value, color))

        for ticker, pos in stats['bond_positions'].items():
            if pos['qty'] > 0:
                current_price_rub = self.current_prices.get(ticker, 0)
                current_value = pos['qty'] * current_price_rub
                if current_value > 0:
                    name = TICKER_NAMES.get(ticker, ticker)
                    color = TICKER_COLORS.get(ticker, COLORS['accent'])
                    positions_data.append((name, current_value, color))

        if positions_data:
            positions_data.sort(key=lambda x: x[1], reverse=True)

            labels = [p[0] for p in positions_data]
            values = [p[1] for p in positions_data]
            colors = [p[2] for p in positions_data]

            wedges, texts, autotexts = ax1.pie(
                values,
                labels=None,
                autopct=lambda pct: f'{pct:.1f}%' if pct > 2 else '',
                colors=colors,
                startangle=90,
                pctdistance=0.7,
                radius=1
            )

            for autotext in autotexts:
                if autotext.get_text():
                    autotext.set_color('white')
                    autotext.set_fontsize(10)
                    autotext.set_weight('bold')

            bbox_props = dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.7)
            kw = dict(arrowprops=dict(arrowstyle="-", color='gray', lw=0.8),
                      bbox=bbox_props, zorder=0, va="center", fontsize=9, color=COLORS['text'])

            for i, (wedge, label) in enumerate(zip(wedges, labels)):
                ang = (wedge.theta2 - wedge.theta1) / 2. + wedge.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))

                horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connectionstyle = f"angle,angleA=0,angleB={ang}"
                kw["arrowprops"].update({"connectionstyle": connectionstyle})

                label_x = 1.4 * x
                label_y = 1.4 * y

                value_str = f"{values[i]:,.0f} ₽".replace(',', ' ')

                ax1.annotate(f"{label}\n{value_str}",
                             xy=(x, y), xytext=(label_x, label_y),
                             horizontalalignment='center',
                             multialignment='center',
                             **kw)

            ax1.axis('equal')
        else:
            ax1.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                     color=COLORS['text'], fontsize=14, transform=ax1.transAxes)

        canvas1 = FigureCanvasTkAgg(fig1, frame1)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Вкладка 2: Доходность по месяцам (чистая прибыль)
        frame2 = ttk.Frame(notebook)
        notebook.add(frame2, text="Доходность по месяцам")

        fig2, ax2 = plt.subplots(figsize=(12, 8))
        fig2.patch.set_facecolor(COLORS['bg_main'])
        ax2.set_facecolor(COLORS['bg_main'])
        ax2.tick_params(colors=COLORS['text'])

        from DB.database import get_portfolio_history
        from DB.db_config import create_connection
        from datetime import datetime
        import pandas as pd

        start_date = datetime(2023, 9, 30)
        end_date = datetime.now()

        history_df = get_portfolio_history(start_date, end_date)

        if history_df is not None and not history_df.empty:
            # Получаем пополнения и налоговые вычеты для вычитания
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")

            # Пополнения
            cursor.execute("SELECT date, amount FROM deposits ORDER BY date")
            deposits = cursor.fetchall()

            # Налоговые вычеты
            cursor.execute("SELECT date, amount FROM tax_deductions ORDER BY date")
            tax_deductions = cursor.fetchall()

            # Возвраты налогов
            cursor.execute("SELECT date, amount FROM tax_refunds ORDER BY date")
            tax_refunds = cursor.fetchall()

            conn.close()

            # Объединяем все внешние поступления
            external_income = {}
            for d in deposits:
                date_obj = d[0]
                external_income[date_obj] = external_income.get(date_obj, 0) + float(d[1])
            for t in tax_deductions:
                date_obj = t[0]
                external_income[date_obj] = external_income.get(date_obj, 0) + float(t[1])
            for t in tax_refunds:
                date_obj = t[0]
                external_income[date_obj] = external_income.get(date_obj, 0) + float(t[1])

            # Вычисляем накопленные внешние поступления на каждую дату
            history_df['date_only'] = pd.to_datetime(history_df['date']).dt.date
            history_df['cumulative_external'] = 0.0

            cum_ext = 0.0
            for i, row in history_df.iterrows():
                date = row['date_only']
                if date in external_income:
                    cum_ext += external_income[date]
                history_df.at[i, 'cumulative_external'] = cum_ext

            # Чистая инвестиционная стоимость = стоимость портфеля - внешние поступления
            history_df['net_investment_value'] = history_df['value'] - history_df['cumulative_external']

            # Группируем по месяцам
            history_df['month'] = pd.to_datetime(history_df['date']).dt.to_period('M')
            monthly = history_df.groupby('month').agg({'net_investment_value': ['first', 'last']})
            monthly['profit'] = monthly[('net_investment_value', 'last')] - monthly[('net_investment_value', 'first')]

            colors = [COLORS['success'] if p >= 0 else COLORS['danger'] for p in monthly['profit']]
            bars = ax2.bar(range(len(monthly)), monthly['profit'], color=colors)

            # Добавляем значения над столбцами
            if len(monthly) <= 24:
                for i, (bar, profit) in enumerate(zip(bars, monthly['profit'])):
                    ax2.text(bar.get_x() + bar.get_width() / 2., profit,
                             f'{profit:,.0f} ₽'.replace(',', ' '),
                             ha='center', va='bottom' if profit >= 0 else 'top',
                             color=COLORS['text'], fontsize=8, rotation=90)

            # Показываем не все месяцы
            step = max(1, len(monthly) // 12)
            ax2.set_xticks(range(0, len(monthly), step))
            ax2.set_xticklabels([str(monthly.index[i]) for i in range(0, len(monthly), step)],
                                rotation=45, ha='right')

            ax2.set_ylabel('Инвестиционная прибыль/Убыток (₽)', color=COLORS['text'], fontsize=12)
            ax2.set_title(f'Чистый инвестиционный доход по месяцам ({monthly.index[0]} - {monthly.index[-1]})',
                          color=COLORS['text'], fontsize=14)
            ax2.axhline(y=0, color=COLORS['text_secondary'], linestyle='-', linewidth=0.5)

            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.spines['left'].set_color(COLORS['text_secondary'])
            ax2.spines['bottom'].set_color(COLORS['text_secondary'])

            fig2.tight_layout()
        else:
            ax2.text(0.5, 0.5, 'Недостаточно данных', ha='center', va='center',
                     color=COLORS['text'], fontsize=14, transform=ax2.transAxes)

        canvas2 = FigureCanvasTkAgg(fig2, frame2)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_closing(self):
        self.update_thread_running = False
        self.root.destroy()

    def load_deposits_data(self):
        '''Загрузка данных о вкладах и выплатах'''
        from DB.database import get_deposit_accounts, get_deposit_payments

        # Очищаем таблицы
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)
        for item in self.payments_tree.get_children():
            self.payments_tree.delete(item)

        # Загружаем счета
        accounts = get_deposit_accounts()
        self.accounts_list = accounts

        total_in_deposits = 0
        for i, acc in enumerate(accounts):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            acc_id, name, acc_type, amount, rate, maturity, notes = acc
            total_in_deposits += float(amount)

            self.accounts_tree.insert('', tk.END,
                                      values=(name, acc_type, f"{float(amount):,.2f}",
                                              f"{float(rate):.2f}%" if rate else "-",
                                              maturity if maturity else "-",
                                              notes if notes else "-"),
                                      tags=(tag,))

        # Загружаем выплаты
        payments = get_deposit_payments()
        for i, pay in enumerate(payments):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            account_name, date, amount = pay
            self.payments_tree.insert('', tk.END,
                                      values=(account_name, date, f"{float(amount):,.2f}"),
                                      tags=(tag,))

    def add_deposit_account(self):
        '''Добавление нового вклада'''
        AddDepositAccountDialog(self.root, self.save_deposit_account)

    def save_deposit_account(self, **kwargs):
        '''Сохранение нового вклада'''
        from DB.database import save_deposit_account
        if save_deposit_account(kwargs['name'], kwargs['acc_type'], kwargs['amount'],
                                kwargs.get('rate'), kwargs.get('maturity'), kwargs.get('notes')):
            messagebox.showinfo("Успех", "Вклад добавлен")
            self.load_deposits_data()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить вклад")

    def add_deposit_payment(self):
        '''Добавление выплаты по вкладу'''
        if not hasattr(self, 'accounts_list') or not self.accounts_list:
            messagebox.showwarning("Внимание", "Сначала добавьте хотя бы один вклад")
            return
        AddDepositPaymentDialog(self.root, self.accounts_list, self.save_deposit_payment)

    def save_deposit_payment(self, **kwargs):
        '''Сохранение выплаты'''
        from DB.database import save_deposit_payment
        if save_deposit_payment(kwargs['account_id'], kwargs['date'], kwargs['amount']):
            messagebox.showinfo("Успех", "Выплата добавлена")
            self.load_deposits_data()
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить выплату")

    def update_account_amount(self):
        """Обновление суммы на счете"""
        if not hasattr(self, 'accounts_list') or not self.accounts_list:
            messagebox.showwarning("Внимание", "Сначала добавьте хотя бы один вклад")
            return
        UpdateAccountDialog(self.root, self.accounts_list, self.save_account_update)

    def save_account_update(self, account_id, new_amount):
        from DB.database import update_deposit_account
        if update_deposit_account(account_id, new_amount, user_id=self.user_id):
            messagebox.showinfo("Успех", "Сумма обновлена")
            self.load_deposits_data()
        else:
            messagebox.showerror("Ошибка", "Не удалось обновить сумму")

    def delete_account(self):
        '''Удаление вклада'''
        selected = self.accounts_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите вклад для удаления")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранный вклад и все связанные выплаты?"):
            # Получаем ID выбранного вклада
            item = self.accounts_tree.item(selected[0])
            values = item['values']
            account_name = values[0]

            # Находим ID по имени
            for acc in self.accounts_list:
                if acc[1] == account_name:
                    from DB.database import delete_deposit_account
                    if delete_deposit_account(acc[0]):
                        messagebox.showinfo("Успех", "Вклад удален")
                        self.load_deposits_data()
                    else:
                        messagebox.showerror("Ошибка", "Не удалось удалить вклад")
                    break


if __name__ == "__main__":
    root = tk.Tk()

    if init_db():
        login = LoginDialog(root)
        user_id = login.show()
        if user_id is None:
            root.destroy()
        else:
            app = InvestmentApp(root, user_id=user_id)
            root.protocol("WM_DELETE_WINDOW", app.on_closing)
            root.mainloop()
    else:
        messagebox.showerror(
            "Ошибка подключения к MySQL",
            "Не удалось инициализировать базу данных.\n\n"
            "Проверьте, что MySQL запущен и заданы параметры подключения (переменные окружения).\n"
            "Подсказка: смотрите пример в файле .env.example.",
        )