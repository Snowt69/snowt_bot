from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputFile, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database
from config import config
import logging
import os
import psutil
import subprocess
import sys
import asyncio
from datetime import datetime, timedelta
import time
import shutil
import sqlite3
import platform
import cpuinfo
import GPUtil
import uuid
import socket
import requests
from typing import Optional, List, Dict, Any
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()
db = Database()
logger = logging.getLogger(__name__)

class DeveloperStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_announcement = State()
    waiting_for_developer_id = State()
    waiting_for_sql_query = State()
    waiting_for_command = State()
    waiting_for_script = State()
    waiting_for_log_search = State()

def is_developer(user_id: int) -> bool:
    """Проверка, является ли пользователь разработчиком"""
    return user_id in config.DEVELOPER_IDS or user_id == config.ADMIN_ID

def format_size(size_bytes: int) -> str:
    """Форматирование размера в читаемый вид"""
    for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"

def format_time(seconds: float) -> str:
    """Форматирование времени в читаемый вид"""
    if seconds < 1:
        return f"{seconds*1000:.0f}мс"
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return f"{days}д {hours}ч {minutes}м {seconds:.0f}с"

def get_system_info() -> Dict[str, Any]:
    """Получение информации о системе"""
    info = {}
    
    # Информация о процессоре
    cpu_info = cpuinfo.get_cpu_info()
    info['cpu'] = {
        'модель': cpu_info.get('brand_raw', 'Неизвестно'),
        'ядра': psutil.cpu_count(logical=False),
        'потоки': psutil.cpu_count(logical=True),
        'нагрузка': psutil.cpu_percent(interval=1)
    }
    
    # Информация о памяти
    memory = psutil.virtual_memory()
    info['память'] = {
        'всего': format_size(memory.total),
        'доступно': format_size(memory.available),
        'используется': format_size(memory.used),
        'процент': memory.percent
    }
    
    # Информация о диске
    disk = psutil.disk_usage('/')
    info['диск'] = {
        'всего': format_size(disk.total),
        'используется': format_size(disk.used),
        'свободно': format_size(disk.free),
        'процент': disk.percent
    }
    
    # Информация о сети
    net_io = psutil.net_io_counters()
    info['сеть'] = {
        'отправлено': format_size(net_io.bytes_sent),
        'получено': format_size(net_io.bytes_recv)
    }
    
    # Информация о GPU
    try:
        gpus = GPUtil.getGPUs()
        info['видеокарта'] = [{
            'модель': gpu.name,
            'нагрузка': gpu.load * 100,
            'память_всего': format_size(gpu.memoryTotal),
            'память_используется': format_size(gpu.memoryUsed),
            'память_свободно': format_size(gpu.memoryFree)
        } for gpu in gpus]
    except:
        info['видеокарта'] = None
    
    # Системная информация
    info['система'] = {
        'ос': platform.system(),
        'версия_ос': platform.version(),
        'имя_хоста': socket.gethostname(),
        'ip': socket.gethostbyname(socket.gethostname()),
        'версия_python': platform.python_version(),
        'время_работы_бота': format_time(time.time() - psutil.Process().create_time())
    }
    
    return info

