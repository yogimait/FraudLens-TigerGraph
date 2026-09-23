import os
from typesafe_sdk import TypeSafeClient, Noul

from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("JEV_API_KEY", "")
if not api_key:
    raise SystemExit("JEV_API_KEY not set")

print("Testing Jev API connection...")

try:
    client = TypeSafeClient(api_key=api_key)
    
    # Try a simple noul (boolean) query using system_one
    result = client.system_one(
        state="The transaction was marked as fraud by the analyst.",
        questions={
            "is_fraud": Noul(instructions="Is the word 'fraud' present in this text?")
        }
    )
    
    print(f"Jev API connection successful!")
    print(f"Result (Noul): {result.nouls['is_fraud'].noul}")
except Exception as e:
    print(f"Failed to connect to Jev API: {e}")
