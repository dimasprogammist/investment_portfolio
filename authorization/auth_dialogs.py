import tkinter as tk
from tkinter import messagebox, ttk

from authorization.auth import authenticate_user, create_user, list_users
from config import COLORS


class SettingsDialog:
    """Окно настроек приложения."""
    def __init__(self, parent, current_theme_callback, switch_user_callback, user_id=None):
        self.parent = parent
        self.current_theme_callback = current_theme_callback
        self.switch_user_callback = switch_user_callback
        self.user_id = user_id

        self.win = tk.Toplevel(parent)
        self.win.title("Настройки")
        self.win.geometry("235x225")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=COLORS["bg_main"])

        frame = tk.Frame(self.win, bg=COLORS["bg_main"])
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=20)

        # Заголовок
        tk.Label(
            frame,
            text="Настройки",
            font=("Calibri", 14, "bold"),
            bg=COLORS["bg_main"],
            fg=COLORS["accent"],
        ).pack(pady=(0, 20))

        # Переключатель темы
        theme_frame = tk.Frame(frame, bg=COLORS["bg_main"])
        theme_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            theme_frame,
            text="Тема:",
            font=("Calibri", 11),
            bg=COLORS["bg_main"],
            fg=COLORS["text"]
        ).pack(side=tk.LEFT)

        self.theme_var = tk.StringVar(value="light")

        self.theme_light = tk.Radiobutton(
            theme_frame,
            text="Светлая",
            variable=self.theme_var,
            value="light",
            command=self._on_theme_change,
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
            selectcolor=COLORS["bg_main"],
            activebackground=COLORS["bg_main"],
            activeforeground=COLORS["text"],
            font=("Calibri", 10)
        )
        self.theme_light.pack(side=tk.LEFT, padx=(10, 0))

        self.theme_dark = tk.Radiobutton(
            theme_frame,
            text="Тёмная",
            variable=self.theme_var,
            value="dark",
            command=self._on_theme_change,
            bg=COLORS["bg_main"],
            fg=COLORS["text"],
            selectcolor=COLORS["bg_main"],
            activebackground=COLORS["bg_main"],
            activeforeground=COLORS["text"],
            font=("Calibri", 10)
        )
        self.theme_dark.pack(side=tk.LEFT, padx=(10, 0))

        # Кнопка смены пользователя
        tk.Button(
            frame,
            text="Сменить\nпользователя",
            command=self._switch_user,
            bg=COLORS["info"],
            fg="white",
            font=("Calibri", 10),
            relief="flat",
            cursor="hand2",
            padx=5,
            pady=5,
            height=1,
            width=80,
        ).pack(pady=(0, 5))

        tk.Button(
            frame,
            text="Выбрать\nактивы",
            command=self._open_assets,
            bg=COLORS["info"],
            fg="white",
            font=("Calibri", 10),
            relief="flat",
            cursor="hand2",
            padx=5,
            pady=5,
            height=1,
            width=80,
        ).pack(pady=(0, 5))

        # Кнопка закрытия
        tk.Button(
            frame,
            text="Закрыть",
            command=self.win.destroy,
            bg=COLORS["bg_header"],
            fg=COLORS["text"],
            font=("Calibri", 10),
            relief="flat",
            cursor="hand2",
            padx=5,
            pady=5,
            height=2,
            width=80,
        ).pack()

        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

    def _on_theme_change(self):
        theme = self.theme_var.get()
        self.current_theme_callback(theme)

    def _switch_user(self):
        self.win.destroy()
        self.switch_user_callback()

    def _open_assets(self):
        """Открывает окно выбора активов"""
        # Получаем user_id из основного приложения
        # Нужно передать его при создании SettingsDialog
        AssetSelectionDialog(self.parent, self.user_id)

