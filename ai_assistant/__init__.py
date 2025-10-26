"""AI Assistant package initialization"""
from ai_assistant.src.ai_assistant import SmartDeepThinkRAG
from ai_assistant.src.cache_manager import EmbeddingCache, MemoryOptimizedCache
from ai_assistant.src.config_manager import ConfigManager
from ai_assistant.src.security_checker import SecurityChecker, SecurityError
from ai_assistant.src.metrics_collector import MetricsCollector
from ai_assistant.src.dialogue_memory import DialogueMemory
from ai_assistant.src.llm_adapter import LLMAdapter, LLMError
from ai_assistant.src.embeddings_manager import EmbeddingsManager

__version__ = "0.1.0"

__all__ = [
    "SmartDeepThinkRAG",
    "EmbeddingCache",
    "MemoryOptimizedCache",
    "ConfigManager",
    "SecurityChecker",
    "SecurityError",
    "MetricsCollector",
    "DialogueMemory",
    "LLMAdapter",
    "LLMError",
    "EmbeddingsManager",
]