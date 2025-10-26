import logging
import warnings
import os
from typing import Optional
import sys
from contextlib import contextmanager

@contextmanager
def suppress_stdout():
    """Временно подавляет вывод в stdout/stderr"""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """Настройка логирования приложения"""
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.ERROR)
    root_logger.addHandler(console_handler)
    
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    
    # отключаем чрезмерно подробные логи сторонних библиотек
    logging.getLogger('transformers').setLevel(logging.ERROR)
    logging.getLogger('tokenizers').setLevel(logging.ERROR)
    logging.getLogger('torch').setLevel(logging.ERROR)
    
    return root_logger