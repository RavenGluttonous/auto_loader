import pyautogui
import pyperclip


def paste_text(text: str):
    """
    把文本录入粘贴板，然后调用ctrl+v使用粘贴快捷键
    Args:
        text: 需要粘贴的文本

    """
    pyperclip.copy(text)
    pyautogui.keyDown("ctrl")
    pyautogui.press("a")
    pyautogui.press("v")
    pyautogui.keyUp("ctrl")


def delete_text():
    pyautogui.keyDown("ctrl")
    pyautogui.press("a")
    pyautogui.keyUp("ctrl")
    pyautogui.press("delete")


def auto_input(text: str | int):
    is_str = isinstance(text, str)
    is_int = isinstance(text, int)
    if is_str:
        if len(text) != 0:
            paste_text(text)
    elif is_int:
        paste_text(text)
    elif not is_str or not is_int:
        pass
    pyautogui.press('tab')
