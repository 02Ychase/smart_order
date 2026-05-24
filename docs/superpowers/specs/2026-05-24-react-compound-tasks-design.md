# ReAct 复合任务增强设计

## 背景与问题

smart_order 的 LangGraph Agent 在处理复合用户请求时存在结构性缺陷。
典型失败场景：

- "推荐几个川菜，然后加入购物车" — RAG 完成后无法续接 action
- "推荐几个川菜，然后都加入购物车" — 多条同名 tool_call 被去重，只执行 1 条
- "推荐一个川菜，再推荐一个湘菜" — 单次 RAG 无法保证分别返回各一个

### 根因诊断

四个结构性缺陷导致现有 `evaluate → plan` 循环是"假循环"：

1. **上下文断裂**：`_build_human_input` 不向 planner LLM 注入 `recent_evidence` 和 `tool_results`。
   re-plan 时 LLM 不知道 RAG 已完成、找到了什么菜品、该填什么 dish_id。

2. **tool_name 去重封锁**：`_parse_tool_calls` 用 `seen: set[str]` 按 tool_name 去重；
   `route_after_plan`、`evaluate_node`、`action_node`、`rag_node`、`execute_action`、
   `action_node` 外层共 6 处用 `{r.get("type","") for r in tool_results}` 判完成——
   同名 tool_call 执行 1 条即标记全部完成。

3. **evidence 替换而非累加**：`rag_node` 返回 `{"recent_evidence": serialized}`，
   第二轮 RAG 结果覆盖第一轮，多 RAG 子任务必丢数据。

4. **rag_node 批量执行**：`rag_node` 用 `plan.normalized_query` 做一次检索，
   然后遍历 plan 中所有 RAG call 一次性标记完成。无法支持两个独立 RAG 子任务
   （如川菜和湘菜分别检索）。

## 方案选型

选择"渐进增强"路线——不改 LangGraph 图拓扑，让现有循环变成真正的 ReAct 循环。

核心策略：**LLM 决策 + 代码兜底**。

- LLM 负责续接规划（从 observation 推断下一步）
- 代码负责参数桥接兜底（evidence → action arguments）
- plan_node 在 pending call 时复用当前 plan，避免 step_id 碰撞
- 双保险，不完全依赖模型质量

## 详细设计

### 1. step_id 替代 tool_name 作为完成标识

**目标**：支持同名工具的多次调用（如 3 条 add_to_cart）。

#### 1.1 GraphToolCall 增加 step_id

文件：`service/agent_runtime/state.py`

```python
@dataclass
class GraphToolCall:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    writes_database: bool = False
    step_id: str = ""  # 自动生成，如 "add_to_cart_0"
```

#### 1.2 GraphToolCallSchema 增加可选 step_id

文件：`service/agent_runtime/schemas.py`

```python
class GraphToolCallSchema(BaseModel):
    tool_name: str = Field(...)
    arguments: dict[str, Any] = Field(...)
    writes_database: bool = Field(...)
    step_id: str = Field(default="", description="Optional step identifier, auto-generated if empty")
```

#### 1.3 _parse_tool_calls 改去重逻辑

文件：`service/agent_runtime/planner.py`

改动：

- 去掉 `seen: set[str]` 的 tool_name 去重
- 改为按 `step_id` 去重（相同 step_id 才跳过）
- 自动生成 step_id：`f"{tool_name}_{index}"`
- 同一 tool_name 但不同 arguments 的调用都被保留

```python
def _parse_tool_calls(self, raw_calls, intent):
    calls = []
    tool_name_counter: dict[str, int] = {}
    seen_step_ids: set[str] = set()
    for item in raw_calls:
        ...
        tool_name = self._normalize_tool_name(raw_name, intent)
        if tool_name is None:
            continue
        count = tool_name_counter.get(tool_name, 0)
        step_id = item.get("step_id") or f"{tool_name}_{count}"
        if step_id in seen_step_ids:
            continue
        tool_name_counter[tool_name] = count + 1
        seen_step_ids.add(step_id)
        calls.append(GraphToolCall(
            tool_name=tool_name,
            arguments=arguments,
            writes_database=writes_database,
            step_id=step_id,
        ))
    return calls
```

