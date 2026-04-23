import asyncio
from agents import plan_content, generate_article
from graph import query_rag

api_key = "AIzaSyAuq9XVpwqfX8e1muQP7PTe1cJttQ1CR_M"
keyword = "how to improve gut health naturally"
print("planning...")
plan = plan_content(keyword, api_key, "")
outline = plan.outlines[0]
print(f"Outline ID: {outline.id}")
print("rag query...")
context = query_rag(f"{keyword} {outline.primary_angle}")
print("generating article...")
art = generate_article(keyword, outline, context, api_key, "")
print("Article generated:")
print(art.title)
