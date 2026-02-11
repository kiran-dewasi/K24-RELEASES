
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

models_to_try = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
    "gemini-pro",
    "gemini-1.0-pro",
    "gemini-2.0-flash-exp"
]

print("Testing model availability...")

for model_name in models_to_try:
    print(f"Testing {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello")
        print(f"SUCCESS: {model_name} worked!")
        break
    except Exception as e:
        print(f"FAILED: {model_name} - {e}")

print("Done.")
