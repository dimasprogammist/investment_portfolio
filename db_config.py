import os
import base64
import hashlib
import secrets
import sys

import mysql.connector
from mysql.connector import Error


def _load_dotenv_if_present(path: str | None = None) -> None:
    """
    Загрузка файла .env

    - Загружает строки вида KEY=VALUE
    - Не переопределяет уже заданные переменные окружения
    """
    try:
        # По умолчанию ищем .env рядом с исходниками проекта, а не в cwd.
        # Это важно при запуске из IDE/планировщика/собранного exe.
        if path is None:
            env_path = os.getenv("MOEX_ENV_PATH")
            if env_path:
                path = env_path
            else:
                if getattr(sys, "frozen", False):
                    base_dir = os.path.dirname(sys.executable)
                else:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(base_dir, ".env")

        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if not key:
                    continue
                os.environ.setdefault(key, value)
    except OSError:
        return


def _load_db_config() -> dict:
    """
    Возвращает параметры подключения к MySQL из переменных окружения.

    Важно: пароль не должен храниться в исходниках. Задайте его через переменную
    `MOEX_DB_PASSWORD` (или `MYSQL_PWD`).
    """
    port_raw = os.getenv("MOEX_DB_PORT", "3306")
    try:
        port = int(port_raw)
    except ValueError:
        port = 3306

    password = os.getenv("MOEX_DB_PASSWORD") or os.getenv("MYSQL_PWD") or ""

    return {
        "host": os.getenv("MOEX_DB_HOST", "localhost"),
        "port": port,
        "user": os.getenv("MOEX_DB_USER", "portfolio_app"),
        "password": password,
        "database": os.getenv("MOEX_DB_NAME", "investment_portfolio"),
    }


def create_connection():
    """Создаёт соединение с базой данных MySQL."""
    try:
        _load_dotenv_if_present()
        db_config = _load_db_config()
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        # Не логируем конфиг, чтобы случайно не вывести пароль.
        print(f"Ошибка подключения к MySQL: {e}")
        return None


