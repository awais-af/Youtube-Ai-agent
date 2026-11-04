"""
Configuration settings for the YouTube Tutorial AI Agent.
"""

import os
from typing import Literal
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

DEFAULT_PROVIDER: Literal["groq", "openai"] = os.getenv("DEFAULT_LLM_PROVIDER", "groq")

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
AVAILABLE_GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b"
]

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AVAILABLE_OPENAI_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "o3-mini"
]

# Transcript Processing Constants
MAX_CHUNK_TOKENS = 1200
DEFAULT_CHUNK_DURATION_SEC = 120  # ~2 minutes blocks for timestamp references
