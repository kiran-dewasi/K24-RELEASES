
import os
import sys
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

try:
    print("Importing IntentClassifier...")
    from backend.agent_intent import IntentClassifier
    print("Initializing IntentClassifier...")
    # Try with the model name from the code
    classifier = IntentClassifier(model_name="gemini-2.0-flash-exp")
    print("IntentClassifier initialized successfully.")
except Exception as e:
    print(f"Error initializing IntentClassifier: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\nImporting GeminiXMLAgent...")
    from backend.agent_gemini import GeminiXMLAgent
    print("Initializing GeminiXMLAgent...")
    agent = GeminiXMLAgent(model_name="gemini-1.5-flash")
    print("GeminiXMLAgent initialized successfully.")
except Exception as e:
    print(f"Error initializing GeminiXMLAgent: {e}")
    import traceback
    traceback.print_exc()
