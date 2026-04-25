import os
import sys
from pathlib import Path
from typing import Optional
import winshell


class AutostartManager:
    """Менеджер для управления автозапуском приложения."""
    
    def __init__(self):
        self._startup_folder: Optional[Path] = None
        self._executable_path: Optional[Path] = None
    
    @property
    def startup_folder(self) -> Path:
        """Возвращает путь к папке автозапуска."""
        if self._startup_folder is None:
            self._startup_folder = Path(winshell.startup())
        return self._startup_folder
    
    @property
    def executable_path(self) -> Path:
        """Возвращает путь к исполняемому файлу приложения."""
        if self._executable_path is None:
            if getattr(sys, 'frozen', False):
                self._executable_path = Path(sys.executable)
            else:
                self._executable_path = Path(sys.argv[0]).absolute()
        return self._executable_path
    
    @property
    def shortcut_path(self) -> Path:
        """Возвращает путь к ярлыку в папке автозапуска."""
        shortcut_name = f"{self.executable_path.stem}.lnk"
        return self.startup_folder / shortcut_name
    
    def is_enabled(self) -> bool:
        """Проверяет, добавлено ли приложение в автозапуск."""
        return self.shortcut_path.exists()
    
    def enable(self) -> bool:
        """Добавляет приложение в автозапуск."""
        try:
            with winshell.shortcut(str(self.shortcut_path)) as link:
                link.path = str(self.executable_path)
                link.description = "Recycle Bin Manager"
                link.working_directory = str(self.executable_path.parent)
            return True
        except Exception as e:
            print(f"Ошибка при добавлении в автозапуск: {e}")
            return False
    
    def disable(self) -> bool:
        """Удаляет приложение из автозапуска."""
        try:
            if self.shortcut_path.exists():
                self.shortcut_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Ошибка при удалении из автозапуска: {e}")
            return False


# Создаем глобальный экземпляр для обратной совместимости
_autostart_manager = AutostartManager()


def is_autostart_enabled() -> bool:
    """Проверяет автозапуск (обертка для совместимости)."""
    return _autostart_manager.is_enabled()


def enable_autostart() -> bool:
    """Включает автозапуск (обертка для совместимости)."""
    return _autostart_manager.enable()


def disable_autostart() -> bool:
    """Отключает автозапуск (обертка для совместимости)."""
    return _autostart_manager.disable()