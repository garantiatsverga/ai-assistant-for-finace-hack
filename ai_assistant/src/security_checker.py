from typing import Tuple, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Базовый класс для ошибок безопасности"""
    pass

class SecurityChecker:
    """Проверка безопасности запросов"""
    def __init__(self, rules_path: str = "security_rules.json"):
        self.rules = self._load_rules(rules_path)
        
    def _load_rules(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Ошибка загрузки правил безопасности: {e}")
            return {}
            
    async def check(self, text: str) -> Tuple[bool, str]:
        """Проверка безопасности текста"""
        text = text.lower()
        
        # Проверяем паттерны
        for pattern, action in self.rules.get('dangerous_patterns', {}).items():
            if pattern in text:
                msg = self.rules.get('rejection_messages', {}).get(
                    pattern, 
                    self.rules.get('rejection_messages', {}).get('default', 'Запрос отклонен.')
                )
                return False, msg
                
        return True, ""
        
    def analyze_intent(self, text: str) -> Tuple[str, float]:
        """Определение намерения в запросе"""
        # TODO: Реализовать определение интента
        return "general", 1.0