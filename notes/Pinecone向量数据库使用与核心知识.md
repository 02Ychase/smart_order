# Pinecone 向量数据库使用与核心知识

## 1. 文档目的

本文面向当前项目，系统整理 Pinecone 向量数据库的核心概念、常见操作流程、Python SDK 用法，以及在“智能点餐助手”中的落地方式。

当前项目的依赖中已经包含：

```txt
pinecone~=7.3.0
```

这意味着项目当前使用的是 Pinecone Python SDK `v7.x` 这一代接口风格。

## 2. Pinecone 是什么

Pinecone 是一个专门面向向量检索场景的数据库。它主要用于存储向量，并在查询时返回“最相似”的记录。

它特别适合下面这些任务：

- 语义搜索
- 检索增强生成（RAG）
- 推荐系统
- 相似内容匹配
- 图文、文本、音频等嵌入向量检索

在当前点餐项目里，Pinecone 最适合承担的职责是：

- 存储菜品描述、口味、食材、类别等内容的嵌入向量
- 根据用户自然语言查询做语义召回
- 配合 LLM 做菜品推荐

## 3. 先理解几个核心概念

### 3.1 向量

向量本质上是一串数字，例如：

```python
[0.12, -0.03, 0.88, ...]
```

这串数字通常来自 embedding 模型，用来表示文本的语义特征。

例如：

- “想吃辣一点的川菜”
- “推荐重口味下饭菜”

这两句话如果语义相近，转换后的向量通常也会比较接近。

### 3.2 Dense Vector 和 Sparse Vector

Pinecone 支持两种主要向量类型：

- Dense vector
  - 用连续浮点数表示语义
  - 适合语义搜索
  - 当前项目最可能使用这一类
- Sparse vector
  - 更强调关键词、词项权重
  - 适合词法搜索

如果你的目标是“用户自然语言问菜品，系统按语义召回”，通常优先使用 dense index。

### 3.3 Index

Index 可以理解为 Pinecone 中的“向量表”或“向量集合”。

所有向量数据都要存进某个 index。

创建 index 时最关键的几个参数是：

- `name`
- `vector_type`
- `dimension`
- `metric`
- `cloud`
- `region`

### 3.4 Dimension

`dimension` 是向量维度，必须和你使用的 embedding 模型输出维度严格一致。

例如：

- 模型输出 1536 维
- 那么 Pinecone index 也必须配置成 1536

如果维度不一致，写入或查询都会失败。

### 3.5 Metric

Pinecone 在 dense index 中常见的相似度度量有：

- `cosine`
- `euclidean`
- `dotproduct`

实践里最常见的是 `cosine`。  
原则是：尽量与 embedding 模型训练时使用的相似度度量保持一致。

### 3.6 Record

Pinecone 里的一条数据通常包含：

- `id`
- `values` 或 `sparse_values`
- `metadata`

例如一条菜品记录可以是：

```python
{
    "id": "dish-1001",
    "values": [...],
    "metadata": {
        "dish_name": "宫保鸡丁",
        "category": "川菜",
        "spice_level": 2,
        "is_vegetarian": False,
        "is_available": True
    }
}
```

### 3.7 Namespace

Namespace 是 index 内部的逻辑分区。

你可以把它理解为：

- 同一个 index 下的“子空间”
- 用于隔离不同业务、不同租户、不同环境的数据

例如：

- `menu-dev`
- `menu-prod`
- `tenant-a`
- `tenant-b`

Pinecone 的官方说明里，namespace 也是实现多租户隔离的关键手段。

## 4. 两种主要工作模式

### 4.1 模式 A：Bring Your Own Vectors

这是最常见、也最适合当前项目的方式。

流程是：

1. 你自己用外部 embedding 模型把文本转成向量
2. 把向量写入 Pinecone
3. 查询时也先把用户问题转成向量
4. 再调用 Pinecone 做相似检索

优点：

- 更灵活
- 可以自由选择 OpenAI、通义千问、BGE 等 embedding 模型
- 更适合和现有 LLM/Embedding 链路集成

