# admin.py
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InputFile, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from database import Database
from config import config
import logging
import os
from datetime import datetime
import random
import string
import time
from typing import Optional
from user import router as user_router

router = Router()
db = Database()
logger = logging.getLogger(__name__)

# Состояния
class LinkCreation(StatesGroup):
    waiting_for_content = State()
    waiting_for_custom_id = State()
    waiting_for_new_id = State()

class AdminActions(StatesGroup):
    waiting_for_admin = State()
    waiting_for_ban_reason = State()
    waiting_for_report_answer = State()
    waiting_for_user_search = State()
    waiting_for_ad_message = State()

class ChannelActions(StatesGroup):
    waiting_for_channel = State()
    waiting_for_check_type = State()

# Классы состояний
class LinkActions(StatesGroup):
    waiting_for_link_search = State()
    waiting_for_link_edit = State()

class BroadcastActions(StatesGroup):
    waiting_for_photo = State()
    waiting_for_text = State()

class ReportSettings(StatesGroup):
    waiting_for_auto_close = State()
    waiting_for_notify = State()

class UserSettings(StatesGroup):
    waiting_for_setting = State()
    waiting_for_link_limit = State()
    waiting_for_report_limit = State()
    waiting_for_cooldown = State()

class LinkSettings(StatesGroup):
    waiting_for_length = State()
    waiting_for_size = State()

# Вспомогательные функции
def generate_link_code(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def is_admin(user_id: int, username: str = None) -> bool:
    if user_id == config.ADMIN_ID:
        return True
    if username and username.lower() == "snowt_tg":
        return True
    return db.is_admin(user_id)

def format_date(date_str: Optional[str]) -> str:
    if not date_str:
        return "не указана"
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
    except:
        return date_str

def get_notification_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Репорты", callback_data="admin_reports")
    return kb.as_markup()

# Клавиатуры
def get_admin_panel_keyboard(user_id: int):
    kb = InlineKeyboardBuilder()
    
    buttons = [
        ("📊 Статистика", "admin_stats"),
        ("🔗 Ссылки", "admin_links"),
        ("👨‍💻 Админы", "admin_admins"),
        ("📝 Репорты", "admin_reports"),
        ("👥 Пользователи", "admin_users"),
        ("📢 Реклама", "admin_advertise"),
        ("📩 Рассылка", "admin_broadcast"),
        ("⚙️ Настройки", "admin_settings")
    ]
    
    for text, data in buttons:
        kb.button(text=text, callback_data=data)
    
    if is_developer(user_id):
        kb.button(text="💻 Панель разработчика", callback_data="developer_panel")
    
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ <b>Настройки бота</b>\n\n"
        "Выберите раздел для настройки:",
        reply_markup=InlineKeyboardBuilder()
            .button(text="📝 Репорты", callback_data="reports_settings")
            .button(text="🔗 Ссылки", callback_data="links_settings")
            .button(text="👥 Пользователи", callback_data="users_settings")
            .button(text="◀️ Назад", callback_data="admin_panel")
            .adjust(1)
            .as_markup()
    )
    await callback.answer()

def is_developer(user_id: int) -> bool:
    return user_id in config.DEVELOPER_IDS or user_id == config.ADMIN_ID

def get_back_keyboard(back_to: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data=back_to)
    return kb.as_markup()

def get_stats_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data="admin_stats")
    kb.button(text="📊 Подробнее", callback_data="detailed_stats")
    kb.button(text="◀️ Назад", callback_data="admin_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_links_management_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Список ссылок", callback_data="links_list_1")
    kb.button(text="🔍 Поиск ссылки", callback_data="search_link")
    kb.button(text="➕ Создать ссылку", callback_data="create_link_menu")
    kb.button(text="◀️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def get_link_detail_keyboard(link_code: str, page: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить ID", callback_data=f"edit_link_id_{link_code}_{page}")
    kb.button(text="📝 Изменить контент", callback_data=f"edit_link_content_{link_code}_{page}")
    kb.button(text="🗑️ Удалить", callback_data=f"ask_delete_link_{link_code}_{page}")
    kb.button(text="📋 В список", callback_data=f"links_list_{page}")
    kb.adjust(2)
    return kb.as_markup()

@router.callback_query(F.data.startswith("edit_link_content_"))
async def edit_link_content(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    link_code = parts[3]
    page = parts[4]
    
    await state.set_state(LinkCreation.waiting_for_content)
    await state.update_data({
        'edit_mode': True,
        'link_code': link_code,
        'page': page
    })
    
    await callback.message.edit_text(
        "📝 <b>Изменение содержимого ссылки</b>\n\n"
        "Отправьте новое содержимое (текст, фото или файл до 2МБ):",
        reply_markup=get_back_keyboard(f"link_detail_{link_code}_{page}")
    )
    await callback.answer()

def get_confirmation_keyboard(action: str, item_id: str, back_to: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"confirm_{action}_{item_id}")
    kb.button(text="❌ Отмена", callback_data=back_to)
    return kb.as_markup()

def get_report_notification_keyboard(report_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✉️ Ответить", callback_data=f"answer_report_{report_id}_1_open")
    kb.button(text="🗑️ Удалить", callback_data=f"ask_delete_report_{report_id}_1_open")
    kb.button(text="🚫 Забанить", callback_data=f"ask_ban_from_report_{report_id}_1_open")
    kb.button(text="📝 Репорты", callback_data="admin_reports")
    kb.adjust(2)
    return kb.as_markup()

def get_admins_list_keyboard(page: int, total_pages: int):
    kb = InlineKeyboardBuilder()
    if page > 1:
        kb.button(text="⬅️ Назад", callback_data=f"admins_list_{page-1}")
    if page < total_pages:
        kb.button(text="Вперед ➡️", callback_data=f"admins_list_{page+1}")
    kb.button(text="◀️ В меню", callback_data="admin_admins")
    kb.adjust(2)
    return kb.as_markup()

def get_report_detail_keyboard(report_id: int, page: int, status: str):
    kb = InlineKeyboardBuilder()
    if status == 'open':
        kb.button(text="✉️ Ответить", callback_data=f"answer_report_{report_id}_{page}_{status}")
    kb.button(text="🗑️ Удалить", callback_data=f"ask_delete_report_{report_id}_{page}_{status}")
    kb.button(text="🚫 Забанить", callback_data=f"ask_ban_from_report_{report_id}_{page}_{status}")
    kb.button(text="📋 В список", callback_data=f"reports_list_{status}_{page}")
    kb.adjust(2)
    return kb.as_markup()

def get_admins_management_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Список админов", callback_data="admins_list_1")
    kb.button(text="➕ Добавить админа", callback_data="add_admin")
    kb.button(text="◀️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def get_reports_management_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Открытые репорты", callback_data="reports_list_open_1")
    kb.button(text="📋 Закрытые репорты", callback_data="reports_list_closed_1")
    kb.button(text="⚙️ Настройки", callback_data="reports_settings")
    kb.button(text="◀️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

@router.callback_query(F.data == "reports_settings")
async def reports_settings(callback: CallbackQuery):
    try:
        settings = db.get_report_settings()
        text = "⚙️ <b>Настройки репортов</b>\n\n"
        text += f"🔔 Уведомления: {'ВКЛ' if settings['notifications'] else 'ВЫКЛ'}\n"
        text += f"⏱ Автозакрытие: {'ВКЛ' if settings['auto_close'] else 'ВЫКЛ'}"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardBuilder()
                .button(text="🔔 Уведомления", callback_data="toggle_notify")
                .button(text="⏱ Автозакрытие", callback_data="toggle_auto_close")
                .button(text="◀️ Назад", callback_data="admin_reports")
                .adjust(1)
                .as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка в настройках репортов: {e}")
        await callback.answer("❌ Ошибка загрузки настроек", show_alert=True)

def get_users_management_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Поиск пользователя", callback_data="search_user")
    kb.button(text="🚫 Список забаненных", callback_data="banned_users_1")
    kb.button(text="📊 Топ активных", callback_data="top_active_users")
    kb.button(text="◀️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

@router.callback_query(F.data == "top_active_users")
async def top_active_users(callback: CallbackQuery):
    users = db.get_top_active_users(limit=10)
    text = "🏆 <b>Топ активных пользователей</b>\n\n"
    
    for i, user in enumerate(users, 1):
        text += f"{i}. {user['first_name']} (@{user.get('username', 'нет')}) - {user['activity_count']} действий\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("admin_users")
    )

def get_advertise_management_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Список каналов", callback_data="channels_list_1")
    kb.button(text="➕ Добавить канал", callback_data="add_channel")
    kb.button(text="📢 Проверить подписки", callback_data="check_subscriptions")
    kb.button(text="◀️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def get_broadcast_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📢 Текстовая рассылка", callback_data="text_broadcast")
    kb.button(text="🖼️ Рассылка с фото", callback_data="photo_broadcast")
    kb.button(text="📊 Статистика рассылок", callback_data="broadcast_stats")
    kb.button(text="◀️ Назад", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

@router.callback_query(F.data == "broadcast_stats")
async def broadcast_stats(callback: CallbackQuery):
    stats = db.get_broadcast_stats()
    text = "📈 <b>Статистика рассылок</b>\n\n"
    text += f"Всего рассылок: {stats['total']}\n"
    text += f"Успешных: {stats['success']}\n"
    text += f"Неудачных: {stats['failed']}\n"
    text += f"Последняя: {format_date(stats['last_date'])}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard("admin_broadcast")
    )

@router.callback_query(F.data == "photo_broadcast")
async def photo_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastActions.waiting_for_photo)
    await callback.message.edit_text(
        "🖼️ <b>Рассылка с фото</b>\n\nОтправьте фото с подписью:",
        reply_markup=get_back_keyboard("admin_broadcast")
    )

# Основные обработчики
@router.message(Command("admin"))
async def admin_panel(message: Message):
    user = message.from_user
    
    if not is_admin(user.id, user.username):
        await message.answer("🚫 У вас нет доступа к админ-панели!")
        return
    
    await message.answer(
        "⚡ <b>Админ-панель</b> ⚡\n\n"
        "Выберите раздел для управления ботом:",
        reply_markup=get_admin_panel_keyboard(user.id)
    )

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id, callback.from_user.username):
        await callback.answer("🚫 У вас нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚡ <b>Админ-панель</b> ⚡\n\n"
        "Выберите раздел для управления ботом:",
        reply_markup=get_admin_panel_keyboard(callback.from_user.id)
    )
    await callback.answer()

# Статистика
@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    # Получаем свежие данные статистики
    stats = db.get_user_stats()
    
    # Добавляем проверки на существование ключей
    text = "📊 <b>Статистика бота:</b>\n\n"
    text += f"👥 <b>Пользователей всего:</b> {stats.get('total_users', 0)}\n"
    text += f"🟢 <b>Активных:</b> {stats.get('active_users', 0)}\n"
    text += f"🔴 <b>Заблокированных:</b> {stats.get('banned_users', 0)}\n\n"
    text += f"🔗 <b>Ссылок:</b> {stats.get('total_links', 0)}\n"
    text += f"🖱️ <b>Переходов:</b> {stats.get('total_link_visits', 0)}\n\n"
    text += f"📝 <b>Отчетов:</b> {stats.get('total_reports', 0)}\n"
    text += f"📩 <b>Открытых:</b> {stats.get('open_reports', 0)}\n"
    text += f"📨 <b>Закрытых:</b> {stats.get('closed_reports', 0)}\n\n"
    text += f"📢 <b>Каналов:</b> {stats.get('subscription_channels', 0)}"
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_stats_keyboard()
        )
    except:
        await callback.message.answer(
            text,
            reply_markup=get_stats_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "detailed_stats")
