# Smart Assistant LLM-Routed RAG Upgrade Design

**Date:** 2026-04-23  
**Scope:** Upgrade the existing `smart_order` assistant from a rule-based phase-1 skeleton into a resume-quality LLM-routed, hybrid-RAG, evidence-grounded recommendation and comparison assistant, while keeping future tool execution boundaries for cart and address actions.

## Goal

Redesign the current assistant so it behaves like a real intelligent assistant rather than a rule template engine. In this iteration, the assistant should:

- understand whether the user is greeting, asking for recommendations, comparing merchants, or asking grounded catalog questions,
- use hybrid RAG only when retrieval is actually needed,
- generate final answers with an LLM from grounded evidence rather than direct template stitching,
- produce a mixed response format with natural-language explanation, structured cards, and citations,
- preserve clean extension points for later business action tools such as add-to-cart and address management.

The main product goal is to make the assistant a strong engineering highlight for the project and for the user's resume.

## Why This Redesign Is Needed

The current phase-1 implementation established useful foundations, but it does not satisfy the original product requirement.

Current behavior and gaps:
- the request flow is effectively `parse -> retrieve -> compose`,
- intent routing is rule-based rather than LLM-first,
- greetings such as `Hi` can incorrectly fall into recommendation retrieval,
- the vector layer is not yet contributing real semantic recall,
- the final answer is composed from templates rather than grounded generation.

This means the current system is a good API/demo skeleton, but not yet the intended Agent + RAG assistant.

## Confirmed Product Decisions

1. The assistant remains one of the most important showcase features in the project.
2. This upgrade should prioritize **recommendation and merchant comparison** over write actions.
3. The assistant should use a **mixed response style**:
   - natural-language explanation first,
   - structured recommendation/comparison cards second,
   - explicit citations/evidence third.
4. This iteration should support:
   - greeting and small talk routing,
   - dish recommendation,
   - merchant comparison,
   - grounded knowledge answers over merchant/dish metadata.
5. This iteration should **not yet execute** real cart writes or address writes.
6. However, the architecture must preserve future tool boundaries for:
   - `add_to_cart`,
   - `save_address`,
   - related controlled business actions.
7. Existing merchant and dish metadata work should be reused as the retrieval knowledge base.
8. Existing external LLM, embedding, and Pinecone infrastructure should be reused where practical.

## Recommended Approach

Adopt an **LLM-routed hybrid-RAG assistant** with clear separation between:

- intent routing,
- constraint resolution,
- retrieval,
- grounded response generation,
- future tool invocation.

This is the best fit because it gives the assistant a real "intelligence" layer without collapsing the design into an uncontrolled general agent. It also keeps the system testable: retrieval can be validated separately from generation, and future business tools can be introduced without rewriting the recommendation core.

## Alternatives Considered

### Option A — Recommended: LLM-routed hybrid RAG with grounded generation
- LLM decides the path.
- Retrieval runs only for recommendation/comparison/grounded QA.
- LLM generates the final mixed-format answer from evidence.
- Future tools are defined architecturally but not executed yet.

**Why recommended:** best balance of assistant quality, controllability, demo value, and future extensibility.

### Option B — Keep rule routing and only upgrade final answer generation
- Keep current parser as the main entry path.
- Use LLM only to rewrite or polish the answer.

**Tradeoff:** lower implementation cost, but not a convincing Agent/RAG story. It leaves the main intelligence problem unsolved.

### Option C — Full free-form action agent immediately
- Let the LLM decide retrieval and write actions freely.
- Implement cart/address execution in the same iteration.

**Tradeoff:** too broad for the next slice. Safety, UX, and testability all become weaker.

## Design

### 1. Scope of This Iteration

This iteration upgrades the assistant from a rule-driven recommendation shell into a read-only intelligent assistant with LLM-first orchestration.

Included:
- greeting/small-talk handling,
- recommendation intent detection,
- comparison intent detection,
- grounded merchant/dish Q&A,
- multi-turn clarification for missing recommendation constraints,
- hybrid retrieval over merchant and dish knowledge,
- evidence-grounded final response generation,
- frontend rendering for different assistant response types.

Explicitly excluded:
- real add-to-cart execution,
- real address creation/update execution,
- full autonomous planning agent behavior,
- long-term user profile personalization,
- arbitrary/open-ended tool calling.

