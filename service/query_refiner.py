import json
import logging
import os

from tools.llm_tool import call_llm

logger = logging.getLogger(__name__)

_REFINER_PROMPT = """你是一个查询提炼专家。

请将用户的口语化需求提炼成适合向量数据库检索的简短关键词查询。

要求：
- 保留核心实体（菜系、口味、场景、食材）
- 去除礼貌用语、语气词、冗余描述
- 输出应为关键词组合，不超过20个字

请严格按照以下 JSON 格式返回，不要包含任何其他文字：
{
    "refined_query": "提炼后的关键词查询"
}

示例：
用户："想吃下饭一点的川菜" -> {"refined_query": "下饭 川菜 口味重 米饭搭档"}
用户："推荐几个湘菜，辣一点的" -> {"refined_query": "湘菜 辣味 重口味"}
用户："有哪些卖咖啡的店" -> {"refined_query": "咖啡 饮品 甜品"}

记住：只返回纯 JSON，不要有任何额外字符和解释。"""


class QueryRefiner:
    def __init__(self) -> None:
        self._model_name = os.getenv("MODEL_NAME")

    def refine(self, message: str) -> str:
        if not self._model_name:
            return message

        try:
            llm_response = call_llm(query=message, system_instruction=_REFINER_PROMPT)
            cleaned = self._clean_json_response(llm_response)
            parsed = json.loads(cleaned)
            refined = parsed.get("refined_query", "").strip()
            return refined if refined else message
        except Exception as e:
            logger.warning(f"Query refinement failed: {e}, falling back to original")
            return message

    @staticmethod
    def _clean_json_response(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return raw[start : end + 1]
        return raw
