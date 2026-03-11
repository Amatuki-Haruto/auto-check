"""
価格履歴の保存・読み込み
DATABASE_URL が設定されていれば PostgreSQL、なければ JSON ファイルを使用
"""
import json
import logging
from pathlib import Path
from datetime import datetime

from filelock import FileLock

from config import MAX_RECORDS, DATABASE_URL

logger = logging.getLogger(__name__)

# JSON 用
DATA_FILE = Path(__file__).parent / "price_history.json"
LOCK_FILE = Path(__file__).parent / "price_history.json.lock"

_use_db = bool(DATABASE_URL)

if _use_db:
    from db import get_db, init_db
    init_db()


def _load_json() -> list[dict]:
    with FileLock(LOCK_FILE, timeout=10):
        if not DATA_FILE.exists():
            return []
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_json(records: list[dict]):
    with FileLock(LOCK_FILE, timeout=10):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)


def load_history() -> list[dict]:
    """価格履歴を読み込む"""
    if _use_db:
        from db import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT timestamp, items FROM price_records ORDER BY timestamp ASC")
                rows = cur.fetchall()
                return [{"timestamp": r[0].isoformat(), "items": r[1]} for r in rows]
    return _load_json()


def add_price_record(prices: dict[str, dict]) -> dict:
    """
    1回分のスクレイピング結果を履歴に追加
    prices: { "こんぼう": {"min": 36, "max": 40, "unit": "マー"}, ... }
    """
    record = {
        "timestamp": datetime.now().isoformat(),
        "items": prices,
    }
    if _use_db:
        from db import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO price_records (timestamp, items) VALUES (%s, %s)",
                    (datetime.now(), json.dumps(prices, ensure_ascii=False))
                )
                cur.execute(
                    "SELECT COUNT(*) FROM price_records"
                )
                count = cur.fetchone()[0]
                if count > MAX_RECORDS:
                    cur.execute("""
                        DELETE FROM price_records WHERE id IN (
                            SELECT id FROM price_records ORDER BY timestamp ASC LIMIT %s
                        )
                    """, (count - MAX_RECORDS,))
    else:
        with FileLock(LOCK_FILE, timeout=10):
            if not DATA_FILE.exists():
                history = []
            else:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            history.append(record)
            if len(history) > MAX_RECORDS:
                history = history[-MAX_RECORDS:]
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
    return record


def get_item_history(item_name: str) -> list[dict]:
    """
    特定アイテムの価格推移を取得
    戻り値: [{"timestamp": "...", "min": 36, "max": 40, "unit": "マー"}, ...]
    """
    history = load_history()
    result = []
    for rec in history:
        if item_name in rec.get("items", {}):
            item = rec["items"][item_name]
            result.append({
                "timestamp": rec["timestamp"],
                "min": item["min"],
                "max": item["max"],
                "unit": item["unit"],
            })
    return result


def get_all_items() -> list[str]:
    """履歴に登場した全アイテム名を取得"""
    history = load_history()
    items = set()
    for rec in history:
        items.update(rec.get("items", {}).keys())
    return sorted(items)


def get_base_item_history(base_name: str, use_normalized: bool = True) -> list[dict]:
    """
    基底アイテムの価格推移（+1,+2...を正規化して統合）
    例: こんぼう, こんぼう+1, こんぼう+2 を こんぼう に統合
    正規化: 無印=1, +1=1/3, +2=1/9 (価格/3^nで無印換算)
    """
    from item_categories import get_base_item_name, get_plus_value, normalize_price

    history = load_history()
    result = []
    for rec in history:
        items_data = rec.get("items", {})
        norm_mins = []
        norm_maxs = []
        for full_name, data in items_data.items():
            base = get_base_item_name(full_name)
            if base != base_name:
                continue
            plus = get_plus_value(full_name)
            if use_normalized:
                norm_mins.append(normalize_price(data["min"], plus))
                norm_maxs.append(normalize_price(data["max"], plus))
            else:
                norm_mins.append(float(data["min"]))
                norm_maxs.append(float(data["max"]))
        if norm_mins:
            result.append({
                "timestamp": rec["timestamp"],
                "min": round(min(norm_mins), 1),
                "max": round(max(norm_maxs), 1),
                "unit": list(items_data.values())[0].get("unit", "マー"),
            })
    return result


def get_multi_history(item_names: list[str], use_normalized: bool = True) -> dict[str, list[dict]]:
    """複数アイテムの履歴を取得（比較用）。基底名で統合する場合は use_normalized=True"""
    from item_categories import get_base_item_name

    if use_normalized:
        bases = sorted(set(get_base_item_name(n) for n in item_names))
        return {base: get_base_item_history(base, use_normalized=True) for base in bases}
    else:
        result = {}
        for name in item_names:
            h = get_item_history(name)
            if h:
                result[name] = h
        return result
