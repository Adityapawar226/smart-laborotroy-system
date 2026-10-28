import os
import time
import logging
from pathlib import Path

import pymysql
from pymysqlpool import ConnectionPool

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_SSL_CA = BASE_DIR / "aiven-ca.pem"

_pool = None


def initialize_db_pool():
    """
    Initialize one small PyMySQL connection pool per Python process.
    Requires DB_HOST, DB_PORT, DB_USER, DB_PASSWORD and DB_NAME.
    """

    global _pool

    if _pool is not None:
        return _pool

    required_vars = (
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
    )

    missing = [
        name for name in required_vars
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

    start = time.perf_counter()

    try:
        _pool = ConnectionPool(
            size=3,
            maxsize=5,
            host=os.environ["DB_HOST"],
            port=int(os.environ["DB_PORT"]),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"],
            ssl={"ca": str(DB_SSL_CA)},
            connect_timeout=10,
            autocommit=False
        )

        logger.info(
            "PERF | PyMySQL connection pool initialized | %.2f ms",
            (time.perf_counter() - start) * 1000,
        )

        return _pool

    except Exception:
        logger.exception("PyMySQL connection pool initialization failed")
        raise


def get_db():
    """Get a connection from the shared PyMySQL pool or fallback to direct connection."""

    start = time.perf_counter()

    try:
        pool = initialize_db_pool()
        connection = pool.get_connection()

        logger.info(
            "PERF | PyMySQL pooled connection acquired | %.2f ms",
            (time.perf_counter() - start) * 1000,
        )

        return connection

    except Exception:
        logger.warning("Pool acquisition failed, falling back to direct PyMySQL connection")
        
        # Fallback direct connection for serverless cold-starts or pool limits
        return pymysql.connect(
            host=os.environ["DB_HOST"],
            port=int(os.environ["DB_PORT"]),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"],
            ssl={"ca": str(DB_SSL_CA)},
            connect_timeout=10
        )