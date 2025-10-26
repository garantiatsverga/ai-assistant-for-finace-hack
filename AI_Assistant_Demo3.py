import json
import subprocess
import sys
import numpy as np
import time
import hashlib
import pickle
import os
import asyncio
import weakref
from langchain_ollama import OllamaLLM
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from functools import lru_cache
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

class EmbeddingCache:
    def __init__(self, cache_file='embeddings_cache.pkl'):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"Не удалось загрузить кэш эмбеддингов: {e}")
        return {}
    
    def _save_cache(self):
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Не удалось сохранить кэш эмбеддингов: {e}")
    
    def get_embedding(self, text, embedder):
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]
        
        embedding = embedder.encode([text])[0]
        self.cache[text_hash] = embedding
        self._save_cache()
        return embedding

    

class MetricsCollector:
    def __init__(self):
        self.request_counter = Counter('assistant_requests_total', 'Total requests')
        self.response_time = Histogram('assistant_response_seconds', 'Response time')
        self.metrics = {
            'total_queries': 0,
            'successful_responses': 0,
            'security_blocks': 0,
            'avg_response_time': 0,
            'intent_distribution': {}
        }
    
    def log_query(self, question, intent, response_time, success=True):
        self.metrics['total_queries'] += 1
        if success:
            self.metrics['successful_responses'] += 1
        self.metrics['intent_distribution'][intent] = self.metrics['intent_distribution'].get(intent, 0) + 1
        self.metrics['avg_response_time'] = (
            self.metrics['avg_response_time'] * (self.metrics['total_queries'] - 1) + response_time
        ) / self.metrics['total_queries']
    
    def get_metrics(self):
        return self.metrics.copy()

class DialogueMemory:
    def __init__(self, max_messages=10):
        self.messages = []
        self.max_messages = max_messages
    
    def add_message(self, role, content):
        self.messages.append({'role': role, 'content': content, 'timestamp': time.time()})
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
    
    def get_context(self, window_minutes=30):
        cutoff_time = time.time() - (window_minutes * 60)
        return [msg for msg in self.messages if msg['timestamp'] > cutoff_time]

