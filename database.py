import os
import time
import logging
import threading

from pathlib import Path

import pymysql
from dbutils.pooled_db import PooledDB


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

DB_SSL_CA = BASE_DIR / "aiven-ca.pem"


# =========================================================
# GLOBAL CONNECTION POOL
# =========================================================

_db_pool = None
_pool_lock = threading.Lock()


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

def get_db_config():

    required_vars = (
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
    )

    missing = [
        name
        for name in required_vars
        if not os.getenv(name)
    ]

    if missing:
        raise RuntimeError(
            "Missing required database environment variables: "
            + ", ".join(missing)
        )

    if not DB_SSL_CA.is_file():
        raise FileNotFoundError(
            f"Aiven CA certificate not found: {DB_SSL_CA}"
        )

    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ["DB_PORT"]),
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "database": os.environ["DB_NAME"],

        "ssl": {
            "ca": str(DB_SSL_CA)
        },

        "connect_timeout": 10,

        "read_timeout": 30,
        "write_timeout": 30,

        "charset": "utf8mb4",

        "cursorclass": pymysql.cursors.DictCursor
    }


# =========================================================
# CREATE CONNECTION POOL
# =========================================================

def get_db_pool():

    global _db_pool

    if _db_pool is None:

        with _pool_lock:

            if _db_pool is None:

                config = get_db_config()

                # Keep the pool small in serverless instances.
                default_max = (
                    "2" if os.getenv("VERCEL") else "5"
                )

                max_connections = int(
                    os.getenv(
                        "DB_POOL_MAX_CONNECTIONS",
                        default_max
                    )
                )

                max_cached = int(
    os.getenv("DB_POOL_MAX_CACHED", str(max_connections))
)

                if max_connections < 1:
                    raise ValueError(
                        "DB_POOL_MAX_CONNECTIONS must be at least 1"
                    )

                if max_cached < 0:
                    raise ValueError(
                        "DB_POOL_MAX_CACHED cannot be negative"
                    )

                max_cached = min(
                    max_cached,
                    max_connections
                )

                logger.info(
                    "Initializing MySQL connection pool | max=%d | cached=%d",
                    max_connections,
                    max_cached
                )

                _db_pool = PooledDB(

                    creator=pymysql,

                    mincached=0,

                    maxcached=max_cached,

                    maxshared=0,

                    maxconnections=max_connections,

                    blocking=True,

                    maxusage=500,

                    ping=1,

                    **config
                )

    return _db_pool


# =========================================================
# GET DATABASE CONNECTION
# =========================================================

def get_db():

    start = time.perf_counter()

    try:

        pool = get_db_pool()

        connection = pool.connection()

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        logger.info(
            "PERF | MySQL pool checkout | %.2f ms",
            elapsed_ms
        )

        return connection

    except Exception:

        logger.exception(
            "MySQL connection pool checkout failed"
        )

        raise