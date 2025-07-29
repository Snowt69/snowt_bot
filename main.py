import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties
from config import config
from database import Database
from start import start_router
from user import user_router, UserMiddleware, SubscriptionCheckMiddleware
from admin import admin_router
from developer import developer_router
from logger import setup_logging, DatabaseLogHandler
import asyncio
import signal
import sys

# Configure advanced logging
setup_logging()
logger = logging.getLogger(__name__)

async def on_startup(bot: Bot):
    """Actions on bot startup"""
    try:
        # Initialize database logger
        db = Database()
        db_log_handler = DatabaseLogHandler(db)
        db_log_handler.setLevel(logging.WARNING)
        logging.getLogger().addHandler(db_log_handler)
        
        logger.info("Bot starting up...")
        
        # Register admins and developers from config
        for admin_id in [config.ADMIN_ID] + config.DEVELOPER_IDS:
            db.add_admin(admin_id, "config_admin", 0)
            logger.info(f"Registered admin: {admin_id}")
        
        # Set bot commands
        commands = [
            types.BotCommand(command="start", description="🚀 Start the bot"),
            types.BotCommand(command="help", description="ℹ️ Get help"),
            types.BotCommand(command="admin", description="⚡ Admin panel"),
        ]
        
        await bot.set_my_commands(commands)
        logger.info("Bot commands set up")
        
    except Exception as e:
        logger.critical(f"Startup failed: {e}")
        raise

async def main():
    try:
        bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML")
        )
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Подключаем middleware в правильном порядке
        dp.update.outer_middleware(UserMiddleware())
        dp.message.middleware(SubscriptionCheckMiddleware())
        dp.callback_query.middleware(SubscriptionCheckMiddleware())
        
        dp.include_router(start_router)
        dp.include_router(admin_router)
        dp.include_router(developer_router)
        dp.include_router(user_router)
        dp.startup.register(on_startup)
        
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        sys.exit(1)