async def detailed_stats(callback: CallbackQuery):
    try:
        stats = db.get_detailed_stats()
        
        text = "📊 <b>Подробная статистика</b>\n\n"
        text += f"👥 <b>Новые пользователи:</b>\n"
        text += f"├ За 24ч: {stats['new_users_24h']}\n"
        text += f"└ За 7д: {stats['new_users_7d']}\n\n"
        text += f"🟢 <b>Активные пользователи:</b>\n"
        text += f"├ За 24ч: {stats['active_24h']}\n"
        text += f"└ За 7д: {stats['active_7d']}\n\n"
        text += f"🔗 <b>Новые ссылки:</b>\n"
        text += f"├ За 24ч: {stats['new_links_24h']}\n"
        text += f"└ За 7д: {stats['new_links_7d']}\n\n"
        text += f"🖱️ <b>Переходы по ссылкам:</b>\n"
        text += f"├ За 24ч: {stats['visits_24h']}\n"
        text += f"└ За 7д: {stats['visits_7d']}"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardBuilder()
                .button(text="◀️ Назад", callback_data="admin_stats")
                .as_markup()
        )
    except Exception as e:
        logger.error(f"Error showing detailed stats: {e}")
        await callback.answer("❌ Ошибка при получении статистики", show_alert=True)

# Управление ссылками
@router.callback_query(F.data == "admin_links")
async def admin_links(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔗 <b>Управление ссылками</b>\n\n"
        "Выберите действие:",
        reply_markup=get_links_management_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("links_list_"))
async def links_list(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    per_page = 5
    links = db.get_all_links(page=page, per_page=per_page)
    total_links = db.count_links()
    total_pages = (total_links + per_page - 1) // per_page
    
    text = f"📋 <b>Список ссылок</b> (страница {page}/{total_pages})\n\n"
    
    kb = InlineKeyboardBuilder()
    
    for link in links:
        kb.button(
            text=f"{link['link_code']} ({link['content_type']}, 👁️ {link['visits']})",
            callback_data=f"link_detail_{link['link_code']}_{page}"
        )
    
    if page > 1:
        kb.button(text="⬅️ Назад", callback_data=f"links_list_{page-1}")
    if page < total_pages:
        kb.button(text="Вперед ➡️", callback_data=f"links_list_{page+1}")
    kb.button(text="➕ Создать", callback_data="create_link_menu")
    kb.button(text="🔍 Поиск", callback_data="search_link")
    kb.button(text="◀️ В меню", callback_data="admin_links")
    
    kb.adjust(1, *[1 for _ in links], 2, 2)
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("link_detail_"))
async def link_detail(callback: CallbackQuery):
    parts = callback.data.split("_")
    link_code = parts[2]
    page = parts[3]
    
    link = db.get_link(link_code)
    if not link:
        await callback.answer("❌ Ссылка не найдена!")
        return
    
    bot_info = await callback.bot.get_me()
    creator = db.get_user(link['created_by'])
    creator_name = f"@{creator['username']}" if creator and creator.get('username') else f"ID: {link['created_by']}"
    
    text = f"🔗 <b>Детали ссылки</b>\n\n"
    text += f"🆔 <b>Код:</b> {link['link_code']}\n"
    text += f"🔗 <b>Ссылка:</b> t.me/{bot_info.username}?start={link['link_code']}\n"
    text += f"📌 <b>Тип:</b> {link['content_type']}\n"
    text += f"📅 <b>Создана:</b> {format_date(link['creation_date'])}\n"
    text += f"👤 <b>Автор:</b> {creator_name}\n"
    text += f"👁️ <b>Переходов:</b> {link['visits']}\n"
    if link['content_text']:
        text += f"\n📝 <b>Текст:</b>\n{link['content_text'][:200]}..."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_link_detail_keyboard(link_code, page)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("ask_delete_link_"))
