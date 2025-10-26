from typing import List, Dict, Any
import time

class DialogueMemory:
    """Память диалога с поддержкой временного окна"""
    
    def __init__(self, max_messages: int = 10):
        self.messages: List[Dict[str, Any]] = []
        self.max_messages = max_messages

    def add_message(self, role: str, content: str) -> None:
        """Добавление нового сообщения в память"""
        message = {
            'role': role,
            'content': content,
            'timestamp': time.time()
        }
        
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_context(self, window_minutes: int = 30) -> List[Dict[str, Any]]:
        """Получение контекста в пределах временного окна"""
        cutoff = time.time() - (window_minutes * 60)
        return [msg for msg in self.messages if msg['timestamp'] >= cutoff]

    def clear(self) -> None:
        """Очистка памяти"""
        self.messages.clear()