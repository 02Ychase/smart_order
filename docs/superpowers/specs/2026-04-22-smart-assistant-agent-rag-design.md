# Smart Assistant Agent & RAG Design

**Date:** 2026-04-22
**Scope:** smart_order existing-codebase intelligent assistant, phase-1 RAG-first assistant with phase-2 action-agent expansion

## Goal

Design a standout intelligent assistant for `smart_order` that can act as a multi-turn food recommendation and restaurant knowledge assistant in phase 1, then evolve naturally into a tool-using business agent in phase 2.

The first phase should emphasize engineering credibility rather than generic chat. It should clarify the user’s constraints, retrieve grounded merchant and dish knowledge from the existing catalog, compare options, and generate explainable recommendations. The second phase should reuse the same architecture to support controlled business actions such as add-to-cart and address management.

## Confirmed Product Decisions

1. The assistant is one of the project’s most important showcase features and should be designed as a **resume-quality engineering highlight** rather than a simple chatbot.
2. The overall emphasis is **engineering execution first**, but the RAG system must still contain clear technical standout points.
3. Phase 1 should focus on **RAG / question-answering / recommendation demo quality**, not on full business execution.
4. The strongest phase-1 scenarios are:
   - dish recommendation,
   - constraint-aware filtering,
   - merchant comparison,
   - grounded knowledge Q&A.
5. The assistant should follow a **multi-turn clarification** interaction model rather than only single-turn direct answers.
6. Phase 1 should **not depend on user profile personalization**. It should operate mainly on merchant and dish knowledge, not on current cart, address, or long-term user preference data.
7. The implementation may **reuse the existing external LLM, Pinecone, and embedding setup**.
8. The design should explicitly include a **phase-2 action-agent path** for cart and address operations, but phase 1 should not execute those write actions yet.

## Existing Context

The current codebase already provides several important foundations for this design:

- `ui/src/components/home/FloatingAssistant.vue` already mounts a visible assistant panel, but it is currently static UI with no real conversation flow.
- `ui/src/App.vue` already hosts the main homepage shell and is the natural place to keep the assistant globally available.
- `api/models/catalog.py` already contains retrieval-friendly merchant and dish metadata including merchant tags, business hours, detailed addresses, cuisine type, flavor profile, ingredients, allergens, and cooking method.
- `api/routes/catalog.py` already exposes live merchant and dish data that can be reused for grounding and indexing.
- `api/routes/agent_context.py` exists, but it currently returns placeholder data and should not be treated as a production-ready assistant memory layer.
- `tools/pinecone_tool.py` and related dependencies show that the project already has vector indexing infrastructure and embedding dependencies available.
- The current assistant-related code under `agent/assistant.py` is closer to an earlier intent-routing experiment than to the grounded RAG assistant needed here.

This means the project already has:
- meaningful restaurant and dish knowledge,
- a basic assistant UI entrypoint,
- backend API and ORM surfaces,
- an external-vector retrieval foundation.

What it does **not** yet have is:
- a production assistant API,
- a multi-turn conversation state model,
- a structured retrieval pipeline,
- a recommendation-oriented answer composer,
- a safe tool-execution path.

## Recommended Approach

Adopt a **RAG-first assistant architecture with explicit phase separation**.

Phase 1 should build a grounded assistant that asks clarification questions, parses constraints, runs hybrid retrieval over merchant and dish knowledge, and produces structured, explainable recommendations. Phase 2 should build on the same orchestration boundary to add white-listed tool execution for business actions like cart and address management.

This is the best fit because:
- it produces a strong demo sooner than a full action agent,
- it keeps the first release focused on answer quality and retrieval quality,
- it avoids introducing risky write paths before the answer system is trustworthy,
- it still gives the project a clear and impressive “Agent evolution” story.

## Alternatives Considered

### Option A — Recommended: RAG-first assistant with later tool execution
- Phase 1: clarification + retrieval + recommendation + explainable answers.
- Phase 2: controlled tool calling for cart and address actions.

