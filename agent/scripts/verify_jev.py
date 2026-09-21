import os
from typesafe_sdk import TypeSafeClient, Noul

api_key = "apikey_21904c41935973b7403595d40111cba6fc15_52c18b6b0f806631aae83e7232801a0954b65fa935e9a0a49e28afe6d33e313e"

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
