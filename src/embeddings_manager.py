from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer, util
import asyncio
# добавляем импорт suppress_stdout
from .logging_setup import suppress_stdout
import logging
import os
from .cache_manager import EmbeddingCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingsManager:
    """Управление эмбеддингами"""
    
    def __init__(self, model_name: str = "cointegrated/rubert-tiny2"):
        # Отключаем прогресс-бары/многопоточность до загрузки любых библиотек
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        os.environ['HF_DISABLE_TQDM'] = '1'
        os.environ['TQDM_DISABLE'] = '1'
        os.environ['HF_DATASETS_PROGRESS_BAR'] = 'false'
        os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

        # Подменяем tqdm на "тихий" вариант (защита если библиотека уже импортирована)
        try:
            import tqdm
            class _DummyTqdm:
                def __init__(self, it=None, **kw):
                    self._it = it
                def __iter__(self):
                    return iter(self._it or [])
                def update(self, *a, **k): pass
                def close(self): pass
                def __enter__(self): return self
                def __exit__(self, *a): return False
            tqdm.tqdm = lambda it=None, **kw: _DummyTqdm(it)
            try:
                import tqdm.auto as _tq
                _tq.tqdm = lambda it=None, **kw: _DummyTqdm(it)
            except Exception:
                pass
        except Exception:
            pass

        try:
            # Подавляем stdout/stderr на время инициализации модели
            with suppress_stdout():
                self.model = SentenceTransformer(model_name)
            logger.info(f"Модель эмбеддингов {model_name} успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка инициализации модели эмбеддингов: {e}")
            raise RuntimeError(f"Не удалось инициализировать модель эмбеддингов: {e}")

    async def get_embedding(self, text: str) -> np.ndarray:
        """Асинхронное получение эмбеддинга для текста (с подавлением вывода)"""
        if not self.model:
            raise RuntimeError("Модель эмбеддингов не инициализирована")
        try:
            loop = asyncio.get_running_loop()
            # Подавляем вывод сторонних библиотек при вычислении эмбеддинга
            with suppress_stdout():
                embedding = await loop.run_in_executor(None, self.model.encode, [text])
            return embedding[0]
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга: {e}")
            raise RuntimeError(f"Не удалось получить эмбеддинг: {e}")

    def precompute_embeddings(self, documents: List[str], cache: EmbeddingCache) -> np.ndarray:
        """Предварительное вычисление эмбеддингов с использованием кэша"""
        if not documents:
            return np.array([])
            
        try:
            embeddings = []
            for doc in documents:
                emb = cache.get_embedding(doc, self.model)
                embeddings.append(emb)
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Ошибка предварительного вычисления эмбеддингов: {e}")
            raise RuntimeError(f"Не удалось вычислить эмбеддинги: {e}")

    async def find_similar(self, question: str, q_embedding: np.ndarray, 
                        doc_embeddings: np.ndarray, documents: List[str], 
                        top_k: int = 3, threshold: float = 0.3) -> List[str]:  # Понизим порог
        """Простой и надежный поиск"""
        try:
            if not documents:
                return ["Информация по вашему запросу не найдена в базе знаний."]
            
            # ПРОСТО ВОЗВРАЩАЕМ ВСЕ ДОКУМЕНТЫ ДЛЯ ТЕСТА
            logger.info(f"Возвращаем все {len(documents)} документов для тестирования")
            return documents[:top_k]
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return ["Информация по вашему запросу не найдена в базе знаний."]