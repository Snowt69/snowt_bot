# utils/logger.py
import logging
from logging.handlers import RotatingFileHandler
from config import config
from database import Database
import os
import traceback
from pathlib import Path

def setup_logging():
    """Настройка системы логирования"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Создаем директорию для логов если ее нет
    logs_dir = Path(config.LOGS_FILE).parent
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)  # Добавлен exist_ok для избежания ошибок
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        config.LOGS_FILE,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'  # Добавлена кодировка для корректной работы с русским текстом
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(name)s - %(levelname)s - %(message)s"
    ))
    
    # Очищаем существующие обработчики, чтобы избежать дублирования
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

class DatabaseLogHandler(logging.Handler):
    """Обработчик логов, сохраняющий записи в базу данных"""
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
    
    def emit(self, record):
        try:
            log_entry = self.format(record)
            traceback_text = None
            
            if record.exc_info:
                traceback_text = ''.join(traceback.format_exception(*record.exc_info))
            
            # Добавляем проверку на доступность базы данных
            if hasattr(self.db, 'add_log'):
                self.db.add_log(
                    level=record.levelname,
                    message=log_entry,
                    traceback=traceback_text
                )
        except Exception as e:
            # Логируем ошибку самого логгера в консоль
            print(f"Ошибка при записи лога в базу данных: {e}")
    
    def formatException(self, ei):
        """Форматирует информацию об исключении в строку"""
        return ''.join(traceback.format_exception(*ei))