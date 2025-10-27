"""Main AI Assistant module"""
from typing import List, Optional, Dict, Any, AsyncGenerator
import asyncio
import logging
import os
import time

from ..src.cache_manager import EmbeddingCache
from ..src.config_manager import ConfigManager
from ..src.security_checker import SecurityChecker
from ..src.metrics_collector import MetricsCollector
from ..src.dialogue_memory import DialogueMemory
from ..src.llm_adapter import LLMAdapter, LLMError
from ..src.embeddings_manager import EmbeddingsManager

logger = logging.getLogger(__name__)

class AssistantInitializationError(Exception):
    """Ошибка инициализации ассистента"""
    pass

class SmartDeepThinkRAG:
    """Основной класс ассистента с поддержкой streaming"""
    
    def __init__(self, config_path: str = "config.json"):
        try:
            self.config = ConfigManager.load_config(config_path)
            self._validate_config()
            
            # Инициализация компонентов
            self.embedding_manager = EmbeddingsManager(
                self.config['embedder']['model_name']
            )
            self.embedding_cache = EmbeddingCache()
            self.llm = LLMAdapter(
                model_name=self.config['model']['name'],
                timeout=self.config.get('model', {}).get('timeout', 30)
            )
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
            
        except Exception as e:
            logger.error(f"Ошибка инициализации ассистента: {e}")
            raise AssistantInitializationError(f"Не удалось инициализировать ассистент: {e}")

    def _validate_config(self):
        """Валидация конфигурации"""
        required_fields = ['model', 'rag', 'embedder']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Отсутствует обязательное поле конфигурации: {field}")

    def _load_knowledge_base(self) -> List[str]:
        """Загрузка базы знаний из файла"""
        knowledge_base_paths = [
            "knowledge_base.txt",
            os.path.join(os.path.dirname(__file__), '..', 'data', 'knowledge_base.txt'),
            os.path.join(os.path.dirname(__file__), 'knowledge_base.txt')
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

    async def ask_streaming(self, question: str) -> AsyncGenerator[str, None]:
        """Асинхронный метод обработки вопроса со стримингом в реальном времени"""
        start_time = time.time()
        
        try:
            # Сохраняем оригинальный вопрос для метрик
            original_question = question
            
            # Проверяем режим deep think
            deepthink_mode = question.endswith(" -deepthink")
            if deepthink_mode:
                question = question[:-10].strip()
                
            # Исправляем раскладку
            question = self._fix_keyboard_layout(question)
            
            # Проверяем безопасность
            is_safe, reason = await self.security.check(question)
            if not is_safe:
                yield reason
                return
            
            # Получаем эмбеддинг вопроса
            question_embedding = await self.embedding_manager.get_embedding(question)
            
            # Ищем релевантные документы
            similar_docs = await self.embedding_manager.find_similar(
                question,
                question_embedding,
                self.doc_embeddings,
                self.documents,
                top_k=self.config['rag']['top_k_documents']
            )
            
            # Добавляем сообщение в память диалога
            self.memory.add_message('user', question)
            
            # Генерация ответа со стримингом
            full_response = ""
            
            # Сначала выводим индикатор начала ответа
            yield "\n🤖 Ответ: "
            
            # Затем стримим ответ от модели
            async for chunk in self.llm.generate_answer_streaming(question, similar_docs, deepthink_mode):
                if chunk:
                    yield chunk
                    full_response += chunk
            
            # Добавляем ответ в память
            self.memory.add_message('assistant', full_response)
            
            # В конце выводим время ответа
            response_time = time.time() - start_time
            time_info = f"\n\n⏱️ Время ответа: {response_time:.2f} сек"
            yield time_info
            
            # Сбор метрик
            intent, _ = self.security.analyze_intent(original_question)
            self.metrics.log_query(original_question, intent, response_time, True)
            
        except RuntimeError as e:
            logger.error(f"Ошибка при обработке вопроса: {e}")
            yield "😔 Извините, произошла техническая ошибка. Попробуйте повторить запрос позже."
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            yield "❌ Произошла непредвиденная ошибка. Пожалуйста, обратитесь к администратору."

    async def ask(self, question: str) -> str:
        """Асинхронный метод для обратной совместимости (без стриминга)"""
        full_response = ""
        async for chunk in self.ask_streaming(question):
            full_response += chunk
        return full_response

    def ask_sync(self, question: str) -> str:
        """Синхронная обертка с посимвольным выводом в реальном времени"""
        
        print("\n🤖 Обрабатываю запрос...", end='', flush=True)
        
        async def process_question():
            first_chunk = True
            full_response = ""
            
            async for chunk in self.ask_streaming(question):
                if first_chunk and chunk == "\n🤖 Ответ: ":
                    print("\r" + " " * 30 + "\r", end='')  # Очищаем строку "Обрабатываю запрос..."
                    print("🤖 Ответ: ", end='', flush=True)
                    first_chunk = False
                else:
                    print(chunk, end='', flush=True)
                    full_response += chunk
            
            print()  # Конечный перенос строки
            return full_response
        
        return asyncio.run(process_question())

    def _fix_keyboard_layout(self, text: str) -> str:
        """Исправление текста, набранного в английской раскладке вместо русской"""
        if not text:
            return text

        en_chars = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
        ru_chars = "йцукенгшщзхъфывапролджэячсмитьбю.ё"
        en_upper = en_chars.upper()
        ru_upper = ru_chars.upper()

        char_map = str.maketrans(en_chars + en_upper, ru_chars + ru_upper)

        latin_count = sum(1 for c in text if c in en_chars + en_upper)
        total_len = len(text)
        latin_ratio = (latin_count / total_len) if total_len > 0 else 0.0

        if latin_ratio > 0.3:
            fixed = text.translate(char_map)
            logger.info("Исправлена раскладка: '%s' -> '%s'", text, fixed)
            return fixed

        return text

# Если запускается как основной скрипт        
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        assistant = SmartDeepThinkRAG()
        
        print("\n🎯 AI Assistant готов к работе!")
        print("💡 Для углубленного анализа добавьте '-deepthink' к вопросу")
        print("🚪 Для выхода введите 'exit', 'quit' или 'стоп'")
        
        while True:
            question = input("\n💬 Ваш вопрос: ").strip()
            if question.lower() in ['exit', 'quit', 'стоп']:
                print("👋 До свидания!")
                break
            if not question:
                continue
                
            assistant.ask_sync(question)
            
    except AssistantInitializationError as e:
        print(f"❌ Ошибка инициализации: {e}")
        print("🔧 Проверьте настройки и зависимости")
    except KeyboardInterrupt:
        print("\n👋 Работа завершена пользователем")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")