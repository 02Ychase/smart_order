# -*- coding: utf-8 -*-
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
    default_hours = ["10:00-21:30", "11:00-22:00", "10:00-21:00"]
    options = EXTENDED_CATEGORY_BUSINESS_HOURS.get(homepage_category, default_hours)
    return options[_stable_number(name) % len(options)]


def _build_detailed_address(name: str, district: str) -> str:
    district_points = {
        "静安": {"address": "南京西路 818 号"},
        "徐汇": {"address": "漕溪北路 399 号"},
        "浦东": {"address": "张杨路 1088 号"},
        "杨浦": {"address": "黄兴路 1888 号"},
        "长宁": {"address": "长宁路 1018 号"},
        "黄浦": {"address": "南京东路 100 号"},
        "虹口": {"address": "四川北路 2000 号"},
        "普陀": {"address": "中山北路 3000 号"},
        "闵行": {"address": "沪闵路 4000 号"},
        "宝山": {"address": "牡丹江路 500 号"},
    }
    base_address = district_points[district]["address"].replace(" ", "")
    code = _stable_number(name)
    building_suffixes = ["中心广场", "邻里汇", "时光里", "星坊", "悦荟", "国际商厦", "商业中心", "美食城", "购物广场", "生活广场"]
    building = building_suffixes[code % len(building_suffixes)]
    floor = code % 5 + 1
    room = 100 + code % 200
    return f"{base_address}{building}{floor}层{room}室"


def _build_address_note(name: str, district: str) -> str:
    landmarks = {
        "静安": "地铁站商务楼下",
        "徐汇": "写字楼连廊口",
        "浦东": "商场沿街外摆位",
        "杨浦": "大学路街角",
        "长宁": "社区商业入口",
        "黄浦": "步行街入口处",
        "虹口": "公园东门对面",
        "普陀": "地铁站出口旁",
        "闵行": "小区门口",
        "宝山": "公交站附近",
    }
    entry = _stable_number(name) % 6 + 1
    return f"近{landmarks[district]}{entry}号取餐点"


def _build_merchant_tags(homepage_category: str, description: str, promo_text: str, avg_delivery_minutes: int) -> list[str]:
    default_tags = ["美食", "热销", "推荐"]
    tags = list(EXTENDED_CATEGORY_TAGS.get(homepage_category, default_tags))
    if "下午茶" in description:
        tags.append("下午茶")
    if "夜宵" in description or avg_delivery_minutes >= 35:
        tags.append("夜宵友好")
    if "工作日" in description or avg_delivery_minutes <= 28:
        tags.append("午餐快送")
    if "双人" in promo_text or "套餐" in promo_text:
        tags.append("套餐点单")
    return _unique(tags)[:3]


