from pydantic import BaseModel, Field
from typing import List
from agents import get_llm

class KeywordItem(BaseModel):
    keyword: str
    category: str = Field(description="One of: Health, Finance, Shopping, Legal, Insurance")
    intent: str = Field(description="E.g., Informational, Commercial")

class KeywordBatch(BaseModel):
    keywords: List[KeywordItem]

def generate_keyword_batch(api_key: str) -> KeywordBatch:
    generator_llm = get_llm(api_key).with_structured_output(KeywordBatch)
    prompt = """
    You are an expert SEO Content Strategist.
    Generate a diverse batch of exactly 5 distinct keywords for content marketing articles.
    Ensure they span the following categories: Health, Finance, Shopping, Legal, and Insurance.
    Focus on keywords that have mid-to-low CPCs but strong search intent.
    Do not return fewer or more than 5 keywords.
    """
    return generator_llm.invoke(prompt)
