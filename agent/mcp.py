"""
实现LangChain中各个基础组件（定义三个工具，工具一：处理常规问题的对话问答；工具二：实现菜品查询问答对话；工具三：实现配送范围配送问答对话）
"""

from langchain_core.tools import ToolException, tool
import os
import logging
from tools.llm_tool import call_llm
from typing import Any, Dict
from tools.assistant_vector_store import AssistantVectorStore
from tools.amap_tool import check_delivery_range, PathInputMode

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_prompt_template(prompt_file_name: str) -> str:
    """加载指定提示词文件

    Args:
        prompt_file_name (str): 提示词文件名

    Returns:
        str: 提示词内容
    """
    try:
        # 1.定位到当前文件的路径
        current_file_path = os.path.abspath(__file__)
        current_file_dir = os.path.dirname(current_file_path)
        project_dir = os.path.dirname(current_file_dir)

        # 2.拼接提示词目录
        prompt_path = os.path.join(project_dir, "prompt", f"{prompt_file_name}")

        # 3.读取指定路径下的提示词文件内容
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        return prompt_template.strip()
    except Exception as e:
        logging.error(f"Error loading prompt template: {e}")
        return "无法加载指定的提示词内容，请根据用户的问题，直接给出一个合理的回复。"


@tool
def general_inquiry(query: str, context: str = None) -> str:
    """
    常规问询工具

    处理用户的一般性问题，包括但不限于：
    - 餐厅介绍和服务信息
    - 营业时间和联系方式
    - 优惠活动和会员服务
    - 其他非菜品相关的咨询

    Args:
        query: 用户的询问内容
        context: 可选的上下文信息，用于提供更精准的回复

    Returns:
        str: 针对用户问询的智能回复

    Raises:
        ToolException: 当处理查询时发生错误
    """
    try:
        # 1.加载常规问题提示词
        prompt_template = load_prompt_template("general_inquiry.txt")

        # 从记忆文件中读取历史对话内容（扩展）
        if context:
            full_query = f"当前历史对话内容\n\n{context}\n当前用户问题:\n\n{query}\n请根据上述内容，结合常规问题提示词，给出一个合理的回复。"
        else:
            full_query = (
                f"当前用户问题:\n\n{query}\n请根据常规问题提示词，给出一个合理的回复。"
            )

        # 2.调用llm模型
        llm_response = call_llm(query=full_query, system_instruction=prompt_template)

        # 3.组成想要的数据返回
        return llm_response
        # 3.1将QA写入到记忆组件(扩展)

    except Exception as e:
        logging.error(f"Error in general_inquiry: {e}")
        raise ToolException(f"处理常规问询时发生错误：{e}，请稍后再试。")


@tool
def menu_inquiry(query: str) -> Dict[str, Any]:
    """
    智能菜品咨询工具

    专门处理与菜品相关的所有查询，包括：
    - 菜品介绍和详细信息
    - 价格和营养信息
    - 菜品推荐和搭配建议
    - 过敏原和饮食限制相关问题
    - 菜品可用性和特色介绍

    该工具会自动通过语义搜索找到最相关的菜品信息，然后基于这些信息回答用户问题。

    Args:
        query: 用户关于菜品的具体问题

    Returns:
        Dict[str, Any]: 包含推荐建议和菜品ID的字典
        {
            "recommendation": "基于菜品信息的推荐建议",
            "menu_ids": ["菜品ID1", "菜品ID2"]
        }

    Raises:
        ToolException: 当处理菜品查询时发生错误
    """
    try:
        # 1.加载菜品信息推荐问题的提示词
        prompt_template = load_prompt_template("menu_inquiry.txt")

        # 2.通过 AssistantVectorStore 进行语义检索（使用 smart-order-assistant 索引）
        store = AssistantVectorStore(auto_create_index=False)
        matches = store.semantic_search(query, top_k=5, namespace="dishes") if store.is_ready() else []

        menu_ids: list[str] = []
        if matches:
            context_lines = []
            for m in matches:
                meta = m.get("metadata", {})
                dish_id = meta.get("dish_id") or meta.get("source_id")
                if dish_id:
                    menu_ids.append(str(dish_id))
                line = (
                    f"菜品ID:{dish_id} "
                    f"菜品名:{meta.get('dish_name', '')} "
                    f"价格:{meta.get('price', '')} "
                    f"菜系:{meta.get('cuisine_type', '')} "
                    f"口味:{meta.get('flavor_profile', '')} "
                    f"简介:{meta.get('description', '')}"
                )
                context_lines.append(f"- {line.strip()}")

            menu_contents_context = "\n".join(context_lines)
            full_query = f"基于当前向量数据库中的菜品信息：\n{menu_contents_context}\n用户问题是：{query}\n请根据上述内容，给用户一个合理的回复，并且推荐相关菜品。"
        else:
            full_query = f"暂无相关菜品信息。\n用户问题是：{query}\n请根据上述内容，给出一个合理的回复，并且推荐相关菜品。"

        # 3.调用模型
        llm_response = call_llm(query=full_query, system_instruction=prompt_template)

        # 4.封装字典结构返回
        return {
            "recommendation": llm_response,
            "menu_ids": menu_ids,
        }
    except Exception as e:
        raise ToolException(f"处理菜品查询时发生错误：{e}，请稍后再试。")


@tool
def delivery_check_tool(address: str, travel_mode: PathInputMode = None) -> str:
    """
    配送范围检查工具

    检查指定地址是否在配送范围内，并提供距离信息。

    Args:
        address: 配送地址
        travel_mode: 距离计算方式（1=步行距离，2=骑行距离，3=驾车距离）

    Returns:
        str: 配送检查结果的格式化信息

    Raises:
        ToolException: 当配送检查失败时
    """

    # 说明：不需要调用任何模型，直接根据地址和距离计算方式进行配送范围检查，返回结果即可

    try:
        # 1.调用配送范围查询函数
        check_delivery_range_result = check_delivery_range(address, travel_mode)

        # 2.处理数据直接返回
        if check_delivery_range_result["status"] == "success":
            status_text = "✅ 可以配送" if check_delivery_range_result["in_range"] else "❌ 超出配送范围"

            response = f"""
                配送信息查询结果：
                配送地址：{check_delivery_range_result['formatted_address']}
                配送距离：{check_delivery_range_result['distance']}公里（骑电车车）
                配送状态：{status_text}
                """.strip()

        else:
            response = f"❌ 配送查询失败：{check_delivery_range_result['message']}"

        return response
    except Exception as e:
        raise ToolException(f"配送范围检查失败:{e}")




if __name__ == "__main__":
    # print(general_inquiry(query="你们餐厅几点关门"))

    # print(menu_inquiry(query="推荐几个你们最贵的菜"))
    print(delivery_check_tool.invoke(input={"address": "武汉大学"}))
    pass
