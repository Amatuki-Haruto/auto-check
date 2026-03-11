"""
スクレイピングを実行し、取得した価格データをRenderアプリのAPIに送信する
使い方:
  export RENDER_URL=https://your-app.onrender.com
  export API_SECRET=your-secret
  python push_data.py
"""
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scraper import run_scrape
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    render_url = os.environ.get("RENDER_URL", "").rstrip("/")
    api_secret = os.environ.get("API_SECRET", "")
    if not render_url or not api_secret:
        logger.error("RENDER_URL と API_SECRET を環境変数に設定してください")
        sys.exit(1)
    url = f"{render_url}/api/push_prices"
    logger.info("スクレイピング実行中...")
    result = run_scrape()
    if not result.get("success"):
        logger.error("スクレイピング失敗: %s", result.get("error", "不明"))
        sys.exit(1)
    prices = result.get("prices", {})
    if not prices:
        logger.error("取得データがありません")
        sys.exit(1)
    logger.info("取得: %d アイテム → %s に送信中", len(prices), render_url)
    try:
        resp = requests.post(
            url,
            json={"prices": prices},
            headers={"X-API-Secret": api_secret, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("success"):
            logger.info("送信完了: %d 件", data.get("count", len(prices)))
        else:
            logger.error("送信エラー: %s", data.get("error", "不明"))
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        logger.exception("送信失敗: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
