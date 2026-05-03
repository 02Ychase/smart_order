from database.seeds.extended_merchant_data import (
    EXTENDED_CATEGORY_BUSINESS_HOURS,
    EXTENDED_CATEGORY_TAGS,
    EXTENDED_CATEGORIES,
)


def _stable_number(value: str) -> int:
    return sum(ord(char) for char in value)


def _unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def _build_phone(name: str) -> str:
    return f"021-{62000000 + _stable_number(name) % 3000000:08d}"


def _build_business_hours(name: str, homepage_category: str) -> str:
    options = EXTENDED_CATEGORY_BUSINESS_HOURS[homepage_category]
    return options[_stable_number(name) % len(options)]


def _build_detailed_address(name: str, district: str) -> str:
    district_points = {
        "静安": {"address": "南京西路 818 号"},
        "徐汇": {"address": "漕溪北路 399 号"},
        "浦东": {"address": "张杨路 1088 号"},
        "杨浦": {"address": "黄兴路 1888 号"},
        "长宁": {"address": "长宁路 1018 号"},
    }
    base_address = district_points[district]["address"].replace(" ", "")
    code = _stable_number(name)
    building_suffixes = ["中心广场", "邻里汇", "时光里", "星坊", "悦荟", "国际商厦"]
    building = building_suffixes[code % len(building_suffixes)]
    floor = code % 3 + 1
    room = 100 + code % 120
    return f"{base_address}{building}{floor}层{room}室"


def _build_address_note(name: str, district: str) -> str:
    landmarks = {
        "静安": "地铁站商务楼下",
        "徐汇": "写字楼连廊口",
        "浦东": "商场沿街外摆位",
        "杨浦": "大学路街角",
        "长宁": "社区商业入口",
    }
    entry = _stable_number(name) % 4 + 1
    return f"近{landmarks[district]}{entry}号取餐点"


def _build_merchant_tags(homepage_category: str, description: str, promo_text: str, avg_delivery_minutes: int) -> list[str]:
    tags = list(EXTENDED_CATEGORY_TAGS[homepage_category])
    if "下午茶" in description:
        tags.append("下午茶")
    if "夜宵" in description or avg_delivery_minutes >= 35:
        tags.append("夜宵友好")
    if "工作日" in description or avg_delivery_minutes <= 28:
        tags.append("午餐快送")
    if "双人" in promo_text or "套餐" in promo_text:
        tags.append("套餐点单")
    return _unique(tags)[:3]


def build_extended_merchant_seed(
    *,
    name: str,
    description: str,
    district: str,
    homepage_category: str,
    promo_text: str,
    delivery_radius_meters: int,
    delivery_fee: float,
    min_order_amount: float,
    avg_delivery_minutes: int,
    rating: float,
    categories: list[dict],
) -> dict:
    return {
        "name": name,
        "description": description,
        "city": "上海",
        "district": district,
        "address": _build_detailed_address(name, district),
        "longitude": 121.4521 + (_stable_number(name) % 100) * 0.0001,
        "latitude": 31.2291 + (_stable_number(name) % 80) * 0.0001,
        "homepage_category": homepage_category,
        "promo_text": promo_text,
        "delivery_radius_meters": delivery_radius_meters,
        "delivery_fee": delivery_fee,
        "min_order_amount": min_order_amount,
        "avg_delivery_minutes": avg_delivery_minutes,
        "rating": rating,
        "phone": _build_phone(name),
        "business_hours": _build_business_hours(name, homepage_category),
        "detailed_address": _build_detailed_address(name, district),
        "address_note": _build_address_note(name, district),
        "merchant_tags": _build_merchant_tags(homepage_category, description, promo_text, avg_delivery_minutes),
        "categories": categories,
    }


