import sqlite3
from contextlib import contextmanager
from datetime import datetime
import os
from aiogram import Bot
from typing import Optional, Union, List, Dict, Any
from config import config
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name: str = config.DB_NAME):
        self.db_name = db_name
        self._ensure_db_exists()
        self._create_backup_dir()
    
    def _get_connection(self):
        """Получить соединение с базой данных"""
        return sqlite3.connect(self.db_name)
    
    def _ensure_db_exists(self):
        """Ensure database file and tables exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
        
        # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    join_date TEXT,
                    last_active TEXT,
                    is_banned INTEGER DEFAULT 0,
                    ban_reason TEXT,
                    banned_by INTEGER,
                    ban_date TEXT,
                    link_visits INTEGER DEFAULT 0
                )
            ''')
        
        # Links table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS links (
                    link_code TEXT PRIMARY KEY,
                    content_type TEXT NOT NULL,
                    content_text TEXT,
                    content_file_id TEXT,
                    created_by INTEGER NOT NULL,
                    creation_date TEXT NOT NULL,
                    visits INTEGER DEFAULT 0,
                    last_visit TEXT
                )
            ''')
        
        # Admins table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    added_by INTEGER,
                    added_date TEXT
                )
            ''')
        
        # Reports table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    message TEXT,
                    report_date TEXT,
                    status TEXT DEFAULT 'open',
                    answer TEXT
                )
            ''')
        
        # Subscription channels table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS subscription_channels (
                    channel_id INTEGER PRIMARY KEY,
                    username TEXT,
                    title TEXT,
                    added_by INTEGER,
                    added_date TEXT,
                    check_type INTEGER DEFAULT 1,
                    subscribers_count INTEGER DEFAULT 0
                )
            ''')
        
        # System messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_text TEXT,
                    sent_by INTEGER,
                    sent_date TEXT,
                    recipients_count INTEGER
                )
            ''')
        
        # Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    message TEXT,
                    timestamp TEXT,
                    traceback TEXT
                )
            ''')
        
        # Developers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS developers (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    added_by INTEGER,
                    added_date TEXT
                )
            ''')
        
        # Broadcasts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    send_date TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    message_text TEXT
                )
            ''')
        
        # User activity table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activity_date TEXT NOT NULL,
                    activity_type TEXT NOT NULL
                )
            ''')
        
        # User settings table - исправленная версия
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link_limit INTEGER DEFAULT 10,
                    report_limit INTEGER DEFAULT 5,
                    report_cooldown INTEGER DEFAULT 5
                )
            ''')
        
        # Report settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS report_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    auto_close INTEGER DEFAULT 0,
                    notifications INTEGER DEFAULT 1
                )
            ''')
        
        # Insert default settings if tables are empty
            cursor.execute('SELECT 1 FROM user_settings LIMIT 1')
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO user_settings 
                    (link_limit, report_limit, report_cooldown)
                    VALUES (10, 5, 5)
                ''')
            
            cursor.execute('SELECT 1 FROM report_settings LIMIT 1')
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO report_settings 
                    (auto_close, notifications)
                    VALUES (0, 1)
                ''')
            
            conn.commit()
    
    def _create_backup_dir(self):
        """Create backup directory if it doesn't exist"""
        Path(config.DB_BACKUP_DIR).mkdir(exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with context manager"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _recreate_user_settings_table(self):
        """Recreate user_settings table with correct structure"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('DROP TABLE IF EXISTS user_settings')
                cursor.execute('''
                    CREATE TABLE user_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        link_limit INTEGER DEFAULT 10,
                        report_limit INTEGER DEFAULT 5,
                        report_cooldown INTEGER DEFAULT 5
                    )
                ''')
                cursor.execute('''
                    INSERT INTO user_settings 
                    (link_limit, report_limit, report_cooldown)
                    VALUES (10, 5, 5)
                ''')
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Error recreating user_settings table: {e}")
                conn.rollback()
    
    async def check_inactive_subscriptions(self, bot: Bot) -> List[Dict[str, Any]]:
        """Проверяет подписки пользователей и возвращает список неактивных"""
        inactive_users = []
    
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
            
            # Получаем все каналы
                cursor.execute('SELECT channel_id FROM subscription_channels')
                channels = [row['channel_id'] for row in cursor.fetchall()]
            
                if not channels:
                    return []
            
            # Получаем всех активных пользователей
                cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
                users = [row['user_id'] for row in cursor.fetchall()]
            
                for user_id in users:
                    try:
                        for channel_id in channels:
                        # Проверяем подписку пользователя
                            member = await bot.get_chat_member(
                                chat_id=channel_id,
                                user_id=user_id
                            )
                            if member.status not in ['member', 'administrator', 'creator']:
                                inactive_users.append({'user_id': user_id})
                                break
                    except Exception as e:
                        logger.error(f"Error checking subscription for user {user_id}: {e}")
                        continue
                    
        except Exception as e:
            logger.error(f"Database error in check_subscriptions: {e}")
    
        return inactive_users
    
    # User methods
    def get_user_settings(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
            # Проверяем существование колонок
                cursor.execute("PRAGMA table_info(user_settings)")
                columns = [col[1] for col in cursor.fetchall()]
            
            # Если таблица пуста или нет нужных колонок - пересоздаем
                if not columns or 'report_cooldown' not in columns:
                    self._recreate_user_settings_table()
                    return {
                        'link_limit': 10,
                        'report_limit': 5,
                        'report_cooldown': 5
                    }
            
                cursor.execute('''
                    SELECT link_limit, report_limit, report_cooldown 
                    FROM user_settings LIMIT 1
                ''')
                row = cursor.fetchone()
            
                return {
                    'link_limit': row[0] if row else 10,
                    'report_limit': row[1] if row else 5,
                    'report_cooldown': row[2] if row else 5
                }
            
            except sqlite3.Error as e:
                logger.error(f"Error getting user settings: {e}")
                return {
                    'link_limit': 10,
                    'report_limit': 5,
                    'report_cooldown': 5
                }
    
    def update_user_setting(self, setting_name: str, value: int) -> bool:
        valid_settings = ['link_limit', 'report_limit', 'report_cooldown']
        if setting_name not in valid_settings:
            return False
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
            # Проверяем существование колонки
                cursor.execute(f'''
                    SELECT 1 FROM pragma_table_info('user_settings') 
                    WHERE name = ?
                ''', (setting_name,))
                if not cursor.fetchone():
                    return False
                
                cursor.execute(f'''
                    UPDATE user_settings SET {setting_name} = ?
                ''', (value,))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error updating user setting: {e}")
                return False
    
    def count_user_reports(self, user_id: int) -> int:
        """Подсчет жалоб пользователя"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM reports WHERE user_id = ?', (user_id,))
            return cursor.fetchone()[0]

    def get_old_open_reports(self, user_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """Получить старые открытые жалобы пользователя"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM reports 
                WHERE user_id = ? 
                AND status = 'open' 
                AND report_date <= datetime('now', ?)
            ''', (user_id, f'-{days} days'))
            return [dict(row) for row in cursor.fetchall()]

    def close_report(self, report_id: int) -> bool:
        """Закрыть жалобу"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reports SET status = 'closed' WHERE report_id = ?
            ''', (report_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_last_user_report(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM reports 
                WHERE user_id = ? 
                ORDER BY report_date DESC 
                LIMIT 1
            ''', (user_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, join_date, last_active)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (user_id, username, first_name, last_name))
            conn.commit()
    
    def update_user_activity(self, user_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET last_active = datetime('now') WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            if result:
                return dict(result)
            return None
    
    def check_user_subscription(self, user_id: int, channel_id: int) -> bool:
        """Проверяет, подписан ли пользователь на канал"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM user_subscriptions 
                WHERE user_id = ? AND channel_id = ?
            ''', (user_id, channel_id))
            return cursor.fetchone() is not None
    
    def ban_user(self, user_id: int, reason: str, banned_by: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_banned = 1, ban_reason = ?, banned_by = ?, ban_date = datetime('now')
                WHERE user_id = ?
            ''', (reason, banned_by, user_id))
            conn.commit()
    
    def unban_user(self, user_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET is_banned = 0, ban_reason = NULL, banned_by = NULL, ban_date = NULL
                WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
    
    def increment_link_visits(self, user_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET link_visits = link_visits + 1 WHERE user_id = ?
            ''', (user_id,))
            conn.commit()
    
    def get_banned_users(self, page: int, per_page: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT user_id, username, ban_reason, ban_date 
                FROM users 
                WHERE is_banned = 1
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    # Link methods
    def create_link(
        self,
        link_code: str,
        content_type: str,
        created_by: int,
        content_text: str = None,
        content_file_id: str = None
    ) -> bool:
        """Создать новую ссылку"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    '''INSERT INTO links 
                    (link_code, content_type, content_text, content_file_id, created_by, creation_date)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))''',
                    (link_code, content_type, content_text, content_file_id, created_by)
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"Error creating link: {e}")
                return False
    
    def get_link(self, link_code: str) -> Optional[dict]:
        """Получить ссылку по коду"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM links WHERE link_code = ?", (link_code,))
            result = cursor.fetchone()
            if result:
                return {
                    'link_code': result[0],
                    'content_type': result[1],
                    'content_text': result[2],
                    'content_file_id': result[3],
                    'created_by': result[4],
                    'creation_date': result[5],
                    'visits': result[6],
                    'last_visit': result[7] if len(result) > 7 else None
                }
            return None
    
    def increment_link_visits(self, link_code: str):
        """Увеличить счетчик переходов по ссылке"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE links SET visits = visits + 1, last_visit = datetime('now') WHERE link_code = ?",
                    (link_code,)
                )
                conn.commit()
            except Exception as e:
                print(f"Error incrementing link visits: {e}")
    
    def delete_link(self, link_code: str) -> bool:
        """Удалить ссылку"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM links WHERE link_code = ?", (link_code,))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"Error deleting link: {e}")
                return False
    
    def get_all_links(self, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT * FROM links ORDER BY creation_date DESC LIMIT ? OFFSET ?
            ''', (per_page, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def count_links(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM links')
            return cursor.fetchone()[0]
    
    def update_link_code(self, old_code: str, new_code: str) -> bool:
        """Обновить код ссылки"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE links SET link_code = ? WHERE link_code = ?",
                    (new_code, old_code)
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"Error updating link code: {e}")
                return False
    
    # Admin methods
    def add_admin(self, user_id: int, username: str, added_by: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO admins (user_id, username, added_by, added_date)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (user_id, username, added_by))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def remove_admin(self, user_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def is_admin(self, user_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_admins(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM admins ORDER BY added_date DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_broadcast_stats(self):
        """Возвращает статистику рассылок"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM broadcasts')
            total = cursor.fetchone()[0]
            cursor.execute('SELECT SUM(success_count) FROM broadcasts')
            success = cursor.fetchone()[0] or 0
            cursor.execute('SELECT SUM(failed_count) FROM broadcasts')
            failed = cursor.fetchone()[0] or 0
            cursor.execute('SELECT MAX(send_date) FROM broadcasts')
            last_date = cursor.fetchone()[0]
            return {
                'total': total,
                'success': success,
                'failed': failed,
                'last_date': last_date
            }
    
    def get_top_active_users(self, limit=10):
        """Возвращает топ активных пользователей"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, first_name, username, link_visits as activity_count 
                FROM users 
                ORDER BY activity_count DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Report methods
    def get_report_settings(self):
        """Возвращает настройки репортов"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM report_settings LIMIT 1')
            row = cursor.fetchone()
            return {
                'auto_close': bool(row['auto_close']),
                'notifications': bool(row['notifications'])
            } if row else {'auto_close': False, 'notifications': True}
    
    def get_reports_by_status(self, status: str, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        """Получить репорты по статусу с пагинацией"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT * FROM reports 
                WHERE status = ?
                ORDER BY report_date DESC 
                LIMIT ? OFFSET ?
            ''', (status, per_page, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_open_reports(self, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        """Получить открытые репорты (удобный алиас)"""
        return self.get_reports_by_status('open', page, per_page)
    
    def get_closed_reports(self, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        """Получить закрытые репорты (удобный алиас)"""
        return self.get_reports_by_status('answered', page, per_page)
    
    def update_report_status(self, report_id: int, status: str) -> bool:
        """Обновить статус репорта"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reports SET status = ? WHERE report_id = ?
            ''', (status, report_id))
            conn.commit()
            return cursor.rowcount > 0

    def close_report(self, report_id: int) -> bool:
        """Закрыть репорт (удобный алиас)"""
        return self.update_report_status(report_id, 'answered')

    def reopen_report(self, report_id: int) -> bool:
        """Открыть репорт заново (удобный алиас)"""
        return self.update_report_status(report_id, 'open')

    def get_reports_count_by_status(self, status: str) -> int:
        """Получить количество репортов по статусу"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM reports WHERE status = ?', (status,))
            return cursor.fetchone()[0]

    def get_user_reports(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить все репорты пользователя"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM reports 
                WHERE user_id = ?
                ORDER BY report_date DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_reports(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Получить последние репорты"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM reports
                ORDER BY report_date DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def search_reports(self, search_term: str) -> List[Dict[str, Any]]:
        """Поиск репортов по тексту сообщения"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM reports 
                WHERE message LIKE ?
                ORDER BY report_date DESC
            ''', (f'%{search_term}%',))
            return [dict(row) for row in cursor.fetchall()]

    def create_report(self, user_id: int, message: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reports (user_id, message, report_date)
                VALUES (?, ?, datetime('now'))
            ''', (user_id, message))
            conn.commit()
            return cursor.lastrowid
    
    def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM reports WHERE report_id = ?', (report_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def answer_report(self, report_id: int, answer: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reports SET answer = ?, status = 'answered' WHERE report_id = ?
            ''', (answer, report_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_report(self, report_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM reports WHERE report_id = ?', (report_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_all_reports(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM reports ORDER BY report_date DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def count_reports(self, status: str = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT COUNT(*) FROM reports'
            params = []
            
            if status:
                query += ' WHERE status = ?'
                params.append(status)
            
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    
    # Subscription channel methods
    def add_subscription_channel(self, channel_id: str, username: str, title: str, 
                           added_by: int, check_type: int = 1) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO subscription_channels 
                    (channel_id, username, title, added_by, added_date, check_type)
                    VALUES (?, ?, ?, ?, datetime('now'), ?)
                ''', (channel_id, username, title, added_by, check_type))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def remove_subscription_channel(self, channel_id: str) -> bool:
        """Удалить канал подписки"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM subscription_channels WHERE channel_id = ?', (channel_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_subscription_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM subscription_channels WHERE channel_id = ?', (channel_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_channel_detail(self, channel_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM subscription_channels 
                WHERE channel_id = ?
            ''', (channel_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_all_subscription_channels(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM subscription_channels ORDER BY added_date DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def increment_channel_subscribers(self, channel_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE subscription_channels 
                SET subscribers_count = subscribers_count + 1 
                WHERE channel_id = ?
            ''', (channel_id,))
            conn.commit()
    
    # System message methods
    def add_system_message(self, message_text: str, sent_by: int, recipients_count: int) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_messages (message_text, sent_by, sent_date, recipients_count)
                VALUES (?, ?, datetime('now'), ?)
            ''', (message_text, sent_by, recipients_count))
            conn.commit()
            return cursor.lastrowid
    
    def get_system_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM system_messages WHERE message_id = ?', (message_id,))
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_all_system_messages(self, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page
            cursor.execute('''
                SELECT * FROM system_messages ORDER BY sent_date DESC LIMIT ? OFFSET ?
            ''', (per_page, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def count_system_messages(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM system_messages')
            return cursor.fetchone()[0]
    
    # Log methods
    def add_log(self, level: str, message: str, traceback: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO logs (level, message, timestamp, traceback)
                VALUES (?, ?, datetime('now'), ?)
            ''', (level, message, traceback))
            conn.commit()
    
    def get_logs(self, page: int = 1, per_page: int = 10, level: str = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            offset = (page - 1) * per_page
            query = 'SELECT * FROM logs'
            params = []
            
            if level:
                query += ' WHERE level = ?'
                params.append(level)
            
            query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
            params.extend([per_page, offset])
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def count_logs(self, level: str = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT COUNT(*) FROM logs'
            params = []
            
            if level:
                query += ' WHERE level = ?'
                params.append(level)
            
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    
    def clear_logs(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM logs')
            conn.commit()
    
    # Developer methods
    def add_developer(self, user_id: int, username: str, added_by: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO developers (user_id, username, added_by, added_date)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (user_id, username, added_by))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
    
    def remove_developer(self, user_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM developers WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def is_developer(self, user_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM developers WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
    
    def get_all_developers(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM developers ORDER BY added_date DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    # Statistics methods
    def get_user_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            stats = {
                'total_users': 0,
                'active_users': 0,
                'banned_users': 0,
                'total_links': 0,
                'total_link_visits': 0,
                'total_reports': 0,
                'open_reports': 0,
                'closed_reports': 0,
                'subscription_channels': 0
            }
        
            try:
                # Total users
                cursor.execute('SELECT COUNT(*) FROM users')
                result = cursor.fetchone()
                stats['total_users'] = result[0] if result and result[0] is not None else 0
            
                # Active users (active in last 30 days)
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE last_active >= datetime('now', '-30 days')
                ''')
                result = cursor.fetchone()
                stats['active_users'] = result[0] if result and result[0] is not None else 0
            
                # Banned users
                cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
                result = cursor.fetchone()
                stats['banned_users'] = result[0] if result and result[0] is not None else 0
            
                # Total links
                cursor.execute('SELECT COUNT(*) FROM links')
                result = cursor.fetchone()
                stats['total_links'] = result[0] if result and result[0] is not None else 0
            
                # Total link visits
                cursor.execute('SELECT SUM(visits) FROM links')
                result = cursor.fetchone()
                stats['total_link_visits'] = result[0] if result and result[0] is not None else 0
            
                # Total reports
                cursor.execute('SELECT COUNT(*) FROM reports')
                result = cursor.fetchone()
                stats['total_reports'] = result[0] if result and result[0] is not None else 0
            
                # Open reports
                cursor.execute('SELECT COUNT(*) FROM reports WHERE status = "open"')
                result = cursor.fetchone()
                stats['open_reports'] = result[0] if result and result[0] is not None else 0
            
                # Closed reports
                cursor.execute('SELECT COUNT(*) FROM reports WHERE status = "closed"')
                result = cursor.fetchone()
                stats['closed_reports'] = result[0] if result and result[0] is not None else 0
            
                # Subscription channels
                cursor.execute('SELECT COUNT(*) FROM subscription_channels')
                result = cursor.fetchone()
                stats['subscription_channels'] = result[0] if result and result[0] is not None else 0
            
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
            
            return stats
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            stats = {
                'new_users_24h': 0,
                'new_users_7d': 0,
                'active_24h': 0,
                'active_7d': 0,
                'new_links_24h': 0,
                'new_links_7d': 0,
                'visits_24h': 0,
                'visits_7d': 0
            }
        
            try:
                # Новые пользователи (24ч)
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE join_date >= datetime('now', '-1 day')
                ''')
                result = cursor.fetchone()
                stats['new_users_24h'] = result[0] if result else 0
            
                # Новые пользователи (7д)
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE join_date >= datetime('now', '-7 days')
                ''')
                result = cursor.fetchone()
                stats['new_users_7d'] = result[0] if result else 0
            
                # Активные пользователи (24ч)
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE last_active >= datetime('now', '-1 day')
                ''')
                result = cursor.fetchone()
                stats['active_24h'] = result[0] if result else 0
            
                # Активные пользователи (7д)
                cursor.execute('''
                    SELECT COUNT(*) FROM users 
                    WHERE last_active >= datetime('now', '-7 days')
                ''')
                result = cursor.fetchone()
                stats['active_7d'] = result[0] if result else 0
            
                # Новые ссылки (24ч)
                cursor.execute('''
                    SELECT COUNT(*) FROM links 
                    WHERE creation_date >= datetime('now', '-1 day')
                ''')
                result = cursor.fetchone()
                stats['new_links_24h'] = result[0] if result else 0
            
                # Новые ссылки (7д)
                cursor.execute('''
                    SELECT COUNT(*) FROM links 
                    WHERE creation_date >= datetime('now', '-7 days')
                ''')
                result = cursor.fetchone()
                stats['new_links_7d'] = result[0] if result else 0
            
                # Переходы (24ч)
                cursor.execute('''
                    SELECT SUM(visits) FROM links 
                    WHERE creation_date >= datetime('now', '-1 day')
                ''')
                result = cursor.fetchone()
                stats['visits_24h'] = result[0] if result and result[0] else 0
            
                # Переходы (7д)
                cursor.execute('''
                    SELECT SUM(visits) FROM links 
                    WHERE creation_date >= datetime('now', '-7 days')
                ''')
                result = cursor.fetchone()
                stats['visits_7d'] = result[0] if result and result[0] else 0
            
            except Exception as e:
                logger.error(f"Error getting detailed stats: {e}")
            
            return stats
    
    # Backup methods
    def create_backup(self) -> str:
        """Create a database backup and return backup file path"""
        backup_path = os.path.join(config.DB_BACKUP_DIR, 
                                 f"{config.DB_NAME}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        
        with self._get_connection() as src:
            with sqlite3.connect(backup_path) as dst:
                src.backup(dst)
        
        return backup_path
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        if not os.path.exists(backup_path):
            return False
        
        with sqlite3.connect(backup_path) as src:
            with self._get_connection() as dst:
                src.backup(dst)
        
        return True
    
    def reset_database(self):
        """Reset all database tables"""
        tables = [
            'users', 'links', 'admins', 'reports', 
            'subscription_channels', 'system_messages', 'logs', 'developers',
            'broadcasts', 'user_activity', 'report_settings', 'user_settings'
        ]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for table in tables:
                cursor.execute(f'DELETE FROM {table}')
            conn.commit()
            
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            return dict(result) if result else None