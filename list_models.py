import os
from dotenv import load_dotenv
import google.generativeai as genai

# 1. Load your API key from .env
load_dotenv()
api_key = os.getenv('GENAI_API_KEY')
if not api_key:
    raise RuntimeError("GENAI_API_KEY not found in .env")
genai.configure(api_key=api_key)

# 2. Call list_models() to see what model names exist
all_models = genai.list_models()

# 3. Print each model’s name only
for m in all_models:
    print(m.name)
