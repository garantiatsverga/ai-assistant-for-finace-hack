from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import asyncio
from .cache_manager import EmbeddingCache

class EmbeddingsManager:
    """Управление эмбеддингами"""
    
    def __init__(self, model_name: str = "cointegrated/rubert-tiny2"):
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            print(f"Ошибка загрузки модели эмбеддингов: {e}")
            self.model = None

    def precompute_embeddings(self, 
                            documents: List[str],
                            cache: EmbeddingCache) -> np.ndarray:
        """Предварительное вычисление эмбеддингов документов"""
        if not self.model or not documents:
            return np.array([])
            
        embeddings = []
        for doc in documents:
            emb = cache.get_embedding(doc, self.model)
            embeddings.append(emb)
        return np.array(embeddings)

    async def get_embedding(self, text: str) -> np.ndarray:
        """Асинхронное получение эмбеддинга"""
        if not self.model:
            raise ValueError("Модель эмбеддингов не инициализирована")
            
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            None,
            self.model.encode,
            [text]
        )
        return embedding[0]

    async def find_similar(self,
                          question: str,
                          q_embedding: np.ndarray,
                          doc_embeddings: np.ndarray,
                          documents: List[str],
                          top_k: int = 3) -> List[str]:
        """Поиск похожих документов"""
        if doc_embeddings.size == 0:
            return []
            
        # Вычисляем косинусное сходство
        similarities = np.dot(doc_embeddings, q_embedding)
        top_idx = np.argsort(similarities)[-top_k:][::-1]
        
        return [documents[i] for i in top_idx]