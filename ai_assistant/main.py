"""Главный файл запуска AI Assistant с финансовыми данными"""
import os
import sys
import asyncio
import logging

# Добавляем корневую директорию в Python path для абсолютных импортов
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)

# Настройка логирования
def setup_logging():
    """Настройка логирования приложения"""
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('assistant.log', encoding='utf-8')
        ]
    )

    logging.getLogger('ai_assistant.src.ai_assistant').setLevel(logging.WARNING)
    logging.getLogger('ai_assistant.src.llm_adapter').setLevel(logging.WARNING)
    logging.getLogger('ai_assistant.src.embeddings_manager').setLevel(logging.WARNING)

    return logging.getLogger(__name__)

class AIAssistantApp:
    """Основное приложение AI Assistant"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.db_manager = None
        self.auth_manager = None
        self.auth_ui = None
        self.assistant = None

    async def check_ollama_availability(self) -> bool:
        """Проверка доступности Ollama"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model['name'] for model in data.get('models', [])]
                        if any('qwen' in model.lower() for model in models):
                            print("Ollama запущен, модель найдена")
                            return True
                        else:
                            print("Модель qwen не найдена в Ollama")
                            return False
                    else:
                        print("Ollama не отвечает")
                        return False
        except Exception as e:
            print(f"Ошибка подключения к Ollama: {e}")
            return False
    
    async def initialize_components(self):
        """Инициализация всех компонентов приложения"""
        try:
            # Сначала проверяем Ollama
            if not await self.check_ollama_availability():
                print("Проблема с Ollama! Проверь:")
                print("   - Запущен ли Ollama (ollama serve)")
                print("   - Загружена ли модель (ollama pull qwen2.5:0.5b)")
                return False
            
            # АБСОЛЮТНЫЕ импорты
            from ai_assistant.registration.database import DatabaseManager
            from ai_assistant.registration.auth_manager import AuthManager
            from ai_assistant.registration.auth_ui import AuthUI
            from ai_assistant.src.financial_assistant import FinancialAssistant
            
            # Инициализация базы данных
            connection_string = "postgresql://postgres@localhost:5432/bank_assistant"
            self.db_manager = DatabaseManager(connection_string)
            await self.db_manager.connect()
            self.logger.info("База данных подключена")
            
            # Инициализация аутентификации
            self.auth_manager = AuthManager(self.db_manager)
            self.auth_ui = AuthUI(self.auth_manager)
            self.logger.info("Система аутентификации инициализирована")
            
            # Инициализация ассистента
            self.assistant = FinancialAssistant()
            self.logger.info("Финансовый ассистент инициализирован")
            
            self.logger.info("Все компоненты успешно инициализированы")
            return True
            
        except ImportError as e:
            self.logger.error(f"Ошибка импорта компонентов: {e}")
            print(f"Ошибка импорта: {e}")
            print("Текущая структура проекта:")
            for root, dirs, files in os.walk(current_dir):
                level = root.replace(current_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f'{indent}{os.path.basename(root)}/')
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    if file.endswith('.py'):
                        print(f'{subindent}{file}')
            return False
        except Exception as e:
            self.logger.error(f"Ошибка инициализации: {e}")
            print(f"Ошибка инициализации: {e}")
            return False
    
    async def show_welcome_screen(self):
        """Отображение приветственного экрана"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("БАНКОВСКИЙ ИИ-АССИСТЕНТ С ФИНАНСОВЫМИ ДАННЫМИ")
        print("=" * 60)
        print("Теперь с реальными данными с бирж и ЦБ РФ!")
        print("=" * 60)
        print("1. Вход в систему")
        print("2. Регистрация")
        print("3. Выход")
        print("4. Отладочный вход (для разработки)")
        print("=" * 60)
    
    async def handle_user_choice(self, choice: str) -> bool:
        """Обработка выбора пользователя"""
        try:
            if choice == '1':  # Обычный вход
                return await self.auth_ui.handle_login()
            
            elif choice == '2':  # Регистрация
                return await self.auth_ui.handle_registration()
            
            elif choice == '3':  # Выход
                print("\nДо свидания!")
                return True
            
            elif choice == '4':  # Отладочный вход
                return await self.auth_ui.handle_debug_login()
            
            else:
                print("Неверный выбор. Попробуйте снова.")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки выбора: {e}")
            print(f"Произошла ошибка: {e}")
            return False

    async def show_welcome_screen(self):
        """Отображение приветственного экрана с отладочной опцией"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("БАНКОВСКИЙ ИИ-АССИСТЕНТ С ФИНАНСОВЫМИ ДАННЫМИ")
        print("=" * 60)
        print("Теперь с реальными данными с бирж и ЦБ РФ!")
        print("=" * 60)
        print("1. Вход в систему")
        print("2. Регистрация") 
        print("3. Выход")
        print("4. Отладочный вход (для разработки)")
        print("=" * 60)

    async def run_assistant_session(self):
        """Запуск сессии ассистента после входа"""
        print("\n" + "="*60)
        print("ЗАПУСК АССИСТЕНТА...")
        print("="*60)
        
        # Детальная диагностика состояния
        print("ДИАГНОСТИКА СЕССИИ:")
        print(f"   - Ассистент инициализирован: {'ДА' if self.assistant else 'НЕТ'}")
        print(f"   - Пользователь аутентифицирован: {'ДА' if self.auth_manager.is_authenticated() else 'НЕТ'}")
        
        if self.auth_manager.is_authenticated():
            user = self.auth_manager.get_current_user()
            print(f"   - Текущий пользователь: {user['full_name']} ({user['login']})")
        else:
            print("ОШИБКА: Пользователь не аутентифицирован!")
            print("Возврат в главное меню...")
            return
        
        if not self.assistant:
            print("ОШИБКА: Ассистент не инициализирован!")
            return
        
        print("\nДоступные команды:")
        print("   - 'exit', 'quit', 'выход' - выход из ассистента")
        print("   - '-deepthink' - углубленный анализ")
        print("="*60)
        
        # Основной цикл ассистента
        while True:
            try:
                question = input("\nВаш вопрос: ").strip()
                
                # Команды выхода
                if question.lower() in ['exit', 'quit', 'выход', 'logout']:
                    print("\nВыход из ассистента...")
                    self.auth_manager.logout()
                    print("Возврат в главное меню...")
                    break
                
                if not question:
                    continue
                
                # Обработка вопроса через ассистента
                print(f"\nОбрабатываю запрос: '{question}'")
                await self.assistant.ask_streaming_wrapper(question)
                
            except KeyboardInterrupt:
                print("\n\nСессия завершена пользователем")
                self.auth_manager.logout()
                break
            except EOFError:
                print("\nДо свидания!")
                self.auth_manager.logout()
                break
            except Exception as e:
                self.logger.error(f"Ошибка в сессии ассистента: {e}")
                print(f"Произошла ошибка: {e}")
                continue
    
    async def main_loop(self):
        """Главный цикл приложения"""
        try:
            # Инициализация
            if not await self.initialize_components():
                return
            
            # Главный цикл
            while True:
                try:
                    await self.show_welcome_screen()
                    choice = input("\nВыберите действие (1-4): ").strip()
                    
                    if choice == '3':  # Выход
                        print("\nДо свидания!")
                        break
                    
                    success = await self.handle_user_choice(choice)
                    
                    if success and choice in ['1', '4']:  # Обычный вход ИЛИ отладочный вход
                        await self.run_assistant_session()
                        
                    elif success and choice == '2':  # Регистрация
                        print("\nРегистрация успешна! Хотите войти? (да/нет)")
                        login_choice = input("Ваш выбор: ").strip().lower()
                        if login_choice in ['да', 'д', 'yes', 'y']:
                            # Предлагаем войти с только что созданными данными
                            login_success = await self.auth_ui.handle_login()
                            if login_success:
                                await self.run_assistant_session()
                            
                except KeyboardInterrupt:
                    print("\n\nРабота приложения завершена")
                    break
                except Exception as e:
                    self.logger.error(f"Ошибка в главном цикле: {e}")
                    print(f"Произошла ошибка: {e}")
                    input("\nНажмите Enter для продолжения...")
        
        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}")
            print(f"Критическая ошибка: {e}")
        finally:
            await self.cleanup()
    
    async def main_loop(self):
        """Главный цикл приложения"""
        try:
            # Инициализация
            if not await self.initialize_components():
                return
            
            # Главный цикл
            while True:
                try:
                    await self.show_welcome_screen()
                    choice = input("\nВыберите действие (1-4): ").strip()
                    
                    if choice == '3':  # Выход
                        print("\nДо свидания!")
                        break
                    
                    success = await self.handle_user_choice(choice)
                    
                    if success and choice in ['1', '4']:
                        print("ДИАГНОСТИКА: Успешный вход, запускаем ассистента...")
                        await self.run_assistant_session()
                        
                    elif success and choice == '2':  # Регистрация
                        print("\nРегистрация успешна! Хотите войти? (да/нет)")
                        login_choice = input("Ваш выбор: ").strip().lower()
                        if login_choice in ['да', 'д', 'yes', 'y']:
                            login_success = await self.auth_ui.handle_login()
                            if login_success:
                                await self.run_assistant_session()
                            
                except KeyboardInterrupt:
                    print("\n\nРабота приложения завершена")
                    break
                except Exception as e:
                    self.logger.error(f"Ошибка в главном цикле: {e}")
                    print(f"Произошла ошибка: {e}")
                    input("\nНажмите Enter для продолжения...")
        
        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}")
            print(f"Критическая ошибка: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Очистка ресурсов при завершении"""
        self.logger.info("Очистка ресурсов приложения...")
        
        try:
            # Закрываем ассистента
            if self.assistant and hasattr(self.assistant, 'close'):
                await self.assistant.close()
                self.logger.info("Ассистент закрыт")
            
            # Закрываем базу данных
            if self.db_manager:
                await self.db_manager.close()
                self.logger.info("База данных закрыта")
                
        except Exception as e:
            self.logger.error(f"Ошибка при очистке ресурсов: {e}")
        
        self.logger.info("Приложение завершено")

def main():
    """Точка входа приложения"""
    print("Запуск ИИ-ассистента для финансов...")
    
    app = AIAssistantApp()
    
    try:
        # Запускаем асинхронное приложение
        asyncio.run(app.main_loop())
    except KeyboardInterrupt:
        print("\nПриложение завершено пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)