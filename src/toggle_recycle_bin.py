import ctypes
import winreg
from typing import Optional


class RecycleBinVisibilityManager:
    """Менеджер для управления видимостью корзины на рабочем столе."""
    
    # Константы реестра
    REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel"
    RECYCLE_BIN_GUID = "{645FF040-5081-101B-9F08-00AA002F954E}"
    
    # Константы для SHChangeNotify
    SHCNE_ASSOCCHANGED = 0x8000000
    SHCNF_IDLIST = 0x1000
    
    @classmethod
    def set_visibility(cls, visible: bool) -> bool:
        """
        Устанавливает видимость корзины на рабочем столе.
        
        Args:
            visible: True - показывать корзину, False - скрыть
            
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            # Устанавливаем значение в реестре
            value = 0 if visible else 1
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY_PATH, 
                               0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, cls.RECYCLE_BIN_GUID, 0, winreg.REG_DWORD, value)
            
            # Обновляем рабочий стол
            ctypes.windll.shell32.SHChangeNotify(cls.SHCNE_ASSOCCHANGED, 
                                                cls.SHCNF_IDLIST, None, None)
            return True
            
        except Exception as e:
            print(f"Ошибка при установке видимости корзины: {e}")
            return False
    
    @classmethod
    def is_visible(cls) -> bool:
        """
        Проверяет, видима ли корзина на рабочем столе.
        
        Returns:
            bool: True если корзина видима, иначе False
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.REG_KEY_PATH, 
                               0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, cls.RECYCLE_BIN_GUID)
                return value == 0
                
        except FileNotFoundError:
            # Если ключ отсутствует, корзина видима по умолчанию
            return True
        except Exception as e:
            print(f"Ошибка при чтении состояния корзины: {e}")
            return True


# Для обратной совместимости
def toggle_show_recycle_bin(checked: bool) -> None:
    """Включает/отключает отображение корзины (обертка для совместимости)."""
    RecycleBinVisibilityManager.set_visibility(checked)


def is_recycle_bin_visible() -> bool:
    """Возвращает видимость корзины (обертка для совместимости)."""
    return RecycleBinVisibilityManager.is_visible()