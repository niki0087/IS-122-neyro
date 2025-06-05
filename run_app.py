#!/usr/bin/env python3

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_qt_environment():
    """Исправление окружения Qt для работы в виртуальном окружении"""
    try:
        if sys.platform.startswith('linux'):
            os.environ['QT_QPA_PLATFORM'] = 'xcb'
            
            # Получаем путь к плагинам из установки PyQt5
            from PyQt5.QtCore import QLibraryInfo
            qt_plugin_path = QLibraryInfo.location(QLibraryInfo.PluginsPath)
            os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
            
            xcb_plugin = os.path.join(qt_plugin_path, 'platforms', 'libqxcb.so')
            if not os.path.exists(xcb_plugin):
                logger.warning(f"Qt xcb plugin not found at: {xcb_plugin}")
            else:
                logger.info(f"Found Qt xcb plugin at: {xcb_plugin}")
            
            qt_lib_path = QLibraryInfo.location(QLibraryInfo.LibrariesPath)
            if 'LD_LIBRARY_PATH' in os.environ:
                os.environ['LD_LIBRARY_PATH'] = qt_lib_path + ':' + os.environ['LD_LIBRARY_PATH']
            else:
                os.environ['LD_LIBRARY_PATH'] = qt_lib_path
            
            logger.info(f"Set LD_LIBRARY_PATH to: {os.environ['LD_LIBRARY_PATH']}")
            
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugin_path, 'platforms')
            logger.info(f"Set QT_QPA_PLATFORM_PLUGIN_PATH to: {os.environ['QT_QPA_PLATFORM_PLUGIN_PATH']}")
        else:
            # Для не-Linux систем просто устанавливаем QT_PLUGIN_PATH
            from PyQt5.QtCore import QLibraryInfo
            qt_plugin_path = QLibraryInfo.location(QLibraryInfo.PluginsPath)
            os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
            logger.info(f"Set QT_PLUGIN_PATH to: {qt_plugin_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error setting Qt environment: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting application...")
    
    if not fix_qt_environment():
        logger.error("Failed to fix Qt environment. Application may not start properly.")
    
    from app.gui import start_app
    
    try:
        start_app()
    except Exception as e:
        logger.exception(f"Application failed: {str(e)}")
        sys.exit(1)