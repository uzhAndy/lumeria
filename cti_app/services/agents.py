# makes sure that agents are only built once in views
from cti_app.services.agent_builder import build_rag_agent, build_simple_agent_with_memory, \
    build_simple_agent_no_system_prompt

_RAG_AGENT = None
_PLAIN_AGENT = None
_MEMORYLESS_PLAIN_AGENT = None

def get_rag_agent():
    global _RAG_AGENT
    if _RAG_AGENT is None:
        _RAG_AGENT = build_rag_agent()
    return _RAG_AGENT

def get_plain_agent_with_memory():
    global _PLAIN_AGENT
    if _PLAIN_AGENT is None:
        _PLAIN_AGENT = build_simple_agent_with_memory()
    return _PLAIN_AGENT

def get_plain_agent_no_memory():
    global _MEMORYLESS_PLAIN_AGENT
    if _MEMORYLESS_PLAIN_AGENT is None:
        _MEMORYLESS_PLAIN_AGENT = build_simple_agent_no_system_prompt()
    return _MEMORYLESS_PLAIN_AGENT