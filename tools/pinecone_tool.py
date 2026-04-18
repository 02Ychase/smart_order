"""
Pinecone向量数据库工具模块

💡
该模块提供Pinecone向量数据库的连接和操作功能，
用于存储和查询菜品信息的向量数据，支持语义搜索

"""

from dotenv import load_dotenv
import os
from pinecone import Pinecone, ServerlessSpec
from typing import List,Dict,Any
import dashscope
import logging
from http import HTTPStatus
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tools.db_tool import get_all_menu_items


logging.basicConfig(
    level=logging.INFO,
    encoding="utf-8",
)
logger = logging.getLogger(__name__)


load_dotenv()


class PineconeVectorDB:
    """Pinecone向量数据库的操作"""

    def __init__(self):
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        self.pinecone_env = os.getenv("PINECONE_ENY")

        # 定义索引名称，embedding模型名称，维度
        self.index_name = "menu-items-index"
        self.embedding_model = "text-embedding-v4"
        self.dimension = 1536

        # 配置pinecone客户端对象和索引对象
        self.pc = None
        self.index = None

    def initialize_connection(self) -> bool:
        # 初始化pinecone客户端
        # 初始化索引
        try:
            if not self.pinecone_api_key:
                logger.error("Pinecone api_key 不存在")
                return False
            # 初始化创建pinecone客户端对象
            self.pc = Pinecone(api_key=self.pinecone_api_key)

            # 初始化索引对象
            if not self.pc.has_index(self.index_name):
                self.pc.create_index(
                    name=self.index_name,
                    vector_type="dense",
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=self.pinecone_env),
                )
            self.index = self.pc.Index(self.index_name)

            logger.info("初始化Pinecone客户端和Index成功")

            return True
        except Exception as e:
            logger.error(f"初始化Pinecone客户端对象失败{e}")
            return False

    def clear_index_vector(self) -> True:
        """清空指定索引下的向量数据"""
        try:
            if self.index is None:
                logger.error("索引对象不存在")
                return False
            # 获取索引中向量数据的个数
            index_status = self.index.describe_index_stats()
            count = index_status["total_vector_count"]
            if count == 0:
                logger.info("该索引下不存在任何数据")
                return True
            else:
                self.index.delete(delete_all=True)
                logger.info("成功删除该索引下所有数据")
                return True
        except Exception as e:
            logger.error(f"删除该索引下数据失败:{e}")
            return False

    def _embedding_content(self, content: str) -> List[float]:
        """对文本进行向量化

        Args:
            content (str): 文本

        Returns:
            List[float]: 嵌入向量
        """
        # 使用dashscope的embedding模型
        try:
            # 发送请求
            resp = dashscope.TextEmbedding.call(
                model=self.embedding_model,
                input=content,
                dimension=self.dimension,
                api_key=self.dashscope_api_key,
            )

            # 解析结果
            # 如果正常获取响应
            if resp["status_code"] == HTTPStatus.OK:
                logger.info(f"文本:{content},向量化成功")
                return resp.get("output").get("embeddings")[0].get("embedding")
            else:
                logger.error("发送文本嵌入模型请求失败")
                return None
        except Exception as e:
            logger.error(f"发送文本嵌入模型请求失败:{e}")
            return None

    def _validate_datasourc(self, validation_content: str) -> bool:
        """用于校验获取的菜单字符串是否合法

        Args:
            validation_content (str): 菜单字符串
        """
        if not validation_content:
            logger.error("数据源不存在")
            return False

        validation_result_str = ("当前无可用菜品信息", "查询所有菜品信息失败")

        if validation_content.startswith(validation_result_str):
            return False
        else:
            return True

    def _split_content(self, content: str) -> List[str]:
        try:
            # 定义文本切分器(递归文本切分器RecursiveCharacterTextSplitter)
            text_spliter = RecursiveCharacterTextSplitter(
                chunk_size=100, chunk_overlap=0, separators=["\n"], length_function=len
            )

            # 切分
            docs = text_spliter.create_documents([content])

            # 处理切分后的文档列表
            clearned_docs = []
            for doc in docs:
                # 提取文档内容
                page_content = doc.page_content
                # 进一步清洗
                clearned_content = page_content.strip()
                clearned_docs.append(clearned_content)
            logger.info(f"菜单信息切分后的chunk数量:{len(clearned_docs)}")
            return clearned_docs
        except Exception as e:
            logger.error(f"菜单信息切分失败:{e}")
            return []

    def upsert_menu_data(
        self, menu_data: str = None, batch_size: int = 30, clear_existing: bool = False
    ) -> bool:
        """将文本向量存储到向量数据库中

        Args:
            menu_data (str): 菜品信息
            batch_size (int, optional): batch_size，攒够一批向量数据插入到向量数据库中. Defaults to 30.
            clear_existing (bool, optional): 是否清空原有index下数据. Defaults to True.
        """
        try:
            # # 清空现有index中的数据
            if clear_existing:
                self.clear_index_vector()

            if  menu_data is None:       
                # 获取菜单数据
                menu_data = get_all_menu_items()
                # 校验
                if self._validate_datasourc(menu_data) == False:
                    logger.error("数据校验失败，不能继续向量化")
                    return False


            # 对数据进行切分
            splited_menu_str = self._split_content(menu_data)
            if not splited_menu_str:
                logger.error("数据切分失败，不进行向量化")
                return False

            batch = []
            # 对切分后的str进行向量化
            for line_num, chunk in enumerate(splited_menu_str):
                # 获取向量化后的向量
                embeddinged_chunk = self._embedding_content(content=chunk)
                # 如果不是一个向量或者向量维度不匹配
                if (
                    not embeddinged_chunk
                    or len(embeddinged_chunk) != self.dimension
                ):
                    logger.error("向量值不存在或者维度不匹配")
                    return False

                # 将向量插入到向量数据库中
                if self.index is None:
                    logger.error("索引不存在")
                    return False

                # 准备元数据metadata
                menu_metadata = {
                    "content": chunk,  # 原始文本内容
                    "line_num": line_num,
                    "type": "menu_item",
                }

                # 准备向量数据库的唯一标识
                vector_id = f"{line_num}"

                batch.append((vector_id, embeddinged_chunk, menu_metadata))

                # 大于batch_size阈值，可以插入
                if len(batch) > batch_size:
                    self.index.upsert(vectors=batch)
                    # batch清空
                    batch = []

            if batch:
                self.index.upsert(vectors=batch)

            logger.info("切分后的文本内容成功存储到向量数据库中")
            return True
            # else:
            #     logger.info(f"处理文本数据:{menu_data}")
            #     embedding_menu_data=self._embedding_content(content=menu_data)
            #     if (not embedding_menu_data or len(embedding_menu_data) != self.dimension):
            #         logger.error("向量值不存在或者维度不匹配")
            #         return False
            #     menu_metadata={
            #         "content":menu_data,
            #         "type":"menu_item"
            #     }
                
        except Exception as e:
            logger.error(f"插入到向量数据库失败:{e}")
            return False

    def search_similarity_menu_item(self, query: str, top_k: int = 5):
        """相似性检索

        Args:
            query (str): query查询
            topk (int, optional): topk. Defaults to 5.
        """
        try:
            if self.index is None:
                logger.error("索引不存在请先创建索引")
                return []
            # 将query进行向量化
            query_vector = self._embedding_content(content=query)
            # 判断获取到的向量是否合法 可能返回None或者维度不匹配
            if not query_vector or len(query_vector) != self.dimension:
                logger.error("向量不存在或者维度不匹配")
                return []

            # 执行语义搜索
            similar_result = self.index.query(
                vector=query_vector, top_k=top_k, include_metadata=True
            )

            # 提取结果
            matches_result = similar_result["matches"]

            if not matches_result:
                logger.error("暂无查询到相似性结果")
                return []
            final_matches_result = []
            for item in matches_result:
                match_item = {
                    "id": item["id"],
                    "score": item["score"],
                    "content": item["metadata"]["content"],  # 原始文本
                    "line_number": item["metadata"]["line_num"],
                }
                final_matches_result.append(match_item)

            logger.info(f"查询到相似性结果个数为{len(final_matches_result)}")
            return final_matches_result

        except Exception as e:
            logger.error(f"相似性文档检索失败:{e}")
            return []

