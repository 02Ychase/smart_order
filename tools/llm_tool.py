"""
llm_tool模块

该模块提供了通用的LLM调用
将LLM调用进行统一，在后续调用时只需要调用call_llm即可

"""

import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

load_dotenv(override=True)


def call_llm(query: str, system_instruction: str):
    """通用llm处理

    Args:
        query (str): 问题
        system_instruction (str): 某个业务对应的提示词是什么
    """

    # 1. 定义模型实例
    model_name = os.getenv("MODEL_NAME")
    if not model_name:
        raise ValueError("模型配置信息不全")

    llm = init_chat_model(model=model_name, model_provider="openai")

    # 2. 定义提示词模板对象
    # role:AI/Human/System
    chat_prompt_template = ChatPromptTemplate.from_messages(
        [("system", "{system_instruction}"), ("human", "{query}")]
    )

    # 3.定义链(chain) --->通过LCEL语法构建  |
    chain = chat_prompt_template | llm

    # 4. 执行链invoke:先去调用chat_prompt_template组件的invoke()方法结果返回格式化后的模板（变量已经被赋值了），再把结果给llm组件
    response = chain.invoke({
        "system_instruction":system_instruction,
        "query":query
    })

    return response.content


if __name__=="__main__":
    res=call_llm(query="写一首五言诗",system_instruction="你是一个诗人")
    print(res)
    pass