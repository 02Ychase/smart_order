# Smart Assistant Agent + RAG Highlight Design

## Goal

Build the smart assistant into the core technical highlight of `smart_order`.

The assistant should use existing merchant, dish, cart, address, and user data to answer catalog questions, recommend merchants and dishes, prepare cart changes, and help manage addresses. The design targets a resume-ready implementation: clear Agent architecture, tool calling, high-quality RAG, guardrails for side effects, and measurable retrieval/evaluation metrics.

The preferred demo environment can depend on external services:

- LLM: OpenAI-compatible chat model through the existing `MODEL_NAME` and API key configuration.
- Embedding: DashScope `text-embedding-v4`.
- Vector store: Pinecone.

The implementation should still keep defensive fallbacks where practical, but external services are the primary path.

## Product Scope

The first version focuses on four user-facing capabilities:

1. Answer questions about merchants and dishes.
2. Recommend merchants or dishes based on natural-language constraints.
3. Help add recommended or explicitly requested dishes to the cart.
4. Help parse and save delivery addresses.

The target is not a fully autonomous shopping agent. Data-changing actions are controlled by a mixed execution strategy:

- Direct execution is allowed for low-risk, explicit, unambiguous operations.
- Confirmation is required for recommendation-driven cart changes, batch actions, address saves, default address changes, and ambiguous matches.
- Clarification is required when key slots are missing, such as budget, party size, contact phone, or a unique dish target.

## Chosen Approach

Use a ReAct-style Agent with Tool Calling and Workflow Guardrails.

The LLM plans and decides which tools to request. Backend code owns retrieval, validation, database writes, confirmation, and final response contracts. This keeps the system demonstrably agentic while avoiding uncontrolled LLM side effects.

Rejected alternatives:

- A lightweight router plus RAG would be simpler and stable, but it has weaker Agent value for the resume goal.
- A multi-agent planner/executor/verifier system would sound more advanced, but it is too complex for the current project stage and would make demos harder to stabilize.

## Architecture

```text
Frontend Assistant UI
  -> Assistant API
    -> Agent Orchestrator
      -> Agent Planner / ReAct Decision
      -> Tool Registry
        -> User Context Tool
        -> Hybrid RAG Tool
        -> Recommendation Tool
        -> Cart Tool
        -> Address Tool
      -> Confirmation Manager
      -> Grounded Response Generator
      -> Assistant Session Store
```

Core principle: the LLM understands and plans; deterministic backend components retrieve, validate, execute, and evaluate.

## Backend Components

### Assistant API

`POST /assistant/chat` remains the main entrypoint. It receives user messages and optional `session_id` / `user_id`, then delegates to the orchestrator.

The response contract should support:

- natural-language message
- response type
- recommendations
- comparisons or knowledge results
- citations
- pending confirmation action
- executed actions
- suggested next actions

Suggested response shape:

```json
{
  "session_id": "abc",
  "message": "我推荐这几道菜，是否加入购物车？",
  "response_type": "recommendation",
  "recommendations": [],
  "citations": [],
  "pending_action": {
    "action_id": "pa_123",
    "type": "cart_add",
    "summary": "将 3 道菜各 1 份加入购物车",
    "items": []
  },
  "executed_actions": [],
  "suggested_actions": []
}
```

User confirmation can be handled through the same chat endpoint with messages such as `确认` or `取消`. A separate action endpoint can be added later if the UI needs explicit buttons:

```text
POST /assistant/actions/{action_id}/confirm
POST /assistant/actions/{action_id}/cancel
```

### Agent Orchestrator

The orchestrator owns the turn-level workflow:

```text
Load session
-> call Agent Planner
-> check missing slots
-> execute retrieval / recommendation / parse tools
-> decide whether confirmation is required
-> execute safe actions or store pending actions
-> generate grounded response
-> persist session state
```

It is the right place to enforce that only one pending action can be active per session unless the user explicitly starts a new task.

### Agent Planner

The planner uses the LLM to convert a message and session context into a structured decision.

