"""Скрипт запуска AI Assistant"""
import sys
import os

# Добавляем текущую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_assistant.main import main

if __name__ == "__main__":
    sys.exit(main())