#### 1.4 所有完成判定改用 step_id

文件：`service/agent_runtime/nodes.py`

以下 6 处 `completed_tools` 逻辑全部改为按 `step_id` 匹配：

```python
# 通用模式（替换所有 6 处）
completed_step_ids = {r.get("step_id", r.get("type", "")) for r in state.get("tool_results", [])}
remaining_calls = [c for c in plan.tool_calls if c.step_id not in completed_step_ids]
```

涉及函数（6 处）：
1. `route_after_plan`（第 222-224 行）— 判断 remaining_calls
2. `evaluate_node`（第 271-274 行）— 判断 pending_calls
3. `action_node`（第 536-539 行）— 确定 executed_tool_name
4. `LocalActionExecutor.execute_action`（第 366-369 行）— 找下一个 action call
5. `rag_node`（第 337-338 行）— 标记 RAG call 完成
6. `_normalize_tool_result` 调用处 — 记录 step_id 到结果中

#### 1.5 tool_results 记录 step_id

`_normalize_tool_result` 增加 step_id 字段：

```python
def _normalize_tool_result(result, state, executed_tool_name="", step_id=""):
    ...
    return {
        "type": ...,
        "step_id": step_id,  # 新增
        "success": ...,
        "message": ...,
        "data": ...,
    }
```

所有调用 `_normalize_tool_result` 的地方传入当前执行的 `step_id`。

### 2. plan_node Pending Call 复用

**目标**：当 current_plan 还有未完成的 step 时，直接复用当前 plan，
不重新调用 LLM。避免 step_id 碰撞（re-plan 从 0 重新编号导致和已完成步骤冲突）。

文件：`service/agent_runtime/nodes.py` — `plan_node`

```python
def plan_node(state, config=None):
    # 复用逻辑：如果当前 plan 还有未完成的 step，直接复用
    current_plan = state.get("current_plan")
    if current_plan and current_plan.tool_calls:
        completed_step_ids = {
            r.get("step_id", r.get("type", ""))
            for r in state.get("tool_results", [])
        }
        pending = [c for c in current_plan.tool_calls if c.step_id not in completed_step_ids]
        if pending:
            return {"current_plan": current_plan}  # 复用，不 re-plan

    # 否则：调 LLM 做续接规划（全部完成 + 有新意图 的情况）
    runtime = get_runtime(config)
    planner = (runtime.planner if runtime else None) or _get_default_planner()
    user_message = latest_user_message(state)
    conversation_history = _format_recent_turns(state.get("messages", []), max_turns=3)
    plan = planner.plan(user_message, {
        "session_id": state.get("session_id"),
        "user_id": state.get("user_id"),
        "loaded_user_memories": state.get("loaded_user_memories", []),
        "recent_action_ids": state.get("recent_action_ids", []),
        "iteration_count": state.get("iteration_count", 0),
        "recent_evidence": state.get("recent_evidence", []),
        "tool_results": state.get("tool_results", []),
        "conversation_history": conversation_history,
        "last_recommendations": state.get("last_recommendations", []),
    })
    return {"current_plan": plan}
```

**执行流程决策树**：

```
evaluate → plan_node:
  ├─ current_plan 有 pending calls? → 复用 plan（step_id 不变）
  └─ 全部完成或无 plan? → 调 LLM 续接规划（生成新 step_id）
```

### 3. ReAct 上下文注入

**目标**：让 planner LLM 在续接规划时看到前一步的结果。

#### 3.1 _build_human_input 增加 Observation sections

文件：`service/agent_runtime/planner.py`

在 `_build_human_input` 中，当存在 evidence 或 tool_results 时注入新 section：

