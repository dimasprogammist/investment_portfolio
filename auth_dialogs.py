import tkinter as tk
from tkinter import messagebox, ttk

from auth import authenticate_user, create_user, list_users
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

