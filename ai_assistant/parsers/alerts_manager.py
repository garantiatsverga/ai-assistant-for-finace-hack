"""Менеджер ценовых алертов"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PriceAlertsManager:
    """Менеджер ценовых алертов"""
    
    def __init__(self):
        self.alerts: Dict[str, Dict] = {}
        self.is_monitoring = False
    
    async def add_alert(self, user_id: str, symbol: str, 
                       target_price: float, condition: str) -> str:
        """Добавление алерта"""
        alert_id = f"{user_id}_{symbol}_{datetime.now().timestamp()}"
        
        self.alerts[alert_id] = {
            'user_id': user_id,
            'symbol': symbol,
            'target_price': target_price,
            'condition': condition,  # 'above', 'below', 'equals'
            'active': True,
            'created_at': datetime.now(),
            'triggered': False
        }
        
        logger.info(f"Добавлен алерт {alert_id} для {symbol}")
        return alert_id
    
    async def check_alert(self, alert_id: str, current_price: float) -> bool:
        """Проверка конкретного алерта"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        if not alert['active'] or alert['triggered']:
            return False
        
        condition_met = False
        if alert['condition'] == 'above' and current_price >= alert['target_price']:
            condition_met = True
        elif alert['condition'] == 'below' and current_price <= alert['target_price']:
            condition_met = True
        elif alert['condition'] == 'equals' and current_price == alert['target_price']:
            condition_met = True
        
        if condition_met:
            alert['triggered'] = True
            alert['triggered_at'] = datetime.now()
            alert['triggered_price'] = current_price
            logger.info(f"Алерт {alert_id} сработал!")
        
        return condition_met
    
    def get_user_alerts(self, user_id: str) -> List[Dict]:
        """Получение алертов пользователя"""
        return [
            alert for alert in self.alerts.values() 
            if alert['user_id'] == user_id
        ]
    
    def remove_alert(self, alert_id: str) -> bool:
        """Удаление алерта"""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            return True
        return False