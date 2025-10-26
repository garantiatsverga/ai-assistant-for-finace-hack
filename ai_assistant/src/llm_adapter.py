from typing import List, Optional
from langchain_ollama import OllamaLLM
import asyncio
import logging
import re

logger = logging.getLogger(__name__)

class LLMError(Exception):
    """Ошибки при работе с LLM"""
    pass

class LLMAdapter:
    """Адаптер для работы с языковой моделью"""
    
    def __init__(self, model_name: str = "qwen2.5:0.5b"):
        try:
            self.llm = OllamaLLM(model=model_name)
        except Exception as e:
            logger.error(f"Ошибка инициализации LLM: {e}")
            self.llm = None

        # Шаблоны для определения запросов на генерацию кода/SQL
        self._code_patterns = re.compile(
            r'\b(sql|select|insert|update|delete|drop|create table|execute|eval|exec)\b|написать код|сгенерируй sql',
            flags=re.IGNORECASE
        )

    def _is_code_request(self, text: str) -> bool:
        if not text:
            return False
        return bool(self._code_patterns.search(text))

    async def generate_answer(self, 
                            question: str, 
                            context_docs: List[str],
                            deep_think: bool = False) -> str:
        """Генерация ответа с учетом контекста. Блокируем генерацию кода/SQL."""
        # Защитный слой: отказываем в генерации исполняемого кода/SQL прямо здесь
        if self._is_code_request(question):
            logger.info("Запрос на генерацию кода/SQL заблокирован: %s", question)
            return "Извините, я не могу помогать с генерацией исполняемого кода или SQL-запросов по соображениям безопасности."

        if not self.llm:
            return self._fallback_answer(context_docs)

        prompt = self._create_prompt(question, context_docs, deep_think)
        
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, 
                self.llm.invoke,
                prompt
            )
            return response if len(response.strip()) > 10 else self._fallback_answer(context_docs)
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return self._fallback_answer(context_docs)

    def _create_prompt(self, 
                      question: str, 
                      context_docs: List[str],
                      deep_think: bool) -> str:
        """Создание промпта для модели"""
        base_prompt = f"""Ты - ассистент российского банка. Отвечай ТОЛЬКО используя информацию из контекста ниже.

КОНТЕКСТ:
{chr(10).join(context_docs)}

ВОПРОС: {question}

ПРАВИЛА:
1. Отвечай ТОЛЬКО на русском языке
2. Используй ТОЛЬКО факты из контекста выше
3. Если информации нет в контексте - скажи "Информация не найдена"
4. Будь кратким и точным
5. Не придумывай информацию
"""
        if deep_think:
            base_prompt += "\nПОКАЖИ ХОД РАССУЖДЕНИЙ:\n"
            
        base_prompt += "\nОТВЕТ:"
        return base_prompt

    def _fallback_answer(self, context_docs: List[str]) -> str:
        """Ответ при ошибке LLM"""
        if not context_docs:
            return "❌ Информация по вашему запросу не найдена в базе знаний."
        
        return "Найденная информация:\n" + "\n".join(
            [f"- {doc[:100]}..." for doc in context_docs[:3]]
        )