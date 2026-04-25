import ctypes
import sys
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
)
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtCore import QTimer, QSettings

from toggle_recycle_bin import RecycleBinVisibilityManager
from icon_manager import IconManager
import autostart as autostart


@dataclass
class RecycleBinInfo:
    """Информация о состоянии корзины."""
    items_count: int
    total_size: int
    
    @property
    def is_empty(self) -> bool:
        return self.items_count == 0
    
    @property
    def formatted_size(self) -> str:
        """Возвращает отформатированный размер."""
        return self._format_size(self.total_size)
    
    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Форматирует размер в человекочитаемый вид."""
        if bytes_size < 1024:
            return f"{bytes_size} B"
        
        size = bytes_size / 1024  # KB
        if size < 1024:
            return f"{size:.1f} KB"
        
        size /= 1024  # MB
        if size < 1024:
            return f"{size:.0f} MB"
        
        size /= 1024  # GB
        if size < 1024:
            return f"{size:.0f} GB"
        
        size /= 1024  # TB
        return f"{size:.2f} TB"


class RecycleBinAPI:
    """API для работы с системной корзиной Windows."""
    
    CSIDL_BITBUCKET = 0x000a
    EMPTY_RB_ALL = 0x01
    
    class SHQUERYRBINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("i64Size", ctypes.c_int64),
            ("i64NumItems", ctypes.c_int64),
        ]
    
    @classmethod
    def get_info(cls) -> Optional[RecycleBinInfo]:
        """Получает информацию о корзине."""
        rbinfo = cls.SHQUERYRBINFO()
        rbinfo.cbSize = ctypes.sizeof(cls.SHQUERYRBINFO)
        
        result = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rbinfo))
        
        if result != 0:
            return None
        
        return RecycleBinInfo(
            items_count=rbinfo.i64NumItems,
            total_size=rbinfo.i64Size
        )
    
    @classmethod
    def empty(cls) -> bool:
        """Очищает корзину. Возвращает True при успехе."""
        try:
            bin_path = ctypes.create_unicode_buffer(260)
            ctypes.windll.shell32.SHGetFolderPathW(
                0, cls.CSIDL_BITBUCKET, 0, 0, bin_path
            )
            
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(
                None, bin_path.value, cls.EMPTY_RB_ALL
            )
            
            return result == 0 or result == -2147418113
            
        except Exception as e:
            print(f"Ошибка при очистке корзины: {e}")
            return False
    
    @classmethod
    def open(cls) -> bool:
        """Открывает окно корзины. Возвращает True при успехе."""
        try:
            os.startfile("shell:RecycleBinFolder")
            return True
        except Exception as e:
            print(f"Ошибка при открытии корзины: {e}")
            return False


class RecycleBinTrayApp:
    """Главное приложение для управления корзиной из системного трея."""
    
    # Константы настроек
    SETTINGS_ICON_SET = "icon_set"
    SETTINGS_SHOW_NOTIFICATIONS = "show_notifications"
    SETTINGS_UPDATE_INTERVAL = "update_interval"
    
    # Значения по умолчанию
    DEFAULT_ICON_SET = "default"
    DEFAULT_SHOW_NOTIFICATIONS = True
    DEFAULT_UPDATE_INTERVAL = 1  # секунды
    
    # Доступные интервалы обновления
    AVAILABLE_INTERVALS = [1, 3, 5]
    
    def __init__(self):
        """Инициализирует приложение."""
        self.app = QApplication(sys.argv)
        self.settings = QSettings("RecycleBinManager", "RecycleManager")
        self.icon_manager = IconManager(self.settings)
        
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.timer: Optional[QTimer] = None
        
        # Действия меню
        self.autostart_action: Optional[QAction] = None
        self.notifications_action: Optional[QAction] = None
        self.show_recycle_bin_action: Optional[QAction] = None
    
    def run(self) -> int:
        """Запускает приложение."""
        # Проверяем иконки
        if not self.icon_manager.verify_icons():
            print("Ошибка: Не найдены необходимые иконки")
            return 1
        
        # Создаем и настраиваем трей
        self._create_tray_icon()
        self._setup_timer()
        
        return self.app.exec()
    
    def _create_tray_icon(self) -> None:
        """Создает и настраивает иконку в системном трее."""
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(self.icon_manager.load_main_icon("recycle-empty.ico"))
        self.tray_icon.setToolTip("Менеджер Корзины")
        
        # Создаем контекстное меню
        menu = self._create_context_menu()
        self.tray_icon.setContextMenu(menu)
        
        # Подключаем сигналы
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.show()
        
        # Первоначальное обновление
        self._update_icon()
    
    def _create_context_menu(self) -> QMenu:
        """Создает контекстное меню для трея."""
        menu = QMenu()
        
        # Основные действия
        menu.addAction("Открыть корзину", self._open_recycle_bin)
        menu.addAction("Очистить корзину", self._empty_recycle_bin)
        menu.addSeparator()
        
        # Дополнительные меню
        self._add_autostart_menu(menu)
        self._add_notifications_menu(menu)
        self._add_recycle_bin_visibility_menu(menu)
        self._add_icon_set_menu(menu)
        self._add_update_interval_menu(menu)
        
        # Выход
        menu.addSeparator()
        menu.addAction("Выход", self._exit_program)
        
        return menu
    
    def _add_autostart_menu(self, menu: QMenu) -> None:
        """Добавляет пункт меню автозапуска."""
        self.autostart_action = QAction("Автозапуск", checkable=True)
        self.autostart_action.setChecked(autostart.is_autostart_enabled())
        self.autostart_action.triggered.connect(self._toggle_autostart)
        menu.addAction(self.autostart_action)
    
    def _add_notifications_menu(self, menu: QMenu) -> None:
        """Добавляет пункт меню уведомлений."""
        self.notifications_action = QAction("Показывать уведомления", checkable=True)
        self.notifications_action.setChecked(
            self.settings.value(self.SETTINGS_SHOW_NOTIFICATIONS, 
                              self.DEFAULT_SHOW_NOTIFICATIONS, type=bool)
        )
        self.notifications_action.triggered.connect(self._toggle_notifications)
        menu.addAction(self.notifications_action)
        menu.addSeparator()
    
    def _add_recycle_bin_visibility_menu(self, menu: QMenu) -> None:
        """Добавляет пункт меню видимости корзины."""
        self.show_recycle_bin_action = QAction("Отображать 🗑️ на рабочем столе", checkable=True)
        self.show_recycle_bin_action.setChecked(RecycleBinVisibilityManager.is_visible())
        self.show_recycle_bin_action.triggered.connect(self._toggle_recycle_bin_visibility)
        menu.addAction(self.show_recycle_bin_action)
        menu.addSeparator()
    
    def _add_icon_set_menu(self, menu: QMenu) -> None:
        """Добавляет меню выбора набора иконок."""
        icon_set_menu = QMenu("Выбрать набор иконок", menu)
        available_sets = self.icon_manager.get_available_icon_sets()
        
        if not available_sets:
            return
        
        action_group = QActionGroup(icon_set_menu)
        action_group.setExclusive(True)
        
        current_set = self.icon_manager.get_current_icon_set()
        
        for icon_set in available_sets:
            action = QAction(icon_set, checkable=True, parent=action_group)
            action.setData(icon_set)
            action.setChecked(icon_set == current_set)
            action.triggered.connect(lambda checked, name=icon_set: self._set_icon_set(name))
            icon_set_menu.addAction(action)
        
        menu.addMenu(icon_set_menu)
    
    def _add_update_interval_menu(self, menu: QMenu) -> None:
        """Добавляет меню выбора интервала обновления."""
        interval_menu = QMenu("Таймер обновления корзины", menu)
        action_group = QActionGroup(interval_menu)
        action_group.setExclusive(True)
        
        current_interval = self.settings.value(
            self.SETTINGS_UPDATE_INTERVAL, 
            self.DEFAULT_UPDATE_INTERVAL, 
            type=int
        )
        
        if current_interval not in self.AVAILABLE_INTERVALS:
            current_interval = self.DEFAULT_UPDATE_INTERVAL
        
        for interval in self.AVAILABLE_INTERVALS:
            action = QAction(f"{interval} сек", checkable=True, parent=action_group)
            action.setChecked(interval == current_interval)
            action.triggered.connect(lambda checked, sec=interval: self._set_update_interval(sec))
            interval_menu.addAction(action)
        
        menu.addMenu(interval_menu)
    
    def _setup_timer(self) -> None:
        """Настраивает таймер для периодического обновления."""
        interval = self.settings.value(
            self.SETTINGS_UPDATE_INTERVAL,
            self.DEFAULT_UPDATE_INTERVAL,
            type=int
        )
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_icon)
        self.timer.start(interval * 1000)
    
    def _update_icon(self) -> None:
        """Обновляет иконку и тултип в трее."""
        bin_info = RecycleBinAPI.get_info()
        
        if bin_info is None:
            self.tray_icon.setIcon(self.icon_manager.load_main_icon("recycle-full.ico"))
            self.tray_icon.setToolTip("Менеджер Корзины")
            return
        
        # Обновляем иконку
        icon_name = "recycle-empty.ico" if bin_info.is_empty else "recycle-full.ico"
        self.tray_icon.setIcon(self.icon_manager.load_main_icon(icon_name))
        
        # Обновляем тултип
        tooltip = f"Менеджер Корзины\nЭлементов: {bin_info.items_count}\nЗанято: {bin_info.formatted_size}"
        self.tray_icon.setToolTip(tooltip)
    
    def _show_notification(self, title: str, message: str, icon_name: str = None, is_main: bool = True) -> None:
        """Отображает системное уведомление."""
        if not self.settings.value(self.SETTINGS_SHOW_NOTIFICATIONS, self.DEFAULT_SHOW_NOTIFICATIONS, type=bool):
            return
        
        icon = QIcon()
        if icon_name:
            if is_main:
                icon = self.icon_manager.load_main_icon(icon_name)
            else:
                icon = self.icon_manager.load_common_icon(icon_name)
        
        self.tray_icon.showMessage(title, message, icon, 5000)
    
    def _empty_recycle_bin(self) -> None:
        """Очищает корзину."""
        success = RecycleBinAPI.empty()
        
        if success:
            self._show_notification("Корзина", "Корзина успешно очищена.", "recycle-empty.ico")
        else:
            self._show_notification("Корзина", "Произошла ошибка при очистке корзины.", "recycle-full.ico")
        
        self._update_icon()
    
    def _open_recycle_bin(self) -> None:
        """Открывает окно корзины."""
        if not RecycleBinAPI.open():
            self._show_notification("Ошибка", "Не удалось открыть корзину.", "recycle-full.ico")
    
    def _toggle_autostart(self, checked: bool) -> None:
        """Включает/отключает автозапуск."""
        if checked:
            success = autostart.enable_autostart()
            icon = "autostart-enabled.ico"
            message = "Автозапуск включен."
        else:
            success = autostart.disable_autostart()
            icon = "autostart-disabled.ico"
            message = "Автозапуск отключен."
        
        if success:
            self._show_notification("Автозапуск", message, icon, is_main=False)
        else:
            self._show_notification("Автозапуск", f"Не удалось {message.lower()}", icon, is_main=False)
            self.autostart_action.setChecked(not checked)
    
    def _toggle_notifications(self, checked: bool) -> None:
        """Включает/отключает уведомления."""
        self.settings.setValue(self.SETTINGS_SHOW_NOTIFICATIONS, checked)
        if checked:
            self._show_notification("Уведомления", "Уведомления включены.", "notifications-enabled.ico", is_main=False)
    
    def _toggle_recycle_bin_visibility(self, checked: bool) -> None:
        """Включает/отключает видимость корзины на рабочем столе."""
        RecycleBinVisibilityManager.set_visibility(checked)
    
    def _set_icon_set(self, set_name: str) -> None:
        """Устанавливает набор иконок."""
        self.icon_manager.set_icon_set(set_name)
        self._update_icon()
        self._show_notification("Набор иконок", f"Выбран набор иконок: {set_name}")
    
    def _set_update_interval(self, seconds: int) -> None:
        """Устанавливает интервал обновления."""
        self.timer.setInterval(seconds * 1000)
        self.settings.setValue(self.SETTINGS_UPDATE_INTERVAL, seconds)
        self._show_notification("Таймер обновления", f"Интервал обновления установлен на {seconds} сек.", is_main=False)
    
    def _on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Обрабатывает активацию иконки в трее."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_recycle_bin()
    
    def _exit_program(self) -> None:
        """Завершает работу приложения."""
        QApplication.quit()


def main() -> int:
    """Главная функция приложения."""
    if os.name != 'nt':
        print("Это приложение работает только на Windows.")
        return 1
    
    app = RecycleBinTrayApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())