from __future__ import annotations

from data_pipeline.models import NormalizedMerchant, RawMerchant


CATEGORY_RULES: tuple[tuple[str, str], ...] = (
    # Chinese keywords → Chinese category names
    ("火锅", "火锅"),
    ("川菜", "川菜"),
    ("湘菜", "湘菜"),
    ("湖南", "湘菜"),
    ("面", "面食"),
    ("粉", "面食"),
    ("米线", "面食"),
    ("粥", "粥面"),
    ("饭", "盖浇饭"),
    ("炒饭", "盖浇饭"),
    ("盖浇饭", "盖浇饭"),
    ("烧烤", "烧烤"),
    ("烤肉", "烧烤"),
    ("龙虾", "烧烤"),
    ("咖啡", "咖啡甜品"),
    ("甜品", "咖啡甜品"),
    ("蛋糕", "咖啡甜品"),
    ("奶茶", "咖啡甜品"),
    ("寿司", "日韩料理"),
    ("日料", "日韩料理"),
    ("日本", "日韩料理"),
    ("韩", "日韩料理"),
    ("披萨", "披萨意面"),
    ("比萨", "披萨意面"),
    ("意面", "披萨意面"),
    ("西餐", "西餐"),
    ("汉堡", "炸鸡汉堡"),
    ("炸鸡", "炸鸡汉堡"),
    ("轻食", "轻食"),
    ("沙拉", "轻食"),
    ("麻辣烫", "麻辣烫"),
    ("串串", "火锅串串"),
    ("鸭脖", "鸭脖卤味"),
    ("卤味", "鸭脖卤味"),
    # English keywords
    ("hotpot", "火锅"),
    ("noodle", "面食"),
    ("rice", "盖浇饭"),
    ("bbq", "烧烤"),
    ("barbecue", "烧烤"),
    ("coffee", "咖啡甜品"),
    ("dessert", "咖啡甜品"),
    ("pizza", "披萨意面"),
    ("burger", "炸鸡汉堡"),
    ("sushi", "日韩料理"),
    ("korean", "日韩料理"),
    ("sichuan", "川菜"),
    ("hunan", "湘菜"),
)


def infer_homepage_category(raw: RawMerchant) -> str:
    text = " ".join([raw.category, raw.name, *raw.tags]).lower()
    for keyword, category in CATEGORY_RULES:
        if keyword in text:
            return category
    return "中餐"


def normalize_merchant(raw: RawMerchant) -> NormalizedMerchant:
    category = infer_homepage_category(raw)
    description = f"{category}商家，位于{raw.district}"
    promo_text = f"{raw.district}{category}配送"
    merchant_tags = [t for t in raw.tags if t != category][:5]
    return NormalizedMerchant.from_raw(
        raw,
        homepage_category=category,
        description=description,
        promo_text=promo_text,
        business_hours="10:00-22:00",
        merchant_tags=merchant_tags,
    )
