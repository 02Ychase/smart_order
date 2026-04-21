from copy import deepcopy


DISTRICT_POINTS = {
    "静安": {"address": "南京西路 818 号", "longitude": 121.4521, "latitude": 31.2291},
    "徐汇": {"address": "漕溪北路 399 号", "longitude": 121.4372, "latitude": 31.1948},
    "浦东": {"address": "张杨路 1088 号", "longitude": 121.5440, "latitude": 31.2282},
    "杨浦": {"address": "黄兴路 1888 号", "longitude": 121.5254, "latitude": 31.2990},
    "长宁": {"address": "长宁路 1018 号", "longitude": 121.4246, "latitude": 31.2202},
}

CATEGORY_BUSINESS_HOURS = {
    "湘菜": ["10:00-21:30", "09:30-21:00", "10:30-22:00"],
    "轻食": ["08:30-20:00", "09:00-20:30", "10:00-20:00"],
    "咖啡甜品": ["09:00-21:00", "10:00-21:30", "11:00-22:00"],
    "炸鸡汉堡": ["10:30-22:30", "11:00-23:00", "10:00-22:00"],
    "粥面": ["06:30-13:30,17:00-22:30", "07:00-14:00,17:30-23:00", "06:30-21:30"],
    "日韩料理": ["10:30-21:30", "11:00-22:00", "10:00-21:00"],
    "麻辣烫": ["10:30-23:00", "11:00-23:30", "10:00-22:30"],
    "披萨意面": ["10:30-21:30", "11:00-22:00", "10:00-21:00"],
}

CATEGORY_TAGS = {
    "湘菜": ["现炒", "下饭菜", "工作餐"],
    "轻食": ["轻负担", "高蛋白", "午餐优选"],
    "咖啡甜品": ["下午茶", "手作甜点", "咖啡搭子"],
    "炸鸡汉堡": ["现炸", "能量快餐", "夜宵友好"],
    "粥面": ["暖胃", "早餐", "夜宵"],
    "日韩料理": ["定食", "便当感", "清爽口味"],
    "麻辣烫": ["锅底可选", "重口爱好", "晚餐热门"],
    "披萨意面": ["多人分享", "芝士控", "西式简餐"],
}

DISTRICT_LANDMARKS = {
    "静安": "地铁站商务楼下",
    "徐汇": "写字楼连廊口",
    "浦东": "商场沿街外摆位",
    "杨浦": "大学路街角",
    "长宁": "社区商业入口",
}

BUILDING_SUFFIXES = ["中心广场", "邻里汇", "时光里", "星坊", "悦荟", "国际商厦"]

SPECIFIC_INGREDIENTS = {
    "辣椒炒肉": ["猪前腿肉", "青椒", "红椒", "蒜片"],
    "攸县香干炒肉": ["攸县香干", "猪肉片", "青椒", "蒜苗"],
    "外婆菜炒鸡蛋": ["外婆菜", "鸡蛋", "蒜末", "小米椒"],
    "小炒黄牛肉": ["黄牛肉", "芹菜", "小米椒", "蒜末"],
    "皮蛋瘦肉粥": ["大米", "皮蛋", "猪瘦肉", "姜丝"],
    "鲜虾云吞面": ["鲜虾", "猪肉馅", "云吞皮", "细面"],
    "照烧鸡排饭": ["鸡腿排", "照烧汁", "洋葱", "米饭"],
    "宫保鸡丁": ["鸡胸肉", "花生米", "青椒", "红椒", "葱段"],
    "玛格丽特披萨": ["披萨饼底", "番茄酱", "马苏里拉芝士", "罗勒"],
    "奶油培根意面": ["意面", "培根", "淡奶油", "黑胡椒"],
}

HANDWRITTEN_DISH_DESCRIPTIONS = {
    "辣椒炒肉": "现切猪前腿肉搭配青红椒大火快炒，锅气足、咸香辣劲明显，是工作日最稳的下饭菜。",
    "小炒黄牛肉": "黄牛肉片现炒到刚刚断生，芹菜和小米椒提香提辣，口感嫩爽，越吃越开胃。",
    "鲜虾云吞面": "鲜虾云吞现煮后配细面和热汤，入口鲜甜不腻，适合想吃热乎主食的时候来一碗。",
    "香煎鸡胸藜麦碗": "香煎鸡胸切片铺在藜麦和时蔬上，调味清爽不厚重，饱腹感在线，做午餐很合适。",
    "燕麦拿铁": "浓缩咖啡融合燕麦奶，入口顺滑带坚果香，苦感柔和，适合上午提神或下午慢慢喝。",
    "巴斯克芝士蛋糕": "表层带一点焦香，内里绵密湿润，芝士味浓但不腻，配一杯热美式会更舒服。",
}



def _stable_number(value: str) -> int:
    return sum(ord(char) for char in value)



