# LangGraph Agent + Advanced RAG Design

## Goal

Refactor the smart_order assistant backend from a rule-heavy custom orchestrator into a LangGraph-based agent runtime with advanced RAG retrieval, short-term session memory, long-term user memory, function-specific prompts, and reversible local write actions.

The target assistant behavior is:

- Answer recommendation and knowledge questions directly without requiring budget, party size, or other optional slots.
- Use LLM structured planning instead of regex as the primary understanding layer.
- Execute reversible local write actions directly for cart, address, and user preference operations.
- Support undo for those local reversible actions through an action journal.
- Use a stronger RAG system with multi-route recall, fusion, reranking, diversification, grounding, and measurable retrieval quality.

## Current Problems

The current `/assistant/chat` path is implemented by `AssistantService -> AssistantOrchestrator -> AgentPlanner -> ToolRegistry -> RagRetriever`. It works, but several responsibilities are tangled:

- `AssistantOrchestrator`, `AgentPlanner`, and `RagQueryRewriter` all perform overlapping intent or slot extraction.
- Recommendation flow treats budget and party size as required clarification slots, which slows common user requests.
- Regex is the primary extraction mechanism in several places, so unusual phrasing, multi-language queries, or implicit constraints are brittle.
- Session memory is a custom in-memory dict and is not durable.
- Pending confirmation is the main protection for write actions, but the desired product behavior is direct execution with undo for local reversible actions.
- RAG currently has useful foundations, but recall and ranking are mostly dense vector plus SQL filtering plus a simple weighted reranker.

## Core Decisions

Use LangGraph as the agent runtime and state machine. Use LangChain for model calls, tool definitions, structured output, and prompt integration.

Use LangGraph checkpointers for short-term thread memory. Each frontend `session_id` maps to a LangGraph `thread_id`.

Use database-backed action journaling for reversible local write actions. LangGraph state can store recent action IDs, but undo payloads and snapshots live in SQL.

Use separate, function-specific prompts instead of one global prompt. Prompts are attached to graph nodes and tools by responsibility.

Use advanced RAG as a standalone subsystem that receives structured retrieval plans from the agent and returns grounded evidence packs.

## Non-Goals

This design does not make external irreversible actions directly undoable. Order submission, payment, refund, and delivery operations need separate business cancellation or compensation flows.

This design does not rely on conversational text alone to restore deleted data. Undo must use deterministic snapshots or inverse operations in the action journal.

This design does not require replacing Pinecone immediately. Pinecone remains the dense vector store, with room to add sparse/hybrid retrieval.

## High-Level Architecture

```text
POST /assistant/chat
  -> LangGraph app.invoke(..., thread_id=session_id)
       load_context
       plan_with_llm
       route
         rag_retrieve
         execute_local_action
         undo_action
         general_answer
       record_action
       write_memory
       respond
  -> AssistantChatResponse
```

### Main Components

- `agent_graph.py`: builds and compiles the LangGraph state machine.
- `agent_state.py`: defines graph state, including messages, user_id, session metadata, recent evidence, recent actions, and loaded memories.
- `prompt_registry.py`: loads prompt files by stable keys.
- `planner_node.py`: turns user messages into structured plans.
- `rag_node.py`: calls the advanced RAG subsystem and returns evidence.
- `action_node.py`: executes cart/address/preference tools and records reversible actions.
- `undo_node.py`: resolves and executes undo requests.
- `memory_node.py`: extracts and stores durable user memories.
- `responder_node.py`: produces grounded final responses.
- `service/rag/`: owns retrieval planning, recall, fusion, filtering, reranking, diversification, and evaluation.
- `ActionJournalService`: persists before/after snapshots and undo metadata.
- `UserMemoryService`: persists and retrieves user preference memories.

## Agent State

LangGraph thread state should include:

```python
class SmartOrderAgentState(AgentState):
    user_id: int | None
    session_id: str
    active_topic: str | None
    loaded_user_memories: list[dict]
    recent_evidence: list[dict]
    recent_action_ids: list[str]
    current_plan: dict | None
    tool_results: list[dict]
```

The `messages` field from `AgentState` remains the canonical short-term conversation history.

State is scoped to a session/thread. It should not be treated as durable business data. Business facts are stored in SQL or Redis-backed services and reloaded into state at the start of each turn.

## Memory Design