async def ask_delete_link(callback: CallbackQuery):
    parts = callback.data.split("_")
    link_code = parts[3]
    page = parts[4]
    
    link = db.get_link(link_code)
    if not link:
        await callback.answer("❌ Ссылка не найдена!")
        return
    
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы уверены, что хотите удалить ссылку?\n\n"
        f"🆔 <b>Код:</b> {link['link_code']}\n"
        f"📌 <b>Тип:</b> {link['content_type']}\n"
        f"👁️ <b>Переходов:</b> {link['visits']}",
        reply_markup=get_confirmation_keyboard(
            "delete_link", 
            f"{link_code}_{page}", 
            f"link_detail_{link_code}_{page}"
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_link_"))
async def confirm_delete_link(callback: CallbackQuery):
    parts = callback.data.split("_")
    link_code = parts[3]
    page = parts[4]
    
    if db.delete_link(link_code):
        await callback.answer("✅ Ссылка успешно удалена!", show_alert=True)
        await callback.message.edit_text(
            "✅ <b>Ссылка успешно удалена!</b>",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📋 К списку ссылок", callback_data=f"links_list_{page}")
                .button(text="◀️ В меню", callback_data="admin_links")
                .as_markup()
        )
    else:
        await callback.answer("❌ Ошибка при удалении ссылки!", show_alert=True)

@router.callback_query(F.data.startswith("edit_link_id_"))
async def edit_link_id(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    link_code = parts[3]
    page = parts[4]
    
    await state.set_state(LinkCreation.waiting_for_new_id)
    await state.update_data({
        'old_link_code': link_code,
        'page': page
    })
    
    await callback.message.edit_text(
        f"✏️ <b>Изменение ID ссылки</b>\n\n"
        f"Текущий ID: <code>{link_code}</code>\n\n"
        "Введите новый ID (от 3 до 20 символов, только буквы и цифры):",
        reply_markup=get_back_keyboard(f"link_detail_{link_code}_{page}")
    )
    await callback.answer()

@router.message(LinkCreation.waiting_for_new_id)
async def process_new_link_id(message: Message, state: FSMContext):
    data = await state.get_data()
    old_link_code = data['old_link_code']
    page = data['page']
    new_link_code = message.text.strip()
    
    if not (3 <= len(new_link_code) <= 20) or not new_link_code.isalnum():
        await message.answer("❌ ID должен содержать от 3 до 20 буквенно-цифровых символов!")
        return
    
    if db.get_link(new_link_code):
        await message.answer("❌ Этот ID уже занят, выберите другой")
        return
    
    if db.update_link_code(old_link_code, new_link_code):
        bot_info = await message.bot.get_me()
        await message.answer(
            f"✅ <b>ID ссылки изменён</b>\n\n"
            f"Старый ID: <code>{old_link_code}</code>\n"
            f"Новый ID: <code>{new_link_code}</code>\n\n"
            f"Новая ссылка: t.me/{bot_info.username}?start={new_link_code}",
            reply_markup=InlineKeyboardBuilder()
                .button(text="🔗 К деталям ссылки", callback_data=f"link_detail_{new_link_code}_{page}")
                .as_markup()
        )
    else:
        await message.answer("❌ Ошибка при изменении ID ссылки")
    
    await state.clear()

@router.callback_query(F.data == "create_link_menu")
async def create_link_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔗 <b>Создание ссылки</b>\n\n"
        "Выберите тип создания:",
        reply_markup=InlineKeyboardBuilder()
            .button(text="🔄 Авто ID", callback_data="create_link_auto")
            .button(text="✏️ Кастомный ID", callback_data="create_link_custom")
            .button(text="◀️ Назад", callback_data="admin_links")
            .adjust(2)
            .as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "create_link_auto")
async def create_link_auto(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LinkCreation.waiting_for_content)
    await state.update_data(link_type="auto")
    await callback.message.edit_text(
        "📝 <b>Создание ссылки (авто ID)</b>\n\n"
        "Отправьте содержимое для ссылки (текст, фото или файл до 2МБ):",
        reply_markup=get_back_keyboard("create_link_menu")
    )
    await callback.answer()

@router.callback_query(F.data == "create_link_custom")
async def create_link_custom(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LinkCreation.waiting_for_content)
    await state.update_data(link_type="custom")
    await callback.message.edit_text(
        "📝 <b>Создание ссылки (кастомный ID)</b>\n\n"
        "Отправьте содержимое для ссылки (текст, фото или файл до 2МБ):",
        reply_markup=get_back_keyboard("create_link_menu")
    )
    await callback.answer()

@router.message(
    F.content_type.in_({'text', 'photo', 'document'}),
    LinkCreation.waiting_for_content
)
async def process_link_content(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id, message.from_user.username):
        await state.clear()
        return
    
    content_type = message.content_type
    content_text = message.caption if content_type != 'text' else message.text
    content_file_id = None
    
    if content_type == 'photo':
        content_file_id = message.photo[-1].file_id
    elif content_type == 'document':
        if message.document.file_size > config.MAX_FILE_SIZE:
            await message.answer("🚫 Файл слишком большой (макс. 2МБ)")
            return
        content_file_id = message.document.file_id
    
    await state.update_data({
        'content_type': content_type,
        'content_text': content_text,
        'content_file_id': content_file_id
    })
    
    data = await state.get_data()
    if data.get('link_type') == "custom":
        await state.set_state(LinkCreation.waiting_for_custom_id)
        await message.answer(
            "✏️ <b>Введите желаемый ID для ссылки</b>\n\n"
            "Требования:\n"
            "- От 3 до 20 символов\n"
            "- Только буквы и цифры (A-Z, a-z, 0-9)\n"
            "- Уникальный (не занят другой ссылкой)",
            reply_markup=get_back_keyboard("create_link_menu")
        )
    else:
        await create_link_final(message, state)

@router.callback_query(F.data == "search_link")
async def search_link_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LinkActions.waiting_for_link_search)
    await callback.message.edit_text(
        "🔍 <b>Поиск ссылки</b>\n\nВведите ID ссылки для поиска:",
        reply_markup=InlineKeyboardBuilder()
            .button(text="◀️ Отмена", callback_data="admin_links")
            .as_markup()
    )

@router.message(LinkActions.waiting_for_link_search)
async def process_link_search(message: Message, state: FSMContext, bot: Bot):
    link_code = message.text.strip()
    link = db.get_link(link_code)
    
    if not link:
        await message.answer(
            "❌ Ссылка не найдена",
            reply_markup=InlineKeyboardBuilder()
                .button(text="🔍 Попробовать снова", callback_data="search_link")
                .button(text="◀️ В меню", callback_data="admin_links")
                .as_markup()
        )
        await state.clear()
        return
    
    bot_username = (await bot.get_me()).username
    text = (
        f"🔗 <b>Найдена ссылка:</b>\n\n"
        f"🆔 ID: <code>{link['link_code']}</code>\n"
        f"🔗 Полная ссылка: t.me/{bot_username}?start={link['link_code']}\n"
        f"📌 Тип: {link['content_type']}\n"
        f"📅 Создана: {format_date(link['creation_date'])}\n"
        f"👁️ Переходов: {link['visits']}"
    )
    
    await message.answer(
        text,
        reply_markup=InlineKeyboardBuilder()
            .button(text="✏️ Редактировать", callback_data=f"edit_link_{link['link_code']}")
            .button(text="🗑️ Удалить", callback_data=f"delete_link_{link['link_code']}")
            .button(text="◀️ В меню", callback_data="admin_links")
            .adjust(2)
            .as_markup()
    )
    await state.clear()

@router.callback_query(F.data.startswith("edit_link_"))
async def edit_link_menu(callback: CallbackQuery):
    link_code = callback.data.split("_")[2]
    await callback.message.edit_text(
        f"✏️ <b>Редактирование ссылки</b>\n\nID: {link_code}",
        reply_markup=InlineKeyboardBuilder()
            .button(text="📝 Изменить контент", callback_data=f"edit_link_content_{link_code}")
            .button(text="✏️ Изменить ID", callback_data=f"edit_link_id_{link_code}")
            .button(text="◀️ Назад", callback_data=f"link_detail_{link_code}_1")
            .adjust(1)
            .as_markup()
    )