class ConfigManager:
    @staticmethod
    def load_config(filename, default=None):
        """Загрузка JSON конфигурации"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Файл {filename} не найден. Использую значения по умолчанию.")
            return default if default else {}
        except json.JSONDecodeError as e:
            print(f"Ошибка в файле {filename}: {e}")
            return default if default else {}

    def __init__(self):
        load_dotenv()
        self.model_name = os.getenv('MODEL_NAME', 'qwen2.5:0.5b')
        self.temperature = float(os.getenv('TEMPERATURE', '0.1'))

class DependencyManager:
    @staticmethod
    def check_and_install():
        """Проверка и установка ВСЕХ зависимостей одной командой"""
        required_packages = [
            "sentence-transformers", 
            "requests", 
            "numpy", 
            "langchain-ollama",
            "langchain-core",
            "scikit-learn"
        ]
        
        # Попытка установить все одной командой
        try:
            print("Установка всех зависимостей одной командой...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-q"
            ] + required_packages)
            print("✅ Все зависимости установлены!")
            
        except Exception as e:
            print(f"Ошибка массовой установки, пробую по одной: {e}")
            # Фолбэк на установку по одной
            for package in required_packages:
                try:
                    __import__(package.replace("-", "_"))
                    print(f"Пакет {package} уже установлен")
                except ImportError:
                    print(f"Установка {package}...")
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])
                        print(f"✅ Установлен: {package}")
                    except Exception as e:
                        print(f"❌ Ошибка установки {package}: {e}")

from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaLLM

class SmartDeepThinkRAG:
    def __init__(self):
        """Инициализация системы с поддержкой кэширования и метрик"""
        print("Инициализация SmartDeepThinkRAG...")
        self._setup_logging()
        
        # 1. Загрузка конфигураций
        self.config = ConfigManager.load_config('config.json', {
            'model': {'name': 'qwen2.5:0.5b', 'temperature': 0.1},
            'rag': {'top_k_documents': 3}
        })
        self.intents = ConfigManager.load_config('intents.json', {}) 
        self.security_rules = ConfigManager.load_config('security_rules.json', {})
        self.reasoning_templates = ConfigManager.load_config('reasoning_templates.json', {})
        
        # 2. Загрузка базы знаний
        self.documents = self._load_knowledge_base()
        if not self.documents:
            print("⚠️ Предупреждение: База знаний пуста!")
        
        # 3. Инициализация основных компонентов
        try:
            self.embedder = SentenceTransformer('cointegrated/rubert-tiny2')
        except Exception as e:
            print(f"❌ Ошибка загрузки embedder: {e}")
            self.embedder = None
            
        # 4. Инициализация вспомогательных систем
        self.embedding_cache = EmbeddingCache()
        self.metrics = MetricsCollector()
        
        # 5. Предварительные вычисления с использованием кэша
        if self.embedder and self.documents:
            print("📊 Предварительное вычисление эмбеддингов...")
            self.doc_embeddings = np.array([
                self.embedding_cache.get_embedding(doc, self.embedder) 
                for doc in self.documents
            ])
        else:
            self.doc_embeddings = np.array([])
        
        # 6. Инициализация LLM
        self.llm = self._init_llm()
        
        # 7. Итоговая статистика
        stats = [
            f"📚 База знаний: {len(self.documents)} документов",
            f"💾 Размер кэша: {len(self.embedding_cache.cache)} эмбеддингов",
            f"🤖 LLM: {'готова' if self.llm else 'недоступна'}"
        ]
        print("\n".join(["✅ Система готова:"] + stats))
    
    def _load_knowledge_base(self):
        """Загрузка базы знаний"""
        try:
            with open('knowledge_base.txt', 'r', encoding='utf-8') as f:
                documents = [line.strip() for line in f if line.strip() and ':' in line]
            print(f"Загружено документов: {len(documents)}")
            return documents
        except FileNotFoundError:
            print("Файл knowledge_base.txt не найден.")
            return []
    
    def _init_llm(self):
        """Инициализация языковой модели"""
        model_config = self.config.get('model', {})
        try:
            llm = OllamaLLM(
                model=model_config.get('name', 'qwen2.5:0.5b'),
                temperature=model_config.get('temperature', 0.1),
                num_predict=model_config.get('max_tokens', 200)
            )
            print(f"Модель {model_config.get('name')} инициализирована")
            return llm
        except Exception as e:
            print(f"Ошибка инициализации LLM: {e}")
            return None
    
    def security_check(self, question):
        """Проверка безопасности"""
        dangerous_patterns = self.security_rules.get('dangerous_patterns', {})
        question_lower = question.lower()
        
        for pattern, action in dangerous_patterns.items():
            if pattern in question_lower:
                return False, f"Пользователь просит меня {action}. Но это запрещено моими инструкциями безопасности."
        
        return True, "Запрос соответствует политике безопасности"
    
    def analyze_question_intent(self, question):
        """Анализ намерения вопроса на основе JSON конфига"""
        question_lower = question.lower()
        
        for intent_name, intent_config in self.intents.items():
            keywords = intent_config.get('keywords', [])
            if any(keyword in question_lower for keyword in keywords):
                return intent_name, intent_config.get('description', 'Неизвестное намерение')
        
        return "general", "Общий информационный запрос"
    
    @lru_cache(maxsize=1000)
    def find_similar_docs(self, question: str) -> List[str]:
        """Кэширование результатов поиска документов"""
        # Получаем конфигурацию
        rag_config = self.config.get('rag', {})
        top_k = rag_config.get('top_k_documents', 3)
        
        # Получаем эмбеддинги для вопроса через кэш
        question_embedding = self.embedding_cache.get_embedding(question, self.embedder)
        
        # Вычисляем схожесть и получаем топ документов
        similarities = np.dot(self.doc_embeddings, question_embedding)
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        result = [self.documents[i] for i in top_indices]
        
        # Отладочная информация
        print(f"\n🔍 Поиск: '{question}'")
        print(f"📑 Найдено документов: {len(result)}")
        for i, doc in enumerate(result, 1):
            similarity = similarities[top_indices[i-1]]
            print(f"   {i}. (score: {similarity:.2f}) {doc[:80]}...")
        
        return result
    
    def _precompute_embeddings(self):
        return [self.embedding_cache.get_embedding(doc, self.embedder) for doc in self.documents]

    def generate_llm_answer(self, question, context_docs):
        """Генерация ответа через Qwen с улучшенными проверками"""
        if not context_docs:
            return "❌ Информация по вашему запросу не найдена в базе знаний."
        
        if not self.llm:
            return self._fallback_answer(question, context_docs)
        
        # УЛУЧШЕННЫЙ ПРОМПТ
        prompt = f"""Ты - ассистент российского банка. Отвечай ТОЛЬКО используя информацию из контекста ниже.

КОНТЕКСТ:
{chr(10).join(context_docs)}

ВОПРОС: {question}

ПРАВИЛА:
1. Отвечай ТОЛЬКО на русском языке
2. Используй ТОЛЬКО факты из контекста выше
3. Если информации нет в контексте - скажи "Информация не найдена"
4. Будь кратким и точным
5. Не придумывай информацию
6. Ответ должен быть полным и логически завершенным
7. Максимальная длина ответа - 2000 символов