```python
@staticmethod
def _build_human_input(user_message, context):
    parts = []

    # 现有：对话历史
    conversation_history = context.get("conversation_history", "")
    if conversation_history:
        parts.append(f"## 对话历史\n{conversation_history}")

    # 现有：上一轮推荐结果
    last_recs = context.get("last_recommendations", [])
    if last_recs:
        ...  # 不变

    # 🆕 本轮已检索到的结果
    recent_evidence = context.get("recent_evidence", [])
    if recent_evidence:
        evidence_lines = []
        for idx, item in enumerate(recent_evidence, 1):
            facts = item.get("facts", {})
            source_type = item.get("source_type", "")
            if source_type == "dish":
                line = (
                    f"{idx}. {facts.get('dish_name', '')} "
                    f"(dish_id={facts.get('dish_id', '')}, "
                    f"商家={facts.get('merchant_name', '')}, "
                    f"{facts.get('price', '')}元, "
                    f"{facts.get('cuisine_type', '')}/{facts.get('flavor_profile', '')})"
                )
            else:
                line = (
                    f"{idx}. {facts.get('merchant_name', facts.get('name', ''))} "
                    f"(merchant_id={facts.get('merchant_id', facts.get('id', ''))})"
                )
            evidence_lines.append(line)
        parts.append("## 本轮已检索到的结果\n" + "\n".join(evidence_lines))

    # 🆕 本轮已完成的操作
    tool_results = context.get("tool_results", [])
    if tool_results:
        result_lines = []
        for r in tool_results:
            status = "成功" if r.get("success") else "失败"
            result_lines.append(
                f"- {r.get('step_id', r.get('type', ''))}: {status} - {r.get('message', '')}"
            )
        parts.append("## 本轮已完成的操作\n" + "\n".join(result_lines))

    # 现有：用户最新消息
    parts.append(f"## 用户最新消息\n{user_message}")
    return "\n\n".join(parts)
```

### 4. Planner Prompt 续接规划指令

**目标**：让 LLM 知道如何在续接规划中利用 observation。

文件：`prompt/agent/planner.system.md`

在现有规则末尾追加：

```markdown
续接规划规则（ReAct 循环）：
- 当输入中包含"## 本轮已检索到的结果"时，说明本轮内 RAG 检索已经完成。
- 当输入中包含"## 本轮已完成的操作"时，不要输出已完成的 step_id 对应的 tool_call。
- 如果用户的原始请求包含后续操作（如"加入购物车""记住偏好"），你应当：
  - intent 设为后续操作对应的类型（如 cart_action、preference_action）
  - 从"## 本轮已检索到的结果"中提取需要的参数（如 dish_id）填入 tool_call arguments
  - 如果用户没有指定具体哪个结果，默认选择排名第 1 的
  - 如果用户说"都加入购物车"，为每个菜品生成一条 add_to_cart，每条携带不同的 dish_id
- 如果用户请求多个独立子查询（如"推荐一个川菜，再推荐一个湘菜"），而当前检索结果只覆盖了部分，
  则应当为未满足的部分生成新的 recommend_dishes 调用，更新 normalized_query 和 filters。
- 续接规划时，如果 RAG 阶段已完成且后续只有 action，requires_rag 设为 false。
```

### 5. rag_node 单步执行

**目标**：rag_node 像 action_node 一样，每次只执行一个未完成的 RAG call，
使用该 call 的 arguments 做检索，只标记该 step_id 完成。

文件：`service/agent_runtime/nodes.py` — `rag_node`

