import subprocess
import sys
from typing import List
import logging

logger = logging.getLogger(__name__)

class DependencyManager:
    """Установка и проверка зависимостей"""
    
    @staticmethod
    def check_dependencies() -> bool:
        """Проверка установленных зависимостей"""
        required = [
            'langchain_ollama',
            'sentence_transformers',
            'numpy',
            'prometheus_client'
        ]
        
        missing = []
        for package in required:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
                
        if missing:
            logger.warning(f"Отсутствуют пакеты: {', '.join(missing)}")
            return False
        return True

    @staticmethod
    def install_dependencies() -> bool:
        """Установка недостающих зависимостей"""
        try:
            subprocess.check_call([
                sys.executable, 
                "-m", 
                "pip", 
                "install", 
                "-r", 
                "requirements.txt"
            ])
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка установки зависимостей: {e}")
            return False