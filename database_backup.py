# utils/database_backup.py
import os
from datetime import datetime
from config import config
import logging

def create_database_backup():
    """Create a backup of the database"""
    backup_dir = config.DB_BACKUP_DIR
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{config.DB_NAME}_backup_{timestamp}.db")
    
    try:
        with open(config.DB_NAME, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        logging.info(f"Database backup created: {backup_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to create database backup: {e}")
        return False