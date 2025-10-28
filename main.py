"""Entry point for AI Assistant"""
import os
import sys
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)

# Добавляем текущую директорию в Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from ai_assistant import SmartDeepThinkRAG
    from ai_assistant.registration.auth_manager import AuthManager
    from ai_assistant.registration.auth_ui import AuthUI
    from ai_assistant.registration.database import DatabaseManager
    from ai_assistant.src.logging_setup import setup_logging
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("📁 Текущая директория:", current_dir)
    print("📁 Содержимое текущей директории:")
    for item in os.listdir(current_dir):
        print(f"   - {item}")
    
    if os.path.exists('src'):
        print("📁 Содержимое src/:")
        for item in os.listdir('src'):
            print(f"   - {item}")
    
    if os.path.exists('registration'):
        print("📁 Содержимое registration/:")
        for item in os.listdir('registration'):
            print(f"   - {item}")
    
    sys.exit(1)

class AIAssistantApp:
    """Основное приложение AI Assistant с аутентификацией"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.db_manager = None
        self.auth_manager = None
        self.auth_ui = None
        self.assistant = None
    
    async def initialize(self):
        """Инициализация приложения"""
        try:
            # Инициализация базы данных
            connection_string = self._get_connection_string()
            self.db_manager = DatabaseManager(connection_string)
            await self.db_manager.connect()
            
            # Инициализация менеджеров
            self.auth_manager = AuthManager(self.db_manager)
            self.auth_ui = AuthUI(self.auth_manager)
            
            self.logger.info("Приложение инициализировано")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации: {e}")
            print(f"❌ Ошибка инициализации: {e}")
            print("🔧 Проверьте настройки PostgreSQL")
            raise
    
    def _get_connection_string(self) -> str:
        """Получение строки подключения к PostgreSQL в Docker"""
        return "postgresql://postgres@localhost:5432/bank_assistant"

    async def run(self):
        """Запуск основного цикла приложения"""
        try:
            await self.initialize()
            
            while True:
                try:
                    self.auth_ui.show_welcome()
                    choice = self.auth_ui.get_menu_choice()
                    
                    if choice == '1':  # Вход
                        if await self.auth_ui.handle_login():
                            await self._run_assistant()
                    
                    elif choice == '2':  # Регистрация
                        await self.auth_ui.handle_registration()
                    
                    elif choice == '3':  # Выход
                        print("\n👋 До свидания!")
                        break
                        
                except (KeyboardInterrupt, EOFError):
                    print("\n👋 Работа завершена пользователем")
                    break
                    
        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}")
            print(f"\n💥 Критическая ошибка: {e}")
        finally:
            if self.db_manager:
                await self.db_manager.close()

    async def _run_assistant(self):
        """Запуск ассистента с синхронным вводом в executor"""
        if not self.assistant:
            self.assistant = SmartDeepThinkRAG()
        
        user = self.auth_manager.get_current_user()
        self._show_assistant_welcome(user)
        
        import asyncio
        
        while True:
            try:
                # Запускаем input в thread executor чтобы не блокировать event loop
                loop = asyncio.get_event_loop()
                question = await loop.run_in_executor(
                    None, input, "\n💬 Ваш вопрос: "
                )
                question = question.strip()
                
                if not question:
                    continue
                    
                if question.lower() in ['exit', 'quit', 'выход', 'logout']:
                    self.auth_manager.logout()
                    print("👋 До свидания!")
                    break
                    
                await self.assistant.ask_streaming_wrapper(question)
                
            except KeyboardInterrupt:
                print("\n👋 До свидания!")
                self.auth_manager.logout()
                break
            except EOFError:
                print("\n👋 До свидания!")
                self.auth_manager.logout()
                break

    def _show_assistant_welcome(self, user: dict):
        """Отображение приветствия ассистента"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
        print(f"🎯 Добро пожаловать, {user['full_name']}!")
        print(f"👤 Вы вошли как: {user['login']}")
        print("🤖 AI Assistant готов к работе!")
        print("💡 Для углубленного анализа добавьте '-deepthink' к вопросу")
        print("🚪 Для выхода введите 'exit', 'quit' или 'выход'")
        print("=" * 60)

def main():
    """Точка входа приложения"""
    app = AIAssistantApp()
    
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\n👋 Работа завершена")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())