import os 
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
LLM_PROVIDER = os.getenv("LLM_PROVIDER")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the environment variables.")

print("Gemini API Key:", bool(GEMINI_API_KEY))
print("Gemini Model:", GEMINI_MODEL)