```python
def rag_node(state, config=None):
    from service.config import get_config

    runtime = get_runtime(config)
    retriever = (runtime.retriever if runtime else None) or AdvancedRagRetriever()
    rag_cfg = get_config().rag
    plan = state["current_plan"]

    # 找下一个未完成的 RAG call
    completed_step_ids = {
        r.get("step_id", r.get("type", ""))
        for r in state.get("tool_results", [])
    }
    next_rag_call = next(
        (c for c in plan.tool_calls
         if c.tool_name in RAG_TOOL_NAMES and c.step_id not in completed_step_ids),
        None,
    )

    if next_rag_call is None:
        return {}  # 无 pending RAG call

    # 用该 call 的 arguments 决定检索参数
    call_args = next_rag_call.arguments or {}
    effective_query = (
        call_args.get("query")
        or plan.normalized_query
        or latest_user_message(state)
    )

    # 如果 call 自带 filters，构造一个临时 plan 副本传给 retriever
    call_plan = _build_call_scoped_plan(plan, call_args)

    evidence = retriever.retrieve(
        effective_query,
        agent_plan=call_plan,
        memories=state.get("loaded_user_memories", []),
        limit=rag_cfg.output_limit_default,
        max_limit=rag_cfg.output_limit_max,
    )

    serialized = [
        {
            "source_type": item.source_type,
            "source_id": item.source_id,
            "merchant_id": item.merchant_id,
            "title": item.title,
            "facts": item.facts,
            "why_matched": item.why_matched,
            "citation": item.citation,
            "score": item.score,
        }
        for item in evidence
    ]

    # evidence 累加（不覆盖之前的结果）
    existing_evidence = list(state.get("recent_evidence", []))
    seen_keys = {(e["source_type"], e["source_id"]) for e in existing_evidence}
    for item in serialized:
        key = (item["source_type"], item["source_id"])
        if key not in seen_keys:
            existing_evidence.append(item)
            seen_keys.add(key)

    # 只标记当前 step 完成
    existing_results = list(state.get("tool_results", []))
    existing_results.append({
        "type": next_rag_call.tool_name,
        "step_id": next_rag_call.step_id,
        "success": True,
        "message": f"检索到 {len(serialized)} 条结果",
        "data": {},
    })

    return {"recent_evidence": existing_evidence, "tool_results": existing_results}
```

辅助函数 `_build_call_scoped_plan`：

```python
def _build_call_scoped_plan(plan, call_args):
    """用 tool_call 的 arguments 覆盖 plan 的 filters，生成作用域 plan。

    如果 call_args 有自己的 cuisine_types/flavor_preferences 等 filter，
    用它们替换 plan 级别的 filter，使检索只针对该子任务。
    """
    import copy
    scoped = copy.copy(plan)
    filters = dict(plan.filters or {})

    # call_args 中的 filter 字段覆盖 plan 级别
    for key in ("cuisine_types", "flavor_preferences", "required_keywords",
                "forbidden_keywords", "exclude_allergens", "source_types",
                "limit", "sort_by", "price_preference", "budget_max"):
        if key in call_args and call_args[key] is not None:
            filters[key] = call_args[key]

    # 如果 call_args 有自己的 query，也覆盖 normalized_query
    if call_args.get("query"):
        scoped.normalized_query = call_args["query"]

    scoped.filters = filters
    return scoped
```

### 6. Evidence 自动桥接（代码兜底）

**目标**：即使 LLM 漏填参数，action 仍能执行。

文件：`service/agent_runtime/nodes.py` — `LocalActionExecutor.execute_action`

在 `add_to_cart` 分支中增加 fallback：

```python
if call.tool_name == "add_to_cart":
    dish_id = call.arguments.get("dish_id")

    # 兜底：LLM 没填 dish_id 时从 evidence 取
    if dish_id is None:
        dish_evidence = [
            e for e in state.get("recent_evidence", [])
            if e.get("source_type") == "dish"
        ]
        if dish_evidence:
            dish_id = dish_evidence[0].get("facts", {}).get("dish_id")

    if dish_id is None:
        return {"success": False, "message": "缺少 dish_id 参数", "undo_available": False}
    # ... 继续现有逻辑
```

### 7. evaluate_node 未满足意图检查

**目标**：当 plan 中的 tool_calls 全部完成，但用户原始消息包含未执行的后续意图时，
回路到 plan 进行续接规划。覆盖两类场景：未满足的 action 意图和未满足的检索子任务。

文件：`service/agent_runtime/nodes.py`

#### 7.1 统一入口

```python
def evaluate_node(state):
    ...
    # 现有逻辑：检查 plan 中的 pending calls
    if has_pending_action or has_pending_rag:
        return {..., "_next": "plan"}

    if has_evidence or has_tool_results:
        # 🆕 检查是否有未满足的后续意图
        if _has_unfulfilled_intent(state):
            return {..., "_next": "plan"}
        return {..., "_next": "respond"}
    ...
```

