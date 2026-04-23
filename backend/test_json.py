import asyncio
from agents import get_llm, GeneratedArticle
from pydantic import BaseModel, Field

api_key = "AIzaSyAuq9XVpwqfX8e1muQP7PTe1cJttQ1CR_M"
try:
    llm = get_llm(api_key).with_structured_output(GeneratedArticle)
    print("invoking...")
    res = llm.invoke("Generate an article with outline_id 1, title 'Test', and a 5 word content.")
    print("Success")
    print(res)
except Exception as e:
    print(f"Error: {e}")
