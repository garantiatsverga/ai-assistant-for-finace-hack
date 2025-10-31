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
    
    def __init__(self, model_name: str = "qwen2.5:0.5b", base_url: str = "http://localhost:11434", timeout: int = 120):
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
                                    deep_think: bool = False,
                                    flags: List[str] = None) -> AsyncGenerator[str, None]:
        """Генерация ответа со стримингом с поддержкой флагов"""
        
        if flags is None:
            flags = []
        
        logger.info(f"[LLM-1] Начало generate_answer_streaming. Флаги: {flags}")
        
        # Защитный слой: отказываем в генерации исполняемого кода/SQL (если не отключено флагом)
        if self._is_code_request(question) and '-nocode' not in flags:
            logger.info("[LLM-1a] Запрос заблокирован (код/SQL)")
            yield "Извините, я не могу помогать с генерацией исполняемого кода или SQL-запросов по соображениям безопасности."
            return

        logger.info("[LLM-2] Создаем промпт")
        prompt = self._create_prompt(question, context_docs, deep_think, flags)
        
        logger.info("[LLM-3] Начинаем стриминг от Ollama")
        try:
            chunk_count = 0
            async for chunk in self._stream_from_ollama(prompt):
                logger.info(f"[LLM-3a] Отправляем chunk #{chunk_count}: '{chunk}'")
                chunk_count += 1
                
                # Если активен простой режим, убираем лишние формальности
                if '-simple' in flags:
                    chunk = self._simplify_response(chunk)
                    
                yield chunk
                    
            logger.info(f"[LLM-4] generate_answer_streaming завершен. Чанков: {chunk_count}")
            
        except Exception as e:
            logger.error(f"[LLM-ERROR] Ошибка в generate_answer_streaming: {e}")
            yield self._fallback_answer(context_docs)

    async def _stream_from_ollama(self, prompt: str) -> AsyncGenerator[str, None]:
        """Правильное потоковое получение ответа от Ollama API с ретраями"""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 600,
                "repeat_penalty": 1.2
            }
        }
        
        max_retries = 2
        retry_delay = 1
        
        for attempt in range(max_retries + 1):
            try:
                async with self._create_session() as session:
                    async with session.post(url, json=payload) as response:
                        logger.info(f"Статус ответа: {response.status}")
                        
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Ошибка Ollama API: {response.status} - {error_text}")
                            
                            if attempt < max_retries:
                                logger.info(f"Повторная попытка {attempt + 1}/{max_retries}")
                                await asyncio.sleep(retry_delay)
                                continue
                            else:
                                yield "Ошибка соединения с моделью."
                                return
                        
                        logger.info("Начинаем чтение потока...")
                        chunk_count = 0
                        
                        async for line_bytes in response.content:
                            if line_bytes:
                                line = line_bytes.decode('utf-8').strip()
                                
                                if not line:
                                    continue
                                    
                                try:
                                    data = json.loads(line)
                                    
                                    if data.get('done', False):
                                        logger.info(f"Стриминг завершен. Чанков: {chunk_count}")
                                        break
                                    
                                    if 'response' in data and data['response']:
                                        chunk_count += 1
                                        yield data['response']
                                        
                                except json.JSONDecodeError:
                                    continue
                                except Exception:
                                    continue
                        
                        logger.info("Поток успешно завершен")
                        return
                                        
            except asyncio.TimeoutError:
                logger.warning(f"Таймаут на попытке {attempt + 1}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    yield "Превышено время ожидания ответа."
                    return
            except aiohttp.ClientConnectorError:
                logger.error("Не удалось подключиться к Ollama")
                yield "Не удалось подключиться к языковой модели."
                return
            except Exception as e:
                logger.error(f"Неожиданная ошибка: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    yield "Произошла ошибка при генерации ответа."
                    return

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
                    deep_think: bool,
                    flags: List[str]) -> str:
        """Улучшенный промпт для инвестиционных вопросов"""
        
        context_text = "\n".join(context_docs) if context_docs else "Информация не найдена"
        
        question_lower = question.lower()
        if any(word in question_lower for word in ['акции', 'инвестиц', 'вложить', 'куда вложить', 'выгодн', 'портфель']):
            return f"""Ты - финансовый консультант. Дай конкретные рекомендации по инвестициям в акции.

    ВОПРОС КЛИЕНТА: {question}

    БАЗА ЗНАНИЙ ОБ АКЦИЯХ:
    {context_text}

    ИНСТРУКЦИИ:
    - Дай конкретные рекомендации по акциям
    - Объясни почему именно эти акции
    - Учитывай риск и потенциальную доходность
    - Предложи диверсификацию портфеля
    - Будь конкретен и практичен

    ОТВЕТ:"""
        
        elif deep_think:
            return f"""ПРОЦЕСС МЫШЛЕНИЯ:

    1. АНАЛИЗ ЗАПРОСА:
    - Вопрос пользователя: "{question}"
    - Возможное намерение: {self._analyze_intent(question)}
    - Соответствие политике безопасности: {"Соответствует" if not self._is_code_request(question) else "❌ Нарушает"}

    2. ИНФОРМАЦИЯ ДЛЯ ОТВЕТА:
    {context_text}

    3. ЛОГИЧЕСКИЙ АНАЛИЗ:
    - Какая информация наиболее релевантна?
    - Что именно спрашивает пользователь?
    - Какие детали важны для полного ответа?

    4. ФОРМИРОВАНИЕ ОТВЕТА:
    - Структурировать информацию логически
    - Выделить ключевые моменты
    - Дать практические рекомендации

    ОТВЕТ:"""
        
        elif '-simple' in flags:
            # Простой режим
            return f"Вопрос: {question}\nДанные: {context_text}\nКраткий ответ:"
            
        else:
            # Обычный режим
            return f"""Ответь на вопрос: {question}

    Информация для ответа:
    {context_text}

    Ответ:"""    
        
    def _analyze_intent(self, question: str) -> str:
        """Анализ намерения пользователя"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['что такое', 'определ', 'означает']):
            return "получить определение понятия"
        elif any(word in question_lower for word in ['как', 'процесс', 'оформить']):
            return "узнать процесс оформления"
        elif any(word in question_lower for word in ['документ', 'нужно', 'требуется']):
            return "узнать необходимые документы"
        elif any(word in question_lower for word in ['ставк', 'процент', 'сколько стоит']):
            return "узнать стоимость или ставки"
        elif any(word in question_lower for word in ['акции', 'инвестиц', 'вложить']):
            return "получить инвестиционные рекомендации"
        else:
            return "общий информационный запрос"
    
    def _fallback_answer(self, context_docs: List[str]) -> str:
        """Ответ при ошибке LLM"""
        if not context_docs:
            return "Информация по вашему запросу не найдена в базе знаний."
        
        return "Найденная информация:\n" + "\n".join(
            [f"• {doc[:100]}..." if len(doc) > 100 else f"• {doc}" 
             for doc in context_docs[:3]]
        )

    def _simplify_response(self, text: str) -> str:
        """Упрощение ответа для простого режима"""
        # Убираем формальные обращения и лишние слова
        simplifications = {
            "Конечно,": "",
            "Рад помочь!": "",
            "Вот ответ на ваш вопрос:": "",
            "Согласно предоставленной информации,": ""
        }
        
        for old, new in simplifications.items():
            text = text.replace(old, new)
        
        return text.strip()