### Short-Term Memory

Short-term memory is session-scoped and managed by LangGraph checkpointer.

Stored content:

- Recent messages.
- Current topic.
- Recent recommendation evidence IDs.
- Recent action IDs.
- Last successful tool result summaries.

Development can use `InMemorySaver`. Production should use a durable checkpointer, preferably database-backed. SQLite can be used for local development; Postgres/MySQL-compatible persistence should be considered for deployment.

### Long-Term Memory

Long-term memory is user-scoped and available across sessions.

Store examples:

- Food preferences: "prefers spicy Hunan dishes".
- Dietary constraints: "does not want peanuts".
- Merchant affinity: "often chooses coffee desserts".
- Interaction preferences: "likes concise answers".

Long-term memory should be structured, not raw chat logs. The memory writer node proposes candidate memories; backend policy decides whether to insert, update, ignore, or expire them.

Storage options:

- SQL for canonical user memory records.
- Redis for fast hot-cache reads.
- Optional vector memory index for semantic recall when memory volume grows.

### Action Journal

Action journal is required for undo.

Each local write action creates a record:

```json
{
  "action_id": "act_xxx",
  "session_id": "s1",
  "user_id": 123,
  "action_type": "cart_clear",
  "status": "completed",
  "undo_policy": "snapshot_restore",
  "before_snapshot": {"items": [{"dish_id": 11, "quantity": 2}]},
  "after_snapshot": {"items": []},
  "undo_tool": "restore_cart_snapshot",
  "natural_summary": "清空购物车"
}
```

Undo policies:

- `snapshot_restore`: restore a previous full state, e.g. cart before clear.
- `inverse_operation`: apply inverse mutation, e.g. remove item that was just added.
- `compensating_action`: business cancellation flow, reserved for future orders.
- `not_undoable`: irreversible action.

Initial reversible scope:

- Cart add/remove/clear.
- Address create/update/delete/default switch.
- User preference create/update/delete.

## Prompt Design

Use function-specific system prompts loaded through a prompt registry.

Suggested files:

```text
prompt/agent/planner.system.md
prompt/agent/query_rewrite.system.md
prompt/agent/answer_grounded.system.md
prompt/agent/memory_writer.system.md
prompt/agent/undo_resolver.system.md
prompt/tools/recommendation.system.md
prompt/tools/catalog_qa.system.md
prompt/tools/cart_action.system.md
prompt/tools/address_action.system.md
prompt/tools/preference_action.system.md
```

Prompt responsibilities:

- Planner prompt: classify intent and choose the next graph path.
- Query rewrite prompt: generate retrieval plans and optional filters.
- Grounded answer prompt: answer from evidence only.
- Memory writer prompt: extract durable memory candidates.
- Undo resolver prompt: map user undo language to an action journal target.
- Action prompts: convert natural language into tool parameters.

LLM outputs must use structured schemas. Free-form JSON cleaning should be replaced by model structured output where supported, with schema validation fallback.

## Planner Output

Planner output example:

```json
{
  "intent": "recommendation",
  "requires_rag": true,
  "action": null,
  "normalized_query": "辣的湘菜",
  "filters": {
    "cuisine_types": ["湘菜"],
    "flavor_preferences": ["辣"],
    "budget_max": null,
    "party_size": null,
    "exclude_allergens": []
  },
  "should_answer_directly": true
}
```

Budget, party size, and similar attributes are optional filters. The planner should not ask clarification for missing optional filters. Clarification is reserved for cases where a requested action cannot be executed safely because no target can be identified.

## Write Action Behavior

For cart, address, and preference mutations:

1. Planner identifies the action.
2. Action prompt/tool parser extracts parameters.
3. Tool executes directly.
4. Action journal records before and after state.
5. Response summarizes the completed action and mentions it can be undone.

Example response:

```text
已清空购物车。你可以继续说“撤回刚才的操作”来恢复清空前的购物车。
```

No confirmation step is used for the initial reversible scope.

## Advanced RAG Design

### Retrieval Units

Index multiple unit types:

- Dish unit: dish name, merchant, cuisine, flavor, ingredients, allergens, price, tags, scenarios.
- Merchant unit: merchant name, category, tags, business hours, delivery metadata, description.
- Menu section unit: category-level context such as "披萨意面/焗饭主食".
- User memory unit: structured preference memory converted to retrieval text.

