import os

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from pydantic import SecretStr


"""
api_key = os.getenv("ANTHROPIC_API_KEY")
LLM_MODEL = "claude-sonnet-4-5-20250929"
PROVIDER = "anthropic"
TEMPERATURE = 0.1
llm = ChatAnthropic(
            model_name=LLM_MODEL,
            temperature=TEMPERATURE,
            api_key=SecretStr(api_key),
            stop=None,
            timeout=None,
        )

"""
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# ollama constants
# CHAT_MODEL = "ollama:llama3.1"
LLM_MODEL = "llama3.1"
PROVIDER = "ollama"
llm = ChatOllama(
    model=LLM_MODEL,
    temperature=0.1,
    base_url=OLLAMA_URL  # required for docker
)
# llm = ChatOllama(model=LLM_MODEL, temperature=0.0)
TEMPERATURE = 0.1

"""
# openai constants
LLM_MODEL = "gpt-4o-mini"
PROVIDER = "openai"
#CHAT_MODEL = "openai:gpt-4o"
CHAT_MODEL = "openai:gpt-4o-mini"
llm = ChatOpenAI(
     model=LLM_MODEL,
     temperature=0.0,
)
TEMPERATURE = 0.1
"""