# -*- coding: utf-8 -*-
"""扩展商家种子数据 V3 — 在已有品类内增加多样性，总计 100 商家 ~1000 菜品"""


def _stable_number(value: str) -> int:
    return sum(ord(c) for c in value)


def _unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for v in values:
        if v and v not in ordered:
            ordered.append(v)
    return ordered


def _build_phone(name: str) -> str:
    return f"021-{62000000 + _stable_number(name) % 3000000:08d}"


def _build_business_hours(name: str, homepage_category: str) -> str:
    hours_map = {
        "湘菜": ["10:00-21:30", "09:30-21:00", "10:30-22:00"],
        "轻食": ["08:30-20:00", "09:00-20:30", "10:00-20:00"],
        "咖啡甜品": ["09:00-21:00", "10:00-21:30", "11:00-22:00"],
        "炸鸡汉堡": ["10:30-22:30", "11:00-23:00", "10:00-22:00"],
        "粥面": ["06:30-13:30,17:00-22:30", "07:00-14:00,17:30-23:00", "06:30-21:30"],
        "日韩料理": ["10:30-21:30", "11:00-22:00", "10:00-21:00"],
        "麻辣烫": ["10:30-23:00", "11:00-23:30", "10:00-22:30"],
        "披萨意面": ["10:30-21:30", "11:00-22:00", "10:00-21:00"],
        "龙虾烧烤": ["16:00-02:00", "17:00-03:00", "15:30-01:30"],
        "火锅串串": ["11:00-23:00", "10:30-22:30", "11:30-23:30"],
        "鸭脖卤味": ["10:00-22:00", "09:30-21:30", "10:30-22:30"],
        "西餐": ["11:00-21:30", "10:30-22:00", "11:30-22:30"],
        "川菜": ["10:30-21:30", "11:00-22:00", "10:00-21:00"],
    }
    options = hours_map.get(homepage_category, ["10:00-21:00"])
    return options[_stable_number(name) % len(options)]


def _build_address(district: str, name: str) -> tuple[str, str]:
    district_map = {
        "静安": ("南京西路 818 号", 121.4521, 31.2291),
        "徐汇": ("漕溪北路 399 号", 121.4372, 31.1948),
        "浦东": ("张杨路 1088 号", 121.5440, 31.2282),
        "杨浦": ("黄兴路 1888 号", 121.5254, 31.2990),
        "长宁": ("长宁路 1018 号", 121.4246, 31.2202),
        "黄浦": ("南京东路 100 号", 121.4846, 31.2304),
        "虹口": ("四川北路 2000 号", 121.4903, 31.2648),
        "普陀": ("中山北路 3000 号", 121.4113, 31.2483),
        "闵行": ("沪闵路 4000 号", 121.3817, 31.1122),
        "宝山": ("牡丹江路 500 号", 121.4894, 31.4052),
    }
    d = district_map[district]
    code = _stable_number(name)
    suffixes = ["中心广场", "邻里汇", "时光里", "星坊", "悦荟", "国际商厦", "生活广场", "美食城", "汇金中庭", "万象天地"]
    floor = code % 4 + 1
    room = 101 + code % 180
    addr = f"{d[0].replace(' ','')}{suffixes[code % len(suffixes)]}{floor}层{room}室"
    return addr, d[1] + (code % 30) * 0.001, d[2] + (code % 25) * 0.001


def _build_address_note(name: str, district: str) -> str:
    landmarks = {
        "静安": "地铁站商务楼下", "徐汇": "写字楼连廊口", "浦东": "商场沿街外摆位",
        "杨浦": "大学路街角", "长宁": "社区商业入口", "黄浦": "步行街入口处",
        "虹口": "公园东门对面", "普陀": "地铁站出口旁", "闵行": "小区门口",
        "宝山": "公交站附近",
    }
    return f"近{landmarks[district]}{_stable_number(name) % 6 + 1}号取餐点"


def _tags(cat: str, desc: str, promo: str, avg_min: int) -> list[str]:
    tag_map = {
        "湘菜": ["现炒", "下饭菜", "工作餐"],
        "轻食": ["轻负担", "高蛋白", "午餐优选"],
        "咖啡甜品": ["下午茶", "手作甜点", "咖啡搭子"],
        "炸鸡汉堡": ["现炸", "能量快餐", "夜宵友好"],
        "粥面": ["暖胃", "早餐", "夜宵"],
        "日韩料理": ["定食", "便当感", "清爽口味"],
        "麻辣烫": ["锅底可选", "重口爱好", "晚餐热门"],
        "披萨意面": ["多人分享", "芝士控", "西式简餐"],
        "龙虾烧烤": ["夜宵首选", "聚会必点", "现烤现吃"],
        "火锅串串": ["串串自由", "锅底多样", "深夜食堂"],
        "鸭脖卤味": ["追剧伴侣", "下酒好菜", "休闲零食"],
        "西餐": ["约会首选", "精致摆盘", "西式风味"],
        "川菜": ["麻辣鲜香", "下饭菜", "地道川味"],
    }
    tags = list(tag_map.get(cat, ["美食", "热销"]))
    if "下午茶" in desc: tags.append("下午茶")
    if "夜宵" in desc or avg_min >= 35: tags.append("夜宵友好")
    if "工作日" in desc or avg_min <= 28: tags.append("午餐快送")
    if "双人" in promo or "套餐" in promo: tags.append("套餐点单")
    return _unique(tags)[:3]


def build_merchant(*, name, description, district, homepage_category, promo_text,
                   delivery_radius_meters, delivery_fee, min_order_amount,
                   avg_delivery_minutes, rating, categories):
    addr, lon, lat = _build_address(district, name)
    return {
        "name": name, "description": description, "city": "上海", "district": district,
        "address": addr, "longitude": lon, "latitude": lat,
        "homepage_category": homepage_category, "promo_text": promo_text,
        "delivery_radius_meters": delivery_radius_meters, "delivery_fee": delivery_fee,
        "min_order_amount": min_order_amount, "avg_delivery_minutes": avg_delivery_minutes,
        "rating": rating, "phone": _build_phone(name),
        "business_hours": _build_business_hours(name, homepage_category),
        "detailed_address": addr, "address_note": _build_address_note(name, district),
        "merchant_tags": _tags(homepage_category, description, promo_text, avg_delivery_minutes),
        "categories": categories,
    }


def section(name: str, dishes: list[dict]) -> dict:
    return {"name": name, "dishes": dishes}


def dish(name: str, description: str, price: float, tags: str, is_rec: bool = False) -> dict:
    return {"name": name, "description": description, "price": price, "tags": tags,
            "cuisine_type": "", "flavor_profile": "", "ingredients": [],
            "allergens": [], "cooking_method": "", "is_recommended": is_rec}


# ═══════════════════════════════════════════════════════════════
# 湘菜 (+4 merchants, ~40 dishes)
# ═══════════════════════════════════════════════════════════════

XC_FRY_HOME = [
    section("猛火小炒", [
        dish("辣椒炒肉", "猪前腿肉配青红椒爆炒，锅气十足", 29, "招牌,下饭", True),
        dish("酸萝卜炒牛百叶", "自制酸萝卜配牛百叶，酸辣开胃", 38, "酸辣,爽脆"),
        dish("腊肉炒蒜薹", "湘西腊肉配嫩蒜薹，烟熏咸香", 35, "腊味,时令"),
        dish("紫苏煎黄瓜", "紫苏叶煎黄瓜片，清香微辣", 22, "素菜,特色"),
        dish("口味牛蛙", "现杀牛蛙配泡椒小米辣，鲜嫩入味", 52, "招牌,辣味", True),
    ]),
    section("蒸菜煲汤", [
        dish("剁椒蒸排骨", "仔排铺满剁椒蒸制，鲜辣脱骨", 45, "蒸菜,下饭", True),
        dish("腊味合蒸", "腊肉腊肠腊鱼三拼蒸，咸香浓郁", 42, "腊味,经典"),
        dish("肉丸菌汤", "手工猪肉丸配菌菇慢炖，汤鲜味醇", 28, "汤品,暖胃"),
        dish("清炒时蔬", "当日时蔬猛火快炒，清脆爽口", 18, "素菜"),
    ]),
]

