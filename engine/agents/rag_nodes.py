import os
import json
import asyncio
from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_cohere import CohereEmbeddings
from core.state import AgentState
from utils.privacy_vault import vault as privacy_vault
from core.vault import vault as local_vault
from core.memory import memory
from core.logger import get_logger
from core.config import settings

logger = get_logger("LocalRAGNodes")

class Grade(BaseModel):
    binary_score: str = Field(description="Is the document relevant? 'yes' or 'no'")

class Judge(BaseModel):
    faithfulness: float = Field(description="How accurately does the answer represent the facts in the context? (0.0 to 1.0)")
    groundedness: float = Field(description="Is the answer directly supported by the context without external info? (0.0 to 1.0)")
    hallucination_score: float = Field(description="Probability that the answer contains non-contextual info. (0.0 to 1.0)")
    reasoning: str = Field(description="Brief explanation for the scores.")

class Facts(BaseModel):
    facts: List[str] = Field(description="List of extracted atomic facts.")

class RAGNodes:
    """Core Intelligence Nodes optimized for Standalone Local Retrieval."""
    def __init__(self):
        self.llm = None
        self.fast_llm = None
        if settings.GROQ_API_KEY:
            # Note: We use streaming=True to support on_chat_model_stream in orchestrator
            self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, streaming=True)
            self.fast_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, streaming=True)

    # ... (mask_query and retrieve remain same)

    async def mask_query(self, state: AgentState):
        privacy_vault.reset()
        return {"masked_query": privacy_vault.mask(state["original_query"])}

    async def retrieve(self, state: AgentState):
        """History-Aware Retrieval: Contextualizes the query using previous messages and searches the vault."""
        masked_q = state["masked_query"]
        history = state.get("messages", [])
        
        # 1. Contextualize only if there is history
        search_query = masked_q
        if len(history) > 1 and self.fast_llm:
            history_str = "\n".join([f"{m.type}: {m.content}" for m in history[:-1]])
            context_prompt = f"Given chat history and the latest question, create a high-precision standalone search query.\n\nHISTORY:\n{history_str}\n\nQUESTION: {masked_q}\n\nQuery:"
            result = await self.fast_llm.ainvoke(context_prompt)
            search_query = result.content.strip().strip('"')

        # 2. Try Cache
        cache_key = f"retrieval:{search_query}"
        cached_data = await memory.get_cache(cache_key)
        if cached_data:
            return {"documents": json.loads(cached_data), "search_query": search_query}

        # 3. Retrieve & Rerank
        try:
            initial_docs = await local_vault.retrieve(search_query, limit=15)
            reranked_docs = await local_vault.rerank(search_query, initial_docs, top_n=5)
            await memory.set_cache(cache_key, json.dumps(reranked_docs), expire=3600)
            return {"documents": reranked_docs, "search_query": search_query}
        except Exception as e:
            logger.error(f"Retrieval Error: {e}")
            return {"documents": [], "search_query": search_query}

    async def grade_documents(self, state: AgentState):
        if not self.fast_llm: return {"is_relevant": True}
        grader = self.fast_llm.with_structured_output(Grade)
        prompt = f"Query: {state['masked_query']}\nDocs: {state['documents']}\nGrade relevance (yes/no):"
        result = await grader.ainvoke(prompt)
        return {"is_relevant": result.binary_score == "yes"}

    async def generate(self, state: AgentState):
        """Generates a professional legal response with mandatory numerical citations."""
        # 1. Format Context with Metadata
        context_parts = []
        for i, d in enumerate(state["documents"], 1):
            meta = d.get('metadata', {})
            ref = f"[{i}] SOURCE: {d.get('source')} | ARTICLE: {meta.get('article', 'N/A')} | PAGE: {meta.get('page', 'N/A')}"
            context_parts.append(f"{ref}\nCONTENT: {d['content']}")
        
        doc_context = "\n\n".join(context_parts)
        u_context = state.get("utility_context", "")
        if u_context and "unavailable" not in u_context.lower():
            doc_context = f"REAL-TIME RESEARCH:\n{u_context}\n\nLOCAL RECORDS:\n{doc_context}"

        system_prompt = f"""
        You are Aegis, a Senior Legal AI Analyst.
        
        STRICT RULES:
        1. Every factual statement MUST include a numerical citation from the context, e.g. 'Notice is 30 days [1].'
        2. Use ONLY the provided context.
        3. End your response with a 'Citations' section mapping [ID] to Source/Article/Page.
        
        CONTEXT:
        {doc_context}
        """
        
        # Use astream to ensure on_chat_model_stream triggers
        result = await self.llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": state["masked_query"]}
        ])
        return {"masked_answer": result.content}

    async def judge_answer(self, state: AgentState):
        """Performs multi-dimensional evaluation of the generated response."""
        if not self.fast_llm: return {"metrics": {}}
        
        evaluator = self.fast_llm.with_structured_output(Judge)
        eval_prompt = f"""
        Evaluate the following Legal AI Response against the provided context.
        
        CONTEXT:
        {state['documents']}
        
        RESPONSE:
        {state['masked_answer']}
        
        Assign scores (0.0 to 1.0) for:
        - Faithfulness: Accuracy of the representation.
        - Groundedness: Reliance on context vs external info.
        - Hallucination Score: Probability of fabricated facts.
        """
        
        result = await evaluator.ainvoke(eval_prompt)
        return {
            "evaluation": result.dict(),
            "hallucination_detected": result.hallucination_score > 0.3
        }

    async def polish_answer(self, state: AgentState):
        """Refines for tone while preserving the citations."""
        if not self.fast_llm: return {"masked_answer": state["masked_answer"]}
        
        prompt = f"Refine the following legal response for clarity and professionalism. DO NOT remove or change the numerical citations [1], [2], etc.\n\nRESPONSE:\n{state['masked_answer']}"
        result = await self.fast_llm.ainvoke(prompt)
        return {"masked_answer": result.content.strip()}

    async def unmask_response(self, state: AgentState):
        unmasked = privacy_vault.unmask(state["masked_answer"])
        return {
            "final_answer": unmasked, 
            "documents": state.get("documents", []),
            "evaluation": state.get("evaluation", {})
        }

    async def extract_facts(self, state: AgentState):
        if not self.fast_llm: return {"facts": []}
        content = f"Q: {state.get('original_query')}\nA: {state.get('final_answer')}"
        prompt = f"Extract 3 atomic facts. Bulleted list only.\n\n{content}"
        try:
            result = await self.fast_llm.ainvoke(prompt)
            facts = [f.strip("- ").strip() for f in result.content.split("\n") if f.strip("- ")]
            for fact in facts:
                await local_vault.store_fact(state.get("user_id", "local-user"), fact)
            return {"facts": facts}
        except Exception:
            return {"facts": []}

    async def guardrail(self, state: AgentState):
        """Final safety and legal boundary check."""
        if not self.fast_llm: return {"safety_check": True}
        
        prompt = f"As a legal supervisor, evaluate if this response provides unauthorized legal advice or contains harmful content. Respond with 'safe' or 'unsafe'.\n\nRESPONSE: {state['masked_answer']}"
        result = await self.fast_llm.ainvoke(prompt)
        return {"safety_check": "unsafe" not in result.content.lower()}

nodes = RAGNodes()