#### 7.2 未满足意图检测（覆盖 action + retrieval）

```python
def _has_unfulfilled_intent(state):
    return _has_unfulfilled_action_intent(state) or _has_unfulfilled_retrieval_intent(state)
```

#### 7.3 Action 意图检测（按工具粒度映射）

关键改进：
- 按 tool_name 粒度映射 keywords → 具体工具，而非整个 ACTION_TOOL_NAMES
- 只把 `success=True` 的结果算已完成

```python
_ACTION_INTENT_MAPPING = {
    "add_to_cart": ["加入购物车", "加购物车", "加到购物车", "都加入", "加购", "买"],
    "remove_from_cart": ["移除", "从购物车删", "去掉"],
    "cart_clear": ["清空购物车", "全部删除"],
    "upsert_preference": ["记住", "偏好", "不吃", "过敏"],
    "save_address": ["保存地址", "加入地址"],
}

def _has_unfulfilled_action_intent(state):
    user_message = latest_user_message(state)
    # 只统计成功完成的 action tool
    completed_action_tools = {
        r.get("type", "")
        for r in state.get("tool_results", [])
        if r.get("success", False) and r.get("type", "") in ACTION_TOOL_NAMES
    }
    for tool_name, keywords in _ACTION_INTENT_MAPPING.items():
        if any(kw in user_message for kw in keywords):
            if tool_name not in completed_action_tools:
                return True
    return False
```

#### 7.4 Retrieval 意图检测（复合查询覆盖度）

检测用户是否请求了多个独立检索子任务，且 evidence 尚未全部覆盖。

```python
_COMPOUND_QUERY_MARKERS = ["再推荐", "再来", "还要", "另外推荐", "还推荐", "同时推荐"]
_CUISINE_KEYWORDS = {
    "川菜": "川菜", "湘菜": "湘菜", "粤菜": "粤菜", "日料": "日韩料理",
    "韩餐": "日韩料理", "西餐": "西餐", "火锅": "火锅", "烧烤": "烧烤",
    "咖啡": "咖啡甜品", "甜品": "咖啡甜品", "轻食": "轻食",
}

def _has_unfulfilled_retrieval_intent(state):
    user_message = latest_user_message(state)

    # 只在检测到复合查询标记词时触发
    if not any(marker in user_message for marker in _COMPOUND_QUERY_MARKERS):
        return False

    # 提取用户提到的菜系
    mentioned = set()
    for keyword, cuisine in _CUISINE_KEYWORDS.items():
        if keyword in user_message:
            mentioned.add(cuisine)

    if len(mentioned) < 2:
        return False  # 没提到多个菜系，不是复合检索

    # 检查 evidence 是否覆盖了所有提到的菜系
    evidence = state.get("recent_evidence", [])
    covered = {
        e.get("facts", {}).get("cuisine_type", "")
        for e in evidence
        if e.get("source_type") == "dish"
    }
    return not mentioned.issubset(covered)
```

### 8. respond_node 合并 Action 确认

**目标**：当复合任务同时产生 evidence（推荐结果）和 tool_results（action 结果）时，
最终回复应同时包含推荐信息和操作确认，而非只展示推荐。

文件：`service/agent_runtime/nodes.py` — `respond_node`

#### 8.1 LLM 回复路径：注入 tool_results

将 `tool_results` 传入 `_generate_llm_response`，让 LLM 同时基于
evidence 和已完成操作生成回复：

```python
if evidence and use_llm:
    message = _generate_llm_response(
        user_message, response_type, evidence, conversation_history,
        tool_results=tool_results,  # 🆕
    )
```

`_generate_llm_response` 增加 tool_results 参数：

```python
def _generate_llm_response(user_message, response_type, evidence,
                           conversation_history="", tool_results=None):
    ...
    parts = []
    if conversation_history:
        parts.append(f"对话历史：\n{conversation_history}\n")
    parts.append(f"用户最新消息：{user_message}")
    parts.append(f"意图：{response_type}")
    parts.append(f"\n检索到的证据：\n{evidence_text}")

    # 🆕 注入已完成操作
    if tool_results:
        action_lines = []
        for r in tool_results:
            if r.get("type", "") in ACTION_TOOL_NAMES:
                status = "成功" if r.get("success") else "失败"
                action_lines.append(f"- {r.get('message', '')}（{status}）")
        if action_lines:
            parts.append(f"\n已完成的操作：\n" + "\n".join(action_lines))

    parts.append("\n请基于证据和已完成操作生成自然回复。")
    ...
```

