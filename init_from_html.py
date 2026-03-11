"""
保存したあるけみすと.htmlから初回データを投入するスクリプト
使い方: python init_from_html.py /path/to/あるけみすと.html
"""
import sys
import json
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from scraper import parse_prices
from data_store import add_price_record


def main():
    if len(sys.argv) < 2:
        print("Usage: python init_from_html.py /path/to/あるけみすと.html")
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
    add_price_record(prices)
    print(f"Added {len(prices)} items from {html_path}")
    if "こんぼう" in prices:
        print("  こんぼう:", prices["こんぼう"])


if __name__ == "__main__":
    main()
