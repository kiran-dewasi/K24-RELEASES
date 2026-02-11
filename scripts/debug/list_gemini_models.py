import os
import google.generativeai as genai

def main():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY not set in environment.")
        return

    print(f"Using API Key: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        genai.configure(api_key=api_key)

        print("\nFetching available Gemini models...")
        print("-" * 60)
        
        for m in genai.list_models():
            # Handle potential variations in attribute names across SDK versions
            name = getattr(m, "name", getattr(m, "model", "UNKNOWN_NAME"))
            displayName = getattr(m, "displayName", "")
            methods = getattr(m, "supported_generation_methods", getattr(m, "generation_methods", []))
            
            print(f"Name: {name}")
            if displayName:
                print(f"Display Name: {displayName}")
            print(f"Methods: {methods}")
            print("-" * 60)
            
    except Exception as e:
        print(f"Error fetching models: {e}")

if __name__ == "__main__":
    main()