### 4.2 模式 B：Integrated Embedding

Pinecone 也支持“索引内置 embedding 模型”的模式。

这种模式下：

- 写入时直接传文本
- 查询时也可以直接传文本
- Pinecone 自动帮你做 embedding

优点：

- 开发路径更短
- 原型验证速度快

局限：

- 绑定 Pinecone 托管模型
- 某些操作有额外限制
- 对已有 embedding 体系的项目不一定是最优解

对于当前项目，如果后续已有固定 embedding 模型，通常优先采用 Bring Your Own Vectors。

## 5. Python SDK 安装与版本

### 5.1 基础安装

```bash
pip install pinecone
```

### 5.2 如果想要更好的数据面性能

```bash
pip install "pinecone[grpc]"
```

### 5.3 如果要配合 FastAPI 做异步

```bash
pip install "pinecone[asyncio]"
```

### 5.4 当前项目的版本含义

根据 Pinecone 官方 SDK 文档，Python SDK `v7.x` 对应 Pinecone API `2025-04` 这一代。

当前项目依赖：

```txt
pinecone~=7.3.0
```

所以文档里的示例可以按 v7.x 风格理解。

## 6. 典型使用流程

Pinecone 的使用一般分为 6 步：

1. 准备 API Key
2. 创建 index
3. 获取 index host
4. 初始化 index 客户端
5. 写入向量
6. 查询、更新、删除、统计

## 7. 创建一个 Dense Index

如果你使用外部 embedding 模型，最常见的是创建一个 dense index。

示例：

```python
import os
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec


pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

index_name = "smart-order-menu"

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        vector_type="dense",
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1",
        ),
        deletion_protection="disabled",
        tags={"project": "smart-order"},
    )
```

注意事项：

- `dimension` 必须和 embedding 模型一致
- `metric` 要和模型匹配
- `cloud` 和 `region` 创建后不能随便改

## 8. 为什么官方建议用 host 访问 index

Pinecone 把“控制面”和“数据面”区分得很明确。

如果你每次通过 index 名称去读写数据，SDK 往往要先调用 `describe_index` 再找到 host，这会多一次网络请求。

所以官方建议：

- 测试阶段：可以按 index name 使用
- 生产阶段：应缓存并直接使用 `host`

因此，推荐你把 `PINECONE_INDEX_HOST` 放到环境变量中。

示例：

```python
import os
from pinecone.grpc import PineconeGRPC as Pinecone


pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
index = pc.Index(host=os.environ["PINECONE_INDEX_HOST"])
```

## 9. 写入数据：Upsert

### 9.1 Upsert 是什么

`upsert` = insert + update。

它的语义是：

- 如果 `id` 不存在，就插入
- 如果 `id` 已存在，就覆盖整条记录

这点很重要：

- 如果只是改部分字段，优先考虑 `update`
- 如果整条数据重新生成，使用 `upsert`

### 9.2 菜品向量写入示例

```python
records = [
    {
        "id": "dish-1001",
        "values": [0.12, -0.08, 0.44, 0.91],
        "metadata": {
            "dish_name": "宫保鸡丁",
            "category": "川菜",
            "price": 32.0,
            "spice_level": 2,
            "flavor": "香辣",
            "is_vegetarian": False,
            "is_available": True,
        },
    },
    {
        "id": "dish-1002",
        "values": [0.22, -0.18, 0.31, 0.76],
        "metadata": {
            "dish_name": "麻婆豆腐",
            "category": "川菜",
            "price": 26.0,
            "spice_level": 3,
            "flavor": "麻辣",
            "is_vegetarian": True,
            "is_available": True,
        },
    },
]

index.upsert(vectors=records, namespace="menu-prod")
```

### 9.3 批量写入建议

官方建议：

- 向量 upsert 一次请求尽量做批量
- 单批次不要超过 2 MB
- 单次最多 1000 条向量记录

如果是集成 embedding 的文本 upsert，单批次还有更小的模型侧限制。

