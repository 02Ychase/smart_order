"""Expand test cases: add merchant info queries and more diverse cases."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = PROJECT_ROOT / "tests/eval/assistant_rag_cases.jsonl"

# Load existing cases
existing = []
with open(CASES_PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            existing.append(json.loads(line))
existing_ids = {c.get("id", "") for c in existing}

# New merchant info test cases
merchant_info_cases = [
    # ── 电话查询 ──
    {"id": "merchant_phone_001", "category": "merchant_info", "query": "兰姨小炒的电话是多少", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_phone_002", "category": "merchant_info", "query": "午后豆房的电话", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_phone_003", "category": "merchant_info", "query": "厚牛堡局联系电话", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_phone_004", "category": "merchant_info", "query": "给我元气食堂的电话号码", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_phone_005", "category": "merchant_info", "query": "阿福粥铺的电话是什么", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_phone_006", "category": "merchant_info", "query": "意面小站的联系方式", "expected_source_type": "merchant", "constraints": {}},

    # ── 地址查询 ──
    {"id": "merchant_addr_001", "category": "merchant_info", "query": "午后豆房的地址在哪", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_addr_002", "category": "merchant_info", "query": "兰姨小炒在哪里", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_addr_003", "category": "merchant_info", "query": "骨汤烫铺的地址", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_addr_004", "category": "merchant_info", "query": "请问阿福粥铺在哪", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_addr_005", "category": "merchant_info", "query": "谷粒厨房地址是哪里", "expected_source_type": "merchant", "constraints": {}},

    # ── 营业时间查询 ──
    {"id": "merchant_hours_001", "category": "merchant_info", "query": "兰姨小炒的营业时间是几点", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_hours_002", "category": "merchant_info", "query": "午后豆房几点开门", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_hours_003", "category": "merchant_info", "query": "阿福粥铺几点营业", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_hours_004", "category": "merchant_info", "query": "深夜汤面开到几点", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_hours_005", "category": "merchant_info", "query": "厚牛堡局的营业时间", "expected_source_type": "merchant", "constraints": {}},

    # ── 评分/配送查询 ──
    {"id": "merchant_meta_001", "category": "merchant_info", "query": "评分最高的湘菜店是哪家", "expected_source_type": "merchant", "constraints": {"cuisine_types": ["湘菜"]}},
    {"id": "merchant_meta_002", "category": "merchant_info", "query": "兰姨小炒的评分是多少", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_meta_003", "category": "merchant_info", "query": "哪家麻辣烫评分最高", "expected_source_type": "merchant", "constraints": {"cuisine_types": ["麻辣烫"]}},
    {"id": "merchant_meta_004", "category": "merchant_info", "query": "配送费最便宜的是哪几家", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_meta_005", "category": "merchant_info", "query": "有哪些店可以送到静安区", "expected_source_type": "merchant", "constraints": {}},

    # ── 商家描述查询 ──
    {"id": "merchant_desc_001", "category": "merchant_info", "query": "兰姨小炒是什么样的店", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_desc_002", "category": "merchant_info", "query": "谷粒厨房主打什么", "expected_source_type": "merchant", "constraints": {}},
    {"id": "merchant_desc_003", "category": "merchant_info", "query": "午后豆房有什么特色", "expected_source_type": "merchant", "constraints": {}},

    # ── 商家菜品查询 ──
    {"id": "merchant_menu_001", "category": "merchant_info", "query": "兰姨小炒有哪些招牌菜", "expected_source_type": "dish", "constraints": {}},
    {"id": "merchant_menu_002", "category": "merchant_info", "query": "谷粒厨房有什么吃的", "expected_source_type": "dish", "constraints": {}},
    {"id": "merchant_menu_003", "category": "merchant_info", "query": "阿福粥铺除了粥还有什么", "expected_source_type": "dish", "constraints": {}},
    {"id": "merchant_menu_004", "category": "merchant_info", "query": "骨汤烫铺有哪些锅底", "expected_source_type": "dish", "constraints": {}},
    {"id": "merchant_menu_005", "category": "merchant_info", "query": "意面小站有什么披萨", "expected_source_type": "dish", "constraints": {}},
]

# Additional diverse query cases (more categories and edge cases)
diverse_cases = [
    # ── 扩展菜系推荐 ──
    {"id": "cuisine_011", "category": "cuisine_rec", "query": "想吃川菜，推荐几个经典菜", "expected_source_type": "dish", "constraints": {"cuisine_types": ["川菜"]}},
    {"id": "cuisine_012", "category": "cuisine_rec", "query": "推荐几道粤菜", "expected_source_type": "dish", "constraints": {"cuisine_types": ["粤菜"]}},
    {"id": "cuisine_013", "category": "cuisine_rec", "query": "东北菜有啥推荐的", "expected_source_type": "dish", "constraints": {"cuisine_types": ["东北菜"]}},
    {"id": "cuisine_014", "category": "cuisine_rec", "query": "日韩料理里面最好吃的几道", "expected_source_type": "dish", "constraints": {"cuisine_types": ["日韩料理"]}},
    {"id": "cuisine_015", "category": "cuisine_rec", "query": "推荐点炸鸡汉堡", "expected_source_type": "dish", "constraints": {"cuisine_types": ["炸鸡汉堡"]}},

    # ── 扩展口味 ──
    {"id": "flavor_011", "category": "flavor_pref", "query": "要特别辣的，越辣越好", "expected_source_type": "dish", "constraints": {"flavor_preferences": ["麻辣", "辣"]}},
    {"id": "flavor_012", "category": "flavor_pref", "query": "有没有不辣又好吃的", "expected_source_type": "dish", "constraints": {"forbidden_keywords": ["辣", "麻辣"]}},
    {"id": "flavor_013", "category": "flavor_pref", "query": "香辣口味的有没有", "expected_source_type": "dish", "constraints": {"flavor_preferences": ["香辣"]}},
    {"id": "flavor_014", "category": "flavor_pref", "query": "清淡一点的，适合老人吃的", "expected_source_type": "dish", "constraints": {"flavor_preferences": ["清淡"]}},
    {"id": "flavor_015", "category": "flavor_pref", "query": "奶香浓郁的甜品推荐", "expected_source_type": "dish", "constraints": {"flavor_preferences": ["奶香"]}},

    # ── 扩展预算 ──
    {"id": "budget_009", "category": "budget_constraints", "query": "25块钱以内有什么好吃的", "expected_source_type": "dish", "constraints": {"budget_max": 25}},
    {"id": "budget_010", "category": "budget_constraints", "query": "人均80左右推荐", "expected_source_type": "dish", "constraints": {"budget_max": 80}},
    {"id": "budget_011", "category": "budget_constraints", "query": "最贵的几个菜是什么", "expected_source_type": "dish", "constraints": {"sort_by": "price_desc", "price_preference": "most_expensive"}},
    {"id": "budget_012", "category": "budget_constraints", "query": "有没有5块钱以下的东西", "expected_source_type": "dish", "constraints": {"budget_max": 5}},

    # ── 扩展过敏原 ──
    {"id": "allergen_006", "category": "allergen_exclusions", "query": "我对大豆过敏，能吃啥", "expected_source_type": "dish", "constraints": {"exclude_allergens": ["大豆"]}},
    {"id": "allergen_007", "category": "allergen_exclusions", "query": "坚果过敏的人能吃什么", "expected_source_type": "dish", "constraints": {"exclude_allergens": ["坚果"]}},
    {"id": "allergen_008", "category": "allergen_exclusions", "query": "不能吃辣的，也不要海鲜", "expected_source_type": "dish", "constraints": {"forbidden_keywords": ["辣"], "exclude_allergens": ["海鲜", "甲壳类", "鱼类"]}},

    # ── 扩展多约束 ──
    {"id": "multi_009", "category": "multi_constraint", "query": "推荐3个不辣的川菜，40块以内", "expected_source_type": "dish", "constraints": {"cuisine_types": ["川菜"], "budget_max": 40, "limit": 3, "forbidden_keywords": ["辣"]}},
    {"id": "multi_010", "category": "multi_constraint", "query": "2个人吃日料，人均60，不要生的", "expected_source_type": "dish", "constraints": {"cuisine_types": ["日韩料理"], "budget_max": 60, "party_size": 2}},
    {"id": "multi_011", "category": "multi_constraint", "query": "推荐几个披萨，不要榴莲的，50以内", "expected_source_type": "dish", "constraints": {"cuisine_types": ["披萨意面"], "budget_max": 50, "forbidden_keywords": ["榴莲"]}},
    {"id": "multi_012", "category": "multi_constraint", "query": "想吃烤肉串，要羊肉的，人均40左右", "expected_source_type": "dish", "constraints": {"flavor_preferences": ["烤"], "required_keywords": ["羊肉"], "budget_max": 40}},
    {"id": "multi_013", "category": "multi_constraint", "query": "3个人吃火锅，人均50，要辣的", "expected_source_type": "dish", "constraints": {"cuisine_types": ["火锅串串"], "budget_max": 50, "party_size": 3, "flavor_preferences": ["辣"]}},

    # ── 扩展中英混合 ──
    {"id": "mixed_004", "category": "mixed_language", "query": "give me 3 spicy Hunan dishes", "expected_source_type": "dish", "constraints": {"cuisine_types": ["湘菜"], "limit": 3}},
    {"id": "mixed_005", "category": "mixed_language", "query": "推荐几个 best selling 披萨", "expected_source_type": "dish", "constraints": {"cuisine_types": ["披萨意面"]}},

    # ── 扩展噪音输入 ──
    {"id": "noisy_004", "category": "noisy_input", "query": "那个...有没有...就是那个...辣的", "expected_source_type": "dish", "constraints": {"flavor_preferences": ["辣"]}},
    {"id": "noisy_005", "category": "noisy_input", "query": "随便推荐点啥吃的吧", "expected_source_type": "dish", "constraints": {}},

    # ── 扩展会话跟进 ──
    {"id": "followup_006", "category": "session_followups", "query": "这个太甜了，换苦一点的", "expected_source_type": "dish", "constraints": {"forbidden_keywords": ["甜"]}},
    {"id": "followup_007", "category": "session_followups", "query": "有没有同一家店的其他菜", "expected_source_type": "dish", "constraints": {}},
    {"id": "followup_008", "category": "session_followups", "query": "刚才推荐的不够辣", "expected_source_type": "dish", "constraints": {"flavor_preferences": ["麻辣", "辣"]}},

    # ── 扩展数量限制 ──
    {"id": "quantity_006", "category": "quantity_limits", "query": "推荐5个最受欢迎的菜", "expected_source_type": "dish", "constraints": {"limit": 5}},
    {"id": "quantity_007", "category": "quantity_limits", "query": "给我推荐10个菜选择一下", "expected_source_type": "dish", "constraints": {"limit": 10}},

    # ── 价格区间 ──
    {"id": "price_range_001", "category": "price_sorting", "query": "20到40块钱之间的菜", "expected_source_type": "dish", "constraints": {"budget_max": 40}},
    {"id": "price_range_002", "category": "price_sorting", "query": "有哪些便宜又好吃的", "expected_source_type": "dish", "constraints": {"sort_by": "price_asc", "price_preference": "least_expensive"}},
    {"id": "price_range_003", "category": "price_sorting", "query": "贵的和便宜的都给几个", "expected_source_type": "dish", "constraints": {}},

    # ── 特殊场景 ──
    {"id": "special_001", "category": "special", "query": "有没有适合减肥吃的", "expected_source_type": "dish", "constraints": {"cuisine_types": ["轻食"]}},
    {"id": "special_002", "category": "special", "query": "宵夜吃什么好", "expected_source_type": "dish", "constraints": {}},
    {"id": "special_003", "category": "special", "query": "早餐有什么可以点的", "expected_source_type": "dish", "constraints": {"cuisine_types": ["粥面"]}},
    {"id": "special_004", "category": "special", "query": "下午茶推荐几个", "expected_source_type": "dish", "constraints": {"cuisine_types": ["咖啡甜品"]}},
    {"id": "special_005", "category": "special", "query": "适合聚会人多吃的", "expected_source_type": "dish", "constraints": {"cuisine_types": ["披萨意面", "龙虾烧烤"]}},
    {"id": "special_006", "category": "special", "query": "冬天适合吃什么暖身的", "expected_source_type": "dish", "constraints": {}},
    {"id": "special_007", "category": "special", "query": "有没有适合小朋友吃的清淡的", "expected_source_type": "dish", "constraints": {"flavor_preferences": ["清淡"]}},
]

# Combine and deduplicate
all_new = merchant_info_cases + diverse_cases
for case in all_new:
    if case["id"] not in existing_ids:
        existing.append(case)
        existing_ids.add(case["id"])

# Write back
with open(CASES_PATH, "w", encoding="utf-8") as f:
    for case in existing:
        f.write(json.dumps(case, ensure_ascii=False) + "\n")

print(f"Added {len(all_new)} new cases. Total: {len(existing)} cases")
print(f"  - merchant info: {len(merchant_info_cases)}")
print(f"  - diverse queries: {len(diverse_cases)}")
