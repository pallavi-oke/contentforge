from langchain_google_genai import ChatGoogleGenerativeAI
import time

api_key = "AIzaSyAuq9XVpwqfX8e1muQP7PTe1cJttQ1CR_M"
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)

print("Invoking...")
start = time.time()
try:
    res = llm.invoke("Write a 300 word article about gut health.")
    print(f"Success in {time.time()-start:.2f}s")
    print(res.content[:100])
except Exception as e:
    print(f"Error: {e}")
