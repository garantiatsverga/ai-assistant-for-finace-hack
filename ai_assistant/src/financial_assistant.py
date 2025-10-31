"""Финансовый ассистент - расширение основного ассистента"""
import logging
from typing import Dict, Any, Optional, AsyncGenerator
import asyncio
import time

from .ai_assistant import SmartDeepThinkRAG

# Пробуем импортировать парсеры
try:
    from ai_assistant.parsers.financial_parser import FinancialDataParser
    from ai_assistant.parsers.alerts_manager import PriceAlertsManager
    PARSERS_AVAILABLE = True
except ImportError as e:
    PARSERS_AVAILABLE = False
    print(f"Парсеры финансовых данных недоступны: {e}")

logger = logging.getLogger(__name__)

class FinancialAssistant(SmartDeepThinkRAG):
    """Расширенный ассистент с финансовыми данными"""
    
    def __init__(self, config_path: str = "config.json"):
        super().__init__(config_path)
        
        self.financial_parser = None
        self.alerts_manager = None
        
        if PARSERS_AVAILABLE:
            try:
                self.financial_parser = FinancialDataParser()
                self.alerts_manager = PriceAlertsManager()
                logger.info("Финансовые парсеры инициализированы")
            except Exception as e:
                logger.error(f"Ошибка инициализации парсеров: {e}")
                self.financial_parser = None
        else:
            logger.warning("Финансовые парсеры недоступны")
    
    async def ask_streaming(self, question: str) -> AsyncGenerator[str, None]:
        """ПЕРЕОПРЕДЕЛЯЕМ streaming метод для финансовых запросов"""
        start_time = time.time()
        
        # Сначала проверяем финансовые запросы
        financial_response = await self._handle_financial_question(question)
        if financial_response is not None:
            # Если это финансовый запрос, возвращаем ответ как стрим
            yield "\nОтвет: "
            yield financial_response
            yield f"\n\n⏱Время ответа: {time.time() - start_time:.2f} сек"
            return
        
        # Иначе используем базовый RAG стриминг
        async for chunk in super().ask_streaming(question):
            yield chunk
    
    async def ask(self, question: str) -> str:
        """Обработка вопросов с ПРИОРИТЕТОМ финансовых данных"""
        # Сначала проверяем финансовые запросы
        financial_response = await self._handle_financial_question(question)
        if financial_response is not None:
            return financial_response
        
        # Иначе используем базовый RAG
        return await super().ask(question)
    
    async def _handle_financial_question(self, question: str) -> Optional[str]:
        """Обработка финансовых вопросов"""
        if not self.financial_parser:
            return None  # Пусть базовый RAG обработает
        
        question_lower = question.lower()
        
        try:
            if any(word in question_lower for word in ['ставк', 'ключев', 'цб', 'центробанк', 'процент']):
                data = await self.financial_parser.get_market_summary()
                
                if 'key_rate' in data and data['key_rate'] and 'error' not in data['key_rate']:
                    rate_info = data['key_rate']
                    rate = rate_info.get('rate', 'N/A')
                    
                    response = f"Ключевая ставка ЦБ РФ: {rate}%".upper()
                    
                    # Добавляем дополнительную информацию
                    if 'date' in rate_info:
                        response += f"\nДата: {rate_info['date']}".upper()
                    if 'next_meeting' in rate_info:
                        response += f"\nСледующее заседание: {rate_info['next_meeting']}".upper()
                    if 'note' in rate_info:
                        response += f"\n{rate_info['note']}".upper()
                    
                    return response
                else:
                    return "Не удалось получить актуальные данные о ключевой ставке ЦБ"
            
            elif any(word in question_lower for word in ['акци', 'тикер', 'котировк', 'цена акци']):
                symbols = {
                    'sber': 'SBER', 'сбер': 'SBER', 'сбербанк': 'SBER',
                    'gazp': 'GAZP', 'газпром': 'GAZP', 
                    'lkoh': 'LKOH', 'лукойл': 'LKOH',
                    'vtbr': 'VTBR', 'втб': 'VTBR',
                    'rosn': 'ROSN', 'роснефть': 'ROSN'
                }
                
                symbol_found = None
                for keyword, symbol in symbols.items():
                    if keyword in question_lower:
                        symbol_found = symbol
                        break
                
                if not symbol_found:
                    symbol_found = 'SBER'  # По умолчанию
                
                data = await self.financial_parser.get_stock_price(symbol_found)
                return self._format_stock_response(data)
            
            elif any(word in question_lower for word in ['курс', 'валют', 'доллар', 'евро', 'usd', 'eur']):
                data = await self.financial_parser.get_currency_rates()
                return self._format_currency_response(data)
            
            elif any(word in question_lower for word in ['биржа', 'рынок', 'индекс', 'сводк', 'мосбирж', 'финанс']):
                data = await self.financial_parser.get_market_summary()
                return self._format_market_summary(data)
            
            elif any(word in question_lower for word in ['сбербанк', 'газпром', 'лукойл', 'втб', 'роснефть']):
                symbols = {
                    'сбербанк': 'SBER', 'газпром': 'GAZP', 'лукойл': 'LKOH',
                    'втб': 'VTBR', 'роснефть': 'ROSN'
                }
                
                for name, symbol in symbols.items():
                    if name in question_lower:
                        data = await self.financial_parser.get_stock_price(symbol)
                        return self._format_stock_response(data)
                        
        except Exception as e:
            logger.error(f"Ошибка обработки финансового запроса: {e}")
            return f"Ошибка при получении финансовых данных: {str(e)}"
        
        return None
    
    def _format_stock_response(self, data: Dict) -> str:
        """Форматирование ответа по акции"""
        if 'error' in data:
            return f"{data['error']}"
        
        change = data.get('change', 0)
        change_percent = data.get('change_percent', 0)
        change_icon = "📈" if change >= 0 else "📉"
        change_color = "+" if change >= 0 else ""
        
        response = f"""
{change_icon} **{data.get('name', data['symbol'])}** ({data['symbol']})

Цена:{data.get('last_price', 'N/A')} руб.
Изменение:{change_color}{change} ({change_color}{change_percent}%)
Объем:{self._format_number(data.get('volume', 0))}
Источник: {data.get('source', 'MOEX')}
""".upper()
        return response
    
    def _format_currency_response(self, data: Dict) -> str:
        """Форматирование ответа по валютам"""
        if 'error' in data:
            return f"{data['error']}"
        
        response = "💱 Курсы валют ЦБ РФ:\n\n".upper()
        
        main_currencies = ['USD', 'EUR', 'CNY']
        found_currencies = 0
        
        for currency in main_currencies:
            if currency in data and 'error' not in data[currency]:
                info = data[currency]
                change = info.get('change', 0)
                change_icon = "📈" if change >= 0 else "📉"
                change_color = "+" if change >= 0 else ""
                
                response += f"{change_icon} **{info['name']}:** {info['value']} руб. "
                if change != 0:
                    response += f"({change_color}{change:.2f}, {change_color}{info.get('change_percent', 0):.2f}%)\n"
                else:
                    response += "\n"
                found_currencies += 1
        
        if found_currencies == 0:
            return "Не удалось получить данные о курсах валют"
        
        return response
    
    def _format_market_summary(self, data: Dict) -> str:
        """Форматирование сводки рынка"""
        if 'error' in data:
            return f"{data['error']}"
        
        response = "Финансовая сводка:\n\n".upper()
        
        # Ключевая ставка
        if data.get('key_rate') and 'error' not in data['key_rate']:
            rate_info = data['key_rate']
            response += f"Ключевая ставка ЦБ: {rate_info.get('rate', 'N/A')}%\n\n"
        
        # Индексы
        if data.get('indices'):
            indices_data = data['indices']
            response += "ОСНОВНЫЕ ИНДЕКСЫ:\n".upper()
            
            for index_key in ['IMOEX', 'RTSI']:
                if index_key in indices_data and 'error' not in indices_data[index_key]:
                    info = indices_data[index_key]
                    change = info.get('change', 0)
                    change_icon = "📈" if change >= 0 else "📉"
                    change_color = "+" if change >= 0 else ""
                    
                    response += f"  {change_icon} {info.get('name', index_key)}: {info.get('value', 'N/A')} "
                    if change != 0:
                        response += f"({change_color}{change:.2f})\n"
                    else:
                        response += "\n"
        
        # Курсы валют
        if data.get('currencies'):
            currencies_data = data['currencies']
            if 'error' not in currencies_data:
                response += "\n💱 **Курсы валют:**\n"
                
                for currency in ['USD', 'EUR']:
                    if currency in currencies_data and 'error' not in currencies_data[currency]:
                        info = currencies_data[currency]
                        response += f"  🇺🇸 {currency}: {info.get('value', 'N/A')} руб.\n"
        
        return response
    
    def _format_number(self, number: float) -> str:
        """Форматирование больших чисел"""
        if number >= 1_000_000_000:
            return f"{number/1_000_000_000:.1f} млрд"
        elif number >= 1_000_000:
            return f"{number/1_000_000:.1f} млн"
        elif number >= 1_000:
            return f"{number/1_000:.1f} тыс"
        return str(number)
    
    async def ask_streaming_wrapper(self, question: str) -> None:
        """Обертка для стримингового вывода"""
        async for chunk in self.ask_streaming(question):
            print(chunk, end='', flush=True)
        print()
    
    async def close(self):
        """Закрытие ресурсов"""
        if self.financial_parser and hasattr(self.financial_parser, 'close'):
            await self.financial_parser.close()
        await super().close() if hasattr(super(), 'close') else None