import os
import cohere
from dotenv import load_dotenv

# Load your .env file
load_dotenv()
api_key = os.getenv("COHERE_API_KEY")

# 1. Check if the key is even being read
if not api_key:
    print("❌ ERROR: COHERE_API_KEY is not found in your .env file!")
else:
    print(f"📡 Attempting to connect with key: {api_key[:5]}... (shortened for safety)")
    
    try:
        # 2. Try to initialize the client
        co = cohere.Client(api_key)
        
        # 3. Try a simple chat request
        response = co.chat(
            message="Say 'Hello World' if you can hear me.",
            model="command-r7b-12-2024" # Use 'command-r' instead of the nightly version for this test
        )
        print(f"✅ SUCCESS! Cohere responded: {response.text}")
        
    except Exception as e:
        print(f"❌ FAILED! Cohere error: {str(e)}")