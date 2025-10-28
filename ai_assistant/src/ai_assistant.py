"""Main AI Assistant module"""
from typing import List, Optional, Dict, Any, AsyncGenerator
import asyncio
import logging
import os
import time
import sys

# Добавляем путь для импортов
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, current_dir)

from .cache_manager import EmbeddingCache
from .config_manager import ConfigManager
from .security_checker import SecurityChecker
from .metrics_collector import MetricsCollector
from .dialogue_memory import DialogueMemory
from .llm_adapter import LLMAdapter, LLMError
from .embeddings_manager import EmbeddingsManager

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
        """Асинхронный метод со detailed tracing и поддержкой флагов"""
        start_time = time.time()
        
        try:
            logger.info("🔧 [1] Начало ask_streaming")
            
            # Извлекаем флаги из вопроса
            clean_question, flags = self.security._extract_flags(question)
            
            # Показываем активные флаги
            if flags:
                yield f"\n🎛️ Активные флаги: {', '.join(flags)}\n"
            
            # Сохраняем оригинальный вопрос для метрик
            original_question = question
            
            # Проверяем режим deep think (учитываем флаги)
            deepthink_mode = question.endswith(" -deepthink") and '-nodeep' not in flags
            if deepthink_mode:
                clean_question = clean_question[:-10].strip()
                
            logger.info("🔧 [2] Исправляем раскладку")
            clean_question = self._fix_keyboard_layout(clean_question)
            
            logger.info("🔧 [3] Проверяем безопасность")
            is_safe, reason = await self.security.check(question)  # Проверяем оригинальный вопрос с флагами
            
            if not is_safe:
                logger.info("🔧 [3a] Запрос заблокирован")
                yield reason
                return
            
            logger.info("🔧 [4] Получаем эмбеддинг вопроса")
            question_embedding = await self.embedding_manager.get_embedding(clean_question)
            
            logger.info("🔧 [5] Ищем похожие документы")
            similar_docs = await self.embedding_manager.find_similar(
                clean_question,
                question_embedding,
                self.doc_embeddings,
                self.documents,
                top_k=self.config['rag']['top_k_documents']
            )
            
            logger.info(f"🔧 [5a] Найдено документов: {len(similar_docs)}")
            
            # Добавляем сообщение в память диалога
            self.memory.add_message('user', clean_question)
            
            # Генерация ответа со стримингом
            full_response = ""
            
            # Сначала выводим индикатор начала ответа
            logger.info("🔧 [6] Отправляем индикатор ответа")
            
            # Показываем информацию о режиме
            if '-simple' in flags:
                yield "\n🤖 [ПРОСТОЙ РЕЖИМ] "
            elif flags:
                yield f"\n🤖 [РЕЖИМ: {', '.join(flags)}] "
            else:
                yield "\n🤖 Ответ: "
            
            # Затем стримим ответ от модели
            logger.info("🔧 [7] Начинаем стриминг от LLM")
            chunk_count = 0
            
            # Передаем флаги в LLM для адаптации ответа
            async for chunk in self.llm.generate_answer_streaming(clean_question, similar_docs, deepthink_mode, flags):
                logger.info(f"🔧 [7a] Получен chunk #{chunk_count}: '{chunk}'")
                chunk_count += 1
                yield chunk
                full_response += chunk
            
            logger.info(f"🔧 [8] Стриминг завершен. Чанков: {chunk_count}")
            
            # Добавляем ответ в память
            self.memory.add_message('assistant', full_response)
            
            # В конце выводим время ответа
            response_time = time.time() - start_time
            time_info = f"\n\n⏱️ Время ответа: {response_time:.2f} сек"
            logger.info(f"🔧 [9] Отправляем время ответа: {response_time:.2f}сек")
            yield time_info
            
            # Сбор метрик
            intent, _ = self.security.analyze_intent(original_question)
            self.metrics.log_query(original_question, intent, response_time, True)
            
            logger.info("🔧 [10] Ask_streaming завершен успешно")
            
        except Exception as e:
            logger.error(f"💥 Критическая ошибка в ask_streaming: {e}", exc_info=True)
            yield f"❌ Произошла ошибка: {e}"

    async def ask(self, question: str) -> str:
        """Асинхронный метод для прямого вызова из main.py"""
        full_response = ""
        async for chunk in self.ask_streaming(question):
            print(chunk, end='', flush=True)
            full_response += chunk
        print()  # Конечный перенос строки
        return full_response
    
    async def ask_streaming_wrapper(self, question: str) -> None:
        """Обертка для вывода стриминга напрямую в консоль"""
        async for chunk in self.ask_streaming(question):
            print(chunk, end='', flush=True)
        print()  # Конечный перенос строки

    def ask_sync(self, question: str) -> str:
        """Синхронная обертка для использования в асинхронном контексте"""
        import asyncio
        
        # Просто запускаем асинхронную функцию и возвращаем результат
        # Без создания новых event loops
        try:
            # Пробуем получить текущий loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если loop уже запущен, используем asyncio.run_coroutine_threadsafe
                future = asyncio.run_coroutine_threadsafe(self.ask(question), loop)
                return future.result()
            else:
                # Если loop не запущен, используем run_until_complete
                return loop.run_until_complete(self.ask(question))
        except RuntimeError:
            # Если нет event loop, создаем новый
            return asyncio.run(self.ask(question))

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