# ReAct 复合任务增强设计

## 背景与问题

smart_order 的 LangGraph Agent 在处理复合用户请求时存在结构性缺陷。
典型失败场景：

- "推荐几个川菜，然后加入购物车" — RAG 完成后无法续接 action
- "推荐几个川菜，然后都加入购物车" — 多条同名 tool_call 被去重，只执行 1 条
- "推荐一个川菜，再推荐一个湘菜" — 单次 RAG 无法保证分别返回各一个

### 根因诊断

三个结构性缺陷导致现有 `evaluate → plan` 循环是"假循环"：

1. **上下文断裂**：`_build_human_input` 不向 planner LLM 注入 `recent_evidence` 和 `tool_results`。
   re-plan 时 LLM 不知道 RAG 已完成、找到了什么菜品、该填什么 dish_id。

2. **tool_name 去重封锁**：`_parse_tool_calls` 用 `seen: set[str]` 按 tool_name 去重；
   `route_after_plan`、`evaluate_node`、`action_node`、`rag_node`、`execute_action`
   共 6 处用 `{r.get("type","") for r in tool_results}` 判完成——同名 tool_call 执行 1 条即
   标记全部完成。

3. **evidence 替换而非累加**：`rag_node` 返回 `{"recent_evidence": serialized}`，
   第二轮 RAG 结果覆盖第一轮，多 RAG 子任务必丢数据。

## 方案选型

选择"渐进增强"路线——不改 LangGraph 图拓扑，让现有循环变成真正的 ReAct 循环。

核心策略：**LLM 决策 + 代码兜底**。

- LLM 负责续接规划（从 observation 推断下一步）
- 代码负责参数桥接兜底（evidence → action arguments）
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

涉及函数：
- `route_after_plan`（第 222-224 行）
- `evaluate_node`（第 271-274 行）
- `action_node`（第 536-539 行）
- `LocalActionExecutor.execute_action`（第 366-369 行）
- `rag_node`（第 337-338 行）

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

### 2. ReAct 上下文注入

**目标**：让 planner LLM 在续接规划时看到前一步的结果。

#### 2.1 _build_human_input 增加 Observation sections

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
            result_lines.append(f"- {r.get('step_id', r.get('type', ''))}: {status} - {r.get('message', '')}")
        parts.append("## 本轮已完成的操作\n" + "\n".join(result_lines))

    # 现有：用户最新消息
    parts.append(f"## 用户最新消息\n{user_message}")
    return "\n\n".join(parts)
```

### 3. Planner Prompt 续接规划指令

**目标**：让 LLM 知道如何在第 2+ 轮规划中利用 observation。

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

### 4. Evidence 自动桥接（代码兜底）

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

### 5. evaluate_node 未满足意图检查

**目标**：当 plan 中的 tool_calls 全部完成，但用户原始消息包含未执行的后续意图时，
回路到 plan 进行续接规划。

文件：`service/agent_runtime/nodes.py`

```python
# 在 evaluate_node 的 "all steps done" 分支前增加：
if has_evidence and not has_tool_action_results:
    if _has_unfulfilled_action_intent(state):
        return {"iteration_count": iteration, "_next": "plan", "metrics": existing_metrics}
```

`_has_unfulfilled_action_intent` 是轻量规则检查（不调用 LLM）：

```python
_ACTION_INTENT_KEYWORDS = {
    "cart_action": ["加入购物车", "加购物车", "加到购物车", "都加入", "加购", "买"],
    "preference_action": ["记住", "偏好", "不吃", "过敏"],
    "address_action": ["保存地址", "加入地址"],
}

def _has_unfulfilled_action_intent(state):
    user_message = latest_user_message(state)
    completed_types = {r.get("type", "") for r in state.get("tool_results", [])}
    for action_category, keywords in _ACTION_INTENT_KEYWORDS.items():
        if any(kw in user_message for kw in keywords):
            # 检查是否已有对应类型的 action 完成
            if not any(t in ACTION_TOOL_NAMES for t in completed_types):
                return True
    return False
```

### 6. rag_node Evidence 累加

**目标**：多轮 RAG 结果保留而非覆盖。

文件：`service/agent_runtime/nodes.py` — `rag_node`

```python
# 改前：
return {"recent_evidence": serialized, "tool_results": existing_results}