### 2. High-Level Architecture

The assistant should be organized into six bounded components.

#### AssistantOrchestrator
The main backend entrypoint for assistant chat.

Responsibilities:
- load current session state,
- call the intent router,
- decide whether retrieval is needed,
- call constraint resolution,
- call retrieval and grounded response generation,
- store updated session state,
- return a stable API response contract.

This component coordinates; it does not contain retrieval internals or direct response-writing logic.

#### IntentRouter
This component makes the first LLM-assisted decision about what kind of request the user made.

Target intent classes for this iteration:
- `greeting`
- `recommendation`
- `comparison`
- `knowledge`
- `action_intent`
- `unsupported`

Examples:
- `Hi` -> `greeting`
- `推荐几种川菜` -> `recommendation`
- `比较兰姨小炒和午后豆房` -> `comparison`
- `这家店几点营业` -> `knowledge`
- `帮我加入购物车` -> `action_intent`

The router should also indicate:
- whether retrieval is required,
- whether clarification is likely needed,
- whether the input maps to a future tool boundary.

#### ConstraintResolver
This component normalizes user intent into structured recommendation or comparison constraints.

Expected fields include:
- `cuisine_types`
- `budget_max`
- `party_size`
- `flavor_preferences`
- `exclude_allergens`
- `merchant_targets`
- `meal_context`

Recommended implementation style:
- deterministic extraction for obvious fields,
- LLM normalization for fuzzy or mixed phrasing,
- explicit missing-field detection for clarification.

#### HybridRetriever
This is the retrieval core for recommendation, comparison, and grounded knowledge answers.

It should execute in three stages:
1. **Structured filtering**
   - cuisine,
   - budget,
   - allergens,
   - merchant target,
   - optionally merchant availability/business metadata.
2. **Vector recall**
   - query embeddings over merchant/dish knowledge chunks.
3. **Re-ranking**
   - combine business fit, semantic similarity, and explanation usefulness.

The retriever outputs evidence candidates, not end-user language.

#### GroundedResponder
This component calls the LLM to generate the final answer from:
- user message,
- normalized constraints,
- selected evidence,
- recent session context.

Output should include:
- `message` (natural-language answer)
- `response_type`
- structured cards
- citations
- suggested follow-up actions

The responder must be instructed to stay grounded in provided evidence and avoid unsupported claims.

#### ToolRegistry (future boundary)
This component is defined now but remains read-only in this iteration.

Future tools may include:
- `add_to_cart`
- `remove_from_cart`
- `save_address`
- `update_address`

In this iteration, if `action_intent` is detected, the assistant should acknowledge the intent and clearly state that execution is not yet enabled, rather than pretending success.

### 3. Data Flow

The assistant should follow this decision flow:

1. User message enters `AssistantOrchestrator`.
2. `IntentRouter` classifies the request.
3. Based on intent:
   - `greeting` -> answer directly with light LLM response, no retrieval.
   - `recommendation` -> resolve constraints, clarify if needed, otherwise retrieve and answer.
   - `comparison` -> resolve target merchants/criteria, retrieve comparison evidence, answer.
   - `knowledge` -> retrieve relevant merchant/dish evidence, answer.
   - `action_intent` -> respond with understood-but-not-executable action status.
   - `unsupported` -> explain scope and redirect.
4. Updated session state is stored.
5. Frontend renders the response by response type.

This flow prevents simple greeting traffic from accidentally turning into recommendation output and establishes a clean upgrade path to future tools.

### 4. Retrieval Design

The RAG system should be presented as a **hybrid retrieval pipeline tailored to food recommendation and merchant reasoning**, not as a generic chatbot memory layer.

#### Retrieval units
The indexed knowledge should continue to use two main unit types:

1. **Merchant evidence blocks**
   - merchant name,
   - merchant tags,
   - business hours,
   - address/location context,
   - merchant description,
   - cuisine coverage.

2. **Dish evidence blocks**
   - dish name,
   - dish description,
   - price,
   - cuisine type,
   - flavor profile,
   - ingredients,
   - allergens,
   - cooking method,
   - merchant linkage.

#### Retrieval behavior
The retrieval pipeline should emphasize three technical highlights:

