import os
from dotenv import load_dotenv

load_dotenv()

# Test the second API key from the .env file
api_key = os.getenv("GEMINI_API_KEYS", "")
if not api_key:
    print("No GEMINI_API_KEYS (plural) found.")
    exit(1)

print(f"Testing with KEY starting with: {api_key[:8]}...")

try:
    from google import genai
    client = genai.Client(api_key=api_key)
    
    models_to_test = [
        "gemini-1.5-flash",
        "gemini-2.0-flash"
    ]
    
    for m in models_to_test:
        try:
            print(f"Testing {m}...", end=" ")
            res = client.models.generate_content(model=m, contents="ping")
            print(f"SUCCESS: {res.text.strip()}")
        except Exception as e:
             print(f"FAILED: {str(e)[:50]}")
             
except Exception as e:
    print(f"Check failed: {e}")
