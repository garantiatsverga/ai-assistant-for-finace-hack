import os
import pickle
import hashlib
from typing import Any, Dict
# добавляем импорт
from .logging_setup import suppress_stdout

class EmbeddingCache:
    """Кэш для эмбеддингов с персистентностью"""
    def __init__(self, cache_file: str = 'embeddings_cache.pkl'):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_cache(self) -> None:
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception:
            pass

    def _key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get_embedding(self, text: str, embedder: Any) -> Any:
        key = self._key(text)
        if key in self.cache:
            return self.cache[key]
        # Подавляем stdout/stderr во время вычисления эмбеддинга
        with suppress_stdout():
            embedding = embedder.encode([text])
        emb = embedding[0] if isinstance(embedding, (list, tuple)) else embedding
        self.cache[key] = emb
        self._save_cache()
        return emb

class MemoryOptimizedCache:
    """Кэш с ограничением по памяти"""
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
    
    def get(self, key: str) -> Any:
        return self.cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        if len(self.cache) >= self.max_size:
            # Удаляем первый элемент при переполнении
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = value