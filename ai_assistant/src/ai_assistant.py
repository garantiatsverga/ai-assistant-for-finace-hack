"""Основной модуль ИИ-ассистента"""
from typing import List, Optional, Dict, Any, AsyncGenerator
import asyncio
import logging
import os
import time

# Импорты из той же папки
from .cache_manager import EmbeddingCache
from .config_manager import ConfigManager
from .security_checker import SecurityChecker
from .metrics_collector import MetricsCollector
from .dialogue_memory import DialogueMemory
from .llm_adapter import LLMAdapter, LLMError
from .embeddings_manager import EmbeddingsManager
from .stock_analyzer import StockAnalyzer

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
                timeout=self.config.get('model', {}).get('timeout', 120)
            )
            self.security = SecurityChecker()
            self.metrics = MetricsCollector()
            self.memory = DialogueMemory()

            async def initialize_qdrant(self):
                """Инициализация Qdrant"""
                if self.config.get('qdrant', {}).get('enabled', True):
                    qdrant_status = await self.embedding_manager.get_qdrant_status()
                    logger.info(f"Статус Qdrant: {qdrant_status}")
            
            # Инициализация анализатора акций
            self.stock_analyzer = StockAnalyzer()
            
            # Загрузка базы знаний и предварительные вычисления
            self.documents = self._load_knowledge_base()
            self.doc_embeddings = self.embedding_manager.precompute_embeddings(
                self.documents, 
                self.embedding_cache
            )

            # Вызываем Qdrant
            asyncio.create_task(self.initialize_qdrant())
            
            logger.info(f"Система инициализирована. Документов в базе: {len(self.documents)}")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации ассистента: {e}")
            raise AssistantInitializationError(f"Не удалось инициализировать ассистент: {e}")

    async def initialize_qdrant(self):
        """Инициализация Qdrant"""
        if self.config.get('qdrant', {}).get('enabled', True):
            qdrant_status = await self.embedding_manager.get_qdrant_status()
            logger.info(f"Статус Qdrant: {qdrant_status}")

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
        """Асинхронный метод с улучшенным DeepThink и аналитикой акций"""
        start_time = time.time()
        
        try:
            # Извлекаем флаги и определяем режимы
            clean_question, flags = self.security._extract_flags(question)
            deepthink_mode = question.endswith(" -deepthink") and '-nodeep' not in flags
            
            if deepthink_mode:
                clean_question = clean_question[:-10].strip()
                yield "АКТИВИРОВАН РЕЖИМ DEEPTHINK\n"
                yield "=" * 50 + "\n"
            
            # Проверка безопасности
            is_safe, reason = await self.security.check(question)
            if not is_safe:
                if deepthink_mode:
                    yield f"АНАЛИЗ БЕЗОПАСНОСТИ: {reason}\n"
                    yield "Запрос отклонен по политике безопасности\n"
                    yield "=" * 50 + "\n"
                else:
                    yield reason
                return
            
            # Получаем информацию для ответа
            question_embedding = await self.embedding_manager.get_embedding(clean_question)
            similar_docs = await self.embedding_manager.find_similar(
                clean_question, question_embedding, self.doc_embeddings, self.documents, top_k=3
            )
            
            # Анализ акций (если применимо)
            investment_analysis = None
            question_lower = clean_question.lower()
            
            if any(word in question_lower for word in ['акции', 'инвестиц', 'вложить', 'куда вложить', 'портфель', 'выгодн']):
                market_data = await self._get_real_market_data()
                
                # Анализ конкретной акции
                for symbol in ['GAZP', 'SBER', 'LKOH', 'YNDX', 'ROSN', 'VTBR']:
                    if symbol.lower() in question_lower:
                        investment_analysis = await self.stock_analyzer.analyze_single_stock(symbol, market_data)
                        break
                
                # Общий инвестиционный анализ
                if not investment_analysis:
                    investment_analysis = await self.stock_analyzer.analyze_investment_query(clean_question, market_data)
            
            # DeepThink анализ
            if deepthink_mode:
                yield await self._generate_deepthink_analysis(clean_question, similar_docs, investment_analysis)
            
            # Показываем финансовый анализ (если есть)
            if investment_analysis and 'error' not in investment_analysis:
                yield "\nФИНАНСОВЫЙ АНАЛИЗ:\n"
                if 'strategy_name' in investment_analysis:
                    strategy = investment_analysis
                    yield f"{strategy['strategy_name'].upper()} СТРАТЕГИЯ\n"
                    yield f"{strategy['strategy_description']}\n"
                    yield f"Распределение: {strategy['recommended_allocation']}\n\n"
                    
                    yield "РЕКОМЕНДУЕМЫЕ АКЦИИ:\n"
                    for stock in strategy['stocks']:
                        yield f"• {stock['name']} ({stock['symbol']}) - {stock['price']} руб.\n"
                        yield f"  Риск: {stock['risk']} | Дивиденды: {stock['dividend_yield']}\n"
                        description = stock.get('description', '')
                        if description:
                            yield f"  📊 {description}\n"
                        yield "\n"
                else:
                    # Анализ одной акции
                    stock = investment_analysis
                    yield f"{stock['name']} ({stock['symbol']})\n"
                    yield f"Текущая цена: {stock['current_price']} руб.\n"
                    yield f"Динамика: {stock['change']:+.2f} ({stock['change_percent']:+.2f}%)\n"
                    yield f"Тренд: {stock['trend']}\n"
                    yield f"Уровень риска: {stock['risk']}\n"
                    yield f"Дивидендная доходность: {stock['dividend_yield']}\n"
                    yield f"Рекомендация: {stock['recommendation']}\n\n"
            
            # Основной ответ
            if deepthink_mode:
                yield "ОСНОВНОЙ ОТВЕТ:\n"
            elif '-simple' in flags:
                yield "[ПРОСТОЙ РЕЖИМ] "
            else:
                yield "Ответ: "
            
            # Генерация ответа от LLM с проверкой релевантности
            full_response = ""
            relevant_chunks = []
            
            async for chunk in self.llm.generate_answer_streaming(clean_question, similar_docs, deepthink_mode, flags):
                # Проверяем релевантность чанка
                if self._is_relevant_chunk(chunk, clean_question):
                    relevant_chunks.append(chunk)
                    yield chunk
                full_response += chunk
            
            # Если ответ нерелевантен - даем запаcной вариант
            if not self._is_response_relevant(full_response, clean_question) and investment_analysis:
                yield "\n\nНа основе анализа рекомендую:\n"
                if 'stocks' in investment_analysis:
                    for stock in investment_analysis['stocks'][:3]:
                        yield f"• {stock['name']} - {stock.get('price', 'N/A')} руб. ({stock.get('risk', 'N/A')} риск)\n"
                elif 'current_price' in investment_analysis:
                    stock = investment_analysis
                    yield f"• {stock['name']} - {stock.get('current_price', 'N/A')} руб. ({stock.get('risk', 'N/A')} риск)\n"
            
            # Добавляем в память и выводим время
            self.memory.add_message('user', clean_question)
            self.memory.add_message('assistant', full_response)
            
            response_time = time.time() - start_time
            yield f"\n\n⏱Время ответа: {response_time:.2f} сек"
            
        except Exception as e:
            logger.error(f"Критическая ошибка в ask_streaming: {e}", exc_info=True)
            yield f"Произошла ошибка: {e}"

    async def _generate_deepthink_analysis(self, question: str, similar_docs: List[str], investment_analysis: Any) -> str:
        """Генерация анализа для DeepThink режима"""
        analysis = []
        
        # Анализ намерения
        question_lower = question.lower()
        if any(word in question_lower for word in ['что такое', 'определ']):
            intent = "ПОЛУЧИТЬ ОПРЕДЕЛЕНИЕ"
        elif any(word in question_lower for word in ['как', 'процесс']):
            intent = "УЗНАТЬ ПРОЦЕСС"
        elif any(word in question_lower for word in ['документ', 'нужно']):
            intent = "УЗНАТЬ ДОКУМЕНТЫ" 
        elif any(word in question_lower for word in ['ставк', 'стоимость']):
            intent = "УЗНАТЬ СТОИМОСТЬ"
        elif any(word in question_lower for word in ['акции', 'инвестиц', 'вложить']):
            intent = "ИНВЕСТИЦИОННЫЙ ЗАПРОС"
        else:
            intent = "ℹОБЩИЙ ЗАПРОС"
        
        analysis.append(f"АНАЛИЗ НАМЕРЕНИЯ: {intent}")
        analysis.append(f"ОРИГИНАЛЬНЫЙ ВОПРОС: '{question}'")
        analysis.append(f"НАЙДЕНО ДОКУМЕНТОВ: {len(similar_docs)}")
        
        if similar_docs:
            analysis.append("РЕЛЕВАНТНАЯ ИНФОРМАЦИЯ:")
            for i, doc in enumerate(similar_docs[:2], 1):
                preview = doc[:100] + "..." if len(doc) > 100 else doc
                analysis.append(f"   {i}. {preview}")
        
        if investment_analysis and 'error' not in investment_analysis:
            analysis.append("ДОСТУПНЫ ДАННЫЕ РЫНКА:")
        
        analysis.append("СООТВЕТСТВИЕ БЕЗОПАСНОСТИ: Проверено")
        analysis.append("=" * 50)
        analysis.append("")
        
        return "\n".join(analysis)

    async def _get_real_market_data(self) -> Dict[str, Any]:
        """Получение реальных рыночных данных для анализа"""
        try:
            # Используем существующие парсеры для получения реальных данных
            from ..parsers.financial_parser import FinancialDataParser
            
            parser = FinancialDataParser()
            market_data = {}
            
            # Получаем данные по основным акциям
            symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'ROSN', 'VTBR']
            
            for symbol in symbols:
                try:
                    stock_data = await parser.get_stock_price(symbol)
                    if 'error' not in stock_data:
                        market_data[symbol] = {
                            'last_price': stock_data.get('last_price'),
                            'change': stock_data.get('change', 0),
                            'change_percent': stock_data.get('change_percent', 0),
                            'volume': stock_data.get('volume', 0)
                        }
                except Exception as e:
                    logger.warning(f"Не удалось получить данные по {symbol}: {e}")
                    # Используем заглушку если API не доступно
                    market_data[symbol] = await self._get_fallback_data(symbol)
            
            await parser.close()
            return market_data
            
        except Exception as e:
            logger.error(f"Ошибка получения рыночных данных: {e}")
            return await self._get_fallback_data()
        

    def _is_relevant_chunk(self, chunk: str, question: str) -> bool:
        """Проверка релевантности чанка вопросу"""
        question_lower = question.lower()
        chunk_lower = chunk.lower()
        
        # Если вопрос про акции, а ответ про ипотеку - нерелевантно
        if any(word in question_lower for word in ['акции', 'инвестиц', 'вложить']):
            if any(word in chunk_lower for word in ['ипотек', 'кредит на недвижимость', 'вклад']):
                return False
        
        return True

    def _is_response_relevant(self, response: str, question: str) -> bool:
        """Проверка релевантности всего ответа"""
        question_lower = question.lower()
        response_lower = response.lower()
        
        relevant_keywords = []
        if any(word in question_lower for word in ['акции', 'инвестиц']):
            relevant_keywords = ['акци', 'сбер', 'газпром', 'лукойл', 'яндекс', 'дивидент', 'портфель', 'инвест']
        
        return any(keyword in response_lower for keyword in relevant_keywords)

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
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.ask(question), loop)
                return future.result()
            else:
                return loop.run_until_complete(self.ask(question))
        except RuntimeError:
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
        
        print("\nИИ-ассистент готов к работе!")
        print("Для углубленного анализа добавьте '-deepthink' к вопросу")
        print("Для выхода введите 'exit', 'quit' или 'стоп'")
        
        while True:
            question = input("\nВаш вопрос: ").strip()
            if question.lower() in ['exit', 'quit', 'стоп']:
                print("До свидания!")
                break
            if not question:
                continue
                
            assistant.ask_sync(question)
            
    except AssistantInitializationError as e:
        print(f"Ошибка инициализации: {e}")
        print("Проверьте настройки и зависимости")
    except KeyboardInterrupt:
        print("\nРабота завершена пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")