如果数据规模达到千万级，官方建议考虑 `import`，不要只靠 `upsert`。

## 10. 查询数据：Query / Search

### 10.1 Bring Your Own Vectors 场景

这种情况下你先自己拿到查询向量，再调用 Pinecone：

```python
query_vector = [0.15, -0.05, 0.49, 0.88]

result = index.query(
    namespace="menu-prod",
    vector=query_vector,
    top_k=5,
    include_metadata=True,
    include_values=False,
)
```

典型返回结果里会包含：

- 命中的 `id`
- 相似度分数
- `metadata`

### 10.2 加过滤条件的查询

在点餐项目里，最常见的过滤条件包括：

- 只查可售卖菜品
- 限定某个分类
- 限定辣度
- 过滤素食

示例：

```python
result = index.query(
    namespace="menu-prod",
    vector=query_vector,
    top_k=5,
    include_metadata=True,
    include_values=False,
    filter={
        "$and": [
            {"is_available": {"$eq": True}},
            {"category": {"$eq": "川菜"}},
            {"spice_level": {"$gte": 2}},
        ]
    },
)
```

### 10.3 常用过滤操作符

Pinecone 官方过滤语言常见操作符包括：

- `$eq`
- `$ne`
- `$gt`
- `$gte`
- `$lt`
- `$lte`
- `$in`
- `$nin`
- `$exists`
- `$and`
- `$or`

经验上：

- 精确匹配布尔或分类字段时用 `$eq`
- 数值范围用 `$gte`、`$lte`
- 多条件组合优先用 `$and`

## 11. 获取原始记录：Fetch

如果你已经知道记录 ID，最适合用 `fetch`。

```python
result = index.fetch(
    ids=["dish-1001", "dish-1002"],
    namespace="menu-prod",
)
```

适用场景：

- 根据召回结果回查完整记录
- 调试某条记录有没有写进去
- 验证更新是否生效

官方也提示了一点：

- 在按需型 serverless index 中，`fetch` 取向量值可能比只查 metadata 更慢
- 如果只需要 metadata，可以考虑 `query(..., include_values=False)`

## 12. 更新已有记录：Update

### 12.1 更新单条记录

如果你只改元数据的一部分，或者要替换某条向量值，可以使用 `update`。

```python
index.update(
    namespace="menu-prod",
    id="dish-1001",
    set_metadata={
        "price": 35.0,
        "is_available": False,
    },
)
```

如果要更新 dense vector 的值，也可以传 `values=[...]`，但向量长度必须与原记录一致。

### 12.2 更新与 Upsert 的区别

- `upsert`
  - 更像整条覆盖
  - 同一个 `id` 会覆盖整条记录
- `update`
  - 更像局部修改
  - 更适合变更部分 metadata

### 12.3 批量按 metadata 更新

官方支持基于 metadata filter 批量更新 metadata，但不能通过这种方式批量更新向量值。

这个能力更适合：

- 全量给某一批记录补标签
- 批量修正 metadata 字段

## 13. 删除数据：Delete

### 13.1 按 ID 删除

```python
index.delete(
    ids=["dish-1001"],
    namespace="menu-prod",
)
```

这是删除指定记录最直接、最有效率的方式。

### 13.2 按 metadata 删除

```python
index.delete(
    filter={"category": {"$eq": "临时测试分类"}},
    namespace="menu-prod",
)
```

### 13.3 删除整个 namespace 内的全部记录

```python
index.delete(
    delete_all=True,
    namespace="menu-prod",
)
```

注意：

- `delete_all=True` 删除的是 namespace 内的全部记录
- 不等于删掉整个 index

## 14. Namespace 的正确用法

### 14.1 Namespace 的价值

Namespace 适合做：

- 多租户隔离
- 开发、测试、生产环境隔离
- 业务场景隔离

### 14.2 Namespace 的创建方式

Pinecone 官方说明里，namespace 可以在 upsert 时自动创建。

也就是说：

- 你第一次往 `menu-prod` 写数据
- 如果它不存在，Pinecone 会自动创建

