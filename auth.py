import base64
import hashlib
import hmac
import secrets

from db_config import create_connection


def _hash_password_pbkdf2(password: str, iterations: int = 260_000) -> str:
    """ PBKDF2-HMAC-SHA256.
        Формат хранения: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>"""

    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(dk).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"


def _verify_password_pbkdf2(password: str, stored: str) -> bool:
    try:
        algo, iters_str, salt_b64, hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iters_str)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except Exception:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def authenticate_user(username: str, password: str) -> int | None:
    """Возвращает id пользователя при успешной проверке логина/пароля."""
    conn = create_connection()
    if not conn:
        return None
    cur = conn.cursor()
    cur.execute("USE investment_portfolio")
    cur.execute("SELECT id, password_hash FROM users WHERE username = %s LIMIT 1", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    user_id, password_hash = row
    if _verify_password_pbkdf2(password, password_hash):
        return int(user_id)
    return None


def create_user(username: str, password: str) -> int | None:
    """Создаёт пользователя. Возвращает id или None при ошибке."""
    password_hash = _hash_password_pbkdf2(password)
    conn = create_connection()
    if not conn:
        return None
    cur = conn.cursor()
    cur.execute("USE investment_portfolio")
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, password_hash),
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
        return int(user_id)
    except Exception:
        conn.close()
        return None


def list_users() -> list[str]:
    conn = create_connection()
    if not conn:
        return []
    cur = conn.cursor()
    cur.execute("USE investment_portfolio")
    cur.execute("SELECT username FROM users ORDER BY username")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