XC_SMOKE_POT = [
    section("烟熏腊味", [
        dish("湘西烟熏肉", "柴火烟熏五花肉，切片爆炒", 38, "熏肉,经典", True),
        dish("茶油炒土鸡", "山茶油爆炒土鸡块，皮脆肉紧", 46, "土鸡,招牌"),
        dish("白辣椒炒肉", "湖南白辣椒配前腿肉，干香下饭", 32, "特色,辣味"),
        dish("蒜苗炒猪血丸子", "邵阳猪血丸子配青蒜苗，烟熏豆香", 28, "特色,素荤"),
    ]),
    section("瓦罐煨汤", [
        dish("海带排骨瓦罐汤", "小瓦罐慢煨三小时，排骨酥烂", 24, "汤品,煨制", True),
        dish("墨鱼炖肉", "干墨鱼配五花肉煨制，海鲜肉香交融", 36, "汤品,浓香"),
        dish("冰糖湘莲", "湘潭莲子配冰糖桂花，清甜软糯", 16, "甜品,传统"),
        dish("米饭", "东北香米现煮", 2, "主食"),
    ]),
]

XC_SPICY_LEGEND = [
    section("镇店硬菜", [
        dish("剁椒鱼头", "三斤大雄鱼头铺满剁椒，鲜辣嫩滑", 68, "招牌,大菜", True),
        dish("跳跳蛙", "现杀牛蛙配青红花椒，麻辣鲜嫩", 55, "招牌,麻辣"),
        dish("毛氏红烧肉", "五花三层慢炖，肥而不腻入口即化", 42, "经典,下饭", True),
        dish("宁乡花猪肉", "宁乡花猪前腿肉配辣椒，肉香浓郁", 48, "特色,土猪"),
    ]),
    section("下饭搭档", [
        dish("擂辣椒皮蛋", "炭火烤椒配松花蛋擂制，烟熏香辣", 18, "凉菜,特色"),
        dish("酸豆角肉沫", "自制酸豆角配猪肉沫，开胃搭饭", 16, "小炒,下饭"),
        dish("蒸水蛋", "土鸡蛋蒸制嫩滑，淋酱汁葱花", 12, "家常,清淡"),
        dish("米豆腐", "湖南米豆腐红烧，软糯入味配饭绝", 20, "素菜,特色"),
    ]),
]

