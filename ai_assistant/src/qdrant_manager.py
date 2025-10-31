import logging
from typing import List, Dict, Any, Optional
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
import uuid
import asyncio
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class QdrantManager:
    """Менеджер векторной БД Qdrant"""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 6333,
                 collection_name: str = "financial_documents",
                 vector_size: int = 312):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.embedder = None
        
    async def initialize(self, embedder: SentenceTransformer):
        self.embedder = embedder
        
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Создана коллекция {self.collection_name}")
            else:
                logger.info(f"Коллекция {self.collection_name} уже существует")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации Qdrant: {e}")
            raise

    async def add_documents(self, documents: List[str], metadata: List[Dict] = None) -> bool:
        if not documents:
            return False
            
        try:
            embeddings = await self._generate_embeddings_batch(documents)
            
            points = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                point_id = str(uuid.uuid4())
                
                point_metadata = {
                    "text": doc,
                    "document_id": i,
                    "length": len(doc)
                }
                
                if metadata and i < len(metadata):
                    point_metadata.update(metadata[i])
                
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload=point_metadata
                    )
                )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Добавлено {len(points)} документов в Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления документов в Qdrant: {e}")
            return False

    async def search_similar(self, 
                           query: str, 
                           top_k: int = 5,
                           score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        if not self.embedder:
            raise RuntimeError("Embedder не инициализирован")
            
        try:
            query_embedding = await self._generate_embedding(query)
            
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=top_k,
                score_threshold=score_threshold
            )
            
            results = []
            for hit in search_result:
                results.append({
                    "text": hit.payload.get("text", ""),
                    "score": hit.score,
                    "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
                })
            
            logger.info(f"Найдено {len(results)} похожих документов для запроса: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка поиска в Qdrant: {e}")
            return []

    async def _generate_embedding(self, text: str) -> np.ndarray:
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, self.embedder.encode, [text]
        )
        return embedding[0]

    async def _generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, self.embedder.encode, texts
        )
        return embeddings

    async def get_collection_info(self) -> Dict[str, Any]:
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "vectors_count": info.vectors_count,
                "status": info.status,
                "segments_count": len(info.segments)
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о коллекции: {e}")
            return {}

    async def clear_collection(self) -> bool:
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Коллекция {self.collection_name} очищена")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки коллекции: {e}")
            return False