import os
from dotenv import load_dotenv

load_dotenv()

# -- LangSmith tracing (optional; only turns on if a key is present) --
if os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGSMITH_PROJECT", "Control Tower - Phase 1")

# -- Provider: OpenRouter (OpenAI-compatible endpoint) --
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# -- Model settings --
CLASSIFIER_MODEL = "openai/gpt-5.4-nano"   # cheap + fast: simple 7-way categorization
RESOLVER_MODEL   = "openai/gpt-5.4-mini"   # stronger: policy + fraud reasoning

# -- Guardrail thresholds (used in the human-approval gate, Step 6) --
HIGH_VALUE_THRESHOLD_USD = 150.0