#### 8.2 Template fallback 路径：追加 action 摘要

```python
elif evidence:
    message = _template_recommendation(recommendations)
    # 🆕 追加 action 确认
    if tool_results:
        action_msgs = [
            r.get("message", "")
            for r in tool_results
            if r.get("success") and r.get("type", "") in ACTION_TOOL_NAMES
        ]
        if action_msgs:
            message += "\n\n" + "\n".join(f"✅ {m}" for m in action_msgs)
```

#### 8.3 response_type 适配复合场景

当 evidence 和 action results 同时存在时，`response_type` 应设为 `"action_completed"`
而非 `"recommendation"`，以让前端正确展示操作确认区域：

```python
def _external_response_type(plan, state):
    ...
    # 🆕 复合场景：有 evidence + 有成功 action → action_completed
    tool_results = state.get("tool_results", [])
    has_successful_action = any(
        r.get("success") and r.get("type", "") in ACTION_TOOL_NAMES
        for r in tool_results
    )
    if has_successful_action:
        return "action_completed"
    ...
```

## 不变的部分

- **图拓扑**：`_build_graph` 不改，节点和边不变
- **SmartOrderAgentState**：不新增字段（step_id 在 GraphToolCall 内部）
- **RAG pipeline**：recall/fusion/rerank/diversify 全部不变
- **前端**：FloatingAssistant.vue 和所有 API schema 不变
- **API 路由**：不变

## 端到端执行流验证

### 场景 1："推荐几个川菜，然后加入购物车"

```
input_guardrail → load_memory →
plan[0]: 首次规划，intent=recommendation, tool_calls=[recommend_dishes_0(cuisine=川菜)]
  → route_after_plan: requires_rag, no evidence → "rag"
  → rag_node: 找到 recommend_dishes_0，用其 args 检索，找到 3 道川菜 (dish_id=12,35,7)
              标记 recommend_dishes_0 完成，evidence=[3 道川菜]
  → evaluate: pending_calls=空，检测 _has_unfulfilled_action_intent("加入购物车") → True → _next=plan
plan[1]: plan_node 无 pending calls → 调 LLM 续接规划
         LLM 看到 evidence（含 dish_id），intent=cart_action
         tool_calls=[add_to_cart_0(dish_id=12)]
  → route_after_plan: next_call=add_to_cart_0 → "action"
  → action_node: 执行 add_to_cart_0，成功
  → evaluate: pending_calls=空，无未满足意图 → _next=respond
respond: LLM 生成"为你推荐了 3 道川菜，已将宫保鸡丁加入购物车"
  → write_memory → END
```

### 场景 2："推荐几个川菜，然后都加入购物车"

```
plan[0]: tool_calls=[recommend_dishes_0(cuisine=川菜)]
  → rag: 找到 3 道川菜 (12,35,7)，标记 recommend_dishes_0 完成
  → evaluate: 检测 "都加入购物车" 未满足 → _next=plan

plan[1]: plan_node 无 pending calls → LLM 续接规划
         LLM 看到 3 道川菜，生成:
         tool_calls=[add_to_cart_0(12), add_to_cart_1(35), add_to_cart_2(7)]
  → route: next_call=add_to_cart_0 → "action"
  → action: 执行 add_to_cart_0
  → evaluate: pending=[add_to_cart_1, add_to_cart_2] → _next=plan

plan[2]: plan_node 有 pending calls → 复用当前 plan（不调 LLM，step_id 不变）
  → route: next_call=add_to_cart_1 → "action"
  → action: 执行 add_to_cart_1
  → evaluate: pending=[add_to_cart_2] → _next=plan

plan[3]: plan_node 有 pending calls → 复用
  → action: 执行 add_to_cart_2
  → evaluate: 全部完成 → _next=respond

respond: "为你推荐了 3 道川菜。✅ 已将宫保鸡丁加入购物车 ✅ 已将水煮鱼片加入购物车 ✅ 已将干煸四季豆加入购物车"
```

