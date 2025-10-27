import logging
from typing import Optional, Dict, Any
from .database import DatabaseManager

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
                     birth_date: str,  # строка в формате ГГГГ-ММ-ДД
                     phone: str) -> Dict[str, Any]:
        """Регистрация нового пользователя"""
        from datetime import datetime
        
        try:
            # Преобразуем дату рождения
            birth_date_obj = datetime.strptime(birth_date, '%Y-%m-%d').date()
            
            return await self.db.register_user(
                login, password, email, full_name,
                passport_series, passport_number, birth_date_obj, phone
            )
        except ValueError:
            return {"success": False, "error": "Неверный формат дата рождения. Используйте ГГГГ-ММ-ДД"}
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