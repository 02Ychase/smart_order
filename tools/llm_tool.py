"""
llm_tool模块

该模块提供了通用的LLM调用
将LLM调用进行统一，在后续调用时只需要调用call_llm即可

"""

import json
import logging
import os
import time
from typing import TypeVar

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

load_dotenv(override=True)

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def _create_chat_model(model_name: str | None = None) -> BaseChatModel:
    model_name = model_name or os.getenv("MODEL_NAME")
    if not model_name:
        raise ValueError("模型配置信息不全")
    return init_chat_model(model=model_name, model_provider="openai")


def _validate_json(raw: str) -> bool:
    """Validate that the string is valid JSON.

    Args:
        raw: The raw string to validate.

    Returns:
        True if the string is valid JSON, False otherwise.
    """
    try:
        json.loads(raw)
        return True
    except json.JSONDecodeError:
        return False


def _strip_thinking_tags(content: str) -> str:
    """Remove thinking tags from LLM response content."""
    import re
    pattern = r'<think>.*?</think>\s*'
    cleaned = re.sub(pattern, '', content, flags=re.DOTALL)
    cleaned = cleaned.strip()
    return cleaned


def _create_repair_prompt(original_response: str, error: str) -> str:
    """Create a prompt to repair malformed JSON.

    Args:
        original_response: The original malformed JSON response.
        error: The error message describing what went wrong.

    Returns:
        A repair prompt string to send back to the LLM.
    """
    return f"""The following response is not valid JSON. Please fix the JSON format.

Original response:
{original_response}

Error: {error}

Please provide the corrected JSON:"""


def call_llm(
    query: str,
    system_instruction: str,
    max_retries: int = 2,
    retry_delay: float = 1.0,
):
    """通用llm处理 with retry mechanism.

    Args:
        query: 用户查询/消息
        system_instruction: 系统提示词
        max_retries: Maximum number of retry attempts (default: 2, meaning 3 total attempts)
        retry_delay: Base delay in seconds between retries (exponential backoff applied)

    Returns:
        The LLM response content as a string.

    Raises:
        ValueError: If model configuration is incomplete.
        Exception: If all retry attempts are exhausted.
    """

    model_name = os.getenv("MODEL_NAME")
    if not model_name:
        raise ValueError("模型配置信息不全")

    is_structured = "json" in system_instruction.lower() or "JSON" in system_instruction

    last_response_content = ""
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            llm = init_chat_model(model=model_name, model_provider="openai")

            chat_prompt_template = ChatPromptTemplate.from_messages(
                [("system", "{system_instruction}"), ("human", "{query}")]
            )
            chain = chat_prompt_template | llm
            response = chain.invoke({
                "system_instruction": system_instruction,
                "query": query,
            })

            content = response.content
            content = _strip_thinking_tags(content)
            last_response_content = content

            if is_structured and not _validate_json(content):
                error_msg = "Invalid JSON format"
                if attempt < max_retries:
                    logger.warning(
                        "JSON validation failed on attempt %d/%d, retrying with repair prompt",
                        attempt + 1,
                        max_retries + 1,
                    )
                    repair_query = _create_repair_prompt(content, error_msg)
                    query = repair_query
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                raise json.JSONDecodeError(error_msg, content, 0)

            return content

        except json.JSONDecodeError as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    "JSON decode error on attempt %d/%d: %s, retrying with repair prompt",
                    attempt + 1,
                    max_retries + 1,
                    e,
                )
                repair_query = _create_repair_prompt(last_response_content, str(e))
                query = repair_query
                time.sleep(retry_delay * (2 ** attempt))
                continue
            raise

        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    "LLM call failed on attempt %d/%d: %s, retrying...",
                    attempt + 1,
                    max_retries + 1,
                    e,
                )
                time.sleep(retry_delay * (2 ** attempt))
                continue
            raise

    # This should never be reached, but just in case
    raise last_exception or RuntimeError("Max retries exceeded")


def call_llm_with_retry(
    query: str,
    system_instruction: str,
    max_retries: int = 2,
) -> str:
    """Wrapper for call_llm with built-in retry logic.

    Convenience function that calls call_llm with retry enabled by default.

    Args:
        query: 用户查询/消息
        system_instruction: 系统提示词
        max_retries: Maximum number of retry attempts (default: 2)

    Returns:
        The LLM response content as a string.
    """
    return call_llm(query, system_instruction, max_retries=max_retries)


def call_llm_with_schema(
    query: str,
    system_instruction: str,
    schema: type[T],
    model_name: str | None = None,
) -> T:
    """通用LLM结构化输出调用。

    使用 LangChain 的 with_structured_output() 将 LLM 输出直接解析为 Pydantic 模型，
    消除手动 JSON 解析的脆弱性。

    Args:
        query: 用户查询/消息
        system_instruction: 系统提示词
        schema: Pydantic 模型类，用于结构化输出
        model_name: 可选模型名称，默认从环境变量 MODEL_NAME 读取

    Returns:
        schema 类型的实例，由 LLM 结构化输出自动填充

    Raises:
        ValueError: 模型配置不完整
        Exception: LLM 调用或结构化解析失败
    """
    if model_name is None:
        model_name = os.getenv("MODEL_NAME")
    if not model_name:
        raise ValueError("MODEL_NAME not configured")

    llm = init_chat_model(model=model_name, model_provider="openai")
    structured_llm = llm.with_structured_output(schema)

    messages = [
        ("system", system_instruction),
        ("human", query),
    ]

    return structured_llm.invoke(messages)


if __name__=="__main__":
    res=call_llm(query="写一首五言诗",system_instruction="你是一个诗人")
    print(res)
    pass