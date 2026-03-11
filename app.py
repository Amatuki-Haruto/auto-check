"""
あるけみすと 市場価格変動確認 Webアプリ（Render 専用）
データは push_data.py から POST で送信される
"""
import logging

from flask import Flask, render_template, jsonify, request

from config import DATABASE_URL, API_SECRET
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
    items_param = request.args.get("items", "")
    normalized = request.args.get("normalized", "0") in ("1", "true", "yes")
    if not items_param:
        return jsonify({"items": {}, "error": "items parameter required"})
    item_names = [n.strip() for n in items_param.split(",") if n.strip()]
    if not item_names:
        return jsonify({"items": {}, "error": "no valid items"})
    data = get_multi_history(item_names, use_normalized=normalized)
    return jsonify({"items": data, "normalized": normalized})


@app.route("/api/push_prices", methods=["POST"])
def api_push_prices():
    """外部からの価格データ受信。X-API-Secret ヘッダで認証"""
    if not API_SECRET:
        return jsonify({"success": False, "error": "API_SECRET が設定されていません"}), 500
    auth = request.headers.get("X-API-Secret") or (request.json or {}).get("api_secret")
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


if __name__ == "__main__":
    from config import FLASK_DEBUG, FLASK_PORT
    logger.info("http://127.0.0.1:%s でアクセス", FLASK_PORT)
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=FLASK_DEBUG, use_reloader=False)