**Why recommended:** strongest balance of short-term demo quality, engineering credibility, and long-term extensibility.

### Option B — Retrieval-heavy recommendation engine first
- Focus almost entirely on hybrid retrieval, ranking, and recommendation quality.
- Leave agent/tool architecture mostly unspecified for later.

**Tradeoff:** strong RAG story, but weaker assistant/product story. It risks feeling like a search demo rather than an intelligent assistant.

### Option C — Full action-agent platform immediately
- Design and implement planning, tool calling, permissions, and business execution from the beginning.

**Tradeoff:** the overall story is ambitious, but the first delivery scope becomes too broad. The system is more likely to feel unfinished in both RAG quality and execution safety.

## Design

### 1. High-level architecture

The assistant should be organized into five layers:

1. **Assistant UI layer**
   - hosts the chat panel,
   - displays clarifying questions,
   - renders recommendation cards and comparison views,
   - shows citations and structured results.

2. **Assistant API orchestration layer**
   - receives user messages,
   - reads and updates conversation state,
   - decides whether to clarify or retrieve,
   - coordinates retrieval and answer generation,
   - returns a structured response contract for the frontend.

3. **RAG retrieval layer**
   - performs structured filtering,
   - performs vector recall,
   - performs final re-ranking,
   - packages grounded snippets for answer generation.

4. **Domain knowledge layer**
   - uses existing merchant and dish metadata as the system’s source of truth,
   - supports grounding, comparison, and recommendation reasoning.

5. **Tool execution layer (phase 2)**
   - exposes safe business actions behind white-listed tools,
   - is intentionally not active for write operations in phase 1.

This layering keeps the first phase grounded and controllable while making the second phase a natural extension rather than a redesign.

### 2. Assistant interaction model

The assistant should behave as a **multi-turn clarification assistant**.

Example behavior:
- User: “推荐几种川菜。”
- Assistant: asks follow-up questions such as budget, party size, spiciness preference, allergy constraints, or meal occasion.
- User provides more conditions.
- Assistant retrieves candidates and returns recommendations with reasons and citations.

This interaction model is preferred over single-turn direct answers because the target domain naturally involves missing constraints. It also creates a stronger product feel and a more credible agent story.

### 3. Core backend components

#### Assistant Gateway
The gateway is the public orchestration boundary for the assistant.

Responsibilities:
- accept messages and session identifiers,
- load conversation state,
- route the request to clarification or retrieval flow,
- call the answer composer,
- return a stable assistant response schema.

The gateway should not contain direct SQL or vector-store logic.

#### Conversation State Manager
This component stores short-lived session context for multi-turn interactions.

Phase-1 state should include:
- original user request,
- extracted constraints,
- missing constraints still worth clarifying,
- last retrieved candidates,
- prior assistant questions.

This is session memory, not long-term user memory.

#### Constraint Parser
This component converts natural-language restaurant requests into structured constraints.

Typical extracted fields include:
- cuisine type,
- budget ceiling,
- party size,
- allergy exclusions,
- flavor preferences,
- meal occasion,
- merchant-vs-dish comparison intent.

The recommended implementation style is **rule-assisted extraction plus LLM completion**. Common fields should be extracted deterministically where possible, while the model handles more ambiguous phrasing.

#### Hybrid Retriever
This is the core of the RAG system.

The retriever should run in three steps:
1. **Structured filter** for hard constraints such as cuisine, budget, allergens, merchant open-state, or explicit comparison targets.
2. **Vector recall** for semantic matching of taste, scenario, or freeform descriptive intent.
3. **Re-rank** to prioritize candidates based on constraint satisfaction, semantic relevance, and answer usefulness.

#### Answer Composer
This component turns grounded retrieval outputs into structured assistant responses.

Its responsibilities include:
- deciding whether to answer or ask another clarifying question,
- generating recommendation reasons,
- generating merchant comparison summaries,
- attaching citations,
- providing suggested next actions.

