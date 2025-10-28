from typing import Tuple, Dict, Any, List
import json
import logging
import re

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Базовый класс для ошибок безопасности"""
    pass

class SecurityChecker:
    """Проверка безопасности запросов с поддержкой флагов"""
    
    def __init__(self, rules_path: str = "security_rules.json"):
        self.rules = self._load_rules(rules_path)
        
        # Флаги для управления поведением
        self.flags = {
            '-notrigger': 'отключить триггеры безопасности',
            '-nocode': 'отключить проверку кода',
            '-nodeep': 'отключить глубокий анализ',
            '-simple': 'простой режим ответа'
        }
        
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

    def _extract_flags(self, text: str) -> Tuple[str, List[str]]:
        """Извлечение флагов из текста запроса"""
        flags_found = []
        clean_text = text
        
        for flag in self.flags.keys():
            if flag in clean_text:
                flags_found.append(flag)
                clean_text = clean_text.replace(flag, '').strip()
        
        return clean_text, flags_found

    async def check(self, text: str) -> Tuple[bool, str]:
        """Проверка безопасности текста с поддержкой флагов"""
        # Извлекаем флаги и очищаем текст
        clean_text, flags = self._extract_flags(text)
        
        # Если флаг -notrigger активен, пропускаем все проверки
        if '-notrigger' in flags:
            logger.info("🔓 Режим -notrigger: проверки безопасности отключены")
            return True, "🔓 Режим без триггеров активирован"
        
        text_l = clean_text.lower()

        # Проверяем явные запрещённые паттерны из rules
        for pattern, action in self.rules.get('dangerous_patterns', {}).items():
            if pattern in text_l:
                # Если флаг -nocode активен и это код-запрос, пропускаем
                if '-nocode' in flags and any(code_word in pattern for code_word in ['код', 'sql', 'команду']):
                    logger.info("🔓 Режим -nocode: проверка кода отключена")
                    continue
                    
                msg = self.rules.get('rejection_messages', {}).get(
                    pattern,
                    self.rules.get('rejection_messages', {}).get('default', 'Запрос отклонен по политике безопасности.')
                )
                return False, msg

        # Дополнительно блокируем запросы, явно требующие написания исполняемого кода / SQL
        if self._code_regex.search(clean_text) and '-nocode' not in flags:
            msg = self.rules.get('rejection_messages', {}).get(
                'code',
                'Извините, я не могу генерировать программный код или инструкции для выполнения SQL-запросов.'
            )
            return False, msg

        return True, ""

    def analyze_intent(self, text: str) -> Tuple[str, float]:
        """Определение намерения в запросе с учетом флагов"""
        if not text:
            return "unknown", 0.0

        # Извлекаем флаги для чистого анализа
        clean_text, flags = self._extract_flags(text)
        
        # Если флаг -notrigger активен, используем общий интент
        if '-notrigger' in flags:
            return "general", 0.9

        # Простая логика определения интента
        if self._code_regex.search(clean_text) and '-nocode' not in flags:
            return "code", 0.95

        # Финансовые интенты
        text_l = clean_text.lower()
        if any(k in text_l for k in ["ипотек", "кредит", "вклад", "карта", "ставк"]):
            return "finance", 0.8

        return "general", 0.5

    def get_available_flags(self) -> Dict[str, str]:
        """Получение списка доступных флагов"""
        return self.flags.copy()