class LoginDialog:
    """Диалог входа/выбора пользователя. Возвращает user_id при успехе."""
    def __init__(self, parent):
        self.parent = parent
        self.user_id: int | None = None

        self.win = tk.Toplevel(parent)
        self.win.title("Вход")
        self.win.geometry("300x195")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=COLORS["bg_main"])

        frame = tk.Frame(self.win, bg=COLORS["bg_main"])
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        tk.Label(
            frame,
            text="Авторизация",
            font=("Calibri", 12, "bold"),
            bg=COLORS["bg_main"],
            fg=COLORS["accent"],
        ).pack(pady=(0, 10))

        users = list_users()
        tk.Label(frame, text="Пользователь:", bg=COLORS["bg_main"], fg=COLORS["text"]).pack(anchor="w")
        self.user_combo = ttk.Combobox(frame, values=users, state="readonly")
        self.user_combo.pack(fill=tk.X, pady=(0, 8))
        if users:
            self.user_combo.set(users[0])

        tk.Label(frame, text="Пароль:", bg=COLORS["bg_main"], fg=COLORS["text"]).pack(anchor="w")
        self.pw_entry = tk.Entry(frame, show="*")
        self.pw_entry.pack(fill=tk.X, pady=(0, 12))

        btns = tk.Frame(frame, bg=COLORS["bg_main"])
        btns.pack(fill=tk.X)

        tk.Button(
            btns,
            text="Войти",
            command=self._login,
            bg=COLORS["success"],
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            width=8,
        ).pack(side=tk.LEFT)

        tk.Button(
            btns,
            text="Создать \nпользователя",
            command=self._register,
            bg=COLORS["info"],
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=6,
            width=8,
        ).pack(side=tk.LEFT, padx=8)

        tk.Button(
            btns,
            text="Выход",
            command=self._cancel,
            bg=COLORS["danger"],
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
            width=8,
        ).pack(side=tk.RIGHT)

        self.win.protocol("WM_DELETE_WINDOW", self._cancel)
        self.pw_entry.bind("<Return>", lambda _e: self._login())

    def _login(self):
        username = self.user_combo.get().strip()
        password = self.pw_entry.get()
        if not username:
            messagebox.showerror("Ошибка", "Выберите пользователя")
            return
        uid = authenticate_user(username, password)
        if uid is None:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
            return
        self.user_id = uid
        self.win.destroy()

    def _register(self):
        RegisterDialog(self.win)
        # обновим список пользователей
        users = list_users()
        self.user_combo.configure(values=users)
        if users and not self.user_combo.get():
            self.user_combo.set(users[0])

    def _cancel(self):
        self.user_id = None
        self.win.destroy()

    def show(self) -> int | None:
        self.parent.wait_window(self.win)
        return self.user_id


class RegisterDialog:
    """Простой диалог создания пользователя."""

    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("Новый пользователь")
        self.win.geometry("250x200")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=COLORS["bg_main"])

        frame = tk.Frame(self.win, bg=COLORS["bg_main"])
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        tk.Label(
            frame,
            text="Создать пользователя",
            font=("Calibri", 12, "bold"),
            bg=COLORS["bg_main"],
            fg=COLORS["accent"],
        ).pack(pady=(0, 10))

        tk.Label(frame, text="Логин:", bg=COLORS["bg_main"], fg=COLORS["text"]).pack(anchor="w")
        self.user_entry = tk.Entry(frame)
        self.user_entry.pack(fill=tk.X, pady=(0, 8))

        tk.Label(frame, text="Пароль:", bg=COLORS["bg_main"], fg=COLORS["text"]).pack(anchor="w")
        self.pw1 = tk.Entry(frame, show="*")
        self.pw1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(frame, text="Повтор пароля:", bg=COLORS["bg_main"], fg=COLORS["text"]).pack(anchor="w")
        self.pw2 = tk.Entry(frame, show="*")
        self.pw2.pack(fill=tk.X, pady=(0, 12))

        btns = tk.Frame(frame, bg=COLORS["bg_main"])
        btns.pack(fill=tk.X)

        tk.Button(
            btns,
            text="Создать",
            command=self._create,
            bg=COLORS["success"],
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
        ).pack(side=tk.LEFT)

        tk.Button(
            btns,
            text="Отмена",
            command=self.win.destroy,
            bg=COLORS["danger"],
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            pady=6,
        ).pack(side=tk.RIGHT)

    def _create(self):
        username = self.user_entry.get().strip()
        pw1 = self.pw1.get()
        pw2 = self.pw2.get()
        if not username:
            messagebox.showerror("Ошибка", "Введите логин")
            return
        if not pw1:
            messagebox.showerror("Ошибка", "Введите пароль")
            return
        if pw1 != pw2:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return
        uid = create_user(username, pw1)
        if uid is None:
            messagebox.showerror("Ошибка", "Не удалось создать пользователя (возможно, логин уже занят)")
            return
        messagebox.showinfo("Готово", "Пользователь создан")
        self.win.destroy()


