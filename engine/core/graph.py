from langgraph.graph import StateGraph, START, END
from core.state import AgentState
from agents.rag_nodes import nodes
from agents.utility_nodes import utility_agent

def build_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("mask", nodes.mask_query)
    workflow.add_node("retrieve", nodes.retrieve)
    workflow.add_node("grade", nodes.grade_documents)
    workflow.add_node("generate", nodes.generate)
    workflow.add_node("judge", nodes.judge_answer)
    workflow.add_node("polish", nodes.polish_answer)
    workflow.add_node("guardrail", nodes.guardrail)
    workflow.add_node("unmask", nodes.unmask_response)
    workflow.add_node("learn", nodes.extract_facts)
    workflow.add_node("utility", utility_agent.run_utility_check)

    # Build Edges
    workflow.add_edge(START, "mask")
    
    # Branching
    workflow.add_edge("mask", "utility")
    workflow.add_edge("mask", "retrieve")
    
    workflow.add_edge("retrieve", "grade")
    
    # Merging
    workflow.add_edge("utility", "generate")
    workflow.add_edge("grade", "generate")

    workflow.add_edge("generate", "judge")
    workflow.add_edge("judge", "polish")
    workflow.add_edge("polish", "guardrail")
    workflow.add_edge("guardrail", "unmask")
    
    # Learn in parallel or after unmasking
    workflow.add_edge("unmask", "learn")
    workflow.add_edge("learn", END)

    return workflow.compile()

nexus_graph = build_graph()