# 改后：
existing_evidence = list(state.get("recent_evidence", []))
seen_keys = {(e["source_type"], e["source_id"]) for e in existing_evidence}
for item in serialized:
    key = (item["source_type"], item["source_id"])
    if key not in seen_keys:
        existing_evidence.append(item)
        seen_keys.add(key)
return {"recent_evidence": existing_evidence, "tool_results": existing_results}
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
plan[0]: intent=recommendation, tool_calls=[recommend_dishes_0(cuisine=川菜)]
  → rag: 找到 3 道川菜 (dish_id=12,35,7)
  → evaluate: recommend_dishes_0 完成，检测到"加入购物车"未满足 → _next=plan
plan[1]: LLM 看到 evidence，intent=cart_action, tool_calls=[add_to_cart_0(dish_id=12)]
  → action: 成功加入购物车
  → evaluate: 全部完成 → _next=respond
respond → write_memory → END
```

### 场景 2："推荐几个川菜，然后都加入购物车"

```
plan[0] → rag: 找到 3 道川菜 (12,35,7)
  → evaluate: 检测到"都加入"未满足 → _next=plan
plan[1]: LLM 看到 3 道菜，生成 3 条 add_to_cart:
  tool_calls=[add_to_cart_0(12), add_to_cart_1(35), add_to_cart_2(7)]
  → action: 执行 add_to_cart_0 (step_id 匹配)
  → evaluate: add_to_cart_1, add_to_cart_2 未完成 → _next=plan
plan[2]: LLM 看到 add_to_cart_0 已完成，remaining=[add_to_cart_1, add_to_cart_2]
  → action: 执行 add_to_cart_1
  → evaluate: add_to_cart_2 未完成 → _next=plan
plan[3]: → action: 执行 add_to_cart_2
  → evaluate: 全部完成 → _next=respond
```

### 场景 3："推荐一个川菜，再推荐一个湘菜"

```
plan[0]: intent=recommendation, tool_calls=[recommend_dishes_0(cuisine=川菜, limit=1)]
  → rag: 找到 1 道川菜
  → evaluate: 检测到"再推荐一个湘菜"→ LLM 看到 evidence 只有川菜 → _next=plan
plan[1]: LLM 看到川菜已有，生成 recommend_dishes_1(cuisine=湘菜, limit=1)
  → rag: 找到 1 道湘菜，evidence 累加（川菜 + 湘菜）
  → evaluate: 全部完成 → _next=respond
respond: 同时展示川菜和湘菜结果
```

## 测试计划

新增测试文件：`tests/service/test_compound_tasks.py`

| 测试用例 | 验证点 |
|---|---|
| test_rag_then_add_to_cart | RAG→Action 续接，dish_id 正确桥接 |
| test_rag_then_add_all_to_cart | 多条 add_to_cart 不被去重，全部执行 |
| test_multi_cuisine_rag | 两轮 RAG 分别返回川菜和湘菜，evidence 累加 |
| test_step_id_uniqueness | _parse_tool_calls 为同名工具生成不同 step_id |
| test_completed_tools_by_step_id | 按 step_id 判完成，不误标同名工具 |
| test_evidence_bridging_fallback | LLM 漏填 dish_id 时代码从 evidence 兜底 |
| test_unfulfilled_intent_detection | evaluate_node 正确检测未满足的 action 意图 |
| test_evidence_accumulation | rag_node 多次调用 evidence 累加不覆盖 |

## 改动文件汇总

| 文件 | 改动类型 |
|---|---|
| `service/agent_runtime/state.py` | GraphToolCall 增加 step_id |
| `service/agent_runtime/schemas.py` | GraphToolCallSchema 增加 step_id |
| `service/agent_runtime/planner.py` | _parse_tool_calls 去重改 step_id；_build_human_input 注入 observation |
| `service/agent_runtime/nodes.py` | 6 处 completed_tools 改 step_id；rag_node 累加；action_node 桥接；evaluate_node 意图检查 |
| `prompt/agent/planner.system.md` | 续接规划指令 |
| `tests/service/test_compound_tasks.py` | 新增 8 个测试用例 |
