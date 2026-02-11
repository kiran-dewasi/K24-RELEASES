
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key present: {bool(api_key)}")

try:
    genai.configure(api_key=api_key)
    print("Listing models...")
    for m in genai.list_models():
        print(f"Found model: {m.name}")
        # Accessing properties to ensure full object is built
        print(f" - Supported methods: {m.supported_generation_methods}")
    print("List models completed successfully.")

except Exception as e:
    print(f"Error listing models: {e}")
    import traceback
    traceback.print_exc()