### 14.3 一个重要限制

单次普通 query 是针对单个 namespace 的。  
如果要跨多个 namespace 查询，需要自己合并结果，或者使用 SDK 提供的辅助能力。

所以在设计时不要把需要联合查询的数据切得过碎。

## 15. 集成 Embedding 的用法

如果你不想自己管理 embedding 模型，可以走集成 embedding 路线。

### 15.1 创建带集成 embedding 的 index

```python
import os
from pinecone import Pinecone


pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

pc.create_index_for_model(
    name="smart-order-integrated",
    cloud="aws",
    region="us-east-1",
    embed={
        "model": "llama-text-embed-v2",
        "field_map": {"text": "dish_text"},
    },
)
```

### 15.2 直接 upsert 文本

```python
index = pc.Index(host=os.environ["PINECONE_INDEX_HOST"])

index.upsert_records(
    "menu-prod",
    [
        {
            "_id": "dish-1001",
            "dish_text": "宫保鸡丁，川菜，鸡肉，花生，口味香辣，下饭。",
            "category": "川菜",
            "is_available": True,
        }
    ],
)
```

### 15.3 直接用文本查询

```python
result = index.search(
    namespace="menu-prod",
    query={
        "inputs": {"text": "推荐一个下饭的微辣川菜"},
        "top_k": 5,
        "filter": {"is_available": True},
    },
    fields=["category", "dish_text"],
)
```

### 15.4 集成 embedding 的注意点

官方说明里需要特别注意：

- 文本 upsert / 文本 search 只适用于带集成 embedding 的 index
- 带集成 embedding 的 index，对“基于文本的 update / import”存在限制

因此，生产项目要先确定是：

- 让 Pinecone 负责 embedding
- 还是你自己统一负责 embedding

## 16. 数据新鲜度与最终一致性

Pinecone 不是“强一致立刻可见”的思路，而是最终一致性。

这意味着：

- 你刚 upsert / update / delete 完
- 立即查询时，可能会有一个很短的延迟
- 结果不一定瞬间反映最新状态

官方建议可以通过 `describe_index_stats()` 等方式检查数据状态。

```python
stats = index.describe_index_stats()
print(stats)
```

在调试时，如果你发现：

- 明明写入成功
- 查询却暂时没结果

先不要急着怀疑代码，优先考虑最终一致性的短暂延迟。

## 17. Pinecone 在当前点餐项目中的落地设计建议

### 17.1 推荐存什么

最适合做 embedding 的字段通常不是单个字段，而是一个组合文本。

例如可以把一条菜品拼成：

```text
菜品名称：宫保鸡丁
分类：川菜
描述：鸡肉配花生，酸甜微辣，下饭
口味：香辣
主要食材：鸡肉、花生、葱
辣度：中辣
是否素食：否
过敏原：花生
```

再把这段文本送入 embedding 模型，得到向量后写入 Pinecone。

### 17.2 推荐保存哪些 metadata

建议 metadata 放“搜索过滤和展示真正需要”的字段：

- `dish_name`
- `category`
- `price`
- `spice_level`
- `flavor`
- `is_vegetarian`
- `is_available`
- `allergens`

### 17.3 一条合理的数据结构

```python
{
    "id": "dish-1001",
    "values": [...],
    "metadata": {
        "dish_name": "宫保鸡丁",
        "category": "川菜",
        "price": 32.0,
        "spice_level": 2,
        "flavor": "香辣",
        "is_vegetarian": False,
        "is_available": True,
        "allergens": "花生"
    }
}
```

### 17.4 检索链路

在当前项目里，一条典型查询链路应该是：

1. 用户输入自然语言需求
2. 用 embedding 模型把用户问题转成向量
3. 用 Pinecone 做 `query`
4. 结合 metadata 过滤无效菜品
5. 把召回结果交给 LLM 做最终组织和推荐

## 18. 什么时候适合用 Pinecone，什么时候不适合

### 18.1 适合

