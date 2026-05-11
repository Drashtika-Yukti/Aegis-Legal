from typing import List
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from core.state import AgentState
from utils.tools import utility_tools
from core.logger import get_logger
from core.config import settings

logger = get_logger("UtilityAgent")

class UtilityNodes:
    """
    The Assistant Agent that provides auxiliary powers to the Legal Engine.
    Equipped with Search, Math, and Real-time data tools.
    """
    def __init__(self):
        self.llm_with_tools = None
        try:
            if settings.GROQ_API_KEY:
                self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
                self.llm_with_tools = self.llm.bind_tools(utility_tools)
        except Exception:
            self.llm_with_tools = None

    async def run_utility_check(self, state: AgentState):
        """
        Determines if the query requires external tools (time, search, math).
        """
        query = state["original_query"]
        logger.info(f"Utility Check: {query}")
        if self.llm_with_tools is None:
            return {"utility_context": "Utility model unavailable."}
        
        system_prompt = (
            "You are the Aegis Utility Gatekeeper. Your job is to help the legal engine "
            "by using specialized tools for time, weather, or calculations.\n\n"
            "INTERNET SEARCH POLICY:\n"
            "1. ONLY use 'internet_search' to verify current dates, live legal updates, or specific missing facts.\n"
            "2. DO NOT use internet search if the user is asking for a whole book or statute you don't have.\n"
            "3. If a large document is missing, simply report that it is not in the vault."
        )
        
        existing_context = state.get("utility_context", "")
        
        try:
            # Include existing context in the utility agent's vision
            user_content = f"CONTEXT:\n{existing_context}\n\nQUERY: {query}" if existing_context else query
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
            response = await self.llm_with_tools.ainvoke(messages)
            
            # If the LLM wants to call a tool, we execute it
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                logger.info(f"Executing Tool: {tool_name}")
                
                target_tool = next((t for t in utility_tools if t.name == tool_name), None)
                if target_tool:
                    tool_result = await target_tool.ainvoke(tool_args)
                    new_context = f"Tool Result ({tool_name}): {tool_result}"
                    combined = f"{existing_context}\n\n{new_context}" if existing_context else new_context
                    return {
                        "utility_context": combined
                    }
            
            return {"utility_context": existing_context or "No utility tools required."}
            
        except Exception as e:
            logger.error(f"Utility Error: {e}")
            return {"utility_context": existing_context or "Utility check failed."}

utility_agent = UtilityNodes()
