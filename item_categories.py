"""
アイテムのカテゴリ分類
https://wikiwiki.jp/alchemist-p/装備 を参考
"""
import re

# カテゴリ名（表示用）
CATEGORY_NAMES = {
    "weapon": "武器",
    "hats": "頭具",
    "armor": "防具",
    "boots": "足具",
    "accessory": "アクセサリー",
    "item": "アイテム",
    "other": "その他",
}

# 基底アイテム名 → カテゴリ
# +1, +2 などは含めず基底のみ
BASE_ITEM_CATEGORY: dict[str, str] = {
    "こんぼう": "weapon",
    "アイアンブレード": "weapon",
    "ウッドハンマー": "weapon",
    "アイアンバックラー": "weapon",
    "ブロンズスピア": "weapon",
    "シルバーダガー": "weapon",
    "アイアンモーニングスター": "weapon",
    "紅蓮の盾": "weapon",
    "スチールソード": "weapon",
    "オークウォーハンマー": "weapon",
    "ブロンズピケ": "weapon",
    "竜皮の盾": "weapon",
    "ミスリルブレード": "weapon",
    "エレガントラピア": "weapon",
    "ステンレスクロウ": "weapon",
    "サンライトシールド": "weapon",
    "虚空を断つ刀": "weapon",
    "シルバーナイトソード": "weapon",
    "ドラゴンバトルハンマー": "weapon",
    "ミスリルステッキ": "weapon",
    "聖騎士の刃楯": "weapon",
    "天啓目録": "weapon",
    "オニキスブレード": "weapon",
    "デーモンズグレイブ": "weapon",
    "聖者の杖": "weapon",
    "アヴァロンの盾": "weapon",
    "クリムゾンバレット": "weapon",
    "絶対零弩": "weapon",
    "夢幻水晶": "weapon",
    "ヴァルキリーシールド": "weapon",
    "引鉄斧": "weapon",
    "聖槍ロンギヌス": "weapon",
    "ベレー帽": "hats",
    "赤いリボン": "hats",
    "てっかめん": "hats",
    "シルバーイヤリング": "hats",
    "ドラゴンヘルム": "hats",
    "ホワイトブリム": "hats",
    "カウボーイハット": "hats",
    "天使の光輪": "hats",
    "戦士のバンダナ": "hats",
    "モコモコマフラー": "hats",
    "アルケ・ゴーグル": "hats",
    "フレイムクラウン": "hats",
    "ルナ・ティアラ": "hats",
    "タイタンヘッド": "hats",
    "くさりかたびら": "armor",
    "布のローブ": "armor",
    "鋼鉄の鎧": "armor",
    "魔法使いのローブ": "armor",
    "ドラゴンスキンアーマー": "armor",
    "エルフのシルクローブ": "armor",
    "守護者の鎧": "armor",
    "賢者のローブ": "armor",
    "デーモンプレートアーマー": "armor",
    "幻影のローブ": "armor",
    "光の鎧": "armor",
    "大魔導師のローブ": "armor",
    "厄災のヴェール": "armor",
    "煉獄の炎鎧": "armor",
    "レザーブーツ": "boots",
    "布製のブーツ": "boots",
    "鉄のブーツ": "boots",
    "エナメルブーツ": "boots",
    "鋼鉄のブーツ": "boots",
    "クロコダイルブーツ": "boots",
    "神秘のブーツ": "boots",
    "砂漠のブーツ": "boots",
    "フォレストブーツ": "boots",
    "竜鱗のブーツ": "boots",
    "星空ブーツ": "boots",
    "シャドウブーツ": "boots",
    "雷鳴のグリーブス": "boots",
    "クロノギア・ブーツ": "boots",
    "銅の指輪": "accessory",
    "布製のベルト": "accessory",
    "銀のペンダント": "accessory",
    "鋼鉄の腕輪": "accessory",
    "ルビーの指輪": "accessory",
    "魔法のネックレス": "accessory",
    "竜の牙": "accessory",
    "宝石のブローチ": "accessory",
    "伝説のメダリオン": "accessory",
    "星屑のリング": "accessory",
    "神秘のペンダント": "accessory",
    "太陽のアミュレット": "accessory",
    "竜王のブレスレット": "accessory",
    "ミスティック・オーブ": "accessory",
}


def get_base_item_name(full_name: str) -> str:
    """アイテム名から基底名を取得（こんぼう+2 → こんぼう）"""
    m = re.match(r"^(.+?)\s*\+\s*\d+$", full_name.strip())
    return m.group(1).strip() if m else full_name


def get_plus_value(full_name: str) -> int:
    """強化値を取得（こんぼう+2 → 2）。无印は0"""
    m = re.search(r"\+\s*(\d+)\s*$", full_name.strip())
    return int(m.group(1)) if m else 0


def get_category(item_name: str) -> str:
    """アイテムのカテゴリを返す"""
    base = get_base_item_name(item_name)
    return BASE_ITEM_CATEGORY.get(base, "other")


def normalize_price(price: int, plus_value: int) -> float:
    """
    価格を無印換算に正規化
    +1 = 3倍, +2 = 9倍, +3 = 27倍...
    無印換算 = price / (3 ** plus_value)
    """
    if plus_value <= 0:
        return float(price)
    return price / (3**plus_value)


def categorize_items(items: list[str]) -> dict[str, list[str]]:
    """アイテムリストをカテゴリ別にグループ化"""
    result: dict[str, list[str]] = {}
    for name in sorted(items):
        cat = get_category(name)
        if cat not in result:
            result[cat] = []
        result[cat].append(name)
    return result