Expected decision shape:

```json
{
  "intent": "recommendation | knowledge | cart_action | address_action | mixed_task | unsupported",
  "reasoning_summary": "用户想要川菜推荐并可能加购",
  "tool_plan": [
    {
      "tool": "recommend_dishes",
      "arguments": {
        "query": "川菜 下饭",
        "budget": 100,
        "party_size": 2
      },
      "requires_confirmation": false
    }
  ],
  "missing_slots": [],
  "needs_confirmation": false
}
```

The prompt should explicitly distinguish:

- knowledge query: asks what exists or asks facts
- recommendation: asks for personalized selection
- cart action: asks to mutate cart
- address action: asks to save or manage address
- mixed task: combines recommendation/query with a later mutation

### Tool Registry

Tools are registered with schema, permission requirement, side-effect classification, and handler.

Each tool returns a common result:

```json
{
  "ok": true,
  "tool_name": "recommend_dishes",
  "data": {},
  "evidence": [],
  "requires_confirmation": false,
  "error": null
}
```

Recoverable tool failures should return structured errors instead of leaking exceptions:

```json
{
  "ok": false,
  "error": {
    "code": "AMBIGUOUS_DISH",
    "message": "找到了多个同名菜品",
    "candidates": []
  }
}
```

### Confirmation Manager

The confirmation manager controls operations that write user data.

Direct execution is allowed when:

- the user is authenticated
- the target is explicit and unique
- the quantity is small and clear
- the action does not affect default address or other persistent preference

Confirmation is required for:

- recommendation-driven cart additions
- batch cart additions
- address creation, update, delete, or default-address changes
- ambiguous dish or merchant matches
- unusually large quantity or total price

Pending action state:

```json
{
  "action_id": "pa_123",
  "type": "cart_add",
  "items": [{"dish_id": 11, "quantity": 1}],
  "summary": "将鱼香肉丝 1 份加入购物车",
  "created_at": "2026-04-24T19:00:00",
  "expires_at": "2026-04-24T19:10:00"
}
```

### Session State

Session state should store enough context for natural follow-up messages:

```json
{
  "session_id": "abc",
  "user_id": 1,
  "last_intent": "mixed_task",
  "pending_action": {},
  "last_evidence_ids": ["dish_11", "merchant_2"],
  "slots": {
    "budget": 100,
    "party_size": 2,
    "exclude_allergens": ["花生"]
  }
}
```

This enables follow-ups such as `确认`, `换一个便宜点的`, `不要辣的`, and `只加前两个`.

## Hybrid RAG Design

The RAG pipeline should optimize both recall and accuracy:

```text
User query
-> Query Rewrite
-> Dense Recall
-> Metadata Recall
-> Keyword Recall
-> Merge and deduplicate
-> SQL hard filters
-> Rerank
-> Evidence Pack
-> Grounded Response
```

### Indexing

Use separate Pinecone namespaces for merchants and dishes.

Merchant metadata:

- `merchant_id`
- `name`
- `description`
- `homepage_category`
- `merchant_tags`
- `business_hours`
- `delivery_fee`
- `min_order_amount`
- `district`
- `rating`

Dish metadata:

- `dish_id`
- `merchant_id`
- `merchant_name`
- `dish_name`
- `description`
- `cuisine_type`
- `flavor_profile`
- `ingredients`
- `allergens`
- `cooking_method`
- `price`
- `is_recommended`

Vector text should be written as semantic documents rather than raw field dumps:

```text
菜品: 鱼香肉丝
商家: 兰姨小炒
菜系: 川味麻辣
口味: 酸甜微辣、下饭、微辣
价格: 28元
适合场景: 两人工作日晚餐、米饭搭配
配料: 猪里脊、木耳、胡萝卜
过敏原: 无花生
```

This improves recall for natural language queries such as `下饭一点`, `不太辣`, and `两个人预算 100`.

### Query Rewrite

The rewriter should produce multiple semantic queries and hard filters.

