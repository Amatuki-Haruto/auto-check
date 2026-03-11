"""
PostgreSQL接続とテーブル初期化
Render等でDATABASE_URLが設定されている場合に使用
"""
import logging
from contextlib import contextmanager

from config import DATABASE_URL

logger = logging.getLogger(__name__)


def _get_conn():
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    return conn


@contextmanager
def get_db():
    """データベース接続のコンテキストマネージャ"""
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """テーブル作成"""
    if not DATABASE_URL:
        return
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS price_records (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    items JSONB NOT NULL
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_price_records_ts ON price_records(timestamp)")
    logger.info("Database initialized")
