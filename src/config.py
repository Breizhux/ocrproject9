"""Config POC : lit .env, expose les secrets + URL RAG."""
import os
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
RAGIFIX_API_TOKEN = os.getenv("RAGIFIX_API_TOKEN", "")
RAG_BASE_URL = os.getenv("RAG_BASE_URL", "http://127.0.0.1:8421").rstrip("/")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral-small-latest")
