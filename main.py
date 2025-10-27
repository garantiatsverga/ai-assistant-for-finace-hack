"""Entry point for AI Assistant"""
import os
import sys
from ai_assistant import SmartDeepThinkRAG
from ai_assistant.src.logging_setup import setup_logging

def clear_screen():
    """Очистка экрана"""
    os.system('clear' if os.name == 'posix' else 'cls')

def main():
    # Настраиваем логирование в файл
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    log_file = os.path.join(log_dir, 'assistant.log')
    logger = setup_logging(log_file)
    
    try:
        # Перенаправляем stdout в лог во время инициализации
        original_stdout = sys.stdout
        with open(log_file, 'a') as f:
            sys.stdout = f
            assistant = SmartDeepThinkRAG()
            sys.stdout = original_stdout
        
        clear_screen()
        print("\nAI Assistant готов к работе!")
        print("Для выхода введите 'exit' или 'quit'")
        
        while True:
            question = input("\nВаш вопрос: ").strip()
            if question.lower() in ['exit', 'quit', 'стоп']:
                break
            if not question:
                continue
                
            assistant.ask_sync(question)
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print("\nПроизошла ошибка. Подробности в логах.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())