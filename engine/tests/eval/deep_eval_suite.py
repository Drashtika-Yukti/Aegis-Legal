import pytest
import json
import os
import sys
sys.path.append(os.getcwd())

from deepeval.metrics import HallucinationMetric, GEval
from deepeval.test_case import LLMTestCase
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_groq import ChatGroq
from core.orchestrator import run_nexus

# NEW: Wrapper for DeepEval to use Groq
class GroqDeepEval(DeepEvalBaseLLM):
    def __init__(self, model_name="llama-3.3-70b-versatile"):
        self.model = ChatGroq(model=model_name)

    def load_model(self):
        return self.model

    def generate(self, prompt: str) -> str:
        return self.model.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        res = await self.model.ainvoke(prompt)
        return res.content

    def get_model_name(self):
        return "Groq Llama-3.3"

# Initialize Groq Judge
groq_judge = GroqDeepEval()

# Load Golden Set
with open("data/golden_eval_set.json", "r") as f:
    golden_set = json.load(f)

@pytest.mark.parametrize("test_data", golden_set[:3])
def test_nexus_intelligence_threshold(test_data):
    """
    DeepEval test suite using Groq to ensure response quality.
    """
    query = test_data["question"]
    result = run_nexus(query, "deepeval_automation")
    
    test_case = LLMTestCase(
        input=query,
        actual_output=result["answer"],
        retrieval_context=result["documents"]
    )
    
    # 1. Hallucination Metric (Using Groq)
    hallucination_metric = HallucinationMetric(threshold=0.3, model=groq_judge)
    
    # 2. G-Eval (Using Groq)
    legal_correctness_metric = GEval(
        name="Legal Correctness",
        criteria="Evaluate if the answer matches the ground truth legal statute accurately.",
        evaluation_params=["input", "actual_output", "retrieval_context"],
        threshold=0.6,
        model=groq_judge
    )
    
    # 3. Execution
    hallucination_metric.measure(test_case)
    legal_correctness_metric.measure(test_case)
    
    assert not hallucination_metric.is_successful(), f"FAILURE: Hallucination detected for: {query}"
    assert legal_correctness_metric.is_successful(), f"FAILURE: Legal correctness below threshold for: {query}"

if __name__ == "__main__":
    pytest.main([__file__])
