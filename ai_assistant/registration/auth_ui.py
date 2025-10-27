import getpass
import re
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, date
from .auth_manager import AuthManager

class AuthUI:
    """Пользовательский интерфейс для аутентификации"""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth = auth_manager
    
    def clear_screen(self):
        """Очистка экрана"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def show_welcome(self):
        """Отображение приветственного экрана"""
        self.clear_screen()
        print("🎯 БАНКОВСКИЙ ИИ-АССИСТЕНТ")
        print("=" * 50)
        print("1. Вход в систему")
        print("2. Регистрация")
        print("3. Выход")
        print("=" * 50)
    
    def get_menu_choice(self) -> str:
        """Получение выбора пользователя"""
        while True:
            choice = input("\nВыберите действие (1-3): ").strip()
            if choice in ['1', '2', '3']:
                return choice
            print("❌ Неверный выбор. Попробуйте снова.")
    
    async def handle_login(self) -> bool:
        """Обработка входа в систему"""
        self.clear_screen()
        print("🔐 ВХОД В СИСТЕМУ")
        print("=" * 40)
        print("Можно использовать: логин, email или номер телефона")
        print("=" * 40)
        
        identifier = input("Логин/Email/Телефон: ").strip()
        password = getpass.getpass("Пароль: ")
        
        if not identifier or not password:
            print("\n❌ Все поля обязательны для заполнения!")
            input("\nНажмите Enter для продолжения...")
            return False
        
        result = await self.auth.login(identifier, password)
        
        if result["success"]:
            user = result["user"]
            print(f"\n✅ Добро пожаловать, {user['full_name']}!")
            print(f"👤 Логин: {user['login']}")
            print(f"📧 Email: {user['email']}")
            print(f"📱 Телефон: {user['phone']}")
            input("\nНажмите Enter для продолжения...")
            return True
        else:
            print(f"\n❌ {result['error']}")
            input("\nНажмите Enter для продолжения...")
            return False
    
    async def handle_registration(self) -> bool:
        """Обработка регистрации"""
        self.clear_screen()
        print("📝 РЕГИСТРАЦИЯ")
        print("=" * 40)
        
        try:
            # Собираем данные
            user_data = {}
            
            user_data['login'] = self._get_valid_login()
            if not user_data['login']:
                return False
            
            user_data['password'] = self._get_valid_password()
            if not user_data['password']:
                return False
            
            user_data['email'] = self._get_valid_email()
            if not user_data['email']:
                return False
            
            user_data['full_name'] = self._get_valid_full_name()
            if not user_data['full_name']:
                return False
            
            user_data['passport_series'], user_data['passport_number'] = self._get_valid_passport()
            if not user_data['passport_series']:
                return False
            
            user_data['birth_date'] = self._get_valid_birth_date()
            if not user_data['birth_date']:
                return False
            
            user_data['phone'] = self._get_valid_phone()
            if not user_data['phone']:
                return False
            
            # Подтверждение данных
            if not self._confirm_registration(user_data):
                return False
            
            # Регистрация
            result = await self.auth.register(**user_data)
            
            if result["success"]:
                print(f"\n✅ {result['message']}")
                print("Теперь вы можете войти в систему.")
                input("\nНажмите Enter для продолжения...")
                return True
            else:
                print(f"\n❌ {result['error']}")
                input("\nНажмите Enter для продолжения...")
                return False
                
        except KeyboardInterrupt:
            print("\n\n❌ Регистрация прервана пользователем.")
            return False
    
    def _get_valid_login(self) -> str:
        """Получение валидного логина"""
        while True:
            login = input("Логин (3-50 символов, только латиница/цифры/_): ").strip()
            if 3 <= len(login) <= 50:
                if re.match(r'^[a-zA-Z0-9_]+$', login):
                    return login
                else:
                    print("❌ Логин может содержать только латинские буквы, цифры и подчеркивание")
            else:
                print("❌ Логин должен содержать от 3 до 50 символов")
    
    def _get_valid_password(self) -> str:
        """Получение пароля с звездочками через stdiomask"""
        try:
            import stdiomask
            
            while True:
                password = stdiomask.getpass("Пароль (минимум 6 символов): ", mask='*')
                
                if len(password) < 6:
                    print("❌ Пароль должен содержать минимум 6 символов.")
                    continue
                
                confirm = stdiomask.getpass("Подтвердите пароль: ", mask='*')
                
                if password == confirm:
                    return password
                else:
                    print("❌ Пароли не совпадают.")
                    
        except ImportError:
            # Fallback на обычный getpass
            import getpass
            print("⚠️  Установите 'pip install stdiomask' для отображения звездочек")
            password = getpass.getpass("Пароль (минимум 6 символов): ")
            confirm = getpass.getpass("Подтвердите пароль: ")
            return password if password == confirm else ""

    def _get_valid_email(self) -> str:
        """Получение валидного email"""
        while True:
            email = input("Email: ").strip().lower()
            if '@' in email and len(email) <= 100:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if re.match(email_pattern, email):
                    return email
                else:
                    print("❌ Введите корректный email адрес")
            else:
                print("❌ Введите корректный email адрес")
    
    def _get_valid_full_name(self) -> str:
        """Получение валидного ФИО"""
        while True:
            full_name = input("ФИО (например, Иванов Иван Иванович): ").strip()
            if 2 <= len(full_name) <= 200 and len(full_name.split()) >= 2:
                return full_name
            print("❌ Введите корректное ФИО (минимум 2 слова, до 200 символов).")
    
    def _get_valid_passport(self) -> Tuple[str, str]:
        """Получение валидных данных паспорта"""
        while True:
            passport_series = input("Серия паспорта (4 цифры): ").strip()
            passport_number = input("Номер паспорта (6 цифр): ").strip()
            
            if (passport_series.isdigit() and len(passport_series) == 4 and
                passport_number.isdigit() and len(passport_number) == 6):
                return passport_series, passport_number
            print("❌ Введите корректные данные паспорта (4 цифры серии + 6 цифр номера).")
    
    def _get_valid_birth_date(self) -> str:
        """Получение валидной даты рождения"""
        while True:
            birth_date = input("Дата рождения (ГГГГ-ММ-ДД): ").strip()
            try:
                birth_date_obj = datetime.strptime(birth_date, '%Y-%m-%d').date()
                today = date.today()
                
                if birth_date_obj > today:
                    print("❌ Дата рождения не может быть в будущем.")
                    continue
                
                # Вычисляем возраст
                age = today.year - birth_date_obj.year
                if today.month < birth_date_obj.month or (today.month == birth_date_obj.month and today.day < birth_date_obj.day):
                    age -= 1
                
                if age < 18:
                    print("❌ Регистрация доступна только с 18 лет")
                    continue
                
                if age > 120:
                    print("❌ Проверьте корректность даты рождения")
                    continue
                
                print(f"✅ Возраст: {age} лет")
                return birth_date
                
            except ValueError:
                print("❌ Введите дату в формате ГГГГ-ММ-ДД.")
    
    def _get_valid_phone(self) -> str:
        """Получение валидного номера телефона"""
        while True:
            phone = input("Номер телефона (10-11 цифр): ").strip()
            # Убираем все нецифровые символы
            phone_clean = re.sub(r'\D', '', phone)
            if len(phone_clean) in [10, 11]:
                return phone_clean
            print("❌ Введите корректный номер телефона (10-11 цифр).")
    
    def _confirm_registration(self, user_data: Dict[str, Any]) -> bool:
        """Подтверждение данных регистрации"""
        self.clear_screen()
        print("📋 ПОДТВЕРЖДЕНИЕ РЕГИСТРАЦИИ")
        print("=" * 50)
        print(f"👤 ФИО: {user_data['full_name']}")
        print(f"🔑 Логин: {user_data['login']}")
        print(f"📧 Email: {user_data['email']}")
        print(f"📱 Телефон: +7{user_data['phone']}")
        print(f"📇 Паспорт: {user_data['passport_series']} {user_data['passport_number']}")
        print(f"🎂 Дата рождения: {user_data['birth_date']}")
        
        # Вычисляем возраст для подтверждения
        birth_date_obj = datetime.strptime(user_data['birth_date'], '%Y-%m-%d').date()
        today = date.today()
        age = today.year - birth_date_obj.year
        if today.month < birth_date_obj.month or (today.month == birth_date_obj.month and today.day < birth_date_obj.day):
            age -= 1
        print(f"📅 Возраст: {age} лет")
        print("=" * 50)
        
        confirm = input("\nПодтвердить регистрацию? (да/нет): ").strip().lower()
        return confirm in ['да', 'д', 'yes', 'y']