
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

try:
    genai.configure(api_key=api_key)
    print("Getting model...")
    model = genai.get_model('models/gemini-1.5-flash')
    print(f"Got model: {model.name}")
except Exception as e:
    print(f"Error getting model: {e}")

print("-" * 20)

try:
    print("Generating content...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hi")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error generating content: {e}")
