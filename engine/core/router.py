from typing import Literal
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from core.config import settings

class Intent(BaseModel):
    category: Literal["GREETING", "LEGAL_QUERY", "DOCUMENT_ACTION", "UNKNOWN"] = Field(description="The primary intent of the user.")
    complexity: Literal["LOW", "HIGH"] = Field(description="Complexity of the query.")
    reasoning: str = Field(description="Brief reasoning for the classification.")

class Router:
    """
    Intelligent router to minimize latency and cost.
    Uses local-first approach for simple classification.
    """
    def __init__(self):
        self.structured_llm = None
        try:
            if settings.GROQ_API_KEY:
                self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
                self.structured_llm = self.llm.with_structured_output(Intent)
        except Exception:
            self.structured_llm = None

    async def route(self, query: str) -> Intent:
        if self.structured_llm is None:
            return Intent(category="LEGAL_QUERY", complexity="LOW", reasoning="Router LLM unavailable; default route.")
        prompt = f"Analyze the following query and classify its intent and complexity: {query}"
        try:
            return await self.structured_llm.ainvoke(prompt)
        except Exception as e:
            return Intent(category="UNKNOWN", complexity="LOW", reasoning=f"Error: {str(e)}")

router = Router()
