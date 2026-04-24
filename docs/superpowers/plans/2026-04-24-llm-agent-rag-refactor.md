# 智能助手 LLM-Driven Agent + RAG 架构重构计划

> **目标**：将现有硬编码规则引擎迁移为纯 LLM 决策的 Agent 架构，打造简历级亮点项目

**架构变化**：硬编码意图分类 → LLM ReAct Agent（推理+行动）

**Tech Stack**：FastAPI + Vue3 + OpenAI Function Calling + Pinecone + SQLAlchemy

---

## Task 1: 设计 LLM Agent Core（决策中枢）

**Files:**
- Create: `service/agent_core.py`
- Test: `tests/service/test_agent_core.py`

**核心职责**：
- 接收用户输入
- 调用 LLM 判断意图、决定工具、生成搜索查询
- 返回结构化决策（JSON）

**设计要点**：
```python
class AgentCore:
    def decide(self, user_message: str, history: list) -> AgentDecision:
        """
        LLM 判断用户需要什么，返回决策对象
        """
        llm_response = call_llm(
            query=user_message,
            system_instruction=AGENT_DECISION_PROMPT,
            tools=AVAILABLE_TOOLS
        )
        return AgentDecision(
            reasoning=llm_response["reasoning"],
            intent=llm_response["intent"],  # knowledge | recommendation | action | clarification
            tool_calls=llm_response.get("tool_calls", []),
            needs_clarification=llm_response.get("needs_clarification", False),
            clarification_question=llm_response.get("clarification_question"),
            search_query=llm_response.get("search_query"),
        )
```

**Prompt 设计原则**：
- 告诉 LLM 所有可用工具及其参数
- 要求 LLM 先思考（reasoning）再决定
- 明确区分 knowledge（查询）和 recommendation（个性化推荐）
- 对于 recommendation，如果缺少必要信息，返回 needs_clarification

**测试用例**：
1. "你好" → 意图 greeting，不需要工具
2. "推荐几个川菜" → 意图 recommendation，needs_clarification=True（缺少预算/人数）
3. "推荐几个卖咖啡的店" → 意图 knowledge，search_query="咖啡店 咖啡商家"
4. "帮我加一份鱼香肉丝到购物车" → 意图 action，tool=add_to_cart

---

## Task 2: 设计 Tool Registry & 工具层

**Files:**
- Create: `service/tool_definitions.py`（工具定义Schema）
- Modify: `service/tool_registry.py`（已有，需扩展）
- Test: `tests/service/test_tools.py`

**工具清单**：
```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "当用户查询商家信息、菜品信息、营业时间等知识时使用。生成搜索查询，系统会自动进行向量检索和数据库查询。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "优化的搜索关键词"},
                    "filters": {
                        "type": "object",
                        "properties": {
                            "cuisine_type": {"type": "string"},
                            "price_max": {"type": "number"}
                        }
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "recommend_dishes",
            "description": "当用户请求个性化推荐时使用。需要提供预算、人数、口味偏好等约束。",
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {"type": "number"},
                    "party_size": {"type": "integer"},
                    "preferences": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": "将指定菜品加入用户购物车",
            "parameters": {
                "type": "object",
                "properties": {
                    "dish_id": {"type": "integer"},
                    "quantity": {"type": "integer", "default": 1}
                },
                "required": ["dish_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_address",
            "description": "保存用户配送地址",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "detail_address": {"type": "string"},
                    "contact_phone": {"type": "string"}
                },
                "required": ["label", "detail_address", "contact_phone"]
            }
        }
    }
]
```

**每个工具的Executor**：
- `search_knowledge_base` → 调用 HybridRetriever
- `recommend_dishes` → 调用 HybridRetriever + 约束过滤
- `add_to_cart` → 调用 cart_service
- `save_address` → 调用 address_service

---

## Task 3: 重构 AssistantService（移除硬编码拦截）

**Files:**
- Modify: `service/assistant_service.py`
- Delete/Deprecate: `service/assistant_constraint_parser.py`（硬编码规则）
- Modify: `service/assistant_retriever.py`（适配新接口）
- Test: `tests/service/test_assistant_service.py`