Example:

```json
{
  "semantic_queries": [
    "川菜 下饭 微辣 两人餐",
    "100元以内 川味菜 不含花生",
    "适合两人分享的川菜"
  ],
  "hard_filters": {
    "cuisine_type": ["川菜", "川味麻辣"],
    "price_per_dish_max": 50,
    "exclude_allergens": ["花生"]
  }
}
```

### Multi-Route Recall

Each retrieval pass should combine:

1. Dense recall from Pinecone embeddings.
2. Metadata recall by cuisine, price, allergen, merchant category, district, and tags.
3. Keyword recall for exact or fuzzy merchant and dish names.

Do not answer directly from top 3 vector results. First build a candidate pool of roughly 30 to 50 records, then filter and rerank.

### Hard Filters

These constraints must be enforced by code:

- budget
- party size
- allergen exclusion
- dish availability
- merchant open status
- unique target requirement for direct actions
- authenticated user requirement for mutations

The LLM may extract these constraints, but it should not be trusted to enforce them.

### Reranking

Use a blended score:

```text
final_score =
  0.45 * semantic_score
+ 0.20 * keyword_score
+ 0.15 * merchant_rating
+ 0.10 * recommendation_boost
+ 0.10 * constraint_match_score
```

An LLM reranker can be added after deterministic filtering to judge fit among already-valid candidates. It must not override hard constraints.

### Evidence Pack

The RAG output should return structured evidence:

```json
{
  "source_type": "dish",
  "dish_id": 11,
  "merchant_id": 1,
  "title": "鱼香肉丝｜兰姨小炒",
  "facts": {
    "price": 28,
    "cuisine_type": "川味麻辣",
    "flavor_profile": "酸甜微辣",
    "allergens": [],
    "merchant_rating": 4.8
  },
  "why_matched": ["匹配川菜", "单价符合预算", "未命中花生过敏原"],
  "citation": "川味麻辣；酸甜微辣；配料为猪里脊、木耳、胡萝卜"
}
```

The response generator should use this evidence pack and avoid unsupported claims.

## Core Workflows

### Recommendation Then Cart

User:

```text
帮我推荐几种川菜并加入购物车
```

Flow:

```text
Planner -> mixed_task
Slot check -> budget and party size missing
Assistant asks clarification
```

After user says:

```text
2个人，100以内，不要花生
```

Flow:

```text
recommend_dishes
-> Hybrid RAG
-> hard filter budget and allergens
-> return top 3 recommendations
-> create pending cart action
-> ask for confirmation
```

After user says:

```text
确认
```

Flow:

```text
commit_cart_action
-> CartService.add_item
-> response action_completed
```

### Explicit Cart Action

User:

```text
把鱼香肉丝加一份到购物车
```

Flow:

```text
search_catalog("鱼香肉丝")
-> if unique dish: add directly
-> if multiple matches: ask user to choose merchant/dish
```

### Address Save

User:

```text
帮我将以下地址加入地址管理：上海市静安区南京西路818号，联系人张三，电话13800000000
```

Flow:

```text
parse_address
-> validate required fields
-> geocode if longitude/latitude are missing
-> prepare pending address action
-> ask confirmation
-> commit_address_action after confirmation
```

### Knowledge Question

User:

```text
有哪些咖啡甜品店？几点营业？
```

Flow:

```text
search_catalog(source_type=merchant)
-> retrieve merchant evidence
-> answer with citations
```

## Mapping To Current Codebase

Reuse current components where possible:

- `service/assistant_service.py`: keep as API-facing facade.
- `service/agent_core.py`: evolve into `AgentPlanner`.
- `service/assistant_retriever.py`: split or internally reorganize into query rewrite, retrieval, filtering, and rerank.
- `service/grounded_responder.py`: keep as grounded response generator.
- `service/tool_registry.py`: extend with schema, permissions, and confirmation metadata.
- `service/tools/cart_tool.py`: support explicit add and staged confirmation flow.
- `service/tools/address_tool.py`: support validated address parsing and staged confirmation flow.
- `tools/assistant_vector_store.py`: keep as Pinecone/DashScope adapter.
- `service/assistant_session_store.py`: expand to store slots, evidence IDs, and pending actions.