async def create_link_final(message: Message, state: FSMContext):
    data = await state.get_data()
    link_code = data.get('custom_id', generate_link_code())
    
    success = db.create_link(
        link_code=link_code,
        content_type=data['content_type'],
        content_text=data['content_text'],
        content_file_id=data['content_file_id'],
        created_by=message.from_user.id
    )
    
    await state.clear()
    
    bot_info = await message.bot.get_me()
    if success:
        await message.answer(
            f"✅ <b>Ссылка успешно создана!</b>\n\n"
            f"🔗 <b>Ссылка:</b> t.me/{bot_info.username}?start={link_code}\n"
            f"🆔 <b>Код:</b> <code>{link_code}</code>\n"
            f"📌 <b>Тип:</b> {data['content_type']}",
            reply_markup=InlineKeyboardBuilder()
                .button(text="🔗 К деталям ссылки", callback_data=f"link_detail_{link_code}_1")
                .button(text="➕ Ещё ссылку", callback_data="create_link_menu")
                .as_markup()
        )
    else:
        await message.answer(
            "❌ <b>Не удалось создать ссылку!</b>\n\n"
            "Возможные причины:\n"
            "- Такой ID уже существует\n"
            "- Ошибка базы данных",
            reply_markup=get_back_keyboard("create_link_menu")
        )

@router.message(LinkCreation.waiting_for_custom_id)
async def process_custom_id(message: Message, state: FSMContext):
    custom_id = message.text.strip()
    
    if not (3 <= len(custom_id) <= 20) or not custom_id.isalnum():
        await message.answer(
            "❌ <b>Некорректный ID!</b>\n\n"
            "ID должен:\n"
            "- Содержать от 3 до 20 символов\n"
            "- Состоять только из букв и цифр (A-Z, a-z, 0-9)",
            reply_markup=get_back_keyboard("create_link_menu")
        )
        return
    
    if db.get_link(custom_id):
        await message.answer(
            "❌ <b>ID уже занят!</b>\n\n"
            "Пожалуйста, выберите другой ID",
            reply_markup=get_back_keyboard("create_link_menu")
        )
        return
    
    await state.update_data({'custom_id': custom_id})
    await create_link_final(message, state)

# Управление администраторами
@router.callback_query(F.data == "admin_admins")
async def admin_admins(callback: CallbackQuery):
    await callback.message.edit_text(
        "👨‍💻 <b>Управление администраторами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admins_management_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admins_list_"))
async def admins_list(callback: CallbackQuery):
    admins = db.get_all_admins()
    per_page = 5
    total_admins = len(admins)
    
    try:
        page = int(callback.data.split("_")[2])
    except:
        page = 1
    
    total_pages = (total_admins + per_page - 1) // per_page
    paginated = admins[(page-1)*per_page:page*per_page]
    
    text = f"👨‍💻 <b>Список администраторов</b> (страница {page}/{total_pages})\n\n"
    
    for i, admin in enumerate(paginated, 1):
        is_main = admin['user_id'] == config.ADMIN_ID
        text += f"{'👑' if is_main else '👨‍💻'} <b>{i}. {'Главный админ' if is_main else 'Администратор'}</b>\n"
        text += f"🆔 ID: <code>{admin['user_id']}</code>\n"
        text += f"📛 Username: @{admin.get('username', 'нет')}\n"
        text += f"📅 Добавлен: {format_date(admin['added_date'])}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admins_list_keyboard(page, total_pages)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("ask_remove_admin_"))
async def ask_remove_admin(callback: CallbackQuery):
    parts = callback.data.split("_")
    admin_id = int(parts[3])
    page = parts[4]
    
    if admin_id == config.ADMIN_ID:
        await callback.answer("🚫 Нельзя удалить главного админа!", show_alert=True)
        return
    
    admin = next((a for a in db.get_all_admins() if a['user_id'] == admin_id), None)
    if not admin:
        await callback.answer("Админ не найден!")
        return
    
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы уверены, что хотите удалить администратора?\n\n"
        f"🆔 ID: <code>{admin['user_id']}</code>\n"
        f"📛 Username: @{admin.get('username', 'нет')}\n"
        f"📅 Добавлен: {format_date(admin['added_date'])}",
        reply_markup=get_confirmation_keyboard(
            "remove_admin", 
            str(admin_id), 
            f"admins_list_{page}"
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_remove_admin_"))
async def confirm_remove_admin(callback: CallbackQuery):
    admin_id = int(callback.data.split("_")[3])
    
    if db.remove_admin(admin_id):
        await callback.answer("✅ Администратор удалён!", show_alert=True)
        await callback.message.edit_text(
            "✅ <b>Администратор успешно удалён!</b>",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📋 К списку админов", callback_data="admins_list_1")
                .button(text="◀️ В меню", callback_data="admin_admins")
                .as_markup()
        )
    else:
        await callback.answer("❌ Ошибка при удалении администратора!", show_alert=True)

@router.callback_query(F.data == "add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminActions.waiting_for_admin)
    await callback.message.edit_text(
        "👨‍💻 <b>Добавление администратора</b>\n\n"
        "Введите username или ID пользователя:",
        reply_markup=get_back_keyboard("admin_admins")
    )
    await callback.answer()

@router.message(AdminActions.waiting_for_admin)
async def add_admin_process(message: Message, state: FSMContext):
    user_identifier = message.text.strip()
    
    try:
        if user_identifier.isdigit():
            user_id = int(user_identifier)
            user = db.get_user(user_id)
            if not user:
                await message.answer("❌ Пользователь не найден!")
                await state.clear()
                return
        else:
            username = user_identifier.lstrip('@')
            user = db.get_user_by_username(username)
            if not user:
                await message.answer("❌ Пользователь не найден!")
                await state.clear()
                return
            user_id = user['user_id']
        
        if user_id == config.ADMIN_ID:
            await message.answer("❌ Этот пользователь уже является главным админом!")
            await state.clear()
            return
            
        if db.is_admin(user_id):
            await message.answer("❌ Этот пользователь уже является админом!")
            await state.clear()
            return
        
        db.add_admin(
            user_id=user_id,
            username=user.get('username', ''),
            added_by=message.from_user.id
        )
        
        await message.answer(
            f"✅ <b>Пользователь добавлен в админы!</b>\n\n"
            f"👤 Имя: {user.get('first_name', '')}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📛 Username: @{user.get('username', 'нет')}",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📋 К списку админов", callback_data="admins_list_1")
                .button(text="◀️ В меню", callback_data="admin_admins")
                .as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка при добавлении админа: {e}")
        await message.answer(
            "❌ <b>Ошибка при добавлении админа!</b>\n\n"
            "Проверьте правильность ввода и попробуйте снова.",
            reply_markup=get_back_keyboard("admin_admins")
        )
    
    await state.clear()

# Управление репортами
@router.callback_query(F.data == "admin_reports")
async def admin_reports(callback: CallbackQuery):
    new_reports = db.count_reports(status='open')
    text = f"📝 <b>Управление репортами</b>"
    if new_reports > 0:
        text += f"\n\n⚠️ <b>Новых репортов:</b> {new_reports}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_reports_management_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("reports_list_"))
async def reports_list(callback: CallbackQuery):
    parts = callback.data.split("_")
    status = parts[2]
    page = int(parts[3])
    
    reports = db.get_reports_by_status(status)
    per_page = 5
    total_reports = len(reports)
    total_pages = (total_reports + per_page - 1) // per_page
    paginated = reports[(page-1)*per_page:page*per_page]
    
    text = f"📝 <b>{'Открытые' if status == 'open' else 'Закрытые'} репорты</b> (стр. {page}/{total_pages})\n\n"
    
    kb = InlineKeyboardBuilder()
    
    for report in paginated:
        user = db.get_user(report['user_id'])
        if user:
            kb.button(
                text=f"#{report['report_id']} от {user['first_name']}",
                callback_data=f"report_detail_{report['report_id']}_{page}_{status}"
            )
        else:
            kb.button(
                text=f"#{report['report_id']} (пользователь удалён)",
                callback_data=f"report_detail_{report['report_id']}_{page}_{status}"
            )
    
    if page > 1:
        kb.button(text="⬅️ Назад", callback_data=f"reports_list_{status}_{page-1}")
    if page < total_pages:
        kb.button(text="Вперед ➡️", callback_data=f"reports_list_{status}_{page+1}")
    kb.button(text="◀️ В меню", callback_data="admin_reports")
    
    kb.adjust(1, *[1 for _ in paginated], 2, 1)
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "users_settings")
async def users_settings(callback: CallbackQuery):
    settings = db.get_user_settings()
    await callback.message.edit_text(
        "👥 <b>Настройки пользователей</b>\n\n"
        f"🔗 Лимит ссылок: {settings['link_limit']}\n"
        f"📝 Лимит жалоб: {settings['report_limit']}\n"
        f"⏱ Задержка между жалобами: {settings['report_cooldown']} мин.\n\n"
        "Выберите параметр для изменения:",
        reply_markup=InlineKeyboardBuilder()
            .button(text="🔗 Лимит ссылок", callback_data="set_link_limit")
            .button(text="📝 Лимит жалоб", callback_data="set_report_limit")
            .button(text="⏱ Задержка жалоб", callback_data="set_report_cooldown")
            .button(text="◀️ Назад", callback_data="admin_settings")
            .adjust(1)
            .as_markup()
    )

@router.callback_query(F.data == "set_link_limit")
async def set_link_limit_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettings.waiting_for_link_limit)
    await callback.message.edit_text(
        "✏️ <b>Изменение лимита ссылок</b>\n\n"
        "Введите новое максимальное количество ссылок для пользователей:",
        reply_markup=get_back_keyboard("users_settings")
    )

@router.message(UserSettings.waiting_for_link_limit)
async def process_link_limit(message: Message, state: FSMContext):
    try:
        limit = int(message.text)
        if limit < 1:
            raise ValueError
        if db.update_user_setting('link_limit', limit):
            await message.answer(
                f"✅ Лимит ссылок успешно изменён на {limit}",
                reply_markup=get_back_keyboard("users_settings")
            )
        else:
            await message.answer(
                "❌ Ошибка при изменении лимита",
                reply_markup=get_back_keyboard("users_settings")
            )
    except ValueError:
        await message.answer(
            "❌ Введите корректное число (больше 0)",
            reply_markup=get_back_keyboard("users_settings")
        )
    await state.clear()

@router.callback_query(F.data == "set_report_limit")
async def set_report_limit_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettings.waiting_for_report_limit)
    await callback.message.edit_text(
        "✏️ <b>Изменение лимита жалоб</b>\n\n"
        "Введите новое максимальное количество жалоб для пользователей:",
        reply_markup=get_back_keyboard("users_settings")
    )