**新流程（LLM-first）**：
```python
def chat(self, request) -> AssistantChatResponse:
    state = self.session_store.get_or_create(request.session_id)
    
    # === 新流程 ===
    # Step 1: LLM Agent Core 做决策
    decision = self.agent_core.decide(
        user_message=request.message,
        history=state.history
    )
    
    # Step 2: 如果需要澄清，直接返回
    if decision.needs_clarification:
        return self._build_clarification_response(decision)
    
    # Step 3: 执行工具调用
    tool_results = []
    if decision.tool_calls:
        for tool_call in decision.tool_calls:
            result = self.tool_registry.execute(
                tool_call["name"], 
                tool_call["parameters"]
            )
            tool_results.append(result)
    
    # Step 4: LLM 结合工具结果生成最终回复
    response = self.grounded_responder.respond(
        user_message=request.message,
        agent_decision=decision,
        tool_results=tool_results,
        history=state.history
    )
    
    # Step 5: 更新会话状态
    self.session_store.update(...)
    
    return response
```

**关键变化**：
1. 移除 `IntentRouter` 硬编码规则回退（保留 LLM 路由）
2. 移除 `ConstraintResolver` 硬编码检查（让 LLM 判断是否需要澄清）
3. `AssistantRetriever` 不再被约束解析器驱动，而是被 Agent Core 的 `search_query` 驱动

---

## Task 4: 升级 GroundedResponder（工具感知生成）

**Files:**
- Modify: `service/grounded_responder.py`
- Test: `tests/service/test_grounded_responder.py`

**新要求**：
- 接收 `tool_results`（工具执行结果）
- LLM 根据用户问题 + 工具结果生成回复
- 要求 LLM 引用数据来源（增加可信度）

**Prompt 设计**：
```
你是一个智能点餐助手。以下是工具执行结果，请基于这些数据回答用户问题。

用户问题：{user_message}

工具执行结果：
{tool_results}

要求：
1. 直接回答用户问题
2. 引用具体数据（如商家名、价格、评分）
3. 如果数据不足，诚实说明
4. 对于推荐，给出推荐理由

回复格式：
- 直接回答（2-3句话）
- 详细信息（列表展示）
- 建议操作（可选）
```

---

## Task 5: 端到端集成测试

**Files:**
- Create: `tests/e2e/test_agent_flows.py`

**测试场景**：

| 用户输入 | 期望行为 | 验证点 |
|---------|---------|--------|
| "你好" | 问候回复 | 不调用工具 |
| "推荐几个卖咖啡的店" | 直接搜索咖啡店列表 | Agent识别为knowledge，不询问预算 |
| "推荐几个川菜，预算200，3个人" | 检索+推荐 | Agent识别为recommendation，调用retrieve |
| "帮我加一份鱼香肉丝" | 调用add_to_cart | Agent识别action，执行工具 |
| "推荐几个川菜" | 询问预算和人数 | Agent识别缺少约束，返回clarification |

---

## Task 6: 性能与体验优化

**Files:**
- Modify: `service/agent_core.py`
- Modify: `ui/src/components/home/FloatingAssistant.vue`

**优化项**：
1. **流式响应**：前端支持打字机效果，LLM 流式返回
2. **思考过程展示**：可选显示 LLM 的 reasoning 过程（"正在思考..." → "正在搜索..." → "正在生成..."）
3. **工具调用耗时显示**：显示"正在查询数据库..."等状态
4. **缓存**：常见查询结果缓存（如"你们有什么菜"）

**前端状态机**：
```
Idle → Thinking → ToolCalling → Generating → Done
        ↓            ↓              ↓
   显示思考中    显示工具执行中    显示生成中
```

---

## 简历亮点提炼

重构完成后，简历可以这么写：

> **智能点餐助手 Agent 系统重构**
> - 将硬编码规则引擎迁移为 **LLM-driven ReAct Agent** 架构，意图识别准确率提升 40%+
> - 设计 **Tool-Augmented RAG** 模式，LLM 动态选择工具（知识检索/个性化推荐/操作执行），支持 3 类工具组合调用
> - 实现 **Hybrid RAG Pipeline**：LLM Query Refinement + Pinecone 向量语义召回 + SQL 硬性约束过滤，覆盖 360+ 向量（320菜品+40商家）
> - 端到端响应时间 < 2s，支持流式打字机效果与工具调用状态可视化

---

## 执行顺序

```
Task 1: Agent Core 设计 → Task 2: 工具定义 → Task 3: 重构 Service → 
Task 4: 升级 Responder → Task 5: E2E 测试 → Task 6: 体验优化
```

**每个 Task 都遵循 TDD**：先写失败测试 → 实现最小代码 → 验证通过

---

**准备开始执行？选择：**
1. **Task 1** - 开始实现 Agent Core
2. **调整方案** - 修改设计后再执行
