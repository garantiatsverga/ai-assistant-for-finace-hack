from typing import Dict, Any
from prometheus_client import Counter, Histogram
import time

class MetricsCollector:
    """Сбор метрик работы ассистента"""
    def __init__(self):
        # Prometheus метрики
        self.request_counter = Counter(
            'assistant_requests_total', 
            'Общее количество запросов'
        )
        self.response_time = Histogram(
            'assistant_response_seconds', 
            'Время ответа'
        )
        
        # Локальные метрики
        self._local = {
            'total_queries': 0,
            'successful_responses': 0,
            'total_time': 0.0,
            'intent_distribution': {}
        }
    
    def log_query(self, question: str, intent: str, 
                 response_time: float, success: bool = True) -> None:
        """Логирование метрик запроса"""
        try:
            self.request_counter.inc()
            self.response_time.observe(response_time)
        except Exception:
            pass
            
        self._local['total_queries'] += 1
        if success:
            self._local['successful_responses'] += 1
        self._local['total_time'] += response_time
        self._local['intent_distribution'][intent] = \
            self._local['intent_distribution'].get(intent, 0) + 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение текущих метрик"""
        avg_time = (self._local['total_time'] / self._local['total_queries']) \
            if self._local['total_queries'] else 0.0
            
        return {
            'total_queries': self._local['total_queries'],
            'successful_responses': self._local['successful_responses'],
            'avg_response_time': avg_time,
            'intent_distribution': self._local['intent_distribution']
        }