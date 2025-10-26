"""Entry point for AI Assistant"""
import logging
from ai_assistant import SmartDeepThinkRAG

def main():
    logging.basicConfig(level=logging.INFO)
    assistant = SmartDeepThinkRAG()
    
    print("\nAI Assistant готов к работе!")
    print("Для выхода введите 'exit' или 'quit'")
    
    while True:
        question = input("\nВаш вопрос: ").strip()
        if question.lower() in ['exit', 'quit', 'стоп']:
            break
        if not question:
            continue
            
        print(assistant.ask_sync(question))

if __name__ == "__main__":
    main()