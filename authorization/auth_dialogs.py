import tkinter as tk
from tkinter import messagebox, ttk

from authorization.auth import authenticate_user, create_user, list_users
from config import COLORS


class SettingsDialog:
    """Окно настроек приложения."""
    def __init__(self, parent, current_theme_callback, switch_user_callback):
        self.parent = parent
        self.current_theme_callback = current_theme_callback
        self.switch_user_callback = switch_user_callback

        self.win = tk.Toplevel(parent)
        self.win.title("Настройки")
        self.win.geometry("250x200")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=COLORS["bg_main"])

        frame = tk.Frame(self.win, bg=COLORS["bg_main"])
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

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
            padx=20,
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
            padx=20,
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
        self.win.geometry("300x200")
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
    def __init__(self, parent, user_id):
        self.parent = parent
        self.user_id = user_id
        self.selected_assets = set()

        self.win = tk.Toplevel(parent)
        self.win.title("Выбор активов")
        self.win.geometry("650x550")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.configure(bg=COLORS["bg_main"])

        # Заголовок
        tk.Label(self.win, text="Выберите ваши активы", font=("Calibri", 14, "bold"),
                 bg=COLORS["bg_main"], fg=COLORS["accent"]).pack(pady=(10, 5))

        # Поиск
        search_frame = tk.Frame(self.win, bg=COLORS["bg_main"])
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(search_frame, text="🔍 Поиск:", bg=COLORS["bg_main"], fg=COLORS["text"]).pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame, width=30, bg="white", fg=COLORS["text"])
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', self.filter_assets)

        # Загружаем все активы
        from config import STOCKS, BONDS, TICKER_NAMES
        self.all_assets = []
        for t in STOCKS:
            self.all_assets.append((t, 'Акция', TICKER_NAMES.get(t, t)))
        for t in BONDS:
            self.all_assets.append((t, 'Облигация', TICKER_NAMES.get(t, t)))

        # Загружаем выбранные ранее активы
        self.load_selected_assets()

        # Таблица
        columns = ('selected', 'type', 'ticker', 'name')
        self.tree = ttk.Treeview(self.win, columns=columns, show='headings', height=20)
        self.tree.heading('selected', text='✓')
        self.tree.heading('type', text='Тип')
        self.tree.heading('ticker', text='Тикер')
        self.tree.heading('name', text='Название')
        self.tree.column('selected', width=40, anchor='center')
        self.tree.column('type', width=100, anchor='center')
        self.tree.column('ticker', width=120, anchor='center')
        self.tree.column('name', width=250)

        self.tree.bind('<Button-1>', self.on_click)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10)

        # Кнопки
        btn_frame = tk.Frame(self.win, bg=COLORS["bg_main"])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(btn_frame, text="Сохранить", command=self.save,
                  bg=COLORS["success"], fg="white", relief="flat", padx=20, pady=8,
                  cursor="hand2").pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(btn_frame, text="Отмена", command=self.win.destroy,
                  bg=COLORS["danger"], fg="white", relief="flat", padx=20, pady=8,
                  cursor="hand2").pack(side=tk.RIGHT)

        self.show_all()

    def load_selected_assets(self):
        from db_config import create_connection
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            cursor.execute("SELECT ticker FROM user_assets WHERE user_id = %s AND is_active = TRUE", (self.user_id,))
            self.selected_assets = set(row[0] for row in cursor.fetchall())
            conn.close()

    def save(self):
        from db_config import create_connection
        conn = create_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("USE investment_portfolio")
            # Удаляем старые
            cursor.execute("DELETE FROM user_assets WHERE user_id = %s", (self.user_id,))
            # Вставляем новые
            for ticker in self.selected_assets:
                sec_type = 'stock' if ticker in STOCKS else 'bond'
                cursor.execute("INSERT INTO user_assets (user_id, ticker, security_type) VALUES (%s, %s, %s)",
                               (self.user_id, ticker, sec_type))
            conn.commit()
            conn.close()
        self.win.destroy()

    def show_all(self):
        self.show_filtered(self.all_assets)

    def filter_assets(self, event=None):
        query = self.search_entry.get().lower()
        filtered = [(t, s, n) for t, s, n in self.all_assets
                    if query in t.lower() or query in n.lower()]
        self.show_filtered(filtered)

    def show_filtered(self, assets):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for ticker, sec_type, name in assets:
            selected = ticker in self.selected_assets
            self.tree.insert('', tk.END, values=('✓' if selected else '○', sec_type, ticker, name))

    def on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if col == '#1' and item:
            values = self.tree.item(item, 'values')
            ticker = values[2]
            if ticker in self.selected_assets:
                self.selected_assets.remove(ticker)
                self.tree.item(item, values=('○', values[1], values[2], values[3]))
            else:
                self.selected_assets.add(ticker)
                self.tree.item(item, values=('✓', values[1], values[2], values[3]))