Suggested new files:

```text
service/assistant_orchestrator.py
service/agent_planner.py
service/agent_state.py
service/confirmation_manager.py
service/rag_query_rewriter.py
service/rag_retriever.py
service/rag_reranker.py
service/rag_evaluator.py
service/tools/catalog_tool.py
service/tools/recommendation_tool.py
```

## Evaluation

Create `tests/eval/assistant_rag_cases.jsonl`. Each case should include:

- user query
- expected source IDs or accepted categories
- hard constraints
- expected behavior, such as answer, clarification, confirmation, or tool execution

Metrics:

- `recall@5`: expected merchant or dish appears in top 5 candidate pool.
- `precision@3`: top 3 recommendations match the expected category or intent.
- `constraint_pass_rate`: budget, allergen, cuisine, and availability constraints are all satisfied.
- `citation_coverage`: each recommendation or factual answer has a citation.
- `tool_success_rate`: cart and address tool calls complete when expected.
- `clarification_accuracy`: missing information triggers the correct follow-up question.

Add a script:

```text
tools/evaluate_assistant_rag.py
```

The script should run retrieval and flow-level checks, then print a compact metric report for demos and README documentation.

## Testing Strategy

Unit tests:

- query rewrite extracts semantic queries and filters
- retriever merges dense, metadata, and keyword results
- hard filters reject invalid candidates
- reranker orders valid candidates predictably
- tool registry rejects unknown tools and invalid params
- confirmation manager gates side-effect operations

Flow tests:

- `推荐川菜` asks for clarification
- `2人100元不要花生` returns recommendations and pending cart action
- `确认` commits cart action
- explicit unique dish add directly updates cart
- ambiguous dish name asks user to choose
- address save creates pending action
- address confirmation writes to address table
- knowledge query answers with citations

Frontend tests:

- assistant renders clarification
- assistant renders recommendations and citations
- assistant renders pending action confirmation
- assistant renders action completed
- API interceptor handles assistant errors

## Implementation Phases

### Phase 1: Agent State Machine And Confirmation

Implement orchestrator, planner contract, session state, pending action, and cart confirmation. This creates the most important demo flow: recommend dishes and add them to cart.

### Phase 2: Hybrid RAG Upgrade

Implement multi-query rewrite, dense + metadata + keyword recall, SQL hard filters, rerank, and evidence pack.

### Phase 3: Address Management Agent

Implement address parsing, geocoding integration, validation, pending address action, and confirmation.

### Phase 4: Evaluation And Resume Packaging

Add eval cases, metric script, README architecture section, and final resume bullet points.

## Resume Description

Recommended resume wording:

> Designed and implemented a smart ordering LLM Agent using ReAct Planning and Tool Calling to decompose natural-language requests into catalog search, personalized recommendation, cart operations, and address management. Added confirmation guardrails for side-effect tools to prevent unsafe database writes. Built a Hybrid RAG pipeline with LLM Query Rewrite, Pinecone dense retrieval, metadata and keyword recall, SQL hard-constraint filtering, reranking, and citation evidence packs. Evaluated retrieval quality with recall@5, precision@3, constraint pass rate, citation coverage, and tool success rate.

## Acceptance Criteria

The design is complete when the implemented system can demonstrate:

1. A knowledge query returns merchant or dish facts with citations.
2. A sparse recommendation request asks for missing slots.
3. A constrained recommendation returns valid dishes that satisfy budget, cuisine, and allergen constraints.
4. A recommendation-plus-cart request creates a pending cart action and commits it after confirmation.
5. An explicit unique cart request can execute directly.
6. An address save request parses fields, asks for confirmation, and writes the address after confirmation.
7. The RAG evaluation script reports recall and constraint metrics over a fixed case set.
