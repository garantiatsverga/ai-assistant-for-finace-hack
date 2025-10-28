import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def debug_finance():
    print("🔍 ДИАГНОСТИКА ФИНАНСОВОГО АССИСТЕНТА")
    print("=" * 50)
    
    try:
        from ai_assistant.parsers.financial_parser import FinancialDataParser
        from ai_assistant.src.financial_assistant import FinancialAssistant
        
        print("✅ Модули импортированы успешно")
        
        # Тестируем парсер напрямую
        print("\n🧪 Тестируем парсер...")
        parser = FinancialDataParser()
        
        print("📈 Запрос ставки ЦБ...")
        summary = await parser.get_market_summary()
        print(f"Данные: {summary}")
        
        if 'key_rate' in summary:
            print(f"✅ Ставка ЦБ: {summary['key_rate']}")
        else:
            print("❌ Ставка ЦБ не найдена в данных")
        
        await parser.close()
        
        # Тестируем ассистента
        print("\n🤖 Тестируем ассистента...")
        assistant = FinancialAssistant()
        
        print("🔍 Проверяем определение запроса 'ставка ЦБ'...")
        question = "ставка ЦБ"
        response = await assistant._handle_financial_question(question)
        print(f"Ответ финансового модуля: {response}")
        
        if response is None:
            print("❌ Финансовый модуль вернул None - будет использован базовый RAG")
        else:
            print("✅ Финансовый модуль вернул ответ")
            
        await assistant.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_finance())