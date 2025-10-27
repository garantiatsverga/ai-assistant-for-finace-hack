from typing import Tuple, Dict, Any
import json
import logging
import re

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Базовый класс для ошибок безопасности"""
    pass

class SecurityChecker:
    """Проверка безопасности запросов"""
    def __init__(self, rules_path: str = "security_rules.json"):
        self.rules = self._load_rules(rules_path)
        # предкомпилируем шаблоны для быстрого поиска опасных интентов
        self._code_patterns = [
            r'\bsql\b', r'\bselect\b', r'\binsert\b', r'\bupdate\b', r'\bdelete\b',
            r'\bdrop\b', r'\bcreate table\b', r'\bexecute\b', r'\beval\b', r'\bexec\b',
            r'написать код', r'сгенерируй sql', r'запрос sql', r'выполнить sql', r'как выполнить sql'
        ]
        self._code_regex = re.compile("|".join(self._code_patterns), flags=re.IGNORECASE)

    def _load_rules(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Ошибка загрузки правил безопасности: {e}")
            return {}

    async def check(self, text: str) -> Tuple[bool, str]:
        """Проверка безопасности текста"""
        text_l = text.lower()

        # Проверяем явные запрещённые паттерны из rules
        for pattern, action in self.rules.get('dangerous_patterns', {}).items():
            if pattern in text_l:
                msg = self.rules.get('rejection_messages', {}).get(
                    pattern,
                    self.rules.get('rejection_messages', {}).get('default', 'Запрос отклонен по политике безопасности.')
                )
                return False, msg

        # Дополнительно блокируем запросы, явно требующие написания исполняемого кода / SQL
        if self._code_regex.search(text):
            msg = self.rules.get('rejection_messages', {}).get(
                'code',
                'Извините, я не могу генерировать программный код или инструкции для выполнения SQL-запросов.'
            )
            return False, msg

        return True, ""

    def analyze_intent(self, text: str) -> Tuple[str, float]:
        """Определение намерения в запросе. Возвращает (intent, confidence)"""
        if not text:
            return "unknown", 0.0

        # Простая логика определения интента: если присутствуют паттерны кода — intent=code
        if self._code_regex.search(text):
            return "code", 0.95

        # можно расширять: ключевые слова для финансирования, ипотека, карта и т.д.
        text_l = text.lower()
        if any(k in text_l for k in ["ипотек", "кредит", "вклад", "карта", "ставк"]):
            return "finance", 0.8

        return "general", 0.5