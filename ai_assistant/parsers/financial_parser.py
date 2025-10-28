"""Главный парсер финансовых данных"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
import logging

from .moex_parser import MOEXParser
from .cbr_parser import CBRParser
from .cache.financial_cache import FinancialDataCache

logger = logging.getLogger(__name__)

class FinancialDataParser:
    """Универсальный парсер финансовых данных с управлением ресурсами"""
    
    def __init__(self, cache_ttl: int = 300):
        self.sources = {
            'moex': MOEXParser(),
            'cbr': CBRParser()
        }
        self.cache = FinancialDataCache(ttl=cache_ttl)
        self.logger = logging.getLogger(__name__)
    
    async def get_stock_price(self, symbol: str) -> Dict:
        """Получение цены акции"""
        cache_key = f"stock_{symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            data = await self.sources['moex'].get_stock_data(symbol)
            self.cache.set(cache_key, data)
            return data
        except Exception as e:
            self.logger.error(f"Ошибка получения цены акции {symbol}: {e}")
            return {"error": f"Не удалось получить данные по {symbol}"}
    
    async def get_currency_rates(self) -> Dict:
        """Курсы валют"""
        cache_key = "currency_rates"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            data = await self.sources['cbr'].get_currency_rates()
            self.cache.set(cache_key, data)
            return data
        except Exception as e:
            self.logger.error(f"Ошибка получения курсов валют: {e}")
            return {"error": "Не удалось получить курсы валют"}
    
    async def get_market_summary(self) -> Dict:
        """Сводка по рынку"""
        cache_key = "market_summary"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            tasks = [
                self.sources['moex'].get_indices(),
                self.sources['cbr'].get_currency_rates(),
                self.sources['cbr'].get_key_rate()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            summary = {
                'indices': results[0] if not isinstance(results[0], Exception) else {},
                'currencies': results[1] if not isinstance(results[1], Exception) else {},
                'key_rate': results[2] if not isinstance(results[2], Exception) else {},
                'timestamp': datetime.now().isoformat()
            }
            
            self.cache.set(cache_key, summary)
            return summary
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки рынка: {e}")
            return {"error": "Не удалось получить сводку рынка"}
    
    async def get_multiple_stocks(self, symbols: List[str]) -> Dict:
        """Данные по нескольким акциям"""
        tasks = [self.get_stock_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        return {
            symbol: result for symbol, result in zip(symbols, results)
        }
    
    async def close(self):
        """Закрытие всех сессий парсеров"""
        self.logger.info("Закрытие сессий парсеров...")
        close_tasks = []
        
        for name, parser in self.sources.items():
            if hasattr(parser, 'close'):
                close_tasks.append(parser.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.logger.info("Все сессии парсеров закрыты")