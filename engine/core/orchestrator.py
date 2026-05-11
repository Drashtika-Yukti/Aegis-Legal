import asyncio
from core.router import router
from core.memory import memory
from core.graph import nexus_graph
from agents.rag_nodes import nodes
from core.logger import get_logger

logger = get_logger("AegisEngine")

async def run_aegis_stream(query: str, session_id: str = "default", user_id: str = "", utility_context: str = ""):
    """
    Aegis Master Entry Point (Streaming).
    Yields JSON events for the frontend.
    """
    logger.info(f"Session {session_id} | User {user_id} | Starting stream.")

    try:
        # 0. Fetch History
        history_dicts = await memory.get_history(session_id, user_id, k=10)
        from langchain_core.messages import HumanMessage, AIMessage
        history_messages = []
        for msg in history_dicts:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            else:
                history_messages.append(AIMessage(content=msg["content"]))

        # 1. Routing Status
        yield {"type": "status", "content": "Analyzing legal intent..."}
        intent_result = await router.route(query)
        
        if intent_result.category == "GREETING":
            yield {"type": "token", "content": "Hello! I am Aegis, your Legal Intelligence Assistant. How can I help you today?"}
            return

        # 2. Graph Streaming
        initial_state = {
            "original_query": query,
            "messages": history_messages,
            "masked_query": "",
            "documents": [],
            "masked_answer": "",
            "final_answer": "",
            "is_relevant": True,
            "hallucination_detected": False,
            "evaluation": {},
            "safety_check": True,
            "facts": [],
            "user_id": user_id,
            "utility_context": utility_context
        }

        async for event in nexus_graph.astream_events(
            initial_state,
            version="v2"
        ):
            kind = event["event"]
            node = event.get("metadata", {}).get("langgraph_node", "")

            # Stream Status Updates
            if kind == "on_chain_start" and node:
                status_map = {
                    "mask": "Shielding sensitive identifiers...",
                    "retrieve": "Searching law library...",
                    "grade": "Verifying document relevance...",
                    "generate": "Drafting legal insight...",
                    "judge": "Auditing for faithfulness...",
                    "polish": "Refining professional tone...",
                    "guardrail": "Performing final safety check..."
                }
                if node in status_map:
                    yield {"type": "status", "content": status_map[node]}

            # Stream Chat Tokens (from the generate node)
            if kind == "on_chat_model_stream" and node == "generate":
                content = event["data"]["chunk"].content
                if content:
                    yield {"type": "token", "content": content}

            # Final Data (from the end of the chain)
            if kind == "on_chain_end" and node == "unmask":
                result = event["data"]["output"]
                final_answer = result.get("final_answer") or result.get("masked_answer") or ""
                
                # Check for Guardrail Failure
                if not result.get("safety_check", True):
                    final_answer = "ACCESS DENIED: This response violated Aegis safety protocols."

                yield {
                    "type": "final",
                    "documents": result.get("documents", []),
                    "evaluation": result.get("evaluation", {}),
                    "safety_check": result.get("safety_check", True)
                }
                await memory.add_message(session_id, user_id, "user", query)
                if final_answer:
                    await memory.add_message(session_id, user_id, "ai", final_answer)
                
                # Background Learning (Dual-Memory Fact Extraction)
                asyncio.create_task(nodes.extract_facts(result))

    except Exception as e:
        logger.error(f"Stream Error: {str(e)}", exc_info=True)
        yield {
            "type": "error",
            "content": "Aegis has encountered a legal paradox. Our scribes are resolving the conflict."
        }