def build_merchant_v2(
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


def section(name: str, dishes: list[dict]) -> dict:
    return {"name": name, "dishes": dishes}


def dish(name: str, description: str, price: float, tags: str, *args) -> dict:
    cuisine_type = ""
    flavor_profile = ""
    ingredients: list[str] | None = None
    allergens: list[str] | None = None
    cooking_method = ""
    is_recommended = False

    if args:
        if isinstance(args[0], bool):
            is_recommended = args[0]

    return {
        "name": name,
        "description": description,
        "price": price,
        "tags": tags,
        "cuisine_type": cuisine_type,
        "flavor_profile": flavor_profile,
        "ingredients": ingredients or [],
        "allergens": allergens or [],
        "cooking_method": cooking_method,
        "is_recommended": is_recommended,
    }


LONGXIA_SHAOKAO_CATEGORIES = [
    section("招牌龙虾", [
        dish("蒜蓉小龙虾", "蒜香浓郁，虾肉弹牙", 88.0, "龙虾,蒜蓉,招牌", True),
        dish("十三香小龙虾", "十三香卤制，入味十足", 98.0, "龙虾,十三香,热销", True),
        dish("麻辣小龙虾", "麻辣鲜香，重口最爱", 88.0, "龙虾,麻辣,重口"),
        dish("冰镇小龙虾", "冰镇爽口，原汁原味", 108.0, "龙虾,冰镇,清爽"),
        dish("椒盐小龙虾", "椒盐酥脆，回味无穷", 98.0, "龙虾,椒盐,酥脆"),
    ]),
    section("特色烧烤", [
        dish("羊肉串", "孜然羊肉，外焦里嫩", 3.0, "烧烤,羊肉,孜然", True),
        dish("烤鸡翅", "蜜汁鸡翅，皮脆肉嫩", 4.0, "烧烤,鸡翅,蜜汁"),
        dish("烤五花肉", "五花肉烤制，肥而不腻", 5.0, "烧烤,五花肉,焦香"),
        dish("烤鱿鱼", "鱿鱼烤制，鲜香弹牙", 5.0, "烧烤,鱿鱼,海鲜"),
        dish("烤茄子", "茄子烤制，蒜蓉酱香", 4.0, "烧烤,茄子,蒜蓉"),
    ]),
]

HUOGUO_CHUANCHUAN_CATEGORIES = [
    section("锅底系列", [
        dish("麻辣锅底", "正宗川味麻辣锅底", 38.0, "火锅,麻辣,锅底", True),
        dish("清汤锅底", "清汤锅底，清淡爽口", 28.0, "火锅,清汤,锅底"),
        dish("番茄锅底", "番茄锅底，酸甜开胃", 32.0, "火锅,番茄,锅底"),
        dish("菌汤锅底", "菌汤锅底，鲜香浓郁", 35.0, "火锅,菌汤,锅底"),
        dish("鸳鸯锅底", "一半清汤一半麻辣", 42.0, "火锅,鸳鸯,双拼"),
    ]),
    section("经典串串", [
        dish("牛肉串", "牛肉串涮制，嫩滑多汁", 2.0, "串串,牛肉,涮锅", True),
        dish("毛肚", "毛肚涮制，脆嫩爽口", 3.0, "串串,毛肚,脆嫩", True),
        dish("鸭肠", "鸭肠涮制，爽脆弹牙", 2.5, "串串,鸭肠,爽脆"),
        dish("黄喉", "黄喉涮制，口感独特", 3.0, "串串,黄喉,口感"),
        dish("午餐肉", "午餐肉涮制，经典美味", 1.5, "串串,午餐肉,经典"),
    ]),
]

YABO_LUWEI_CATEGORIES = [
    section("招牌鸭货", [
        dish("鸭脖", "鸭脖卤制，麻辣入味", 15.0, "卤味,鸭脖,麻辣", True),
        dish("鸭翅", "鸭翅卤制，酱香浓郁", 12.0, "卤味,鸭翅,酱香", True),
        dish("鸭锁骨", "鸭锁骨卤制，肉质紧实", 10.0, "卤味,鸭锁骨,紧实"),
        dish("鸭舌", "鸭舌卤制，口感独特", 18.0, "卤味,鸭舌,口感"),
        dish("鸭头", "鸭头卤制，入味十足", 8.0, "卤味,鸭头,入味"),
    ]),
    section("素菜卤味", [
        dish("卤藕片", "藕片卤制，爽脆可口", 6.0, "卤味,藕片,爽脆"),
        dish("卤海带", "海带卤制，软糯入味", 5.0, "卤味,海带,软糯"),
        dish("卤豆干", "豆干卤制，酱香浓郁", 5.0, "卤味,豆干,酱香"),
        dish("卤腐竹", "腐竹卤制，吸汁十足", 6.0, "卤味,腐竹,吸汁"),
        dish("卤花生", "花生卤制，香脆可口", 4.0, "卤味,花生,香脆"),
    ]),
]

XICAN_CATEGORIES = [
    section("牛排系列", [
        dish("菲力牛排", "菲力牛排，嫩滑多汁", 128.0, "牛排,菲力,嫩滑", True),
        dish("西冷牛排", "西冷牛排，有嚼劲", 108.0, "牛排,西冷,有嚼劲", True),
        dish("肋眼牛排", "肋眼牛排，油花丰富", 118.0, "牛排,肋眼,油花"),
        dish("T骨牛排", "T骨牛排，一排两吃", 138.0, "牛排,T骨,双拼"),
    ]),
    section("意面披萨", [
        dish("奶油培根意面", "奶油培根意面，浓郁顺滑", 48.0, "意面,奶油,培根", True),
        dish("番茄肉酱意面", "番茄肉酱意面，酸甜开胃", 42.0, "意面,番茄,肉酱"),
        dish("玛格丽特披萨", "玛格丽特披萨，经典美味", 58.0, "披萨,玛格丽特,经典"),
        dish("培根披萨", "培根披萨，咸香可口", 62.0, "披萨,培根,咸香"),
    ]),
]

CHUANCAI_CATEGORIES = [
    section("经典川菜", [
        dish("麻婆豆腐", "麻婆豆腐，麻辣鲜香", 28.0, "川菜,豆腐,麻辣", True),
        dish("回锅肉", "回锅肉，肥而不腻", 38.0, "川菜,猪肉,回锅", True),
        dish("水煮鱼", "水煮鱼，麻辣嫩滑", 58.0, "川菜,鱼,水煮"),
        dish("宫保鸡丁", "宫保鸡丁，香辣开胃", 35.0, "川菜,鸡肉,宫保"),
        dish("鱼香肉丝", "鱼香肉丝，酸甜微辣", 32.0, "川菜,猪肉,鱼香"),
    ]),
    section("川味小吃", [
        dish("担担面", "担担面，麻辣鲜香", 22.0, "川菜,面条,担担", True),
        dish("钟水饺", "钟水饺，红油香辣", 18.0, "川菜,饺子,红油"),
        dish("龙抄手", "龙抄手，皮薄馅大", 16.0, "川菜,抄手,清汤"),
        dish("夫妻肺片", "夫妻肺片，麻辣爽口", 32.0, "川菜,牛肉,麻辣"),
        dish("川北凉粉", "川北凉粉，爽滑开胃", 12.0, "川菜,凉粉,酸辣"),
    ]),
]

XIANGCAI_CATEGORIES = [
    section("家常小炒", [
        dish("辣椒炒肉", "辣椒炒肉，下饭神器", 29.0, "湘菜,辣椒,猪肉", True),
        dish("小炒黄牛肉", "小炒黄牛肉，嫩滑多汁", 42.0, "湘菜,牛肉,小炒", True),
        dish("攸县香干炒肉", "攸县香干炒肉，香辣可口", 32.0, "湘菜,香干,猪肉"),
        dish("外婆菜炒鸡蛋", "外婆菜炒鸡蛋，开胃下饭", 28.0, "湘菜,外婆菜,鸡蛋"),
        dish("干锅肥肠", "干锅肥肠，香辣浓郁", 46.0, "湘菜,肥肠,干锅"),
    ]),
    section("砂锅热菜", [
        dish("剁椒鱼头", "剁椒鱼头，鲜辣开胃", 58.0, "湘菜,鱼头,剁椒", True),
        dish("砂锅排骨", "砂锅排骨，软烂入味", 48.0, "湘菜,排骨,砂锅"),
        dish("农家一碗香", "农家一碗香，蛋香肉香", 33.0, "湘菜,鸡蛋,猪肉"),
        dish("口味虾", "口味虾，麻辣鲜香", 68.0, "湘菜,虾,麻辣"),
        dish("毛氏红烧肉", "毛氏红烧肉，肥而不腻", 42.0, "湘菜,猪肉,红烧"),
    ]),
]

QINGSHI_CATEGORIES = [
    section("能量碗", [
        dish("香煎鸡胸藜麦碗", "香煎鸡胸搭配藜麦，高蛋白低脂", 33.0, "轻食,鸡胸,藜麦", True),
        dish("牛肉南瓜能量碗", "牛肉搭配南瓜，营养均衡", 37.0, "轻食,牛肉,南瓜", True),
        dish("三文鱼牛油果碗", "三文鱼搭配牛油果，清爽健康", 42.0, "轻食,三文鱼,牛油果"),
        dish("虾仁蔬菜碗", "虾仁搭配时蔬，低卡饱腹", 35.0, "轻食,虾仁,蔬菜"),
    ]),
    section("轻食卷饼", [
        dish("牛油果鲜虾卷", "牛油果鲜虾卷，清爽不寡淡", 26.0, "轻食,卷饼,牛油果", True),
        dish("香草鸡肉卷", "香草鸡肉卷，口感清爽", 29.0, "轻食,卷饼,鸡肉"),
        dish("烟熏三文鱼卷", "烟熏三文鱼卷，风味独特", 32.0, "轻食,卷饼,三文鱼"),
        dish("蔬菜素食卷", "蔬菜素食卷，纯素健康", 22.0, "轻食,卷饼,素食"),
    ]),
]

KAFFEE_CATEGORIES = [
    section("咖啡系列", [
        dish("燕麦拿铁", "燕麦拿铁，奶香平衡", 21.0, "咖啡,燕麦,拿铁", True),
        dish("美式咖啡", "美式咖啡，经典醇香", 18.0, "咖啡,美式,经典"),
        dish("卡布奇诺", "卡布奇诺，奶泡绵密", 22.0, "咖啡,卡布奇诺,奶泡"),
        dish("手冲咖啡", "手冲咖啡，风味纯净", 28.0, "咖啡,手冲,精品"),
    ]),
    section("甜点烘焙", [
        dish("巴斯克芝士蛋糕", "巴斯克芝士蛋糕，焦香浓郁", 28.0, "甜点,芝士,蛋糕", True),
        dish("提拉米苏杯", "提拉米苏杯，绵密微苦", 26.0, "甜点,提拉米苏,意式"),
        dish("可颂面包", "可颂面包，外酥里软", 15.0, "烘焙,可颂,面包"),
        dish("肉桂卷", "肉桂卷，香甜可口", 16.0, "烘焙,肉桂,甜点"),
    ]),
]

ZHAJI_HANBAO_CATEGORIES = [
    section("汉堡系列", [
        dish("厚切牛肉堡", "厚切牛肉堡，肉香扎实", 31.0, "汉堡,牛肉,厚切", True),
        dish("香辣鸡腿堡", "香辣鸡腿堡，外脆里嫩", 28.0, "汉堡,鸡肉,香辣", True),
        dish("双层芝士堡", "双层芝士堡，芝士浓郁", 35.0, "汉堡,芝士,双层"),
        dish("鳕鱼堡", "鳕鱼堡，鱼肉鲜嫩", 32.0, "汉堡,鳕鱼,海鲜"),
    ]),
    section("炸鸡小食", [
        dish("原味炸鸡块", "原味炸鸡块，肉汁充足", 26.0, "炸鸡,原味,热卖", True),
        dish("甜辣鸡翅", "甜辣鸡翅，韩式风味", 24.0, "炸鸡,鸡翅,甜辣"),
        dish("芝士薯条", "芝士薯条，浓郁拉丝", 18.0, "小吃,薯条,芝士"),
        dish("洋葱圈", "洋葱圈，酥脆可口", 15.0, "小吃,洋葱圈,酥脆"),
    ]),
]

ZHOUMLAN_CATEGORIES = [
    section("粥品系列", [
        dish("皮蛋瘦肉粥", "皮蛋瘦肉粥，顺滑暖胃", 14.0, "粥,皮蛋,瘦肉", True),
        dish("艇仔粥", "艇仔粥，配料丰富", 18.0, "粥,海鲜,配料", True),
        dish("生滚鱼片粥", "生滚鱼片粥，鲜美嫩滑", 16.0, "粥,鱼片,鲜美"),
        dish("南瓜粥", "南瓜粥，香甜软糯", 12.0, "粥,南瓜,甜口"),
    ]),
    section("面食点心", [
        dish("鲜虾云吞面", "鲜虾云吞面，汤头鲜甜", 22.0, "面,云吞,鲜虾", True),
        dish("生煎包", "生煎包，底脆汁多", 12.0, "点心,生煎,肉馅"),
        dish("鲜肉小馄饨", "鲜肉小馄饨，皮薄汤鲜", 15.0, "馄饨,鲜肉,清汤"),
        dish("葱油拌面", "葱油拌面，葱香四溢", 14.0, "面,葱油,拌面"),
    ]),
]

RIHAN_CATEGORIES = [
    section("定食系列", [
        dish("照烧鸡排饭", "照烧鸡排饭，咸甜平衡", 29.0, "盖饭,鸡排,照烧", True),
        dish("鳗鱼饭", "鳗鱼饭，酱香浓郁", 43.0, "盖饭,鳗鱼,日式", True),
        dish("咖喱猪排饭", "咖喱猪排饭，香浓顺滑", 32.0, "盖饭,猪排,咖喱"),
        dish("牛肉丼", "牛肉丼，鲜嫩多汁", 35.0, "盖饭,牛肉,日式"),
    ]),
    section("小食料理", [
        dish("章鱼小丸子", "章鱼小丸子，酱香弹嫩", 16.0, "小吃,章鱼,日式", True),
        dish("炸虾天妇罗", "炸虾天妇罗，酥脆鲜美", 22.0, "小吃,天妇罗,虾"),
        dish("味噌汤", "味噌汤，暖胃开胃", 10.0, "汤品,味噌,日式"),
        dish("日式煎饺", "日式煎饺，底脆馅嫩", 18.0, "小吃,煎饺,日式"),
    ]),
]

MALATANG_CATEGORIES = [
    section("汤底选择", [
        dish("骨汤麻辣烫", "骨汤麻辣烫，汤底浓郁", 26.0, "麻辣烫,骨汤,招牌", True),
        dish("番茄麻辣烫", "番茄麻辣烫，酸甜开胃", 24.0, "麻辣烫,番茄,酸甜", True),
        dish("菌汤麻辣烫", "菌汤麻辣烫，鲜香清淡", 22.0, "麻辣烫,菌汤,清淡"),
        dish("麻辣拌", "麻辣拌，干拌更香", 25.0, "麻辣烫,干拌,麻辣"),
    ]),
    section("配菜选择", [
        dish("肥牛卷", "肥牛卷，肉香十足", 12.0, "加料,肥牛,肉类"),
        dish("虾滑", "虾滑，弹嫩鲜香", 14.0, "加料,虾滑,海鲜"),
        dish("午餐肉", "午餐肉，经典美味", 8.0, "加料,午餐肉,经典"),
        dish("宽粉", "宽粉，软糯入味", 6.0, "加料,宽粉,主食"),
        dish("豆皮", "豆皮，吸汁十足", 5.0, "加料,豆皮,素菜"),
    ]),
]

PIASA_CATEGORIES = [
    section("披萨系列", [
        dish("玛格丽特披萨", "玛格丽特披萨，番茄芝士经典", 42.0, "披萨,经典,番茄", True),
        dish("榴莲披萨", "榴莲披萨，芝士拉丝", 56.0, "披萨,榴莲,热销", True),
        dish("培根披萨", "培根披萨，咸香可口", 48.0, "披萨,培根,咸口"),
        dish("海鲜披萨", "海鲜披萨，鲜美多汁", 58.0, "披萨,海鲜,鲜美"),
        dish("BBQ鸡肉披萨", "BBQ鸡肉披萨，烟熏风味", 52.0, "披萨,鸡肉,BBQ"),
    ]),
    section("意面焗饭", [
        dish("奶油培根意面", "奶油培根意面，浓郁顺滑", 38.0, "意面,奶油,培根", True),
        dish("番茄肉酱意面", "番茄肉酱意面，酸甜开胃", 35.0, "意面,番茄,肉酱"),
        dish("芝士鸡排焗饭", "芝士鸡排焗饭，奶香浓郁", 29.0, "焗饭,鸡排,芝士"),
        dish("海鲜焗饭", "海鲜焗饭，料足味鲜", 33.0, "焗饭,海鲜,芝士"),
    ]),
]


EXTENDED_MERCHANTS_V2 = [
    build_merchant_v2(
        name="虾皇烧烤",
        description="主打夜宵小龙虾和炭火烧烤，聚会首选",
        district="黄浦",
        homepage_category="龙虾烧烤",
        promo_text="龙虾啤酒套餐立减25元",
        delivery_radius_meters=3500,
        delivery_fee=6.0,
        min_order_amount=58.0,
        avg_delivery_minutes=38,
        rating=4.7,
        categories=LONGXIA_SHAOKAO_CATEGORIES,
    ),
    build_merchant_v2(
        name="串串香",
        description="地道成都串串香，锅底多样选择多",
        district="虹口",
        homepage_category="火锅串串",
        promo_text="串串满100送锅底",
        delivery_radius_meters=3000,
        delivery_fee=5.0,
        min_order_amount=45.0,
        avg_delivery_minutes=32,
        rating=4.6,
        categories=HUOGUO_CHUANCHUAN_CATEGORIES,
    ),
    build_merchant_v2(
        name="煌上煌",
        description="招牌鸭货卤味，追剧必备零食",
        district="普陀",
        homepage_category="鸭脖卤味",
        promo_text="鸭脖鸭翅套餐立减12元",
        delivery_radius_meters=2500,
        delivery_fee=3.0,
        min_order_amount=25.0,
        avg_delivery_minutes=25,
        rating=4.7,
        categories=YABO_LUWEI_CATEGORIES,
    ),
    build_merchant_v2(
        name="王品牛排",
        description="精品牛排西餐，约会聚餐首选",
        district="闵行",
        homepage_category="西餐",
        promo_text="双人牛排套餐立减60元",
        delivery_radius_meters=3000,
        delivery_fee=8.0,
        min_order_amount=88.0,
        avg_delivery_minutes=40,
        rating=4.8,
        categories=XICAN_CATEGORIES,
    ),
    build_merchant_v2(
        name="眉州东坡",
        description="正宗川菜馆，麻辣鲜香地道口味",
        district="宝山",
        homepage_category="川菜",
        promo_text="川菜满100减25",
        delivery_radius_meters=3200,
        delivery_fee=5.0,
        min_order_amount=45.0,
        avg_delivery_minutes=33,
        rating=4.6,
        categories=CHUANCAI_CATEGORIES,
    ),
    build_merchant_v2(
        name="湘味人家",
        description="家常湘菜小炒，下饭神器",
        district="黄浦",
        homepage_category="湘菜",
        promo_text="双人湘菜套餐立减15元",
        delivery_radius_meters=3200,
        delivery_fee=4.0,
        min_order_amount=20.0,
        avg_delivery_minutes=28,
        rating=4.6,
        categories=XIANGCAI_CATEGORIES,
    ),
    build_merchant_v2(
        name="超级碗轻食",
        description="高蛋白低脂轻食，健身人群首选",
        district="虹口",
        homepage_category="轻食",
        promo_text="能量碗套餐减10元",
        delivery_radius_meters=2800,
        delivery_fee=5.0,
        min_order_amount=26.0,
        avg_delivery_minutes=29,
        rating=4.7,
        categories=QINGSHI_CATEGORIES,
    ),
    build_merchant_v2(
        name="星巴克咖啡",
        description="经典咖啡品牌，品质稳定",
        district="普陀",
        homepage_category="咖啡甜品",
        promo_text="咖啡加烘焙立减8元",
        delivery_radius_meters=2500,
        delivery_fee=3.0,
        min_order_amount=18.0,
        avg_delivery_minutes=24,
        rating=4.8,
        categories=KAFFEE_CATEGORIES,
    ),
    build_merchant_v2(
        name="麦当劳",
        description="经典快餐品牌，出餐快速",
        district="闵行",
        homepage_category="炸鸡汉堡",
        promo_text="单人套餐立减7元",
        delivery_radius_meters=3000,
        delivery_fee=6.0,
        min_order_amount=29.0,
        avg_delivery_minutes=34,
        rating=4.5,
        categories=ZHAJI_HANBAO_CATEGORIES,
    ),
    build_merchant_v2(
        name="嘉和一品粥",
        description="养生粥品面点，早餐首选",
        district="宝山",
        homepage_category="粥面",
        promo_text="早点套餐满25减8",
        delivery_radius_meters=2600,
        delivery_fee=4.0,
        min_order_amount=18.0,
        avg_delivery_minutes=25,
        rating=4.6,
        categories=ZHOUMLAN_CATEGORIES,
    ),
    build_merchant_v2(
        name="吉野家",
        description="日式牛肉饭连锁，出餐快速",
        district="黄浦",
        homepage_category="日韩料理",
        promo_text="定食套餐减10元",
        delivery_radius_meters=3000,
        delivery_fee=5.0,
        min_order_amount=35.0,
        avg_delivery_minutes=32,
        rating=4.6,
        categories=RIHAN_CATEGORIES,
    ),
    build_merchant_v2(
        name="杨国福麻辣烫",
        description="连锁麻辣烫品牌，汤底浓郁",
        district="虹口",
        homepage_category="麻辣烫",
        promo_text="满39元送饮料",
        delivery_radius_meters=3200,
        delivery_fee=4.0,
        min_order_amount=22.0,
        avg_delivery_minutes=29,
        rating=4.5,
        categories=MALATANG_CATEGORIES,
    ),
    build_merchant_v2(
        name="达美乐披萨",
        description="外卖披萨专家，30分钟送达",
        district="普陀",
        homepage_category="披萨意面",
        promo_text="披萨买一送一",
        delivery_radius_meters=3300,
        delivery_fee=5.0,
        min_order_amount=30.0,
        avg_delivery_minutes=35,
        rating=4.6,
        categories=PIASA_CATEGORIES,
    ),
]