Each unit stores:

- Stable ID, source type, source ID, merchant ID.
- Text used for embedding.
- Metadata for filtering.
- Citation snippet.
- Freshness/version fields.

### Query Planning

The query planner generates:

- `original_query`: raw user message.
- `normalized_query`: concise query for dense retrieval.
- `expansion_queries`: multiple semantic variants.
- `must_filters`: strict constraints.
- `should_filters`: ranking preferences.
- `source_types`: dish, merchant, memory, or mixed.
- `answer_mode`: recommendation, knowledge, comparison, action_support.

Example:

```json
{
  "normalized_query": "辣的湘菜",
  "expansion_queries": ["湘菜 香辣 下饭", "小炒 剁椒 辣味", "湖南菜 重口味"],
  "must_filters": {"is_available": true},
  "should_filters": {"cuisine_types": ["湘菜"], "flavor_preferences": ["辣"]},
  "source_types": ["dish"]
}
```

### Multi-Route Recall

Use multiple recall paths to maximize recall:

1. Dense semantic recall from Pinecone over dish and merchant namespaces.
2. Sparse/keyword recall over dish names, merchant names, ingredients, tags, and cuisine labels.
3. SQL metadata recall for exact fields and range conditions.
4. User memory recall for personal preferences.
5. Business recall for recommended dishes, high-rated merchants, and popular items.
6. Optional HyDE recall where the LLM generates a hypothetical ideal dish description and retrieves against that text.

Each recall path returns candidates with route-specific scores and explanations.

### Candidate Fusion

Merge all recall results by stable entity key:

```text
dish:<dish_id>
merchant:<merchant_id>
memory:<memory_id>
```

Use Reciprocal Rank Fusion (RRF) as the default route fusion method because it is simple, explainable, and robust across heterogeneous retrievers.

Candidate metadata should include:

- Which routes found it.
- Rank and score per route.
- Matched query terms.
- Matched filters.

### Filtering

Hard filters remove invalid candidates:

- Unavailable dishes.
- Explicit excluded allergens.
- Merchant mismatch when user names a specific merchant.
- Price constraints when stated as hard requirements.
- Delivery range when address context exists and the request implies deliverability.

Soft preferences influence ranking but do not remove candidates:

- Flavor preference.
- Cuisine preference when user wording is broad.
- Price friendliness.
- Merchant rating.
- Delivery speed.
- User historical preference.
- Business boost.

### Reranking

Use a two-stage ranking approach.

Stage 1: retrieval and fusion produce Top 50-100 candidates.

Stage 2: reranker scores candidates against the original user question and normalized query.

Preferred order:

1. Cross-encoder or hosted reranker when available.
2. LLM pairwise/listwise reranker for small Top N.
3. Local weighted reranker fallback.

Fallback formula:

```text
final_score =
  0.45 * rerank_relevance
+ 0.20 * dense_score
+ 0.10 * lexical_score
+ 0.10 * constraint_match
+ 0.05 * merchant_rating
+ 0.05 * user_preference_match
+ 0.05 * business_boost
```

Weights are initial values and should be tuned through evaluation.

### Diversification

After reranking, apply diversity rules:

- Avoid returning all top dishes from the same merchant unless the user specified that merchant.
- Avoid repeated dish names or near-duplicates.
- Prefer a mix of price bands when no budget is specified.
- Prefer a mix of categories when the query is broad.

### Grounding

The RAG subsystem returns evidence packs:

```json
{
  "source_type": "dish",
  "source_id": 31,
  "merchant_id": 3,
  "title": "小炒黄牛肉｜兰姨小炒",
  "facts": {
    "dish_name": "小炒黄牛肉",
    "merchant_name": "兰姨小炒",
    "price": 42,
    "cuisine_type": "湘菜",
    "flavor_profile": "鲜辣下饭"
  },
  "why_matched": ["湘菜", "鲜辣", "下饭"],
  "citation": "黄牛肉片现炒，芹菜和小米椒提香提辣。"
}
```

The answer node must only recommend entities present in evidence. If evidence is weak, it should say so and offer the closest matches without fabricating data.

## Evaluation

Expand the current `tests/eval/assistant_rag_cases.jsonl` into a small but representative RAG benchmark.

Metrics:

