
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key present: {bool(api_key)}")

try:
    print("Initializing ChatGoogleGenerativeAI...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=api_key,
        temperature=0.1,
        max_tokens=500
    )
    print("ChatGoogleGenerativeAI initialized.")
    
    print("Invoking LLM...")
    response = llm.invoke("Hello, are you working?")
    print(f"Response: {response.content}")

except Exception as e:
    print(f"Error with ChatGoogleGenerativeAI: {e}")
    import traceback
    traceback.print_exc()

print("-" * 20)

try:
    print("Initializing genai.GenerativeModel directly...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    print("genai.GenerativeModel initialized.")
    
    print("Generating content...")
    response = model.generate_content("Hello")
    print(f"Response: {response.text}")

except Exception as e:
    print(f"Error with genai.GenerativeModel: {e}")
    import traceback
    traceback.print_exc()