- 菜品描述很多，想做语义检索
- 用户问题自由度高
- 需要“相似菜品”或“推荐”能力
- 后续可能扩展到 RAG

### 18.2 不适合只用 Pinecone

如果你只是：

- 按菜名精确查询
- 按价格排序
- 按分类分页展示

那么仅靠 MySQL 就足够。  
Pinecone 的价值不在传统结构化查询，而在语义召回。

更合理的组合通常是：

- MySQL 负责结构化数据和事务
- Pinecone 负责语义检索

## 19. 常见坑

### 19.1 维度不一致

最常见错误之一。

例如：

- index 是 1536 维
- 你写入的是 1024 维向量

这种一定会失败。

### 19.2 把太多无用字段塞进 metadata

metadata 不是越多越好。

官方文档明确提到：

- 过多 metadata 可能拖慢索引构建
- 也可能拖慢查询

所以建议只存：

- 要展示的字段
- 要过滤的字段

### 19.3 没有区分 upsert 和 update

如果你只是改价格、上下架状态，不一定要整条 upsert。  
如果整条文本和向量都重算了，再 upsert 更合适。

### 19.4 生产环境还按 index name 每次查 host

开发时问题不大，生产时会多一次控制面调用。  
更稳妥的方式是直接缓存 `host`。

### 19.5 忽略最终一致性

刚写完马上查不到，不一定是写入失败，也可能只是数据还没完全可见。

## 20. 推荐的项目级环境变量

建议给当前项目统一配置：

```env
PINECONE_API_KEY=xxx
PINECONE_INDEX_NAME=smart-order-menu
PINECONE_INDEX_HOST=xxx.svc.xxx.pinecone.io
PINECONE_NAMESPACE=menu-prod
```

如果后续按环境隔离，还可以增加：

```env
APP_ENV=dev
```

## 21. 一个适合当前项目的最小模板

```python
import os
from pinecone.grpc import PineconeGRPC as Pinecone


def get_pinecone_index():
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    return pc.Index(host=os.environ["PINECONE_INDEX_HOST"])


def query_menu_by_vector(query_vector, top_k=5):
    index = get_pinecone_index()
    return index.query(
        namespace=os.getenv("PINECONE_NAMESPACE", "menu-prod"),
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        include_values=False,
        filter={"is_available": {"$eq": True}},
    )
```

## 22. 核心记忆点

把 Pinecone 压缩成最重要的几点，就是：

1. Pinecone 负责“向量相似检索”，不是替代 MySQL 的通用数据库
2. 创建 index 时最重要的是 `vector_type`、`dimension`、`metric`
3. `dimension` 必须和 embedding 模型输出完全一致
4. 生产环境优先通过 `host` 访问 index
5. `upsert` 会覆盖整条记录，局部改动用 `update`
6. `namespace` 是隔离数据的重要手段
7. metadata 是过滤和展示的关键，但不要滥存
8. Pinecone 是最终一致性，写入后可能有短暂延迟
9. 当前点餐项目最适合用 dense index + 外部 embedding
10. MySQL 管结构化数据，Pinecone 管语义检索，两者配合最合理

## 23. 官方资料

以下是本文整理时参考的 Pinecone 官方文档：

- Pinecone Python SDK: https://docs.pinecone.io/reference/sdks/python/overview
- Create an index: https://docs.pinecone.io/guides/index-data/create-an-index
- Target an index: https://docs.pinecone.io/guides/manage-data/target-an-index
- Upsert records: https://docs.pinecone.io/guides/index-data/upsert-data
- Semantic search: https://docs.pinecone.io/guides/search/semantic-search
- Filter by metadata: https://docs.pinecone.io/guides/search/filter-by-metadata
- Manage namespaces: https://docs.pinecone.io/guides/manage-data/manage-namespaces
- Update records: https://docs.pinecone.io/guides/manage-data/update-data
- Delete records: https://docs.pinecone.io/guides/manage-data/delete-data
- Check data freshness: https://docs.pinecone.io/guides/index-data/check-data-freshness
