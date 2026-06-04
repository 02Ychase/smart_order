from __future__ import annotations

from data_pipeline.models import NormalizedDish, RawDish


PRICE_BANDS = {
    "川菜": 38.0,
    "湘菜": 38.0,
    "火锅": 58.0,
    "火锅串串": 48.0,
    "咖啡甜品": 24.0,
    "炸鸡汉堡": 32.0,
    "西餐": 46.0,
    "披萨意面": 40.0,
    "烧烤": 48.0,
    "日韩料理": 42.0,
    "面食": 26.0,
    "粥面": 22.0,
    "盖浇饭": 28.0,
    "轻食": 30.0,
    "麻辣烫": 28.0,
    "鸭脖卤味": 25.0,
    "中餐": 36.0,
}


ALLERGEN_RULES = {
    "鸡蛋": "蛋类",
    "蛋": "蛋类",
    "蛋清": "蛋类",
    "牛奶": "乳制品",
    "奶": "乳制品",
    "芝士": "乳制品",
    "奶酪": "乳制品",
    "奶油": "乳制品",
    "黄油": "乳制品",
    "淡奶油": "乳制品",
    "面粉": "麸质",
    "小麦": "麸质",
    "面条": "麸质",
    "高筋面粉": "麸质",
    "低筋面粉": "麸质",
    "花生": "花生",
    "虾": "甲壳类",
    "蟹": "甲壳类",
    "虾仁": "甲壳类",
    "大豆": "大豆",
    "酱油": "大豆",
    "豆腐": "大豆",
    "豆瓣酱": "大豆",
    "蚝油": "甲壳类",
    # English
    "egg": "蛋类",
    "milk": "乳制品",
    "cheese": "乳制品",
    "cream": "乳制品",
    "butter": "乳制品",
    "wheat": "麸质",
    "noodle": "麸质",
    "flour": "麸质",
    "peanut": "花生",
    "shrimp": "甲壳类",
    "crab": "甲壳类",
    "soy": "大豆",
    "tofu": "大豆",
}


CUISINE_KEYWORDS = {
    "川菜": "川菜",
    "四川": "川菜",
    "湘菜": "湘菜",
    "湖南": "湘菜",
    "火锅": "火锅",
    "串串": "火锅串串",
    "面": "面食",
    "粉": "面食",
    "米线": "面食",
    "粥": "粥面",
    "饭": "盖浇饭",
    "炒饭": "盖浇饭",
    "盖浇饭": "盖浇饭",
    "烧烤": "烧烤",
    "烤肉": "烧烤",
    "龙虾": "烧烤",
    "寿司": "日韩料理",
    "日料": "日韩料理",
    "日本": "日韩料理",
    "韩": "日韩料理",
    "披萨": "披萨意面",
    "比萨": "披萨意面",
    "意面": "披萨意面",
    "西餐": "西餐",
    "汉堡": "炸鸡汉堡",
    "炸鸡": "炸鸡汉堡",
    "轻食": "轻食",
    "沙拉": "轻食",
    "麻辣烫": "麻辣烫",
    "鸭脖": "鸭脖卤味",
    "卤味": "鸭脖卤味",
    "咖啡": "咖啡甜品",
    "甜品": "咖啡甜品",
    "蛋糕": "咖啡甜品",
    "奶茶": "咖啡甜品",
    # English
    "sichuan": "川菜",
    "hunan": "湘菜",
    "hotpot": "火锅",
    "noodle": "面食",
    "rice": "盖浇饭",
    "bbq": "烧烤",
    "coffee": "咖啡甜品",
    "dessert": "咖啡甜品",
    "pizza": "披萨意面",
    "burger": "炸鸡汉堡",
    "sushi": "日韩料理",
    "korean": "日韩料理",
}


def infer_cuisine_from_tags(raw: RawDish) -> str:
    text = " ".join([raw.cuisine_type, *raw.tags, raw.name, raw.description])
    for keyword, cuisine in CUISINE_KEYWORDS.items():
        if keyword in text:
            return cuisine
    return ""


def infer_flavor(raw: RawDish) -> str:
    text = " ".join([raw.name, raw.description, *raw.ingredients, *raw.tags])
    rules = (
        ("辣", ("辣", "椒", "麻", "花椒", "辣椒", "胡椒", "chili", "pepper", "spicy")),
        ("甜", ("甜", "蜜", "糖", "蜜汁", "sweet", "sugar", "honey", "dessert")),
        ("咸鲜", ("酱油", "红烧", "卤", "炖", "酱", "soy", "salt", "beef", "chicken", "pork")),
        ("清淡", ("沙拉", "柠檬", "凉拌", "清蒸", "白灼", "salad", "lemon", "tomato", "cucumber")),
        ("奶香", ("奶", "奶油", "芝士", "milk", "cream", "cheese")),
    )
    for flavor, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return flavor
    return "家常"


def infer_cooking_method(raw: RawDish) -> str:
    text = " ".join([raw.name, raw.description])
    rules = (
        ("炒", ("炒", "煎", "炸", "干锅", "爆", "fried", "stir fry", "saute")),
        ("煮", ("煮", "炖", "汤", "面", "烫", "涮", "水煮", "noodle", "soup", "boil")),
        ("烤", ("烤", "烘焙", "bake", "pizza", "cake", "bread")),
        ("烧", ("烧", "烤串", "炭烤", "grill", "bbq", "barbecue", "roast")),
        ("凉拌", ("凉拌", "拌", "沙拉", "salad", "mix")),
        ("蒸", ("蒸", "清蒸", "steam")),
    )
    for method, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return method
    return "烹饪"


def infer_allergens(raw: RawDish) -> list[str]:
    text = " ".join(raw.ingredients)
    allergens = [allergen for keyword, allergen in ALLERGEN_RULES.items() if keyword in text]
    return list(dict.fromkeys(allergens))


def infer_price(cuisine_type: str, ingredient_count: int) -> float:
    base = PRICE_BANDS.get(cuisine_type, PRICE_BANDS["中餐"])
    return base + min(max(ingredient_count - 3, 0), 8) * 1.5


def normalize_dish(raw: RawDish, *, fallback_cuisine: str = "中餐", merchant_category: str = "") -> NormalizedDish:
    cuisine_type = raw.cuisine_type or infer_cuisine_from_tags(raw) or merchant_category or fallback_cuisine
    flavor = infer_flavor(raw)
    price = raw.price if raw.price is not None else infer_price(cuisine_type, len(raw.ingredients))
    return NormalizedDish.from_raw(
        raw,
        cuisine_type=cuisine_type,
        flavor_profile=flavor,
        cooking_method=infer_cooking_method(raw),
        allergens=infer_allergens(raw),
        price=price,
        is_recommended=len(raw.ingredients) >= 3 and bool(raw.description),
    )
