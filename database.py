import os
import time
import logging
from pathlib import Path
import pymysql

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_SSL_CA = BASE_DIR / "aiven-ca.pem"

def get_db():
    """
    Establish a direct PyMySQL connection. Ideal for serverless environments
    like Vercel to prevent connection limit exhaustion and missing module errors.
    """
    start = time.perf_counter()

    required_vars = (
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
    )

    missing = [name for name in required_vars if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Missing required database environment variables: "
            + ", ".join(missing)
        )

    if not DB_SSL_CA.is_file():
        raise FileNotFoundError(
            f"Aiven CA certificate not found: {DB_SSL_CA}"
        )

    try:
        connection = pymysql.connect(
            host=os.environ["DB_HOST"],
            port=int(os.environ["DB_PORT"]),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"],
            ssl={"ca": str(DB_SSL_CA)},
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor
        )

        logger.info(
            "PERF | PyMySQL connection established | %.2f ms",
            (time.perf_counter() - start) * 1000,
        )

        return connection

    except Exception:
        logger.exception("PyMySQL connection failed")
        raise