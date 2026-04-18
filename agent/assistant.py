"""
智能点餐助手主程序
LangChain中Agent组件的作用：根据用户的意图选择合适的工具，调用工具。
该程序构建了一个包含工具选择功能的LLM系统（相当于LangChain中的Agent角色），能够：
1. 自动选择合适的工具（常规咨询、菜品推荐、配送范围检查）
2. 调用相应工具并返回结果
3. 提供自然、友好的对话体验
"""

import time
from typing import Any, Dict
from tools.llm_tool import call_llm
from agent.mcp import general_inquiry, menu_inquiry, delivery_check_tool
import json
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SmartRestaurantAssistant:
    def __init__(self):
        # 给agent封装工具，tools需要封装工具的名字（函数名）和工具的对象（函数对象）
        self.tools = {
            "general_inquiry": general_inquiry,
            "menu_inquiry": menu_inquiry,
            "delivery_check_tool": delivery_check_tool,
        }

        self.instruction = """你是一个智能餐厅助手的意图分析器。
        请分析用户问题意图，并且选择最合适的工具来处理：

        工具说明：
        1. general_inquiry: 处理餐厅常规咨询（营业时间、地址、电话、优惠活动、预约等）
        2. menu_inquiry: 处理智能菜品推荐和咨询（推荐菜品、介绍菜品、询问菜品信息、点餐等）
        3. delivery_check_tool: 处理配送范围检查（查询某个地址是否在配送范围内、能否送达等）

        你必须严格按照以下JSON格式返回，不要包含任何其他文字：
        {
            "tool_name": "工具名称",
            "format_query": "处理后的用户问题"
        }

        正确示例：
        用户："你们几点营业？" -> {"tool_name": "general_inquiry", "format_query": "营业时间"}
        用户："推荐川菜系列的菜品" -> {"tool_name": "menu_inquiry", "format_query": "推荐川菜"}
        用户："能送到武汉大学吗？" -> {"tool_name": "delivery_check_tool", "format_query": "武汉大学"}

        重要规则：
        - 只返回纯JSON，不要有任何额外字符和解释
        - 确保JSON格式完全正确
        - tool_name必须是以下之一：general_inquiry, menu_inquiry, delivery_check_tool
        - format_query要简洁明了地概括用户问题

        记住：如果你错误的选择工具，你将收到惩罚，系统将会出现崩溃。
        """

        self.max_retries = 3  # 最大重试次数

        self.backoff = 1  # 重试间隔

    def _analyze_intention(self, user_query: str, last_exception: Exception = None):
        """分析用户意图

        Args:
            user_query (str): 用户问题
        """

        # 判断是否有错误
        instruction = self.instruction
        if last_exception:
            instruction += f"\n\n上次解析失败，错误信息：{last_exception}。请根据这个错误信息，调整你的输出，确保返回的JSON格式正确，并且工具名称必须是指定的三个工具之一。"

        # 1.调用llm模型分析用户意图，选择工具：返回的应该是json格式的字符串
        llm_response_str = call_llm(query=user_query, system_instruction=instruction)

        # 清洗模型输出的结果
        cleaned_response_str = self._clean_llm_response(llm_response_str)

        # 2.解析模型的结果，反序列化成json
        llm_response_json = json.loads(cleaned_response_str)

        # 3.返回结果
        return llm_response_json

    def _clean_llm_response(self, llm_response_str: str):
        """清洗llm的结果

        Args:
            llm_response_str (str): llm的原始输出结果字符串
        """
        try:
            # 1.处理markdown格式的字符串，去掉markdown语法
            if llm_response_str.startswith("```") or llm_response_str.endswith("```"):
                cleaned_response = llm_response_str.replace("```", "").strip()

            # 2. 处理json嵌套（有效json）的位置
            start_index = llm_response_str.find("{")
            end_index = llm_response_str.rfind("}")

            # 3.获取有效的json
            if start_index != -1 and end_index != -1 and end_index > start_index:
                cleaned_response = llm_response_str[start_index : end_index + 1]

            return cleaned_response
        except Exception as e:
            raise ValueError(f"{llm_response_str}不是有效的JSON格式字符串: {e}")

    def _analyse_intention_fallback(self, user_query: str):
        """降级处理用户意图分析，基于关键字列表的规则，手动封装工具结构信息
        1.列表匹配
        2.正则匹配
        3.语义匹配（嵌入模型）
        4.LLM进行相似性匹配



        Args:
            user_query (str): 用户问题
        """
        logging.info("使用兜底意图分析")

        # 配送相关关键词
        delivery_keywords = ['配送', '送达', '送到', '送货', '外卖', '地址', '区域', '范围']
        # 菜单相关关键词
        menu_keywords = ['菜单', '菜品', '推荐', '点餐', '招牌', '特色', '什么好吃', '有什么菜']
        # 常规咨询关键词
        general_keywords = ['营业', '时间', '电话', '预约', '预订', '位置', '在哪', '多少钱', '优惠', '活动']

        # 检查配送意图
        if any(keyword in user_query for keyword in delivery_keywords):

            return {"tool_name": "delivery_check_tool", "format_query": user_query}

        # 检查菜单意图
        elif any(keyword in user_query for keyword in menu_keywords):
            return {"tool_name": "menu_inquiry", "format_query": user_query}

        # 默认常规咨询
        else:
            return {"tool_name": "general_inquiry", "format_query": user_query}



    def analyse_intention_with_retry(self, user_query: str):


        # 1.重试
        last_exception = None
        for i in range(self.max_retries):  # 0,1,2
            try:
                llm_response_json = self._analyze_intention(user_query, last_exception)
                logging.info(f"第{i + 1}次分析用户意图成功")
                return llm_response_json
            except (ValueError, json.JSONDecodeError) as e:
                last_exception = e
                logging.warning(f"第{i + 1}次分析用户意图失败，错误信息：{e}")

                if i<self.max_retries-1:
                    time.sleep(self.backoff)

        logging.error(f"重试次数已经达到了最大：{self.max_retries}")

        # 2.降级处理
        return self._analyse_intention_fallback(user_query)

    def execute_tool(self, tool_name: str, tool_params: str):
        """执行工具

        Args:
            tool_name (str): 工具名称
            tool_params (str): 工具参数
        """
        try:
            # 1.判断工具是否存在
            if self.tools.get(tool_name) is None:
                raise ValueError(f"工具{tool_name}不存在")

            # 2.调用工具
            # 2.1 常规问题咨询工具
            if tool_name == "general_inquiry":
                tool = self.tools.get("general_inquiry")
                tool_result = tool.invoke({"query": tool_params})
            # 2.2 菜品推荐工具
            elif tool_name == "menu_inquiry":
                tool = self.tools.get("menu_inquiry")
                tool_result = tool.invoke({"query": tool_params})
            # 2.3 配送范围检查工具
            else:
                tool = self.tools.get("delivery_check_tool")
                tool_result = tool.invoke(input={"address": tool_params})
            return tool_result
        except Exception as e:
            raise Exception(f"执行工具{tool_name}时发生错误：{e}")

    def invoke(self, user_query: str):
        """和小助手agent聊天

        Args:
            user_query (str): 问题
        """
        # 1.分析用户的意图（找工具）
        structured_tool = self._analyze_intention(user_query=user_query)

        # 1.1 获取工具名称
        tool_name = structured_tool.get("tool_name")

        # 1.2 获取工具参数
        tool_params = structured_tool.get("format_query")

        # 2.调用工具
        tools_result = self.execute_tool(tool_name=tool_name, tool_params=tool_params)

        # 3.返回工具结果
        return tools_result


# 全局方法(给service调用)
def chat_with_assistant(user_query: str):
    """和智能小助手对话"""
    try:
        # 1.实例化
        assistant = SmartRestaurantAssistant()

        # 2.调用聊天chat方法
        assistant_response = assistant.invoke(user_query)

        print(f"助手的回复:\n{assistant_response}")

        return assistant_response
    except Exception as e:
        raise Exception(f"和智能小助手对话时发生错误：{e}")
    


if __name__ == "__main__":
    chat_with_assistant("你们餐厅的联系电话时多少")
