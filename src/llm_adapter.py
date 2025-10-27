from typing import List, Optional, AsyncGenerator
import aiohttp
import json
import logging
import re
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class LLMError(Exception):
    """Ошибки при работе с LLM"""
    pass

class LLMAdapter:
    """Адаптер для работы с языковой моделью через Ollama API"""
    
    def __init__(self, model_name: str = "qwen2.5:0.5b", base_url: str = "http://localhost:11434", timeout: int = 30):
        self.model_name = model_name
        self.base_url = base_url
        self.timeout = timeout
        
        # Шаблоны для определения запросов на генерацию кода/SQL
        self._code_patterns = re.compile(
            r'\b(sql|select|insert|update|delete|drop|create table|execute|eval|exec)\b|написать код|сгенерируй sql',
            flags=re.IGNORECASE
        )

    def _is_code_request(self, text: str) -> bool:
        """Проверка, является ли запрос запросом на генерацию кода"""
        if not text:
            return False
        return bool(self._code_patterns.search(text))

    @asynccontextmanager
    async def _create_session(self):
        """Создание aiohttp сессии с таймаутом"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        session = aiohttp.ClientSession(timeout=timeout)
        try:
            yield session
        finally:
            await session.close()

    async def generate_answer_streaming(self, 
                                      question: str, 
                                      context_docs: List[str],
                                      deep_think: bool = False) -> AsyncGenerator[str, None]:
        """Генерация ответа со стримингом в реальном времени"""
        
        # Защитный слой: отказываем в генерации исполняемого кода/SQL
        if self._is_code_request(question):
            yield "Извините, я не могу помогать с генерацией исполняемого кода или SQL-запросов по соображениям безопасности."
            return

        prompt = self._create_prompt(question, context_docs, deep_think)
        
        try:
            async for chunk in self._stream_from_ollama(prompt):
                yield chunk
                
        except asyncio.TimeoutError:
            logger.error("Таймаут при генерации ответа")
            yield "⏰ Превышено время ожидания ответа. Попробуйте позже."
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            yield self._fallback_answer(context_docs)

    async def _stream_from_ollama(self, prompt: str) -> AsyncGenerator[str, None]:
        """Потоковое получение ответа от Ollama API с защитой от повторений"""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 800,  # Уменьшим длину ответа
                "repeat_penalty": 1.3,  # Увеличим штраф за повторения
                "stop": ["\n\n", "###", "Кредит - это"]  # Стоп-слова для предотвращения зацикливания
            }
        }
        
        last_chunk = ""
        chunk_count = 0
        
        async with self._create_session() as session:
            try:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ошибка Ollama API: {response.status} - {error_text}")
                        yield "❌ Ошибка соединения с моделью."
                        return
                    
                    async for line in response.content:
                        if line:
                            line_text = line.decode('utf-8').strip()
                            if line_text:
                                try:
                                    data = json.loads(line_text)
                                    
                                    if data.get('done', False):
                                        break
                                    
                                    if 'response' in data and data['response']:
                                        chunk = data['response']
                                        
                                        # Защита от повторений - пропускаем если chunk похож на предыдущий
                                        if chunk != last_chunk:
                                            yield chunk
                                            last_chunk = chunk
                                            chunk_count += 1
                                        
                                        # Ограничиваем максимальное количество чанков
                                        if chunk_count > 500:
                                            break
                                        
                                except json.JSONDecodeError:
                                    continue
                                    
            except Exception as e:
                logger.error(f"Ошибка при стриминге: {e}")
                yield "❌ Произошла ошибка при генерации ответа."

    async def generate_answer(self, 
                            question: str, 
                            context_docs: List[str],
                            deep_think: bool = False) -> str:
        """Обычная генерация ответа (для обратной совместимости)"""
        full_response = ""
        async for chunk in self.generate_answer_streaming(question, context_docs, deep_think):
            full_response += chunk
        return full_response

    def _create_prompt(self, 
                    question: str, 
                    context_docs: List[str],
                    deep_think: bool) -> str:
        """Строгий промпт с акцентом на использование контекста"""
        
        # Проверяем контекст
        if context_docs and context_docs[0] != "Информация по вашему запросу не найдена в базе знаний.":
            context_text = "ДОСТУПНАЯ ИНФОРМАЦИЯ:\n" + "\n".join([f"• {doc}" for doc in context_docs])
            context_status = "ИНФОРМАЦИЯ_НАЙДЕНА"
        else:
            context_text = "ИНФОРМАЦИЯ НЕ НАЙДЕНА"
            context_status = "ИНФОРМАЦИЯ_НЕ_НАЙДЕНА"
        
        base_prompt = f"""Ты - ассистент банка. Отвечай ТОЛЬКО на основе информации ниже.

    {context_text}

    ВОПРОС: {question}
    СТАТУС_КОНТЕКСТА: {context_status}

    ЖЕСТКИЕ ПРАВИЛА:
    - ЕСЛИ СТАТУС_КОНТЕКСТА = "ИНФОРМАЦИЯ_НЕ_НАЙДЕНА" → ответь: "Информация по вашему запросу не найдена в базе знаний."
    - ЕСЛИ СТАТУС_КОНТЕКСТА = "ИНФОРМАЦИЯ_НАЙДЕНА" → используй ТОЛЬКО информацию из контекста
    - НЕ добавляй приветствия, вступления, заключения
    - НЕ придумывай информацию
    - Ответ должен быть КРАТКИМ (1-2 предложения)

    ПРИМЕРЫ:
    ВОПРОС: Что такое кредит?
    КОНТЕКСТ: • КРЕДИТ: Деньги банка на 1-5 лет под 12-18% годовых.
    ОТВЕТ: Кредит - это деньги банка на 1-5 лет под 12-18% годовых.

    ВОПРОС: Что такое инвестиции?  
    КОНТЕКСТ: ИНФОРМАЦИЯ НЕ НАЙДЕНА
    ОТВЕТ: Информация по вашему запросу не найдена в базе знаний.

    ОТВЕТ:"""
        
        return base_prompt    
    
    def _fallback_answer(self, context_docs: List[str]) -> str:
        """Ответ при ошибке LLM"""
        if not context_docs:
            return "❌ Информация по вашему запросу не найдена в базе знаний."
        
        return "Найденная информация:\n" + "\n".join(
            [f"• {doc[:100]}..." if len(doc) > 100 else f"• {doc}" 
             for doc in context_docs[:3]]
        )