EXTENDED_MERCHANT_SEED_DATA = [
    build_extended_merchant_seed(
        name="虾搞烧烤",
        description="夜宵烧烤小龙虾，聚会必点",
        district="静安",
        homepage_category="龙虾烧烤",
        promo_text="龙虾啤酒套餐立减20元",
        delivery_radius_meters=3500,
        delivery_fee=6.0,
        min_order_amount=58.0,
        avg_delivery_minutes=38,
        rating=4.6,
        categories=EXTENDED_CATEGORIES["龙虾烧烤"][0],
    ),
    build_extended_merchant_seed(
        name="炭火江湖",
        description="炭火烧烤为主，龙虾季节限定",
        district="徐汇",
        homepage_category="龙虾烧烤",
        promo_text="烧烤拼盘第二份半价",
        delivery_radius_meters=3200,
        delivery_fee=6.0,
        min_order_amount=55.0,
        avg_delivery_minutes=36,
        rating=4.5,
        categories=EXTENDED_CATEGORIES["龙虾烧烤"][1],
    ),
    build_extended_merchant_seed(
        name="串串龙",
        description="地道成都串串香，锅底多样",
        district="浦东",
        homepage_category="火锅串串",
        promo_text="串串满100送锅底",
        delivery_radius_meters=3000,
        delivery_fee=5.0,
        min_order_amount=45.0,
        avg_delivery_minutes=32,
        rating=4.7,
        categories=EXTENDED_CATEGORIES["火锅串串"][0],
    ),
    build_extended_merchant_seed(
        name="冒椒火辣",
        description="冒菜串串双拼，麻辣鲜香",
        district="杨浦",
        homepage_category="火锅串串",
        promo_text="冒菜系列满30减8",
        delivery_radius_meters=2800,
        delivery_fee=5.0,
        min_order_amount=40.0,
        avg_delivery_minutes=30,
        rating=4.6,
        categories=EXTENDED_CATEGORIES["火锅串串"][1],
    ),
    build_extended_merchant_seed(
        name="绝味鸭脖",
        description="招牌鸭脖卤味，追剧必备",
        district="长宁",
        homepage_category="鸭脖卤味",
        promo_text="鸭脖鸭翅套餐立减10元",
        delivery_radius_meters=2500,
        delivery_fee=3.0,
        min_order_amount=25.0,
        avg_delivery_minutes=25,
        rating=4.8,
        categories=EXTENDED_CATEGORIES["鸭脖卤味"][0],
    ),
    build_extended_merchant_seed(
        name="周黑鸭",
        description="甜辣卤味，休闲零食首选",
        district="静安",
        homepage_category="鸭脖卤味",
        promo_text="满50元送鸭翅一份",
        delivery_radius_meters=2600,
        delivery_fee=3.0,
        min_order_amount=28.0,
        avg_delivery_minutes=26,
        rating=4.7,
        categories=EXTENDED_CATEGORIES["鸭脖卤味"][1],
    ),
    build_extended_merchant_seed(
        name="西堤牛排",
        description="精品牛排西餐，约会首选",
        district="徐汇",
        homepage_category="西餐",
        promo_text="双人牛排套餐立减50元",
        delivery_radius_meters=3000,
        delivery_fee=8.0,
        min_order_amount=88.0,
        avg_delivery_minutes=40,
        rating=4.8,
        categories=EXTENDED_CATEGORIES["西餐"][0],
    ),
    build_extended_merchant_seed(
        name="萨莉亚意式",
        description="平价意式西餐，披萨意面为主",
        district="浦东",
        homepage_category="西餐",
        promo_text="意面披萨双拼减15元",
        delivery_radius_meters=2800,
        delivery_fee=6.0,
        min_order_amount=55.0,
        avg_delivery_minutes=35,
        rating=4.5,
        categories=EXTENDED_CATEGORIES["西餐"][1],
    ),
    build_extended_merchant_seed(
        name="巴国布衣",
        description="正宗川菜馆，麻辣鲜香",
        district="杨浦",
        homepage_category="川菜",
        promo_text="川菜满100减20",
        delivery_radius_meters=3200,
        delivery_fee=5.0,
        min_order_amount=45.0,
        avg_delivery_minutes=33,
        rating=4.7,
        categories=EXTENDED_CATEGORIES["川菜"][0],
    ),
    build_extended_merchant_seed(
        name="蜀大侠",
        description="川味火锅串串，重口最爱",
        district="长宁",
        homepage_category="川菜",
        promo_text="火锅套餐立减30元",
        delivery_radius_meters=3100,
        delivery_fee=5.0,
        min_order_amount=50.0,
        avg_delivery_minutes=34,
        rating=4.6,
        categories=EXTENDED_CATEGORIES["川菜"][1],
    ),
]