def get_main_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🗃 База данных", callback_data="dev_database")
    kb.button(text="📨 Сообщения", callback_data="dev_messages")
    kb.button(text="👨‍💻 Разработчики", callback_data="dev_developers")
    kb.button(text="🖥️ Сервер", callback_data="dev_server")
    kb.button(text="⚠️ Ошибки", callback_data="dev_errors")
    kb.button(text="⚙️ Дополнительно", callback_data="dev_advanced")
    kb.button(text="📊 Статистика", callback_data="dev_stats")
    kb.button(text="🔧 Обслуживание", callback_data="dev_maintenance")
    kb.button(text="◀️ Назад", callback_data="admin_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_database_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Скачать", callback_data="download_db")
    kb.button(text="🔄 Сбросить", callback_data="reset_db")
    kb.button(text="🔼 Загрузить", callback_data="upload_db")
    kb.button(text="ℹ️ Статус", callback_data="db_info")
    kb.button(text="🔍 Запрос", callback_data="sql_query")
    kb.button(text="📊 Оптимизировать", callback_data="optimize_db")
    kb.button(text="◀️ Назад", callback_data="developer_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_messages_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📨 Рассылка", callback_data="broadcast_message")
    kb.button(text="📢 Объявление", callback_data="send_announcement")
    kb.button(text="📩 Тест сообщения", callback_data="test_message")
    kb.button(text="📊 Статистика", callback_data="message_stats")
    kb.button(text="◀️ Назад", callback_data="developer_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_developers_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить", callback_data="add_developer")
    kb.button(text="❌ Удалить", callback_data="remove_developer")
    kb.button(text="📋 Список", callback_data="list_developers")
    kb.button(text="🔑 Права", callback_data="dev_permissions")
    kb.button(text="◀️ Назад", callback_data="developer_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_server_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Обновить", callback_data="dev_server")
    kb.button(text="🔄 Перезапуск", callback_data="restart_bot")
    kb.button(text="🛑 Остановить", callback_data="stop_bot")
    kb.button(text="📊 Полная статистика", callback_data="full_server_stats")
    kb.button(text="🌐 Сеть", callback_data="network_info")
    kb.button(text="◀️ Назад", callback_data="developer_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_errors_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📜 Просмотр", callback_data="view_logs")
    kb.button(text="📥 Скачать", callback_data="download_logs")
    kb.button(text="🧹 Очистить", callback_data="clear_logs")
    kb.button(text="🔍 Поиск", callback_data="search_logs")
    kb.button(text="📊 Статистика", callback_data="logs_stats")
    kb.button(text="◀️ Назад", callback_data="developer_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_advanced_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="💾 Файлы", callback_data="file_manager")
    kb.button(text="🛠️ Команда", callback_data="run_command")
    kb.button(text="📜 Скрипт", callback_data="execute_script")
    kb.button(text="🌐 Удаленный скрипт", callback_data="remote_script")
    kb.button(text="📡 Вебхук", callback_data="webhook_info")
    kb.button(text="🔐 Переменные", callback_data="env_vars")
    kb.button(text="◀️ Назад", callback_data="developer_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_maintenance_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🧹 Очистка кеша", callback_data="clean_cache")
    kb.button(text="🔄 Обновление", callback_data="update_bot")
    kb.button(text="📦 Полный бэкап", callback_data="backup_all")
    kb.button(text="🛠️ Ремонт БД", callback_data="repair_db")
    kb.button(text="◀️ Назад", callback_data="developer_panel")
    kb.adjust(2)
    return kb.as_markup()

def get_confirmation_keyboard(confirm_data: str, cancel_data: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=confirm_data)
    kb.button(text="❌ Отмена", callback_data=cancel_data)
    return kb.as_markup()

@router.message(Command("developer_panel"))
async def developer_panel(message: Message):
    if not is_developer(message.from_user.id):
        await message.answer("🚫 Доступ запрещен!")
        return
    
    await message.answer(
        "💻 Панель разработчика",
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "developer_panel")
async def developer_panel_callback(callback: CallbackQuery):
    if not is_developer(callback.from_user.id):
        await callback.answer("🚫 Доступ запрещен!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💻 Панель разработчика",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

# Раздел базы данных
@router.callback_query(F.data == "dev_database")
async def dev_database(callback: CallbackQuery):
    await callback.message.edit_text(
        "🗃 Управление базой данных",
        reply_markup=get_database_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "download_db")
async def download_database(callback: CallbackQuery):
    try:
        backup_path = db.create_backup()
        file = FSInputFile(backup_path, filename=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        await callback.message.answer_document(
            document=file,
            caption="📦 Резервная копия базы данных"
        )
    except Exception as e:
        logger.error(f"Ошибка резервного копирования БД: {e}")
        await callback.message.answer("🚫 Не удалось создать резервную копию")
    await callback.answer()

@router.callback_query(F.data == "reset_db")
async def reset_database_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите сбросить базу данных?\n"
        "Это действие нельзя отменить! Все данные будут удалены!",
        reply_markup=get_confirmation_keyboard("confirm_reset_db", "dev_database")
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_reset_db")
async def reset_database(callback: CallbackQuery):
    try:
        db.reset_database()
        await callback.message.edit_text("✅ База данных успешно сброшена!")
    except Exception as e:
        logger.error(f"Ошибка сброса БД: {e}")
        await callback.message.edit_text("🚫 Не удалось сбросить базу данных!")
    await callback.answer()

@router.callback_query(F.data == "upload_db")
async def upload_database_start(callback: CallbackQuery):
    await callback.message.edit_text(
        "📤 Отправьте файл базы данных (.db):",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_database").as_markup()
    )
    await callback.answer()

@router.message(F.document)
async def upload_database_process(message: Message):
    if not is_developer(message.from_user.id):
        return
    
    document = message.document
    if not document.file_name.endswith('.db'):
        await message.answer("🚫 Файл должен иметь расширение .db!")
        return
    
    try:
        temp_path = os.path.join(config.DB_BACKUP_DIR, "temp_upload.db")
        await message.bot.download(document, destination=temp_path)
        
        try:
            test_conn = sqlite3.connect(temp_path)
            test_conn.close()
        except sqlite3.Error:
            os.remove(temp_path)
            await message.answer("🚫 Неверный формат базы данных")
            return
        
        await message.answer("⏳ Загрузка базы данных... Бот будет перезапущен")
        shutil.move(temp_path, config.DB_NAME)
        python = sys.executable
        os.execl(python, python, *sys.argv)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки БД: {e}")
        await message.answer("🚫 Не удалось загрузить базу данных")

@router.callback_query(F.data == "db_info")
async def database_info(callback: CallbackQuery):
    try:
        db_size = os.path.getsize(config.DB_NAME)
        db_created = datetime.fromtimestamp(os.path.getctime(config.DB_NAME)).strftime('%Y-%m-%d %H:%M:%S')
        db_modified = datetime.fromtimestamp(os.path.getmtime(config.DB_NAME)).strftime('%Y-%m-%d %H:%M:%S')
        
        stats = db.get_user_stats()
        
        text = "ℹ️ Информация о базе данных:\n\n"
        text += f"📊 Размер: {format_size(db_size)}\n"
        text += f"📅 Создана: {db_created}\n"
        text += f"🔄 Изменена: {db_modified}\n"
        text += f"👥 Пользователи: {stats['total_users']} (Активных: {stats['active_users']})\n"
        text += f"🔗 Ссылки: {stats['total_links']} (Переходов: {stats['total_link_visits']})\n"
        text += f"📝 Логи: {db.count_logs()}\n"
        text += f"📂 Путь: {os.path.abspath(config.DB_NAME)}"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_database_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка получения информации о БД: {e}")
        await callback.message.edit_text(
            "🚫 Не удалось получить информацию о базе данных",
            reply_markup=get_database_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "sql_query")
async def sql_query_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_sql_query)
    await callback.message.edit_text(
        "🔍 Введите SQL запрос (только для чтения):",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_database").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_sql_query)
async def sql_query_execute(message: Message, state: FSMContext):
    query = message.text.strip()
    
    # Защита от опасных запросов
    if any(word in query.upper() for word in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"]):
        await message.answer("🚫 Разрешены только SELECT запросы!")
        await state.clear()
        return
    
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            results = cursor.fetchall()
            if not results:
                await message.answer("✅ Запрос выполнен. Результатов нет.")
                return
            
            # Форматирование результатов
            columns = [description[0] for description in cursor.description]
            formatted = "\n".join([f"{col}: {row[i]}" for row in results[:5] for i, col in enumerate(columns)])
            
            if len(results) > 5:
                formatted += f"\n\n...и еще {len(results)-5} строк"
            
            await message.answer(f"🔍 Результаты запроса (первые 5 строк):\n\n<code>{formatted}</code>", parse_mode="HTML")
    
    except Exception as e:
        await message.answer(f"🚫 Ошибка запроса: {str(e)}")
    
    await state.clear()

@router.callback_query(F.data == "optimize_db")
async def optimize_database(callback: CallbackQuery):
    try:
        with db._get_connection() as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            conn.commit()
        
        await callback.message.edit_text("✅ База данных оптимизирована!")
    except Exception as e:
        logger.error(f"Ошибка оптимизации БД: {e}")
        await callback.message.edit_text("🚫 Не удалось оптимизировать базу данных!")
    await callback.answer()

# Раздел сообщений
@router.callback_query(F.data == "dev_messages")
async def dev_messages(callback: CallbackQuery):
    await callback.message.edit_text(
        "📨 Управление сообщениями",
        reply_markup=get_messages_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "broadcast_message")
async def broadcast_message_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_broadcast)
    await callback.message.edit_text(
        "📨 Введите сообщение для рассылки всем пользователям:",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_messages").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_broadcast)
async def broadcast_message_process(message: Message, state: FSMContext):
    users = db.get_all_users()
    total = len(users)
    success = 0
    failed = 0
    
    progress_msg = await message.answer(f"⏳ Рассылка для {total} пользователей...")
    
    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user['user_id'],
                text=message.text
            )
            success += 1
            
            if success % 10 == 0:
                await progress_msg.edit_text(
                    f"⏳ Прогресс: {success + failed}/{total}\n"
                    f"✅ Успешно: {success}\n"
                    f"🚫 Ошибки: {failed}"
                )
            
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Ошибка рассылки для пользователя {user['user_id']}: {e}")
            failed += 1
    
    db.add_system_message(message.text, message.from_user.id, success)
    
    await progress_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📤 Всего отправлено: {total}\n"
        f"✅ Успешно: {success}\n"
        f"🚫 Ошибки: {failed}"
    )
    await state.clear()

@router.callback_query(F.data == "send_announcement")
async def send_announcement_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_announcement)
    await callback.message.edit_text(
        "📢 Введите текст объявления (будет закреплено в чатах/каналах):",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_messages").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_announcement)
async def send_announcement_process(message: Message, state: FSMContext):
    # Здесь должна быть реализация отправки в каналы
    await message.answer("✅ Объявление подготовлено (нужна реализация для каналов)")
    await state.clear()

@router.callback_query(F.data == "test_message")
async def test_message(callback: CallbackQuery):
    try:
        await callback.bot.send_message(
            chat_id=callback.from_user.id,
            text="📩 Это тестовое сообщение от панели разработчика"
        )
        await callback.answer("✅ Тестовое сообщение отправлено!")
    except Exception as e:
        logger.error(f"Ошибка тестового сообщения: {e}")
        await callback.answer("🚫 Не удалось отправить тестовое сообщение")

@router.callback_query(F.data == "message_stats")
async def message_stats(callback: CallbackQuery):
    stats = db.get_user_stats()
    messages = db.get_all_system_messages()
    
    text = "📊 Статистика сообщений:\n\n"
    text += f"📨 Всего сообщений: {stats.get('total_messages', 0)}\n"
    text += f"📤 Получателей последней рассылки: {stats.get('last_broadcast_recipients', 0)}\n"
    
    if messages:
        last_msg = messages[0]
        text += f"\n📝 Последнее сообщение:\n"
        text += f"Дата: {last_msg['sent_date']}\n"
        text += f"Получатели: {last_msg['recipients_count']}\n"
        text += f"Текст: {last_msg['message_text'][:100]}..."
    
    await callback.message.edit_text(text, reply_markup=get_messages_keyboard())
    await callback.answer()

# Раздел разработчиков
@router.callback_query(F.data == "dev_developers")
async def dev_developers(callback: CallbackQuery):
    try:
        # Получаем список ID разработчиков из конфига
        developers = config.DEVELOPER_IDS
        
        # Добавляем главного админа, если его нет в списке
        if config.ADMIN_ID not in developers:
            developers.append(config.ADMIN_ID)
        
        text = "👨‍💻 Список разработчиков:\n\n"
        
        for i, dev_id in enumerate(developers, 1):
            user = db.get_user(dev_id)
            if user:
                username = f"@{user['username']}" if user.get('username') else "нет юзернейма"
                text += f"{i}. ID: {dev_id} | Юзернейм: {username}\n"
            else:
                text += f"{i}. ID: {dev_id} | Пользователь не найден в БД\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_developers_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка разработчиков: {e}")
        await callback.message.edit_text(
            "🚫 Не удалось получить список разработчиков",
            reply_markup=get_developers_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "add_developer")
async def add_developer_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_developer_id)
    await callback.message.edit_text(
        "👨‍💻 Введите ID пользователя для добавления в разработчики:",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_developers").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_developer_id)
async def add_developer_process(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("🚫 Пользователь не найден!")
            await state.clear()
            return
            
        if user_id in config.DEVELOPER_IDS:
            await message.answer("ℹ️ Этот пользователь уже разработчик")
            await state.clear()
            return
            
        # В реальной реализации нужно обновить конфиг/БД
        await message.answer(f"✅ Пользователь {user_id} добавлен в разработчики (нужно обновить конфиг)")
        
    except ValueError:
        await message.answer("🚫 Неверный формат ID пользователя")
    
    await state.clear()

@router.callback_query(F.data == "remove_developer")
async def remove_developer_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_developer_id)
    await callback.message.edit_text(
        "👨‍💻 Введите ID пользователя для удаления из разработчиков:",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_developers").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_developer_id)
async def remove_developer_process(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        
        if user_id == config.ADMIN_ID:
            await message.answer("🚫 Нельзя удалить главного админа!")
            await state.clear()
            return
            
        if user_id not in config.DEVELOPER_IDS:
            await message.answer("ℹ️ Этот пользователь не разработчик")
            await state.clear()
            return
            
        # В реальной реализации нужно обновить конфиг/БД
        await message.answer(f"✅ Пользователь {user_id} удален из разработчиков (нужно обновить конфиг)")
        
    except ValueError:
        await message.answer("🚫 Неверный формат ID пользователя")
    
    await state.clear()

@router.callback_query(F.data == "dev_permissions")
async def dev_permissions(callback: CallbackQuery):
    text = "🔑 Права разработчиков:\n\n"
    text += "• Полный доступ ко всем функциям бота\n"
    text += "• Управление базой данных\n"
    text += "• Контроль сервера\n"
    text += "• Рассылка сообщений\n"
    text += "• Обслуживание системы\n"
    
    await callback.message.edit_text(text, reply_markup=get_developers_keyboard())
    await callback.answer()

# Раздел сервера
@router.callback_query(F.data == "dev_server")
async def dev_server(callback: CallbackQuery):
    try:
        info = get_system_info()
        
        text = "🖥️ Состояние сервера:\n\n"
        text += f"⏱ Время работы: {info['система']['время_работы_бота']}\n"
        text += f"🖥 CPU: {info['cpu']['модель']} ({info['cpu']['ядра']} ядер, {info['cpu']['нагрузка']}%)\n"
        text += f"🧠 RAM: {info['память']['используется']}/{info['память']['всего']} ({info['память']['процент']}%)\n"
        text += f"💾 Диск: {info['диск']['используется']}/{info['диск']['всего']} ({info['диск']['процент']}%)\n"
        
        if info['видеокарта']:
            text += f"🎮 GPU: {info['видеокарта'][0]['модель']} ({info['видеокарта'][0]['нагрузка']:.1f}%)\n"
        
        text += f"🌐 Сеть: ↑{info['сеть']['отправлено']} ↓{info['сеть']['получено']}"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_server_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка получения состояния сервера: {e}")
        await callback.message.edit_text(
            "🚫 Ошибка получения состояния сервера!",
            reply_markup=get_server_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "full_server_stats")
async def full_server_stats(callback: CallbackQuery):
    try:
        info = get_system_info()
        
        text = "📊 Полная статистика сервера:\n\n"
        text += f"💻 Имя сервера: {info['система']['имя_хоста']}\n"
        text += f"🖥 ОС: {info['система']['ос']} {info['система']['версия_ос']}\n"
        text += f"🐍 Python: {info['система']['версия_python']}\n"
        text += f"⏱ Время работы: {info['система']['время_работы_бота']}\n\n"
        
        text += "🖥 Подробнее о CPU:\n"
        text += f"• Модель: {info['cpu']['модель']}\n"
        text += f"• Ядра: {info['cpu']['ядра']} физических, {info['cpu']['потоки']} логических\n"
        text += f"• Нагрузка: {info['cpu']['нагрузка']}%\n\n"
        
        text += "🧠 Подробнее о памяти:\n"
        text += f"• Всего: {info['память']['всего']}\n"
        text += f"• Используется: {info['память']['используется']} ({info['память']['процент']}%)\n"
        text += f"• Доступно: {info['память']['доступно']}\n\n"
        
        if info['видеокарта']:
            text += "🎮 Подробнее о видеокарте:\n"
            for gpu in info['видеокарта']:
                text += f"• {gpu['модель']}: {gpu['нагрузка']:.1f}% нагрузки\n"
                text += f"  Память: {gpu['память_используется']}/{gpu['память_всего']}\n"
        
        await callback.message.answer(text)
    except Exception as e:
        logger.error(f"Ошибка полной статистики сервера: {e}")
        await callback.answer("🚫 Ошибка получения полной статистики!")
    await callback.answer()

@router.callback_query(F.data == "network_info")
async def network_info(callback: CallbackQuery):
    try:
        info = get_system_info()
        net_io = psutil.net_io_counters()
        net_if = psutil.net_if_addrs()
        
        text = "🌐 Сетевая информация:\n\n"
        text += f"🖥 Имя сервера: {info['система']['имя_хоста']}\n"
        text += f"📡 IP: {info['система']['ip']}\n\n"
        text += "📊 Трафик:\n"
        text += f"• Отправлено: {info['сеть']['отправлено']}\n"
        text += f"• Получено: {info['сеть']['получено']}\n\n"
        text += "🔌 Интерфейсы:\n"
        
        for interface, addrs in net_if.items():
            text += f"• {interface}:\n"
            for addr in addrs:
                text += f"  - {addr.family.name}: {addr.address}\n"
        
        await callback.message.answer(text)
    except Exception as e:
        logger.error(f"Ошибка сетевой информации: {e}")
        await callback.answer("🚫 Ошибка получения сетевой информации!")
    await callback.answer()

@router.callback_query(F.data == "restart_bot")
async def restart_bot_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите перезапустить бота?",
        reply_markup=get_confirmation_keyboard("confirm_restart_bot", "dev_server")
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_restart_bot")
async def restart_bot(callback: CallbackQuery):
    await callback.message.edit_text("🔄 Перезапуск...")
    await callback.answer()
    python = sys.executable
    os.execl(python, python, *sys.argv)

@router.callback_query(F.data == "stop_bot")
async def stop_bot_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите остановить бота?\n"
        "Бот останется остановленным до ручного запуска!",
        reply_markup=get_confirmation_keyboard("confirm_stop_bot", "dev_server")
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_stop_bot")
async def stop_bot(callback: CallbackQuery):
    await callback.message.edit_text("🛑 Остановка бота...")
    await callback.answer()
    os._exit(0)

# Раздел ошибок
@router.callback_query(F.data == "dev_errors")
async def dev_errors(callback: CallbackQuery):
    try:
        log_stats = {
            'total': db.count_logs(),
            'critical': db.count_logs('CRITICAL'),
            'error': db.count_logs('ERROR'),
            'warning': db.count_logs('WARNING'),
            'info': db.count_logs('INFO'),
            'debug': db.count_logs('DEBUG')
        }
        
        log_size = os.path.getsize(config.LOGS_FILE) if os.path.exists(config.LOGS_FILE) else 0
        
        text = "⚠️ Логи ошибок:\n\n"
        text += f"📊 Всего: {log_stats['total']}\n"
        text += f"🔴 Критические: {log_stats['critical']}\n"
        text += f"🟠 Ошибки: {log_stats['error']}\n"
        text += f"🟡 Предупреждения: {log_stats['warning']}\n"
        text += f"🟢 Инфо: {log_stats['info']}\n"
        text += f"🔵 Отладка: {log_stats['debug']}\n"
        text += f"📁 Размер файла: {format_size(log_size)}"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_errors_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка получения информации о логах: {e}")
        await callback.message.edit_text(
            "🚫 Не удалось получить информацию о логах!",
            reply_markup=get_errors_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "view_logs")
async def view_logs(callback: CallbackQuery):
    try:
        if not os.path.exists(config.LOGS_FILE):
            await callback.message.edit_text(
                "Файл логов не найден!",
                reply_markup=get_errors_keyboard()
            )
            return
        
        with open(config.LOGS_FILE, 'r', encoding='utf-8') as f:
            logs = f.read()
        
        if len(logs) > 4000:
            logs = logs[-4000:]
        
        await callback.message.edit_text(
            f"📜 Последние логи:\n\n<code>{logs}</code>",
            reply_markup=get_errors_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка чтения логов: {e}")
        await callback.message.edit_text(
            "🚫 Не удалось прочитать логи!",
            reply_markup=get_errors_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "download_logs")
async def download_logs(callback: CallbackQuery):
    try:
        if not os.path.exists(config.LOGS_FILE):
            await callback.answer("Файл логов не найден!", show_alert=True)
            return
        
        file = FSInputFile(config.LOGS_FILE, filename="bot_logs.log")
        await callback.message.answer_document(
            document=file,
            caption="📜 Логи бота"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки логов: {e}")
        await callback.message.answer("🚫 Не удалось отправить логи")
    await callback.answer()

@router.callback_query(F.data == "clear_logs")
async def clear_logs_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите очистить все логи?\n"
        "Это действие нельзя отменить! Все логи будут удалены!",
        reply_markup=get_confirmation_keyboard("confirm_clear_logs", "dev_errors")
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_clear_logs")
async def clear_logs(callback: CallbackQuery):
    try:
        db.clear_logs()
        if os.path.exists(config.LOGS_FILE):
            with open(config.LOGS_FILE, 'w'):
                pass
        
        await callback.message.edit_text("✅ Логи успешно очищены!")
    except Exception as e:
        logger.error(f"Ошибка очистки логов: {e}")
        await callback.message.edit_text("🚫 Ошибка очистки логов!")
    await callback.answer()

@router.callback_query(F.data == "search_logs")
async def search_logs_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_log_search)
    await callback.message.edit_text(
        "🔍 Введите текст для поиска в логах:",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_errors").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_log_search)
async def search_logs_process(message: Message, state: FSMContext):
    term = message.text.strip()
    
    try:
        logs = db.get_logs_by_search(term)
        
        if not logs:
            await message.answer("🔍 Логов по вашему запросу не найдено")
            await state.clear()
            return
            
        formatted = "\n".join([
            f"{log['timestamp']} [{log['level']}]: {log['message'][:100]}"
            for log in logs[:5]
        ])
        
        if len(logs) > 5:
            formatted += f"\n\n...и еще {len(logs)-5} записей"
        
        await message.answer(f"🔍 Результаты поиска:\n\n<code>{formatted}</code>", parse_mode="HTML")
        
    except Exception as e:
        await message.answer(f"🚫 Ошибка поиска: {str(e)}")
    
    await state.clear()

@router.callback_query(F.data == "logs_stats")
async def logs_stats(callback: CallbackQuery):
    try:
        stats = {
            'total': db.count_logs(),
            'last_hour': db.count_logs_since(datetime.now() - timedelta(hours=1)),
            'last_day': db.count_logs_since(datetime.now() - timedelta(days=1)),
            'last_week': db.count_logs_since(datetime.now() - timedelta(weeks=1)),
        }
        
        text = "📊 Статистика логов:\n\n"
        text += f"📈 Всего логов: {stats['total']}\n"
        text += f"⏱ За последний час: {stats['last_hour']}\n"
        text += f"📅 За последние 24 часа: {stats['last_day']}\n"
        text += f"🗓 За последнюю неделю: {stats['last_week']}\n"
        
        await callback.message.edit_text(text, reply_markup=get_errors_keyboard())
    except Exception as e:
        logger.error(f"Ошибка статистики логов: {e}")
        await callback.answer("🚫 Ошибка получения статистики логов!")
    await callback.answer()

# Дополнительные инструменты
@router.callback_query(F.data == "dev_advanced")
async def dev_advanced(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ Дополнительные инструменты",
        reply_markup=get_advanced_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "file_manager")
async def file_manager(callback: CallbackQuery):
    try:
        files = os.listdir('.')
        text = "📁 Файловый менеджер (текущая директория):\n\n"
        
        for i, file in enumerate(files[:10], 1):
            size = os.path.getsize(file)
            text += f"{i}. {file} ({format_size(size)})\n"
        
        if len(files) > 10:
            text += f"\n...и еще {len(files)-10} файлов"
        
        await callback.message.edit_text(text)
    except Exception as e:
        logger.error(f"Ошибка файлового менеджера: {e}")
        await callback.answer("🚫 Ошибка доступа к файлам!")
    await callback.answer()

@router.callback_query(F.data == "run_command")
async def run_command_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_command)
    await callback.message.edit_text(
        "⌨️ Введите команду для выполнения (только безопасные команды):",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_advanced").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_command)
async def run_command_process(message: Message, state: FSMContext):
    cmd = message.text.strip()
    
    # Белый список разрешенных команд для безопасности
    ALLOWED_COMMANDS = ['ls', 'pwd', 'df', 'free', 'uptime', 'date', 'whoami']
    
    if not any(cmd.startswith(allowed) for allowed in ALLOWED_COMMANDS):
        await message.answer("🚫 Команда запрещена из соображений безопасности!")
        await state.clear()
        return
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        output = result.stdout or result.stderr or "Нет вывода"
        
        if len(output) > 4000:
            output = output[:2000] + "\n...\n" + output[-2000:]
        
        await message.answer(f"⌨️ Результаты команды:\n\n<code>{output}</code>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"🚫 Ошибка выполнения команды: {str(e)}")
    
    await state.clear()

@router.callback_query(F.data == "execute_script")
async def execute_script_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_script)
    await callback.message.edit_text(
        "📜 Отправьте файл Python скрипта для выполнения (макс. 10КБ):",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_advanced").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_script, F.document)
async def execute_script_process(message: Message, state: FSMContext):
    if not message.document.file_name.endswith('.py'):
        await message.answer("🚫 Разрешены только файлы .py!")
        await state.clear()
        return
    
    if message.document.file_size > 10 * 1024:  # Лимит 10КБ
        await message.answer("🚫 Файл слишком большой (макс. 10КБ)!")
        await state.clear()
        return
    
    try:
        temp_path = f"temp_{uuid.uuid4().hex}.py"
        await message.bot.download(message.document, destination=temp_path)
        
        # Проверка безопасности
        with open(temp_path, 'r') as f:
            content = f.read()
            if any(banned in content for banned in ['import os', 'import sys', 'subprocess']):
                os.remove(temp_path)
                await message.answer("🚫 Скрипт содержит запрещенные импорты!")
                await state.clear()
                return
        
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout or result.stderr or "Нет вывода"
        
        if len(output) > 4000:
            output = output[:2000] + "\n...\n" + output[-2000:]
        
        await message.answer(f"📜 Результаты скрипта:\n\n<code>{output}</code>", parse_mode="HTML")
        
        os.remove(temp_path)
    except Exception as e:
        await message.answer(f"🚫 Ошибка выполнения скрипта: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    await state.clear()

@router.callback_query(F.data == "remote_script")
async def remote_script_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DeveloperStates.waiting_for_script)
    await callback.message.edit_text(
        "🌐 Введите URL удаленного скрипта (только из доверенных источников):",
        reply_markup=InlineKeyboardBuilder().button(text="◀️ Назад", callback_data="dev_advanced").as_markup()
    )
    await callback.answer()

@router.message(DeveloperStates.waiting_for_script)
async def remote_script_process(message: Message, state: FSMContext):
    url = message.text.strip()
    
    if not url.startswith(('http://', 'https://')):
        await message.answer("🚫 Неверный формат URL!")
        await state.clear()
        return
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        if len(response.content) > 10 * 1024:  # Лимит 10КБ
            await message.answer("🚫 Скрипт слишком большой (макс. 10КБ)!")
            await state.clear()
            return
            
        temp_path = f"temp_{uuid.uuid4().hex}.py"
        with open(temp_path, 'w') as f:
            f.write(response.text)
        
        # Проверка безопасности
        if any(banned in response.text for banned in ['import os', 'import sys', 'subprocess']):
            os.remove(temp_path)
            await message.answer("🚫 Скрипт содержит запрещенные импорты!")
            await state.clear()
            return
        
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout or result.stderr or "Нет вывода"
        
        if len(output) > 4000:
            output = output[:2000] + "\n...\n" + output[-2000:]
        
        await message.answer(f"🌐 Результаты удаленного скрипта:\n\n<code>{output}</code>", parse_mode="HTML")
        
        os.remove(temp_path)
    except Exception as e:
        await message.answer(f"🚫 Ошибка удаленного скрипта: {str(e)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    await state.clear()

@router.callback_query(F.data == "webhook_info")
async def webhook_info(callback: CallbackQuery):
    try:
        webhook_info = await callback.bot.get_webhook_info()
        
        text = "📡 Информация о вебхуке:\n\n"
        text += f"🔗 URL: {webhook_info.url or 'Не установлен'}\n"
        text += f"🔄 Ожидающие обновления: {webhook_info.pending_update_count}\n"
        text += f"⏱ Последняя ошибка: {webhook_info.last_error_date or 'Никогда'}\n"
        text += f"⚠️ Сообщение ошибки: {webhook_info.last_error_message or 'Нет'}"
        
        await callback.message.edit_text(text)
    except Exception as e:
        logger.error(f"Ошибка информации о вебхуке: {e}")
        await callback.answer("🚫 Ошибка получения информации о вебхуке!")
    await callback.answer()

@router.callback_query(F.data == "env_vars")
async def env_vars(callback: CallbackQuery):
    try:
        env_vars = {
            'BOT_TOKEN': '***' + config.BOT_TOKEN[-3:] if config.BOT_TOKEN else 'Не установлен',
            'ADMIN_ID': config.ADMIN_ID,
            'DEVELOPER_IDS': config.DEVELOPER_IDS,
            'DB_NAME': config.DB_NAME,
            'LOGS_DIR': config.LOGS_DIR
        }
        
        text = "🔐 Переменные окружения:\n\n"
        for key, value in env_vars.items():
            text += f"{key}: {value}\n"
        
        await callback.message.edit_text(text)
    except Exception as e:
        logger.error(f"Ошибка переменных окружения: {e}")
        await callback.answer("🚫 Ошибка получения переменных окружения!")
    await callback.answer()

# Раздел статистики
@router.callback_query(F.data == "dev_stats")
async def dev_stats(callback: CallbackQuery):
    try:
        stats = db.get_user_stats()
        
        text = "📊 Статистика бота:\n\n"
        text += f"👥 Пользователи: {stats['total_users']} (Активных: {stats['active_users']})\n"
        text += f"🔗 Ссылки: {stats['total_links']} (Переходов: {stats['total_link_visits']})\n"
        text += f"📝 Жалобы: {stats['total_reports']} (Открытых: {stats['open_reports']})\n"
        text += f"📢 Каналы: {stats['subscription_channels']}\n"
        text += f"📨 Сообщения: {stats.get('total_messages', 0)}\n"
        text += f"📜 Логи: {db.count_logs()}"
        
        await callback.message.edit_text(text)
    except Exception as e:
        logger.error(f"Ошибка статистики: {e}")
        await callback.answer("🚫 Ошибка получения статистики!")
    await callback.answer()

# Раздел обслуживания
@router.callback_query(F.data == "dev_maintenance")
async def dev_maintenance(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔧 Инструменты обслуживания",
        reply_markup=get_maintenance_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "clean_cache")
async def clean_cache(callback: CallbackQuery):
    try:
        # Очистка кеша Python
        for root, dirs, files in os.walk('.'):
            for dir in dirs:
                if dir == '__pycache__':
                    shutil.rmtree(os.path.join(root, dir))
        
        await callback.message.edit_text("✅ Кеш успешно очищен!")
    except Exception as e:
        logger.error(f"Ошибка очистки кеша: {e}")
        await callback.message.edit_text("🚫 Ошибка очистки кеша!")
    await callback.answer()

@router.callback_query(F.data == "update_bot")
async def update_bot_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите обновить бота?\n"
        "Это загрузит последние изменения из Git и перезапустит бота.",
        reply_markup=get_confirmation_keyboard("confirm_update_bot", "dev_maintenance")
    )
    await callback.answer()

@router.callback_query(F.data == "confirm_update_bot")
async def update_bot(callback: CallbackQuery):
    try:
        result = subprocess.run(
            ['git', 'pull'],
            capture_output=True,
            text=True
        )
        
        output = result.stdout or result.stderr or "Нет вывода"
        
        if len(output) > 4000:
            output = output[:2000] + "\n...\n" + output[-2000:]
        
        await callback.message.edit_text(
            f"🔄 Результаты обновления:\n\n<code>{output}</code>\n\nПерезапуск бота...",
            parse_mode="HTML"
        )
        
        python = sys.executable
        os.execl(python, python, *sys.argv)
    except Exception as e:
        logger.error(f"Ошибка обновления: {e}")
        await callback.message.edit_text(f"🚫 Ошибка обновления: {str(e)}")
    await callback.answer()

@router.callback_query(F.data == "backup_all")
async def backup_all(callback: CallbackQuery):
    try:
        # Создание директории для бэкапа
        backup_dir = f"backups/full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Бэкап базы данных
        db_backup_path = db.create_backup()
        shutil.move(db_backup_path, os.path.join(backup_dir, os.path.basename(db_backup_path)))
        
        # Бэкап логов
        if os.path.exists(config.LOGS_FILE):
            shutil.copy(config.LOGS_FILE, backup_dir)
        
        # Бэкап конфига
        if os.path.exists('.env'):
            shutil.copy('.env', backup_dir)
        
        # Создание zip-архива
        shutil.make_archive(backup_dir, 'zip', backup_dir)
        
        # Отправка бэкапа
        file = FSInputFile(f"{backup_dir}.zip", filename=f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
        await callback.message.answer_document(
            document=file,
            caption="📦 Полный бэкап"
        )
        
        # Очистка
        shutil.rmtree(backup_dir)
        os.remove(f"{backup_dir}.zip")
    except Exception as e:
        logger.error(f"Ошибка бэкапа: {e}")
        await callback.message.answer("🚫 Не удалось создать бэкап!")
    await callback.answer()

@router.callback_query(F.data == "repair_db")
async def repair_db(callback: CallbackQuery):
    try:
        # Сначала создаем бэкап
        backup_path = db.create_backup()
        
        # Проверка целостности
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            if result and result[0] == 'ok':
                await callback.message.edit_text("✅ Целостность базы данных подтверждена - ошибок не найдено!")
            else:
                # Попытка восстановления
                cursor.execute("REINDEX")
                cursor.execute("VACUUM")
                conn.commit()
                await callback.message.edit_text("🛠️ База данных успешно восстановлена!")
    except Exception as e:
        logger.error(f"Ошибка восстановления БД: {e}")
        await callback.message.edit_text("🚫 Не удалось восстановить базу данных!")
    await callback.answer()

developer_router = router