pinecone_db = PineconeVectorDB()
pinecone_db.initialize_connection()


# 定义全局同步向量数据库操作方法
def pinecone_input(menu_data: str = None, clear_existing: bool = True) -> bool:
    """
    将数据库的菜品数据输入到Pinecone向量数据库
    
    Args:
        menu_data: 菜品数据字符串，每行一个菜品的完整信息。如果为None，则从数据库获取
        clear_existing: 是否在插入前清除现有数据，默认为True
        
    Returns:
        bool: 是否输入成功
    """
    return pinecone_db.upsert_menu_data(menu_data, clear_existing=clear_existing)


# 定义全局查询向量数据库操作方法
def search_menu_items(query: str, top_k: int = 3):
    """
    根据查询搜索相关菜品
    
    Args:
        query: 查询文本
        top_k: 返回结果数量
        
    Returns:相关菜品信息列表
    """
    results = pinecone_db.search_similarity_menu_item(query, top_k)

    return [item["content"] for item in results]



def search_menu_items_with_id(query: str, top_k: int = 2) -> Dict[str, Any]:
    """
     根据查询文本搜索相似的菜品
    Args:
        query: str: 查询文本
        top_k: int: 返回的结果数量

    Returns:
        Dict[str,Any]:包含菜品内容列表和真实菜品ID列表的字典
        {
            "contents": [菜品内容列表],
            "ids": [真实菜品ID列表],
            "scores": [相似度分数列表]
        }
    """

    try:
        import re

        #  1. 查询相似性菜品信息
        similar_result = pinecone_db.search_similarity_menu_item(query=query, top_k=top_k)

        if not similar_result:
            return {}

        # 2. 处理相似性检索结果
        item_ids = []
        for item in similar_result:
            content = item['content']
            match = re.search(r'菜品ID:(\d+)', content)
            if match:
                item_ids.append(match.group(1))
            else:
                item_ids.append(item["id"])

        # 3. 返回结果
        return {
            "contents": [item['content'] for item in similar_result],
            "ids": item_ids,
            "scores": [item['score'] for item in similar_result]
        }
    except Exception as e:
        logger.error(f"查询相似性菜品信息带id失败: {e}")
        return {}



if __name__ == "__main__":
    #     pinecone_db=PineconeVectorDB()

    # result = pinecone_db.search_similarity_menu_item(
    #     query="请给我推荐川菜系列的菜品", top_k=10
    # )

    # for item in result:
    #     print(item["content"])
    result=search_menu_items_with_id(query="帮我推荐素食",top_k=3)

    print(result['contents'])
    print(result['ids'])
