"""Standalone RAG evaluation with stub retrievers — no DB/VectorStore needed.

Runs the full evaluate_cases pipeline against the 81-case JSONL dataset
using realistic stub data, outputting all metrics.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.evaluate_assistant_rag import evaluate_cases, load_cases


def _make_evidence(source_type, source_id, merchant_id, dish_name, merchant_name, cuisine_type, price, citation, why_matched=None):
    return type("Evidence", (), {
        "source_type": source_type,
        "source_id": source_id,
        "merchant_id": merchant_id,
        "title": f"{dish_name}｜{merchant_name}" if source_type == "dish" else merchant_name,
        "facts": {
            "dish_id": source_id if source_type == "dish" else None,
            "dish_name": dish_name if source_type == "dish" else None,
            "merchant_id": merchant_id,
            "merchant_name": merchant_name,
            "cuisine_type": cuisine_type,
            "price": price,
            "allergens": [],
            "is_available": True,
            "merchant_rating": 4.5,
            "is_recommended": True,
        },
        "why_matched": why_matched or [cuisine_type],
        "citation": citation,
        "score": random.uniform(0.7, 0.99),
    })()


class RealisticStubRetriever:
    """Returns realistic Chinese restaurant evidence based on query content."""

    def __init__(self):
        self._cache = {}
        self.call_count = 0

    def retrieve(self, query, agent_plan=None, memories=None, limit=5):
        self.call_count += 1
        filters = getattr(agent_plan, "filters", {}) if agent_plan else {}
        intent = getattr(agent_plan, "intent", "recommendation") if agent_plan else "recommendation"
        expected_type = "dish" if intent == "recommendation" else "merchant"

        cuisine = (filters.get("cuisine_types") or filters.get("allowed_cuisine_types") or [None])[0]
        budget_max = filters.get("budget_max")
        sort_by = filters.get("sort_by")

        results = self._pick_results(query, cuisine, budget_max, sort_by, expected_type, limit)
        return results[:limit]

    def _pick_results(self, query, cuisine, budget_max, sort_by, expected_type, limit):
        q = query.lower()

        dish_pool = [
            _make_evidence("dish", 1, 1, "辣椒炒肉", "兰姨小炒", "湘菜", 29, "现炒黄牛肉片，鲜辣下饭", ["湘菜", "鲜辣"]),
            _make_evidence("dish", 2, 1, "小炒黄牛肉", "兰姨小炒", "湘菜", 42, "黄牛肉片现炒，芹菜小米椒提香", ["湘菜", "鲜辣"]),
            _make_evidence("dish", 3, 1, "外婆菜炒鸡蛋", "兰姨小炒", "湘菜", 24, "外婆菜配土鸡蛋，家常下饭", ["湘菜", "家常"]),
            _make_evidence("dish", 4, 2, "干锅肥肠", "洞庭食堂", "湘菜", 46, "干锅煸炒，麻辣浓郁", ["湘菜", "麻辣"]),
            _make_evidence("dish", 5, 2, "剁椒鱼块", "洞庭食堂", "湘菜", 38, "鲜辣剁椒蒸鱼块", ["湘菜", "鲜辣"]),
            _make_evidence("dish", 6, 6, "香煎鸡胸藜麦碗", "谷粒厨房", "轻食", 33, "低脂高蛋白，健身首选", ["轻食", "健康"]),
            _make_evidence("dish", 7, 7, "烟熏三文鱼牛油果碗", "半勺轻食", "轻食", 39, "进口三文鱼配牛油果", ["轻食", "健康"]),
            _make_evidence("dish", 8, 11, "燕麦拿铁", "午后豆房", "咖啡甜品", 21, "燕麦奶配浓缩咖啡", ["咖啡", "甜品"]),
            _make_evidence("dish", 9, 11, "巴斯克芝士蛋糕", "午后豆房", "咖啡甜品", 28, "流心芝士，绵密口感", ["咖啡", "甜品"]),
            _make_evidence("dish", 10, 16, "厚切牛肉堡", "厚牛堡局", "炸鸡汉堡", 31, "安格斯牛肉厚切", ["汉堡", "美式"]),
            _make_evidence("dish", 11, 18, "原味炸鸡块", "脆脆鸡食堂", "炸鸡汉堡", 26, "酥脆外皮，鲜嫩多汁", ["炸鸡", "小食"]),
            _make_evidence("dish", 12, 21, "皮蛋瘦肉粥", "阿福粥铺", "粥面", 14, "现熬皮蛋瘦肉粥，暖胃", ["粥品", "暖胃"]),
            _make_evidence("dish", 13, 22, "鲜虾云吞面", "深夜汤面", "粥面", 22, "鲜虾云吞配竹升面", ["面食", "鲜香"]),
            _make_evidence("dish", 14, 26, "照烧鸡排饭", "元气食堂", "日韩料理", 29, "日式照烧鸡腿排", ["日料", "照烧"]),
            _make_evidence("dish", 15, 28, "骨汤麻辣烫", "骨汤烫铺", "麻辣烫", 26, "骨汤底料配时蔬", ["麻辣烫", "骨汤"]),
            _make_evidence("dish", 16, 30, "经典冒菜", "麻辣拌研究所", "麻辣烫", 28, "川味经典冒菜", ["麻辣烫", "川味"]),
            _make_evidence("dish", 17, 31, "玛格丽特披萨", "意面小站", "披萨意面", 42, "意式经典薄底披萨", ["披萨", "意式"]),
            _make_evidence("dish", 18, 32, "榴莲披萨", "芝士角", "披萨意面", 56, "金枕榴莲芝士披萨", ["披萨", "意式"]),
            _make_evidence("dish", 19, 33, "芝士鸡排焗饭", "番茄厨房", "披萨意面", 29, "芝士焗鸡排配米饭", ["焗饭", "意式"]),
            _make_evidence("dish", 20, 36, "麻辣拌", "藤椒冒菜馆", "麻辣烫", 25, "四川风味麻辣拌", ["麻辣烫", "川味"]),
        ]

        merchant_pool = [
            _make_evidence("merchant", 1, 1, "", "兰姨小炒", "湘菜", None, "静安区正宗湘菜小炒", ["湘菜", "高评分"]),
            _make_evidence("merchant", 2, 2, "", "洞庭食堂", "湘菜", None, "徐汇区砂锅湘菜", ["湘菜", "砂锅"]),
            _make_evidence("merchant", 11, 11, "", "午后豆房", "咖啡甜品", None, "静安区精品咖啡烘焙", ["咖啡", "高评分"]),
            _make_evidence("merchant", 6, 6, "", "谷粒厨房", "轻食", None, "静安区健康轻食", ["轻食", "健康"]),
            _make_evidence("merchant", 16, 16, "", "厚牛堡局", "炸鸡汉堡", None, "静安区美式汉堡", ["汉堡", "美式"]),
            _make_evidence("merchant", 21, 21, "", "阿福粥铺", "粥面", None, "静安区暖胃粥品", ["粥品"]),
            _make_evidence("merchant", 26, 26, "", "元气食堂", "日韩料理", None, "静安区日式料理", ["日料"]),
            _make_evidence("merchant", 28, 28, "", "骨汤烫铺", "麻辣烫", None, "浦东区骨汤麻辣烫", ["麻辣烫"]),
            _make_evidence("merchant", 31, 31, "", "意面小站", "披萨意面", None, "静安区意面披萨", ["披萨", "意式"]),
        ]

        if expected_type == "merchant" or any(w in q for w in ["店", "营业", "电话", "地址"]):
            results = list(merchant_pool)
        else:
            results = list(dish_pool)

        if cuisine:
            results = [r for r in results if cuisine in (r.facts.get("cuisine_type") or "")]
            if not results:
                results = list(dish_pool)

        if budget_max is not None:
            results = [r for r in results if (r.facts.get("price") or 999) <= budget_max]

        if sort_by == "price_desc":
            results.sort(key=lambda r: r.facts.get("price") or 0, reverse=True)
        elif sort_by == "price_asc":
            results.sort(key=lambda r: r.facts.get("price") or 0)

        return results


def main():
    parser_args = sys.argv[1:]
    enable_llm_judge = "--llm-judge" in parser_args
    enable_ablation = "--ablation" in parser_args
    case_limit = None
    for i, arg in enumerate(parser_args):
        if arg == "--limit" and i + 1 < len(parser_args):
            case_limit = int(parser_args[i + 1])

    cases_path = PROJECT_ROOT / "tests/eval/assistant_rag_cases.jsonl"
    cases = load_cases(cases_path)
    if case_limit:
        cases = cases[:case_limit]

    retriever = RealisticStubRetriever()

    metrics = evaluate_cases(
        cases,
        retriever,
        enable_llm_judge=enable_llm_judge,
        enable_ablation=enable_ablation,
    )

    metrics["retriever_calls"] = retriever.call_count

    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    # Summary
    rec = metrics.get("recall_metrics", {})
    rank = metrics.get("ranking_metrics", {})
    lat = metrics.get("latency", {})
    cache = metrics.get("cache", {})

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"  Cases:                {metrics['case_count']}")
    print(f"  Recall@5:             {rec.get('recall_at_5', 'N/A'):.4f}")
    print(f"  Constraint Pass Rate: {rec.get('constraint_pass_rate', 'N/A'):.4f}")
    print(f"  Diversity Pass Rate:  {rec.get('diversity_pass_rate', 'N/A'):.4f}")
    print(f"  Citation Coverage:    {rec.get('citation_coverage', 'N/A'):.4f}")
    if rank:
        print(f"  NDCG@5:               {rank.get('ndcg_at_5', 'N/A'):.4f}")
        print(f"  MRR:                  {rank.get('mrr', 'N/A'):.4f}")
        print(f"  Precision@5:          {rank.get('precision_at_5', 'N/A'):.4f}")
        print(f"  MAP:                  {rank.get('map', 'N/A'):.4f}")
        print(f"  Hit Rate:             {rank.get('hit_rate', 'N/A'):.4f}")
        print(f"  (cases with grades:   {rank.get('cases_with_grades', 'N/A')})")
    print(f"  Latency P50:          {lat.get('p50_ms', 'N/A')} ms")
    print(f"  Latency P95:          {lat.get('p95_ms', 'N/A')} ms")
    print(f"  Cache Hit Rate:       {cache.get('hit_rate', 'N/A'):.4f}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
