#!/usr/bin/env python3
"""同步数据库中的商家和菜品数据到Pinecone向量数据库。

用法:
    python tools/assistant_sync.py                  # 同步所有数据
    python tools/assistant_sync.py --sync-dishes    # 只同步菜品
    python tools/assistant_sync.py --sync-merchants # 只同步商家
    python tools/assistant_sync.py --clear-existing # 同步前清空现有数据

"""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
from dotenv import load_dotenv
for dotenv_path in [PROJECT_ROOT / ".env", Path(".env")]:
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=False)

from tools.assistant_vector_store import AssistantVectorStore


def _build_dish_text(dish: dict, merchant: dict) -> str:
    """构建菜品语义文本描述，用于生成嵌入向量。"""
    allergens = dish["allergens"] if dish["allergens"] else ["无显式过敏原"]
    scenario_terms = []
    if "下饭" in dish["description"] or "辣" in dish["flavor_profile"]:
        scenario_terms.append("工作餐")
        scenario_terms.append("米饭搭配")
    if dish["price"] <= 35:
        scenario_terms.append("单人简餐")
    if not scenario_terms:
        scenario_terms.append("日常点餐")

    parts = [
        f"菜品:{dish['name']}",
        f"商家:{merchant['name']}",
        f"菜系:{dish['cuisine_type'] or '其他'}",
        f"口味:{dish['flavor_profile'] or '未知'}",
        f"价格:{dish['price']:.0f}元",
        f"适合场景:{','.join(scenario_terms)}",
        f"食材:{','.join(dish['ingredients']) if dish['ingredients'] else '未注明'}",
        f"过敏原:{','.join(allergens)}",
        f"特色:{dish['description'][:50] if dish['description'] else '无描述'}",
        f"烹饪方式:{dish['cooking_method'] or '未知'}",
    ]
    return "。".join(parts)


def _build_merchant_text(merchant: dict) -> str:
    """构建商家语义文本描述，用于生成嵌入向量。"""
    parts = [
        f"商家:{merchant['name']}",
        f"菜系标签:{','.join(merchant['merchant_tags']) if merchant['merchant_tags'] else '综合'}",
        f"营业时间:{merchant['business_hours'] or '未注明'}",
        f"配送费:{merchant['delivery_fee']:.0f}元",
        f"起送价:{merchant['min_order_amount']:.0f}元",
        f"评分:{merchant['rating']}",
        f"描述:{merchant['description'][:80] if merchant['description'] else '无描述'}",
    ]
    return "。".join(parts)


def _create_dish_candidate(dish: dict, merchant: dict) -> dict:
    """创建用于向量存储的菜品候选项。"""
    return {
        "id": f"dish_{dish['id']}",
        "text": _build_dish_text(dish, merchant),
        "metadata": {
            "source_type": "dish",
            "source_id": dish["id"],
            "dish_id": dish["id"],
            "dish_name": dish["name"],
            "merchant_id": merchant["id"],
            "merchant_name": merchant["name"],
            "price": dish["price"],
            "cuisine_type": dish["cuisine_type"],
            "flavor_profile": dish["flavor_profile"],
            "ingredients": dish["ingredients"],
            "allergens": dish["allergens"],
        },
    }


def _create_merchant_candidate(merchant: dict) -> dict:
    """创建用于向量存储的商家候选项。"""
    return {
        "id": f"merchant_{merchant['id']}",
        "text": _build_merchant_text(merchant),
        "metadata": {
            "source_type": "merchant",
            "source_id": merchant["id"],
            "merchant_id": merchant["id"],
            "merchant_name": merchant["name"],
            "rating": merchant["rating"],
            "merchant_tags": merchant["merchant_tags"],
            "business_hours": merchant["business_hours"],
            "description": merchant["description"],
        },
    }


def sync_dishes(store: AssistantVectorStore, catalog_service, merchants: list[dict], clear: bool = False) -> int:
    """同步所有菜品数据到向量数据库。

    Returns:
        int: 同步的菜品数量
    """
    candidates = []

    for merchant in merchants:
        dishes = catalog_service.list_dishes_by_merchant(merchant["id"])
        for dish in dishes:
            candidates.append(_create_dish_candidate(dish, merchant))

    if not candidates:
        print("没有找到可同步的菜品数据")
        return 0

    namespace = "dishes"

    if clear:
        print(f"清空现有菜品数据(namespace: {namespace})...")
        try:
            store._index.delete(delete_all=True, namespace=namespace)
        except Exception as e:
            print(f"警告: 清空数据失败: {e}")

    print(f"正在同步 {len(candidates)} 个菜品到向量数据库...")

    if store.upsert_candidates(candidates, batch_size=30, namespace=namespace):
        print(f"成功同步 {len(candidates)} 个菜品")
        return len(candidates)
    else:
        print("同步菜品失败")
        return 0


def sync_merchants(store: AssistantVectorStore, merchants: list[dict], clear: bool = False) -> int:
    """同步所有商家数据到向量数据库。

    Returns:
        int: 同步的商家数量
    """
    candidates = [_create_merchant_candidate(m) for m in merchants]

    if not candidates:
        print("没有找到可同步的商家数据")
        return 0

    namespace = "merchants"

    if clear:
        print(f"清空现有商家数据(namespace: {namespace})...")
        try:
            store._index.delete(delete_all=True, namespace=namespace)
        except Exception as e:
            print(f"警告: 清空数据失败: {e}")

    print(f"正在同步 {len(candidates)} 个商家到向量数据库...")

    if store.upsert_candidates(candidates, batch_size=30, namespace=namespace):
        print(f"成功同步 {len(candidates)} 个商家")
        return len(candidates)
    else:
        print("同步商家失败")
        return 0


def main():
    parser = argparse.ArgumentParser(description="同步商家和菜品数据到Pinecone向量数据库")
    parser.add_argument("--sync-dishes", action="store_true", help="只同步菜品")
    parser.add_argument("--sync-merchants", action="store_true", help="只同步商家")
    parser.add_argument("--clear-existing", action="store_true", help="同步前清空现有数据")
    args = parser.parse_args()

    # 初始化向量存储
    store = AssistantVectorStore()

    if not store.is_ready():
        print("错误: Pinecone向量数据库未准备好，请检查配置:")
        print("  - PINECONE_API_KEY")
        print("  - PINECONE_ASSISTANT_INDEX")
        return 1

    print("Pinecone向量数据库已连接")

    # 从数据库加载数据
    from api.db import SessionLocal
    from service.catalog_service import CatalogService

    session = SessionLocal()
    try:
        catalog_service = CatalogService(session)
        merchants = catalog_service.list_merchants()

        print(f"从数据库加载了 {len(merchants)} 个商家")

        total_synced = 0

        # 默认同步所有，或根据参数指定
        sync_all = not (args.sync_dishes or args.sync_merchants)

        if sync_all or args.sync_merchants:
            count = sync_merchants(store, merchants, clear=args.clear_existing)
            total_synced += count

        if sync_all or args.sync_dishes:
            count = sync_dishes(store, catalog_service, merchants, clear=args.clear_existing)
            total_synced += count

        print(f"\n同步完成，共同步 {total_synced} 条数据")
        return 0

    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