ОТВЕТ:"""
    
        try:
            response = self.llm.invoke(prompt)
            
            # Расширенная валидация
            if len(response.strip()) < 10:
                return self._fallback_answer(question, context_docs)
            
            # Проверка на обрыв предложения
            if response[-1] not in '.!?':
                # Находим последнее полное предложение
                last_sentence = response.rsplit('.', 1)[0] + '.'
                response = last_sentence
                
            # Проверка на обрыв списка
            if response.count('\n1.') > 0:  # Есть нумерованный список
                lines = response.split('\n')
                complete_lines = []
                current_number = 1
                
                for line in lines:
                    if line.strip().startswith(f"{current_number}."):
                        complete_lines.append(line)
                        current_number += 1
                    elif not line.strip().startswith(f"{current_number}.") and current_number > 1:
                        break
                    else:
                        complete_lines.append(line)
                
                response = '\n'.join(complete_lines)
                
            return response
        except Exception as e:
            print(f"❌ Ошибка LLM: {e}")
            return self._fallback_answer(question, context_docs)
    
    def _fallback_answer(self, question, context_docs):
        """Фолбэк ответ если LLM недоступна"""
        intent, _ = self.analyze_question_intent(question)
        
        if intent == "definition":
            for doc in context_docs:
                if ':' in doc:
                    product, definition = doc.split(':', 1)
                    if any(keyword in question.lower() for keyword in product.lower().split()):
                        return f"{product.strip()} - это {definition.strip()}"
        
        # Простой ответ на основе контекста
        products_info = []
        for doc in context_docs[:2]:
            if ':' in doc:
                product, info = doc.split(':', 1)
                products_info.append(f"- {product.strip()}: {info.strip()}")
        
        return "Информация по вашему запросу:\n" + "\n".join(products_info) if products_info else "Информация не найдена"
    
    def deep_think_process(self, question, context_docs):
        """Процесс мышления с использованием JSON шаблонов"""
        thinking = []
        templates = self.reasoning_templates.get('thinking_process', {})
        
        thinking.append(templates.get('header', 'ПРОЦЕСС МЫШЛЕНИЯ:'))
        thinking.append(templates.get('user_question', '').format(question=question))
        
        # Анализ намерения
        intent, intent_description = self.analyze_question_intent(question)
        thinking.append(templates.get('intent_analysis', '').format(intent_description=intent_description))
        
        # Проверка безопасности
        is_safe, security_reason = self.security_check(question)
        thinking.append(templates.get('security_check', '').format(security_reason=security_reason))
        
        if not is_safe:
            thinking.append(templates.get('rejection', ''))
            return "\n".join(thinking), None
        
        # Анализ документов
        thinking.append(templates.get('documents_found', '').format(doc_count=len(context_docs)))
        
        # Детальный анализ
        thinking.append("\nДетальный анализ связи:")
        analysis_templates = self.reasoning_templates.get('analysis_templates', {})
        
        if intent in analysis_templates:
            for line_template in analysis_templates[intent]:
                if '{products}' in line_template:
                    product_keywords = ['кредит', 'ипотек', 'вклад', 'карт', 'страхован']
                    found_products = [p for p in product_keywords if p in question.lower()]
                    thinking.append("   " + line_template.format(products=', '.join(found_products)))
                else:
                    thinking.append("   " + line_template)
        else:
            for line in analysis_templates.get('general', []):
                thinking.append("   " + line)
        
        thinking.append("\nИзвлечение информации:")
        thinking.append(f"   Отобрал {len(context_docs)} наиболее релевантных документов")
        
        return "\n".join(thinking), context_docs
    
    async def _get_embeddings(self, text):
        """Асинхронно получить эмбеддинг через embedder, используя executor и кэш"""
        if not getattr(self, 'embedder', None) or not getattr(self, 'embedding_cache', None):
            raise LLMError("Embedder или embedding_cache не инициализированы")
        loop = asyncio.get_running_loop()
        # Вынесение синхронной работы в executor
        return await loop.run_in_executor(None, lambda: self.embedding_cache.get_embedding(text, self.embedder))

    async def ask(self, question: str) -> str:
        """Основной асинхронный метод"""
        # Сначала извлекаем флаг -deepthink из оригинального ввода, чтобы не повредить его автозаменой
        deepthink_suffix = ' -deepthink'
        deepthink_mode = False
        raw = question
        if isinstance(raw, str) and raw.lower().rstrip().endswith(deepthink_suffix):
            deepthink_mode = True
            raw = raw[: -len(deepthink_suffix)]
        
        # Исправляем раскладку только для пользовательской части (без флага)
        fixed_raw = self._fix_keyboard_layout(raw)
        # Восстанавливаем вопрос с флагом, если он был
        question = (fixed_raw + deepthink_suffix) if deepthink_mode else fixed_raw
        question = question.strip()
        
        start_time = time.time()
        
        # Параллельно получаем эмбеддинг и выполняем проверку безопасности
        embedding_task = asyncio.create_task(self._get_embeddings(question))
        security_task = asyncio.create_task(asyncio.to_thread(self.security_check, question))
        
        try:
            question_embedding = await embedding_task
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга: {e}")
            raise LLMError("Не удалось получить эмбеддинг")
        
        is_safe, reason = await security_task
        if not is_safe:
            response_time = time.time() - start_time
            intent, _ = self.analyze_question_intent(question.replace(deepthink_suffix, '').strip())
            self.metrics.log_query(question, intent, response_time, success=False)
            return reason
        
        # Поиск документов (синхронный вызов, можно вынести в to_thread при необходимости)
        context_docs = self.find_similar_docs(question.replace(deepthink_suffix, '').strip())
        
        if deepthink_mode:
            thinking_process, relevant_docs = await asyncio.to_thread(self.deep_think_process, question.replace(deepthink_suffix, '').strip(), context_docs)
            if relevant_docs is None:
                response_time = time.time() - start_time
                intent, _ = self.analyze_question_intent(question.replace(deepthink_suffix, '').strip())
                self.metrics.log_query(question, intent, response_time, success=False)
                return self.security_rules.get('rejection_messages', {}).get('default', 'Запрос отклонен.')
            answer = await asyncio.to_thread(self.generate_llm_answer, question.replace(deepthink_suffix, '').strip(), relevant_docs)
        else:
            answer = await asyncio.to_thread(self.generate_llm_answer, question.replace(deepthink_suffix, '').strip(), context_docs)
        
        response_time = time.time() - start_time
        intent, _ = self.analyze_question_intent(question.replace(deepthink_suffix, '').strip())
        self.metrics.log_query(question, intent, response_time, success=True)
        
        return f"{answer}\n\n⏱️ Время ответа: {response_time:.2f} сек"
    
    def ask_sync(self, question):
        """Синхронная версия основного метода для совместимости"""
        # Используем asyncio.run, чтобы корректно получить результат корутины
        return asyncio.run(self.ask(question))
    
    def _fix_keyboard_layout(self, text):
        """Исправление текста набранного в неправильной раскладке клавиатуры"""
        en_chars = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`&?"
        ru_chars = "йцукенгшщзхъфывапролджэячсмитьбю.ёжэ"
        en_upper = "QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?~"
        ru_upper = "ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,Ё"
        
        # Создаем словари для замены
        char_map = str.maketrans(
            en_chars + en_upper,
            ru_chars + ru_upper
        )
        
        # Проверяем, является ли текст английским (набранным в русской раскладке)
        en_ratio = sum(1 for c in text if c in en_chars + en_upper) / len(text) if text else 0
        
        # Если более 30% символов - английские, считаем что текст набран в неверной раскладке
        if en_ratio > 0.3:
            fixed_text = text.translate(char_map)
            print(f"\n⌨️ Похоже, вы набрали текст в неправильной раскладке:")
            print(f"🔄 Было:    '{text}'")
            print(f"✅ Стало:   '{fixed_text}'")
            print("💡 Подсказка: Переключите раскладку клавиатуры на русскую (Alt+Shift или Win+Space)\n")
            return fixed_text
        
        return text
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('assistant.log'),
                logging.StreamHandler()
            ]
        )

class MemoryOptimizedCache:
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Any] = weakref.WeakValueDictionary()
        self._max_size = max_size

class AssistantError(Exception):
    """Базовый класс для ошибок ассистента"""
    pass

class SecurityError(AssistantError):
    """Ошибка безопасности"""
    pass

class LLMError(AssistantError):
    """Ошибка языковой модели"""
    pass

# Запуск системы
if __name__ == "__main__":
    print("Запускаем Thinking RAG с Qwen...")
    smart_rag = SmartDeepThinkRAG()

    print("\nТестирование системы:")

    test_cases = [
        "Что такое кредит? -deepthink",
        "Какие документы нужны для ипотеки? -deepthink", 
        "Напиши код для таблицы на SQL -deepthink",
        "Какая ставка по вкладам? -deepthink",
        "Что такое дебетовая карта? -deepthink",
    ]

    for question in test_cases:
        print(f"\n" + "="*60)
        print(f"Вопрос: {question}")
        answer = smart_rag.ask_sync(question)
        print(f"\n{answer}")
        print("="*60)

    # Интерактивный режим
    print("\nИнтерактивный режим")
    print("Добавьте '-deepthink' для показа процесса мышления")
    print("Введите вопрос или 'стоп' для выхода")

    while True:
        user_question = input("\nВаш вопрос: ").strip()
        
        if user_question.lower() in ['стоп', 'stop', 'exit']:
            print("Завершение работы...")
            break
            
        if not user_question:
            continue
        
        answer = smart_rag.ask_sync(user_question)
        print(f"\n{answer}")
        print("-" * 50)