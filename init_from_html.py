"""
保存したあるけみすと.htmlから初回データを投入
Render の /api/push_prices に送信する
使い方:
  export RENDER_URL=https://your-app.onrender.com
  export API_SECRET=your-secret
  python init_from_html.py /path/to/あるけみすと.html
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scraper import parse_prices
import requests


def main():
    if len(sys.argv) < 2:
        print("Usage: python init_from_html.py /path/to/あるけみすと.html")
        print("  RENDER_URL と API_SECRET を環境変数に設定してください")
        sys.exit(1)
    render_url = os.environ.get("RENDER_URL", "").rstrip("/")
    api_secret = os.environ.get("API_SECRET", "")
    if not render_url or not api_secret:
        print("Error: RENDER_URL と API_SECRET を環境変数に設定してください")
        sys.exit(1)
    html_path = Path(sys.argv[1])
    if not html_path.exists():
        print(f"File not found: {html_path}")
        sys.exit(1)
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    prices = parse_prices(html)
    if not prices:
        print("No prices found in HTML")
        sys.exit(1)
    url = f"{render_url}/api/push_prices"
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
            print(f"Sent {len(prices)} items to {render_url}")
            if "こんぼう" in prices:
                print("  こんぼう:", prices["こんぼう"])
        else:
            print("Error:", data.get("error", "不明"))
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
