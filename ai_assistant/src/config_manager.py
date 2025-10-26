import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigManager:
    """Менеджер конфигурации приложения"""
    
    @staticmethod
    def load_config(path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Загрузка конфигурации из JSON файла
        
        Args:
            path (str): Имя конфигурационного файла
            default (Dict[str, Any], optional): Значения по умолчанию
            
        Returns:
            Dict[str, Any]: Загруженная конфигурация
        """
        load_dotenv()
        
        # Определяем возможные пути к конфигу
        config_paths = [
            path,  # Текущая директория
            os.path.join(os.path.dirname(__file__), '..', 'config', path),  # В папке config
            os.path.join(os.path.dirname(__file__), path)  # В папке с модулем
        ]
        
        # Устанавливаем дефолтные значения
        if default is None:
            default = {
                'model': {
                    'name': 'qwen2.5:0.5b',
                    'temperature': 0.1
                },
                'rag': {
                    'top_k_documents': 3
                },
                'embedder': {
                    'model_name': 'cointegrated/rubert-tiny2'
                }
            }

        # Пробуем загрузить конфиг из всех возможных мест
        for config_path in config_paths:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Загружена конфигурация из {config_path}")
                    # Обновляем дефолтные значения загруженными
                    default.update(config)
                    return default
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.warning(f"Ошибка загрузки конфигурации {config_path}: {e}")
                continue

        logger.warning(f"Конфигурация {path} не найдена, используются значения по умолчанию")
        return default