@router.message(UserSettings.waiting_for_report_limit)
async def process_report_limit(message: Message, state: FSMContext):
    try:
        limit = int(message.text)
        if limit < 1:
            raise ValueError
        if db.update_user_setting('report_limit', limit):
            await message.answer(
                f"✅ Лимит жалоб успешно изменён на {limit}",
                reply_markup=get_back_keyboard("users_settings")
            )
        else:
            await message.answer(
                "❌ Ошибка при изменении лимита",
                reply_markup=get_back_keyboard("users_settings")
            )
    except ValueError:
        await message.answer(
            "❌ Введите корректное число (больше 0)",
            reply_markup=get_back_keyboard("users_settings")
        )
    await state.clear()

@router.callback_query(F.data == "set_report_cooldown")
async def set_report_cooldown_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettings.waiting_for_cooldown)
    await callback.message.edit_text(
        "✏️ <b>Изменение задержки между жалобами</b>\n\n"
        "Введите задержку в минутах (например, 5 - жалобы можно отправлять раз в 5 минут):",
        reply_markup=get_back_keyboard("users_settings")
    )

@router.message(UserSettings.waiting_for_cooldown)
async def process_report_cooldown(message: Message, state: FSMContext):
    try:
        cooldown = int(message.text)
        if cooldown < 1:
            raise ValueError
        if db.update_user_setting('report_cooldown', cooldown):
            await message.answer(
                f"✅ Задержка между жалобами успешно изменена на {cooldown} минут",
                reply_markup=get_back_keyboard("users_settings")
            )
        else:
            await message.answer(
                "❌ Ошибка при изменении задержки",
                reply_markup=get_back_keyboard("users_settings")
            )
    except ValueError:
        await message.answer(
            "❌ Введите корректное число (больше 0)",
            reply_markup=get_back_keyboard("users_settings")
        )
    await state.clear()

@router.callback_query(F.data == "edit_user_limits")
async def edit_user_limits(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSettings.waiting_for_link_limit)  # Используем существующее состояние
    await callback.message.edit_text(
        "✏️ <b>Изменение лимитов пользователей</b>\n\n"
        "Введите новые лимиты в формате:\n"
        "Лимит ссылок|Лимит жалоб\n\n"
        "Пример: 10|5",
        reply_markup=get_back_keyboard("users_settings")
    )

@router.message(UserSettings.waiting_for_link_limit)  # Используем существующее состояние
async def process_user_limits(message: Message, state: FSMContext):
    try:
        link_limit, report_limit = map(int, message.text.split('|'))
        db.execute('''
            UPDATE user_settings 
            SET link_limit = ?, report_limit = ?
        ''', (link_limit, report_limit))
        await message.answer(
            "✅ Лимиты успешно обновлены!",
            reply_markup=get_back_keyboard("users_settings")
        )
    except Exception as e:
        await message.answer(
            "❌ Неверный формат. Используйте: число|число",
            reply_markup=get_back_keyboard("users_settings")
        )
    await state.clear()

@router.callback_query(F.data == "set_link_length")
async def set_link_length(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LinkSettings.waiting_for_length)
    await callback.message.edit_text(
        "📏 <b>Установка лимита символов</b>\n\n"
        "Введите максимальное количество символов для текста ссылок:",
        reply_markup=get_back_keyboard("links_settings")
    )

@router.message(LinkSettings.waiting_for_length)
async def process_link_length(message: Message, state: FSMContext):
    try:
        length = int(message.text)
        config.MAX_TEXT_LENGTH = length
        await message.answer(
            f"✅ Лимит символов установлен: {length}",
            reply_markup=get_back_keyboard("links_settings")
        )
    except ValueError:
        await message.answer(
            "❌ Введите корректное число",
            reply_markup=get_back_keyboard("links_settings")
        )
    await state.clear()

@router.callback_query(F.data == "set_file_size")
async def set_file_size(callback: CallbackQuery, state: FSMContext):
    await state.set_state(LinkSettings.waiting_for_size)
    await callback.message.edit_text(
        "📦 <b>Установка максимального размера файла</b>\n\n"
        "Введите максимальный размер файла в МБ:",
        reply_markup=get_back_keyboard("links_settings")
    )

@router.message(LinkSettings.waiting_for_size)
async def process_file_size(message: Message, state: FSMContext):
    try:
        size = int(message.text)
        config.MAX_FILE_SIZE = size * 1024 * 1024  # Convert to bytes
        await message.answer(
            f"✅ Максимальный размер файла установлен: {size} МБ",
            reply_markup=get_back_keyboard("links_settings")
        )
    except ValueError:
        await message.answer(
            "❌ Введите корректное число",
            reply_markup=get_back_keyboard("links_settings")
        )
    await state.clear()

@router.callback_query(F.data == "toggle_notify")
async def toggle_notify(callback: CallbackQuery):
    settings = db.get_report_settings()
    new_value = not settings['notifications']
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE report_settings SET notifications = ?', (new_value,))
        conn.commit()
    await reports_settings(callback)

@router.callback_query(F.data == "toggle_auto_close")
async def toggle_auto_close(callback: CallbackQuery):
    settings = db.get_report_settings()
    new_value = not settings['auto_close']
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE report_settings SET auto_close = ?', (new_value,))
        conn.commit()
    await reports_settings(callback)

@router.callback_query(F.data == "links_settings")
async def links_settings(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔗 <b>Настройки ссылок</b>\n\n"
        "Выберите параметр для настройки:",
        reply_markup=InlineKeyboardBuilder()
            .button(text="📏 Лимит символов", callback_data="set_link_length")
            .button(text="📦 Макс. размер файла", callback_data="set_file_size")
            .button(text="◀️ Назад", callback_data="admin_settings")
            .adjust(1)
            .as_markup()
    )

