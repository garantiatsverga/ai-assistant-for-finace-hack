import asyncpg
import logging
from typing import Optional, Dict, Any
import hashlib
import secrets
from datetime import datetime, date
import re

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных PostgreSQL для аутентификации"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Подключение к базе данных и создание таблиц"""
        try:
            self.pool = await asyncpg.create_pool(self.connection_string)
            await self._create_tables()
            logger.info("Подключение к PostgreSQL установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            raise
    
    async def _create_tables(self):
        """Создание необходимых таблиц"""
        async with self.pool.acquire() as conn:
            # Таблица пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    login VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    salt VARCHAR(32) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    full_name VARCHAR(200) NOT NULL,
                    passport_series VARCHAR(4) NOT NULL,
                    passport_number VARCHAR(6) NOT NULL,
                    birth_date DATE NOT NULL,
                    age INTEGER NOT NULL,
                    phone VARCHAR(20) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Индексы для быстрого поиска
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_login ON users(login)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)')
    
    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Хеширование пароля с солью"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
    
    @staticmethod
    def _generate_salt() -> str:
        """Генерация соли для пароля"""
        return secrets.token_hex(16)
    
    @staticmethod
    def _calculate_age(birth_date: date) -> int:
        """Вычисление возраста по дате рождения"""
        today = date.today()
        age = today.year - birth_date.year
        
        # Проверяем, был ли уже день рождения в этом году
        if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
            age -= 1
            
        return age
    
    async def register_user(self, 
                          login: str,
                          password: str,
                          email: str,
                          full_name: str,
                          passport_series: str,
                          passport_number: str,
                          birth_date: date,
                          phone: str) -> Dict[str, Any]:
        """Регистрация нового пользователя"""
        try:
            # Валидация данных
            validation_result = self._validate_registration_data(
                login, password, email, full_name, passport_series, passport_number, birth_date, phone
            )
            
            if not validation_result["success"]:
                return validation_result
            
            # Проверяем уникальность логина, email и телефона
            if await self._check_user_exists(login=login):
                return {"success": False, "error": "Пользователь с таким логином уже существует"}
            
            if await self._check_user_exists(email=email):
                return {"success": False, "error": "Пользователь с таким email уже существует"}
            
            if await self._check_user_exists(phone=phone):
                return {"success": False, "error": "Пользователь с таким номером телефона уже существует"}
            
            # Вычисляем возраст
            age = self._calculate_age(birth_date)
            
            # Хешируем пароль
            salt = self._generate_salt()
            password_hash = self._hash_password(password, salt)
            
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users 
                    (login, password_hash, salt, email, full_name, passport_series, 
                     passport_number, birth_date, age, phone)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ''', login, password_hash, salt, email, full_name, 
                   passport_series, passport_number, birth_date, age, phone)
                
            logger.info(f"Пользователь {login} успешно зарегистрирован")
            return {"success": True, "message": "Регистрация успешно завершена"}
            
        except asyncpg.UniqueViolationError as e:
            logger.warning(f"Нарушение уникальности при регистрации: {e}")
            return {"success": False, "error": "Пользователь с такими данными уже существует"}
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя: {e}")
            return {"success": False, "error": f"Ошибка регистрации: {str(e)}"}
    
    async def _check_user_exists(self, login: str = None, email: str = None, phone: str = None) -> bool:
        """Проверка существования пользователя"""
        try:
            async with self.pool.acquire() as conn:
                if login:
                    user = await conn.fetchrow('SELECT id FROM users WHERE login = $1', login)
                    return user is not None
                elif email:
                    user = await conn.fetchrow('SELECT id FROM users WHERE email = $1', email)
                    return user is not None
                elif phone:
                    user = await conn.fetchrow('SELECT id FROM users WHERE phone = $1', phone)
                    return user is not None
                return False
        except Exception as e:
            logger.error(f"Ошибка проверки пользователя: {e}")
            return False
    
    async def authenticate_user(self, identifier: str, password: str) -> Optional[Dict[str, Any]]:
        """Аутентификация пользователя по логину, email или телефону"""
        try:
            async with self.pool.acquire() as conn:
                # Ищем пользователя по логину, email или телефону
                user = await conn.fetchrow('''
                    SELECT id, login, password_hash, salt, email, full_name, phone,
                           passport_series, passport_number, birth_date, age,
                           is_active
                    FROM users 
                    WHERE (login = $1 OR email = $1 OR phone = $1) AND is_active = TRUE
                ''', identifier)
                
                if not user:
                    return None
                
                # Проверяем пароль
                password_hash = self._hash_password(password, user['salt'])
                if password_hash != user['password_hash']:
                    return None
                
                # Обновляем время последнего входа
                await conn.execute(
                    'UPDATE users SET last_login = $1 WHERE id = $2',
                    datetime.now(), user['id']
                )
                
                return {
                    'id': user['id'],
                    'login': user['login'],
                    'email': user['email'],
                    'full_name': user['full_name'],
                    'phone': user['phone'],
                    'passport_series': user['passport_series'],
                    'passport_number': user['passport_number'],
                    'birth_date': user['birth_date'],
                    'age': user['age'],
                    'is_active': user['is_active']
                }
                
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            return None
    
    def _validate_registration_data(self,
                                login: str,
                                password: str,
                                email: str,
                                full_name: str,
                                passport_series: str,
                                passport_number: str,
                                birth_date: date,
                                phone: str) -> Dict[str, Any]:
        
        # Проверка логина
        if len(login) < 3 or len(login) > 50:
            return {"success": False, "error": "Логин должен содержать от 3 до 50 символов"}
        
        if not re.match(r'^[a-zA-Z0-9_]+$', login):
            return {"success": False, "error": "Логин может содержать только латинские буквы, цифры и подчеркивание"}
        
        # Проверка пароля
        if len(password) < 6:
            return {"success": False, "error": "Пароль должен содержать минимум 6 символов"}
        
        # Проверка email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return {"success": False, "error": "Введите корректный email адрес"}
        
        # Проверка ФИО
        if len(full_name) < 2 or len(full_name) > 200:
            return {"success": False, "error": "ФИО должно содержать от 2 до 200 символов"}
        
        if len(full_name.split()) < 2:
            return {"success": False, "error": "Введите фамилию и имя (минимум 2 слова)"}
        
        # Проверка серии паспорта
        if not passport_series.isdigit() or len(passport_series) != 4:
            return {"success": False, "error": "Серия паспорта должна состоять из 4 цифр"}
        
        # Проверка номера паспорта
        if not passport_number.isdigit() or len(passport_number) != 6:
            return {"success": False, "error": "Номер паспорта должен состоять из 6 цифр"}
        
        # Проверка даты рождения
        if birth_date > date.today():  # 🎯 Работаем с date объектом
            return {"success": False, "error": "Дата рождения не может быть в будущем"}
        
        age = self._calculate_age(birth_date)  # 🎯 Передаем date объект
        if age < 18:
            return {"success": False, "error": "Регистрация доступна только с 18 лет"}
        if age > 120:
            return {"success": False, "error": "Проверьте корректность даты рождения"}
        
        # Проверка телефона
        phone_clean = re.sub(r'\D', '', phone)
        if len(phone_clean) not in [10, 11]:
            return {"success": False, "error": "Введите корректный номер телефона (10-11 цифр)"}
        
        return {"success": True}
    
    async def close(self):
        """Закрытие соединения с базой данных"""
        if self.pool:
            await self.pool.close()