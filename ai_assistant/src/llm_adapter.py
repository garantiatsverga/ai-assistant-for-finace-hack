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
        """Генерация ответа со стримингом с tracing"""
        
        logger.info("🔧 [LLM-1] Начало generate_answer_streaming")
        
        # Защитный слой: отказываем в генерации исполняемого кода/SQL
        if self._is_code_request(question):
            logger.info("🔧 [LLM-1a] Запрос заблокирован (код/SQL)")
            yield "Извините, я не могу помогать с генерацией исполняемого кода или SQL-запросов по соображениям безопасности."
            return

        logger.info("🔧 [LLM-2] Создаем промпт")
        prompt = self._create_prompt(question, context_docs, deep_think)
        
        logger.info("🔧 [LLM-3] Начинаем стриминг от Ollama")
        try:
            chunk_count = 0
            async for chunk in self._stream_from_ollama(prompt):
                logger.info(f"🔧 [LLM-3a] Отправляем chunk #{chunk_count}: '{chunk}'")
                chunk_count += 1
                yield chunk
                    
            logger.info(f"🔧 [LLM-4] generate_answer_streaming завершен. Чанков: {chunk_count}")
            
        except Exception as e:
            logger.error(f"🔧 [LLM-ERROR] Ошибка в generate_answer_streaming: {e}")
            yield self._fallback_answer(context_docs)

    async def _stream_from_ollama(self, prompt: str) -> AsyncGenerator[str, None]:
        """Правильное потоковое получение ответа от Ollama API"""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 500,
                "repeat_penalty": 1.2
            }
        }
        
        logger.info(f"🔧 Отправляем запрос к Ollama...")
        
        async with self._create_session() as session:
            try:
                async with session.post(url, json=payload) as response:
                    logger.info(f"🔧 Статус ответа: {response.status}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка Ollama API: {response.status} - {error_text}")
                        yield "❌ Ошибка соединения с моделью."
                        return
                    
                    logger.info("🔧 Начинаем чтение потока...")
                    
                    # Читаем поток построчно
                    async for line_bytes in response.content:
                        if line_bytes:
                            line = line_bytes.decode('utf-8').strip()
                            
                            # Пропускаем пустые строки
                            if not line:
                                continue
                                
                            try:
                                data = json.loads(line)
                                
                                # Проверяем завершение
                                if data.get('done', False):
                                    logger.info("🔧 Стриминг завершен")
                                    break
                                
                                # Отправляем response если есть
                                if 'response' in data and data['response']:
                                    yield data['response']
                                    
                            except json.JSONDecodeError:
                                logger.warning(f"🔧 Невалидный JSON: {line}")
                                continue
                            except Exception as e:
                                logger.warning(f"🔧 Ошибка обработки: {e}")
                                continue
                    
                    logger.info("🔧 Поток завершен")
                                    
            except asyncio.TimeoutError:
                logger.error("⏰ Таймаут при стриминге")
                yield "⏰ Превышено время ожидания ответа."
            except aiohttp.ClientConnectorError:
                logger.error("🔌 Не удалось подключиться к Ollama")
                yield "🔌 Не удалось подключиться к языковой модели."
            except Exception as e:
                logger.error(f"💥 Неожиданная ошибка: {e}")
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
        """Упрощенный промпт для тестирования"""
        
        context_text = "\n".join(context_docs) if context_docs else "Информация не найдена"
        
        prompt = f"""Ответь на вопрос: {question}

    Информация для ответа:
    {context_text}

    Ответ:"""
        
        return prompt
    
    def _fallback_answer(self, context_docs: List[str]) -> str:
        """Ответ при ошибке LLM"""
        if not context_docs:
            return "❌ Информация по вашему запросу не найдена в базе знаний."
        
        return "Найденная информация:\n" + "\n".join(
            [f"• {doc[:100]}..." if len(doc) > 100 else f"• {doc}" 
             for doc in context_docs[:3]]
        )