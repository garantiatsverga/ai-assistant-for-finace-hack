"""Main AI Assistant module"""
from typing import List, Optional, Dict, Any
import asyncio
import logging
import os
import time

from ..src.cache_manager import EmbeddingCache, MemoryOptimizedCache
from ..src.config_manager import ConfigManager
from ..src.security_checker import SecurityChecker, SecurityError
from ..src.metrics_collector import MetricsCollector
from ..src.dialogue_memory import DialogueMemory
from ..src.llm_adapter import LLMAdapter, LLMError
from ..src.embeddings_manager import EmbeddingsManager

logger = logging.getLogger(__name__)

class SmartDeepThinkRAG:
    """Основной класс ассистента"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = ConfigManager.load_config(config_path)
        self.embedding_manager = EmbeddingsManager()
        self.embedding_cache = EmbeddingCache()
        self.llm = LLMAdapter()
        self.security = SecurityChecker()
        self.metrics = MetricsCollector()
        self.memory = DialogueMemory()
        
        # Загрузка базы знаний и предварительные вычисления
        self.documents = self._load_knowledge_base()
        self.doc_embeddings = self.embedding_manager.precompute_embeddings(
            self.documents, 
            self.embedding_cache
        )
        
        logger.info(f"Система инициализирована. Документов в базе: {len(self.documents)}")

    def _load_knowledge_base(self) -> List[str]:
        """Загрузка базы знаний из файла
        
        Returns:
            List[str]: Список документов из базы знаний
        """
        knowledge_base_paths = [
            "knowledge_base.txt",  # текущая директория
            os.path.join(os.path.dirname(__file__), '..', 'data', 'knowledge_base.txt'),  # в папке data
            os.path.join(os.path.dirname(__file__), 'knowledge_base.txt')  # рядом с модулем
        ]
        
        for kb_path in knowledge_base_paths:
            try:
                with open(kb_path, 'r', encoding='utf-8') as f:
                    documents = [line.strip() for line in f if line.strip()]
                    logger.info(f"Загружена база знаний из {kb_path}: {len(documents)} документов")
                    return documents
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Ошибка загрузки базы знаний {kb_path}: {e}")
                continue
                
        logger.warning("База знаний не найдена")
        return []

    async def ask(self, question: str) -> str:
        """Асинхронный метод обработки вопроса"""
        start_time = time.time()
        
        # Сохраняем оригинальный вопрос для метрик
        original_question = question
        
        # Проверяем режим deep think
        deepthink_mode = question.endswith(" -deepthink")
        if deepthink_mode:
            question = question[:-10].strip()
            
        # Исправляем раскладку
        question = self._fix_keyboard_layout(question)
        
        try:
            # Параллельно получаем эмбеддинги и проверяем безопасность
            embedding_task = self.embedding_manager.get_embedding(question)
            security_task = self.security.check(question)
            
            is_safe, reason = await security_task
            if not is_safe:
                return reason
                
            # Поиск релевантных документов
            similar_docs = await self.embedding_manager.find_similar(
                question,
                await embedding_task,
                self.doc_embeddings,
                self.documents
            )
            
            # Генерация ответа
            answer = await self.llm.generate_answer(question, similar_docs, deepthink_mode)
            
            # Сбор метрик
            response_time = time.time() - start_time
            intent, _ = self.security.analyze_intent(original_question)
            self.metrics.log_query(original_question, intent, response_time, True)
            
            return f"{answer}\n\n⏱️ Время ответа: {response_time:.2f} сек"
            
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса: {e}")
            return "Произошла ошибка при обработке вашего вопроса"

    def ask_sync(self, question: str) -> str:
        """Синхронная обертка для ask"""
        return asyncio.run(self.ask(question))

    def _fix_keyboard_layout(self, text: str) -> str:
        """Исправление текста, набранного в английской раскладке вместо русской.
        Возвращает исправленный текст или исходный, если замена не требуется.
        """
        if not text:
            return text

        # базовая карта раскладки (латинские -> кириллические)
        en_chars = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
        ru_chars = "йцукенгшщзхъфывапролджэячсмитьбю.ё"
        en_upper = en_chars.upper()
        ru_upper = ru_chars.upper()

        char_map = str.maketrans(en_chars + en_upper, ru_chars + ru_upper)

        # оценка доли символов латиницы (чтобы не переводить обычные русские тексты)
        latin_count = sum(1 for c in text if c in en_chars + en_upper)
        total_len = len(text)
        latin_ratio = (latin_count / total_len) if total_len > 0 else 0.0

        # если более 30% символов — вероятно неправильная раскладка
        if latin_ratio > 0.3:
            fixed = text.translate(char_map)
            logger.info("Исправлена раскладка: '%s' -> '%s'", text, fixed)
            return fixed

        return text

# Если запускается как основной скрипт        
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    assistant = SmartDeepThinkRAG()
    
    print("\nAI Assistant готов к работе!")
    print("Для выхода введите 'exit' или 'quit'")
    
    while True:
        question = input("\nВаш вопрос: ").strip()
        if question.lower() in ['exit', 'quit', 'стоп']:
            break
        if not question:
            continue
            
        print(assistant.ask_sync(question))