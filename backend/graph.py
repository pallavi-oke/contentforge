from typing import List, Dict, Any, TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, END
from agents import (
    score_keyword, plan_content, validate_outline, 
    generate_article, review_article,
    ArticleOutline, GeneratedArticle, ReviewResult
)
from rag import query_rag

class AgentState(TypedDict):
    keyword: str
    api_key: str
    custom_instructions: str
    status: str
    is_viable: bool
    score_reasoning: str
    outlines: List[ArticleOutline]
    approved_outlines: List[ArticleOutline]
    generated_articles: List[GeneratedArticle]
    reviews: List[ReviewResult]
    final_articles: List[Dict[str, Any]]

def node_scorer(state: AgentState):
    print(f"--> Scoring Keyword: {state['keyword']}")
    res = score_keyword(state["keyword"], state["api_key"])
    if not res:
        return {"is_viable": False, "score_reasoning": "Agent failed to return structured output.", "status": "Failed"}
    return {
        "is_viable": res.is_viable, 
        "score_reasoning": res.reasoning,
        "status": "Scoring Complete"
    }

def route_scorer(state: AgentState):
    if state.get("is_viable"):
        return "planner"
    return END

def node_planner(state: AgentState):
    print("--> Planning Content")
    res = plan_content(state["keyword"], state["api_key"], state["custom_instructions"])
    outlines = res.outlines if res else []
    return {
        "outlines": outlines,
        "status": "Planning Complete"
    }

def node_validator(state: AgentState):
    print("--> Validating Outlines")
    approved = []
    for outline in state["outlines"]:
        val = validate_outline(state["keyword"], outline, state["api_key"])
        if val and val.is_approved:
            approved.append(outline)
    return {
        "approved_outlines": approved,
        "status": "Validation Complete"
    }

def route_validator(state: AgentState):
    if len(state.get("approved_outlines", [])) > 0:
        return "generator"
    return END

def node_generator(state: AgentState):
    print("--> Generating Articles (with RAG)")
    articles = []
    # In a true LangGraph parallel fan-out, we'd use Send API. 
    # For simplicity in this demo, we loop (since Gemini is fast).
    for outline in state["approved_outlines"]:
        # Distinct RAG query per angle
        rag_query = f"{state['keyword']} {outline.primary_angle}"
        context = query_rag(rag_query)
        
        art = generate_article(state["keyword"], outline, context, state["api_key"], state["custom_instructions"])
        if art:
            articles.append(art)
    
    return {
        "generated_articles": articles,
        "status": "Generation Complete"
    }

def node_reviewer(state: AgentState):
    print("--> Reviewing Articles")
    reviews = []
    final_articles = []
    
    for art in state["generated_articles"]:
        # Re-query context or use the same context (for simplicity we query again)
        outline = next((o for o in state["approved_outlines"] if o.id == art.outline_id), None)
        rag_query = f"{state['keyword']} {outline.primary_angle if outline else ''}"
        context = query_rag(rag_query)
        
        rev = review_article(art, context, state["api_key"])
        
        if not rev:
            final_articles.append({
                "outline_id": art.outline_id,
                "title": art.title,
                "content": art.content,
                "is_compliant": False,
                "quality_score": 0.0,
                "feedback": "Review agent failed to return structured output.",
                "passed": False
            })
            continue

        reviews.append(rev)
        
        final_articles.append({
            "outline_id": art.outline_id,
            "title": art.title,
            "content": art.content,
            "is_compliant": rev.is_compliant,
            "quality_score": rev.quality_score,
            "feedback": rev.feedback,
            "passed": rev.is_compliant and rev.quality_score >= 0.7
        })
        
    return {
        "reviews": reviews,
        "final_articles": final_articles,
        "status": "Review Complete"
    }

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("scorer", node_scorer)
    workflow.add_node("planner", node_planner)
    workflow.add_node("validator", node_validator)
    workflow.add_node("generator", node_generator)
    workflow.add_node("reviewer", node_reviewer)
    
    workflow.set_entry_point("scorer")
    
    workflow.add_conditional_edges(
        "scorer",
        route_scorer,
        {
            "planner": "planner",
            END: END
        }
    )
    
    workflow.add_edge("planner", "validator")
    
    workflow.add_conditional_edges(
        "validator",
        route_validator,
        {
            "generator": "generator",
            END: END
        }
    )
    
    workflow.add_edge("generator", "reviewer")
    workflow.add_edge("reviewer", END)
    
    return workflow.compile()

graph = build_graph()