def _unique(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered



def _infer_cuisine_type(name: str, tags: str) -> str:
    text = f"{name},{tags}"
    rules = [
        ("湘", "湘菜"),
        ("剁椒", "湘菜"),
        ("外婆菜", "湘菜"),
        ("香干", "湘菜"),
        ("寿司", "日料"),
        ("鳗鱼", "日料"),
        ("丼", "日料"),
        ("味噌", "日料"),
        ("咖喱", "日式洋食"),
        ("麻辣烫", "麻辣烫"),
        ("冒菜", "川味麻辣"),
        ("披萨", "意式"),
        ("意面", "意式"),
        ("焗饭", "意式"),
        ("焗面", "意式"),
        ("汉堡", "美式快餐"),
        ("炸鸡", "美式快餐"),
        ("鸡翅", "美式快餐"),
        ("贝果", "轻食"),
        ("藜麦", "轻食"),
        ("沙拉", "轻食"),
        ("卷", "轻食"),
        ("能量碗", "轻食"),
        ("拿铁", "咖啡"),
        ("美式", "咖啡"),
        ("冷萃", "咖啡"),
        ("手冲", "咖啡"),
        ("可颂", "烘焙"),
        ("曲奇", "甜点"),
        ("蛋糕", "甜点"),
        ("布丁", "甜点"),
        ("挞", "甜点"),
        ("粥", "粥品"),
        ("面", "面食"),
        ("云吞", "面食"),
        ("馄饨", "面食"),
        ("饮品", "饮品"),
        ("咖啡", "咖啡"),
        ("甜点", "甜点"),
    ]
    for keyword, cuisine_type in rules:
        if keyword in text:
            return cuisine_type
    return "特色餐食"



def _infer_flavor_profile(name: str, description: str, tags: str) -> str:
    text = f"{name},{description},{tags}"
    rules = [
        ("麻辣", "麻辣浓郁"),
        ("藤椒", "清麻鲜辣"),
        ("甜辣", "甜辣回甘"),
        ("酸甜", "酸甜平衡"),
        ("香辣", "香辣开胃"),
        ("鲜辣", "鲜辣下饭"),
        ("微辣", "咸鲜微辣"),
        ("辣", "香辣"),
        ("奶香", "奶香浓郁"),
        ("芝士", "浓郁奶香"),
        ("可可", "可可微苦"),
        ("咖啡", "醇苦回甘"),
        ("果香", "清新果香"),
        ("椰香", "椰香顺滑"),
        ("豆香", "豆香咸鲜"),
        ("菌香", "菌香浓郁"),
        ("鲜甜", "鲜甜清爽"),
        ("咸鲜", "咸鲜适口"),
        ("清爽", "清爽轻盈"),
        ("甜", "香甜柔和"),
    ]
    for keyword, flavor_profile in rules:
        if keyword in text:
            return flavor_profile
    return "风味均衡"



def _infer_ingredients(name: str, description: str, tags: str, cuisine_type: str) -> list[str]:
    if name in SPECIFIC_INGREDIENTS:
        return list(SPECIFIC_INGREDIENTS[name])

    text = f"{name},{description},{tags},{cuisine_type}"
    ingredient_rules = [
        ("牛肉", ["牛肉", "洋葱", "黑胡椒", "酱汁"]),
        ("猪排", ["猪排", "面包糠", "卷心菜", "酱汁"]),
        ("鸡排", ["鸡腿排", "黑胡椒", "生菜", "米饭"]),
        ("鸡腿", ["鸡腿肉", "面包糠", "生菜", "酱料"]),
        ("鸡胸", ["鸡胸肉", "生菜", "藜麦", "玉米"]),
        ("鸡", ["鸡肉", "洋葱", "青椒", "酱汁"]),
        ("虾", ["鲜虾", "蔬菜", "调味汁", "香料"]),
        ("三文鱼", ["三文鱼", "米饭", "海苔", "黄瓜"]),
        ("鳗鱼", ["鳗鱼", "米饭", "照烧汁", "海苔"]),
        ("鱼", ["鱼肉", "辣椒", "姜丝", "葱段"]),
        ("豆腐", ["豆腐", "葱花", "酱汁", "香料"]),
        ("香干", ["香干", "青椒", "猪肉", "蒜苗"]),
        ("蛋", ["鸡蛋", "葱花", "调味汁", "食用油"]),
        ("粥", ["大米", "高汤", "姜丝", "葱花"]),
        ("云吞", ["云吞皮", "猪肉馅", "高汤", "青菜"]),
        ("面", ["面条", "高汤", "青菜", "葱花"]),
        ("寿司", ["寿司米", "海苔", "黄瓜", "鱼肉"]),
        ("沙拉", ["生菜", "番茄", "黄瓜", "油醋汁"]),
        ("藜麦", ["藜麦", "生菜", "南瓜", "鸡胸肉"]),
        ("卷", ["饼皮", "蔬菜", "蛋白食材", "酱汁"]),
        ("贝果", ["贝果", "鸡蛋", "生菜", "奶酪"]),
        ("拿铁", ["咖啡豆", "牛奶", "燕麦奶"]),
        ("美式", ["咖啡豆", "饮用水"]),
        ("冷萃", ["冷萃咖啡液", "饮用水", "柑橘片"]),
        ("蛋糕", ["奶油奶酪", "鸡蛋", "低筋面粉", "黄油"]),
        ("曲奇", ["黄油", "低筋面粉", "巧克力", "鸡蛋"]),
        ("可颂", ["高筋面粉", "黄油", "酵母", "牛奶"]),
        ("披萨", ["披萨饼底", "芝士", "番茄酱", "配料"]),
        ("意面", ["意面", "橄榄油", "番茄或奶油酱", "香草"]),
        ("焗饭", ["米饭", "芝士", "酱汁", "主菜配料"]),
        ("焗面", ["意面", "芝士", "番茄酱", "肉丸"]),
        ("汉堡", ["汉堡胚", "肉饼", "生菜", "芝士"]),
        ("薯", ["土豆", "海盐", "黑胡椒"]),
        ("炸", ["主料", "面糊", "面包糠", "调味粉"]),
        ("麻辣烫", ["汤底", "蔬菜", "丸类", "豆制品"]),
        ("冒菜", ["辣汤底", "肉类", "蔬菜", "豆制品"]),
        ("豆浆", ["黄豆", "饮用水"]),
        ("酸奶", ["酸奶", "水果", "坚果"]),
        ("果昔", ["水果", "酸奶", "冰块"]),
        ("气泡", ["苏打水", "果汁", "糖浆"]),
        ("冰粉", ["冰粉粉", "红糖浆", "山楂碎", "葡萄干"]),
        ("米饭", ["大米"]),
    ]
    for keyword, ingredients in ingredient_rules:
        if keyword in text:
            return ingredients

    if cuisine_type in {"咖啡", "饮品"}:
        return ["饮用水", "风味原料"]
    if cuisine_type in {"甜点", "烘焙"}:
        return ["面粉", "黄油", "鸡蛋", "糖"]
    return ["主料", "蔬菜", "调味料"]



def _infer_allergens(ingredients: list[str], name: str, tags: str, cuisine_type: str) -> list[str]:
    text = ",".join(ingredients) + f",{name},{tags},{cuisine_type}"
    allergens: list[str] = []
    rules = [
        (["花生"], "花生"),
        (["牛奶", "芝士", "黄油", "奶油", "酸奶", "奶酪"], "牛奶"),
        (["鸡蛋", "蛋"], "鸡蛋"),
        (["黄豆", "豆腐", "豆皮", "香干", "豆浆", "豆制品"], "大豆"),
        (["虾", "虾滑", "甲壳"], "甲壳类"),
        (["鳗鱼", "三文鱼", "鱼肉", "海鲜", "鳕鱼"], "鱼类"),
        (["面", "面粉", "披萨", "意面", "贝果", "可颂", "曲奇", "汉堡胚", "面包糠", "吐司", "饼皮", "云吞皮"], "麸质"),
        (["坚果", "榛子"], "坚果"),
    ]
    for keywords, allergen in rules:
        if any(keyword in text for keyword in keywords):
            allergens.append(allergen)
    return _unique(allergens)



def _infer_cooking_method(name: str, description: str, tags: str) -> str:
    text = f"{name},{description},{tags}"
    rules = [
        (["焗"], "焗烤"),
        (["披萨", "可颂", "曲奇", "挞", "蛋糕", "肉桂卷", "面包"], "烘烤"),
        (["炸", "鸡翅", "鸡柳", "热狗", "薯", "猪排", "唐扬", "可乐饼", "洋葱圈", "鸡米花"], "油炸"),
        (["拿铁", "美式", "冷萃", "手冲"], "萃取"),
        (["沙拉", "寿司", "果昔", "气泡饮", "奶茶"], "冷制"),
        (["粥", "汤", "云吞", "馄饨", "麻辣烫", "冒菜", "锅底"], "炖煮"),
        (["炒", "锅", "丼"], "爆炒"),
        (["照烧", "香煎", "玉子烧", "鸡排"], "煎制"),
    ]
    for keywords, method in rules:
        if any(keyword in text for keyword in keywords):
            return method
    return "现制"



def _ensure_specific_description(
    name: str,
    description: str,
    ingredients: list[str],
    flavor_profile: str,
    cooking_method: str,
) -> str:
    handwritten_description = HANDWRITTEN_DISH_DESCRIPTIONS.get(name)
    if handwritten_description:
        return handwritten_description

    base = description.strip()
    if len(base) >= 20 and not ("以" in base and "呈现" in base):
        return base

    ingredient_text = "、".join(ingredients[:2])
    templates = {
        "爆炒": f"{base}，{ingredient_text}现炒出锅，整体{flavor_profile}，配米饭点单会更过瘾。",
        "炖煮": f"{base}，{ingredient_text}慢火{cooking_method}入味，口感{flavor_profile}，当作正餐很稳妥。",
        "油炸": f"{base}，{ingredient_text}炸到外酥里嫩，趁热吃更香，做加餐或夜宵都合适。",
        "冷制": f"{base}，{ingredient_text}现拌现做，整体{flavor_profile}，清爽不腻也更适合工作日午餐。",
        "烘烤": f"{base}，{ingredient_text}现烤出炉，入口{flavor_profile}，热乎的时候风味更完整。",
        "焗烤": f"{base}，{ingredient_text}焗到香气更足，整体{flavor_profile}，适合想吃浓郁口味的时候点。",
        "煎制": f"{base}，{ingredient_text}煎到表面微脆，内部保留汁水，吃起来是{flavor_profile}的路子。",
        "萃取": f"{base}，选用{ingredient_text}现萃制作，整体{flavor_profile}，适合通勤提神或下午续命。",
        "现制": f"{base}，{ingredient_text}现点现做，整体{flavor_profile}，吃起来更有一份刚出品的满足感。",
    }
    return templates.get(
        cooking_method,
        f"{base}，{ingredient_text}{cooking_method}处理后更显层次，整体{flavor_profile}，点来当一餐也很合适。",
    )



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
        else:
            cuisine_type, flavor_profile, ingredients, allergens, cooking_method = args[:5]
            if len(args) > 5:
                is_recommended = bool(args[5])

    resolved_cuisine_type = cuisine_type or _infer_cuisine_type(name, tags)
    resolved_flavor_profile = flavor_profile or _infer_flavor_profile(name, description, tags)
    resolved_ingredients = list(ingredients) if ingredients is not None else _infer_ingredients(name, description, tags, resolved_cuisine_type)
    resolved_allergens = list(allergens) if allergens is not None else _infer_allergens(resolved_ingredients, name, tags, resolved_cuisine_type)
    resolved_cooking_method = cooking_method or _infer_cooking_method(name, description, tags)
    resolved_description = _ensure_specific_description(
        name,
        description,
        resolved_ingredients,
        resolved_flavor_profile,
        resolved_cooking_method,
    )

    return {
        "name": name,
        "description": resolved_description,
        "price": price,
        "tags": tags,
        "cuisine_type": resolved_cuisine_type,
        "flavor_profile": resolved_flavor_profile,
        "ingredients": resolved_ingredients,
        "allergens": resolved_allergens,
        "cooking_method": resolved_cooking_method,
        "is_recommended": is_recommended,
    }



def section(name: str, dishes: list[dict]) -> dict:
    return {"name": name, "dishes": dishes}



def clone_categories(categories: list[dict]) -> list[dict]:
    return deepcopy(categories)



def _build_phone(name: str) -> str:
    return f"021-{62000000 + _stable_number(name) % 3000000:08d}"



def _build_business_hours(name: str, homepage_category: str) -> str:
    options = CATEGORY_BUSINESS_HOURS[homepage_category]
    return options[_stable_number(name) % len(options)]



def _build_detailed_address(name: str, district: str) -> str:
    base_address = DISTRICT_POINTS[district]["address"].replace(" ", "")
    code = _stable_number(name)
    building = BUILDING_SUFFIXES[code % len(BUILDING_SUFFIXES)]
    floor = code % 3 + 1
    room = 100 + code % 120
    return f"{base_address}{building}{floor}层{room}室"



def _build_address_note(name: str, district: str) -> str:
    entry = code = _stable_number(name) % 4 + 1
    return f"近{DISTRICT_LANDMARKS[district]}{entry}号取餐点"



def _build_merchant_tags(homepage_category: str, description: str, promo_text: str, avg_delivery_minutes: int) -> list[str]:
    tags = list(CATEGORY_TAGS[homepage_category])
    if "下午茶" in description:
        tags.append("下午茶")
    if "夜宵" in description or avg_delivery_minutes >= 35:
        tags.append("夜宵友好")
    if "工作日" in description or avg_delivery_minutes <= 28:
        tags.append("午餐快送")
    if "双人" in promo_text or "套餐" in promo_text:
        tags.append("套餐点单")
    return _unique(tags)[:3]



def _apply_homepage_category_copy_style(categories: list[dict], homepage_category: str) -> list[dict]:
    if homepage_category not in {"湘菜", "轻食", "咖啡甜品"}:
        return categories

    for category in categories:
        for dish in category["dishes"]:
            if dish["name"] in HANDWRITTEN_DISH_DESCRIPTIONS:
                continue

            base = dish["description"].strip()
            ingredients = "、".join(dish["ingredients"][:2])

            if homepage_category == "湘菜":
                if any(keyword in base for keyword in ["下饭", "现炒", "锅气"]):
                    continue
                if dish["cooking_method"] == "爆炒":
                    dish["description"] = f"{base}，{ingredients}现炒出锅更有锅气，咸香里带着{dish['flavor_profile']}，拌饭吃特别下饭。"
                else:
                    dish["description"] = f"{base}，{ingredients}做得很入味，热乎上桌更显香辣，点来配饭尤其下饭。"
                continue

            if homepage_category == "轻食":
                if any(keyword in base for keyword in ["清爽", "轻负担", "低负担"]):
                    continue
                if dish["cooking_method"] in {"冷制", "萃取"} or dish["cuisine_type"] in {"咖啡", "饮品"}:
                    dish["description"] = f"{base}，{ingredients}做得清爽顺口，整体轻负担，搭配卷碗或单点都不会腻。"
                else:
                    dish["description"] = f"{base}，{ingredients}搭配得更清爽，吃完有饱腹感但不厚重，工作日点一份也很轻负担。"
                continue

            if any(keyword in base for keyword in ["口感", "香气", "奶香"]):
                continue
            if dish["cooking_method"] == "萃取" or dish["cuisine_type"] in {"咖啡", "饮品"}:
                dish["description"] = f"{base}，入口先有{dish['flavor_profile']}的层次，随后香气慢慢出来，做下午茶饮品很合适。"
            else:
                dish["description"] = f"{base}，整体口感更细腻，入口能吃到明显香气，拿来配咖啡或做下午茶都很合适。"

    return categories



def build_merchant_seed(
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
    longitude_offset: float,
    latitude_offset: float,
    categories: list[dict],
    phone: str = "",
    business_hours: str = "",
    detailed_address: str = "",
    address_note: str = "",
    merchant_tags: list[str] | None = None,
) -> dict:
    district_meta = DISTRICT_POINTS[district]
    normalized_categories = _apply_homepage_category_copy_style(clone_categories(categories), homepage_category)
    return {
        "name": name,
        "description": description,
        "city": "上海",
        "district": district,
        "address": district_meta["address"],
        "longitude": district_meta["longitude"] + longitude_offset,
        "latitude": district_meta["latitude"] + latitude_offset,
        "homepage_category": homepage_category,
        "promo_text": promo_text,
        "delivery_radius_meters": delivery_radius_meters,
        "delivery_fee": delivery_fee,
        "min_order_amount": min_order_amount,
        "avg_delivery_minutes": avg_delivery_minutes,
        "rating": rating,
        "phone": phone or _build_phone(name),
        "business_hours": business_hours or _build_business_hours(name, homepage_category),
        "detailed_address": detailed_address or _build_detailed_address(name, district),
        "address_note": address_note or _build_address_note(name, district),
        "merchant_tags": list(merchant_tags) if merchant_tags is not None else _build_merchant_tags(homepage_category, description, promo_text, avg_delivery_minutes),
        "categories": normalized_categories,
    }


XIANGCAI_HOME_STYLE = [
    section(
        "现炒小碗菜",
        [
            dish("辣椒炒肉", "鲜辣下饭", 29.0, "湘菜,热卖", True),
            dish("攸县香干炒肉", "豆香浓郁", 31.0, "湘菜,家常"),
            dish("外婆菜炒鸡蛋", "咸鲜开胃", 24.0, "下饭"),
            dish("小炒黄牛肉", "锅气足", 42.0, "招牌", True),
        ],
    ),
    section(
        "配饭小吃",
        [
            dish("红糖糍粑", "外脆内糯", 12.0, "甜口"),
            dish("酸梅汤", "解辣清爽", 8.0, "饮品"),
            dish("米饭", "现煮香米", 2.0, "主食"),
            dish("擂椒皮蛋", "香辣软嫩", 16.0, "凉菜"),
        ],
    ),
]

XIANGCAI_CLAYPOT = [
    section(
        "砂锅下饭菜",
        [
            dish("砂锅豆腐", "热乎入味", 26.0, "砂锅"),
            dish("干锅肥肠", "香辣浓郁", 46.0, "干锅,招牌", True),
            dish("农家一碗香", "蛋香肉香", 33.0, "湘菜", True),
            dish("剁椒鱼块", "鲜辣开胃", 38.0, "剁椒"),
        ],
    ),
    section(
        "热卤配菜",
        [
            dish("卤香海带结", "微辣入味", 9.0, "配菜"),
            dish("酸豆角肉沫", "酸香搭饭", 14.0, "小炒"),
            dish("老长沙冰粉", "爽口收尾", 10.0, "甜品"),
            dish("米饭", "热米饭", 2.0, "主食"),
        ],
    ),
]

LIGHT_MEAL_FITNESS = [
    section(
        "高蛋白能量碗",
        [
            dish("香煎鸡胸藜麦碗", "清爽饱腹", 33.0, "轻食,高蛋白", True),
            dish("牛肉南瓜能量碗", "低负担饱腹", 37.0, "轻食", True),
            dish("椒香鸡腿温沙拉", "热食更满足", 35.0, "沙拉"),
            dish("豆腐鹰嘴豆碗", "植物蛋白", 28.0, "素食"),
        ],
    ),
    section(
        "轻饮加餐",
        [
            dish("冷萃美式", "无糖提神", 14.0, "咖啡"),
            dish("希腊酸奶杯", "水果坚果搭配", 16.0, "酸奶"),
            dish("羽衣甘蓝果昔", "清爽顺口", 18.0, "饮品"),
            dish("牛油果鲜虾卷", "轻盈不寡淡", 26.0, "卷饼", True),
        ],
    ),
]

LIGHT_MEAL_BRUNCH = [
    section(
        "早午餐卷碗",
        [
            dish("嫩炒蛋贝果盒", "适合早午餐", 24.0, "早午餐"),
            dish("香草鸡肉卷", "口感清爽", 29.0, "卷饼,轻食", True),
            dish("烟熏三文鱼牛油果碗", "层次丰富", 39.0, "轻食,海鲜", True),
            dish("烤南瓜藜麦沙拉", "微甜饱腹", 27.0, "素食"),
        ],
    ),
    section(
        "鲜榨轻饮",
        [
            dish("西柚气泡冷萃", "果香提神", 17.0, "饮品,咖啡"),
            dish("草莓酸奶昔", "柔滑轻甜", 18.0, "饮品"),
            dish("牛油果酸种吐司", "香脆有嚼劲", 22.0, "加餐"),
            dish("烤菇温沙拉", "菌香浓郁", 25.0, "沙拉"),
        ],
    ),
]

COFFEE_BAKEHOUSE = [
    section(
        "手作咖啡",
        [
            dish("燕麦拿铁", "奶香平衡", 21.0, "咖啡,招牌", True),
            dish("手冲美式", "清爽明亮", 17.0, "咖啡"),
            dish("橙香冷萃", "果酸轻盈", 19.0, "咖啡"),
            dish("可可摩卡", "巧香浓郁", 24.0, "咖啡,甜感"),
        ],
    ),
    section(
        "烘焙柜台",
        [
            dish("黄油可颂", "层层酥香", 12.0, "烘焙"),
            dish("肉桂卷", "甜香柔软", 15.0, "烘焙"),
            dish("榛子巧克力曲奇", "可可风味足", 13.0, "甜点"),
            dish("香草布丁挞", "奶香细腻", 16.0, "甜点", True),
        ],
    ),
]

COFFEE_DESSERT = [
    section(
        "甜点主场",
        [
            dish("巴斯克芝士蛋糕", "焦香浓郁", 28.0, "甜点,招牌", True),
            dish("提拉米苏杯", "绵密微苦", 26.0, "甜点", True),
            dish("抹茶流心卷", "茶香柔和", 24.0, "甜点"),
            dish("香草千层切件", "层次分明", 27.0, "甜点"),
        ],
    ),
    section(
        "下午茶饮",
        [
            dish("生椰拿铁", "椰香顺滑", 23.0, "咖啡"),
            dish("桂花乌龙奶茶", "茶香清甜", 18.0, "饮品"),
            dish("莓果气泡饮", "酸甜解腻", 16.0, "饮品"),
            dish("阿华田冰沙", "童年风味", 20.0, "饮品"),
        ],
    ),
]

BURGER_COMBO = [
    section(
        "招牌堡套餐",
        [
            dish("厚切牛肉堡", "肉香扎实", 31.0, "汉堡,招牌", True),
            dish("香辣鸡腿堡", "外脆里嫩", 28.0, "汉堡,辣", True),
            dish("蘑菇芝士堡", "菌香浓郁", 32.0, "汉堡"),
            dish("鳕鱼塔塔堡", "清爽不腻", 29.0, "汉堡,海鲜"),
        ],
    ),
    section(
        "薯角小食",
        [
            dish("粗薯角", "外脆内软", 13.0, "小食"),
            dish("洋葱圈", "适合分享", 14.0, "小食"),
            dish("鸡米花", "撒粉更香", 16.0, "炸物"),
            dish("可乐", "冰镇搭配", 8.0, "饮品"),
        ],
    ),
]

FRIED_SHARING = [
    section(
        "炸鸡拼盘",
        [
            dish("原味炸鸡块", "肉汁充足", 26.0, "炸鸡,热卖", True),
            dish("甜辣鸡翅", "韩式风味", 24.0, "炸鸡,辣", True),
            dish("蒜香鸡柳", "蒜香明显", 22.0, "炸物"),
            dish("芝士热狗棒", "拉丝浓郁", 18.0, "小食"),
        ],
    ),
    section(
        "分享加点",
        [
            dish("蜂蜜黄油薯条", "甜咸平衡", 15.0, "薯条"),
            dish("酸黄瓜沙拉", "解腻爽口", 12.0, "沙拉"),
            dish("冰柠茶", "清爽解炸", 10.0, "饮品"),
            dish("奶香玉米杯", "顺口饱腹", 11.0, "小食"),
        ],
    ),
]

CONGEE_BREAKFAST = [
    section(
        "暖胃粥品",
        [
            dish("皮蛋瘦肉粥", "顺滑暖胃", 14.0, "粥,招牌", True),
            dish("香菇滑鸡粥", "咸鲜柔和", 16.0, "粥"),
            dish("南瓜小米粥", "清甜细腻", 12.0, "粥"),
            dish("艇仔粥", "配料丰富", 18.0, "粥", True),
        ],
    ),
    section(
        "早点搭配",
        [
            dish("生煎包", "底脆汁多", 12.0, "点心", True),
            dish("茶叶蛋", "咸香入味", 3.0, "早点"),
            dish("豆浆", "现磨醇香", 5.0, "饮品"),
            dish("小笼包", "汤汁鲜美", 14.0, "点心"),
        ],
    ),
]

NOODLE_LATE_NIGHT = [
    section(
        "汤面馄饨",
        [
            dish("鲜虾云吞面", "汤头鲜甜", 22.0, "面,云吞", True),
            dish("雪菜肉丝面", "家常咸鲜", 18.0, "面"),
            dish("葱油拌面", "葱香浓郁", 16.0, "面"),
            dish("鲜肉小馄饨", "皮薄汤鲜", 15.0, "馄饨", True),
        ],
    ),
    section(
        "夜宵小碟",
        [
            dish("卤豆干", "咸香耐嚼", 8.0, "小菜"),
            dish("酸豆角", "开胃搭面", 4.0, "小菜"),
            dish("辣肉酱", "拌面更香", 6.0, "浇头"),
            dish("冰豆奶", "顺口解腻", 7.0, "饮品"),
        ],
    ),
]

JP_DONBURI_SUSHI = [
    section(
        "盖饭寿司",
        [
            dish("照烧鸡排饭", "咸甜平衡", 29.0, "盖饭", True),
            dish("鳗鱼饭", "酱香浓郁", 43.0, "日料,招牌", True),
            dish("三文鱼寿司拼盘", "鱼脂细腻", 38.0, "寿司"),
            dish("牛肉丼", "洋葱甜润", 31.0, "盖饭"),
        ],
    ),
    section(
        "清爽副菜",
        [
            dish("味噌汤", "暖胃清淡", 8.0, "汤品"),
            dish("海藻沙拉", "酸甜爽口", 12.0, "小食"),
            dish("毛豆", "轻松佐餐", 10.0, "小食"),
            dish("玉子烧", "蛋香柔软", 13.0, "配菜"),
        ],
    ),
]

JP_CURRY_SNACK = [
    section(
        "咖喱定食",
        [
            dish("咖喱猪排饭", "香浓顺滑", 32.0, "咖喱,招牌", True),
            dish("滑蛋牛肉咖喱", "蛋香浓郁", 30.0, "咖喱"),
            dish("唐扬鸡块饭", "外脆内嫩", 29.0, "炸物"),
            dish("炸虾蛋包饭", "酸甜柔和", 34.0, "蛋包饭", True),
        ],
    ),
    section(
        "日式小点",
        [
            dish("章鱼小丸子", "酱香弹嫩", 16.0, "小吃", True),
            dish("抹茶布丁", "回甘轻苦", 14.0, "甜品"),
            dish("可乐饼", "土豆绵密", 12.0, "小食"),
            dish("玄米茶", "清香解腻", 9.0, "饮品"),
        ],
    ),
]

MALATANG_SOUP = [
    section(
        "招牌锅底",
        [
            dish("骨汤麻辣烫", "汤底浓郁", 26.0, "麻辣烫,招牌", True),
            dish("番茄麻辣烫", "酸甜开胃", 24.0, "番茄", True),
            dish("藤椒麻辣烫", "清麻回香", 27.0, "藤椒"),
            dish("菌汤麻辣烫", "鲜香柔和", 25.0, "菌汤"),
        ],
    ),
    section(
        "加料台",
        [
            dish("肥牛", "肉香十足", 12.0, "加料", True),
            dish("虾滑", "弹嫩鲜香", 14.0, "加料", True),
            dish("宽粉", "爽滑弹牙", 7.0, "加料"),
            dish("豆皮", "吸汁入味", 6.0, "加料"),
        ],
    ),
]

MALATANG_MIX = [
    section(
        "麻辣拌冒菜",
        [
            dish("经典冒菜", "香辣够味", 28.0, "冒菜,招牌", True),
            dish("藤椒冒菜", "麻香上头", 29.0, "冒菜"),
            dish("微辣麻辣拌", "干拌更香", 25.0, "麻辣拌", True),
            dish("蒜香麻辣拌", "蒜香突出", 26.0, "麻辣拌"),
        ],
    ),
    section(
        "人气配菜",
        [
            dish("蟹柳", "经典搭配", 8.0, "加料"),
            dish("鸭血", "爽滑入味", 9.0, "加料"),
            dish("土豆片", "面糯吸汁", 6.0, "加料"),
            dish("响铃卷", "口感酥脆", 10.0, "加料"),
        ],
    ),
]

PIZZA_PASTA = [
    section(
        "披萨意面",
        [
            dish("玛格丽特披萨", "番茄芝士经典", 42.0, "披萨,经典", True),
            dish("榴莲披萨", "芝士拉丝", 56.0, "披萨,热卖", True),
            dish("奶油培根意面", "浓郁顺滑", 29.0, "意面"),
            dish("番茄肉酱意面", "酸香开胃", 27.0, "意面"),
        ],
    ),
    section(
        "烘烤小食",
        [
            dish("蒜香面包", "烘烤香脆", 10.0, "小食"),
            dish("凯撒沙拉", "清爽解腻", 18.0, "沙拉"),
            dish("柠檬气泡饮", "清新佐餐", 12.0, "饮品"),
            dish("鸡翅拼盘", "外皮焦香", 22.0, "小食"),
        ],
    ),
]

BAKED_RICE_SNACK = [
    section(
        "焗饭主食",
        [
            dish("芝士鸡排焗饭", "奶香浓郁", 29.0, "焗饭,招牌", True),
            dish("海鲜焗饭", "料足味鲜", 33.0, "焗饭", True),
            dish("番茄肉丸焗面", "酸香开胃", 31.0, "焗面"),
            dish("蘑菇白酱焗饭", "奶香柔和", 28.0, "焗饭"),
        ],
    ),
    section(
        "餐前小点",
        [
            dish("黑椒薯角", "热乎酥香", 13.0, "小食"),
            dish("芝士玉米杯", "奶香甜口", 14.0, "小食"),
            dish("桃桃苏打", "果香清爽", 15.0, "饮品"),
            dish("罗勒番茄沙拉", "酸甜平衡", 16.0, "沙拉"),
        ],
    ),
]


MERCHANT_SEED_DATA = [
    build_merchant_seed(name="兰姨小炒", description="主打现炒湘味下饭菜，适合工作日午晚餐", district="静安", homepage_category="湘菜", promo_text="双人下饭套餐立减10元", delivery_radius_meters=3200, delivery_fee=4.0, min_order_amount=20.0, avg_delivery_minutes=28, rating=4.7, longitude_offset=0.0011, latitude_offset=0.0010, categories=XIANGCAI_HOME_STYLE),
    build_merchant_seed(name="洞庭食堂", description="偏重砂锅和剁椒热菜，晚餐订单更集中", district="徐汇", homepage_category="湘菜", promo_text="招牌热菜第二件半价", delivery_radius_meters=3300, delivery_fee=4.0, min_order_amount=22.0, avg_delivery_minutes=31, rating=4.6, longitude_offset=0.0015, latitude_offset=0.0012, categories=XIANGCAI_CLAYPOT),
    build_merchant_seed(name="下饭湘厨", description="小炒和配饭组合更受白领欢迎", district="浦东", homepage_category="湘菜", promo_text="工作日午餐满减8元", delivery_radius_meters=3100, delivery_fee=4.5, min_order_amount=21.0, avg_delivery_minutes=30, rating=4.5, longitude_offset=0.0018, latitude_offset=0.0013, categories=XIANGCAI_HOME_STYLE),
    build_merchant_seed(name="火宫辣子馆", description="偏辣口热菜和砂锅菜卖得更好", district="杨浦", homepage_category="湘菜", promo_text="辣味招牌套餐限时88折", delivery_radius_meters=3400, delivery_fee=5.0, min_order_amount=24.0, avg_delivery_minutes=33, rating=4.6, longitude_offset=0.0013, latitude_offset=0.0017, categories=XIANGCAI_CLAYPOT),
    build_merchant_seed(name="家味湘菜饭堂", description="家常湘味和米饭快餐都很稳定", district="长宁", homepage_category="湘菜", promo_text="晚餐双拼套餐减12元", delivery_radius_meters=3000, delivery_fee=4.0, min_order_amount=20.0, avg_delivery_minutes=29, rating=4.7, longitude_offset=0.0016, latitude_offset=0.0011, categories=XIANGCAI_HOME_STYLE),
    build_merchant_seed(name="谷粒厨房", description="高蛋白轻食工作餐，主打热食能量碗", district="静安", homepage_category="轻食", promo_text="午间轻食套餐减8元", delivery_radius_meters=2800, delivery_fee=5.0, min_order_amount=26.0, avg_delivery_minutes=29, rating=4.7, longitude_offset=0.0021, latitude_offset=0.0010, categories=LIGHT_MEAL_FITNESS),
    build_merchant_seed(name="半勺轻食", description="早午餐卷饼和轻碗更适合通勤用户", district="徐汇", homepage_category="轻食", promo_text="双人卷饼套餐立减9元", delivery_radius_meters=2700, delivery_fee=5.0, min_order_amount=24.0, avg_delivery_minutes=27, rating=4.6, longitude_offset=0.0024, latitude_offset=0.0011, categories=LIGHT_MEAL_BRUNCH),
    build_merchant_seed(name="日日鲜配", description="每日现配沙拉和蛋白碗，偏清爽口味", district="浦东", homepage_category="轻食", promo_text="满39元赠鲜榨饮品", delivery_radius_meters=2900, delivery_fee=5.5, min_order_amount=25.0, avg_delivery_minutes=31, rating=4.5, longitude_offset=0.0022, latitude_offset=0.0015, categories=LIGHT_MEAL_FITNESS),
    build_merchant_seed(name="森活能量碗", description="植物蛋白和果昔选择更丰富", district="杨浦", homepage_category="轻食", promo_text="轻断食套餐立减7元", delivery_radius_meters=2750, delivery_fee=5.0, min_order_amount=23.0, avg_delivery_minutes=30, rating=4.6, longitude_offset=0.0025, latitude_offset=0.0016, categories=LIGHT_MEAL_BRUNCH),
    build_merchant_seed(name="晴天卷饼社", description="主打卷饼加轻饮，适合下午茶和简餐", district="长宁", homepage_category="轻食", promo_text="卷饼加饮品组合88折", delivery_radius_meters=2600, delivery_fee=4.5, min_order_amount=22.0, avg_delivery_minutes=26, rating=4.4, longitude_offset=0.0023, latitude_offset=0.0012, categories=LIGHT_MEAL_BRUNCH),
    build_merchant_seed(name="午后豆房", description="偏手冲和可颂的社区咖啡店", district="静安", homepage_category="咖啡甜品", promo_text="咖啡加烘焙立减6元", delivery_radius_meters=2500, delivery_fee=3.0, min_order_amount=18.0, avg_delivery_minutes=24, rating=4.8, longitude_offset=0.0031, latitude_offset=0.0010, categories=COFFEE_BAKEHOUSE),
    build_merchant_seed(name="奶油信箱", description="甜点选择更多，适合下午茶拼单", district="徐汇", homepage_category="咖啡甜品", promo_text="甜点双拼限时79折", delivery_radius_meters=2400, delivery_fee=3.0, min_order_amount=20.0, avg_delivery_minutes=25, rating=4.7, longitude_offset=0.0035, latitude_offset=0.0012, categories=COFFEE_DESSERT),
    build_merchant_seed(name="可可角落", description="摩卡和小蛋糕销量一直稳定", district="浦东", homepage_category="咖啡甜品", promo_text="第二杯咖啡半价", delivery_radius_meters=2600, delivery_fee=3.5, min_order_amount=19.0, avg_delivery_minutes=23, rating=4.6, longitude_offset=0.0032, latitude_offset=0.0014, categories=COFFEE_BAKEHOUSE),
    build_merchant_seed(name="慢烘实验室", description="偏精品咖啡和手作烘焙，味型更克制", district="杨浦", homepage_category="咖啡甜品", promo_text="手冲系列满减5元", delivery_radius_meters=2450, delivery_fee=3.0, min_order_amount=18.0, avg_delivery_minutes=24, rating=4.8, longitude_offset=0.0036, latitude_offset=0.0016, categories=COFFEE_BAKEHOUSE),
    build_merchant_seed(name="甜屿茶点", description="甜点和茶饮搭配更偏下午茶路线", district="长宁", homepage_category="咖啡甜品", promo_text="下午茶双人组合减10元", delivery_radius_meters=2550, delivery_fee=3.5, min_order_amount=20.0, avg_delivery_minutes=26, rating=4.7, longitude_offset=0.0033, latitude_offset=0.0012, categories=COFFEE_DESSERT),
    build_merchant_seed(name="厚牛堡局", description="厚切牛肉堡和薯角是主打组合", district="静安", homepage_category="炸鸡汉堡", promo_text="单人堡餐立减7元", delivery_radius_meters=3000, delivery_fee=6.0, min_order_amount=29.0, avg_delivery_minutes=34, rating=4.6, longitude_offset=0.0041, latitude_offset=0.0010, categories=BURGER_COMBO),
    build_merchant_seed(name="脆脆鸡食堂", description="炸鸡拼盘更适合夜宵和多人分享", district="徐汇", homepage_category="炸鸡汉堡", promo_text="炸鸡双拼第二份半价", delivery_radius_meters=3100, delivery_fee=6.0, min_order_amount=28.0, avg_delivery_minutes=35, rating=4.5, longitude_offset=0.0045, latitude_offset=0.0012, categories=FRIED_SHARING),
    build_merchant_seed(name="街角汉堡铺", description="偏美式快餐组合，午餐出单快", district="浦东", homepage_category="炸鸡汉堡", promo_text="午间汉堡套餐赠饮", delivery_radius_meters=2950, delivery_fee=5.5, min_order_amount=27.0, avg_delivery_minutes=33, rating=4.4, longitude_offset=0.0042, latitude_offset=0.0014, categories=BURGER_COMBO),
    build_merchant_seed(name="热浪炸物社", description="炸物分享盘更适合聚会和夜宵", district="杨浦", homepage_category="炸鸡汉堡", promo_text="分享拼盘限时88折", delivery_radius_meters=3050, delivery_fee=6.0, min_order_amount=30.0, avg_delivery_minutes=36, rating=4.5, longitude_offset=0.0046, latitude_offset=0.0017, categories=FRIED_SHARING),
    build_merchant_seed(name="双层芝士屋", description="偏芝士和牛肉风味，适合重口用户", district="长宁", homepage_category="炸鸡汉堡", promo_text="芝士堡升级套餐减6元", delivery_radius_meters=3000, delivery_fee=6.5, min_order_amount=29.0, avg_delivery_minutes=34, rating=4.6, longitude_offset=0.0043, latitude_offset=0.0011, categories=BURGER_COMBO),
    build_merchant_seed(name="阿福粥铺", description="早餐粥品和生煎搭配最受欢迎", district="静安", homepage_category="粥面", promo_text="早点套餐满25减6", delivery_radius_meters=2600, delivery_fee=4.0, min_order_amount=18.0, avg_delivery_minutes=25, rating=4.5, longitude_offset=0.0051, latitude_offset=0.0010, categories=CONGEE_BREAKFAST),
    build_merchant_seed(name="深夜汤面", description="主打夜宵汤面和小馄饨，晚间订单更多", district="徐汇", homepage_category="粥面", promo_text="夜宵时段加料不加价", delivery_radius_meters=2700, delivery_fee=4.0, min_order_amount=19.0, avg_delivery_minutes=27, rating=4.6, longitude_offset=0.0055, latitude_offset=0.0012, categories=NOODLE_LATE_NIGHT),
    build_merchant_seed(name="巷口面档", description="家常拌面和小菜更偏社区口味", district="浦东", homepage_category="粥面", promo_text="拌面套餐减5元", delivery_radius_meters=2500, delivery_fee=4.0, min_order_amount=18.0, avg_delivery_minutes=26, rating=4.4, longitude_offset=0.0052, latitude_offset=0.0015, categories=NOODLE_LATE_NIGHT),
    build_merchant_seed(name="暖胃小馆", description="偏暖胃粥品和早点组合，适合清淡早餐", district="杨浦", homepage_category="粥面", promo_text="暖胃早餐组合88折", delivery_radius_meters=2550, delivery_fee=3.5, min_order_amount=17.0, avg_delivery_minutes=24, rating=4.5, longitude_offset=0.0056, latitude_offset=0.0016, categories=CONGEE_BREAKFAST),
    build_merchant_seed(name="云吞早点铺", description="云吞和早点出品稳定，适合通勤人群", district="长宁", homepage_category="粥面", promo_text="早点满20元送豆浆", delivery_radius_meters=2450, delivery_fee=3.5, min_order_amount=16.0, avg_delivery_minutes=23, rating=4.4, longitude_offset=0.0053, latitude_offset=0.0011, categories=NOODLE_LATE_NIGHT),
    build_merchant_seed(name="元气食堂", description="鳗鱼饭和照烧鸡排饭是点单主力", district="静安", homepage_category="日韩料理", promo_text="定食双人组合减12元", delivery_radius_meters=3000, delivery_fee=5.0, min_order_amount=35.0, avg_delivery_minutes=32, rating=4.7, longitude_offset=0.0061, latitude_offset=0.0010, categories=JP_DONBURI_SUSHI),
    build_merchant_seed(name="海苔饭屋", description="寿司和副菜搭配更适合轻量正餐", district="徐汇", homepage_category="日韩料理", promo_text="寿司拼盘立减9元", delivery_radius_meters=2900, delivery_fee=5.0, min_order_amount=33.0, avg_delivery_minutes=31, rating=4.6, longitude_offset=0.0065, latitude_offset=0.0012, categories=JP_DONBURI_SUSHI),
    build_merchant_seed(name="照烧小厨", description="照烧和咖喱主食更贴近日常便当路线", district="浦东", homepage_category="日韩料理", promo_text="工作日定食套餐减8元", delivery_radius_meters=2950, delivery_fee=5.0, min_order_amount=32.0, avg_delivery_minutes=33, rating=4.5, longitude_offset=0.0062, latitude_offset=0.0014, categories=JP_CURRY_SNACK),
    build_merchant_seed(name="抹茶町", description="小吃和抹茶甜点更适合下午茶加餐", district="杨浦", homepage_category="日韩料理", promo_text="抹茶甜品加购半价", delivery_radius_meters=2800, delivery_fee=4.5, min_order_amount=30.0, avg_delivery_minutes=30, rating=4.6, longitude_offset=0.0066, latitude_offset=0.0016, categories=JP_CURRY_SNACK),
    build_merchant_seed(name="日和定食屋", description="定食与汤品搭配完整，晚餐评价稳定", district="长宁", homepage_category="日韩料理", promo_text="晚餐定食赠味噌汤", delivery_radius_meters=3000, delivery_fee=5.0, min_order_amount=34.0, avg_delivery_minutes=32, rating=4.7, longitude_offset=0.0063, latitude_offset=0.0011, categories=JP_DONBURI_SUSHI),
    build_merchant_seed(name="川辣冒香锅", description="偏骨汤锅底和经典配料，适合大众口味", district="静安", homepage_category="麻辣烫", promo_text="满39元送宽粉一份", delivery_radius_meters=3200, delivery_fee=4.0, min_order_amount=22.0, avg_delivery_minutes=29, rating=4.5, longitude_offset=0.0071, latitude_offset=0.0010, categories=MALATANG_SOUP),
    build_merchant_seed(name="椒椒麻辣烫", description="番茄和藤椒锅底点单更高，汤底选择多", district="徐汇", homepage_category="麻辣烫", promo_text="双人锅底套餐减10元", delivery_radius_meters=3150, delivery_fee=4.0, min_order_amount=23.0, avg_delivery_minutes=30, rating=4.4, longitude_offset=0.0075, latitude_offset=0.0012, categories=MALATANG_SOUP),
    build_merchant_seed(name="骨汤烫铺", description="骨汤和菌汤锅底更偏清爽路线", district="浦东", homepage_category="麻辣烫", promo_text="清汤系列第二份半价", delivery_radius_meters=3100, delivery_fee=4.5, min_order_amount=22.0, avg_delivery_minutes=31, rating=4.5, longitude_offset=0.0072, latitude_offset=0.0014, categories=MALATANG_SOUP),
    build_merchant_seed(name="麻辣拌研究所", description="干拌和冒菜组合更适合重口用户", district="杨浦", homepage_category="麻辣烫", promo_text="麻辣拌系列满减8元", delivery_radius_meters=3250, delivery_fee=4.5, min_order_amount=24.0, avg_delivery_minutes=32, rating=4.6, longitude_offset=0.0076, latitude_offset=0.0017, categories=MALATANG_MIX),
    build_merchant_seed(name="藤椒冒菜馆", description="藤椒麻香明显，冒菜类更受欢迎", district="长宁", homepage_category="麻辣烫", promo_text="藤椒招牌套餐减9元", delivery_radius_meters=3180, delivery_fee=4.0, min_order_amount=23.0, avg_delivery_minutes=30, rating=4.5, longitude_offset=0.0073, latitude_offset=0.0011, categories=MALATANG_MIX),
    build_merchant_seed(name="意面小站", description="经典披萨和意面组合适合家庭点单", district="静安", homepage_category="披萨意面", promo_text="披萨意面双拼减12元", delivery_radius_meters=3300, delivery_fee=5.0, min_order_amount=30.0, avg_delivery_minutes=35, rating=4.6, longitude_offset=0.0081, latitude_offset=0.0010, categories=PIZZA_PASTA),
    build_merchant_seed(name="芝士角", description="偏芝士和烘烤风味，适合重口披萨爱好者", district="徐汇", homepage_category="披萨意面", promo_text="芝士系列加价购饮品", delivery_radius_meters=3200, delivery_fee=5.0, min_order_amount=31.0, avg_delivery_minutes=34, rating=4.7, longitude_offset=0.0085, latitude_offset=0.0012, categories=PIZZA_PASTA),
    build_merchant_seed(name="番茄厨房", description="番茄肉酱和焗饭都更偏家常路线", district="浦东", homepage_category="披萨意面", promo_text="焗饭午餐立减8元", delivery_radius_meters=3250, delivery_fee=5.0, min_order_amount=29.0, avg_delivery_minutes=33, rating=4.5, longitude_offset=0.0082, latitude_offset=0.0014, categories=BAKED_RICE_SNACK),
    build_merchant_seed(name="薄脆披萨屋", description="薄底披萨和气泡饮搭配更适合多人分享", district="杨浦", homepage_category="披萨意面", promo_text="分享披萨套餐88折", delivery_radius_meters=3350, delivery_fee=5.5, min_order_amount=32.0, avg_delivery_minutes=36, rating=4.6, longitude_offset=0.0086, latitude_offset=0.0016, categories=PIZZA_PASTA),
    build_merchant_seed(name="焗饭事务所", description="焗饭和餐前小点更适合工作日正餐", district="长宁", homepage_category="披萨意面", promo_text="双人焗饭套餐减10元", delivery_radius_meters=3150, delivery_fee=5.0, min_order_amount=30.0, avg_delivery_minutes=34, rating=4.5, longitude_offset=0.0083, latitude_offset=0.0011, categories=BAKED_RICE_SNACK),
]
