from aiogram import Router, types, F, Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Callable, Dict, Awaitable, Any, List
from database import Database
from config import config
import logging

# Создаем роутер
router = Router()
db = Database()
logger = logging.getLogger(__name__)

# Middleware для отслеживания пользователей
class UserMiddleware(BaseMiddleware):
    """Middleware для отслеживания пользователей и их активности"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем все, что не является сообщением
        if not isinstance(event, Message):
            return await handler(event, data)

        user = event.from_user
        
        try:
            # Регистрируем/обновляем пользователя
            db.add_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Обновляем время последней активности
            db.update_user_activity(user.id)
            
            logger.debug(f"User activity updated: {user.id} (@{user.username})")
            
        except Exception as e:
            logger.error(f"User tracking error: {e}", exc_info=True)
            
        return await handler(event, data)

# Состояния для репортов
class ReportStates(StatesGroup):
    waiting_for_report = State()

def get_subscription_check_keyboard(channels: List[Dict[str, Any]]) -> types.InlineKeyboardMarkup:
    """Создает клавиатуру для проверки подписки"""
    builder = InlineKeyboardBuilder()
    
    for channel in channels:
        username = channel.get('username')
        if username:
            builder.button(
                text=f"📢 {channel['title']}", 
                url=f"https://t.me/{username}"
            )
    
    builder.button(
        text="✅ Я подписался",
        callback_data="check_subscription"
    )
    
    builder.adjust(1)
    return builder.as_markup()

class SubscriptionCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем служебные обновления
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)
            
        # Получаем user_id в зависимости от типа события
        user_id = event.from_user.id
        
        # Пропускаем команду /start и проверку подписки
        if (isinstance(event, Message) and event.text and event.text.startswith('/start')) or \
           (isinstance(event, CallbackQuery) and event.data == 'check_subscription'):
            return await handler(event, data)
            
        # Получаем список обязательных каналов
        required_channels = db.get_all_subscription_channels()
        if not required_channels:
            return await handler(event, data)
            
        # Проверяем подписку на каждый канал
        bot = data.get('bot')
        not_subscribed = []
        
        for channel in required_channels:
            try:
                chat_member = await bot.get_chat_member(
                    chat_id=channel['channel_id'],
                    user_id=user_id
                )
                if chat_member.status in ['left', 'kicked']:
                    not_subscribed.append(channel)
            except Exception as e:
                logger.error(f"Error checking subscription for channel {channel['channel_id']}: {e}")
                continue
                
        if not_subscribed:
            # Отправляем сообщение с просьбой подписаться
            channels_text = "\n".join(
                f"- {channel['title']} (@{channel.get('username', 'нет')})"
                for channel in not_subscribed
            )
            
            if isinstance(event, Message):
                await event.answer(
                    f"📢 Для использования бота подпишитесь на следующие каналы:\n\n{channels_text}",
                    reply_markup=get_subscription_check_keyboard(not_subscribed)
                )
            elif isinstance(event, CallbackQuery):
                await event.message.edit_text(
                    f"📢 Для использования бота подпишитесь на следующие каналы:\n\n{channels_text}",
                    reply_markup=get_subscription_check_keyboard(not_subscribed)
                )
            return
            
        return await handler(event, data)

# Остальные обработчики (help, profile, report и т.д.)
@router.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer("""
    Весь функционал бота:
    • /start — запустить бота
    • /help — показать это сообщение
    • /profile — показать статистику
    • /report — отправить жалобу
    • /catalog — открыть каталог скриптов
    
    Для админов:
    • /admin — открыть админ-панель""")

@router.message(Command("profile"))
async def profile_handler(message: types.Message):
    user = db.get_user(message.from_user.id)
    
    if user:
        text = (
            f"📊 Ваша статистика:\n\n"
            f"👤 Имя: {user['first_name']}\n"
            f"🆔 ID: {user['user_id']}\n"
            f"📅 Регистрация: {user['join_date']}\n"
            f"🔗 Переходов: {user['link_visits']}"
        )
        await message.answer(text)
    else:
        await message.answer("❌ Профиль не найден")

@router.message(Command("report"))
async def report_handler(message: types.Message, state: FSMContext):
    await state.set_state(ReportStates.waiting_for_report)
    await message.answer(
        "📝 Отправьте вашу жалобу одним сообщением.\n"
        "Администратор рассмотрит её в ближайшее время.\n\n"
        "Чтобы отменить отправку, напишите /cancel"
    )

@router.message(ReportStates.waiting_for_report, F.text)
async def process_report(message: types.Message, state: FSMContext):
    report_text = message.text
    user_id = message.from_user.id
    
    # Сохраняем репорт в базу данных
    report_id = db.create_report(user_id, report_text)
    
    # Отправляем уведомление админам
    admins = db.get_all_admins()
    for admin in admins:
        try:
            await message.bot.send_message(
                chat_id=admin['user_id'],
                text=f"📢 Новый репорт #{report_id}\n"
                     f"От: @{message.from_user.username or 'нет'} (ID: {user_id})\n"
                     f"Сообщение: {report_text[:200]}..."
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу {admin['user_id']}: {e}")
    
    await message.answer(f"✅ Ваш репорт #{report_id} принят! Спасибо за обратную связь.")
    await state.clear()

@router.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer("❌ Действие отменено")

user_router = router