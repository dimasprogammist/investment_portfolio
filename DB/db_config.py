import os
import base64
import hashlib
import secrets
import sys
import datetime

import mysql.connector
from mysql.connector import Error


def _load_dotenv_if_present(path: str | None = None) -> None:
    """Загрузка файла .env"""
    try:
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
    """Параметры подключения к MySQL из переменных окружения."""
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
        print(f"Ошибка подключения к MySQL: {e}")
        return None


def init_db():
    """
    Инициализация БД:
    1. Выполняет init_db.sql (создание схемы)
    2. Применяет миграции (ALTER TABLE для старых таблиц)
    3. Создаёт пользователя admin
    4. Обновляет список доступных активов (раз в неделю)
    """
    import os
    conn = create_connection()
    if not conn:
        print("Не удалось подключиться к MySQL.")
        return False

    cursor = conn.cursor()

    # Создаём базу
    cursor.execute("CREATE DATABASE IF NOT EXISTS investment_portfolio")
    cursor.execute("USE investment_portfolio")

    # 1. Выполняем SQL-файл со схемой
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'init_db.sql')
    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql = f.read()
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for statement in statements:
                try:
                    cursor.execute(statement)
                except Error as e:
                    print(f"SQL ошибка (пропущено): {e}")
    except FileNotFoundError:
        print(f"Файл init_db.sql не найден по пути: {sql_path}")

    # 2. Миграции для существующих таблиц
    _apply_migrations(cursor)

    # 3. Создаём admin
    cursor.execute("SELECT id FROM users WHERE username = 'admin' LIMIT 1")
    if cursor.fetchone() is None:
        admin_password = os.getenv("MOEX_ADMIN_PASSWORD", "admin")
        pwd = _hash_password_pbkdf2(admin_password)
        cursor.execute("INSERT INTO users (username, password_hash) VALUES ('admin', %s)", (pwd,))

    conn.commit()
    cursor.close()
    conn.close()
    print("База данных успешно инициализирована")

    # 4. Обновляем список доступных активов (раз в неделю)
    import os
    asset_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'last_asset_update.txt')
    need_update = True
    if os.path.exists(asset_file):
        try:
            with open(asset_file) as f:
                last_update = datetime.fromisoformat(f.read().strip())
                need_update = (datetime.now() - last_update).days > 7
        except:
            pass

    if need_update:
        print("Обновление списка активов с MOEX...")
        from prices import update_available_assets
        try:
            update_available_assets()
            with open(asset_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            print(f"Не удалось обновить список активов: {e}")

    return True


def _hash_password_pbkdf2(password: str, iterations: int = 260_000) -> str:
    """PBKDF2-HMAC-SHA256."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(dk).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"


def _apply_migrations(cursor):
    """Применяет миграции для существующих таблиц (ALTER TABLE)."""
    migrations = [
        # avg_price в dividends
        ("dividends", "avg_price", "DECIMAL(12,2) DEFAULT NULL"),
        # year в tax_deductions
        ("tax_deductions", "year", "INT"),
        # type в tax_deductions
        ("tax_deductions", "type", "VARCHAR(50) NOT NULL DEFAULT 'ИИС тип А'"),
        # user_id в старых таблицах
        ("deposits", "user_id", "INT NOT NULL DEFAULT 1"),
        ("stock_trades", "user_id", "INT NOT NULL DEFAULT 1"),
        ("bond_trades", "user_id", "INT NOT NULL DEFAULT 1"),
        ("dividends", "user_id", "INT NOT NULL DEFAULT 1"),
        ("coupons", "user_id", "INT NOT NULL DEFAULT 1"),
        ("taxes", "user_id", "INT NOT NULL DEFAULT 1"),
        ("bond_redemptions", "user_id", "INT NOT NULL DEFAULT 1"),
        ("tax_refunds", "user_id", "INT NOT NULL DEFAULT 1"),
        ("deposits_accounts", "user_id", "INT NOT NULL DEFAULT 1"),
        ("deposit_payments", "user_id", "INT NOT NULL DEFAULT 1"),
        ("tax_deductions", "user_id", "INT NOT NULL DEFAULT 1"),
    ]

    for table, column, col_type in migrations:
        try:
            cursor.execute(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                print(f"Добавлена колонка {column} в {table}")
        except Error:
            pass  # Таблицы может не существовать

    # Внешние ключи
    try:
        cursor.execute("""
            SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'deposits' AND COLUMN_NAME = 'user_id'
              AND REFERENCED_TABLE_NAME = 'users' LIMIT 1
        """)
        if cursor.fetchone() is None:
            fk_tables = ["deposits", "stock_trades", "bond_trades", "dividends",
                        "coupons", "taxes", "bond_redemptions", "tax_refunds",
                        "deposits_accounts", "deposit_payments", "tax_deductions"]
            for table in fk_tables:
                try:
                    cursor.execute(f"""ALTER TABLE {table} ADD CONSTRAINT fk_{table}_user
                                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE""")
                except Error:
                    pass
    except Error:
        pass


if __name__ == "__main__":
    init_db()