### 场景 3："推荐一个川菜，再推荐一个湘菜"

```
plan[0]: LLM 分析出两个子查询:
         tool_calls=[recommend_dishes_0(cuisine=川菜,limit=1), recommend_dishes_1(cuisine=湘菜,limit=1)]
  → route: next pending RAG call → "rag"
  → rag_node: 找到 recommend_dishes_0，用其 args(cuisine=川菜,limit=1) 检索
              找到 1 道川菜，标记 recommend_dishes_0 完成
  → evaluate: pending=[recommend_dishes_1] → _next=plan

plan[1]: plan_node 有 pending calls → 复用当前 plan
  → route: next pending RAG call=recommend_dishes_1 → "rag"
  → rag_node: 找到 recommend_dishes_1，用其 args(cuisine=湘菜,limit=1) 检索
              找到 1 道湘菜，evidence 累加（川菜 + 湘菜），标记 recommend_dishes_1 完成
  → evaluate: 全部完成，无未满足意图 → _next=respond

respond: 同时展示 1 道川菜 + 1 道湘菜推荐结果
```

注意场景 3 有两种可能的执行路径：
- **路径 A**（上述）：LLM 在首次规划时就生成两个独立 RAG call。依赖 planner prompt 质量。
- **路径 B**：LLM 首次只生成一个 RAG call（川菜），第一轮完成后，
  `_has_unfulfilled_retrieval_intent` 检测到湘菜未覆盖，触发 re-plan，
  LLM 续接生成第二个 RAG call。依赖 evaluate 的意图检测 + LLM 续接能力。

两条路径都能正确执行。路径 A 更高效（1 次 LLM 调用），路径 B 更健壮（不依赖首次规划完美）。

## 测试计划

新增测试文件：`tests/service/test_compound_tasks.py`

| 测试用例 | 验证点 |
|---|---|
| test_rag_then_add_to_cart | RAG→Action 续接，dish_id 正确桥接 |
| test_rag_then_add_all_to_cart | 多条 add_to_cart 不被去重，全部执行 |
| test_multi_cuisine_rag | 两轮 RAG 分别返回川菜和湘菜，evidence 累加 |
| test_step_id_uniqueness | _parse_tool_calls 为同名工具生成不同 step_id |
| test_completed_tools_by_step_id | 按 step_id 判完成，不误标同名工具 |
| test_plan_reuse_on_pending_calls | pending call 时 plan_node 复用，step_id 不变 |
| test_evidence_bridging_fallback | LLM 漏填 dish_id 时代码从 evidence 兜底 |
| test_unfulfilled_action_intent | evaluate_node 按工具粒度检测未满足 action |
| test_unfulfilled_retrieval_intent | evaluate_node 检测多菜系查询覆盖度 |
| test_evidence_accumulation | rag_node 多次调用 evidence 累加不覆盖 |
| test_rag_single_step_execution | rag_node 每次只执行一个 RAG call |
| test_respond_merges_action_results | respond_node 合并推荐+action 确认 |

## 改动文件汇总

| 文件 | 改动类型 |
|---|---|
| `service/agent_runtime/state.py` | GraphToolCall 增加 step_id |
| `service/agent_runtime/schemas.py` | GraphToolCallSchema 增加 step_id |
| `service/agent_runtime/planner.py` | _parse_tool_calls 去重改 step_id；_build_human_input 注入 observation；_schema_to_plan 传递 step_id |
| `service/agent_runtime/nodes.py` | plan_node pending 复用；6 处 completed 改 step_id；rag_node 单步执行+累加；action_node 桥接；evaluate_node 意图检查；respond_node 合并 action 确认 |
| `prompt/agent/planner.system.md` | 续接规划指令 |
| `tests/service/test_compound_tasks.py` | 新增 12 个测试用例 |
