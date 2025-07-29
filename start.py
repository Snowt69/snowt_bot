# handlers/start.py
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database
from config import config
import logging
from typing import List, Dict, Any

router = Router()
db = Database()
logger = logging.getLogger(__name__)

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

@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    
    # Повторная проверка подписки
    required_channels = db.get_all_subscription_channels()
    not_subscribed = []
    
    for channel in required_channels:
        try:
            chat_member = await bot.get_chat_member(
                chat_id=channel['channel_id'],
                user_id=callback.from_user.id
            )
            if chat_member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            continue
            
    if not_subscribed:
        channels_text = "\n".join(
            f"- {channel['title']} (@{channel.get('username', 'нет')})"
            for channel in not_subscribed
        )
        await callback.message.edit_text(
            f"❌ Вы не подписаны на все каналы:\n\n{channels_text}",
            reply_markup=get_subscription_check_keyboard(not_subscribed)
        )
    else:
        await callback.message.edit_text(
            "✅ Спасибо за подписку! Теперь вы можете пользоваться ботом."
        )
        # Отправляем приветственное сообщение
        await send_welcome_message(callback.message, callback.from_user)

@router.message(CommandStart())
async def handle_start(message: Message, bot: Bot):
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    
    # Register user
    db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    # Проверяем подписку только если есть обязательные каналы
    required_channels = db.get_all_subscription_channels()
    if required_channels:
        not_subscribed = []
        
        for channel in required_channels:
            try:
                chat_member = await bot.get_chat_member(
                    chat_id=channel['channel_id'],
                    user_id=message.from_user.id
                )
                if chat_member.status in ['left', 'kicked']:
                    not_subscribed.append(channel)
            except Exception as e:
                logger.error(f"Error checking subscription: {e}")
                continue
                
        if not_subscribed:
            channels_text = "\n".join(
                f"- {channel['title']} (@{channel.get('username', 'нет')})"
                for channel in not_subscribed
            )
            await message.answer(
                f"📢 Для использования бота подпишитесь на следующие каналы:\n\n{channels_text}",
                reply_markup=get_subscription_check_keyboard(not_subscribed)
            )
            return
    
    # Если подписка проверена или не требуется
    await process_start_command(message, args)

async def process_start_command(message: Message, args: str = None):
    """Обработка команды /start после проверки подписки"""
    if args:
        # Handle link code
        link = db.get_link(args)
        if link:
            db.increment_link_visits(args)
            db.increment_link_visits(message.from_user.id)
            
            if link['content_type'] == 'text':
                await message.answer(link['content_text'])
            elif link['content_type'] == 'photo':
                await message.answer_photo(link['content_file_id'], caption=link.get('content_text'))
            elif link['content_type'] == 'document':
                await message.answer_document(link['content_file_id'], caption=link.get('content_text'))
            return
    
    # Отправляем приветственное сообщение
    await send_welcome_message(message, message.from_user)

async def send_welcome_message(message: Message, user: types.User):
    """Отправляет приветственное сообщение"""
    is_admin = db.is_admin(user.id)
    welcome_text = f"👋 Привет, {user.first_name}!\n\n"
    welcome_text += "Я бот, который выдает скрипты по ссылке, ищет скрипты, а также обходит ссылки\n\n"
    welcome_text += "Почему я лучший?\n"
    welcome_text += "• Актуальные скрипты — база обновляется постоянно!\n"
    welcome_text += "• Собственный каталог — все скрипты с канала в одном каталоге!\n"
    welcome_text += "• Поиск скриптов — напиши команду и получи много скриптов на свой запрос!\n"
    welcome_text += "• Обход ссылок — бот умеет обходить ссылки, например linkvertise, loot-link, lootlabs, lootdest и другие!\n\n"
    welcome_text += "Для полного ознакомления с функционалом бота, напиши /help"
    
    if is_admin:
        welcome_text += "\n\n⚡ Вы администратор этого бота!"
    
    await message.answer(welcome_text)

start_router = router