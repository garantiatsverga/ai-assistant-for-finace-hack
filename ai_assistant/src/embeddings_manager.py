from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import asyncio
from .logging_setup import suppress_stdout
import logging
import os
from .qdrant_manager import QdrantManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingsManager:
    """Управление эмбеддингами с Qdrant"""
    
    def __init__(self, model_name: str = "cointegrated/rubert-tiny2", use_qdrant: bool = True):
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        os.environ['HF_DISABLE_TQDM'] = '1'

        try:
            with suppress_stdout():
                self.model = SentenceTransformer(model_name)
            logger.info(f"Модель эмбеддингов {model_name} успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка инициализации модели эмбеддингов: {e}")
            raise RuntimeError(f"Не удалось инициализировать модель эмбеддингов: {e}")

        self.use_qdrant = use_qdrant
        self.qdrant = None
        self.documents_loaded = False
        
        if use_qdrant:
            self.qdrant = QdrantManager()
            asyncio.create_task(self._initialize_qdrant())

    async def _initialize_qdrant(self):
        try:
            await self.qdrant.initialize(self.model)
            logger.info("Qdrant успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Qdrant: {e}")
            self.use_qdrant = False

    async def load_documents_to_qdrant(self, documents: List[str]) -> bool:
        if not self.use_qdrant or not self.qdrant:
            logger.warning("Qdrant недоступен, используем fallback")
            return False
            
        try:
            success = await self.qdrant.add_documents(documents)
            if success:
                self.documents_loaded = True
                logger.info(f"Документы загружены в Qdrant: {len(documents)}")
            return success
        except Exception as e:
            logger.error(f"Ошибка загрузки документов в Qdrant: {e}")
            return False

    async def get_embedding(self, text: str) -> np.ndarray:
        if not self.model:
            raise RuntimeError("Модель эмбеддингов не инициализирована")
        try:
            loop = asyncio.get_running_loop()
            with suppress_stdout():
                embedding = await loop.run_in_executor(None, self.model.encode, [text])
            return embedding[0]
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга: {e}")
            raise RuntimeError(f"Не удалось получить эмбеддинг: {e}")

    async def find_similar(self, 
                         question: str, 
                         top_k: int = 5,
                         score_threshold: float = 0.3) -> List[str]:
        if self.use_qdrant and self.qdrant and self.documents_loaded:
            try:
                results = await self.qdrant.search_similar(
                    question, top_k=top_k, score_threshold=score_threshold
                )
                
                if results:
                    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
                    return [result['text'] for result in sorted_results]
                    
            except Exception as e:
                logger.error(f"Ошибка поиска в Qdrant: {e}")
        
        logger.warning("Используем fallback поиск")
        if hasattr(self, 'documents') and self.documents:
            return self.documents[:top_k]
        else:
            return ["Информация по вашему запросу не найдена в базе знаний."]

    def precompute_embeddings(self, documents: List[str], cache=None) -> np.ndarray:
        self.documents = documents
        
        if self.use_qdrant and documents:
            asyncio.create_task(self.load_documents_to_qdrant(documents))
        
        return np.array([])

    async def get_qdrant_status(self) -> Dict[str, Any]:
        if not self.use_qdrant or not self.qdrant:
            return {"status": "disabled"}
            
        try:
            info = await self.qdrant.get_collection_info()
            return {
                "status": "active",
                "collection_info": info,
                "documents_loaded": self.documents_loaded
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}