1. **Constraint-aware filtering**
   Hard constraints eliminate business-invalid candidates before semantic recall.

2. **Semantic recall for fuzzy recommendation language**
   Queries like "想吃下饭一点的川菜" or "适合晚上加班吃" should benefit from embeddings rather than relying only on exact tags.

3. **Recommendation-oriented re-ranking**
   Final scores should blend:
   - constraint satisfaction,
   - semantic similarity,
   - merchant quality signals,
   - evidence usefulness for explanation.

#### Evidence packaging
The LLM should not receive raw ORM rows. The retriever should package compact evidence blocks that are easy to cite and reason over.

Each evidence block should include:
- title,
- short summary,
- matching reasons,
- stable identifiers,
- citation-ready snippet.

This reduces hallucination risk and makes the system more explainable.

### 5. Response Model and Frontend Rendering

The assistant response contract should be expanded from the current recommendation-only assumption into typed response modes.

Suggested response types:
- `greeting`
- `clarification`
- `recommendation`
- `comparison`
- `knowledge`
- `action_pending`
- `unsupported`

The frontend should render each response in a mixed format:

1. **Natural-language summary**
   The assistant first explains the answer conversationally.

2. **Structured result area**
   - recommendation cards for dishes/merchants,
   - comparison cards for merchant tradeoffs,
   - knowledge summary blocks where appropriate.

3. **Citation area**
   The assistant shows explicit evidence sources that support the answer.

This mixed design is important because it gives the system both conversational realism and stable demo presentation.

### 6. Future Agent Expansion Path

This design intentionally separates **read-only grounded assistance** from **tool execution**.

That makes the future expansion path simple:
- today: detect `action_intent`, explain that execution is not yet active,
- next phase: map the same routed action intent into an approved tool call,
- later: return execution result plus grounded explanation.

This means the recommendation/RAG core does not need to be rewritten when cart or address actions are enabled.

### 7. Testing Strategy

The redesign should be verified across four layers.

#### Router tests
Validate intent routing behavior such as:
- `Hi` -> greeting, no retrieval,
- `推荐几种川菜` -> recommendation,
- `比较两家商家` -> comparison,
- `帮我加入购物车` -> action intent.

#### Constraint and retrieval tests
Validate:
- constraint extraction and normalization,
- clarification when recommendation info is too sparse,
- hard filtering correctness,
- semantic recall participation,
- stable evidence packaging.

#### Grounded generation tests
Validate:
- final answer contains a natural-language explanation,
- structured cards align with evidence,
- citations reference the same entities used in the answer,
- no recommendation is fabricated when evidence is absent.

#### Frontend interaction tests
Validate:
- different response types render correctly,
- greeting does not render recommendation cards,
- clarification prompts appear when constraints are missing,
- recommendation and comparison cards render with citations,
- session continuity is preserved across turns.

### 8. Resume-Quality Technical Story

If implemented this way, the assistant can be described as:

- designed and implemented an **LLM-routed hybrid-RAG assistant** for an external-food-ordering product,
- built a **constraint-aware retrieval pipeline** combining structured filters, vector recall, and re-ranking,
- generated **evidence-grounded natural-language answers** with structured recommendation and comparison outputs,
- designed a **tool-ready Agent boundary** for later cart/address execution without coupling it to the retrieval core.

This is substantially stronger than describing the project as a simple chatbot.

## Non-Goals

- No real cart mutation or address mutation in this iteration.
- No unrestricted tool calling.
- No long-term user preference learning.
- No fully autonomous planning agent.
- No attempt to solve generic open-domain chat.

## Risks and Mitigations

- **Risk: LLM routing adds variability.**  
  Mitigation: keep intent classes narrow, use explicit schemas, and test greetings/recommendation/comparison boundaries directly.

- **Risk: retrieval returns semantically relevant but business-invalid results.**  
  Mitigation: apply hard filters before semantic recall and keep business constraints first-class.

- **Risk: grounded generation still hallucinates.**  
  Mitigation: package compact evidence blocks, require citations, and test unsupported/no-evidence cases explicitly.

- **Risk: future write actions become tangled with read-only RAG logic.**  
  Mitigation: preserve a separate tool registry boundary and treat action intent as a distinct response path now.