def init_db():
    """
    Создаёт/обновляет схему БД.
    """
    conn = create_connection()
    if not conn:
        print("Не удалось подключиться к MySQL. Проверьте параметры подключения.")
        return False

    cursor = conn.cursor()

    # Создаём базу данных, если её нет
    cursor.execute("CREATE DATABASE IF NOT EXISTS investment_portfolio")
    cursor.execute("USE investment_portfolio")

    # Пользователи
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(64) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    def _hash_password_pbkdf2(password: str, iterations: int = 260_000) -> str:
        """
        PBKDF2-HMAC-SHA256.
        Формат хранения: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
        """
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        salt_b64 = base64.b64encode(salt).decode("ascii")
        hash_b64 = base64.b64encode(dk).decode("ascii")
        return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"

    # Создаём первого пользователя по умолчанию
    cursor.execute("SELECT id FROM users WHERE username = %s LIMIT 1", ("admin",))
    if cursor.fetchone() is None:
        admin_password = os.getenv("MOEX_ADMIN_PASSWORD", "admin")
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            ("admin", _hash_password_pbkdf2(admin_password)),
        )

    # Таблица пополнений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            amount DECIMAL(12,2) NOT NULL
        )
    ''')

    # Таблица сделок с акциями
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_trades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            operation VARCHAR(4) NOT NULL,
            quantity DECIMAL(12,2) NOT NULL,
            price DECIMAL(12,2) NOT NULL,
            total_amount DECIMAL(12,2) NOT NULL
        )
    ''')

    # Таблица сделок с облигациями
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bond_trades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            operation VARCHAR(4) NOT NULL,
            quantity DECIMAL(12,2) NOT NULL,
            price DECIMAL(12,2) NOT NULL,
            total_amount DECIMAL(12,2) NOT NULL
        )
    ''')

    # Таблица дивидендов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dividends (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            quantity DECIMAL(12,2) DEFAULT 0,
            amount DECIMAL(12,2) NOT NULL,
            avg_price DECIMAL(12,2) DEFAULT NULL
        )
    ''')

    # Проверяем, существует ли столбец avg_price в dividends
    cursor.execute("SHOW COLUMNS FROM dividends LIKE 'avg_price'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE dividends ADD COLUMN avg_price DECIMAL(12,2) DEFAULT NULL")
        print("Добавлен столбец avg_price в таблицу dividends")

    # Таблица купонов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            quantity DECIMAL(12,2) DEFAULT 0,
            amount DECIMAL(12,2) NOT NULL
        )
    ''')

    # Таблица налогов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS taxes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            description TEXT
        )
    ''')

    # Таблица погашений облигаций
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bond_redemptions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            quantity DECIMAL(12,2) NOT NULL,
            price DECIMAL(12,2) NOT NULL,
            total_amount DECIMAL(12,2) NOT NULL
        )
    ''')

    # Таблица возвратов налогов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_refunds (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            description TEXT
        )
    ''')

    # Таблица вкладов (сами счета)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposits_accounts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50) NOT NULL,
            current_amount DECIMAL(12,2) NOT NULL,
            interest_rate DECIMAL(5,2),
            maturity_date DATE,
            notes TEXT
        )
    ''')

    # Таблица выплат по вкладам (проценты)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deposit_payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_id INT NOT NULL,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            FOREIGN KEY (account_id) REFERENCES deposits_accounts(id) ON DELETE CASCADE
        )
    ''')

    # Таблица налоговых вычетов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_deductions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL DEFAULT 1,
            date DATE NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            type VARCHAR(50) NOT NULL,
            description TEXT,
            year INT
        )
    ''')

    # Проверяем, существует ли колонка year в tax_deductions
    cursor.execute("SHOW COLUMNS FROM tax_deductions LIKE 'year'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE tax_deductions ADD COLUMN year INT")
        print("Добавлена колонка year в таблицу tax_deductions")

    # Проверяем, существует ли колонка type в tax_deductions
    cursor.execute("SHOW COLUMNS FROM tax_deductions LIKE 'type'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE tax_deductions ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'ИИС тип А'")
        print("Добавлена колонка type в таблицу tax_deductions")

    # Таблица исторических цен для графиков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_prices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            price DECIMAL(12,2) NOT NULL,
            security_type VARCHAR(10) NOT NULL,
            UNIQUE KEY unique_date_ticker (date, ticker)
        )
    ''')

    # Добавление user_id в старые таблицы
    # Если таблицы были созданы ранее (без user_id), добавляем колонку.
    user_tables = [
        ("deposits",),
        ("stock_trades",),
        ("bond_trades",),
        ("dividends",),
        ("coupons",),
        ("taxes",),
        ("bond_redemptions",),
        ("tax_refunds",),
        ("deposits_accounts",),
        ("deposit_payments",),
        ("tax_deductions",),
    ]
    for (table_name,) in user_tables:
        cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE 'user_id'")
        if not cursor.fetchone():
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN user_id INT NOT NULL DEFAULT 1")

    cursor.execute(
        """
        SELECT CONSTRAINT_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'deposits'
          AND COLUMN_NAME = 'user_id'
          AND REFERENCED_TABLE_NAME = 'users'
        LIMIT 1
        """
    )
    if cursor.fetchone() is None:
        for table_name in [
            "deposits",
            "stock_trades",
            "bond_trades",
            "dividends",
            "coupons",
            "taxes",
            "bond_redemptions",
            "tax_refunds",
            "deposits_accounts",
            "deposit_payments",
            "tax_deductions",
        ]:
            try:
                cursor.execute(
                    f"ALTER TABLE {table_name} "
                    f"ADD CONSTRAINT fk_{table_name}_user "
                    f"FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE"
                )
            except Error:
                # Если ограничение уже создано или таблица не поддерживает, просто пропускаем.
                pass

    conn.commit()
    cursor.close()
    conn.close()
    print("База данных успешно инициализирована")
    return True


if __name__ == "__main__":
    init_db()