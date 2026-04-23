import re

from service.assistant_models import AssistantParsedQuery

CUISINE_KEYWORDS = ["川菜", "湘菜", "粤菜", "轻食", "咖啡甜品"]
ALLERGEN_KEYWORDS = ["花生", "麸质", "牛奶", "鸡蛋", "海鲜"]
COMPARISON_SPLITTER = re.compile(r"和|与")
BUDGET_PATTERN = re.compile(r"(?:预算\s*)(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:元|块)(?:以内|以下|之内)?")
PARTY_SIZE_PATTERN = re.compile(r"(\d+)\s*(?:个人|人)")


def parse_assistant_query(message: str) -> AssistantParsedQuery:
    query_type = "knowledge"
    if any(keyword in message for keyword in ["推荐", "吃什么", "适合"]):
        query_type = "recommendation"
    if any(keyword in message for keyword in ["对比", "比较"]):
        query_type = "comparison"

    cuisine_types = [keyword for keyword in CUISINE_KEYWORDS if keyword in message]
    exclude_allergens = [
        keyword
        for keyword in ALLERGEN_KEYWORDS
        if f"不要{keyword}" in message or f"不含{keyword}" in message
    ]

    budget_match = BUDGET_PATTERN.search(message)
    party_size_match = PARTY_SIZE_PATTERN.search(message)

    comparison_targets: list[str] = []
    if query_type == "comparison":
        cleaned = message.replace("帮我", "").replace("对比", "").replace("比较", "")
        comparison_targets = [item.strip() for item in COMPARISON_SPLITTER.split(cleaned) if item.strip()]
        if len(comparison_targets) <= 1:
            comparison_targets = []

    needs_clarification = False
    clarification_question = None
    if query_type == "recommendation" and not budget_match and not party_size_match:
        needs_clarification = True
        clarification_question = "请告诉我这顿大概几个人吃、预算多少？"

    return AssistantParsedQuery(
        raw_message=message,
        query_type=query_type,
        cuisine_types=cuisine_types,
        budget_max=float(budget_match.group(1) or budget_match.group(2)) if budget_match else None,
        party_size=int(party_size_match.group(1)) if party_size_match else None,
        exclude_allergens=exclude_allergens,
        comparison_targets=comparison_targets,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
    )