#### Tool Registry (phase 2)
This component should be defined in the architecture now, even though phase 1 does not execute write actions.

Future examples:
- `add_dish_to_cart`
- `remove_cart_item`
- `create_user_address`
- `update_user_address`
- `set_default_address`

The model should never be allowed to invent new write tools or call arbitrary endpoints.

### 4. RAG system design

The RAG system should be designed as an **external-knowledge-backed hybrid retrieval system for food recommendation and merchant reasoning**, not as a generic chat memory system.

#### Knowledge unit design
The indexed data should be split into two retrieval-friendly document types:

1. **Merchant profile chunks**
   - merchant name,
   - merchant tags,
   - business hours,
   - detailed address,
   - address note,
   - delivery or locality cues,
   - high-level cuisine coverage.

2. **Dish knowledge chunks**
   - dish name,
   - dish description,
   - price,
   - cuisine type,
   - flavor profile,
   - ingredients,
   - allergens,
   - cooking method,
   - merchant association.

This split makes merchant comparison and dish recommendation both first-class retrieval tasks.

#### Hybrid retrieval behavior
The assistant should not rely on vector similarity alone.

The retrieval pipeline should combine:
- **hard filtering** for clear constraints,
- **semantic recall** for fuzzy intent,
- **ranking** for recommendation quality.

This gives phase 1 two strong technical highlights:
1. **constraint-aware retrieval** rather than naive semantic search,
2. **recommendation-oriented RAG** rather than only factual question answering.

#### Explainability and grounding
Each recommendation should be grounded in explicit evidence, for example:
- cuisine match,
- budget fit,
- allergen exclusion match,
- business-hours compatibility,
- merchant specialty coverage,
- descriptive flavor similarity.

Responses should cite the merchant or dish knowledge used rather than sounding like an ungrounded chat model.

### 5. Agent system design

The long-term assistant should evolve into a **controlled business agent**, not a free-form autonomous agent.

#### Phase 1 agent role
In phase 1, the assistant acts as a **grounded advisor**:
- clarifies,
- retrieves,
- compares,
- recommends,
- suggests next steps.

It does not mutate cart or address state.

#### Phase 2 agent role
In phase 2, the assistant becomes a **tool-using agent** that can execute selected actions after explicit confirmation.

Recommended internal modules:
- **Intent Router** — classifies question-answering, recommendation, comparison, and future action requests.
- **Lightweight Planner** — decides whether more clarification is needed and which retrieval/tool path to run.
- **Tool Selector** — maps approved action intents to white-listed tools.
- **Action Guardrail** — blocks unapproved or incomplete write actions and requires confirmation.

The design should favor predictable orchestration over unconstrained autonomous planning.

### 6. Data flow and API design

#### Main phase-1 request flow
Frontend assistant input should flow as follows:

`FloatingAssistant` → `POST /assistant/chat` → conversation-state load/update → constraint parsing → clarify or retrieve → answer composition → structured response → frontend rendering

#### Assistant API contract
The assistant should expose a dedicated chat endpoint.

**Recommended endpoint:** `POST /assistant/chat`

Recommended response fields:
- `session_id`
- `message`
- `needs_clarification`
- `clarification_question`
- `extracted_constraints`
- `recommendations`
- `comparisons`
- `citations`
- `suggested_actions`

Recommended support endpoint:
- `GET /assistant/health`

This allows runtime checks for LLM configuration, vector-store connectivity, and retrieval readiness.

#### Internal retriever contract
The orchestration layer should call retrieval through a stable internal contract.

Retriever input should include:
- original user query,
- extracted constraints,
- retrieval target (`dish`, `merchant`, `mixed`),
- top-k value.

Retriever output should include:
- matched knowledge items,
- source type,
- ranking scores,
- structured summaries,
- grounding snippets.

### 7. Frontend response design

The frontend should not render only a plain chat paragraph.

