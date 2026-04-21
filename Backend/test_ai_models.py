import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY", "")
if not api_key:
    print("No GEMINI_API_KEY found.")
    exit(1)

try:
    from google import genai
    client = genai.Client(api_key=api_key)
    
    models_to_test = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-002",
        "gemini-1.5-pro",
        "gemini-2.0-flash-001"
    ]
    
    for m in models_to_test:
        try:
            print(f"Testing {m}...", end=" ")
            # Try both with and without models/ prefix if needed
            res = client.models.generate_content(model=m, contents="ping")
            print(f"SUCCESS: {res.text.strip()}")
            continue
        except Exception as e:
             print(f"FAILED: {str(e)[:100]}")
             
except Exception as e:
    print(f"Check failed: {e}")
