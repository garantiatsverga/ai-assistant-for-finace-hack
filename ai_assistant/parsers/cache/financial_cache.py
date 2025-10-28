"""Кэш финансовых данных"""
import time
from typing import Any, Dict
from datetime import datetime, timedelta

class FinancialDataCache:
    """Кэш для финансовых данных с TTL"""
    
    def __init__(self, ttl: int = 300):  # 5 минут по умолчанию
        self.ttl = ttl
        self._cache: Dict[str, Dict] = {}
    
    def get(self, key: str) -> Any:
        """Получение данных из кэша"""
        if key in self._cache:
            data = self._cache[key]
            if time.time() - data['timestamp'] < self.ttl:
                return data['value']
            else:
                # Удаляем просроченные данные
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Сохранение данных в кэш"""
        self._cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def clear_expired(self) -> None:
        """Очистка просроченных данных"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._cache.items()
            if current_time - data['timestamp'] >= self.ttl
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def clear_all(self) -> None:
        """Полная очистка кэша"""
        self._cache.clear()