"""
あるけみすと 市場価格変動確認 Webアプリ
ローカル: 毎時15分・45分にスクレイピング実行
Render: 外部からPOSTでデータ受け取り・表示のみ
"""
import logging
from datetime import datetime

from flask import Flask, render_template, jsonify, request

from config import (
    FLASK_DEBUG,
    FLASK_PORT,
    SCRAPE_RATE_LIMIT,
    COOKIE_WARN_HOURS,
    DATABASE_URL,
    API_SECRET,
)
from data_store import (
    add_price_record,
    get_item_history,
    get_all_items,
    load_history,
    get_base_item_history,
    get_multi_history,
)
from item_categories import categorize_items, CATEGORY_NAMES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# レート制限（DATABASE_URL未設定時はflask-limiter使用、設定時は簡易制限）
if not DATABASE_URL:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
    )
else:
    limiter = None


def _start_scheduler():
    """ローカル（JSON使用）時のみスケジューラを起動"""
    if DATABASE_URL:
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    from scraper import run_scrape

    def scheduled_scrape():
        try:
            result = run_scrape()
            if result.get("success") and result.get("prices"):
                add_price_record(result["prices"])
                logger.info("Scraped %d items", len(result["prices"]))
            else:
                logger.warning("Scrape failed: %s", result.get("error", "不明なエラー"))
        except Exception as e:
            logger.exception("Scrape failed: %s", e)

    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_scrape, "cron", minute="15,45", id="scrape_job")
    scheduler.start()


_start_scheduler()


def _cookie_warn() -> bool:
    """Cookieが古い場合True（COOKIE_WARN_HOURSを超えていたら警告）。Renderでは常にFalse"""
    if DATABASE_URL:
        return False
    import json
    from pathlib import Path
    cookie_file = Path(__file__).parent / "cookies.json"
    if not cookie_file.exists():
        return False
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        updated = data.get("updated_at")
        if not updated:
            return False
        updated_dt = datetime.fromisoformat(updated[:19])
        age = datetime.now() - updated_dt
        return age.total_seconds() > COOKIE_WARN_HOURS * 3600
    except Exception:
        return False


def _rate_limit_or_pass(f):
    """limiterが無い場合はそのまま実行"""
    if limiter:
        return limiter.limit(SCRAPE_RATE_LIMIT)(f)
    return f


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/items")
def api_items():
    items = get_all_items()
    categories = categorize_items(items)
    return jsonify({
        "items": items,
        "categories": {k: v for k, v in categories.items() if v},
        "category_names": CATEGORY_NAMES,
    })


@app.route("/api/history/<path:item_name>")
def api_history(item_name):
    history = get_item_history(item_name)
    return jsonify({"item": item_name, "history": history})


@app.route("/api/base_history/<path:base_name>")
def api_base_history(base_name):
    """基底アイテムの履歴（+1,+2を正規化して統合）"""
    history = get_base_item_history(base_name, use_normalized=True)
    return jsonify({"item": base_name, "history": history, "normalized": True})


@app.route("/api/compare")
def api_compare():
    """複数アイテムの比較用履歴。items=こんぼう,こんぼう+1,ウッドハンマー & normalized=0|1"""
    from flask import request
    items_param = request.args.get("items", "")
    normalized = request.args.get("normalized", "0") in ("1", "true", "yes")
    if not items_param:
        return jsonify({"items": {}, "error": "items parameter required"})
    item_names = [n.strip() for n in items_param.split(",") if n.strip()]
    if not item_names:
        return jsonify({"items": {}, "error": "no valid items"})
    data = get_multi_history(item_names, use_normalized=normalized)
    return jsonify({"items": data, "normalized": normalized})


@app.route("/api/scrape", methods=["POST"])
@_rate_limit_or_pass
def api_scrape():
    """ローカル専用: 手動スクレイピング。Renderでは無効"""
    if DATABASE_URL:
        return jsonify({"success": False, "error": "この環境ではスクレイピングは実行できません"}), 400
    from scraper import run_scrape
    result = run_scrape()
    if result.get("success") and result.get("prices"):
        add_price_record(result["prices"])
    return jsonify(result)


@app.route("/api/push_prices", methods=["POST"])
def api_push_prices():
    """外部からの価格データ受信（Render用）。X-API-Secret ヘッダで認証"""
    if not API_SECRET:
        return jsonify({"success": False, "error": "API_SECRET が設定されていません"}), 500
    auth = request.headers.get("X-API-Secret") or request.json and request.json.get("api_secret")
    if auth != API_SECRET:
        return jsonify({"success": False, "error": "認証エラー"}), 401
    data = request.get_json()
    if not data or "prices" not in data:
        return jsonify({"success": False, "error": "prices が必要です"}), 400
    prices = data["prices"]
    if not isinstance(prices, dict):
        return jsonify({"success": False, "error": "prices はオブジェクトである必要があります"}), 400
    try:
        add_price_record(prices)
        return jsonify({"success": True, "count": len(prices)})
    except Exception as e:
        logger.exception("push_prices error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/status")
def api_status():
    history = load_history()
    last = history[-1] if history else None
    return jsonify({
        "last_scrape": last["timestamp"] if last else None,
        "record_count": len(history),
    })


@app.route("/api/cookie_status")
def api_cookie_status():
    return jsonify({"warn": _cookie_warn()})


if __name__ == "__main__":
    logger.info("毎時15分・45分にスクレイピングを実行します")
    logger.info("http://127.0.0.1:%s でアクセス", FLASK_PORT)
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False)
