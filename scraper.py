"""
あるけみすと市場の価格スクレイピングモジュール
https://games-alchemist.com/myshop/ の /get_shop_items/ API からアイテム価格を取得
"""
import logging
import re
import json
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from config import ITEM_TYPES, SCRAPE_TIMEOUT, SCRAPE_RETRY_ATTEMPTS

logger = logging.getLogger(__name__)

BASE_URL = "https://games-alchemist.com"
Myshop_URL = f"{BASE_URL}/myshop/"
GetShopItems_URL = f"{BASE_URL}/get_shop_items/"
COOKIE_FILE = Path(__file__).parent / "cookies.json"


def load_cookies():
    """保存されたCookieを読み込む"""
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("cookies", {})
    return {}


def save_cookies(cookies: dict):
    """Cookieを保存する"""
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump({"cookies": cookies, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)


def _extract_csrf_token(html: str) -> str | None:
    """HTMLからCSRFトークンを抽出"""
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "csrf-token"})
    if meta and meta.get("content"):
        return meta["content"]
    inp = soup.find("input", attrs={"name": "csrfmiddlewaretoken"})
    if inp and inp.get("value"):
        return inp["value"]
    return None


def _parse_prices_from_html(html: str) -> dict[str, dict]:
    """HTML断片からアイテムごとの最安値・最高値を抽出"""
    if not html or not html.strip():
        return {}
    soup = BeautifulSoup(html, "html.parser")
    results = {}

    for tr in soup.find_all("tr"):
        item_cell = tr.find("span", class_="item-name")
        price_cell = tr.find("td", class_=re.compile(r"text-right"))
        if not item_cell or not price_cell:
            continue

        raw_name = item_cell.get_text(strip=True)
        name = re.sub(r"^\[.*?\]\s*", "", raw_name).strip() or raw_name

        price_text = price_cell.get_text(strip=True)
        match = re.match(r"(\d+)\s*(マー|G)", price_text)
        if not match:
            continue
        price_val = int(match.group(1))
        unit = match.group(2)

        if name not in results:
            results[name] = {"min": price_val, "max": price_val, "unit": unit}
        else:
            results[name]["min"] = min(results[name]["min"], price_val)
            results[name]["max"] = max(results[name]["max"], price_val)

    return results


def parse_prices(html: str) -> dict[str, dict]:
    """HTMLからアイテム価格を抽出（init_from_html用・後方互換）"""
    return _parse_prices_from_html(html)


def _merge_prices(acc: dict, new: dict) -> dict:
    """複数カテゴリの結果をマージ"""
    for name, data in new.items():
        if name not in acc:
            acc[name] = data.copy()
        else:
            acc[name]["min"] = min(acc[name]["min"], data["min"])
            acc[name]["max"] = max(acc[name]["max"], data["max"])
    return acc


def _fetch_category(
    session: requests.Session,
    item_type: str,
    csrf_token: str,
    item_name: str,
) -> tuple[str, dict]:
    """1カテゴリ分の市場データを取得"""
    resp = session.post(
        GetShopItems_URL,
        data={
            "query": item_name,
            "target_item_type": item_type,
            "csrfmiddlewaretoken": csrf_token,
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": csrf_token,
        },
        timeout=SCRAPE_TIMEOUT,
    )
    resp.raise_for_status()
    return item_type, _parse_prices_from_html(resp.text)


def run_scrape(cookies: dict | None = None, item_name: str = "") -> dict:
    """
    スクレイピングを実行
    /get_shop_items/ API にPOSTして市場データを取得
    """
    last_error = None
    for attempt in range(SCRAPE_RETRY_ATTEMPTS):
        try:
            return _run_scrape_impl(cookies, item_name)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_error = e
            logger.warning("スクレイピング失敗 (試行 %d/%d): %s", attempt + 1, SCRAPE_RETRY_ATTEMPTS, e)
            if attempt == SCRAPE_RETRY_ATTEMPTS - 1:
                return {"success": False, "error": str(e), "prices": {}}
    return {"success": False, "error": str(last_error), "prices": {}}


def _run_scrape_impl(cookies: dict | None = None, item_name: str = "") -> dict:
    """スクレイピング本体（リトライ用）"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,ja;q=0.8",
        "Referer": f"{Myshop_URL}",
        "Origin": BASE_URL,
    })

    if cookies:
        for k, v in cookies.items():
            session.cookies.set(k, str(v), domain=".games-alchemist.com")
    else:
        saved = load_cookies()
        for k, v in saved.items():
            session.cookies.set(k, str(v), domain=".games-alchemist.com")

    # 1. myshop ページを取得してCSRFトークンを抽出
    try:
        resp = session.get(Myshop_URL, timeout=SCRAPE_TIMEOUT)
        resp.raise_for_status()
        html = resp.text
    except requests.exceptions.HTTPError as e:
        return {"success": False, "error": f"HTTPエラー: {e.response.status_code}", "prices": {}}

    if "ユーザーID" in html and "パスワード" in html and "ログイン" in html:
        return {"success": False, "error": "ログインが必要です。Cookieを設定してください。", "prices": {}}

    csrf_token = _extract_csrf_token(html)
    if not csrf_token:
        csrf_token = session.cookies.get("csrftoken") or load_cookies().get("csrftoken")
    if not csrf_token:
        return {"success": False, "error": "CSRFトークンが取得できませんでした。", "prices": {}}

    # 2. 各カテゴリを並列で取得
    all_prices: dict[str, dict] = {}
    failed_categories: list[str] = []

    def _fetch(item_type: str):
        try:
            return _fetch_category(session, item_type, csrf_token, item_name)
        except Exception as e:
            logger.warning("カテゴリ %s の取得に失敗: %s", item_type, e)
            return item_type, {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch, it): it for it in ITEM_TYPES}
        for future in as_completed(futures):
            item_type, prices = future.result()
            if prices:
                _merge_prices(all_prices, prices)
            else:
                failed_categories.append(item_type)

    if failed_categories:
        logger.warning("失敗したカテゴリ: %s", ", ".join(failed_categories))

    save_cookies(session.cookies.get_dict())

    if not all_prices:
        return {
            "success": False,
            "error": "市場データが取得できませんでした。ログイン期限切れの可能性があります。Cookieを再設定してください。",
            "prices": {},
        }
    return {"success": True, "prices": all_prices, "scraped_at": datetime.now().isoformat()}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_scrape()
    print(json.dumps(result, ensure_ascii=False, indent=2))