Recommended phase-1 assistant UI output blocks:
- assistant message text,
- extracted-condition tags,
- recommendation cards,
- merchant comparison table or list,
- citations/grounding section,
- suggested next-step chips.

This makes the assistant feel like a product feature rather than a raw chatbot.

### 8. Safety and control design

The architecture should enforce clear safety boundaries from the beginning.

#### Phase-1 safety boundaries
- no write actions through the assistant,
- no user-profile personalization dependency,
- no ungrounded answer path when retrieval is required,
- graceful fallback when LLM or vector services fail.

#### Phase-2 safety boundaries
- write operations only through white-listed tools,
- authenticated-user requirement,
- explicit confirmation before mutation,
- validated arguments before execution,
- audit logging for all mutations.

This gives the future action-agent path production-style guardrails without complicating phase 1.

### 9. Observability and evaluation

This project should track assistant quality as an engineering system, not only as a UI feature.

Recommended metrics and logs:
- request type distribution,
- clarification-turn count,
- constraint extraction success/failure,
- retrieval result quality against hard constraints,
- citation coverage,
- LLM/vector failure modes,
- phase-2 tool-call audit events later.

This is especially valuable for resume and interview discussion because it shows system evaluation maturity.

### 10. Testing strategy

Phase-1 verification should be layered.

#### Backend unit/integration tests
- constraint parser tests for cuisine, budget, people count, allergens, and mixed phrasing,
- retriever tests for hard-filter correctness,
- answer composer tests for recommendation structure and citation presence,
- API contract tests for `/assistant/chat` and `/assistant/health`.

#### Frontend behavior tests
- clarification question rendering,
- recommendation card rendering,
- comparison rendering,
- citation display,
- error/fallback rendering.

This keeps the assistant verifiable even while it depends on external AI infrastructure.

## Phase Plan

### Phase 1 — RAG-first grounded assistant
Build:
- assistant UI upgrade,
- assistant API,
- session conversation state,
- constraint parser,
- hybrid retriever,
- structured answer composer,
- recommendation/comparison/Q&A flow.

Do not build yet:
- add-to-cart execution,
- address writes,
- long-term personalization,
- autonomous multi-step action planning.

### Phase 2 — Controlled action agent
Build on the same architecture to add:
- cart tool calls,
- address tool calls,
- explicit confirmation flow,
- mutation audit trail,
- optional use of live user context.

## Non-Goals

The following are explicitly out of scope for phase 1:
- autonomous checkout or payment actions,
- long-term user preference learning,
- full order-history reasoning,
- unrestricted agent planning,
- open-ended function calling to arbitrary services,
- replacing the existing catalog APIs.

## Risks and Mitigations

- **Risk: the assistant becomes a generic chat wrapper.**  
  Mitigation: keep the phase-1 scope anchored on clarification, retrieval, recommendation, comparison, and citations.

- **Risk: vector retrieval looks impressive but misses hard constraints.**  
  Mitigation: always apply structured filters before semantic recall when constraints are explicit.

- **Risk: current assistant context endpoint suggests nonexistent personalization depth.**  
  Mitigation: keep phase-1 design honest and avoid claiming personalization on top of placeholder context.

- **Risk: action-agent scope creeps into phase 1 and weakens delivery quality.**  
  Mitigation: lock write actions behind phase-2 planning only.

- **Risk: external service dependence harms demo reliability.**  
  Mitigation: add health checks, graceful degradation, and deterministic fallback messaging.

## Resume Highlight Framing

This design should support resume phrasing along the lines of:

- Designed a multi-turn intelligent assistant for a local-services ordering system using a **RAG-first, agent-evolution architecture**.
- Built a **constraint-aware hybrid retrieval pipeline** combining structured filtering, vector recall, and re-ranking for recommendation and grounded Q&A.
- Implemented **explainable recommendation responses** grounded in merchant and dish metadata including cuisine, price, allergens, flavor, and business context.
- Defined a phased evolution path from **grounded advisory assistant** to **controlled tool-using agent** for cart and address operations.