- `recall@5` and `recall@10`.
- `precision@3`.
- `MRR`.
- `nDCG@5` if graded relevance is added.
- Constraint pass rate.
- Diversity pass rate.
- Citation coverage.
- Latency p50/p95.

Initial acceptance targets for local catalog data:

- `recall@10 >= 0.90`
- `precision@3 >= 0.65`
- `constraint_pass_rate >= 0.95`
- `citation_coverage = 1.0`
- p95 retrieval latency under a practical local threshold agreed during implementation.

Evaluation cases should cover:

- Exact dish/category search.
- Synonym and colloquial search.
- Multi-language or mixed-language queries.
- Allergy exclusion.
- Merchant-scoped queries.
- Broad recommendations without budget.
- Follow-up queries using session memory.
- Undo-related references.

## API Contract

Keep the existing `AssistantChatRequest` and `AssistantChatResponse` shape where possible, but extend internal response metadata.

Useful additions:

- `memory_updates`: optional debug/admin field, normally hidden.
- `action`: completed action summary.
- `undo_available`: boolean.
- `evidence_debug`: only enabled in development.

Frontend can keep rendering `message`, `recommendations`, `citations`, `executed_actions`, and `pending_action` initially. Pending actions should disappear for reversible local actions and be replaced by completed action summaries.

## Migration Plan

Phase 1: Introduce LangGraph shell.

- Add graph state and nodes.
- Keep existing tools and services as callable business functions.
- Use in-memory checkpointer for tests.

Phase 2: Prompt registry and structured planner.

- Add prompt files.
- Replace regex-first planning with LLM structured output.
- Keep rule fallback only for service degradation.

Phase 3: Action journal and undo.

- Add SQL model and service for action records.
- Implement cart/address/preference reversible tools.
- Remove confirmation flow for reversible local actions.

Phase 4: Advanced RAG subsystem.

- Refactor current RAG modules into route-based recall, fusion, filtering, reranking, and diversification.
- Add sparse/keyword recall.
- Add richer evaluation cases.

Phase 5: Long-term memory.

- Add user memory store.
- Add memory writer node.
- Feed memory into planner and retrieval.

Phase 6: Cleanup and compatibility.

- Deprecate old `agent/assistant.py` path or keep as historical demo only.
- Remove duplicate regex extraction logic from orchestrator and rewriter.
- Update README and frontend docs.

## Testing Strategy

Unit tests:

- Planner structured output parsing.
- Prompt registry loading.
- Graph routing decisions.
- RAG query planning.
- Recall route merging and RRF fusion.
- Hard filter correctness.
- Reranker fallback scoring.
- Diversification behavior.
- Action journal snapshot creation.
- Undo resolution and execution.
- Memory writer candidate extraction.

Integration tests:

- Recommendation query returns evidence without budget clarification.
- "帮我推荐几个比较辣的湘菜" returns spicy Hunan candidates.
- Cart clear executes immediately and undo restores previous cart.
- Address delete executes immediately and undo restores the address.
- Follow-up query uses session memory.
- Long-term preference affects ranking without overriding explicit user request.

Regression tests:

- Existing auth, catalog, cart, address, and order routes continue to pass.
- Existing assistant response schema remains frontend-compatible.

## Risks And Mitigations

LLM planner may output invalid structures. Mitigate with strict schema validation, retries, and deterministic fallback.

RAG reranking may add latency. Mitigate with top-k caps, cache embeddings, cache frequent query plans, and use fallback weighted rerank when reranker is unavailable.

Long-term memory may over-personalize. Mitigate by treating memory as soft preference and always prioritizing explicit current user instructions.

Undo may restore stale state over newer changes. Mitigate by checking action ordering and refusing unsafe undo when dependent later actions exist.

Prompt sprawl can become hard to maintain. Mitigate with a prompt registry, prompt tests, and clear naming by graph node responsibility.

## References

- LangChain short-term memory: https://docs.langchain.com/oss/python/langchain/short-term-memory
- LangGraph memory: https://docs.langchain.com/oss/python/langgraph/add-memory
- RAG paper: https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html
- Pinecone hybrid search: https://docs.pinecone.io/docs/hybrid-search-and-sparse-vectors
- Pinecone reranking: https://docs.pinecone.io/guides/search/rerank-results
- HyDE: https://huggingface.co/papers/2212.10496
- RRF: https://colab.ws/articles/10.1145/1571941.1572114