class AssetSelectionDialog:
    """Окно выбора активов пользователя"""

    def __init__(self, parent, user_id):
        self.parent = parent
        self.user_id = user_id
        self.selected_stocks = set()
        self.selected_bonds = set()
        self.all_stocks = []
        self.all_bonds = []

        self.win = tk.Toplevel(parent)
        self.win.title("Выбор активов")
        self.win.geometry("800x600")
        self.win.resizable(True, True)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=COLORS["bg_main"])

        # Загружаем данные
        self.load_available_assets()
        self.load_selected_assets()

        # Заголовок
        header = tk.Frame(self.win, bg=COLORS["bg_main"])
        header.pack(fill=tk.X, padx=15, pady=(15, 10))

        tk.Label(header, text="Выбор активов", font=("Calibri", 16, "bold"),
                 bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(side=tk.LEFT)

        self.counter_label = tk.Label(header, text="", font=("Calibri", 9),
                                      bg=COLORS["bg_main"], fg=COLORS["text_secondary"])
        self.counter_label.pack(side=tk.RIGHT)
        self.update_counter()

        # Вкладки Акции / Облигации
        notebook = ttk.Notebook(self.win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        self.create_tab(notebook, "Акции", self.all_stocks, 'stock')
        self.create_tab(notebook, "Облигации", self.all_bonds, 'bond')

        # Кнопка закрытия
        tk.Button(self.win, text="Закрыть", command=self.win.destroy,
                  bg=COLORS["bg_header"], fg=COLORS["text"], font=("Calibri", 11),
                  relief="flat", padx=25, pady=8, cursor="hand2").pack(pady=(0, 15))

    def update_counter(self):
        """Обновляет счетчик выбранных активов"""
        self.counter_label.config(
            text=f"Выбрано: {len(self.selected_stocks)} акций, {len(self.selected_bonds)} облигаций"
        )

    def load_available_assets(self):
        """Загружает список всех доступных активов из БД"""
        from DB.db_config import create_connection
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute(
                "SELECT ticker, name, security_type FROM available_assets WHERE is_active = TRUE ORDER BY security_type, ticker"
            )
            for ticker, name, sec_type in cursor.fetchall():
                if sec_type == 'stock':
                    self.all_stocks.append((ticker, name or ticker))
                else:
                    self.all_bonds.append((ticker, name or ticker))
            conn.close()

    def load_selected_assets(self):
        """Загружает выбранные активы из БД"""
        from DB.db_config import create_connection
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute("""
                SELECT ticker, security_type FROM user_assets 
                WHERE user_id = %s AND is_active = TRUE
            """, (self.user_id,))
            for ticker, sec_type in cursor.fetchall():
                if sec_type == 'stock':
                    self.selected_stocks.add(ticker)
                else:
                    self.selected_bonds.add(ticker)
            conn.close()

    def save_asset(self, ticker, sec_type, add):
        """Сохраняет или удаляет актив в БД мгновенно"""
        from DB.db_config import create_connection
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            if add:
                cursor.execute("""
                    INSERT INTO user_assets (user_id, ticker, security_type, is_active)
                    VALUES (%s, %s, %s, TRUE)
                    ON DUPLICATE KEY UPDATE is_active = TRUE
                """, (self.user_id, ticker, sec_type))
            else:
                cursor.execute("""
                    UPDATE user_assets SET is_active = FALSE 
                    WHERE user_id = %s AND ticker = %s
                """, (self.user_id, ticker))
            conn.commit()
            conn.close()

    def create_tab(self, notebook, title, assets, sec_type):
        """Создаёт вкладку с таблицей активов"""
        frame = tk.Frame(notebook, bg=COLORS["bg_main"])
        notebook.add(frame, text=f"{title} ({len(assets)})")

        # Поиск
        search_frame = tk.Frame(frame, bg=COLORS["bg_main"])
        search_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(search_frame, text="🔍", font=("Calibri", 12),
                 bg=COLORS["bg_main"]).pack(side=tk.LEFT, padx=(0, 5))
        search_entry = tk.Entry(search_frame, font=("Calibri", 11), width=30)
        search_entry.pack(side=tk.LEFT)

        # Таблица
        tree_frame = tk.Frame(frame, bg=COLORS["bg_main"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        tree = ttk.Treeview(tree_frame, columns=('✓', 'ticker', 'name'), show='headings', height=20)
        tree.heading('✓', text='✓')
        tree.heading('ticker', text='Тикер')
        tree.heading('name', text='Название')
        tree.column('✓', width=40, anchor='center')
        tree.column('ticker', width=150, anchor='center')
        tree.column('name', width=350, anchor='center')

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.fill_tree(tree, assets, sec_type)

        search_entry.bind('<KeyRelease>', lambda e, t=tree, a=assets, s=search_entry:
        self.fill_tree(t, a, sec_type, s.get()))

        tree.bind('<Button-1>', lambda e, t=tree, st=sec_type: self.on_tree_click(e, t, st))

        if sec_type == 'stock':
            self.stocks_tree = tree
        else:
            self.bonds_tree = tree

    def fill_tree(self, tree, assets, sec_type, filter_text=''):
        """Заполняет таблицу активами"""
        for item in tree.get_children():
            tree.delete(item)

        selected_set = self.selected_stocks if sec_type == 'stock' else self.selected_bonds

        for ticker, name in assets:
            if filter_text and filter_text.lower() not in ticker.lower() and filter_text.lower() not in name.lower():
                continue
            check = '✓' if ticker in selected_set else '○'
            tree.insert('', tk.END, values=(check, ticker, name))

    def on_tree_click(self, event, tree, sec_type):
        """Обрабатывает клик по чекбоксу — СОХРАНЯЕТ СРАЗУ"""
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = tree.identify_column(event.x)
        if column != '#1':
            return

        item = tree.identify_row(event.y)
        if not item:
            return

        values = tree.item(item, 'values')
        ticker = values[1]

        selected_set = self.selected_stocks if sec_type == 'stock' else self.selected_bonds

        if ticker in selected_set:
            selected_set.remove(ticker)
            tree.item(item, values=('○', ticker, values[2]))
            self.save_asset(ticker, sec_type, False)
        else:
            selected_set.add(ticker)
            tree.item(item, values=('✓', ticker, values[2]))
            self.save_asset(ticker, sec_type, True)

        self.update_counter()