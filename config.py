"""
設定の一元管理
環境変数または .env から読み込み
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# Flask
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(os.environ.get("PORT") or os.environ.get("FLASK_PORT", "5001"))

# スクレイピング
ITEM_TYPES = ["Weapon", "Armor", "Boots", "Hats", "Accessories", "Item", "Recent"]
SCRAPE_TIMEOUT = int(os.environ.get("SCRAPE_TIMEOUT", "30"))
SCRAPE_RETRY_ATTEMPTS = int(os.environ.get("SCRAPE_RETRY_ATTEMPTS", "3"))

# データストア
MAX_RECORDS = int(os.environ.get("MAX_RECORDS", "700"))
_raw_db = os.environ.get("DATABASE_URL")
# Render等は postgres:// を返すが psycopg2 は postgresql:// が必要
if _raw_db and _raw_db.startswith("postgres://"):
    _raw_db = "postgresql" + _raw_db[8:]
DATABASE_URL = _raw_db  # 未設定ならJSON使用

# Cookie 警告（時間で判定）
COOKIE_WARN_HOURS = int(os.environ.get("COOKIE_WARN_HOURS", "24"))

# API レート制限
SCRAPE_RATE_LIMIT = os.environ.get("SCRAPE_RATE_LIMIT", "3 per minute")

# 外部からの価格データ受信API認証（Render用）
API_SECRET = os.environ.get("API_SECRET", "")
