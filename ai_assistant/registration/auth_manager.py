import logging
from typing import Optional, Dict, Any
from .database import DatabaseManager
from datetime import date

logger = logging.getLogger(__name__)

class AuthManager:
    """Менеджер аутентификации и регистрации"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.current_user: Optional[Dict[str, Any]] = None
    
    async def register(self,
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
            return await self.db.register_user(
                login, password, email, full_name,
                passport_series, passport_number, birth_date, phone
            )
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            return {"success": False, "error": f"Ошибка регистрации: {str(e)}"}
        
    async def login(self, identifier: str, password: str) -> Dict[str, Any]:
        """Вход пользователя в систему по логину, email или телефону"""
        user = await self.db.authenticate_user(identifier, password)
        if user:
            self.current_user = user
            logger.info(f"Пользователь {user['login']} успешно вошел в систему")
            return {"success": True, "user": user}
        else:
            return {"success": False, "error": "Неверный логин/email/телефон или пароль"}
    
    def logout(self):
        """Выход пользователя из системы"""
        if self.current_user:
            logger.info(f"Пользователь {self.current_user['login']} вышел из системы")
        self.current_user = None
    
    def is_authenticated(self) -> bool:
        """Проверка аутентификации пользователя"""
        return self.current_user is not None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Получение информации о текущем пользователе"""
        return self.current_user
    
    async def debug_login(self, login: str = "debug_user") -> Dict[str, Any]:
        """Принудительный отладочный вход без проверки пароля"""
        try:
            # Ищем пользователя в базе
            async with self.db.pool.acquire() as conn:
                user = await conn.fetchrow('''
                    SELECT id, login, email, full_name, phone,
                        passport_series, passport_number, birth_date, age,
                        is_active
                    FROM users 
                    WHERE login = $1 AND is_active = TRUE
                ''', login)
                
                if user:
                    self.current_user = {
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
                    logger.info(f"Отладочный вход: {self.current_user['login']}")
                    return {"success": True, "user": self.current_user}
                else:
                    return {"success": False, "error": "Отладочный пользователь не найден"}
                    
        except Exception as e:
            logger.error(f"Ошибка отладочного входа: {e}")
            return {"success": False, "error": f"Ошибка отладочного входа: {str(e)}"}