from langchain_google_genai import ChatGoogleGenerativeAI
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key="AIzaSyAuq9XVpwqfX8e1muQP7PTe1cJttQ1CR_M")
    llm.invoke("hello")
    print("Success")
except Exception as e:
    print(f"Error: {e}")
