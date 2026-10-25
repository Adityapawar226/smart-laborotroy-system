
import os
import time
import logging
from pathlib import Path

import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_SSL_CA = BASE_DIR / "aiven-ca.pem"

_pool = None


def initialize_db_pool():
    """
    Initialize one small MySQL connection pool per Python process.
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
        _pool = MySQLConnectionPool(
            pool_name="medilens_pool",
            pool_size=3,
            pool_reset_session=True,
            host=os.environ["DB_HOST"],
            port=int(os.environ["DB_PORT"]),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"],
            ssl_ca=str(DB_SSL_CA),
            ssl_verify_cert=True,
            ssl_verify_identity=True,
            connection_timeout=10,
        )

        logger.info(
            "PERF | MySQL connection pool initialized | %.2f ms",
            (time.perf_counter() - start) * 1000,
        )

        return _pool

    except Exception:
        logger.exception("MySQL connection pool initialization failed")
        raise


def get_db():
    """Get a connection from the shared pool."""

    start = time.perf_counter()

    try:
        pool = initialize_db_pool()
        connection = pool.get_connection()

        # A pooled connection can be returned after db.close().
        # Check whether the underlying connection is still usable.
        if not connection.is_connected():
            connection.reconnect(attempts=1, delay=0)

        logger.info(
            "PERF | MySQL pooled connection acquired | %.2f ms",
            (time.perf_counter() - start) * 1000,
        )

        return connection

    except Exception:
        logger.exception(
            "Unable to acquire a MySQL pooled connection"
        )
        raise

