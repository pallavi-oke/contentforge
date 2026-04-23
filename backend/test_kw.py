from keyword_generator import generate_keyword_batch
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
print("Generating keywords...")
try:
    batch = generate_keyword_batch(api_key)
    print("Success:")
    for k in batch.keywords:
        print(f"- {k.keyword} ({k.category})")
except Exception as e:
    print(f"Error: {e}")
