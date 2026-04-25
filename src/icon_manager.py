import sys
from pathlib import Path
from typing import List, Optional
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSettings


class IconManager:
    """Менеджер для управления иконками приложения."""
    
    def __init__(self, settings: QSettings, icons_base_path: Optional[Path] = None):
        """
        Инициализирует менеджер иконок.
        
        Args:
            settings: Объект настроек QSettings
            icons_base_path: Путь к папке с иконками (если None, определяется автоматически)
        """
        self.settings = settings
        
        if icons_base_path:
            self.base_path = icons_base_path
        else:
            self.base_path = self._get_base_path()
        
        self.icons_path = self.base_path / "icons"
    
    @staticmethod
    def _get_base_path() -> Path:
        """Возвращает базовый путь к ресурсам приложения."""
        try:
            # Для собранного приложения (PyInstaller)
            return Path(sys._MEIPASS)
        except AttributeError:
            # Для режима разработки - поднимаемся на уровень выше (из src в корень)
            return Path(__file__).parent.parent
    
    def resource_path(self, relative_path: str) -> str:
        """Получает полный путь к ресурсу."""
        full_path = self.base_path / relative_path
        if not full_path.exists():
            raise FileNotFoundError(f"Ресурс не найден: {full_path}")
        return str(full_path)
    
    def get_current_icon_set(self) -> str:
        """Возвращает текущий выбранный набор иконок."""
        return self.settings.value("icon_set", "default")
    
    def set_icon_set(self, set_name: str) -> None:
        """Устанавливает выбранный набор иконок."""
        self.settings.setValue("icon_set", set_name)
    
    def load_main_icon(self, icon_name: str) -> QIcon:
        """Загружает основную иконку из выбранного набора."""
        icon_set = self.get_current_icon_set()
        icon_path = self.icons_path / "icon_sets" / icon_set / icon_name
        return self._load_icon(icon_path)
    
    def load_common_icon(self, icon_name: str) -> QIcon:
        """Загружает общую иконку из папки common."""
        icon_path = self.icons_path / "common" / icon_name
        return self._load_icon(icon_path)
    
    def _load_icon(self, icon_path: Path) -> QIcon:
        """Загружает иконку по полному пути."""
        try:
            if not icon_path.exists():
                raise FileNotFoundError(f"Иконка не найдена: {icon_path}")
            return QIcon(str(icon_path))
        except Exception as e:
            print(f"Ошибка при загрузке иконки '{icon_path}': {e}")
            return QIcon()
    
    def get_available_icon_sets(self) -> List[str]:
        """Возвращает список доступных наборов иконок."""
        try:
            icon_sets_dir = self.icons_path / "icon_sets"
            if not icon_sets_dir.exists():
                return []
            return [p.name for p in icon_sets_dir.iterdir() if p.is_dir()]
        except Exception as e:
            print(f"Ошибка при получении списка наборов иконок: {e}")
            return []
    
    def verify_icons(self) -> bool:
        """Проверяет наличие всех необходимых иконок."""
        print(f"Базовый путь: {self.base_path}")
        print(f"Путь к иконкам: {self.icons_path}")
        
        # Проверяем, существует ли папка с иконками
        if not self.icons_path.exists():
            print(f"Ошибка: Папка с иконками не найдена - {self.icons_path}")
            return False
        
        # Проверяем наборы иконок
        icon_sets = self.get_available_icon_sets()
        if not icon_sets:
            print(f"Ошибка: Не найдено наборов иконок в {self.icons_path / 'icon_sets'}")
            return False
        
        required_main_icons = ["recycle-empty.ico", "recycle-full.ico"]
        for icon_set in icon_sets:
            for icon_name in required_main_icons:
                icon_path = self.icons_path / "icon_sets" / icon_set / icon_name
                if not icon_path.exists():
                    print(f"Ошибка: Иконка не найдена - {icon_path}")
                    return False
        
        # Проверяем общие иконки
        required_common_icons = [
            "autostart-enabled.ico",
            "autostart-disabled.ico", 
            "notifications-enabled.ico",
        ]
        
        for icon_name in required_common_icons:
            icon_path = self.icons_path / "common" / icon_name
            if not icon_path.exists():
                print(f"Ошибка: Общая иконка не найдена - {icon_path}")
                return False
        
        print("✓ Все иконки успешно проверены")
        return True