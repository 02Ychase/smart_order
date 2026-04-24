from service.rag_retriever import RagRetriever


class StubCatalog:
    def list_merchants(self, district=None):
        return [
            {
                "id": 1,
                "name": "兰姨小炒",
                "description": "现炒川湘下饭菜",
                "rating": 4.8,
                "business_hours": "10:00-21:30",
                "merchant_tags": ["川湘", "下饭"],
                "homepage_category": "湘菜",
                "delivery_fee": 4.0,
                "min_order_amount": 20.0,
                "district": "静安",
            }
        ]

    def list_dishes_by_merchant(self, merchant_id):
        return [
            {
                "id": 11,
                "merchant_id": 1,
                "name": "鱼香肉丝",
                "description": "酸甜微辣，下饭",
                "price": 28.0,
                "is_recommended": True,
                "cuisine_type": "川味麻辣",
                "flavor_profile": "酸甜微辣",
                "ingredients": ["猪里脊", "木耳"],
                "allergens": [],
                "cooking_method": "爆炒",
            },
            {
                "id": 12,
                "merchant_id": 1,
                "name": "宫保鸡丁",
                "description": "花生香辣",
                "price": 60.0,
                "is_recommended": True,
                "cuisine_type": "川味麻辣",
                "flavor_profile": "香辣",
                "ingredients": ["鸡肉", "花生"],
                "allergens": ["花生"],
                "cooking_method": "爆炒",
            },
        ]


class StubVectorStore:
    def is_ready(self):
        return True

    def semantic_search(self, query, top_k=5, namespace=""):
        if namespace == "dishes":
            return [
                {"id": "dish_11", "score": 0.9, "metadata": {"dish_id": 11}},
                {"id": "dish_12", "score": 0.8, "metadata": {"dish_id": 12}},
            ]
        return []


def test_rag_retriever_filters_budget_and_allergens() -> None:
    retriever = RagRetriever(
        catalog_service=StubCatalog(),
        vector_store=StubVectorStore(),
    )

    evidence = retriever.retrieve("推荐几种川菜，2个人吃，100元以内，不要花生", limit=3)

    assert [item.source_id for item in evidence] == [11]
    assert evidence[0].facts["price"] == 28.0
    assert "未命中花生过敏原" in evidence[0].why_matched


def test_rag_retriever_returns_merchant_evidence_for_knowledge() -> None:
    retriever = RagRetriever(
        catalog_service=StubCatalog(),
        vector_store=StubVectorStore(),
    )

    evidence = retriever.retrieve("有哪些湘菜店？几点营业？", limit=3)

    assert evidence[0].source_type == "merchant"
    assert evidence[0].merchant_id == 1
    assert "10:00-21:30" in evidence[0].citation
