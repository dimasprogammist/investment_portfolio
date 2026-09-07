"""Резервная копия MySQL через mysqldump или выгрузку таблиц."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

from services.app_log import get_logger

log = get_logger()


def _project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def backup_database(dest_dir: str | None = None) -> str:
    from DB.db_config import _load_db_config, _load_dotenv_if_present

    _load_dotenv_if_present()
    cfg = _load_db_config()
    dest_dir = dest_dir or os.path.join(_project_root(), "backups")
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")

    env = os.environ.copy()
    if cfg.get("password"):
        env["MYSQL_PWD"] = cfg["password"]

    cmd = [
        "mysqldump",
        f"--host={cfg['host']}",
        f"--port={cfg['port']}",
        f"--user={cfg['user']}",
        "--routines",
        "--single-transaction",
        cfg["database"],
    ]
    try:
        with open(path, "w", encoding="utf-8") as out:
            proc = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, env=env, text=True, timeout=120)
        if proc.returncode == 0 and os.path.getsize(path) > 0:
            log.info("Бэкап mysqldump: %s", path)
            return path
        log.warning("mysqldump не удался: %s", proc.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        log.info("mysqldump недоступен (%s), пишем Python-дамп", exc)

    _python_dump(cfg["database"], path)
    return path


def _python_dump(database: str, path: str) -> None:
    from DB.db_config import create_connection

    conn = create_connection()
    if not conn:
        raise RuntimeError("Нет подключения к MySQL для бэкапа")
    cursor = conn.cursor()
    cursor.execute(f"USE `{database}`")
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Python dump {datetime.now().isoformat()}\n")
        f.write(f"CREATE DATABASE IF NOT EXISTS `{database}`;\nUSE `{database}`;\n")
        for table in tables:
            cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create_sql = cursor.fetchone()[1]
            f.write(f"\nDROP TABLE IF EXISTS `{table}`;\n{create_sql};\n")
            cursor.execute(f"SELECT * FROM `{table}`")
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            for row in rows:
                values = []
                for value in row:
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    else:
                        escaped = str(value).replace("\\", "\\\\").replace("'", "''")
                        values.append(f"'{escaped}'")
                f.write(f"INSERT INTO `{table}` ({', '.join('`'+c+'`' for c in cols)}) VALUES ({', '.join(values)});\n")
    conn.close()
    log.info("Python-дамп: %s", path)