XC_MALA_KITCHEN = [
    section("麻辣主打", [
        dish("麻辣子鸡", "去骨鸡腿肉爆炒，外焦里麻辣十足", 39, "招牌,麻辣", True),
        dish("水煮牛肉", "牛肉片配豆芽辣椒油泼，麻辣嫩滑", 52, "大菜,重口"),
        dish("干锅花菜", "有机花菜配五花肉干锅煸炒", 26, "干锅,素菜", True),
        dish("辣卤猪蹄", "猪蹄卤制后再辣炒，Q弹入味", 38, "卤味,下酒"),
    ]),
    section("主食汤品", [
        dish("酸辣鸡杂面", "新鲜鸡杂配酸辣汤底，爽口开胃", 24, "面食,酸辣"),
        dish("老姜肉片汤", "老姜片配猪肉片煲汤，驱寒暖胃", 18, "汤品,暖身"),
        dish("酱油炒饭", "隔夜饭配老抽鸡蛋大火炒，粒粒分明", 15, "主食,经典"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 轻食 (+3 merchants, ~27 dishes)
# ═══════════════════════════════════════════════════════════════

QS_POKE_BOWL = [
    section("波奇碗", [
        dish("金枪鱼波奇碗", "刺身级金枪鱼配寿司饭牛油果", 45, "海鲜,高蛋白", True),
        dish("照烧三文鱼碗", "照烧三文鱼配温泉蛋藜麦", 42, "三文鱼,日式", True),
        dish("鲜虾芒果碗", "南美白虾配芒果蔬菜沙拉", 38, "鲜虾,果香"),
        dish("豆腐素食碗", "煎豆腐配毛豆玉米藜麦", 28, "素食,高蛋白"),
    ]),
    section("沙拉果昔", [
        dish("超级绿沙拉", "羽衣甘蓝菠菜配牛油果青酱", 32, "沙拉,排毒"),
        dish("彩虹考伯沙拉", "鸡肉鸡蛋牛油果番茄玉米拼配", 35, "沙拉,经典"),
        dish("芒果百香果昔", "芒果百香果香蕉鲜榨", 24, "果昔,维C"),
        dish("甜菜根能量饮", "甜菜根苹果胡萝卜冷压", 22, "果汁,抗氧化"),
    ]),
]

QS_ASIAN_BOWL = [
    section("亚洲碗", [
        dish("韩式拌饭碗", "韩式辣酱拌牛肉蔬菜藜麦饭", 35, "韩式,辣味", True),
        dish("泰式鸡肉碗", "香茅鸡肉配青木瓜沙拉", 33, "泰式,清爽"),
        dish("越式春卷碗", "鲜虾米纸春卷配鱼露花生酱", 30, "越南,清爽", True),
        dish("印尼加多加多碗", "花生酱拌豆腐蔬菜鸡蛋", 28, "印尼,素食"),
    ]),
    section("健康小食", [
        dish("鹰嘴豆泥配皮塔", "自制鹰嘴豆泥配烤皮塔饼", 18, "小食,高蛋白"),
        dish("烤红薯条", "红薯切条烘烤，天然甜香", 15, "小食,粗粮"),
        dish("抹茶奇亚籽布丁", "抹茶奇亚籽椰奶布丁，低糖", 16, "甜品,超级食物"),
    ]),
]

QS_PROTEIN_BOX = [
    section("蛋白便当", [
        dish("鸡胸肉便当盒", "低温慢煮鸡胸配杂粮蔬菜", 36, "健身,高蛋白", True),
        dish("三文鱼便当盒", "煎三文鱼配糙米饭西兰花", 42, "三文鱼,欧米伽3"),
        dish("牛肉便当盒", "新西兰草饲牛肉配烤南瓜", 45, "牛肉,铁质"),
        dish("全素便当盒", "豆腐天贝配藜麦时蔬", 30, "素食,植物蛋白"),
    ]),
    section("轻饮系列", [
        dish("冷压橙汁", "鲜橙冷压原汁，不加水糖", 18, "果汁,维C"),
        dish("燕麦奶拿铁", "浓缩咖啡配燕麦奶", 22, "咖啡,植物奶"),
        dish("椰子水", "泰国椰青直供，天然电解质", 16, "饮品,补水"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 咖啡甜品 (+3 merchants, ~27 dishes)
# ═══════════════════════════════════════════════════════════════

KF_SPECIALTY = [
    section("精品手冲", [
        dish("耶加雪菲手冲", "埃塞柑橘花香调，日晒处理", 32, "手冲,精品", True),
        dish("曼特宁手冲", "苏门答腊醇厚草本，深烘", 28, "手冲,深烘"),
        dish("瑰夏手冲", "巴拿马翡翠庄园，花香果酸", 58, "手冲,顶级", True),
        dish("冷萃咖啡瓶", "12小时冷萃瓶装，顺滑低酸", 25, "冷萃,便携"),
    ]),
    section("创意特调", [
        dish("海盐焦糖拿铁", "海盐焦糖酱配浓缩燕麦奶", 28, "特调,甜感"),
        dish("椰子冷萃", "椰子水配冷萃咖啡分层", 26, "特调,清爽"),
        dish("桂花酒酿拿铁", "桂花酒酿配拿铁，秋日限定", 30, "限定,花香"),
        dish("开心果拿铁", "开心果酱融入燕麦拿铁", 32, "特调,坚果"),
    ]),
]

KF_BAKERY = [
    section("现烤面包", [
        dish("法式可颂", "法国AOP黄油折叠，层次分明", 16, "面包,法式", True),
        dish("巧克力丹麦", "法芙娜黑巧夹心丹麦酥皮", 18, "面包,巧克力"),
        dish("肉桂卷", "瑞典配方肉桂卷配奶油奶酪", 16, "面包,北欧", True),
        dish("蔓越莓贝果", "全麦贝果配蔓越莓干", 14, "面包,健康"),
    ]),
    section("精致甜点", [
        dish("抹茶千层", "宇治抹茶配淡奶油二十层", 32, "甜点,抹茶", True),
        dish("榴莲芝士挞", "猫山王榴莲配烤芝士", 28, "甜点,榴莲"),
        dish("伯爵茶布蕾", "川宁伯爵茶融入法式烤布蕾", 22, "甜点,茶味"),
        dish("马卡龙礼盒", "六种口味法式马卡龙", 48, "甜点,礼盒"),
    ]),
]

KF_TEAHOUSE = [
    section("中国茶", [
        dish("明前龙井", "西湖核心产区明前龙井", 38, "茶,绿茶", True),
        dish("正山小种", "桐木关传统烟熏正山小种", 32, "茶,红茶"),
        dish("凤凰单丛", "乌岽村老丛鸭屎香", 42, "茶,乌龙"),
        dish("陈年普洱", "勐海十年陈熟普", 28, "茶,黑茶"),
    ]),
    section("茶饮搭配", [
        dish("龙井奶盖", "现萃龙井配淡奶油咸奶盖", 25, "茶饮,创新"),
        dish("白桃乌龙冷泡", "白桃干配台湾高山乌龙", 18, "茶饮,果味"),
        dish("桂花绿豆糕", "去皮绿豆桂花手工糕", 12, "茶点,传统"),
        dish("核桃酥", "黄油核桃酥饼，酥到掉渣", 15, "茶点,酥饼"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 炸鸡汉堡 (+3 merchants, ~24 dishes)
# ═══════════════════════════════════════════════════════════════

ZH_CHICKEN_KING = [
    section("炸鸡招牌", [
        dish("原味炸鸡桶", "8块原味炸鸡配蜂蜜芥末酱", 68, "炸鸡,桶装", True),
        dish("香辣脆皮鸡", "四川花椒腌料炸鸡，麻辣酥脆", 32, "炸鸡,辣味", True),
        dish("蒜香酱油炸鸡", "韩式蒜香酱油裹酱炸鸡", 36, "炸鸡,韩式"),
        dish("芝士雪花炸鸡", "芝士粉撒面配年糕", 38, "炸鸡,芝士"),
    ]),
    section("汉堡拼盘", [
        dish("安格斯牛肉堡", "150g安格斯牛肉饼配车达芝士", 38, "汉堡,牛肉", True),
        dish("炸鸡汉堡", "去骨鸡腿肉炸制配卷心菜沙拉", 28, "汉堡,鸡肉"),
        dish("巨无霸牛肉堡", "双倍牛肉饼配培根芝士", 48, "汉堡,超大"),
    ]),
]

ZH_BURGER_CRAFT = [
    section("手工汉堡", [
        dish("经典芝士堡", "100天谷饲牛肉饼配美式芝士", 35, "汉堡,经典", True),
        dish("培根BBQ堡", "枫糖培根配烟熏BBQ酱牛肉饼", 39, "汉堡,美式", True),
        dish("素食蘑菇堡", "波特菇扒配鹰嘴豆饼", 32, "汉堡,素食"),
        dish("夏威夷堡", "烤菠萝片配照烧牛肉饼", 37, "汉堡,创新"),
    ]),
    section("小食饮品", [
        dish("松露薯条", "黑松露油配帕玛森芝士薯条", 22, "薯条,升级"),
        dish("水牛城鸡翅", "经典水牛城辣酱鸡翅6只", 32, "鸡翅,美式"),
        dish("奶昔", "香草冰淇淋现打奶昔", 18, "饮品,甜品"),
    ]),
]

ZH_KOREAN_FRY = [
    section("韩式炸鸡", [
        dish("原味韩式炸鸡", "两次油炸外酥里嫩配萝卜", 58, "炸鸡,韩式", True),
        dish("甜辣韩式炸鸡", "韩国辣椒酱裹酱炸鸡半只", 62, "炸鸡,甜辣", True),
        dish("蜂蜜黄油炸鸡", "蜂蜜黄油酱配炸鸡翅中", 55, "炸鸡,甜咸"),
    ]),
    section("韩式小食", [
        dish("辣炒年糕", "韩式辣酱炒年糕配鱼饼", 22, "韩式,小吃"),
        dish("泡菜煎饼", "酸辣泡菜配面糊煎制", 18, "韩式,煎饼"),
        dish("韩式炸酱面", "春酱炒制配黄瓜丝", 26, "韩式,面食"),
        dish("紫菜包饭", "紫菜卷牛肉菠菜蛋皮", 16, "韩式,主食"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 粥面 (+3 merchants, ~24 dishes)
# ═══════════════════════════════════════════════════════════════

ZM_HAND_PULL = [
    section("手工拉面", [
        dish("兰州牛肉面", "现拉毛细面条配牛骨清汤牛肉", 22, "拉面,清真", True),
        dish("油泼扯面", "宽面扯制油泼辣子配蒜末", 18, "扯面,西北"),
        dish("炸酱面", "五花肉丁甜面酱炸酱配黄瓜", 20, "面食,北京", True),
        dish("西红柿鸡蛋面", "番茄浓汤配鸡蛋手擀面", 16, "面食,家常"),
    ]),
    section("小菜搭配", [
        dish("酱牛肉", "牛腱子酱制切片，纹理分明", 28, "凉菜,卤味"),
        dish("拍黄瓜", "蒜泥醋汁拍碎黄瓜", 8, "凉菜,清爽"),
        dish("卤蛋", "秘制卤汁卤鸡蛋两颗", 6, "佐餐,卤味"),
    ]),
]

ZM_CONFERENCE_HOUSE = [
    section("招牌粥品", [
        dish("生滚牛肉粥", "现切牛肉片滚粥，嫩滑鲜美", 22, "粥,牛肉", True),
        dish("状元及第粥", "猪肝瘦肉猪腰滚制，料足", 25, "粥,广东", True),
        dish("鲍鱼鸡粥", "鲜鲍鱼仔配走地鸡熬粥", 38, "粥,海鲜"),
        dish("山药排骨粥", "铁棍山药配排骨慢熬", 20, "粥,滋补"),
    ]),
    section("肠粉点心", [
        dish("鲜虾肠粉", "现拉肠粉裹鲜虾仁，淋甜酱油", 18, "肠粉,广东", True),
        dish("叉烧肠粉", "蜜汁叉烧肠粉配甜酱", 16, "肠粉,经典"),
        dish("流沙包", "咸蛋黄奶黄流沙包三只", 14, "点心,蒸点"),
    ]),
]

ZM_RICE_NOODLE = [
    section("米粉米线", [
        dish("过桥米线", "云南建水米线配十碟小料鸡汤", 32, "米线,云南", True),
        dish("螺蛳粉", "柳州螺蛳粉配酸笋腐竹花生", 18, "米粉,广西", True),
        dish("酸辣粉", "红薯粉配酸辣汤底肉沫", 15, "粉,四川"),
        dish("炒牛河", "干炒牛河配芽菜韭黄", 26, "河粉,广东"),
    ]),
    section("风味小吃", [
        dish("炸春卷", "素馅春卷炸制金黄", 12, "小吃,炸物"),
        dish("红油抄手", "猪肉抄手配红油芝麻", 16, "抄手,川味"),
        dish("冰粉", "手搓冰粉配红糖坚果", 10, "甜品,四川"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 日韩料理 (+3 merchants, ~27 dishes)
# ═══════════════════════════════════════════════════════════════

RH_RAMEN = [
    section("拉面定食", [
        dish("豚骨拉面", "猪骨熬制18小时白汤配叉烧溏心蛋", 38, "拉面,豚骨", True),
        dish("味噌拉面", "北海道赤味噌汤底配玉米黄油", 35, "拉面,味噌"),
        dish("酱油拉面", "东京风清汤酱油配笋干葱丝", 32, "拉面,酱油"),
        dish("激辛拉面", "地狱辣豚骨汤底配叉烧", 39, "拉面,辣味", True),
    ]),
    section("小食配菜", [
        dish("煎饺", "日式冰花煎饺六只", 18, "饺子,日式"),
        dish("炸鸡块", "唐扬鸡块配塔塔酱", 22, "炸物,日式"),
        dish("枝豆", "盐煮毛豆配啤酒更佳", 10, "小食,素食"),
        dish("叉烧饭", "炙烤叉烧肉盖饭配酱汁", 32, "盖饭,猪肉"),
    ]),
]

RH_KOREAN_SOUP = [
    section("韩式汤煲", [
        dish("参鸡汤", "整只童子鸡腹塞糯米人参炖制", 58, "汤煲,滋补", True),
        dish("大酱汤", "韩式大酱配豆腐西葫芦蛤蜊", 28, "汤品,家常"),
        dish("部队锅", "午餐肉年糕拉面泡菜一锅煮", 48, "火锅,韩式", True),
        dish("嫩豆腐汤", "韩国辣酱嫩豆腐海鲜汤配鸡蛋", 26, "汤品,辣味"),
    ]),
    section("韩式主食", [
        dish("石锅拌饭", "石锅烤制锅巴饭配五色蔬菜", 32, "拌饭,辣酱", True),
        dish("韩式冷面", "荞麦冷面配冰镇牛肉汤", 25, "冷面,夏季"),
        dish("紫菜包饭卷", "金枪鱼泡菜紫菜包饭", 18, "主食,便当"),
        dish("泡菜炒饭", "韩国泡菜配五花肉炒饭", 28, "炒饭,韩式"),
    ]),
]

RH_IZAKAYA = [
    section("居酒屋料理", [
        dish("烤串拼盘", "鸡肉大葱牛肉香菇烤串五本", 36, "烤串,居酒屋", True),
        dish("天妇罗拼盘", "虾蔬菜天妇罗配萝卜泥蘸汁", 42, "天妇罗,日式"),
        dish("刺身拼盘", "三文鱼甜虾北海道扇贝刺身", 88, "刺身,海鲜", True),
        dish("盐烤青花鱼", "挪威青花鱼盐烤，皮脆肉嫩", 32, "烤鱼,日式"),
    ]),
    section("酒肴轻食", [
        dish("芥末章鱼", "活章鱼配山葵渍", 18, "小食,下酒"),
        dish("明太子玉子烧", "九州明太子卷入玉子烧", 22, "蛋料理,日式"),
        dish("豆腐沙拉", "绢豆腐配芝麻酱沙拉", 16, "沙拉,素食"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 麻辣烫 (+3 merchants, ~24 dishes)
# ═══════════════════════════════════════════════════════════════

MLT_PREMIUM = [
    section("精品汤底", [
        dish("花胶鸡汤麻辣烫", "走地鸡花胶熬制金汤底", 32, "汤底,滋补", True),
        dish("冬阴功汤麻辣烫", "泰式冬阴功酸辣汤底", 28, "汤底,泰式"),
        dish("草本骨汤麻辣烫", "当归枸杞配猪骨白汤", 24, "汤底,养生"),
        dish("咖喱汤麻辣烫", "日式咖喱汤底配椰浆", 26, "汤底,咖喱"),
    ]),
    section("精选食材", [
        dish("和牛卷", "澳洲和牛薄切入汤", 18, "肉类,高端"),
        dish("鲜虾滑", "手打虾滑配鱼籽", 14, "海鲜,手打"),
        dish("蟹味菇拼盘", "三种菌菇拼配", 10, "菌菇,素食"),
        dish("响铃卷", "豆腐衣卷炸制吸汤", 8, "豆制品,经典"),
    ]),
]

MLT_SICHUAN_MASTER = [
    section("川味冒菜", [
        dish("毛肚冒菜", "新鲜毛肚配麻辣红油冒制", 36, "冒菜,招牌", True),
        dish("肥牛冒菜", "雪花肥牛配金针菇冒制", 32, "冒菜,牛肉", True),
        dish("猪脑冒菜", "鲜猪脑配花椒冒制，嫩滑", 28, "冒菜,特色"),
        dish("素菜冒菜拼", "藕片土豆海带豆皮全素拼", 18, "冒菜,素食"),
    ]),
    section("拌面佐餐", [
        dish("麻辣拌面", "芝麻酱辣油拌手工面", 16, "面食,麻辣"),
        dish("冰粉", "红糖冰粉配山楂碎花生", 8, "甜品,解辣"),
        dish("酸梅汤", "乌梅山楂甘草熬制", 6, "饮品,解辣"),
    ]),
]

MLT_HEALTHY = [
    section("清爽系麻辣烫", [
        dish("番茄牛腩麻辣烫", "新鲜番茄熬汤配牛腩块", 28, "汤底,番茄", True),
        dish("菌汤蔬菜麻辣烫", "七种菌菇熬汤纯素搭配", 22, "汤底,素食"),
        dish("清汤豆腐麻辣烫", "日式出汁配嫩豆腐蔬菜", 20, "汤底,日式"),
        dish("泡菜汤麻辣烫", "韩国泡菜五花肉汤底", 24, "汤底,韩式"),
    ]),
    section("健康小料", [
        dish("魔芋丝", "低卡魔芋丝，弹牙爽滑", 6, "素食,低卡"),
        dish("竹荪", "野生竹荪，吸汤入味", 10, "菌菇,高端"),
        dish("海带芽", "嫩海带芽，补充碘质", 5, "海藻,营养"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 披萨意面 (+3 merchants, ~27 dishes)
# ═══════════════════════════════════════════════════════════════

PS_ITALIAN_AUTH = [
    section("认证披萨", [
        dish("那不勒斯披萨", "STG认证圣马扎诺番茄水牛芝士", 58, "披萨,意式", True),
        dish("四季披萨", "四种配料代表四季，火腿菌菇橄榄", 62, "披萨,经典"),
        dish("卡布里乔莎披萨", "朝鲜蓟火腿蘑菇橄榄", 55, "披萨,罗马"),
        dish("卡拉布里亚辣肠披萨", "南意卡拉布里亚辣肠", 52, "披萨,辣味", True),
    ]),
    section("意面烩饭", [
        dish("博洛尼亚肉酱面", "宽面配慢炖牛肉酱", 42, "意面,经典", True),
        dish("海鲜墨鱼面", "墨鱼汁意面配虾仁蛤蜊", 48, "意面,海鲜"),
        dish("牛肝菌烩饭", "意大利牛肝菌配帕玛森烩饭", 52, "烩饭,菌菇"),
        dish("青酱虾仁意面", "罗勒松子青酱配鲜虾意面", 45, "意面,利古里亚"),
    ]),
]

PS_AMERICAN_PIZZA = [
    section("美式厚底披萨", [
        dish("至尊披萨", "培根牛肉香肠青椒洋葱蘑菇", 68, "披萨,美式", True),
        dish("BBQ鸡肉披萨", "烟熏BBQ酱鸡肉配红洋葱", 55, "披萨,美式"),
        dish("水牛城鸡肉披萨", "水牛城辣酱鸡肉配蓝纹芝士", 58, "披萨,辣味"),
        dish("纯芝士披萨", "五种芝士拼配厚底拉丝", 48, "披萨,芝士控"),
    ]),
    section("美式小食", [
        dish("水牛城鸡翅", "经典辣酱鸡翅配蓝纹芝士酱", 28, "鸡翅,美式", True),
        dish("芝士面包条", "蒜香黄油面包条配番茄酱", 18, "小食,面包"),
        dish("凯撒沙拉", "罗马生菜凯撒酱帕玛森", 22, "沙拉,经典"),
    ]),
]

PS_CREATIVE_KITCHEN = [
    section("融合创新", [
        dish("北京烤鸭披萨", "烤鸭片配甜面酱大葱", 62, "披萨,融合", True),
        dish("麻婆豆腐披萨", "麻婆豆腐铺底配芝士", 48, "披萨,川味融合"),
        dish("鳗鱼披萨", "蒲烧鳗鱼配蛋丝海苔", 58, "披萨,日式融合", True),
        dish("避风塘炒蟹披萨", "港式避风塘蟹味海鲜披萨", 66, "披萨,港式融合"),
    ]),
    section("意面创新", [
        dish("咸蛋黄海鲜意面", "咸蛋黄酱配鲜虾鱿鱼", 45, "意面,创新"),
        dish("老干妈鸡肉意面", "老干妈辣酱配鸡腿肉意面", 38, "意面,中西合璧"),
        dish("泰式冬阴功意面", "冬阴功酱配海鲜意面", 42, "意面,泰式融合"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 龙虾烧烤 (+2 merchants, ~18 dishes)
# ═══════════════════════════════════════════════════════════════

LX_SIGNATURE = [
    section("招牌龙虾", [
        dish("金汤蒜蓉龙虾", "蒜蓉炒制金黄配大龙虾", 128, "龙虾,蒜蓉", True),
        dish("冰醉龙虾", "花雕酒冰镇熟醉大龙虾", 158, "龙虾,酒醉", True),
        dish("麻辣龙虾", "四川花椒干辣椒爆炒龙虾", 108, "龙虾,麻辣"),
        dish("蛋黄龙虾", "咸蛋黄焗龙虾，沙沙口感", 118, "龙虾,咸蛋黄"),
    ]),
    section("烧烤串", [
        dish("红柳羊肉串", "红柳枝穿羊肉大串", 8, "烧烤,羊肉", True),
        dish("烤生蚝", "蒜蓉粉丝烤生蚝半打", 36, "烧烤,海鲜"),
        dish("烤羊排", "新西兰法式羊排炭烤", 68, "烧烤,羊排", True),
        dish("烤大虾", "黑虎虾盐烤配柠檬", 48, "烧烤,海鲜"),
        dish("烤馒头片", "馒头切片烤制刷酱", 6, "烧烤,主食"),
    ]),
]

LX_SEAFOOD_BBQ = [
    section("海鲜烧烤", [
        dish("烤鱿鱼", "整只鱿鱼铁板酱烤", 25, "烧烤,海鲜", True),
        dish("烤扇贝", "蒜蓉粉丝烤扇贝六只", 42, "烧烤,海鲜"),
        dish("烤秋刀鱼", "盐烤秋刀鱼配柠檬萝卜泥", 22, "烧烤,鱼类"),
        dish("烤海螺", "海螺炭火烤制蘸酱", 38, "烧烤,海鲜"),
    ]),
    section("下酒菜", [
        dish("毛豆荚", "盐水煮毛豆荚", 12, "小食,素食"),
        dish("盐水花生", "五香盐水煮花生", 10, "小食,下酒"),
        dish("拍黄瓜", "蒜泥拍黄瓜", 8, "凉菜,清爽"),
        dish("烤面包片", "黄油烤面包片", 8, "主食,黄油"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 火锅串串 (+2 merchants, ~18 dishes)
# ═══════════════════════════════════════════════════════════════

HG_CHONGQING = [
    section("重庆老火锅", [
        dish("九宫格红油锅", "重庆石柱红辣椒牛油锅底", 58, "火锅,红油", True),
        dish("屠场鲜毛肚", "当天宰杀鲜毛肚冰镇", 68, "涮品,招牌", True),
        dish("鲜鸭血", "鲜鸭血块入红汤", 22, "涮品,嫩滑"),
        dish("贡菜", "安徽涡阳贡菜干涮制脆爽", 16, "涮品,素菜"),
        dish("耗儿鱼", "冰鲜耗儿鱼入红汤", 32, "涮品,鱼类"),
    ]),
    section("必点涮品", [
        dish("极品肥牛", "雪花肥牛薄切入锅", 48, "涮品,牛肉"),
        dish("手打虾滑", "鲜虾手打虾滑", 38, "涮品,海鲜"),
        dish("现炸酥肉", "现炸酥肉直接吃或涮", 28, "小吃,猪肉"),
        dish("红糖糍粑", "糯米糍粑配红糖黄豆粉", 16, "甜品,四川"),
    ]),
]

HG_BEIJING = [
    section("老北京涮肉", [
        dish("手切鲜羊肉", "宁夏滩羊手切厚片", 58, "涮肉,羊肉", True),
        dish("大三岔肥牛", "雪花肥牛大三岔部位", 68, "涮肉,牛肉", True),
        dish("羊上脑", "羊上脑部位切片，肥瘦相间", 52, "涮肉,羊肉"),
        dish("百叶", "鲜牛百叶涮制蘸麻酱", 38, "涮品,牛杂"),
    ]),
    section("京味配菜", [
        dish("烧饼", "芝麻酱烧饼现烤", 8, "主食,北京"),
        dish("糖蒜", "老北京糖蒜解腻", 6, "小食,传统"),
        dish("芥末墩", "芥末拌白菜墩", 12, "凉菜,北京"),
        dish("杏仁豆腐", "甜杏仁豆腐清凉收尾", 15, "甜品,北京"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 鸭脖卤味 (+2 merchants, ~16 dishes)
# ═══════════════════════════════════════════════════════════════

YB_SPICY_HOUSE = [
    section("麻辣卤味", [
        dish("麻辣鸭脖", "四川花椒辣椒卤制鸭脖", 18, "卤味,麻辣", True),
        dish("麻辣鸭翅", "鸭翅中段麻辣卤制", 15, "卤味,麻辣"),
        dish("麻辣鸭舌", "鸭舌麻辣卤制，下酒佳品", 28, "卤味,高档"),
        dish("香辣鸭锁骨", "鸭锁骨香辣卤制", 12, "卤味,香辣"),
    ]),
    section("卤味拼盘", [
        dish("卤味素拼", "藕片海带豆干腐竹素拼", 15, "卤味,素食", True),
        dish("卤牛肉", "金钱腱卤制切片", 38, "卤味,牛肉"),
        dish("卤凤爪", "脱骨凤爪卤制入味", 22, "卤味,凤爪"),
        dish("卤鸡蛋", "卤汁卤鸡蛋四颗装", 10, "卤味,鸡蛋"),
    ]),
]

YB_SWEET_SPICY = [
    section("甜辣系列", [
        dish("甜辣鸭脖", "韩国辣酱蜂蜜调制甜辣鸭脖", 18, "卤味,甜辣", True),
        dish("甜辣鸭翅", "甜辣酱鸭翅中", 15, "卤味,甜辣"),
        dish("柠檬凤爪", "柠檬酸辣无骨凤爪", 26, "凉拌,酸辣", True),
        dish("泡椒凤爪", "四川泡椒腌制凤爪", 22, "凉拌,泡椒"),
    ]),
    section("休闲搭配", [
        dish("辣条拼盘", "手工辣条小面筋大刀肉", 10, "零食,辣条"),
        dish("五香花生米", "蒜香五香花生米", 8, "零食,下酒"),
        dish("海苔肉松小贝", "海苔肉松包裹蛋糕", 18, "甜点,零食"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 西餐 (+2 merchants, ~18 dishes)
# ═══════════════════════════════════════════════════════════════

XCAN_FRENCH = [
    section("法式料理", [
        dish("油封鸭腿", "法式油封鸭腿配蒜香土豆", 68, "法式,经典", True),
        dish("勃艮第炖牛肉", "红酒炖牛肉配蘑菇小洋葱", 78, "法式,红酒"),
        dish("普罗旺斯炖菜", "茄子节瓜番茄彩椒炖制", 42, "法式,素食"),
        dish("法式洋葱汤", "焦糖洋葱配格鲁耶芝士烤面包", 38, "汤品,法式", True),
    ]),
    section("法式甜品", [
        dish("焦糖布蕾", "香草籽焦糖布蕾现烤", 28, "甜品,法式", True),
        dish("巧克力熔岩蛋糕", "法芙娜黑巧熔岩配香草冰淇淋", 38, "甜品,巧克力"),
        dish("可露丽", "波尔多可露丽焦脆内嫩", 18, "甜品,经典"),
    ]),
]

XCAN_MEDITERRANEAN = [
    section("地中海风味", [
        dish("希腊沙拉", "菲达芝士番茄黄瓜橄榄油", 32, "沙拉,希腊", True),
        dish("西班牙海鲜饭", "藏红花海鲜饭配虾贝", 78, "主食,西班牙", True),
        dish("摩洛哥羊肉塔吉锅", "羊肉配杏干杏仁炖制", 68, "炖菜,摩洛哥"),
        dish("土耳其烤肉卷", "旋转烤肉配酸奶酱皮塔饼", 42, "卷饼,土耳其"),
    ]),
    section("佐酒小食", [
        dish("西班牙土豆烘蛋", "土豆洋葱鸡蛋烘制", 28, "小食,西班牙"),
        dish("烤蔬菜拼盘", "地中海烤蔬菜配香草橄榄油", 35, "素食,烤制"),
        dish("意式烤面包", "番茄罗勒烤面包片", 22, "小食,意大利"),
        dish("提拉米苏", "意式马斯卡彭提拉米苏", 32, "甜品,意式", True),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 川菜 (+2 merchants, ~18 dishes)
# ═══════════════════════════════════════════════════════════════

CC_CLASSIC = [
    section("经典川菜", [
        dish("水煮鱼", "鲜活草鱼片油泼辣椒花椒", 58, "川菜,水煮", True),
        dish("辣子鸡", "带骨鸡块干辣椒爆炒", 42, "川菜,干煸", True),
        dish("鱼香茄子", "鱼香汁配油炸茄子煲", 28, "川菜,鱼香"),
        dish("麻婆豆腐", "郫县豆瓣花椒豆腐煲", 24, "川菜,麻辣", True),
        dish("回锅肉", "二刀肉配蒜苗豆瓣酱回锅", 36, "川菜,经典"),
    ]),
    section("下饭凉菜", [
        dish("夫妻肺片", "牛肉牛杂红油凉拌", 32, "凉菜,红油", True),
        dish("口水鸡", "白斩鸡配红油花生碎", 28, "凉菜,红油"),
        dish("蒜泥白肉", "二刀肉薄片配蒜泥红油", 32, "凉菜,蒜香"),
        dish("川北凉粉", "豌豆凉粉配红油醋汁", 12, "凉菜,酸辣"),
    ]),
]

CC_HOME_TASTE = [
    section("家常川味", [
        dish("水煮肉片", "猪里脊配豆芽油泼", 38, "川菜,水煮", True),
        dish("宫保鸡丁", "鸡腿肉丁配花生米葱段", 32, "川菜,宫保", True),
        dish("干煸四季豆", "四季豆配芽菜肉沫干煸", 22, "川菜,干煸"),
        dish("酸菜鱼", "老坛酸菜配黑鱼片", 52, "川菜,酸菜", True),
    ]),
    section("主食汤羹", [
        dish("担担面", "肉臊子担担面配碎花生", 22, "面食,四川", True),
        dish("酸辣粉", "红薯粉配酸辣肉沫汤", 16, "粉,四川"),
        dish("醪糟汤圆", "糯米小汤圆配甜酒酿", 12, "甜品,四川"),
        dish("番茄蛋花汤", "番茄蛋花配葱花", 12, "汤品,家常"),
    ]),
]

# ═══════════════════════════════════════════════════════════════
# 汇总37家新商家
# ═══════════════════════════════════════════════════════════════

EXTENDED_MERCHANTS_V3 = [
    # ── 湘菜 +4 ──
    build_merchant(name="猛火湘厨", description="主打猛火小炒和蒸菜煲汤，锅气足", district="黄浦", homepage_category="湘菜", promo_text="双人下饭套餐立减15元", delivery_radius_meters=3200, delivery_fee=4.0, min_order_amount=22, avg_delivery_minutes=29, rating=4.7, categories=XC_FRY_HOME),
    build_merchant(name="烟熏火燎", description="湘西烟熏腊味和瓦罐煨汤专营", district="虹口", homepage_category="湘菜", promo_text="烟熏腊味满60减10", delivery_radius_meters=3100, delivery_fee=4.5, min_order_amount=24, avg_delivery_minutes=32, rating=4.5, categories=XC_SMOKE_POT),
    build_merchant(name="湘辣传奇", description="剁椒鱼头等镇店硬菜搭配下饭凉菜", district="普陀", homepage_category="湘菜", promo_text="招牌鱼头套餐减20元", delivery_radius_meters=3300, delivery_fee=5.0, min_order_amount=28, avg_delivery_minutes=31, rating=4.6, categories=XC_SPICY_LEGEND),
    build_merchant(name="麻辣湘厨", description="麻辣子鸡和水煮牛肉为主打的麻辣湘味", district="闵行", homepage_category="湘菜", promo_text="麻辣招牌满80减15", delivery_radius_meters=3000, delivery_fee=4.5, min_order_amount=25, avg_delivery_minutes=30, rating=4.5, categories=XC_MALA_KITCHEN),

    # ── 轻食 +3 ──
    build_merchant(name="波奇碗工坊", description="夏威夷波奇碗和沙拉果昔专营，新鲜健康", district="静安", homepage_category="轻食", promo_text="波奇碗双人组合减12元", delivery_radius_meters=2800, delivery_fee=5.0, min_order_amount=28, avg_delivery_minutes=26, rating=4.7, categories=QS_POKE_BOWL),
    build_merchant(name="亚洲碗局", description="韩式泰式越式亚洲风味能量碗", district="虹口", homepage_category="轻食", promo_text="亚洲碗满40赠饮品", delivery_radius_meters=2700, delivery_fee=4.5, min_order_amount=25, avg_delivery_minutes=27, rating=4.6, categories=QS_ASIAN_BOWL),
    build_merchant(name="蛋白便当", description="健身蛋白便当配杂粮蔬菜，低脂高蛋白", district="徐汇", homepage_category="轻食", promo_text="便当双拼立减10元", delivery_radius_meters=2600, delivery_fee=4.0, min_order_amount=25, avg_delivery_minutes=28, rating=4.5, categories=QS_PROTEIN_BOX),

    # ── 咖啡甜品 +3 ──
    build_merchant(name="手冲研习社", description="精品手冲咖啡和创意特调专营", district="徐汇", homepage_category="咖啡甜品", promo_text="手冲第二杯半价", delivery_radius_meters=2400, delivery_fee=3.0, min_order_amount=22, avg_delivery_minutes=23, rating=4.8, categories=KF_SPECIALTY),
    build_merchant(name="麦香烘焙坊", description="法式现烤面包和精致甜点，每日新鲜", district="静安", homepage_category="咖啡甜品", promo_text="面包加咖啡立减6元", delivery_radius_meters=2500, delivery_fee=3.5, min_order_amount=18, avg_delivery_minutes=25, rating=4.6, categories=KF_BAKERY),
    build_merchant(name="一壶茶舍", description="中式茶饮和手工茶点，雅致慢生活", district="黄浦", homepage_category="咖啡甜品", promo_text="茶饮加茶点立减8元", delivery_radius_meters=2300, delivery_fee=3.0, min_order_amount=20, avg_delivery_minutes=24, rating=4.7, categories=KF_TEAHOUSE),

    # ── 炸鸡汉堡 +3 ──
    build_merchant(name="炸鸡大王", description="原味香辣蒜香多种口味炸鸡桶", district="杨浦", homepage_category="炸鸡汉堡", promo_text="炸鸡桶第二份半价", delivery_radius_meters=3100, delivery_fee=5.5, min_order_amount=30, avg_delivery_minutes=32, rating=4.5, categories=ZH_CHICKEN_KING),
    build_merchant(name="堡格手作", description="手工牛肉汉堡，100天谷饲牛肉", district="黄浦", homepage_category="炸鸡汉堡", promo_text="汉堡套餐加购饮品半价", delivery_radius_meters=2900, delivery_fee=5.0, min_order_amount=32, avg_delivery_minutes=33, rating=4.7, categories=ZH_BURGER_CRAFT),
    build_merchant(name="韩式炸鸡屋", description="正宗韩式甜辣炸鸡配年糕", district="普陀", homepage_category="炸鸡汉堡", promo_text="韩式半只鸡套餐减12元", delivery_radius_meters=3000, delivery_fee=5.0, min_order_amount=35, avg_delivery_minutes=30, rating=4.6, categories=ZH_KOREAN_FRY),

    # ── 粥面 +3 ──
    build_merchant(name="手工拉面馆", description="手工拉面扯面配西北小菜", district="浦东", homepage_category="粥面", promo_text="拉面加小菜减5元", delivery_radius_meters=2700, delivery_fee=3.5, min_order_amount=18, avg_delivery_minutes=26, rating=4.6, categories=ZM_HAND_PULL),
    build_merchant(name="靓粥世家", description="广东生滚粥和现拉肠粉，正宗老广味", district="闵行", homepage_category="粥面", promo_text="粥品满35送肠粉", delivery_radius_meters=2500, delivery_fee=4.0, min_order_amount=18, avg_delivery_minutes=24, rating=4.7, categories=ZM_CONFERENCE_HOUSE),
    build_merchant(name="米粉江湖", description="云南米线广西螺蛳粉等各地米粉精选", district="长宁", homepage_category="粥面", promo_text="米粉满30减6元", delivery_radius_meters=2600, delivery_fee=3.5, min_order_amount=16, avg_delivery_minutes=25, rating=4.5, categories=ZM_RICE_NOODLE),

    # ── 日韩料理 +3 ──
    build_merchant(name="拉面一番", description="正宗日式豚骨味噌酱油拉面专营", district="长宁", homepage_category="日韩料理", promo_text="拉面套餐减8元", delivery_radius_meters=2800, delivery_fee=5.0, min_order_amount=35, avg_delivery_minutes=30, rating=4.7, categories=RH_RAMEN),
    build_merchant(name="韩式汤馆", description="参鸡汤大酱汤部队锅等韩式汤煲", district="宝山", homepage_category="日韩料理", promo_text="汤煲双人套餐减15元", delivery_radius_meters=2900, delivery_fee=5.0, min_order_amount=32, avg_delivery_minutes=33, rating=4.5, categories=RH_KOREAN_SOUP),
    build_merchant(name="居酒屋一番", description="日式居酒屋风格烤串刺身天妇罗", district="静安", homepage_category="日韩料理", promo_text="刺身拼盘满80送清酒", delivery_radius_meters=2700, delivery_fee=5.5, min_order_amount=38, avg_delivery_minutes=31, rating=4.8, categories=RH_IZAKAYA),

    # ── 麻辣烫 +3 ──
    build_merchant(name="汤底大师", description="花胶鸡冬阴功等精品汤底麻辣烫", district="黄浦", homepage_category="麻辣烫", promo_text="精品汤底立减6元", delivery_radius_meters=3000, delivery_fee=4.5, min_order_amount=25, avg_delivery_minutes=28, rating=4.7, categories=MLT_PREMIUM),
    build_merchant(name="川味冒菜坊", description="正宗四川冒菜配拌面甜品", district="徐汇", homepage_category="麻辣烫", promo_text="冒菜满40赠冰粉", delivery_radius_meters=3200, delivery_fee=4.0, min_order_amount=22, avg_delivery_minutes=30, rating=4.6, categories=MLT_SICHUAN_MASTER),
    build_merchant(name="轻煮小烫", description="清爽型麻辣烫，七种汤底任选", district="杨浦", homepage_category="麻辣烫", promo_text="清汤系列第二份半价", delivery_radius_meters=2800, delivery_fee=4.0, min_order_amount=20, avg_delivery_minutes=29, rating=4.5, categories=MLT_HEALTHY),

    # ── 披萨意面 +3 ──
    build_merchant(name="意式认证披萨", description="STG认证正宗那不勒斯披萨和手工意面", district="黄浦", homepage_category="披萨意面", promo_text="认证披萨双拼减20元", delivery_radius_meters=3200, delivery_fee=6.0, min_order_amount=35, avg_delivery_minutes=36, rating=4.8, categories=PS_ITALIAN_AUTH),
    build_merchant(name="美式厚底披萨屋", description="经典美式厚底披萨和水牛城鸡翅", district="宝山", homepage_category="披萨意面", promo_text="美式套餐立减15元", delivery_radius_meters=3300, delivery_fee=5.5, min_order_amount=32, avg_delivery_minutes=34, rating=4.5, categories=PS_AMERICAN_PIZZA),
    build_merchant(name="融合厨房", description="北京烤鸭麻婆豆腐鳗鱼等融合披萨", district="虹口", homepage_category="披萨意面", promo_text="融合披萨满80赠饮品", delivery_radius_meters=3100, delivery_fee=5.0, min_order_amount=30, avg_delivery_minutes=35, rating=4.6, categories=PS_CREATIVE_KITCHEN),

    # ── 龙虾烧烤 +2 ──
    build_merchant(name="龙虾世家", description="金汤蒜蓉冰醉等多种高端龙虾配红柳烧烤", district="虹口", homepage_category="龙虾烧烤", promo_text="龙虾满200减30", delivery_radius_meters=3600, delivery_fee=7.0, min_order_amount=68, avg_delivery_minutes=40, rating=4.7, categories=LX_SIGNATURE),
    build_merchant(name="渔港烧烤", description="海鲜烧烤和炭火烤肉，新鲜海产直供", district="宝山", homepage_category="龙虾烧烤", promo_text="海鲜烧烤拼盘88折", delivery_radius_meters=3500, delivery_fee=6.5, min_order_amount=55, avg_delivery_minutes=38, rating=4.5, categories=LX_SEAFOOD_BBQ),

    # ── 火锅串串 +2 ──
    build_merchant(name="重庆老灶火锅", description="重庆九宫格红油火锅屠场鲜毛肚", district="普陀", homepage_category="火锅串串", promo_text="火锅满150减25", delivery_radius_meters=3100, delivery_fee=6.0, min_order_amount=50, avg_delivery_minutes=35, rating=4.7, categories=HG_CHONGQING),
    build_merchant(name="京味涮肉坊", description="老北京铜锅涮肉配宁夏滩羊手切", district="闵行", homepage_category="火锅串串", promo_text="涮肉双人套餐减30元", delivery_radius_meters=3000, delivery_fee=5.5, min_order_amount=55, avg_delivery_minutes=33, rating=4.6, categories=HG_BEIJING),

    # ── 鸭脖卤味 +2 ──
    build_merchant(name="麻辣卤味坊", description="四川麻辣鸭脖鸭翅鸭舌及卤味拼盘", district="黄浦", homepage_category="鸭脖卤味", promo_text="卤味满50送素拼", delivery_radius_meters=2600, delivery_fee=3.0, min_order_amount=25, avg_delivery_minutes=24, rating=4.6, categories=YB_SPICY_HOUSE),
    build_merchant(name="甜辣卤味屋", description="韩式甜辣鸭脖及柠檬酸辣凤爪", district="徐汇", homepage_category="鸭脖卤味", promo_text="甜辣系列买二赠一", delivery_radius_meters=2500, delivery_fee=3.0, min_order_amount=22, avg_delivery_minutes=23, rating=4.7, categories=YB_SWEET_SPICY),

    # ── 西餐 +2 ──
    build_merchant(name="法式小馆", description="法式油封鸭勃艮第炖牛肉等经典法餐", district="静安", homepage_category="西餐", promo_text="法式双人套餐减50元", delivery_radius_meters=2900, delivery_fee=7.0, min_order_amount=88, avg_delivery_minutes=38, rating=4.8, categories=XCAN_FRENCH),
    build_merchant(name="地中海厨房", description="西班牙海鲜饭摩洛哥塔吉锅等地中海风味", district="浦东", homepage_category="西餐", promo_text="地中海拼盘立减20元", delivery_radius_meters=3000, delivery_fee=6.5, min_order_amount=75, avg_delivery_minutes=36, rating=4.6, categories=XCAN_MEDITERRANEAN),

    # ── 川菜 +2 ──
    build_merchant(name="巴蜀经典", description="水煮鱼辣子鸡等经典川菜配红油凉菜", district="杨浦", homepage_category="川菜", promo_text="川菜满120减25", delivery_radius_meters=3200, delivery_fee=5.0, min_order_amount=45, avg_delivery_minutes=33, rating=4.7, categories=CC_CLASSIC),
    build_merchant(name="家常川味馆", description="水煮肉片宫保鸡丁等家常川菜配主食", district="长宁", homepage_category="川菜", promo_text="家常川菜满60减12", delivery_radius_meters=3100, delivery_fee=4.5, min_order_amount=35, avg_delivery_minutes=31, rating=4.6, categories=CC_HOME_TASTE),

    # ── 额外两商家 (v4填充至100) ──
    build_merchant(name="火宫殿", description="长沙百年老字号臭豆腐糖油粑粑等经典小吃", district="静安", homepage_category="湘菜", promo_text="小吃拼盘满50减10", delivery_radius_meters=3000, delivery_fee=4.0, min_order_amount=20, avg_delivery_minutes=27, rating=4.8, categories=[
        section("经典小吃", [
            dish("臭豆腐", "长沙火宫殿配方，外焦里嫩配萝卜丁", 15, "小吃,招牌", True),
            dish("糖油粑粑", "糯米粑粑裹红糖油炸，软糯甜香", 12, "小吃,甜口"),
            dish("葱油饼", "香葱猪油层叠煎制，外酥里软", 10, "小吃,葱香"),
            dish("刮凉粉", "蚕豆凉粉配红油花生碎", 14, "凉菜,酸辣"),
            dish("姊妹团子", "肉馅糖馅双拼糯米团子", 16, "小吃,蒸制"),
        ]),
        section("湘味硬菜", [
            dish("剁椒蒸鱼头", "三斤大雄鱼头铺满剁椒蒸制", 68, "湘菜,招牌", True),
            dish("腊味合蒸", "腊肉腊肠腊鱼三拼蒸", 45, "湘菜,腊味"),
            dish("辣椒炒肉", "前腿肉配青椒猛火爆炒", 29, "湘菜,下饭"),
            dish("肉丸菌汤", "手打肉丸配茶树菇炖制", 28, "汤品,暖胃"),
            dish("外婆菜炒饭", "湖南外婆菜配蛋炒饭", 18, "主食,湘味"),
        ]),
        section("甜品饮品", [
            dish("甜酒冲蛋", "甜酒酿冲土鸡蛋配桂花", 10, "甜品,暖身"),
            dish("绿豆沙", "去皮绿豆慢熬冰镇", 8, "饮品,解辣"),
            dish("酸梅汤", "乌梅山楂甘草古法熬制", 8, "饮品,解暑"),
        ]),
    ]),
    build_merchant(name="海鲜大排档", description="新鲜海鲜现点现做，椒盐避风塘等多样做法", district="浦东", homepage_category="龙虾烧烤", promo_text="海鲜满200减35", delivery_radius_meters=3500, delivery_fee=7.0, min_order_amount=68, avg_delivery_minutes=42, rating=4.7, categories=[
        section("主打海鲜", [
            dish("避风塘炒蟹", "鲜活青蟹配金蒜面包糠", 128, "海鲜,避风塘", True),
            dish("椒盐皮皮虾", "大皮皮虾椒盐爆炒", 88, "海鲜,椒盐", True),
            dish("豉汁蒸鲍鱼", "六头鲜活鲍鱼豉汁蒸制", 108, "海鲜,清蒸"),
            dish("葱姜炒蟹", "鲜活花蟹葱姜爆炒", 78, "海鲜,粤式"),
            dish("蒜蓉粉丝蒸扇贝", "北海道扇贝蒜蓉粉丝蒸半打", 68, "海鲜,清蒸"),
            dish("白灼虾", "鲜活基围虾白灼蘸酱油", 58, "海鲜,白灼"),
        ]),
        section("烧烤系列", [
            dish("烤生蚝", "湛江生蚝蒜蓉炭烤半打", 42, "烧烤,海鲜", True),
            dish("烤海虾", "黑虎虾海盐炭烤", 48, "烧烤,海鲜"),
            dish("烤鱿鱼", "整只鱿鱼铁板酱烤", 28, "烧烤,海鲜"),
            dish("烤茄子", "茄子蒜蓉烤制", 12, "烧烤,素菜"),
            dish("羊肉串", "红柳枝羊肉串五串", 25, "烧烤,羊肉"),
        ]),
        section("佐餐搭配", [
            dish("海鲜粥", "鲜虾蟹肉生滚粥", 32, "粥品,海鲜"),
            dish("炒时蔬", "当日时蔬蒜蓉清炒", 18, "素菜,时令"),
            dish("海鲜炒饭", "虾仁鱿鱼蛋炒饭", 28, "主食,海鲜"),
            dish("椰青", "泰国椰青直供", 18, "饮品,天然"),
        ]),
    ]),
]
