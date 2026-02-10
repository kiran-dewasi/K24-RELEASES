import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"🔑 checking key ending in ...{api_key[-4:] if api_key else 'None'}")

if not api_key:
    print("❌ GOOGLE_API_KEY is missing!")
    exit(1)

genai.configure(api_key=api_key)

print("\n📋 Listing Available Models for this Key:")
try:
    count = 0
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"   - {m.name}")
            count += 1
    
    if count == 0:
        print("⚠️ No models found supports generateContent")
    else:
        print(f"\n✅ Found {count} available models.")

except Exception as e:
    print(f"❌ Error listing models: {e}") 
