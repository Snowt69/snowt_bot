import os
from dotenv import load_dotenv
from typing import List, Optional
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    # Bot Settings
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8337886690:AAE1sNhCFxiuKAz5nVQd2UYFriuk8h_vUuA")
    BOT_USERNAME: Optional[str] = None  # Will be set on startup
    BOT_VERSION: str = "2.0.0"
    
    # Access Control
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", 0))
    DEVELOPER_IDS: List[int] = [int(id) for id in os.getenv("DEVELOPER_IDS", "7057452528").split(",") if id]
    
    # Database
    DB_NAME: str = os.getenv("DB_NAME", "snowt_database.db")
    DB_BACKUP_DIR: str = os.getenv("DB_BACKUP_DIR", "backups")
    DB_BACKUP_KEEP: int = int(os.getenv("DB_BACKUP_KEEP", 5))
    
    # Security
    MAX_FILE_SIZE: int = 2 * 1024 * 1024  # 2MB
    LINK_CODE_LENGTH: int = 8
    MAX_TEXT_LENGTH = 2000  # Максимальная длина текста

    # Interface Messages (Russian)
    MESSAGES = {
        "start": "👋 Привет, {first_name}!\n\nЯ бот для создания и управления ссылками.",
        "help": "ℹ️ Доступные команды:\n/start - Начать работу\n/help - Помощь",
        "admin_only": "🚫 Только для администраторов",
        "developer_only": "🚫 Только для разработчиков",
        "error": "⚠️ Произошла ошибка",
        "user_banned": "🚫 Ваш аккаунт заблокирован"
    }
    
    # Subscription
    REQUIRED_SUBSCRIPTION: List[int] = [int(id) for id in os.getenv("REQUIRED_SUBSCRIPTION", "").split(",") if id]
    SUBSCRIPTION_MESSAGE: str = "📢 Для использования бота подпишитесь на: {channels}"
    
    # Throttling
    DEFAULT_THROTTLING_RATE: float = 1.0
    THROTTLING_MESSAGE: str = "⏳ Слишком много запросов, попробуйте позже"
    
    # Logging
    LOGS_DIR: str = os.getenv("LOGS_DIR", "logs")
    LOGS_FILE: str = os.path.join(LOGS_DIR, "snowt_bot.log")
    
    # Backup messages
    BACKUP_MESSAGES = {
        "success": "✅ Резервная копия создана",
        "failed": "❌ Не удалось создать резервную копию"
    }

config = Config()