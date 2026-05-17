"""
Performance test script for the smart_order system.
Measures latency of each step in the agent pipeline.
"""

import time
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.db import SessionLocal
from service.agent_runtime.graph import build_agent_graph
from service.agent_runtime.nodes import LocalActionExecutor
from service.agent_runtime.planner import LangGraphAgentPlanner
from service.agent_runtime.runtime import AgentRuntimeContext
from service.rag.retriever import AdvancedRagRetriever
from service.user_memory_service import UserMemoryService
from langchain_core.messages import HumanMessage


def measure_latency(query: str, user_id: int = 1) -> dict:
    """Measure latency of each step in the agent pipeline."""
    results = {}

    # Initialize components
    session = SessionLocal()
    memory_service = UserMemoryService(session)
    planner = LangGraphAgentPlanner()
    retriever = AdvancedRagRetriever(session=session)

    # Build graph and runtime context
    graph = build_agent_graph()
    runtime = AgentRuntimeContext(
        planner=planner,
        retriever=retriever,
        action_executor=LocalActionExecutor(session),
        memory_service=memory_service,
    )

    # Prepare initial state
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "session_id": "test_session",
        "user_id": user_id,
    }

    # Measure total time
    start_total = time.time()

    # Run the graph with runtime injected via config
    config = {"configurable": {"thread_id": "test_thread", "runtime": runtime}}
    final_state = graph.invoke(initial_state, config)

    end_total = time.time()
    results["total"] = end_total - start_total

    # Get the response
    if final_state.get("response_payload"):
        results["response"] = final_state["response_payload"].get("message", "")
    else:
        results["response"] = "No response"

    session.close()
    return results


def measure_component_latency(query: str, user_id: int = 1) -> dict:
    """Measure latency of individual components."""
    results = {}
    session = SessionLocal()
    
    # 1. Measure memory loading
    memory_service = UserMemoryService(session)
    start = time.time()
    memories = memory_service.list_memories(user_id)
    results["memory_loading"] = time.time() - start
    results["memory_count"] = len(memories)
    
    # 2. Measure planning
    planner = LangGraphAgentPlanner()
    start = time.time()
    plan = planner.plan(query, {"user_id": user_id, "loaded_user_memories": memories})
    results["planning"] = time.time() - start
    results["plan_intent"] = plan.intent
    results["requires_rag"] = plan.requires_rag
    
    # 3. Measure RAG retrieval (if needed)
    if plan.requires_rag:
        retriever = AdvancedRagRetriever(session=session)
        start = time.time()
        evidence = retriever.retrieve(query, agent_plan=plan, memories=memories)
        results["rag_retrieval"] = time.time() - start
        results["evidence_count"] = len(evidence)
    
    session.close()
    return results


def run_performance_test():
    """Run performance tests with various queries."""
    test_queries = [
        "推荐几个湘菜",
        "兰姨小炒的电话是多少",
        "有什么咖啡店",
        "我想吃火锅",
        "推荐一个便宜的外卖",
    ]
    
    print("=" * 60)
    print("Smart Order System Performance Test")
    print("=" * 60)
    
    all_results = []
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 40)
        
        # Measure component latency
        component_results = measure_component_latency(query)
        
        print(f"  Memory Loading: {component_results['memory_loading']:.3f}s ({component_results['memory_count']} memories)")
        print(f"  Planning: {component_results['planning']:.3f}s (intent: {component_results['plan_intent']})")
        
        if component_results.get('requires_rag'):
            print(f"  RAG Retrieval: {component_results.get('rag_retrieval', 0):.3f}s ({component_results.get('evidence_count', 0)} evidence)")
        
        # Measure total latency
        total_results = measure_latency(query)
        print(f"  Total Time: {total_results['total']:.3f}s")
        print(f"  Response: {total_results['response'][:100]}...")
        
        all_results.append({
            "query": query,
            "components": component_results,
            "total": total_results['total'],
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    avg_memory = sum(r['components']['memory_loading'] for r in all_results) / len(all_results)
    avg_planning = sum(r['components']['planning'] for r in all_results) / len(all_results)
    avg_total = sum(r['total'] for r in all_results) / len(all_results)
    
    print(f"Average Memory Loading: {avg_memory:.3f}s")
    print(f"Average Planning: {avg_planning:.3f}s")
    print(f"Average Total: {avg_total:.3f}s")
    
    # Identify bottleneck
    if avg_planning > avg_memory:
        print("\nBottleneck: LLM Planning (planning takes more time than memory loading)")
    else:
        print("\nBottleneck: Memory Loading (memory loading takes more time than planning)")
    
    return all_results


if __name__ == "__main__":
    run_performance_test()
