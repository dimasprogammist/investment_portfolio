import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from config import COLORS, TICKER_NAMES


class StyledButton(tk.Button):
    """Кнопка с единым стилем для всего приложения."""

    def __init__(self, parent, text, command, width=15):
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=COLORS["bg_header"],
            fg=COLORS["text"],
            font=("Calibri", 10),
            width=width,
            height=1,
            relief="flat",
            bd=1,
            cursor="hand2",
            padx=8,
            pady=5,
        )
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, _e):
        self.config(bg=COLORS["accent"], fg="white")

    def on_leave(self, _e):
        self.config(bg=COLORS["bg_header"], fg=COLORS["text"])


class StyledDialog:
    """Базовое стилизованное диалоговое окно."""

    def __init__(self, parent, title, width, height):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry(f"{width}x{height}")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg=COLORS["bg_main"])

        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Контентный контейнер с едиными отступами — чтобы диалоги выглядели одинаково.
        self.main_frame = tk.Frame(self.dialog, bg=COLORS["bg_main"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Заголовок окна. Используем общий стиль, чтобы все диалоги выглядели единообразно.
        title_label = tk.Label(
            self.main_frame,
            text=title,
            font=("Calibri", 12, "bold"),
            bg=COLORS["bg_main"],
            fg=COLORS["accent"],
        )
        title_label.pack(pady=(0, 10))


class AddDepositDialog(StyledDialog):
    def __init__(self, parent, callback):
        super().__init__(parent, "Пополнение счёта", 220, 160)
        self.callback = callback
        self.create_widgets()

    def create_widgets(self):
        frame_date = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_date.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_date,
            text="Дата:",
            width=8,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(
            frame_date,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_amount = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_amount.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            frame_amount,
            text="Сумма (₽):",
            width=8,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.amount_entry = tk.Entry(
            frame_amount,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(5, 0))
        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self.save,
            bg=COLORS["success"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

    def save(self):
        try:
            date = self.date_entry.get()
            amount = float(self.amount_entry.get())
            self.callback("deposit", date=date, amount=amount)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректную сумму")


class AddTradeDialog(StyledDialog):
    def __init__(self, parent, sec_type, operation, securities, callback):
        self.sec_type = sec_type
        self.operation = operation
        self.securities = securities
        self.securities_dict = {TICKER_NAMES.get(t, t): t for t in securities}
        self.callback = callback
        title = (
            f"{'Покупка' if operation == 'buy' else 'Продажа'} "
            f"{('акций' if sec_type == 'stock' else 'облигаций')}"
        )
        super().__init__(parent, title, 220, 210)
        self.create_widgets()

    def create_widgets(self):
        frame_ticker = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_ticker.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_ticker,
            text="Бумага:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.ticker_combo = ttk.Combobox(
            frame_ticker,
            values=list(self.securities_dict.keys()),
            font=("Calibri", 10),
            state="readonly",
        )
        self.ticker_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_date = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_date.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_date,
            text="Дата:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(
            frame_date,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_qty = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_qty.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_qty,
            text="Количество:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.qty_entry = tk.Entry(
            frame_qty,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.qty_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_price = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_price.pack(fill=tk.X, pady=(0, 5))
        price_label = "Цена (%):   " if self.sec_type == "bond" else "Цена 1 шт.(₽):"
        tk.Label(
            frame_price,
            text=price_label,
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.price_entry = tk.Entry(
            frame_price,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(10, 0))
        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self.save,
            bg=COLORS["success"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

    def save(self):
        try:
            name = self.ticker_combo.get()
            ticker = self.securities_dict[name]
            date = self.date_entry.get()
            qty = float(self.qty_entry.get())
            price_input = float(self.price_entry.get())

            # В вашем приложении цена облигации в диалоге вводится в условных "десятках".
            # Сохраняем совместимость с текущей логикой расчёта.
            price = price_input * 10 if self.sec_type == "bond" else price_input

            total = qty * price
            self.callback(
                self.sec_type,
                self.operation,
                ticker=ticker,
                date=date,
                quantity=qty,
                price=price,
                total=total,
            )
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные данные")


class AddIncomeDialog(StyledDialog):
    def __init__(self, parent, income_type, securities, callback):
        self.income_type = income_type
        self.securities = securities
        self.securities_dict = {TICKER_NAMES.get(t, t): t for t in securities}
        self.callback = callback
        title = "Дивиденды" if income_type == "dividend" else "Купоны"
        height = 235 if income_type == "dividend" else 205
        super().__init__(parent, title, 250, height)
        self.create_widgets()

    def create_widgets(self):
        frame_ticker = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_ticker.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_ticker,
            text="Бумага:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.ticker_combo = ttk.Combobox(
            frame_ticker,
            values=list(self.securities_dict.keys()),
            font=("Calibri", 10),
            state="readonly",
        )
        self.ticker_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_date = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_date.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_date,
            text="Дата:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(
            frame_date,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_qty = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_qty.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_qty,
            text="Количество:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.qty_entry = tk.Entry(
            frame_qty,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.qty_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        if self.income_type == "dividend":
            frame_avg_price = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
            frame_avg_price.pack(fill=tk.X, pady=(0, 8))
            tk.Label(
                frame_avg_price,
                text="Ср. цена (₽):",
                width=12,
                anchor="w",
                font=("Calibri", 10),
                bg=COLORS["bg_main"],
                fg=COLORS["text"],
            ).pack(side=tk.LEFT)
            self.avg_price_entry = tk.Entry(
                frame_avg_price,
                font=("Calibri", 10),
                bg="white",
                fg=COLORS["text"],
                insertbackground=COLORS["text"],
                relief="solid",
                bd=0,
                highlightthickness=1,
            )
            self.avg_price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_amount = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_amount.pack(fill=tk.X, pady=(0, 5))
        tk.Label(
            frame_amount,
            text="Сумма (₽):",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.amount_entry = tk.Entry(
            frame_amount,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(5, 0))
        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self.save,
            bg=COLORS["success"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

    def save(self):
        try:
            name = self.ticker_combo.get()
            ticker = self.securities_dict[name]
            date = self.date_entry.get()
            qty = float(self.qty_entry.get())
            amount = float(self.amount_entry.get())

            kwargs = {
                "income_type": self.income_type,
                "ticker": ticker,
                "date": date,
                "quantity": qty,
                "amount": amount,
            }

            # Средняя цена нужна только для дивидендов — используем её в расчётах доходности.
            if self.income_type == "dividend" and hasattr(self, "avg_price_entry"):
                avg_price = float(self.avg_price_entry.get())
                kwargs["avg_price"] = avg_price

            self.callback(**kwargs)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные данные")


class AddRedemptionDialog(StyledDialog):
    def __init__(self, parent, bonds, callback):
        self.bonds = bonds
        self.callback = callback
        super().__init__(parent, "Погашение облигаций", 220, 215)
        self.create_widgets()

    def create_widgets(self):
        frame_ticker = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_ticker.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_ticker,
            text="Тикер:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.ticker_combo = ttk.Combobox(
            frame_ticker, values=self.bonds, font=("Calibri", 10), state="readonly"
        )
        self.ticker_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_date = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_date.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_date,
            text="Дата:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(
            frame_date,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_qty = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_qty.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_qty,
            text="Количество:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.qty_entry = tk.Entry(
            frame_qty,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.qty_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_total = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_total.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            frame_total,
            text="Сумма (₽):   ",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.total_entry = tk.Entry(
            frame_total,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.total_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(5, 0))
        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self.save,
            bg=COLORS["success"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

    def save(self):
        try:
            ticker = self.ticker_combo.get()
            date = self.date_entry.get()
            qty = float(self.qty_entry.get())
            total = float(self.total_entry.get())
            price = total / qty
            self.callback(ticker=ticker, date=date, quantity=qty, price=price, total=total)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные данные")


class AddTaxRefundDialog(StyledDialog):
    def __init__(self, parent, callback):
        super().__init__(parent, "Налоговый вычет", 220, 210)
        self.callback = callback
        self.create_widgets()

    def create_widgets(self):
        frame_date = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_date.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_date,
            text="Дата:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(
            frame_date,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_amount = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_amount.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_amount,
            text="Сумма (₽):",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.amount_entry = tk.Entry(
            frame_amount,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_desc = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_desc.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            frame_desc,
            text="Описание:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.desc_entry = tk.Entry(
            frame_desc,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(5, 0))
        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self.save,
            bg=COLORS["success"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

    def save(self):
        try:
            date = self.date_entry.get()
            amount = float(self.amount_entry.get())
            description = self.desc_entry.get()
            self.callback(date=date, amount=amount, description=description)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректную сумму")


class AddDepositAccountDialog(StyledDialog):
    def __init__(self, parent, callback):
        super().__init__(parent, "Добавить вклад/счет", 250, 275)
        self.callback = callback
        self.create_widgets()

    def create_widgets(self):
        frame_name = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_name.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_name,
            text="Название:",
            width=15,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.name_entry = tk.Entry(
            frame_name,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_type = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_type.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_type,
            text="Тип:",
            width=15,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.type_combo = ttk.Combobox(
            frame_type,
            values=["Вклад", "Накопительный счет", "Сберегательный счет"],
            font=("Calibri", 10),
            state="readonly",
        )
        self.type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.type_combo.set("Вклад")

        frame_amount = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_amount.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_amount,
            text="Текущая сумма (₽):",
            width=15,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.amount_entry = tk.Entry(
            frame_amount,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_rate = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_rate.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_rate,
            text="Ставка (%):",
            width=15,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.rate_entry = tk.Entry(
            frame_rate,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.rate_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_maturity = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_maturity.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_maturity,
            text="Дата погашения:",
            width=15,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.maturity_entry = tk.Entry(
            frame_maturity,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.maturity_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.maturity_entry.insert(0, "2025-12-31")

        frame_notes = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_notes.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            frame_notes,
            text="Примечания:",
            width=15,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.notes_entry = tk.Entry(
            frame_notes,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.notes_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(5, 0))
        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self.save,
            bg=COLORS["success"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

    def save(self):
        try:
            name = self.name_entry.get()
            acc_type = self.type_combo.get()
            amount = float(self.amount_entry.get())
            rate = float(self.rate_entry.get()) if self.rate_entry.get() else None
            maturity = self.maturity_entry.get() if self.maturity_entry.get() else None
            notes = self.notes_entry.get() if self.notes_entry.get() else None
            self.callback(name=name, acc_type=acc_type, amount=amount, rate=rate, maturity=maturity, notes=notes)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные данные")


class AddDepositPaymentDialog(StyledDialog):
    def __init__(self, parent, accounts, callback):
        super().__init__(parent, "Добавить выплату", 250, 185)
        self.accounts = accounts
        self.accounts_dict = {f"{acc[1]} ({acc[2]})": acc[0] for acc in accounts}
        self.callback = callback
        self.create_widgets()

    def create_widgets(self):
        frame_account = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_account.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_account,
            text="Счет:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.account_combo = ttk.Combobox(
            frame_account,
            values=list(self.accounts_dict.keys()),
            font=("Calibri", 10),
            state="readonly",
            width=30,
        )
        self.account_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_date = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_date.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_date,
            text="Дата:",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(
            frame_date,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_amount = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_amount.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            frame_amount,
            text="Сумма (₽):",
            width=12,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.amount_entry = tk.Entry(
            frame_amount,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(5, 0))
        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self.save,
            bg=COLORS["success"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

    def save(self):
        try:
            account_key = self.account_combo.get()
            account_id = self.accounts_dict[account_key]
            date = self.date_entry.get()
            amount = float(self.amount_entry.get())
            self.callback(account_id=account_id, date=date, amount=amount)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные данные")


class UpdateAccountDialog(StyledDialog):
    def __init__(self, parent, accounts, callback):
        super().__init__(parent, "Обновить сумму", 245, 150)
        self.accounts = accounts
        self.accounts_dict = {f"{acc[1]} ({acc[2]})": acc for acc in accounts}
        self.callback = callback
        self.create_widgets()

    def create_widgets(self):
        frame_account = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_account.pack(fill=tk.X, pady=(0, 8))
        tk.Label(frame_account, text="Счет:", width=15, anchor="w", font=("Calibri", 10),
                 bg=COLORS["bg_main"], fg=COLORS["text"]).pack(side=tk.LEFT)
        self.account_combo = ttk.Combobox(frame_account, values=list(self.accounts_dict.keys()),
                                          font=("Calibri", 10), state="readonly", width=30)
        self.account_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.account_combo.bind('<<ComboboxSelected>>', self.on_account_select)

        frame_amount = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_amount.pack(fill=tk.X, pady=(0, 8))
        tk.Label(frame_amount, text="Новая сумма (₽):", width=15, anchor="w", font=("Calibri", 10),
                 bg=COLORS["bg_main"], fg=COLORS["text"]).pack(side=tk.LEFT)
        self.amount_entry = tk.Entry(frame_amount, font=("Calibri", 10), bg="white",
                                     fg=COLORS["text"], relief="solid", bd=0, highlightthickness=1)
        self.amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(5, 0))
        tk.Button(btn_frame, text="Обновить", command=self.save,
                  bg=COLORS["success"], fg="white", font=("Calibri", 9),
                  relief="flat", padx=15, pady=5, cursor="hand2").pack(side="left", padx=(0, 10))
        tk.Button(btn_frame, text="Отмена", command=self.dialog.destroy,
                  bg=COLORS["danger"], fg="white", font=("Calibri", 9),
                  relief="flat", padx=15, pady=5, cursor="hand2").pack(side="left")

    def on_account_select(self, event):
        account_key = self.account_combo.get()
        if account_key in self.accounts_dict:
            acc = self.accounts_dict[account_key]
            self.amount_entry.delete(0, tk.END)
            self.amount_entry.insert(0, f"{float(acc[3]):.2f}")

    def save(self):
        try:
            account_key = self.account_combo.get()
            acc = self.accounts_dict[account_key]
            new_amount = float(self.amount_entry.get())
            self.callback(account_id=acc[0], new_amount=new_amount)
            self.dialog.destroy()
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Ошибка", "Введите корректную сумму")

class AddTaxDeductionDialog(StyledDialog):
    def __init__(self, parent, callback):
        super().__init__(parent, "Налоговый вычет", 280, 245)
        self.callback = callback
        self.create_widgets()

    def create_widgets(self):
        frame_date = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_date.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_date,
            text="Дата получения:",
            width=18,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(
            frame_date,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_type = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_type.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_type,
            text="Тип вычета:",
            width=18,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        deduction_types = ["ИИС тип А", "ИИС тип Б", "Социальный", "Имущественный", "Инвестиционный", "Другое"]
        self.type_combo = ttk.Combobox(frame_type, values=deduction_types, font=("Calibri", 10), state="readonly")
        self.type_combo.set("ИИС тип А")
        self.type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_year = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_year.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_year,
            text="За какой год:",
            width=18,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year - 5, current_year + 1)]
        self.year_combo = ttk.Combobox(frame_year, values=years, font=("Calibri", 10), state="readonly")
        self.year_combo.set(str(current_year - 1))
        self.year_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_amount = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_amount.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            frame_amount,
            text="Сумма (₽):",
            width=18,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.amount_entry = tk.Entry(
            frame_amount,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        frame_desc = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        frame_desc.pack(fill=tk.X, pady=(0, 15))
        tk.Label(
            frame_desc,
            text="Описание:",
            width=18,
            anchor="w",
            font=("Calibri", 10),
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT)
        self.desc_entry = tk.Entry(
            frame_desc,
            font=("Calibri", 10),
            bg="white",
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="solid",
            bd=0,
            highlightthickness=1,
        )
        self.desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        btn_frame = tk.Frame(self.main_frame, bg=COLORS["bg_main"])
        btn_frame.pack(pady=(5, 0))
        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self.save,
            bg=COLORS["success"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.dialog.destroy,
            bg=COLORS["danger"],
            fg="white",
            font=("Calibri", 9),
            relief="flat",
            padx=15,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

    def save(self):
        try:
            date = self.date_entry.get()
            deduction_type = self.type_combo.get()
            year = int(self.year_combo.get())
            amount = float(self.amount_entry.get())
            description = self.desc_entry.get()
            self.callback(date=date, amount=amount, deduction_type=deduction_type, description=description, year=year)
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректные данные")

