import os
from pydantic import BaseModel, Field
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(api_key: str):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=api_key,
        temperature=0.7,
        max_tokens=2048,
        timeout=None,
        max_retries=1,
    )

def get_llm_fast(api_key: str):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.2,
        max_tokens=8192,
    )

# --- Pydantic Models for Structured Output ---

class KeywordScore(BaseModel):
    score: float = Field(description="Score from 0.0 to 1.0 indicating keyword viability.")
    reasoning: str = Field(description="Explanation for the score.")
    is_viable: bool = Field(description="True if score >= 0.7, False otherwise.")

class ArticleOutline(BaseModel):
    id: int = Field(description="Unique ID for this outline (1, 2, or 3).")
    primary_angle: str = Field(description="The main angle or hook for this variant.")
    sections: List[str] = Field(description="List of section headings.")

class PlannerOutput(BaseModel):
    outlines: List[ArticleOutline] = Field(description="Exactly 3 distinct article outlines.")

class ValidationResult(BaseModel):
    is_approved: bool = Field(description="Whether the outline is approved.")
    feedback: str = Field(description="Feedback on the outline.")

class GeneratedArticle(BaseModel):
    outline_id: int = Field(description="The ID of the outline this article is based on")
    title: str = Field(description="Catchy, SEO-optimized title")
    content: str = Field(description="Full markdown article content (300+ words)")

class ReviewResult(BaseModel):
    outline_id: int
    is_compliant: bool = Field(description="Does it adhere to the policies?")
    quality_score: float = Field(description="Score from 0.0 to 1.0.")
    feedback: str
    passed: bool

# --- Agent Functions ---

def score_keyword(keyword: str, api_key: str) -> KeywordScore:
    scorer_llm = get_llm_fast(api_key).with_structured_output(KeywordScore)
    prompt = f"""
    You are the Keyword Scorer (Agent 1). 
    Evaluate the viability of this keyword for our marketing program: "{keyword}"
    Consider search intent, commercial value, and broadness.
    Provide a score between 0.0 and 1.0. Consider it viable if >= 0.7.
    """
    return scorer_llm.invoke(prompt)

def plan_content(keyword: str, api_key: str, custom_instructions: str = "") -> PlannerOutput:
    planner_llm = get_llm(api_key).with_structured_output(PlannerOutput)
    prompt = f"""
    You are the Content Planner (Agent 3).
    Create 3 distinct, high-quality article outlines for the keyword: "{keyword}"
    Make sure each outline has a unique 'primary_angle' (e.g., educational, commercial, listicle).
    
    CORE CONSTRAINTS:
    - Adult (18+) audience targeting
    - 4-6 H2 sections with 8-12 paragraphs total
    - RSOC monetization optimization (informational intent, keyword placement, scannable structure, commercial-adjacent framing)
    - Fact based articles
    - Explicit "avoid" list (youth framing, guaranteed language, professional-advice framing, clickbait, fake urgency)
    
    ADDITIONAL UI INSTRUCTIONS:
    {custom_instructions}
    """
    return planner_llm.invoke(prompt)

def validate_outline(keyword: str, outline: ArticleOutline, api_key: str) -> ValidationResult:
    validator_llm = get_llm_fast(api_key).with_structured_output(ValidationResult)
    prompt = f"""
    You are the Outline Validator.
    Review this outline for the keyword "{keyword}".
    Angle: {outline.primary_angle}
    Sections: {', '.join(outline.sections)}
    
    Is this a strong, non-spammy, and logically structured outline?
    """
    return validator_llm.invoke(prompt)

def generate_article(keyword: str, outline: ArticleOutline, context: str, api_key: str, custom_instructions: str = "") -> GeneratedArticle:
    # Use raw string output instead of structured output to avoid JSON parsing errors with long markdown
    generator_llm = get_llm_fast(api_key)
    prompt = f"""
    You are the Content Generator (Agent 4).
    Generate a full, premium article based on the following outline and context.
    
    Prompt:
    Keyword: {keyword}
    Angle: {outline.primary_angle}
    Outline ID: {outline.id}
    Sections: {', '.join(outline.sections)}
    
    CORE CONSTRAINTS:
    - Adult (18+) audience targeting
    - 300-500 word length
    - 3-4 H2 sections with 5-8 paragraphs total
    - 8th-9th grade reading level
    - RSOC monetization optimization (informational intent, keyword placement, scannable structure, commercial-adjacent framing)
    - Fact based articles
    - Explicit "avoid" list (youth framing, guaranteed language, professional-advice framing, clickbait, fake urgency)
    
    ADDITIONAL UI INSTRUCTIONS:
    {custom_instructions}
    
    IMPORTANT CONTEXT (Google Ads Policies / RAG Facts):
    {context}
    
    Ensure you adhere strictly to the context and policies provided. Write in professional Markdown.
    
    CRITICAL INSTRUCTION: You must return your response in the exact format below, with no other text before or after:
    TITLE: [Your Catchy Title]
    CONTENT:
    [Your full markdown article content here]
    """
    res = generator_llm.invoke(prompt)
    text = res.content
    
    title = "Untitled Article"
    content = text
    
    if "TITLE:" in text and "CONTENT:" in text:
        parts = text.split("CONTENT:")
        title = parts[0].replace("TITLE:", "").strip()
        content = parts[1].strip()
        
    return GeneratedArticle(outline_id=outline.id, title=title, content=content)

def review_article(article: GeneratedArticle, context: str, api_key: str) -> ReviewResult:
    reviewer_llm = get_llm(api_key).with_structured_output(ReviewResult)
    prompt = f"""
    You are the Quality & Compliance Reviewer (Agent 5).
    Review the following article for quality and compliance with the provided context.
    
    Article Title: {article.title}
    Content:
    {article.content}
    
    CONTEXT (Policies to check against):
    {context}
    
    Check for:
    1. Are there any claims that violate the policies in the context?
    2. Is the writing quality high?
    
    Provide a quality score (0.0-1.0) and boolean compliance flag.
    Pass the article only if compliant AND quality >= 0.8.
    """
    return reviewer_llm.invoke(prompt)
