
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

print("Testing gemini-pro...")
try:
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content("test")
    print("SUCCESS: gemini-pro worked")
except Exception as e:
    print(f"FAILED: gemini-pro - {e}")

print("Testing gemini-1.5-flash...")
try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("test")
    print("SUCCESS: gemini-1.5-flash worked")
except Exception as e:
    print(f"FAILED: gemini-1.5-flash - {e}")