@router.callback_query(F.data.startswith("report_detail_"))
async def report_detail(callback: CallbackQuery):
    parts = callback.data.split("_")
    report_id = int(parts[2])
    
    report = db.get_report(report_id)
    if not report:
        await callback.answer("❌ Репорт не найден", show_alert=True)
        return
    
    # Добавляем проверку на наличие ключа
    report.setdefault('answered_by', None)
    
    user = db.get_user(report['user_id'])
    admin = db.get_user(report['answered_by']) if report['answered_by'] else None
    
    text = f"📄 <b>Детали репорта #{report_id}</b>\n\n"
    text += f"👤 От: {user['first_name']} (@{user.get('username', 'нет')})\n"
    text += f"📅 Дата: {format_date(report['report_date'])}\n"
    text += f"🔴 Статус: {'Открыт' if report['status'] == 'open' else 'Закрыт'}\n\n"
    text += f"📝 Сообщение:\n{report['message']}\n\n"
    
    if report['answer']:
        text += f"📩 Ответ админа: {report['answer']}\n"
        if admin:
            text += f"👨‍💻 Ответил: {admin['first_name']}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_report_detail_keyboard(report_id, 1, report['status'])
    )

@router.callback_query(F.data.startswith("ask_delete_report_"))
async def ask_delete_report(callback: CallbackQuery):
    parts = callback.data.split("_")
    report_id = int(parts[3])
    page = int(parts[4])
    status = parts[5]
    
    report = db.get_report(report_id)
    if not report:
        await callback.answer("❌ Репорт не найден!", show_alert=True)
        return
    
    user = db.get_user(report['user_id'])
    user_info = f"{user['first_name']} (@{user.get('username', 'нет')})" if user else "Пользователь удалён"
    
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы уверены, что хотите удалить репорт?\n\n"
        f"🆔 ID: {report['report_id']}\n"
        f"👤 От: {user_info}\n"
        f"📅 Дата: {format_date(report['report_date'])}\n"
        f"📝 Сообщение: {report['message'][:200]}...",
        reply_markup=get_confirmation_keyboard(
            "delete_report", 
            f"{report_id}_{page}_{status}", 
            f"report_detail_{report_id}_{page}_{status}"
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_report_"))
async def confirm_delete_report(callback: CallbackQuery):
    parts = callback.data.split("_")
    report_id = int(parts[3])
    page = int(parts[4])
    status = parts[5]
    
    if db.delete_report(report_id):
        await callback.answer("✅ Репорт удалён!", show_alert=True)
        await callback.message.edit_text(
            "✅ <b>Репорт успешно удалён!</b>",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📋 К списку репортов", callback_data=f"reports_list_{status}_{page}")
                .button(text="◀️ В меню", callback_data="admin_reports")
                .as_markup()
        )
    else:
        await callback.answer("❌ Ошибка при удалении репорта!", show_alert=True)

@router.callback_query(F.data.startswith("answer_report_"))
async def answer_report_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    report_id = int(parts[2])
    page = int(parts[3])
    status = parts[4]
    
    await state.update_data({
        'report_id': report_id, 
        'page': page,
        'status': status
    })
    await state.set_state(AdminActions.waiting_for_report_answer)
    
    report = db.get_report(report_id)
    if not report:
        await callback.answer("❌ Репорт не найден!", show_alert=True)
        return
    
    user = db.get_user(report['user_id'])
    user_info = f"{user['first_name']} (@{user.get('username', 'нет')})" if user else "Пользователь удалён"
    
    await callback.message.edit_text(
        f"✉️ <b>Ответ на репорт #{report_id}</b>\n\n"
        f"👤 От: {user_info}\n"
        f"📝 Сообщение: {report['message'][:200]}...\n\n"
        "Введите ваш ответ:",
        reply_markup=get_back_keyboard(f"report_detail_{report_id}_{page}_{status}")
    )
    await callback.answer()

@router.message(AdminActions.waiting_for_report_answer)
async def answer_report_process(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    report_id = data['report_id']
    page = data['page']
    status = data['status']
    
    report = db.get_report(report_id)
    if not report:
        await message.answer("❌ Репорт не найден!")
        await state.clear()
        return
    
    answer = message.text
    db.answer_report(report_id, answer, message.from_user.id)
    
    # Отправляем ответ пользователю
    try:
        if report['user_id']:
            await bot.send_message(
                chat_id=report['user_id'],
                text=f"📩 <b>Ответ на ваш репорт #{report_id}</b>\n\n"
                     f"👨‍💻 <b>Администратор:</b> {message.from_user.full_name}\n\n"
                     f"📝 <b>Ответ:</b>\n{answer}",
                reply_markup=InlineKeyboardBuilder()
                    .button(text="✉️ Ответить", callback_data=f"user_reply_{report_id}")
                    .as_markup()
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке ответа: {e}")
    
    await message.answer(
        "✅ <b>Ответ отправлен пользователю!</b>",
        reply_markup=InlineKeyboardBuilder()
            .button(text="📋 К списку репортов", callback_data=f"reports_list_{status}_{page}")
            .button(text="◀️ В меню", callback_data="admin_reports")
            .as_markup()
    )
    await state.clear()

@router.callback_query(F.data.startswith("ask_ban_from_report_"))
async def ask_ban_from_report(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    report_id = int(parts[4])
    page = int(parts[5])
    status = parts[6]
    
    report = db.get_report(report_id)
    if not report:
        await callback.answer("❌ Репорт не найден!", show_alert=True)
        return
    
    user = db.get_user(report['user_id'])
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    if user['is_banned']:
        await callback.answer("❌ Пользователь уже заблокирован!", show_alert=True)
        return
    
    await state.update_data({
        'user_id': user['user_id'],
        'report_id': report_id,
        'page': page,
        'status': status
    })
    
    await callback.message.edit_text(
        f"⚠️ <b>Блокировка пользователя</b>\n\n"
        f"Вы уверены, что хотите заблокировать пользователя?\n\n"
        f"👤 ID: {user['user_id']}\n"
        f"📛 Username: @{user.get('username', 'нет')}\n"
        f"📝 Причина: Жалоба #{report_id}\n\n"
        "Вы можете изменить причину бана:",
        reply_markup=get_confirmation_keyboard(
            "ban_from_report", 
            f"{report_id}_{page}_{status}", 
            f"report_detail_{report_id}_{page}_{status}"
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_ban_from_report_"))
async def confirm_ban_from_report(callback: CallbackQuery):
    parts = callback.data.split("_")
    report_id = int(parts[4])
    page = int(parts[5])
    status = parts[6]
    
    report = db.get_report(report_id)
    if not report:
        await callback.answer("❌ Репорт не найден!", show_alert=True)
        return
    
    user_id = report['user_id']
    if not user_id:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    db.ban_user(user_id, f"Жалоба #{report_id}", callback.from_user.id)
    
    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=f"🚫 <b>Вы были заблокированы</b>\n\n"
                 f"Причина: Жалоба #{report_id}\n\n"
                 f"Если вы считаете это ошибкой, вы можете подать апелляцию.",
            reply_markup=InlineKeyboardBuilder()
                .button(text="✉️ Подать апелляцию", callback_data=f"user_appeal_{report_id}")
                .as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка при уведомлении пользователя: {e}")
    
    await callback.answer("✅ Пользователь заблокирован!", show_alert=True)
    await callback.message.edit_text(
        "✅ <b>Пользователь успешно заблокирован!</b>",
        reply_markup=InlineKeyboardBuilder()
            .button(text="📋 К списку репортов", callback_data=f"reports_list_{status}_{page}")
            .button(text="◀️ В меню", callback_data="admin_reports")
            .as_markup()
    )

# Управление пользователями
@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Выберите действие:",
        reply_markup=get_users_management_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "search_user")
async def search_user_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminActions.waiting_for_user_search)
    await callback.message.edit_text(
        "🔍 <b>Поиск пользователя</b>\n\n"
        "Введите username или ID пользователя:",
        reply_markup=get_back_keyboard("admin_users")
    )
    await callback.answer()

@router.message(AdminActions.waiting_for_user_search)
async def search_user_process(message: Message, state: FSMContext):
    user_identifier = message.text.strip()
    try:
        if user_identifier.isdigit():
            user_id = int(user_identifier)
            user = db.get_user(user_id)
            if not user:
                await message.answer("❌ Пользователь не найден!")
                await state.clear()
                return
        else:
            user = db.get_user_by_username(user_identifier.lstrip('@'))
            if not user:
                await message.answer("❌ Пользователь не найден!")
                await state.clear()
                return
            user_id = user['user_id']
    
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя: {e}")
        await message.answer("❌ Ошибка при поиске пользователя!")
        await state.clear()
        return
    
    text = f"👤 <b>Информация о пользователе</b>\n\n"
    text += f"🆔 ID: <code>{user['user_id']}</code>\n"
    text += f"👤 Имя: {user['first_name']}\n"
    text += f"📛 Username: @{user.get('username', 'нет')}\n"
    text += f"📅 Регистрация: {format_date(user['registration_date'])}\n"
    text += f"🔴 Статус: {'🚫 Заблокирован' if user['is_banned'] else '🟢 Активен'}\n"
    if user['is_banned']:
        text += f"📝 Причина бана: {user['ban_reason']}\n"
        text += f"📅 Дата бана: {format_date(user['ban_date'])}\n"
        text += f"👨‍💻 Заблокировал: {user['banned_by']}\n"
    text += f"🕒 Последняя активность: {format_date(user.get('last_activity'))}\n"
    text += f"🔗 Переходов по ссылкам: {user.get('link_visits', 0)}\n"
    text += f"📝 Репортов: {db.count_user_reports(user_id)}"
    
    await message.answer(
        text,
        reply_markup=get_user_actions_keyboard(
            user_id=user_id,
            is_banned=user['is_banned'],
            back_to="admin_users"
        )
    )
    await state.clear()

@router.callback_query(F.data.startswith("banned_users_"))
async def banned_users_list(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    banned = db.get_banned_users(page=page, per_page=5)
    
    text = "🚫 <b>Список забаненных</b>\n\n"
    for user in banned:
        text += f"ID: {user['user_id']} | @{user.get('username', 'нет')}\nПричина: {user['ban_reason']}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_banned_list_keyboard(page)
    )

def get_banned_list_keyboard(page: int):
    kb = InlineKeyboardBuilder()
    if page > 1:
        kb.button(text="⬅️ Назад", callback_data=f"banned_users_{page-1}")
    kb.button(text="🔄 Обновить", callback_data=f"banned_users_{page}")
    kb.button(text="◀️ В меню", callback_data="admin_users")
    kb.adjust(2)
    return kb.as_markup()

@router.callback_query(F.data == "check_subscriptions")
async def check_subscriptions(callback: CallbackQuery, bot: Bot):
    await callback.message.edit_text("🔄 Проверяю подписки...")
    
    try:
        inactive = await db.check_inactive_subscriptions(bot)
        text = "🔍 <b>Результаты проверки подписок</b>\n\n"
        
        if not inactive:
            text += "✅ Все пользователи подписаны на требуемые каналы"
        else:
            text += f"🚫 Не подписаны: {len(inactive)} пользователей\n"
            for i, user in enumerate(inactive[:10], 1):  # Показываем первые 10
                user_info = await bot.get_chat(user['user_id'])
                username = f"@{user_info.username}" if user_info.username else "нет username"
                text += f"{i}. {user_info.full_name} ({username}, ID: {user['user_id']})\n"
            
            if len(inactive) > 10:
                text += f"\n...и ещё {len(inactive)-10} пользователей"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_back_keyboard("admin_advertise")
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке подписок: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при проверке подписок",
            reply_markup=get_back_keyboard("admin_advertise")
        )

@router.callback_query(F.data.startswith("ask_ban_user_"))
async def ask_ban_user(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    user_id = int(parts[3])
    page = parts[4]
    
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    if user['is_banned']:
        await callback.answer("❌ Пользователь уже заблокирован!", show_alert=True)
        return
    
    await state.update_data(user_id=user_id, page=page)
    await state.set_state(AdminActions.waiting_for_ban_reason)
    
    await callback.message.edit_text(
        f"⚠️ <b>Блокировка пользователя</b>\n\n"
        f"Введите причину бана для пользователя:\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"📛 Username: @{user.get('username', 'нет')}",
        reply_markup=get_back_keyboard(f"user_info_{user_id}")
    )
    await callback.answer()

@router.message(AdminActions.waiting_for_ban_reason)
async def ban_user_process(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data['user_id']
    page = data.get('page', 1)
    
    reason = message.text
    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден!")
        await state.clear()
        return
    
    if user['is_banned']:
        await message.answer("❌ Пользователь уже заблокирован!")
        await state.clear()
        return
    
    db.ban_user(user_id, reason, message.from_user.id)
    
    # Уведомляем пользователя
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=f"🚫 <b>Вы были заблокированы</b>\n\n"
                 f"Причина: {reason}\n\n"
                 f"Если вы считаете это ошибкой, вы можете подать апелляцию.",
            reply_markup=InlineKeyboardBuilder()
                .button(text="✉️ Подать апелляцию", callback_data="user_appeal")
                .as_markup()
        )
    except Exception as e:
        logger.error(f"Ошибка при уведомлении пользователя: {e}")
    
    await message.answer(
        f"✅ <b>Пользователь @{user.get('username', user_id)} заблокирован!</b>",
        reply_markup=InlineKeyboardBuilder()
            .button(text="🚫 К списку забаненных", callback_data=f"banned_users_{page}")
            .button(text="◀️ В меню", callback_data="admin_users")
            .as_markup()
    )
    await state.clear()

@router.callback_query(F.data.startswith("unban_user_"))
async def unban_user(callback: CallbackQuery):
    parts = callback.data.split("_")
    user_id = int(parts[2])
    page = parts[3] if len(parts) > 3 else 1
    
    user = db.get_user(user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден!", show_alert=True)
        return
    
    if not user['is_banned']:
        await callback.answer("❌ Пользователь не заблокирован!", show_alert=True)
        return
    
    db.unban_user(user_id)
    
    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=f"✅ <b>Вы были разблокированы</b>\n\n"
                 f"Теперь вы снова можете пользоваться ботом."
        )
    except Exception as e:
        logger.error(f"Ошибка при уведомлении пользователя: {e}")
    
    await callback.answer("✅ Пользователь разблокирован!", show_alert=True)
    await callback.message.edit_text(
        "✅ <b>Пользователь успешно разблокирован!</b>",
        reply_markup=InlineKeyboardBuilder()
            .button(text="🚫 К списку забаненных", callback_data=f"banned_users_{page}")
            .button(text="◀️ В меню", callback_data="admin_users")
            .as_markup()
    )

# Управление рекламными каналами
@router.callback_query(F.data == "admin_advertise")
async def admin_advertise(callback: CallbackQuery):
    await callback.message.edit_text(
        "📢 <b>Управление рекламными каналами</b>\n\n"
        "Выберите действие:",
        reply_markup=get_advertise_management_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("channels_list_"))
async def channels_list(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    per_page = 5
    all_channels = db.get_all_subscription_channels()
    total_channels = len(all_channels)
    total_pages = (total_channels + per_page - 1) // per_page
    channels = all_channels[(page-1)*per_page:page*per_page]
    
    text = f"📢 <b>Список каналов</b> (страница {page}/{total_pages})\n\n"
    
    kb = InlineKeyboardBuilder()
    
    for channel in channels:
        kb.button(
            text=f"{channel['title']} ({'🔒' if channel['check_type'] == 1 else '🔗'})", 
            callback_data=f"channel_detail_{channel['channel_id']}"
        )
    
    if page > 1:
        kb.button(text="⬅️ Назад", callback_data=f"channels_list_{page-1}")
    if page < total_pages:
        kb.button(text="Вперед ➡️", callback_data=f"channels_list_{page+1}")
    kb.button(text="➕ Добавить", callback_data="add_channel")
    kb.button(text="◀️ В меню", callback_data="admin_advertise")
    
    kb.adjust(1, *[1 for _ in channels], 2, 2)
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("channel_detail_"))
async def channel_detail(callback: CallbackQuery):
    channel_id = callback.data.split("_")[2]
    channel = db.get_channel_detail(channel_id)
    
    if not channel:
        await callback.answer("❌ Канал не найден", show_alert=True)
        return
    
    text = f"📢 <b>Информация о канале</b>\n\n"
    text += f"📌 Название: {channel['title']}\n"
    text += f"🆔 ID: {channel['channel_id']}\n"
    text += f"🔗 Username: @{channel.get('username', 'нет')}\n"
    text += f"👥 Подписчиков: {channel.get('subscribers_count', 'неизвестно')}"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_channel_detail_keyboard(channel_id)
    )

def get_channel_detail_keyboard(channel_id: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data=f"refresh_channel_{channel_id}")
    kb.button(text="🗑️ Удалить", callback_data=f"ask_delete_channel_{channel_id}")
    kb.button(text="◀️ Назад", callback_data="channels_list_1")
    kb.adjust(1)
    return kb.as_markup()

@router.callback_query(F.data.startswith("ask_delete_channel_"))
async def ask_delete_channel(callback: CallbackQuery):
    channel_id = callback.data.split("_")[3]
    channel = db.get_subscription_channel(channel_id)
    
    if not channel:
        await callback.answer("❌ Канал не найден!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы уверены, что хотите удалить канал?\n\n"
        f"📌 Название: {channel['title']}\n"
        f"🔗 Username: @{channel.get('username', 'нет')}\n"
        f"🔐 Тип проверки: {'🔒 Все функции' if channel['check_type'] == 1 else '🔗 Только ссылки'}",
        reply_markup=get_confirmation_keyboard(
            "delete_channel", 
            channel_id, 
            f"channel_detail_{channel_id}"
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_delete_channel_"))
async def confirm_delete_channel(callback: CallbackQuery):
    channel_id = callback.data.split("_")[3]
    
    if db.remove_subscription_channel(channel_id):
        await callback.answer("✅ Канал успешно удалён!", show_alert=True)
        await callback.message.edit_text(
            "✅ <b>Канал успешно удалён!</b>",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📋 К списку каналов", callback_data="channels_list_1")
                .button(text="◀️ В меню", callback_data="admin_advertise")
                .as_markup()
        )
    else:
        await callback.answer("❌ Ошибка при удалении канала!", show_alert=True)

# Рассылка сообщений
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery):
    await callback.message.edit_text(
        "📩 <b>Рассылка сообщений</b>\n\n"
        "Выберите тип рассылки:",
        reply_markup=get_broadcast_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "text_broadcast")
async def text_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminActions.waiting_for_ad_message)
    await state.update_data(broadcast_type="text")
    await callback.message.edit_text(
        "📝 <b>Текстовая рассылка</b>\n\n"
        "Введите текст сообщения для рассылки:",
        reply_markup=get_back_keyboard("admin_broadcast")
    )
    await callback.answer()

@router.message(AdminActions.waiting_for_ad_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    broadcast_type = data.get('broadcast_type')
    text = message.text if broadcast_type == "text" else message.caption
    
    await state.clear()
    
    # Подтверждение рассылки
    await message.answer(
        f"⚠️ <b>Подтверждение рассылки</b>\n\n"
        f"Тип: {'текст' if broadcast_type == 'text' else 'фото'}\n"
        f"Сообщение:\n{text[:500]}{'...' if len(text) > 500 else ''}\n\n"
        f"Отправить это сообщение всем пользователям?",
        reply_markup=get_confirmation_keyboard(
            "send_broadcast",
            broadcast_type,
            "admin_broadcast"
        )
    )
    
    # Сохраняем данные для рассылки
    await state.update_data({
        'broadcast_type': broadcast_type,
        'text': text,
        'file_id': message.photo[-1].file_id if broadcast_type == "photo" else None
    })

@router.callback_query(F.data.startswith("confirm_send_broadcast_"))
async def confirm_send_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    broadcast_type = callback.data.split("_")[3]
    data = await state.get_data()
    
    users = db.get_all_users()
    total = len(users)
    success = 0
    failed = 0
    
    await callback.message.edit_text(f"📩 <b>Начата рассылка...</b>\n\nОбработано: 0/{total}")
    
    for user in users:
        try:
            if broadcast_type == "text":
                await bot.send_message(
                    chat_id=user['user_id'],
                    text=data['text']
                )
            else:
                await bot.send_photo(
                    chat_id=user['user_id'],
                    photo=data['file_id'],
                    caption=data['text']
                )
            success += 1
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {user['user_id']}: {e}")
            failed += 1
        
        if (success + failed) % 10 == 0:
            await callback.message.edit_text(
                f"📩 <b>Рассылка в процессе...</b>\n\n"
                f"Обработано: {success + failed}/{total}\n"
                f"✅ Успешно: {success}\n"
                f"❌ Ошибок: {failed}"
            )
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Всего пользователей: {total}\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=InlineKeyboardBuilder()
            .button(text="◀️ В меню", callback_data="admin_panel")
            .as_markup()
    )
    await state.clear()
    await callback.answer()

# Обработка репортов от пользователей
@router.message(F.text.startswith("Репорт: "))
async def process_user_report(message: Message, bot: Bot):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    settings = db.get_user_settings()
    
    # Проверка на бан
    if user and user.get('is_banned'):
        await message.answer("🚫 Вы заблокированы и не можете отправлять жалобы.")
        return
    
    # Проверка лимита жалоб
    user_reports_count = db.count_user_reports(user_id)
    if user_reports_count >= settings['report_limit']:
        await message.answer(
            f"❌ Вы достигли лимита жалоб ({settings['report_limit']}).\n"
            "Дождитесь ответа на предыдущие жалобы или их удаления."
        )
        return
    
    # Проверка задержки между жалобами
    last_report = db.get_last_user_report(user_id)
    if last_report:
        last_time = datetime.strptime(last_report['report_date'], "%Y-%m-%d %H:%M:%S")
        cooldown = timedelta(minutes=settings['report_cooldown'])
        if datetime.now() - last_time < cooldown:
            remaining = (last_time + cooldown - datetime.now()).seconds // 60 + 1
            await message.answer(
                f"⏳ Вы можете отправить следующую жалобу через {remaining} минут"
            )
            return
    
    report_text = message.text.replace("Репорт: ", "").strip()
    
    # Проверка на пустое сообщение
    if not report_text:
        await message.answer("❌ Текст жалобы не может быть пустым.")
        return
    
    # Создание жалобы
    report_id = db.create_report(user_id, report_text)
    
    # Отправка уведомлений админам (если включены в настройках)
    report_settings = db.get_report_settings()
    if report_settings['notifications']:
        admins = db.get_all_admins()
        for admin in admins:
            try:
                await bot.send_message(
                    chat_id=admin['user_id'],
                    text=f"⚠️ <b>Новый репорт #{report_id}</b>\n\n"
                         f"👤 От: {message.from_user.full_name} "
                         f"(@{message.from_user.username or 'нет'}, ID: {user_id})\n"
                         f"📝 Сообщение:\n{report_text}",
                    reply_markup=get_report_notification_keyboard(report_id)
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления админу {admin['user_id']}: {e}")
    
    # Ответ пользователю
    await message.answer(
        "✅ <b>Ваш репорт отправлен администраторам!</b>\n\n"
        "Мы рассмотрим ваше сообщение в ближайшее время.",
        reply_markup=InlineKeyboardBuilder()
            .button(text="✉️ Мои репорты", callback_data="user_reports")
            .as_markup()
    )
    
    # Автозакрытие старых репортов (если включено в настройках)
    if report_settings['auto_close']:
        old_reports = db.get_old_open_reports(user_id, days=7)
        for report in old_reports:
            db.close_report(report['report_id'])

# Обработка уведомлений для админов
async def notify_admins(bot: Bot, text: str, report_id: int = None):
    admins = db.get_all_admins()
    for admin in admins:
        try:
            if report_id:
                await bot.send_message(
                    chat_id=admin['user_id'],
                    text=text,
                    reply_markup=get_report_notification_keyboard(report_id)
                )
            else:
                await bot.send_message(
                    chat_id=admin['user_id'],
                    text=text
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления админу {admin['user_id']}: {e}")

admin_router = router