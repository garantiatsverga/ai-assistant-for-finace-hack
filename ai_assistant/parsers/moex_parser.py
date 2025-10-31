"""Парсер Московской биржи"""
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class MOEXParser:
    """Парсер Московской биржи с защитой от блокировки"""
    
    BASE_URL = "https://iss.moex.com/iss"
    REQUEST_DELAY = 0.5
    LAST_REQUEST_TIME = 0
    
    def __init__(self):
        self.session = None
        self.logger = logging.getLogger(__name__)
    
    async def _ensure_session(self):
        """Создание сессии при необходимости"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def _rate_limit(self):
        """Ограничение частоты запросов"""
        current_time = time.time()
        time_since_last = current_time - self.LAST_REQUEST_TIME
        if time_since_last < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - time_since_last)
        self.LAST_REQUEST_TIME = time.time()
    
    async def get_stock_data(self, symbol: str) -> Dict:
        """Данные по акции с ограничением частоты"""
        await self._ensure_session()
        await self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/engines/stock/markets/shares/boards/TQBR/securities/{symbol}.json"
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_stock_response(data, symbol)
                else:
                    self.logger.error(f"MOEX API error: {response.status}")
                    return {"error": f"Акция {symbol} не найдена (статус: {response.status})"}
                    
        except asyncio.TimeoutError:
            self.logger.error(f"Таймаут при запросе {symbol}")
            return {"error": f"Таймаут при получении данных по {symbol}"}
        except Exception as e:
            self.logger.error(f"Ошибка парсинга MOEX для {symbol}: {e}")
            return {"error": f"Ошибка получения данных по {symbol}: {str(e)}"}
    
    def _parse_stock_response(self, data: Dict, symbol: str) -> Dict:
        """Парсинг ответа MOEX для акций"""
        try:
            # Получаем рыночные данные
            market_data = data.get('marketdata', {}).get('data', [])
            if not market_data:
                return {"error": f"Нет рыночных данных по акции {symbol}"}
            
            # Берем первую запись (последние данные)
            last_data = market_data[0]
            
            # Парсим поля согласно документации MOEX
            # LAST - последняя цена, CHANGE - изменение, VALUE - объем в рублях
            last_price = last_data[12] if len(last_data) > 12 else None  # LAST
            change = last_data[13] if len(last_data) > 13 else None      # CHANGE
            change_percent = last_data[14] if len(last_data) > 14 else None  # CHANGE %
            volume_rub = last_data[27] if len(last_data) > 27 else None  # VOLUME
            
            # Если данные отсутствуют, возвращаем ошибку
            if last_price is None:
                return {"error": f"Нет данных по акции {symbol}"}
            
            return {
                'symbol': symbol,
                'name': self._get_stock_name(symbol),
                'last_price': last_price,
                'change': change or 0,
                'change_percent': change_percent or 0,
                'volume': volume_rub or 0,
                'timestamp': datetime.now().isoformat(),
                'source': 'MOEX'
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга данных акции {symbol}: {e}")
            return {"error": f"Ошибка обработки данных по {symbol}: {str(e)}"}
    
    async def get_indices(self) -> Dict:
        """Основные индексы MOEX с задержками"""
        await self._ensure_session()
        
        indices = ['IMOEX', 'RTSI']
        results = {}
        
        for index in indices:
            try:
                await self._rate_limit()
                
                url = f"{self.BASE_URL}/engines/stock/markets/index/boards/SNDX/securities/{index}.json"
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        results[index] = self._parse_index_response(data, index)
                    else:
                        results[index] = {"error": f"Статус {response.status}"}
            except Exception as e:
                self.logger.error(f"Ошибка получения индекса {index}: {e}")
                results[index] = {"error": str(e)}
        
        return results
    
    def _parse_index_response(self, data: Dict, index: str) -> Dict:
        """Парсинг ответа MOEX для индексов"""
        try:
            market_data = data.get('marketdata', {}).get('data', [])
            if not market_data:
                return {"error": f"Нет данных по индексу {index}"}
            
            last_data = market_data[0]
            
            # Для индексов используем другие поля
            open_price = last_data[1] if len(last_data) > 1 else None    # OPEN
            change = last_data[4] if len(last_data) > 4 else None        # CHANGE
            change_percent = last_data[5] if len(last_data) > 5 else None  # CHANGE %
            
            return {
                'symbol': index,
                'name': self._get_index_name(index),
                'value': open_price or 0,
                'change': change or 0,
                'change_percent': change_percent or 0,
                'timestamp': datetime.now().isoformat(),
                'source': 'MOEX'
            }
        except Exception as e:
            self.logger.error(f"Ошибка парсинга индекса {index}: {e}")
            return {"error": str(e)}
    
    def _get_stock_name(self, symbol: str) -> str:
        """Названия акций"""
        names = {
            'SBER': 'Сбербанк',
            'GAZP': 'Газпром',
            'LKOH': 'Лукойл',
            'ROSN': 'Роснефть',
            'VTBR': 'ВТБ',
            'GMKN': 'Норникель',
            'NVTK': 'Новатэк',
            'TATN': 'Татнефть',
            'ALRS': 'АЛРОСА',
            'MGNT': 'Магнит',
            'YNDX': 'Яндекс',
            'TCSG': 'TCS Group'
        }
        return names.get(symbol, symbol)
    
    def _get_index_name(self, index: str) -> str:
        """Названия индексов"""
        names = {
            'IMOEX': 'Индекс Мосбиржи',
            'RTSI': 'Индекс РТС',
            'MOEXBMI': 'Индекс широкого рынка'
        }
        return names.get(index, index)
    
    async def close(self):
        """Закрытие сессии"""
        if self.session and not self.session.closed:
            await self.session.close()